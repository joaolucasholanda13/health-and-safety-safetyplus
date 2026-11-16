from datetime import date
from pathlib import Path
import tempfile
import unittest
import fitz
from app.rac_reports import adherence, plan_counts, append_actions
from app.pdfgen import generate_rac_original
from app.rac_pdf_layouts import RAC_PDF_LAYOUTS
from app.module_configs import RAC_MODULES

class RacReportTests(unittest.TestCase):
    def test_na_and_missing_are_not_falsely_approved(self):
        self.assertIsNone(adherence(['NA'] * 3)['score'])
        self.assertEqual(adherence(['ATENDE'], 3)['state'], 'Incompleta')
        self.assertEqual(adherence([], 3)['pending'], 3)
        self.assertEqual(adherence(['ATENDE','NAO_ATENDE','NA'])['score'], 50)

    def test_general_is_weighted_and_threshold_not_rounded(self):
        self.assertEqual(adherence(['ATENDE'] * 19 + ['NAO_ATENDE'])['score'], 95)
        self.assertEqual(adherence(['ATENDE'] * 18 + ['NAO_ATENDE'])['state'], 'Abaixo da meta')
        self.assertEqual(adherence(['SIM','NAO'])['score'], 50)

    def test_action_states_are_exclusive_and_completed_is_not_overdue(self):
        plans=[{'status':'Concluído','due_date':'01/01/2020'}, {'status':'Em andamento','due_date':'2026-11-01'}, {'status':'Em andamento','due_date':'2026-12-01'}, {}]
        counts=plan_counts(['NAO_ATENDE']*4, plans, date(2026,11,12))
        self.assertEqual(counts, dict(not_started=1,progress=1,complete=1,late=1,opened=3))

    def test_all_official_models_generate_consistent_summary(self):
        with tempfile.TemporaryDirectory() as folder:
            for kind in RAC_PDF_LAYOUTS:
                cfg=RAC_MODULES[kind]; count=sum(len(g['items']) for g in cfg['groups'])
                data=dict(code='RAC-TESTE',inspection_date='12/11/2026',answers=['NAO_ATENDE']+['ATENDE']*(count-1),action_plans=[dict(action='Corrigir com evidência verificável',responsible='João',due_date='10/11/2026')])
                path=Path(folder)/f'{kind}.pdf'
                generate_rac_original(kind,data,path)
                with fitz.open(path) as doc:
                    summary=doc[-2].get_text()
                    self.assertIn('Resultado consolidado',summary,kind)
                    self.assertIn('12/11/2026',summary)
                    self.assertNotIn('1899',summary)
                    self.assertIn('Corrigir com evidência verificável',doc[-1].get_text())
                    self.assertIn('Abaixo da meta',summary)

    def test_long_action_is_paginated_without_losing_end(self):
        doc=fitz.open()
        text=('Ação detalhada e verificável. ' * 700)+'FIM-DO-PLANO'
        append_actions(doc,dict(title='RAC de teste'),[dict(number='1.1',text='Requisito')],dict(answers=['NAO_ATENDE'],action_plans=[dict(action=text)]))
        self.assertGreater(len(doc),1)
        self.assertIn('FIM-DO-PLANO',''.join(p.get_text() for p in doc))

if __name__=='__main__': unittest.main()
