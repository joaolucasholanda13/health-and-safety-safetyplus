import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from tools import maintenance as m

class MaintenanceTests(unittest.TestCase):
    def test_recovery_limits(self):
        state={}
        self.assertFalse(m.recovery(state,False,True,10000,True))
        self.assertFalse(m.recovery(state,False,True,10000,True))
        self.assertTrue(m.recovery(state,False,True,10000,True))
        self.assertFalse(m.recovery(state,False,False,10000,True))
        self.assertFalse(m.recovery(state,False,True,10000,False))
        state['last_restart']=9999
        self.assertFalse(m.recovery(state,False,True,10000,True))
        m.recovery(state,True,True,10000,True)
        self.assertEqual(state['failures'],0)

    def test_failed_restart_persists_cooldown(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            m.save_state(p/'state.json',{'failures':2})
            with patch.object(m,'healthy',side_effect=[True,False]), patch.object(m,'run',side_effect=subprocess.TimeoutExpired('docker',90)), patch.dict(m.os.environ,{'MAINTENANCE_AUTO_RESTART':'1','MAINTENANCE_HEALTH_URL':''}):
                with self.assertRaises(subprocess.TimeoutExpired):m.monitor(p,p)
            state=json.loads((p/'state.json').read_text())
            self.assertFalse(m.recovery(state,False,True,state['last_restart']+60,True))

    def test_backup_failure_never_publishes_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            with patch.object(m,'run',side_effect=subprocess.CalledProcessError(1,'docker')),patch.object(m.shutil,'disk_usage',return_value=type('Disk',(),{'free':10*1024**3})()):
                with self.assertRaises(subprocess.CalledProcessError):m.backup(p,p)
            items=list((p/'backups').iterdir())
            self.assertTrue(items[0].name.endswith('.partial'))
            self.assertFalse((items[0]/'manifest.json').exists())

    def test_backup_validates_both_archives(self):
        calls=[]
        def fake(root,args,**kw):
            calls.append(args)
            if any('pg_dump' in a for a in args):kw['stdout'].write(b'dump fixture')
            elif 'tar' in args:
                with tarfile.open(fileobj=kw['stdout'],mode='w:gz') as t:
                    data=b'signature';entry=tarfile.TarInfo('storage/signatures/example.png');entry.size=len(data)
                    t.addfile(entry,io.BytesIO(data))
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            with patch.object(m,'run',side_effect=fake),patch.object(m.shutil,'disk_usage',return_value=type('Disk',(),{'free':10*1024**3})()):m.backup(p,p)
            items=list((p/'backups').iterdir())
            self.assertFalse(items[0].name.endswith('.partial'))
            manifest=json.loads((items[0]/'manifest.json').read_text())
            self.assertEqual(manifest['storage_entries'],1)
            self.assertFalse(manifest['restore_tested'])
            self.assertTrue(any(any('pg_restore' in a for a in args) for args in calls))

class ModuleTestIsolationTests(unittest.TestCase):
    def test_containers_are_isolated_and_failure_is_reported(self):
        calls=[]
        def docker(command,**kwargs):
            calls.append(command)
            if command[:2]==['docker','rm']:
                return subprocess.CompletedProcess(command,0)
            group=command[-1]
            return subprocess.CompletedProcess(command,1 if group=='pts' else 0,
                stdout=json.dumps(dict(group=group,passed=group!='pts',tests=2,failures=int(group=='pts'),errors=0,skipped=0)),stderr='fixture log')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch.object(m,'run',return_value=subprocess.CompletedProcess([],0,stdout='image-id')),patch.object(m.subprocess,'run',side_effect=docker):
                self.assertEqual(m.module_tests(root,root),1)
            report=json.loads((root/'module-tests.json').read_text())
            self.assertFalse(report['passed'])
            self.assertEqual(len(report['groups']),4)
            runs=[c for c in calls if c[:2]==['docker','run']]
            self.assertEqual(len(runs),4)
            for command in runs:
                self.assertIn('--read-only',command)
                self.assertEqual(command[command.index('--network')+1],'none')
                mounts=[c for c in command if 'type=bind' in c]
                self.assertEqual(len(mounts),3)
                self.assertTrue(all(c.endswith(',readonly') for c in mounts))
                self.assertFalse(any('storage' in c or '.env' in c or 'docker.sock' in c for c in mounts))
