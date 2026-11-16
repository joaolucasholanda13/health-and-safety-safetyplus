#!/usr/bin/env python3
"""Run a bounded capacity test with an ephemeral, ordinary test account.

Run on the VPS host. Requires Docker access, the capacity_test.py sibling and
the existing Caddy CA certificate. Passwords remain in memory; cookies are
stored with mode 0600 and removed in finally. Application code is not changed.
"""
from __future__ import annotations

import argparse
import json
from http.cookies import SimpleCookie
from html.parser import HTMLParser
import os
from pathlib import Path
import secrets
import signal
import ssl
import subprocess
import sys
import threading
import time
from urllib.parse import urlencode, urlsplit

from capacity_test import AddressHTTPSConnection, Config


CREATE_ACCOUNT = '''
import json,sys
from app.database import SessionLocal,User
from app.security import hash_password
p=json.load(sys.stdin)
with SessionLocal.begin() as db:
    user=User(username=p['username'],full_name='Teste temporario de capacidade',
        password_hash=hash_password(p['password']),role='Usuário',active=True)
    db.add(user);db.flush()
    print(json.dumps({'id':user.id,'username':user.username}))
'''

DELETE_ACCOUNT = '''
import json,sys
from sqlalchemy import inspect,MetaData,Table,select,func,or_
from app.database import SessionLocal,User,engine
p=json.load(sys.stdin)
with SessionLocal.begin() as db:
    user=db.get(User,p['id'])
    if not user:
        print(json.dumps({'removed':False,'already_absent':True}));sys.exit(0)
    if user.username!=p['username'] or not user.username.startswith('capacity_') or user.role!='Usuário':
        raise RuntimeError('Test account identity mismatch')
    inspector=inspect(engine)
    for name in inspector.get_table_names():
        if name in ('users','audit_logs'):continue
        columns=set()
        for fk in inspector.get_foreign_keys(name):
            if fk.get('referred_table')=='users' and fk.get('referred_columns')==['id']:
                columns.update(fk['constrained_columns'])
        if name=='support_tickets':columns.update(('user_id','assigned_to'))
        if columns:
            table=Table(name,MetaData(),autoload_with=engine)
            conditions=[table.c[c]==user.id for c in columns if c in table.c]
            if conditions and db.execute(select(func.count()).select_from(table).where(or_(*conditions))).scalar():
                raise RuntimeError('Test account has linked records; cleanup cancelled')
    db.delete(user)
print(json.dumps({'removed':True,'linked_records':0}))
'''


def private_json(path: Path, value) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        json.dump(value, stream, indent=2)


def docker_python(container: str, code: str, payload: dict) -> dict:
    result = subprocess.run(['docker', 'exec', '-i', container, 'python', '-c', code],
                            input=json.dumps(payload), text=True, capture_output=True, timeout=45)
    if result.returncode:
        # Exception output may contain SQL parameters. Keep it out of console/report.
        raise RuntimeError('Test-account database operation failed')
    return json.loads(result.stdout)


class CSRFParser(HTMLParser):
    token = None

    def handle_starttag(self, tag, attributes):
        values = dict(attributes)
        if tag == 'input' and values.get('name') == 'csrf_token':
            self.token = values.get('value')


def authenticate(config: Config, username: str, password: str, user_id: int) -> str:
    target = urlsplit(config.base_url)
    context = ssl.create_default_context(cafile=config.ca_file)
    connection = AddressHTTPSConnection(target.hostname, target.port or 443,
        connect_address=config.connect_address, timeout=10, context=context)
    cookie = ''

    def request(method, route, body=None):
        nonlocal cookie
        headers = {'Host': target.netloc, 'User-Agent': 'SafetyPlus-CapacitySetup/1.0'}
        if cookie:
            headers['Cookie'] = cookie
        if body is not None:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        connection.request(method, route, body=body, headers=headers)
        response = connection.getresponse()
        content = response.read()
        for name, value in response.getheaders():
            if name.lower() == 'set-cookie':
                parsed = SimpleCookie(); parsed.load(value)
                if 'session' in parsed:
                    cookie = 'session=' + parsed['session'].value
        return response, content

    try:
        response, body = request('GET', '/login')
        if response.status != 200:
            raise RuntimeError('Login page did not respond with HTTP 200')
        parser = CSRFParser(); parser.feed(body.decode('utf-8'))
        if not parser.token or not cookie:
            raise RuntimeError('Login session or CSRF missing')
        response, _ = request('POST', '/login', urlencode({
            'username': username, 'password': password, 'csrf_token': parser.token}))
        if response.status != 303 or response.getheader('Location') != '/':
            raise RuntimeError('Temporary account login failed')
        # Do not follow the redirect to /: it can close expired permits globally.
        response, content = request('GET', '/api/session/status')
        status = json.loads(content)
        if response.status != 200 or not status.get('authenticated') or status.get('user_id') != user_id:
            raise RuntimeError('Temporary account authentication not confirmed')
        # Receive a CSRF-bearing cookie as a normal browser would on its first page.
        response, _ = request('GET', '/rac')
        if response.status != 200:
            raise RuntimeError('Authenticated read route unavailable')
        return cookie
    finally:
        connection.close()


def memory_info() -> dict:
    values = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key, value = line.split(':', 1)
        values[key] = int(value.split()[0]) * 1024
    return values


def cpu_times():
    values = [int(x) for x in Path('/proc/stat').read_text().splitlines()[0].split()[1:]]
    return sum(values[:8]), values[3] + values[4]


