/* Safety Plus — Central do Modo Offline (V36.18.95) */
(function () {
  'use strict';
  var root = document.getElementById('offline-center');
  if (!root || !window.SafetyPlusOutbox) return;
  var OB = window.SafetyPlusOutbox, SP = function () { return window.SafetyPlusOffline; };
  var $ = function (id) { return document.getElementById(id); };
  var esc = function (v) { return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); };
  var fmt = function (iso) { try { return new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }); } catch (e) { return ''; } };
  var GROUPS = [['apr', 'APR'], ['permit', 'Permissões de Trabalho'], ['rac', 'RAC'], ['inspection', 'Inspeções e veículos']];
  var FALLBACK = { pt_height: 'Trabalho em Altura', confined: 'Espaço Confinado', electrical: 'Intervenção Elétrica', line_live: 'Linha Viva', vegetation: 'Supressão de Vegetação', lifting: 'Içamento de Carga', tme: 'TME',
    light_vehicle: 'Veículo Leve', hoist: 'Talha Guincho', height_kit: 'Kit de Trabalho em Altura', climber_assist: 'Climber Assist', safety_belt: 'Cinto de Segurança', spiq: 'Equipamentos SPIQ', loto: 'LOTO', grinder: 'Esmerilhadeira', drill: 'Furadeira', rotary_hammer: 'Martelete', circular_saw: 'Serra Circular', marble_saw: 'Serra Mármore', welding_machine: 'Máquina de Solda', lifting_accessories: 'Acessórios de Içamento' };
  var ICON = {
    clock: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
    alert: '<svg viewBox="0 0 24 24"><path d="M12 3 2 20h20L12 3Z"/><path d="M12 10v4M12 17h.01"/></svg>',
    ok: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/></svg>',
    doc: '<svg viewBox="0 0 24 24"><rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6M9 12h6M9 16h4"/></svg>'
  };
  var forms = [], filter = 'all';

  function storedNames() { try { return JSON.parse(localStorage.getItem('sp-offline-forms') || '{}'); } catch (e) { return {}; } }
  function nameFor(path) {
    var n = storedNames()[path]; if (n) return n;
    if (path === '/apr/new') return 'Nova APR';
    if (path === '/vehicle/new') return 'Veículo Pesado';
    var code = path.split('/')[2] || '';
    return FALLBACK[code] || code.replace(/^rac_/, '').replace(/_/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); });
  }
  function groupOf(path) { var g = path.split('/')[1]; return g === 'vehicle' ? 'inspection' : g; }

  function connection() {
    var on = navigator.onLine;
    $('oc-net').textContent = on ? 'Conectado' : 'Sem conexão';
    $('oc-net-dot').className = on ? 'on' : 'off';
    $('oc-send').disabled = !on;
    var label = localStorage.getItem('sp-offline-prepared-at'), ts = Number(localStorage.getItem('sp-offline-prepared-ts') || 0);
    var old = ts && Date.now() - ts > 24 * 3600 * 1000;
    $('oc-prep').textContent = label ? 'Preparado em ' + label + (old ? ' · atualize' : '') : 'Aparelho ainda não preparado';
    $('oc-prep-dot').className = label ? (old ? 'off' : 'on') : 'bad';
    $('oc-prepare').disabled = !on;
  }
  function storage() {
    if (!navigator.storage || !navigator.storage.estimate) return;
    navigator.storage.estimate().then(function (e) {
      var used = (e.usage || 0) / 1048576, quota = (e.quota || 0) / 1048576;
      $('oc-storage').textContent = 'Espaço usado: ' + used.toFixed(1) + ' MB' + (quota ? ' de ' + (quota > 1024 ? (quota / 1024).toFixed(1) + ' GB' : quota.toFixed(0) + ' MB') : '');
      $('oc-storage-chip').hidden = false;
    }).catch(function () {});
  }

  function renderQueue() {
    return Promise.all([OB.list(), OB.history()]).then(function (res) {
      var items = res[0], hist = res[1];
      var att = items.filter(function (i) { return i.status === 'attention'; }), pend = items.length - att.length;
      $('oc-k-pend').textContent = pend; $('oc-k-att').textContent = att.length; $('oc-k-sent').textContent = hist.length;
      var me = (document.body && document.body.dataset.userId) || '';
      $('oc-queue').innerHTML = items.length ? items.map(function (i) {
        var isAtt = i.status === 'attention', other = me && i.user_id && String(i.user_id) !== String(me);
        var desc = i.kind_label + ' · salvo em ' + fmt(i.created_at) + (i.attempts ? ' · ' + i.attempts + ' tentativa(s)' : '');
        var note = isAtt ? i.error : (other ? 'Registrado por outra conta neste aparelho. Entre com ela para enviar.' : (OB.DRAFT_ONLY.test(i.action) ? 'Será salvo no servidor como rascunho.' : (i.error || 'Aguardando conexão.')));
        return '<div class="oc-item ' + (isAtt ? 'att' : '') + '"><span class="ic">' + (isAtt ? ICON.alert : ICON.clock) + '</span><div style="min-width:0"><strong>' + esc(i.title) + '</strong><small>' + esc(desc) + '</small><div class="' + (isAtt ? 'err' : 'oc-muted') + '" style="font-size:.78rem;margin-top:3px">' + esc(note) + '</div></div>' +
          '<div class="acts">' + (isAtt && !other ? '<button type="button" class="sx-btn sx-btn-dark sx-btn-sm" data-review="' + esc(i.id) + '">Revisar e corrigir</button>' : '') + (isAtt && i.result_url ? '<a class="sx-btn sx-btn-dark sx-btn-sm" href="' + esc(i.result_url) + '">Abrir e corrigir</a>' : '') +
          (!isAtt ? '<button type="button" class="sx-btn sx-btn-ghost sx-btn-sm" data-send="' + esc(i.id) + '">Enviar</button>' : '<button type="button" class="sx-btn sx-btn-dark sx-btn-sm" data-retry="' + esc(i.id) + '">Tentar de novo</button><button type="button" class="sx-btn sx-btn-ghost sx-btn-sm" data-done="' + esc(i.id) + '" data-noserver="' + (i.result_url ? '' : '1') + '">Já revisei</button>') +
          '<button type="button" class="sx-btn sx-btn-danger sx-btn-sm" data-discard="' + esc(i.id) + '">Descartar</button></div></div>';
      }).join('') : '<div class="sx-empty">Nada na fila. Tudo o que foi salvo neste aparelho já chegou ao servidor.</div>';
      $('oc-history-wrap').hidden = !hist.length;
      $('oc-history').innerHTML = hist.slice(0, 15).map(function (h) {
        return '<div class="oc-item ok"><span class="ic">' + ICON.ok + '</span><div style="min-width:0"><strong>' + esc(h.title) + '</strong><small>' + esc((h.kind || '') + ' · feito em ' + fmt(h.captured_at) + ' · enviado em ' + fmt(h.synced_at)) + '</small><div class="oc-muted" style="font-size:.78rem;margin-top:3px">' + esc(h.message || '') + '</div></div>' +
          '<div class="acts">' + (h.url ? '<a class="sx-btn sx-btn-ghost sx-btn-sm" href="' + esc(h.url) + '">Abrir</a>' : '') + '</div></div>';
      }).join('');
    }).catch(function () { $('oc-queue').innerHTML = '<div class="sx-empty">Não foi possível ler a fila deste navegador.</div>'; });
  }

  function reviewItem(id) {
    return OB.get(id).then(function (item) {
      if (!item) return;
      var me = (document.body && document.body.dataset.userId) || '';
      if (!me || (item.user_id && String(item.user_id) !== String(me))) {
        alert('Entre com a conta que criou este registro para revisar.'); return;
      }
      var dialog = document.createElement('dialog');
      dialog.style.cssText = 'width:min(680px,90vw);max-height:85vh;overflow:auto;border:1px solid #ddd;border-radius:16px;padding:24px';
      var form = document.createElement('form');
      var title = document.createElement('h2'); title.textContent = 'Revisar e corrigir'; form.appendChild(title);
      var note = document.createElement('p'); note.textContent = (item.error || item.title) + ' Confira os campos abaixo. Os anexos serão mantidos; após salvar, toque em Tentar de novo.'; form.appendChild(note);
      var inputs = [];
      (item.entries || []).forEach(function (entry, index) {
        if (/csrf|token|password|secret/i.test(entry[0]) || /^(action|offline_bundle_id|offline_apr_doc_id|offline_captured_at|offline_leader_sig|offline_sig_\d+)$/.test(entry[0])) return;
        var label = document.createElement('label');
        label.style.cssText = 'display:block;margin:12px 0';
        label.textContent = entry[0].replace(/_/g, ' ');
        if (typeof entry[1] !== 'string') {
          var file = document.createElement('span');
          file.textContent = ' — Anexo mantido: ' + (entry[1].name || 'arquivo'); label.appendChild(file);
        } else {
          var input = document.createElement('textarea'); input.value = entry[1]; input.rows = 2;
          input.style.cssText = 'display:block;width:100%;box-sizing:border-box;padding:8px';
          label.appendChild(input); inputs.push({ index: index, input: input });
        }
        form.appendChild(label);
      });
      var save = document.createElement('button'); save.type = 'submit'; save.className = 'sx-btn sx-btn-dark'; save.textContent = 'Salvar correções';
      var cancel = document.createElement('button'); cancel.type = 'button'; cancel.className = 'sx-btn sx-btn-ghost'; cancel.textContent = 'Cancelar';
      cancel.onclick = function () { dialog.close(); };
      form.append(save, cancel); dialog.appendChild(form); document.body.appendChild(dialog);
      dialog.addEventListener('close', function () { dialog.remove(); });
      form.addEventListener('submit', function (event) {
        event.preventDefault(); save.disabled = true;
        // Mantém anexos, campos repetidos, identidade e destino do registro.
        inputs.forEach(function (field) { item.entries[field.index][1] = field.input.value; });
        item.status = 'attention'; item.error = 'Correções salvas no aparelho. Toque em Tentar de novo para reenviar.';
        OB.put(item).then(function () { dialog.close(); return refreshAll(); }).then(function () { if (SP()) SP().refresh(); })
          .catch(function () { save.disabled = false; alert('Não foi possível salvar as correções. Mantenha esta janela aberta e tente novamente.'); });
      });
      dialog.showModal();
    }).catch(function () { alert('Não foi possível abrir o registro para revisão.'); });
  }

  function renderForms() {
    if (!('caches' in window)) { $('oc-forms').innerHTML = '<div class="sx-card sx-empty">Este navegador não guarda páginas offline.</div>'; return Promise.resolve(); }
    return caches.open(OB.PAGES_CACHE).then(function (c) { return c.keys(); }).then(function (keys) {
      var seen = {}; forms = [];
      var recent = [];
      keys.forEach(function (k) {
        var p = new URL(k.url).pathname; if (seen[p]) return; seen[p] = 1;
        if (/\/new$/.test(p)) forms.push({ path: p, group: groupOf(p), name: nameFor(p) });
        else if (/\/edit$/.test(p)) recent.push(p);
      });
      forms.sort(function (a, b) { return a.name.localeCompare(b.name, 'pt-BR'); });
      $('oc-k-forms').textContent = forms.length;
      // Rascunhos recentes guardados
      var meta = (SP() && SP().recentEdits()) || [];
      var rec = meta.filter(function (r) { return recent.indexOf(r.path) >= 0; });
      $('oc-recent-wrap').hidden = !rec.length;
      $('oc-recent').innerHTML = rec.map(function (r) { return '<div class="oc-item"><span class="ic">' + ICON.doc + '</span><div style="min-width:0"><strong>' + esc(r.title) + '</strong><small>Aberto em ' + esc(fmt(r.at)) + '</small></div><div class="acts"><a class="sx-btn sx-btn-ghost sx-btn-sm" href="' + esc(r.path) + '">Continuar</a><button type="button" class="sx-btn sx-btn-danger sx-btn-sm" data-rm-recent="' + esc(r.path) + '">Remover</button></div></div>'; }).join('');
      drawFilter(); drawForms();
    }).catch(function () {});
  }
  function drawFilter() {
    var html = '<button type="button" data-f="all" class="' + (filter === 'all' ? 'is-active' : '') + '">Todos<em>' + forms.length + '</em></button>';
    GROUPS.forEach(function (g) { var n = forms.filter(function (f) { return f.group === g[0]; }).length; if (n) html += '<button type="button" data-f="' + g[0] + '" class="' + (filter === g[0] ? 'is-active' : '') + '">' + g[1].split(' ')[0] + '<em>' + n + '</em></button>'; });
    $('oc-filter').innerHTML = html;
  }
  function drawForms() {
    var q = ($('oc-search').value || '').trim().toLowerCase(), shown = 0, html = '';
    GROUPS.forEach(function (g) {
      if (filter !== 'all' && filter !== g[0]) return;
      var list = forms.filter(function (f) { return f.group === g[0] && (!q || f.name.toLowerCase().indexOf(q) >= 0); });
      if (!list.length) return; shown += list.length;
      html += '<div class="oc-group"><h4>' + esc(g[1]) + '<em>' + list.length + '</em></h4>' + list.map(function (f) { return '<a class="oc-link" href="' + esc(f.path) + '">' + esc(f.name) + '</a>'; }).join('') + '</div>';
    });
    $('oc-forms').innerHTML = html || '<div class="sx-card sx-empty" style="grid-column:1/-1">' + (forms.length ? 'Nenhum formulário com esse nome.' : 'Nenhum formulário preparado neste aparelho. Com internet, toque em “Preparar este aparelho”.') + '</div>';
    $('oc-forms-label').textContent = shown + ' de ' + forms.length;
  }

  function refreshAll() { connection(); storage(); return Promise.all([renderQueue(), renderForms()]); }

  $('oc-filter').addEventListener('click', function (e) { var b = e.target.closest('button[data-f]'); if (!b) return; filter = b.dataset.f; drawFilter(); drawForms(); });
  $('oc-search').addEventListener('input', drawForms);
  $('oc-queue').addEventListener('click', function (e) {
    var b = e.target.closest('button'); if (!b) return;
    if (b.dataset.review) {
      reviewItem(b.dataset.review);
    } else if (b.dataset.discard) {
      if (!confirm('Descartar este registro? Ele será apagado deste aparelho e NÃO será enviado ao servidor.')) return;
      OB.remove(b.dataset.discard).then(refreshAll).then(function () { if (SP()) SP().refresh(); });
    } else if (b.dataset.retry) {
      b.disabled = true; b.textContent = 'Enviando…';
      OB.flush({ only: b.dataset.retry, includeAttention: true }).then(function (r) {
        if (r.login) alert('Faça login novamente para enviar.'); else if (r.error) alert('Não foi possível enviar: ' + r.error);
      }).then(refreshAll).then(function () { if (SP()) SP().refresh(); });
    } else if (b.dataset.done) {
      if (b.dataset.noserver && !confirm('Atenção: este registro NÃO chegou ao servidor. Se continuar, o conteúdo será apagado deste aparelho. Deseja apagar?')) return;
      OB.remove(b.dataset.done).then(refreshAll).then(function () { if (SP()) SP().refresh(); });
    } else if (b.dataset.send) {
      b.disabled = true; b.textContent = 'Enviando…';
      (SP() ? SP().reachable(4000) : Promise.resolve(navigator.onLine)).then(function (ok) {
        if (!ok) { alert('Sem conexão com o servidor no momento.'); return; }
        return OB.flush({ only: b.dataset.send }).then(function (r) { if (r.login) alert('Faça login novamente para enviar.'); else if (r.error) alert('Não foi possível enviar: ' + r.error); else if (r.otherUser) alert('Este registro foi criado por outra conta. Entre com ela para enviar.'); });
      }).then(refreshAll).then(function () { if (SP()) SP().refresh(); });
    }
  });
  $('oc-send').addEventListener('click', function () {
    var btn = $('oc-send'); btn.disabled = true;
    Promise.resolve(SP() ? SP().sync(true) : OB.flush({})).then(refreshAll).then(function () { btn.disabled = !navigator.onLine; });
  });
  $('oc-clear-history').addEventListener('click', function () { OB.clearHistory().then(refreshAll); });
  $('oc-prepare').addEventListener('click', function () {
    if (!SP()) return;
    var btn = $('oc-prepare'), bar = $('oc-progress'), msg = $('oc-prep-msg');
    btn.disabled = true; bar.style.display = 'block';
    SP().prepare(function (p, m) { bar.firstElementChild.style.width = p + '%'; msg.textContent = m; }, { recent: true }).then(function (r) {
      msg.textContent = r.ok + ' de ' + r.total + ' formulários e ' + r.statics + ' arquivos de apoio guardados.' + (r.failed.length ? ' Indisponíveis: ' + r.failed.length + '.' : '') + (r.persisted ? ' Armazenamento protegido contra limpeza automática.' : '');
    }).catch(function (e) { msg.textContent = 'Não foi possível preparar: ' + e.message; })
      .then(function () { btn.disabled = false; setTimeout(function () { bar.style.display = 'none'; }, 1500); refreshAll(); });
  });
  // ---- Remoção de arquivos guardados neste aparelho (a fila de envio nunca é apagada aqui) ----
  var RECENT_KEY = 'sp-offline-recent-edits', DRAFT_DB = 'safetyplus-browser-drafts-v1';
  var PREP_KEYS = ['sp-offline-prepared-ts', 'sp-offline-prepared-at', 'sp-offline-prepared-user', 'sp-offline-forms', 'sp-offline-people'];
  function lsDel(keys) { keys.forEach(function (k) { try { localStorage.removeItem(k); } catch (e) {} }); }
  function dropDrafts() {
    return new Promise(function (res) {
      if (!('indexedDB' in window)) return res();
      var r = indexedDB.deleteDatabase(DRAFT_DB); r.onsuccess = r.onerror = r.onblocked = function () { res(); };
    });
  }
  function dropOneDraft(path) {
    return new Promise(function (res) {
      if (!('indexedDB' in window)) return res();
      var o = indexedDB.open(DRAFT_DB, 1);
      o.onupgradeneeded = function () { try { o.result.createObjectStore('drafts', { keyPath: 'id' }); } catch (e) {} };
      o.onerror = function () { res(); };
      o.onsuccess = function () {
        try { var tx = o.result.transaction('drafts', 'readwrite'); tx.objectStore('drafts').delete(path); tx.oncomplete = tx.onabort = function () { o.result.close(); res(); }; } catch (e) { res(); }
      };
    });
  }
  function dropCaches(all) {
    if (!('caches' in window)) return Promise.resolve();
    return caches.keys().then(function (names) {
      return Promise.all(names.filter(function (n) { return all ? /^sp-/.test(n) : n === OB.PAGES_CACHE; }).map(function (n) { return caches.delete(n); }));
    });
  }
  function msg(t) { var m = $('oc-clean-msg'); if (m) m.textContent = t; }
  $('oc-recent').addEventListener('click', function (e) {
    var b = e.target.closest('button[data-rm-recent]'); if (!b) return;
    var path = b.dataset.rmRecent;
    if (!confirm('Remover este rascunho guardado no aparelho? O documento no servidor não é afetado.')) return;
    try { var list = JSON.parse(localStorage.getItem(RECENT_KEY) || '[]').filter(function (r) { return r.path !== path; }); localStorage.setItem(RECENT_KEY, JSON.stringify(list)); } catch (err) {}
    Promise.all([dropOneDraft(path), ('caches' in window) ? caches.open(OB.PAGES_CACHE).then(function (c) { return c.delete(path); }) : null]).then(refreshAll);
  });
  $('oc-rm-forms').addEventListener('click', function () {
    if (!confirm('Remover os formulários e arquivos de apoio guardados neste aparelho? Será preciso preparar o aparelho de novo para usar sem internet. A fila de envio não é apagada.')) return;
    dropCaches(true).then(function () { lsDel(PREP_KEYS); msg('Formulários e arquivos guardados foram removidos.'); return refreshAll(); });
  });
  $('oc-rm-drafts').addEventListener('click', function () {
    if (!confirm('Apagar todos os rascunhos automáticos guardados neste aparelho? Documentos já salvos no servidor não são afetados. A fila de envio não é apagada.')) return;
    dropDrafts().then(function () { lsDel([RECENT_KEY]); msg('Rascunhos do aparelho apagados.'); return refreshAll(); });
  });
  $('oc-repair').addEventListener('click', function () {
    if (!confirm('Reparar o modo offline? Os arquivos guardados são limpos e o aparelho é preparado de novo (precisa de internet). A fila de envio e os rascunhos são mantidos.')) return;
    if (!navigator.onLine) { alert('Conecte-se à internet para reparar.'); return; }
    var btn = $('oc-repair'); btn.disabled = true; msg('Limpando…');
    var sw = ('serviceWorker' in navigator) ? navigator.serviceWorker.getRegistrations().then(function (rs) { return Promise.all(rs.map(function (r) { return r.unregister(); })); }) : Promise.resolve();
    sw.then(function () { return dropCaches(true); }).then(function () {
      lsDel(PREP_KEYS);
      if ('serviceWorker' in navigator) return navigator.serviceWorker.register('/sw.js').catch(function () {});
    }).then(function () { msg('Preparando de novo…'); location.reload(); }).catch(function (e) { btn.disabled = false; msg('Não foi possível reparar: ' + (e && e.message || e)); });
  });
  window.addEventListener('online', connection); window.addEventListener('offline', connection);
  window.addEventListener('sp-offline-queue', function () { renderQueue(); });
  refreshAll();
})();
