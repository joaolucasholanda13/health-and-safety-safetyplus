"""Exercise the real viewer JavaScript with deterministic DOM/network events."""
from pathlib import Path
import shutil
import subprocess
import unittest


TEMPLATE = Path(__file__).resolve().parents[1] / 'app/templates/pdf_viewer.html'
HARNESS = r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const scenario=process.argv[2];
const source=fs.readFileSync(process.argv[1],'utf8');
const start=source.indexOf('(function(){\n  const rawUrl=');
const end=source.lastIndexOf('})();')+5;
assert(start>=0&&end>start);
const script=source.slice(start,end).replace('{{ raw_pdf_url|tojson }}',JSON.stringify('/document/1/pdf?raw=1'));
let imageMode=scenario==='imageError'?'error':scenario==='imageHang'?'hang':'success';
const timers=new Map();let nextTimer=1;
const images=[];
class Element {
 constructor(tag){this.tagName=tag.toUpperCase();this.children=[];this.hidden=false;this.style={};this.listeners={};this.clientWidth=1100;this.removed=false;this.className='';this.textContent='';
  this.classList={add:(c)=>{const list=new Set(this.className.split(' ').filter(Boolean));list.add(c);this.className=[...list].join(' ')},remove:(c)=>{this.className=this.className.split(' ').filter(x=>x!==c).join(' ')}};}
 appendChild(child){if(child.tagName==='FRAGMENT'){child.children.slice().forEach(x=>this.appendChild(x));return child;}this.children.push(child);child.parent=this;return child;}
 remove(){this.removed=true;if(this.parent)this.parent.children=this.parent.children.filter(x=>x!==this);}
 setAttribute(key,value){this[key]=value;}
 addEventListener(event,callback){this.listeners[event]=callback;}
 querySelectorAll(selector){const result=[];const visit=x=>{for(const child of x.children){if(selector==='.pdf-page-card'&&child.className.split(' ').includes('pdf-page-card'))result.push(child);visit(child);}};visit(this);return result;}
 set innerHTML(value){this.children=[];this._html=value;}
 set src(value){this._src=value;if(!images.includes(this))images.push(this);if(imageMode==='success')queueMicrotask(()=>this.onload&&this.onload());else if(imageMode==='error')queueMicrotask(()=>this.onerror&&this.onerror());}
 get src(){return this._src;}
}
const ids={pdfPages:new Element('div'),pdfLoading:new Element('div'),pdfStage:new Element('div'),pdfZoomTools:new Element('div'),pdfZoomValue:new Element('span'),pdfZoomOut:new Element('button'),pdfZoomIn:new Element('button')};
ids.pdfPages.hidden=true;ids.pdfZoomTools.hidden=true;
const document={getElementById:id=>ids[id],createElement:tag=>new Element(tag),createDocumentFragment:()=>new Element('fragment')};
const response={status:200,ok:true,redirected:false,url:'http://fixture/document/1/pdf',headers:{get:()=>scenario==='metaHtml'?'text/html':'application/json'},json:async()=>({pages:3})};
if(scenario==='unauthorized')Object.assign(response,{status:401,ok:false});
if(scenario==='forbidden')Object.assign(response,{status:403,ok:false});
if(scenario==='loginRedirect')Object.assign(response,{redirected:true,url:'http://fixture/login'});
const fetch=()=>scenario==='metaHang'?new Promise(()=>{}):Promise.resolve(response);
const context={document,fetch,URL,Promise,Map,Number,Error,Date,AbortController,console,queueMicrotask,
 setTimeout:(callback,ms)=>{const id=nextTimer++;timers.set(id,{callback,ms});return id;},clearTimeout:id=>timers.delete(id),
 window:{location:{origin:'http://fixture',reload:()=>{}},matchMedia:()=>({matches:false}),addEventListener:()=>{}}};
vm.runInNewContext(script,context);
async function flush(){for(let i=0;i<50;i++)await Promise.resolve();}
function advance(ms){for(const [id,timer] of [...timers])if(timer.ms<=ms){timers.delete(id);timer.callback();}}
function all(root){return [root,...root.children.flatMap(all)];}
function visibleText(){return all(ids.pdfPages).map(x=>x.textContent).join(' ');}
(async()=>{
 await flush();
 if(['unauthorized','forbidden','loginRedirect','metaHtml','metaHang'].includes(scenario)){
  if(scenario==='metaHang'){assert.equal(ids.pdfLoading.removed,false);advance(15000);await flush();}
  assert.equal(ids.pdfLoading.removed,true);assert.equal(ids.pdfPages.hidden,false);assert.equal(images.length,0);
  const text=visibleText();
  if(scenario==='forbidden')assert.match(text,/permissão/);
  if(scenario==='unauthorized'||scenario==='loginRedirect')assert.match(text,/sessão expirou/);
  if(scenario==='metaHtml')assert.match(text,/informações do PDF/);
  if(scenario==='metaHang')assert.match(text,/demorou/);
  assert.match(text,/Tentar novamente/);assert.match(text,/Voltar ao painel/);
 }else{
  if(scenario==='imageHang'){
   assert.equal(ids.pdfLoading.removed,false);assert.equal(ids.pdfPages.hidden,true);
   advance(20000);await flush();
  }
  assert.equal(ids.pdfLoading.removed,true);assert.equal(ids.pdfPages.hidden,false);
  assert.equal(ids.pdfZoomTools.hidden,false);assert.equal(images.length,3);
  const cards=ids.pdfPages.querySelectorAll('.pdf-page-card');assert.equal(cards.length,3);
  if(scenario==='imageError'||scenario==='imageHang'){
   const card=cards[0];assert.match(card.className,/pdf-page-load-error/);
   const retry=all(card).find(x=>x.tagName==='BUTTON');assert.equal(retry.hidden,false);
   assert.match(all(card).map(x=>x.textContent).join(' '),/Tente novamente|tente novamente/);
   imageMode='success';retry.listeners.click();await flush();
   assert.equal(images[0].hidden,false);assert(!card.className.includes('pdf-page-load-error'));
   assert(images[0].src.includes('preview_retry='));
  }else assert(images.every(image=>!image.hidden));
 }
 console.log('OK '+scenario);
})().catch(error=>{console.error(error);process.exitCode=1;});
"""


@unittest.skipUnless(shutil.which('node'), 'Node is needed for viewer JavaScript regression checks')
class PDFViewerTests(unittest.TestCase):
    def scenario(self, name):
        result = subprocess.run(['node', '-e', HARNESS, str(TEMPLATE), name],
                                text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_loaded_images_are_displayed(self):
        self.scenario('success')

    def test_image_error_has_message_and_working_retry(self):
        self.scenario('imageError')

    def test_image_timeout_keeps_loader_until_failure_and_can_retry(self):
        self.scenario('imageHang')

    def test_metadata_timeout_has_recovery_actions(self):
        self.scenario('metaHang')

    def test_html_instead_of_metadata_has_clear_error(self):
        self.scenario('metaHtml')

    def test_unauthenticated_response_explains_expired_session(self):
        self.scenario('unauthorized')

    def test_login_redirect_explains_expired_session(self):
        self.scenario('loginRedirect')

    def test_forbidden_response_explains_permission(self):
        self.scenario('forbidden')


if __name__ == '__main__':
    unittest.main()