def resource_monitor(container_ids, stop: threading.Event, abort_file: Path, samples: list):
    previous = cpu_times()
    cpu_high = memory_low = 0
    while not stop.wait(2):
        now = cpu_times()
        total, idle = now[0] - previous[0], now[1] - previous[1]
        previous = now
        cpu = 100 * (1 - idle / total) if total else 0
        memory = memory_info()
        available = 100 * memory['MemAvailable'] / memory['MemTotal']
        row = {'time_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
               'cpu_percent': cpu, 'mem_available_percent': available, 'load1': os.getloadavg()[0]}
        try:
            result = subprocess.run(['docker', 'stats', '--no-stream', '--format', '{{json .}}', *container_ids],
                                    text=True, capture_output=True, timeout=8)
            row['containers'] = [json.loads(line) for line in result.stdout.splitlines()] if result.returncode == 0 else []
        except (subprocess.TimeoutExpired, ValueError):
            row['containers'] = []
        samples.append(row)
        cpu_high = cpu_high + 1 if cpu > 95 else 0
        memory_low = memory_low + 1 if available < 15 else 0
        if cpu_high >= 3 or memory_low >= 3:
            private_json(abort_file, {k: row[k] for k in ('cpu_percent', 'mem_available_percent', 'load1')})
            print('RESOURCE_GUARD_TRIGGERED', flush=True)
            return


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compose-dir', type=Path, required=True)
    parser.add_argument('--work-dir', type=Path, required=True)
    parser.add_argument('--ca-file', required=True)
    parser.add_argument('--base-url', default='https://safetyplus.srna.co')
    parser.add_argument('--connect-address', default='127.0.0.1')
    parser.add_argument('--stages', default='1,10,25,50,100,150,200')
    parser.add_argument('--duration', type=float, default=30)
    args = parser.parse_args(argv)
    config = Config(base_url=args.base_url, connect_address=args.connect_address,
                    ca_file=args.ca_file, stages=tuple(map(int, args.stages.split(','))), duration=args.duration)
    config.validate()
    work = args.work_dir.resolve(); work.mkdir(parents=True, exist_ok=True); work.chmod(0o700)
    cookie_file, abort_file = work / 'session-cookie', work / 'abort.json'
    if abort_file.exists():
        raise RuntimeError('Existing abort marker: use a new test directory')
    compose = ['docker', 'compose', '-p', 'safetyplus', '-f', 'docker-compose.yml', '-f', 'docker-compose.offline.yml']
    def container(service):
        return subprocess.check_output([*compose, 'ps', '--status', 'running', '-q', service],
                                       cwd=args.compose_dir, text=True).strip()
    web, database = container('web'), container('db')
    if not web or not database:
        raise RuntimeError('Application or database container not running')
    account = None
    process = None
    samples = []
    stop = threading.Event()
    monitor = None
    metadata = {'status': 'preparing', 'cpus': os.cpu_count(), 'memory_bytes': memory_info()['MemTotal'],
                'account_type': 'one ephemeral ordinary account, shared by virtual clients',
                'document_writes': False, 'stages_requested': list(config.stages), 'duration_seconds': args.duration}
    private_json(work / 'setup.json', metadata)
    def interrupted(_signum, _frame):
        raise KeyboardInterrupt
    for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(signum, interrupted)
    try:
        username = 'capacity_' + time.strftime('%Y%m%d_') + secrets.token_hex(8)
        password = secrets.token_urlsafe(40)
        account = docker_python(web, CREATE_ACCOUNT, {'username': username, 'password': password})
        private_json(work / 'account.json', account)
        print('TEST_ACCOUNT_CREATED', flush=True)
        cookie = authenticate(config, username, password, account['id'])
        descriptor = os.open(cookie_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w') as stream:
            stream.write(cookie)
        password = cookie = None
        print('AUTHENTICATION_CONFIRMED', flush=True)
        monitor = threading.Thread(target=resource_monitor, args=([web, database], stop, abort_file, samples), daemon=True)
        monitor.start()
        command = [sys.executable, str(Path(__file__).with_name('capacity_test.py')),
                   '--base-url', args.base_url, '--connect-address', args.connect_address,
                   '--ca-file', args.ca_file, '--cookie-file', str(cookie_file), '--stages', args.stages,
                   '--duration', str(args.duration), '--think-time', '1', '--cooldown', '5', '--timeout', '5',
                   '--max-p95-ms', '5000', '--max-error-rate', '0.01', '--abort-file', str(abort_file),
                   '--output', str(work / 'results.json')]
        metadata['status'] = 'running'; private_json(work / 'setup.json', metadata)
        process = subprocess.Popen(command)
        code = process.wait()
        metadata['runner_exit_code'] = code
        metadata['status'] = 'finished' if code == 0 else 'stopped_by_guard_or_error'
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try: process.wait(timeout=12)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait()
        stop.set()
        if monitor is not None: monitor.join(timeout=10)
        cookie_file.unlink(missing_ok=True)
        private_json(work / 'resources.json', {'samples': samples})
        if account is not None:
            cleanup = docker_python(web, DELETE_ACCOUNT, account)
            metadata['account_cleanup'] = cleanup
            print('TEST_ACCOUNT_REMOVED' if cleanup.get('removed') else 'TEST_ACCOUNT_ALREADY_ABSENT', flush=True)
        private_json(work / 'setup.json', metadata)
        print('CAPACITY_REPORT_DIR=' + str(work), flush=True)
    return 0 if metadata.get('runner_exit_code') == 0 else 2


if __name__ == '__main__':
    raise SystemExit(main())
