/* Safety Plus — rascunho automático no aparelho (V36.18.95)
   Guarda o preenchimento a cada alteração. Nunca significa documento enviado ou finalizado. */
(function () {
  'use strict';
  var supported = /^\/(apr\/new|apr\/\d+\/edit|vehicle\/(new|\d+\/edit)|permit\/[^/]+\/(new|\d+\/edit)|rac\/[^/]+\/(new|\d+\/edit)|inspection\/[^/]+\/(new|\d+\/edit))$/.test(location.pathname);
  if (!supported || !('indexedDB' in window)) return;
  var DB = 'safetyplus-browser-drafts-v1', STORE = 'drafts', timer = null, saving = false;
  var SKIP = /password|token|csrf|secret/i;
  function open() { return new Promise(function (res, rej) { var r = indexedDB.open(DB, 1); r.onupgradeneeded = function () { r.result.createObjectStore(STORE, { keyPath: 'id' }); }; r.onsuccess = function () { res(r.result); }; r.onerror = function () { rej(r.error); }; }); }
  function op(mode, method, value) { return open().then(function (db) { return new Promise(function (resolve, reject) { var tx = db.transaction(STORE, mode), r = tx.objectStore(STORE)[method](value); r.onsuccess = function () { resolve(r.result); }; r.onerror = function () { reject(r.error); }; tx.oncomplete = function () { db.close(); }; tx.onabort = function () { db.close(); }; }); }); }
  var id = location.pathname;
  // Atenção: form.action é sombreado pelo campo oculto name="action"; por isso lemos o atributo.
  function formPath(f) { try { return new URL(f.getAttribute('action') || location.pathname, location.origin).pathname; } catch (e) { return ''; } }
  var form = Array.prototype.find.call(document.forms, function (f) { var p = formPath(f); return String(f.getAttribute('method') || '').toLowerCase() === 'post' && /^\/(apr|vehicle|permit|rac|inspection)\//.test(p) && /\/save$/.test(p); });
  if (!form) return;

  var bar = document.createElement('div');
  bar.style.cssText = 'display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:0 0 14px;padding:10px 14px;border-radius:12px;background:#fff;border:1px solid #ECE8E3;font:13px/1.4 Poppins,system-ui,sans-serif;color:#4B4B4B';
  var dot = document.createElement('span'); dot.style.cssText = 'width:8px;height:8px;border-radius:50%;background:#858585;flex:0 0 8px';
  var note = document.createElement('span'); note.setAttribute('role', 'status'); note.style.flex = '1';
  var btn = document.createElement('button'); btn.type = 'button'; btn.hidden = true; btn.textContent = 'Restaurar rascunho do aparelho';
  btn.style.cssText = 'background:#181818;color:#fff;border:0;border-radius:999px;padding:8px 14px;cursor:pointer;font:600 12px Poppins,system-ui,sans-serif';
  bar.append(dot, note, btn); form.parentNode.insertBefore(bar, form);
  function say(text, color) { note.textContent = text; dot.style.background = color || '#858585'; }

  function collect() { var fd = new FormData(form), values = []; fd.forEach(function (v, k) { if (SKIP.test(k) || k === 'action') return; values.push([k, v]); }); return values; }
  function save() {
    if (saving) return Promise.resolve(); saving = true;
    return op('readwrite', 'put', { id: id, values: collect(), at: new Date().toISOString() })
      .then(function () { say('Rascunho salvo neste aparelho às ' + new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }) + '. Para valer, salve/envie o formulário.', '#32CAA0'); btn.hidden = false; })
      .catch(function () { say('Não foi possível salvar no aparelho. Verifique o espaço disponível.', '#D23532'); })
      .then(function () { saving = false; });
  }
  function schedule() { clearTimeout(timer); timer = setTimeout(save, 1200); }
  form.addEventListener('input', schedule); form.addEventListener('change', schedule);
  window.addEventListener('pagehide', function () { save(); });

  btn.addEventListener('click', function () {
    op('readonly', 'get', id).then(function (d) {
      if (!d) return;
      if (!confirm('Restaurar o rascunho guardado neste aparelho? Os campos atuais podem ser substituídos.')) return;
      var grouped = {}; d.values.forEach(function (p) { (grouped[p[0]] || (grouped[p[0]] = [])).push(p[1]); });
      var used = {};
      Array.prototype.forEach.call(form.elements, function (el) {
        if (!el.name || !grouped[el.name] || el.type === 'file' || SKIP.test(el.name) || el.name === 'action') return;
        var vals = grouped[el.name];
        if (el.type === 'checkbox' || el.type === 'radio') el.checked = vals.some(function (v) { return v === el.value; });
        else if (el.tagName === 'SELECT' && el.multiple) Array.prototype.forEach.call(el.options, function (o) { o.selected = vals.indexOf(o.value) >= 0; });
        else { var i = used[el.name] || 0; if (typeof vals[i] === 'string') el.value = vals[i]; used[el.name] = i + 1; }
        el.dispatchEvent(new Event('change', { bubbles: true }));
      });
      // Respostas Sim/Não/N/A ficam em campos ocultos: atualiza também os botões.
      Object.keys(grouped).forEach(function (k) {
        var m = /^check_(\d+)$/.exec(k);
        if (m && typeof window.setChecklist === 'function' && grouped[k][0]) { try { window.setChecklist(Number(m[1]), grouped[k][0]); } catch (e) {} }
      });
      if (grouped.critical_activity && typeof window.setCriticalActivity === 'function') { try { window.setCriticalActivity(grouped.critical_activity[0]); } catch (e) {} }
      if (typeof window.enhanceSelects === 'function') { try { document.querySelectorAll('select.campo').forEach(function (s) { s.dispatchEvent(new Event('change')); }); } catch (e) {} }
      say('Rascunho restaurado. Fotos precisam ser anexadas de novo; rubricas já feitas foram mantidas. Confira antes de enviar.', '#FFD964');
    });
  });
  op('readonly', 'get', id).then(function (d) {
    if (d) { btn.hidden = false; say('Há um rascunho deste formulário guardado no aparelho (' + new Date(d.at).toLocaleString('pt-BR') + ').', '#FFD964'); }
    else say('O preenchimento é guardado automaticamente neste aparelho enquanto você digita.', '#858585');
  }).catch(function () {});
})();
