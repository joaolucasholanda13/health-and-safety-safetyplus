/* Safety Plus — APR offline com assinatura manual e aprovação manual (V36.18.98)
   Sem internet: APR + PTs + rubrica e CPF de cada integrante + rubrica e senha do líder,
   tudo no mesmo aparelho. O pacote vai para a fila e o servidor confere CPF e senha no envio. */
(function () {
  'use strict';
  var OB = window.SafetyPlusOutbox; if (!OB) return;
  var KIND = { 'Trabalho em Altura': 'pt_height', 'Espaço Confinado': 'confined', 'Intervenção Elétrica': 'electrical', 'Linha Viva': 'line_live', 'Supressão de Vegetação': 'vegetation', 'Içamento de Carga': 'lifting', 'PT — TME': 'tme' };
  var DB = 'safetyplus-apr-bundles', STORE = 'pts';
  function idb(mode, fn) {
    return new Promise(function (res, rej) {
      var r = indexedDB.open(DB, 1);
      r.onupgradeneeded = function () { r.result.createObjectStore(STORE, { keyPath: 'key' }); };
      r.onsuccess = function () { var db = r.result, tx = db.transaction(STORE, mode), out = fn(tx.objectStore(STORE)); tx.oncomplete = function () { db.close(); res(out && 'result' in out ? out.result : undefined); }; tx.onerror = function () { db.close(); rej(tx.error); }; };
      r.onerror = function () { rej(r.error); };
    });
  }
  var putPT = function (rec) { return idb('readwrite', function (s) { return s.put(rec); }); };
  var allPT = function () { return idb('readonly', function (s) { return s.getAll(); }); };
  var delPT = function (key) { return idb('readwrite', function (s) { return s.delete(key); }); };
  function isOffline() { return window.SafetyPlusOffline ? window.SafetyPlusOffline.reachable(2500).then(function (ok) { return !ok; }) : Promise.resolve(!navigator.onLine); }
  var esc = function (v) { return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); };

  function css() {
    if (document.getElementById('sp-oa-css')) return;
    var s = document.createElement('style'); s.id = 'sp-oa-css';
    s.textContent = '.oa-back{position:fixed;top:0;left:0;width:100vw;height:100vh;height:100dvh;background:rgba(24,24,24,.55);z-index:100001;display:flex;align-items:stretch;justify-content:center;padding:18px;box-sizing:border-box}' +
      '.oa-sheet{background:#fff;border-radius:20px;width:min(860px,100%);max-height:100%;min-width:0;box-sizing:border-box;display:flex;flex-direction:column;overflow:hidden;font-family:Poppins,system-ui,sans-serif;color:#181818}' +
      '.oa-head{padding:18px 22px;border-bottom:1px solid #ECE8E3;display:flex;justify-content:space-between;gap:12px;align-items:flex-start}.oa-head h3{margin:0;font-family:Serena,Poppins,sans-serif;font-size:1.25rem}.oa-head p{margin:4px 0 0;font-size:.82rem;color:#4B4B4B}' +
      '.oa-steps{display:flex;gap:6px;padding:12px 22px;border-bottom:1px solid #F0ECE7;flex-wrap:wrap}.oa-steps span{font-size:.76rem;border-radius:999px;padding:5px 11px;background:#EDE9E5;color:#4B4B4B}.oa-steps span.on{background:#181818;color:#fff}.oa-steps span.done{background:#DDF5EE;color:#157357}' +
      '.oa-body{padding:18px 22px;overflow-y:auto;flex:1;min-height:0}.oa-foot{padding:14px 22px;border-top:1px solid #ECE8E3;display:flex;justify-content:space-between;gap:10px;background:#FBFAF8;flex-wrap:wrap}' +
      '.oa-btn{border:0;border-radius:999px;padding:11px 20px;font:600 .88rem Poppins,system-ui,sans-serif;cursor:pointer}.oa-dark{background:#181818;color:#fff}.oa-coral{background:#FF5246;color:#fff}.oa-ghost{background:#fff;border:1px solid #DCD7D1;color:#181818}.oa-btn:disabled{opacity:.45;cursor:not-allowed}' +
      '.oa-card{border:1px solid #ECE8E3;border-radius:16px;padding:14px 16px;margin-bottom:12px}.oa-card h4{margin:0 0 2px;font-size:.95rem}.oa-card small{color:#858585;font-size:.76rem}' +
      '.oa-row{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}' +
      '.oa-tag{font-size:.72rem;font-weight:600;border-radius:999px;padding:3px 10px}.oa-ok{background:#DDF5EE;color:#157357}.oa-pend{background:#FFF6D8;color:#7A5B00}' +
      '.oa-pad{width:100%;max-width:100%;box-sizing:border-box;height:150px;border:1px dashed #CFC9C2;border-radius:12px;background:#FBFAF8;touch-action:none;display:block;margin-top:8px}' +
      '.oa-field{display:flex;flex-direction:column;gap:5px;margin-top:10px;font-size:.8rem;font-weight:600}.oa-field input{box-sizing:border-box;width:100%;max-width:100%;border:1px solid #DCD7D1;border-radius:10px;padding:10px 12px;font:16px Poppins,system-ui,sans-serif}' +
      '.oa-note{font-size:.8rem;border-radius:12px;padding:10px 12px;background:#EDE9E5;color:#4B4B4B;margin-bottom:12px;line-height:1.45}.oa-err{color:#D23532;font-size:.8rem;margin-top:6px}' +
      '.oa-frame{position:fixed;inset:0;z-index:100002;background:#fff;display:flex;flex-direction:column}.oa-frame header{padding:10px 14px;background:#181818;color:#fff;display:flex;justify-content:space-between;align-items:center;font:600 .9rem Poppins,system-ui,sans-serif}.oa-frame iframe{flex:1;border:0;width:100%}' +
      '.oa-offbar{display:flex;gap:12px;align-items:center;justify-content:space-between;flex-wrap:wrap;margin:14px 0;padding:14px 16px;border-radius:14px;background:#181818;color:#fff;font:14px/1.45 Poppins,system-ui,sans-serif}.oa-offbar b{display:block}' +
      '@media(max-width:640px){.oa-back{padding:0}.oa-sheet{border-radius:0}}';
    document.head.appendChild(s);
  }
  function pad(canvas) {
    var ctx = canvas.getContext('2d'), drawing = false, ink = false;
    function size() { var r = canvas.getBoundingClientRect(); canvas.width = r.width * 2; canvas.height = r.height * 2; ctx.scale(2, 2); ctx.lineWidth = 2.2; ctx.lineCap = 'round'; ctx.strokeStyle = '#181818'; }
    setTimeout(size, 30);
    function pos(e) { var r = canvas.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; }
    canvas.addEventListener('pointerdown', function (e) { drawing = true; canvas.setPointerCapture(e.pointerId); var p = pos(e); ctx.beginPath(); ctx.moveTo(p[0], p[1]); });
    canvas.addEventListener('pointermove', function (e) { if (!drawing) return; var p = pos(e); ctx.lineTo(p[0], p[1]); ctx.stroke(); ink = true; });
    ['pointerup', 'pointercancel', 'pointerleave'].forEach(function (ev) { canvas.addEventListener(ev, function () { drawing = false; }); });
    return { clear: function () { ctx.clearRect(0, 0, canvas.width, canvas.height); ink = false; drawing = false; }, has: function () { return ink; }, data: function () { return ink ? canvas.toDataURL('image/png') : ''; } };
  }
  function cpfOk(c) { c = String(c || '').replace(/\D/g, ''); if (!/^\d{11}$/.test(c) || /^(\d)\1{10}$/.test(c)) return false; for (var n = 9; n <= 10; n++) { var s = 0; for (var i = 0; i < n; i++) s += +c[i] * ((n + 1) - i); var d = (s * 10) % 11; if (d === 10) d = 0; if (d !== +c[n]) return false; } return true; }

  // =================== Página da PT aberta dentro do pacote offline ===================
  var params = new URLSearchParams(location.search);
  if (params.get('offline_bundle') && /^\/permit\/[^/]+\/new$/.test(location.pathname)) {
    var bundle = params.get('offline_bundle'), permit = params.get('permit') || '';
    document.addEventListener('DOMContentLoaded', function () {
      css();
      var form = document.getElementById('permit-form'); if (!form) return;
      form.noValidate = true; // a validação é feita abaixo (campos de assinatura ficam ocultos neste modo)
      var bar = document.createElement('div'); bar.className = 'oa-offbar';
      bar.innerHTML = '<div><b>PT da APR offline: ' + esc(permit) + '</b>Preencha e toque em “Salvar nesta APR”. As assinaturas são feitas no final, na própria APR.</div>';
      form.parentNode.insertBefore(bar, form);
      var foot = form.querySelector('.form-footer');
      if (foot) foot.innerHTML = '<button type="submit" class="btn btn-primario">Salvar nesta APR</button>';
      form.querySelectorAll('.sig-pad-wrap').forEach(function (el) { el.style.display = 'none'; });
    });
    document.addEventListener('submit', function (ev) {
      var form = ev.target; if (!form || form.id !== 'permit-form') return;
      ev.preventDefault(); ev.stopImmediatePropagation(); 
      var checks = Array.prototype.map.call(form.querySelectorAll('input[id^="check-"]'), function (i) { return i.value; });
      var nao = checks.map(function (v, i) { return v === 'NÃO' ? i + 1 : 0; }).filter(Boolean), blank = checks.map(function (v, i) { return v ? 0 : i + 1; }).filter(Boolean);
      var act = form.querySelector('[name=activity]');
      if (nao.length) { alert('Há resposta NÃO nos itens ' + nao.join(', ') + '. Condição impeditiva: a PT não pode seguir.'); return; }
      if (blank.length) { alert('Responda todos os itens do checklist. Faltam: ' + blank.join(', ') + '.'); return; }
      if (act && !act.value.trim()) { alert('Descreva a atividade da PT.'); act.focus(); return; }
      var entries = []; new FormData(form).forEach(function (v, k) { if (k !== 'csrf_token' && k !== 'action') entries.push([k, v]); });
      putPT({ key: bundle + '|' + permit, bundle: bundle, permit: permit, entries: entries, at: new Date().toISOString() }).then(function () {
        if (window.parent !== window) window.parent.postMessage({ type: 'sp-oa-pt-saved', permit: permit }, location.origin);
        else alert('PT guardada nesta APR. Volte para a APR para concluir.');
      }).catch(function (e) { console.log('SP-OA-ERR '+(e && e.message || e)); alert('Não foi possível guardar a PT no aparelho: ' + (e && e.message || e)); });
    }, true);
    return;
  }

  // =================== Página da APR ===================
  if (!/^\/apr\/(new|\d+\/edit)$/.test(location.pathname)) return;
  var bundleId = 'apr-' + location.pathname + '-' + ((window.SafetyPlusOffline && window.SafetyPlusOffline.instance) || Date.now());
  var aprForm = null;

  function workerRows() {
    return Array.prototype.map.call(document.querySelectorAll('[data-worker-row]'), function (row, i) {
      var pid = row.querySelector('.w-participant-id'), name = row.querySelector('.w-nome'), comp = row.querySelector('.w-empresa');
      var idx = (pid && pid.name.match(/worker_(\d+)_/) || [])[1];
      return { index: idx != null ? +idx : i, pid: pid ? pid.value : '', name: name ? name.value : '', company: comp ? comp.value : '' };
    }).filter(function (w) { return w.pid; });
  }
  function selectedPermits() {
    var crit = document.getElementById('critical_activity');
    if (!crit || crit.value !== 'SIM') return [];
    return Array.prototype.filter.call(document.querySelectorAll('input[name=critical_permits]'), function (i) { return i.checked; }).map(function (i) { return i.value; });
  }
  function preCheck() {
    var errs = [];
    var get = function (n) { var el = aprForm.querySelector('[name="' + n + '"]'); return el ? el.value.trim() : ''; };
    if (!get('cluster')) errs.push('Selecione o Cluster / Site.');
    if (!get('activity')) errs.push('Informe a atividade.');
    var checks = Array.prototype.map.call(aprForm.querySelectorAll('input[id^="check-"]'), function (i) { return i.value; });
    var nao = checks.filter(function (v) { return v === 'NÃO'; }).length, blank = checks.filter(function (v) { return !v; }).length;
    if (nao) errs.push('Há resposta NÃO no checklist: a APR não pode avançar.');
    if (blank) errs.push('Responda todos os itens do checklist (' + blank + ' sem resposta).');
    if (!get('approver_user_id')) errs.push('Escolha o líder ou responsável pela aprovação.');
    if (!workerRows().length) errs.push('Inclua pelo menos um integrante (busque pelo nome).');
    var crit = document.getElementById('critical_activity');
    if (crit && crit.value === 'SIM' && !selectedPermits().length) errs.push('Atividade crítica: marque as PTs necessárias.');
    return errs;
  }

  function openWizard() {
    css(); aprForm = document.getElementById('apr-form');
    var errs = preCheck();
    if (errs.length) { alert('Antes de concluir offline:\n\n• ' + errs.join('\n• ')); return; }
    var permits = selectedPermits(), workers = workerRows();
    var leaderSel = document.getElementById('approver_user_id');
    var leaderName = leaderSel && leaderSel.selectedOptions[0] ? leaderSel.selectedOptions[0].textContent.trim() : 'Líder';
    var steps = (permits.length ? ['PTs'] : []).concat(['Equipe', 'Líder', 'Concluir']);
    var step = 0, pads = {}, leaderPad = null, saved = {};
    var back = document.createElement('div'); back.className = 'oa-back';
    back.innerHTML = '<div class="oa-sheet" role="dialog" aria-modal="true"><div class="oa-head"><div><h3>Concluir APR sem internet</h3><p>Assinatura manual da equipe e aprovação manual do líder neste aparelho. O servidor confere CPF e senha quando a internet voltar.</p></div><button type="button" class="oa-btn oa-ghost" data-x>Fechar</button></div><div class="oa-steps"></div><div class="oa-body"></div><div class="oa-foot"><button type="button" class="oa-btn oa-ghost" data-prev>Voltar</button><button type="button" class="oa-btn oa-dark" data-next>Continuar</button></div></div>';
    document.body.appendChild(back); document.body.style.overflow = 'hidden';
    var body = back.querySelector('.oa-body'), stepsEl = back.querySelector('.oa-steps'), next = back.querySelector('[data-next]'), prev = back.querySelector('[data-prev]');
    function close() { back.remove(); document.body.style.overflow = ''; window.removeEventListener('message', onMsg); }
    back.querySelector('[data-x]').onclick = close;
    function onMsg(e) { if (e.origin === location.origin && e.data && e.data.type === 'sp-oa-pt-saved') { var f = document.querySelector('.oa-frame'); if (f) f.remove(); refreshPTs().then(render); } }
    window.addEventListener('message', onMsg);
    function refreshPTs() { return allPT().then(function (list) { saved = {}; (list || []).forEach(function (r) { if (r.bundle === bundleId) saved[r.permit] = r; }); }); }
    function render() {
      stepsEl.innerHTML = steps.map(function (s, i) { return '<span class="' + (i === step ? 'on' : (i < step ? 'done' : '')) + '">' + (i + 1) + '. ' + s + '</span>'; }).join('');
      prev.style.visibility = step ? 'visible' : 'hidden';
      var name = steps[step];
      if (name === 'PTs') {
        body.innerHTML = '<div class="oa-note">Atividade crítica: preencha cada PT abaixo. Elas ficam guardadas junto desta APR.</div>' + permits.map(function (p) {
          var ok = !!saved[p];
          return '<div class="oa-card oa-row"><div><h4>' + esc(p) + '</h4><small>' + (ok ? 'Preenchida em ' + new Date(saved[p].at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }) : 'Ainda não preenchida') + '</small></div><div style="display:flex;gap:8px;align-items:center"><span class="oa-tag ' + (ok ? 'oa-ok' : 'oa-pend') + '">' + (ok ? 'Pronta' : 'Pendente') + '</span><button type="button" class="oa-btn ' + (ok ? 'oa-ghost' : 'oa-coral') + '" data-pt="' + esc(p) + '">' + (ok ? 'Revisar' : 'Preencher') + '</button></div></div>';
        }).join('');
        body.querySelectorAll('[data-pt]').forEach(function (b) { b.onclick = function () { openPT(b.dataset.pt); }; });
        next.textContent = 'Continuar'; next.disabled = permits.some(function (p) { return !saved[p]; });
      } else if (name === 'Equipe') {
        body.innerHTML = '<div class="oa-note">Cada integrante assina com o dedo e digita o próprio CPF. Passe o aparelho para a pessoa.</div>' + workers.map(function (w) {
          return '<div class="oa-card" data-w="' + w.index + '"><div class="oa-row"><div><h4>' + esc(w.name) + '</h4><small>' + esc(w.company) + '</small></div><button type="button" class="oa-btn oa-ghost" data-clear>Limpar rubrica</button></div><canvas class="oa-pad"></canvas><label class="oa-field">CPF do integrante<input inputmode="numeric" maxlength="14" placeholder="000.000.000-00" data-cpf></label><div class="oa-err" hidden></div></div>';
        }).join('');
        body.querySelectorAll('[data-w]').forEach(function (card) {
          var i = card.dataset.w, p = pad(card.querySelector('canvas')); pads[i] = p; card.querySelector('[data-clear]').onclick = p.clear;
          var inp = card.querySelector('[data-cpf]'); inp.addEventListener('input', function () { var d = inp.value.replace(/\D/g, '').slice(0, 11); inp.value = d.replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d{1,2})$/, '$1-$2'); });
        });
        next.textContent = 'Continuar'; next.disabled = false;
      } else if (name === 'Líder') {
        body.innerHTML = '<div class="oa-note">Aprovação manual de <b>' + esc(leaderName) + '</b>. O líder confere a APR' + (permits.length ? ' e as PTs' : '') + ', assina e digita a senha do Safety Plus. A senha é conferida pelo servidor no envio; se não conferir, a APR vai para a aprovação online.</div>' +
          '<div class="oa-card"><div class="oa-row"><div><h4>' + esc(leaderName) + '</h4><small>Líder ou responsável pela atividade</small></div><button type="button" class="oa-btn oa-ghost" data-clear>Limpar rubrica</button></div><canvas class="oa-pad"></canvas>' +
          '<label class="oa-field">Senha do líder no Safety Plus<input type="password" autocomplete="off" data-pass></label>' +
          '<label style="display:flex;gap:8px;align-items:flex-start;margin-top:12px;font-size:.84rem"><input type="checkbox" data-decl style="margin-top:3px"> Declaro que revisei a APR' + (permits.length ? ' e as PTs' : '') + ' com a equipe e aprovo a execução da atividade.</label><div class="oa-err" hidden></div></div>';
        leaderPad = pad(body.querySelector('canvas')); body.querySelector('[data-clear]').onclick = leaderPad.clear;
        next.textContent = 'Continuar'; next.disabled = false;
      } else {
        body.innerHTML = '<div class="oa-card"><h4>Pronto para guardar</h4><p style="font-size:.86rem;color:#4B4B4B;line-height:1.5;margin:6px 0 0">APR' + (permits.length ? ', ' + permits.length + ' PT(s)' : '') + ', ' + workers.length + ' assinatura(s) da equipe e a aprovação de ' + esc(leaderName) + ' serão guardadas neste aparelho e enviadas sozinhas quando a internet voltar. O PDF oficial é gerado pelo servidor no envio.</p></div><div class="oa-note">Não feche o navegador em aba anônima e não limpe os dados do site até o envio.</div>';
        next.textContent = 'Guardar no aparelho'; next.className = 'oa-btn oa-coral'; next.disabled = false;
      }
    }
    function validate() {
      var name = steps[step];
      if (name === 'Equipe') {
        var okAll = true;
        body.querySelectorAll('[data-w]').forEach(function (card) {
          var err = card.querySelector('.oa-err'), cpf = card.querySelector('[data-cpf]').value, msg = '';
          if (!pads[card.dataset.w].has()) msg = 'Falta a rubrica.'; else if (!cpfOk(cpf)) msg = 'CPF inválido.';
          err.hidden = !msg; err.textContent = msg; if (msg) okAll = false;
        });
        return okAll;
      }
      if (name === 'Líder') {
        var err = body.querySelector('.oa-err'), msg = '';
        if (!leaderPad.has()) msg = 'Falta a rubrica do líder.'; else if (!body.querySelector('[data-pass]').value) msg = 'Digite a senha do líder.'; else if (!body.querySelector('[data-decl]').checked) msg = 'Confirme a declaração.';
        err.hidden = !msg; err.textContent = msg; return !msg;
      }
      return true;
    }
    var collected = { cpf: {}, sig: {}, leaderSig: '', pass: '' };
    function collect() {
      var name = steps[step];
      if (name === 'Equipe') body.querySelectorAll('[data-w]').forEach(function (card) { var i = card.dataset.w; collected.cpf[i] = card.querySelector('[data-cpf]').value; collected.sig[i] = pads[i].data(); });
      if (name === 'Líder') { collected.leaderSig = leaderPad.data(); collected.pass = body.querySelector('[data-pass]').value; }
    }
    function finish() {
      next.disabled = true;
      var fd = new FormData(aprForm), entries = [];
      fd.forEach(function (v, k) { if (k !== 'action') entries.push([k, v]); });
      Object.keys(collected.sig).forEach(function (i) { entries.push(['offline_sig_' + i, collected.sig[i]]); entries.push(['offline_cpf_' + i, collected.cpf[i]]); });
      entries.push(['offline_leader_sig', collected.leaderSig]); entries.push(['offline_leader_password', collected.pass]);
      entries.push(['offline_captured_at', new Date().toISOString()]); entries.push(['offline_bundle_id', bundleId]);
      var m = location.pathname.match(/^\/apr\/(\d+)\/edit$/); if (m) entries.push(['offline_apr_doc_id', m[1]]);
      permits.forEach(function (p, n) { entries.push(['pt' + n + '__permit_name', p]); (saved[p].entries || []).forEach(function (e) { entries.push(['pt' + n + '__' + e[0], e[1]]); }); });
      var act = aprForm.querySelector('[name=activity]');
      var item = { id: bundleId, instance: bundleId, action: '/apr/offline-bundle', entries: entries, user_id: (document.body.dataset.userId || ''),
        title: 'APR offline — ' + (act && act.value ? act.value.trim().slice(0, 90) : 'sem título'), kind_label: 'APR completa (offline)', page: location.pathname,
        requested_action: 'offline_bundle', created_at: new Date().toISOString(), status: 'pending', attempts: 0, error: '' };
      OB.put(item).then(function () {
        permits.forEach(function (p) { delPT(bundleId + '|' + p); });
        if (navigator.serviceWorker && navigator.serviceWorker.ready) navigator.serviceWorker.ready.then(function (r) { if (r.sync) return r.sync.register('sp-outbox-sync'); }).catch(function () {});
        if (window.SafetyPlusOffline) window.SafetyPlusOffline.refresh();
        body.innerHTML = '<div class="oa-card" style="border-color:#32CAA0"><h4>APR guardada no aparelho</h4><p style="font-size:.86rem;color:#4B4B4B;margin:6px 0 0">Ela será enviada sozinha quando a internet voltar. Acompanhe em Modo Offline → Fila de envio.</p></div>';
        stepsEl.innerHTML = ''; prev.style.visibility = 'hidden'; next.textContent = 'Abrir Modo Offline'; next.className = 'oa-btn oa-dark'; next.disabled = false;
        next.onclick = function () { location.href = '/admin/offline'; };
      }).catch(function () { alert('Não foi possível guardar no aparelho. Verifique o espaço disponível.'); next.disabled = false; });
    }
    function openPT(p) {
      var f = document.createElement('div'); f.className = 'oa-frame';
      f.innerHTML = '<header><span>' + esc(p) + ' — PT desta APR</span><button type="button" class="oa-btn oa-ghost">Fechar</button></header><iframe title="PT"></iframe>';
      f.querySelector('iframe').src = '/permit/' + KIND[p] + '/new?offline_bundle=' + encodeURIComponent(bundleId) + '&permit=' + encodeURIComponent(p);
      f.querySelector('button').onclick = function () { f.remove(); refreshPTs().then(render); };
      document.body.appendChild(f);
    }
    next.onclick = function () {
      if (steps[step] === 'Concluir') return finish();
      if (!validate()) return; collect(); step++; render();
    };
    prev.onclick = function () { if (step) { step--; render(); } };
    refreshPTs().then(render);
  }

  // Botão principal: sem internet, abre o assistente offline.
  document.addEventListener('click', function (ev) {
    var btn = ev.target.closest && ev.target.closest('#apr-primary-action');
    if (!btn) return;
    if (navigator.onLine) return; // com indicação de rede, o fluxo online decide; a barra abaixo cobre redes instáveis
    ev.preventDefault(); ev.stopImmediatePropagation(); openWizard();
  }, true);
  function offBar() {
    var footer = document.querySelector('#apr-form .form-footer'); if (!footer) return;
    var bar = document.getElementById('oa-offbar');
    isOffline().then(function (off) {
      if (!off) { if (bar) bar.remove(); return; }
      css(); if (bar) return;
      bar = document.createElement('div'); bar.id = 'oa-offbar'; bar.className = 'oa-offbar';
      bar.innerHTML = '<div><b>Sem internet</b>Conclua esta APR no aparelho: assinatura manual da equipe e aprovação manual do líder.</div><button type="button" class="oa-btn oa-coral">Concluir offline</button>';
      bar.querySelector('button').onclick = openWizard;
      footer.parentNode.insertBefore(bar, footer);
    });
  }
  window.addEventListener('online', offBar); window.addEventListener('offline', offBar);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', offBar); else offBar();
  window.SafetyPlusOfflineApr = { open: openWizard };
})();
