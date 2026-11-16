/* Rubrica nítida: resolução mínima 3x e traço suavizado (curvas) em todos os campos de assinatura. */
(function(){
  try{
    var base=window.devicePixelRatio||1;
    Object.defineProperty(window,'devicePixelRatio',{configurable:true,get:function(){return Math.max(3,base);}});
  }catch(e){}
  var P=window.CanvasRenderingContext2D&&CanvasRenderingContext2D.prototype; if(!P) return;
  var last=new WeakMap(), mv=P.moveTo, ln=P.lineTo, bp=P.beginPath;
  P.beginPath=function(){last.delete(this);return bp.call(this);};
  P.moveTo=function(x,y){last.set(this,{x:x,y:y});return mv.call(this,x,y);};
  P.lineTo=function(x,y){
    var l=last.get(this);
    if(!l){last.set(this,{x:x,y:y});return ln.call(this,x,y);}
    var mx=(l.x+x)/2,my=(l.y+y)/2;
    this.quadraticCurveTo(l.x,l.y,mx,my);
    last.set(this,{x:x,y:y});
    return undefined;
  };
})();

/* Voltar do navegador/bfcache não pode reaproveitar respostas e rubrica de um checklist anterior. */
window.addEventListener('pageshow',function(e){
  try{ if(e.persisted && document.querySelector('#inspection-form,#vehicle-form')) location.reload(); }catch(x){}
});
