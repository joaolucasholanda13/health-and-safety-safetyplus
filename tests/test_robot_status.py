import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from jinja2 import Environment, FileSystemLoader
from app import ti_tools
from tools import maintenance

ROOT=Path(__file__).resolve().parents[1]

class RobotStatusTests(unittest.TestCase):
    def test_disconnected_corrupt_and_stale_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'status.json'
            with patch.dict(os.environ,{'MAINTENANCE_STATUS_FILE':str(path)}):
                self.assertFalse(ti_tools.robot_status()['available'])
                path.write_text('broken')
                self.assertFalse(ti_tools.robot_status()['available'])
                path.write_text(json.dumps({'schema':1,'updated_at':time.time()-600,'monitor_timer_active':True}))
                self.assertEqual(ti_tools.robot_status()['label'],'Sem atualização recente')
                path.write_text(json.dumps({'schema':1,'updated_at':time.time(),'monitor_timer_active':False}))
                self.assertEqual(ti_tools.robot_status()['label'],'Agendamento desativado')
                path.write_text(json.dumps({'schema':1,'updated_at':time.time(),'monitor_timer_active':True}))
                self.assertEqual(ti_tools.robot_status()['label'],'Ativo')

    def test_public_report_excludes_private_state_and_partial_backups(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)
            maintenance.save_state(directory/'state.json',{'checked_at':time.time(),'checks':{'web_ok':True,'db_ok':True,'https_ok':False},'private_key':'secret'})
            for name in ['complete','incomplete.partial']:
                p=directory/'backups'/name;p.mkdir(parents=True)
                (p/'manifest.json').write_text(json.dumps({'created_at_utc':'2026-11-16','restore_tested':False,'private_key':'secret'}))
            with patch.object(maintenance.subprocess,'run') as run:
                run.return_value.returncode=0
                maintenance.publish_status(directory)
            path=directory/'public/status.json'
            report=json.loads(path.read_text())
            self.assertNotIn('secret',path.read_text())
            self.assertEqual(len(report['backups']),1)
            self.assertEqual(path.stat().st_mode & 0o777,0o644)
            template=Environment(loader=FileSystemLoader(str(ROOT/'app/templates')),autoescape=True).get_template('_robot_status.html')
            with patch.dict(os.environ,{'MAINTENANCE_STATUS_FILE':str(path)}):
                html=template.render(robot=ti_tools.robot_status())
            self.assertIn('Saudável',html)
            self.assertIn('Falha',html)
            self.assertIn('2026-11-16',html)
            self.assertIn('Não',html)
            self.assertIn('Não conectado',template.render(robot={'available':False,'label':'Não conectado'}))
