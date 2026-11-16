"""Executa os pads reais para conferir toque vazio, traço e limpeza."""
import subprocess
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HARNESS=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const html=fs.readFileSync(process.argv[1],'utf8'),kind=process.argv[2];
const begin=html.indexOf('  const pads = {};',html.indexOf('// ---- Assinatura'));
const stop=html.indexOf(kind==='vehicle'?'  function atualizarCaixaNc':'  function aplicarPermitParticipante',begin);
let script=html.slice(begin,stop<0?html.indexOf('</script>',begin):stop);
const handlers={},events={};let ink=false;
const ctx={scale(){},beginPath(){},moveTo(){},lineTo(){},stroke(){ink=true},clearRect(){ink=false}};
const canvas={id:'pad-0',clientWidth:400,clientHeight:180,getContext:()=>ctx,getBoundingClientRect:()=>({left:0,top:0}),addEventListener:(n,f)=>handlers[n]=f,toDataURL:()=>ink?'ink':'blank'};
const input={value:''},status={textContent:'',classList:{add(){},remove(){}}};
const env={window:{devicePixelRatio:2,addEventListener:(n,f)=>events[n]=f},document:{querySelectorAll:()=>[canvas],getElementById:id=>id.startsWith('sig-input')?input:status}};
vm.createContext(env);vm.runInContext(script,env);
const e={clientX:10,clientY:10,preventDefault(){}};
handlers.mousedown(e);events.mouseup();assert.equal(input.value,'');
handlers.mousedown(e);handlers.mousemove(e);events.mouseup();assert.equal(input.value,'ink');
env.limparAssinatura('0');assert.equal(input.value,'');
handlers.mousedown(e);events.mouseup();assert.equal(input.value,'');
handlers.mousedown(e);handlers.mousemove(e);events.mouseup();assert.equal(input.value,'ink');
'''
class SignaturePadStateTests(unittest.TestCase):
    def test_checklist_and_permit_pads(self):
        for name,kind in [('vehicle_form.html','vehicle'),('inspection_form.html','inspection'),('permit_form.html','permit')]:
            with self.subTest(name=name):
                subprocess.run(['node','-e',HARNESS,str(ROOT/'app/templates'/name),kind],check=True)

class RacResizeTests(unittest.TestCase):
    def test_resize_preserves_ink_and_updates_submitted_image(self):
        subprocess.run(['node','-e',r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const html=fs.readFileSync(process.argv[1],'utf8');
const start=html.indexOf("const canvas=document.getElementById('pad-responsible');");
const script=html.slice(start,html.indexOf('</script>',start));
const handlers={},events={};
function makeCanvas(){let ink=false,w=300,h=150;const ctx={setTransform(){},beginPath(){},moveTo(){},lineTo(){},stroke(){ink=true},clearRect(){ink=false},drawImage(src){ink=src.hasInk()}};return {get width(){return w},set width(v){w=v;ink=false},get height(){return h},set height(v){h=v;ink=false},clientWidth:400,clientHeight:180,hasInk:()=>ink,getContext:()=>ctx,getBoundingClientRect:()=>({left:0,top:0}),addEventListener:(n,f)=>handlers[n]=f,toDataURL:()=>`${ink?'ink':'blank'}:${w}x${h}`};}
const canvas=makeCanvas(),input={value:''},status={classList:{add(){},remove(){}}};
vm.runInNewContext(script,{window:{devicePixelRatio:2,addEventListener:(n,f)=>events[n]=f},document:{getElementById:id=>id==='pad-responsible'?canvas:id.startsWith('sig-input')?input:status,createElement:()=>makeCanvas()}});
const e={clientX:30,clientY:20,preventDefault(){}};
handlers.mousedown(e);events.mouseup();assert.equal(input.value,'');
handlers.mousedown(e);handlers.mousemove(e);events.mouseup();assert.equal(input.value,'ink:800x360');
canvas.clientWidth=250;events.resize();assert.equal(input.value,'ink:500x360');assert(canvas.hasInk());
''',str(ROOT/'app/templates/rac_form.html')],check=True)

if __name__=='__main__': unittest.main()
