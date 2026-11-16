"""PDFs reais com dados sintéticos e rubricas, sempre em arquivos temporários."""
from pathlib import Path
import tempfile
import unittest
import fitz
from app import pdfgen
from app.module_configs import MODULES, INSPECTION_MODULES, RAC_MODULES


class DocumentFixture(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='safety-module-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        pix=fitz.Pixmap(fitz.csRGB,fitz.IRect(0,0,100,40),False)
        pix.clear_with(255)
        pix.set_rect(fitz.IRect(10,10,80,15),(0,0,0))
        self.signature=self.root/'signature.png'
        pix.save(self.signature)

    def payload(self,kind):
        signature=str(self.signature)
        worker=dict(company='EMPRESA TESTE',worker='PARTICIPANTE TESTE',role='Técnico',
                    date='16/11/2026',signature_image=signature,
                    daily_signatures={'2026-11-16':dict(signature_image=signature,
                        signed_at='16/11/2026 10:00',signed_by_name='PARTICIPANTE TESTE')})
        cfg=INSPECTION_MODULES.get(kind,{})
        return dict(code='TESTE-ROBO-001',activity='ATIVIDADE TESTE ISOLADO',
                    apr_date='16/11/2026',inspection_date='16/11/2026',date='16/11/2026',
                    cluster='CLUSTER TESTE',site='LOCAL TESTE',local='LOCAL TESTE',
                    leader='RESPONSAVEL TESTE',responsible='RESPONSAVEL TESTE',
                    signature_image=signature,workers=[worker],
                    checklist=['SIM']*len(MODULES.get(kind,{}).get('checklist',[])),
                    approvals=[],answers=['C']*len(cfg.get('items',[])),
                    periods={p:dict(date='16/11/2026',answers=['C']*len(cfg.get('items',[])),
                        signature_image=signature) for p in cfg.get('periods',[])},
                    open_signature_image=signature,open_responsible_signature_image=signature,
                    close_signature_image=signature,vehicle='VEICULO TESTE',plate='ABC1D23',company='EMPRESA TESTE',
                    nonconformities=[dict(item='1',action='ACAO TESTE',responsible='RESPONSAVEL TESTE',date='16/11/2026')])

    def check_pdf(self,kind):
        output=self.root/(kind+'.pdf')
        pdfgen.generate_document(kind,self.payload(kind),output)
        self.assertGreater(output.stat().st_size,1000)
        with fitz.open(output) as document:
            text=''.join(page.get_text() for page in document)
            self.assertTrue(text.strip(),kind)
            if kind in ('apr','light_vehicle'):
                self.assertTrue(any(page.get_images() for page in document),kind)
            if kind=='light_vehicle':
                self.assertIn('Sábado',text)
                self.assertIn('Domingo',text)
                for value in ('VEICULO TESTE','ABC1D23','EMPRESA TESTE','ACAO TESTE'):
                    self.assertIn(value,text)
        with fitz.open(output) as doc:
            self.assertGreater(len(doc),0)
            self.assertIn('TESTE',''.join(page.get_text() for page in doc))
            self.assertTrue(all(not page.get_pixmap(matrix=fitz.Matrix(.25,.25)).is_monochrome for page in doc))
        return output


class AprDocumentTests(DocumentFixture):
    def test_apr_daily_signature_is_visible_in_pdf(self):
        output=self.check_pdf('apr')
        with fitz.open(output) as doc:
            daily=doc[-1]
            self.assertIn('ASSINATURAS DI',daily.get_text())
            self.assertIn('PARTICIPANTE TESTE',daily.get_text())
            self.assertTrue(daily.get_images(), 'Rubrica ausente da folha diária')


class PermitDocumentTests(DocumentFixture):
    pass


class ChecklistDocumentTests(DocumentFixture):
    pass


# Cada modelo aparece individualmente no relatório; não escondemos falhas num teste único.
def add_case(cls,kind):
    def case(self):self.check_pdf(kind)
    setattr(cls,'test_pdf_'+kind,case)

for kind in MODULES:add_case(PermitDocumentTests,kind)
for kind in ['vehicle',*INSPECTION_MODULES]:add_case(ChecklistDocumentTests,kind)
