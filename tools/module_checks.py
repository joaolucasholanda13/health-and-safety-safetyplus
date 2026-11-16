"""Executa testes sintéticos em subprocessos, sem usar dados do ambiente atual."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
GROUPS={
    'apr':['tests.test_module_documents.AprDocumentTests','tests.test_apr_signature_accounts','tests.test_apr_execution_member'],
    'pts':['tests.test_module_documents.PermitDocumentTests'],
    'checklists':['tests.test_module_documents.ChecklistDocumentTests','tests.test_finalize_access'],
    'racs':['tests.test_rac_reports'],
}


def worker(group):
    # Sobrescreve configurações ANTES de importar qualquer módulo do sistema.
    with tempfile.TemporaryDirectory(prefix='safety-checks-') as tmp:
        os.environ.update(DATABASE_URL='sqlite:///'+tmp+'/test.db',STORAGE_DIR=tmp,
                          APP_SECRET='isolated-module-check-secret',SECURE_COOKIES='false',
                          ADMIN_USER='module-test-admin',ADMIN_PASSWORD='module-test-only-password',
                          DOMAIN='example.invalid',PYTHONDONTWRITEBYTECODE='1')
        sys.path.insert(0,str(ROOT))
        suite=unittest.defaultTestLoader.loadTestsFromNames(GROUPS[group])
        result=unittest.TextTestRunner(stream=sys.stderr,verbosity=2).run(suite)
        report=dict(group=group,passed=result.wasSuccessful(),tests=result.testsRun,
                    failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped))
        print(json.dumps(report),flush=True)
        return 0 if report['passed'] and report['tests']>0 else 1


def local_checks():
    reports=[]
    for group in GROUPS:
        started=time.time()
        try:
            result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',group],
                                  cwd=ROOT,text=True,capture_output=True,timeout=600)
            sys.stderr.write(result.stderr)
            report=json.loads(result.stdout.strip().splitlines()[-1])
            report['passed']=result.returncode==0 and report.get('passed') is True
        except (subprocess.SubprocessError,ValueError,IndexError,OSError) as error:
            report=dict(group=group,passed=False,error=type(error).__name__)
        report['duration_seconds']=round(time.time()-started,1)
        reports.append(report)
    return reports


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--worker',choices=list(GROUPS))
    args=parser.parse_args()
    if args.worker:raise SystemExit(worker(args.worker))
    reports=local_checks()
    print(json.dumps({'groups':reports,'passed':all(r['passed'] for r in reports)},ensure_ascii=False))
    raise SystemExit(0 if all(r['passed'] for r in reports) else 1)
