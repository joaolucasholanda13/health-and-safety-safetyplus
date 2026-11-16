"""Regressão: rubrica diária aberta a partir de um painel oculto."""
import ast
import base64
from pathlib import Path
import subprocess
import tempfile
import unittest
from datetime import datetime
import secrets
import fitz

ROOT = Path(__file__).resolve().parents[1]


class DailySignatureCaptureTests(unittest.TestCase):
    def test_hidden_canvas_is_initialized_when_opened_and_keeps_strokes(self):
        subprocess.run(['node', '-e', r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const html=fs.readFileSync(process.argv[1],'utf8');
const handlers={},ctx={setTransform(){},beginPath(){},moveTo(){},lineTo(){},stroke(){},clearRect(){}};
const area={style:{display:'none'},scrollIntoView(){}};
const canvas={width:300,height:150,get clientWidth(){return area.style.display==='none'?0:400},get clientHeight(){return area.style.display==='none'?0:180},getContext:()=>ctx,addEventListener:(n,f)=>handlers[n]=f,getBoundingClientRect:()=>({left:0,top:0}),setPointerCapture(){},toDataURL:()=>`image:${canvas.width}x${canvas.height}`};
const input={value:''},els={'daily-pad':canvas,'sig-daily':input,'minha-assinatura':area,'clear-daily':{addEventListener(){}},'daily-sign-form':{addEventListener(){}}};
const window={devicePixelRatio:2,addEventListener(){}};
vm.runInNewContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],{window,document:{getElementById:id=>els[id]},alert(){}});
window.abrirAssinaturaDia({preventDefault(){}});
assert.equal(canvas.width,800);assert.equal(canvas.height,360);
const e={clientX:40,clientY:20,pointerId:1,preventDefault(){}};
handlers.pointerdown(e);handlers.pointerup(e);assert.equal(input.value,'');
handlers.pointerdown(e);handlers.pointermove(e);handlers.pointerup(e);assert.equal(input.value,'image:800x360');
window.abrirAssinaturaDia({preventDefault(){}});assert.equal(input.value,'image:800x360');
''', str(ROOT / 'app/templates/apr_daily_signature.html')], check=True)

    def test_server_rejects_blank_images_and_accepts_ink(self):
        tree=ast.parse((ROOT/'app/main.py').read_text())
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='save_signature')
        with tempfile.TemporaryDirectory() as tmp:
            scope=dict(clean=lambda s:str(s or '').strip(),base64=base64,fitz=fitz,Path=Path,SIG_DIR=Path(tmp),safe_filename=lambda s:s,now=datetime.now,secrets=secrets)
            exec(compile(ast.Module(body=[node],type_ignores=[]),'save_signature','exec'),scope)
            save=scope['save_signature']
            def image(w,h,alpha,ink=False):
                pix=fitz.Pixmap(fitz.csRGB,fitz.IRect(0,0,w,h),alpha)
                pix.set_rect(pix.irect,(0,0,0,0) if alpha else (255,255,255))
                if ink: pix.set_pixel(2,2,(0,0,0,255) if alpha else (0,0,0))
                return 'data:image/png;base64,'+base64.b64encode(pix.tobytes('png')).decode()
            for value in [image(1,1,True),image(20,20,True),image(20,20,False)]:
                self.assertEqual(save(value),'')
            for alpha in [True,False]:
                self.assertTrue(save(image(20,20,alpha,True)))
            self.assertEqual(len(list(Path(tmp).glob('*.png'))),2)


if __name__=='__main__':
    unittest.main()
