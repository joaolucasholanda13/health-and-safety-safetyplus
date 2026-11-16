/* Safety Plus — sincronização offline nas páginas (V36.18.95)
   - Sem conexão real, o envio de APR, PT, RAC, inspeções e veículo vai para a fila do aparelho.
   - Envio automático quando a internet volta (página aberta, Background Sync ou botão Enviar agora).
   - Preparação do dispositivo: formulários + todos os arquivos estáticos que eles usam.
   - Rascunhos abertos recentemente ficam disponíveis offline. */
(function () {
  'use strict';
  if (window.SafetyPlusOffline) return;
  var OB = window.SafetyPlusOutbox;
  if (!OB) return;
  var PREP_KEY = 'sp-offline-prepared-ts', PREP_LABEL = 'sp-offline-prepared-at', RECENT_KEY = 'sp-offline-recent-edits';
  var userId = (document.body && document.body.dataset.userId) || '';
  var instance = (window.crypto && crypto.randomUUID) ? crypto.randomUUID() : (Date.now().toString(36) + Math.random().toString(36).slice(2));
  var lastOk = 0;

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function pathOf(form) { try { return new URL(form.getAttribute('action') || location.pathname, location.origin).pathname; } catch (e) { return ''; } }

  // ---------- Conexão real (não apenas navigator.onLine) ----------
  function reachable(timeout) {
    if (!navigator.onLine) return Promise.resolve(false);
    if (Date.now() - lastOk < 15000) return Promise.resolve(true);
    var ctrl = ('AbortController' in window) ? new AbortController() : null;
    var t = setTimeout(function () { if (ctrl) ctrl.abort(); }, timeout || 2500);
    return fetch('/health?_=' + Date.now(), { cache: 'no-store', credentials: 'same-origin', signal: ctrl ? ctrl.signal : undefined })
      .then(function (r) { clearTimeout(t); if (r.ok) lastOk = Date.now(); return r.ok; })
      .catch(function () { clearTimeout(t); return false; });
  }

  // ---------- Avisos ----------
  function css() {
    if (document.getElementById('sp-off-style')) return;
    var s = document.createElement('style'); s.id = 'sp-off-style';
    s.textContent = '#sp-offline-indicator{display:none;align-items:center;gap:6px;border-radius:999px;padding:6px 11px;font:600 12px/1 Poppins,system-ui,sans-serif;white-space:nowrap;text-decoration:none;flex-shrink:0;border:1px solid transparent}' +
      '#sp-offline-indicator i{width:8px;height:8px;border-radius:50%;background:currentColor;display:inline-block}' +
      '#sp-offline-indicator.off{background:#181818;color:#fff}#sp-offline-indicator.pend{background:#FFF6D8;color:#5F4700;border-color:#F5E3A6}#sp-offline-indicator.att{background:#FBE7E6;color:#D23532;border-color:#F2C2BF}' +
      '.sp-off-toast{position:fixed;left:50%;top:14px;transform:translateX(-50%);z-index:100000;max-width:min(560px,calc(100vw - 24px));background:#181818;color:#fff;border-radius:14px;padding:14px 16px;box-shadow:0 14px 40px rgba(0,0,0,.28);font:14px/1.45 Poppins,system-ui,sans-serif;display:flex;gap:12px;align-items:flex-start}' +
      '.sp-off-toast b{display:block;margin-bottom:2px}.sp-off-toast a{color:#FF5246;font-weight:600}.sp-off-toast button{background:none;border:0;color:#bbb;font-size:18px;cursor:pointer;line-height:1;padding:0 2px}' +
      '.sp-off-toast .bar{width:4px;align-self:stretch;border-radius:4px;background:#FF5246;flex:0 0 4px}.sp-off-toast.ok .bar{background:#32CAA0}.sp-off-toast.warn .bar{background:#FFD964}';
    document.head.appendChild(s);
  }
  function toast(title, msg, kind, ms) {
    css();
    var old = document.querySelector('.sp-off-toast'); if (old) old.remove();
    var el = document.createElement('div'); el.className = 'sp-off-toast ' + (kind || ''); el.setAttribute('role', 'status');
    el.innerHTML = '<span class="bar"></span><div style="flex:1"><b></b><span></span> <a href="/admin/offline">Abrir Modo Offline</a></div><button type="button" aria-label="Fechar">×</button>';
    el.querySelector('b').textContent = title; el.querySelector('span:not(.bar)').textContent = msg;
    el.querySelector('button').onclick = function () { el.remove(); };
    document.body.appendChild(el);
    if (ms !== 0) setTimeout(function () { el.remove(); }, ms || 9000);
  }
  function indicator() {
    var el = document.getElementById('sp-offline-indicator'); if (el) return el;
    var host = document.querySelector('.app-topbar .topbar-actions'); if (!host) return null;
    css(); el = document.createElement('a'); el.id = 'sp-offline-indicator'; el.href = '/admin/offline';
    host.insertBefore(el, host.firstChild); return el;
  }
  function refresh() {
    return OB.list().then(function (items) {
      var pend = items.filter(function (i) { return i.status !== 'attention'; }).length;
      var att = items.length - pend;
      window.safetyPlusOfflinePending = items.length;
      window.dispatchEvent(new CustomEvent('sp-offline-queue', { detail: { count: items.length, pending: pend, attention: att, online: navigator.onLine } }));
      var el = indicator(); if (!el) return;
      var txt = '', cls = '';
      if (att) { txt = att + ' para revisar'; cls = 'att'; }
      else if (pend) { txt = pend + ' na fila'; cls = 'pend'; }
      else if (!navigator.onLine) { txt = 'Offline'; cls = 'off'; }
      el.className = cls; el.style.display = txt ? 'inline-flex' : 'none';
      el.innerHTML = '<i></i>'; el.appendChild(document.createTextNode(txt));
      el.title = att ? 'Há envios que precisam de revisão. Toque para abrir.' : pend ? 'Envios guardados no aparelho, aguardando internet.' : 'Sem conexão. Formulários preparados continuam disponíveis.';
      if (pend) schedule();
    }).catch(function () {});
  }
  var timer = null;
  function schedule() { if (!timer) timer = setInterval(function () { sync(false); }, 45000); }

  // ---------- Fila ----------
  function headingText() {
    var h = document.querySelector('.app-topbar h1') || document.querySelector('h1, h2');
    if (!h) return '';
    var c = h.cloneNode(true); c.querySelectorAll('script,style').forEach(function (x) { x.remove(); });
    return c.textContent.replace(/\s+/g, ' ').trim();
  }
  function titleOf(form) {
    var act = form.querySelector('[name=activity]');
    var base = headingText() || document.title || 'Formulário';
    var a = act && act.value ? ' — ' + act.value.trim().slice(0, 80) : '';
    return (base + a).slice(0, 160);
  }
  function kindLabel(path) {
    if (/^\/apr\//.test(path)) return 'APR';
    if (/^\/permit\//.test(path)) return 'Permissão de Trabalho';
    if (/^\/rac\//.test(path)) return 'RAC';
    if (/^\/vehicle\//.test(path)) return 'Veículo Pesado';
    return 'Inspeção';
  }
  function queue(form, data) {
    var action = pathOf(form), entries = [];
    data.forEach(function (v, k) { entries.push([k, v]); });
    var act = (entries.filter(function (e) { return e[0] === 'action'; })[0] || [])[1] || 'draft';
    var item = {
      id: instance, instance: instance, action: action, entries: entries, user_id: userId,
      title: titleOf(form), kind_label: kindLabel(action), page: location.pathname,
      requested_action: act, created_at: new Date().toISOString(), status: 'pending', attempts: 0, error: ''
    };
    return OB.put(item).then(function () {
      if ('serviceWorker' in navigator && navigator.serviceWorker.ready) {
        navigator.serviceWorker.ready.then(function (reg) { if (reg.sync) return reg.sync.register('sp-outbox-sync'); }).catch(function () {});
      }
      var draftOnly = OB.DRAFT_ONLY.test(action);
      toast('Sem internet: guardado no aparelho',
        draftOnly && act !== 'draft'
          ? 'Será enviado automaticamente como RASCUNHO quando a conexão voltar. Conclua as próximas etapas (assinaturas, início da PT, aprovação) com internet.'
          : 'Será enviado automaticamente quando a conexão voltar. Não limpe os dados do navegador.', 'warn', 12000);
      // Libera os botões que o feedback de envio bloqueou.
      try { window.dispatchEvent(new Event('pageshow')); } catch (e) {}
      refresh();
    });
  }
  document.addEventListener('submit', function (ev) {
    var form = ev.target;
    if (!form || form.tagName !== 'FORM' || ev.defaultPrevented) return;
    if (String(form.getAttribute('method') || '').toLowerCase() !== 'post' || !OB.SAVE_RE.test(pathOf(form))) return;
    if (navigator.onLine && Date.now() - lastOk < 15000) return; // conexão confirmada há pouco: envio normal
    ev.preventDefault();
    // Captura antes da espera: o feedback pode desativar o botão no próximo frame.
    var data = new FormData(form), submitter = ev.submitter;
    if (submitter && submitter.name && !submitter.disabled) data.append(submitter.name, submitter.value);
    reachable().then(function (ok) {
      if (ok) {
        // submit() nativo não inclui o botão que originou o envio.
        var buttonField = null;
        if (submitter && submitter.name) {
          buttonField = document.createElement('input'); buttonField.type = 'hidden';
          buttonField.name = submitter.name; buttonField.value = submitter.value; form.appendChild(buttonField);
        }
        try { HTMLFormElement.prototype.submit.call(form); }
        finally { if (buttonField) buttonField.remove(); }
        return;
      }
      // APR sem conexão real (sinal fraco: navigator.onLine ainda é true): ao avançar de etapa,
      // abre o assistente com rubricas em vez de guardar só um rascunho sem assinaturas.
      var aprAct = String(data.get('action') || '');
      if (form.id === 'apr-form' && aprAct && aprAct !== 'draft' && window.SafetyPlusOfflineApr) {
        try { window.dispatchEvent(new Event('pageshow')); } catch (e) {}
        window.SafetyPlusOfflineApr.open();
        return;
      }
      return queue(form, data).catch(function () {
        alert('Sem conexão e não foi possível guardar no aparelho (espaço ou modo privativo). Mantenha esta tela aberta e tente de novo quando houver sinal.');
        try { window.dispatchEvent(new Event('pageshow')); } catch (e) {}
      });
    });
  }, false);

  // ---------- Sincronização ----------
  function sync(manual) {
    return reachable(4000).then(function (ok) {
      if (!ok) { if (manual) toast('Ainda sem conexão', 'Os envios continuam guardados no aparelho.', 'warn', 6000); return null; }
      return OB.flush({ includeAttention: false }).then(function (r) {
        if (r.login) toast('Faça login para enviar', 'Há envios guardados no aparelho. Entre novamente no Safety Plus para concluir a sincronização.', 'warn', 0);
        else if (r.sent || r.attention) toast(r.sent + ' envio(s) sincronizado(s)' + (r.attention ? ' · ' + r.attention + ' para revisar' : ''),
          r.attention ? 'Alguns registros foram salvos, mas o servidor apontou pendências. Revise no Modo Offline.' : 'Os registros feitos sem internet chegaram ao servidor.', r.attention ? 'warn' : 'ok', 10000);
        else if (manual && r.error) toast('Não foi possível enviar', r.error + ' Os registros continuam guardados no aparelho.', 'warn', 12000);
        else if (manual && r.otherUser) toast('Envios de outro usuário', 'Há registros guardados por outra conta neste aparelho. Entre com ela para enviá-los.', 'warn', 8000);
        refresh(); return r;
      });
    });
  }

  // Migra a fila antiga de checklists (V36.18.35 a V36.18.94) para a nova fila.
  function migrateLegacy() {
    if (!window.indexedDB || lsGet('sp-outbox-migrated') === '1') return Promise.resolve();
    return new Promise(function (resolve) {
      var req = indexedDB.open('safetyplus-offline');
      req.onsuccess = function () {
        var db = req.result;
        if (!db.objectStoreNames.contains('queue')) { db.close(); lsSet('sp-outbox-migrated', '1'); resolve(); return; }
        var r = db.transaction('queue', 'readonly').objectStore('queue').getAll();
        r.onsuccess = function () {
          var items = r.result || [];
          Promise.all(items.map(function (old) {
            return OB.put({ id: 'legacy-' + old.id, instance: 'legacy-' + old.id, action: old.action, entries: old.entries, user_id: userId, title: old.title || 'Checklist', kind_label: 'Inspeção', page: '', requested_action: '', created_at: old.created_at || new Date().toISOString(), status: 'pending', attempts: 0, error: '' });
          })).then(function () {
            var del = db.transaction('queue', 'readwrite'); del.objectStore('queue').clear();
            del.oncomplete = function () { db.close(); lsSet('sp-outbox-migrated', '1'); resolve(); };
            del.onerror = function () { db.close(); resolve(); };
          }, function () { db.close(); resolve(); });
        };
        r.onerror = function () { db.close(); resolve(); };
      };
      req.onupgradeneeded = function () { /* banco antigo inexistente */ };
      req.onerror = function () { resolve(); };
    });
  }

  // ---------- Preparação do dispositivo ----------
  function staticRefs(html) {
    var out = [], re = /(?:src|href)="(\/static\/[^"#]+)"/g, m;
    while ((m = re.exec(html))) out.push(m[1].replace(/&amp;/g, '&'));
    return out;
  }
  var CORE_STATIC = ['/offline', '/static/offline.html', '/static/manifest.webmanifest?v=361831', '/static/css/serena-tokens.css?v=361895', '/static/css/serena-admin.css?v=361895',
    '/static/fonts/Serena-Variable.woff2', '/static/js/offline-core.js?v=361919', '/static/js/offline-sync.js?v=361920', '/static/js/offline-drafts.js?v=361895',
    '/static/js/offline-center.js?v=361918', '/static/js/offline-apr.js?v=361901', '/static/js/pwa.js', '/static/js/notifications-push.js', '/static/css/submit-feedback.css', '/static/js/submit-feedback.js',
    '/static/icons/safety-plus-icon-192-v361831.png', '/static/icons/safety-plus-favicon-64-v361831.png', '/static/icons/safety-plus-favicon-32-v361831.png'];
  function prepare(onProgress, opts) {
    opts = opts || {};
    var report = function (p, msg) { if (onProgress) try { onProgress(p, msg); } catch (e) {} };
    if (!navigator.onLine) return Promise.reject(new Error('Conecte-se à internet e faça login antes de preparar.'));
    if (!('serviceWorker' in navigator) || !('caches' in window)) return Promise.reject(new Error('Este navegador não suporta modo offline.'));
    var ok = 0, failed = [], statics = {};
    CORE_STATIC.forEach(function (u) { statics[u] = 1; });
    return fetch('/api/offline/form-manifest', { credentials: 'same-origin', cache: 'no-store' }).then(function (mr) {
      if (!mr.ok || mr.redirected) throw new Error('Sessão encerrada. Faça login e tente novamente.');
      return mr.json();
    }).then(function (manifest) {
      fetch('/api/offline/participants', { credentials: 'same-origin', cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : null; })
        .then(function (d) { if (d && d.people) lsSet('sp-offline-people', JSON.stringify({ at: Date.now(), user: userId, people: d.people })); }).catch(function () {});
      var names = {}; (manifest.items || []).forEach(function (it) { names[it.path] = it.title; });
      lsSet('sp-offline-forms', JSON.stringify(names));
      var paths = (manifest.paths || []).concat((opts.recent ? recentEdits().filter(function (r) { return !r.user || r.user === userId; }).map(function (r) { return r.path; }) : []));
      if (!paths.length) throw new Error('Nenhum formulário encontrado.');
      return navigator.serviceWorker.register('/sw.js', { updateViaCache: 'none' }).then(function () { return navigator.serviceWorker.ready; }).then(function () {
        return caches.open(OB.PAGES_CACHE);
      }).then(function (pages) {
        var chain = Promise.resolve();
        paths.forEach(function (path, i) {
          chain = chain.then(function () {
            report(Math.round(i * 80 / paths.length), 'Preparando ' + (i + 1) + ' de ' + paths.length);
            return fetch(path, { credentials: 'same-origin', cache: 'no-store' }).then(function (res) {
              if (res.ok && !res.redirected && (res.headers.get('content-type') || '').indexOf('text/html') >= 0) {
                return res.clone().text().then(function (html) { staticRefs(html).forEach(function (u) { statics[u] = 1; }); return pages.put(path, res); }).then(function () { if (path.indexOf('/new') > 0) ok++; });
              }
              failed.push(path);
            }).catch(function () { failed.push(path); });
          });
        });
        return chain;
      }).then(function () {
        return caches.open(OB.STATIC_CACHE).then(function (cache) {
          var list = Object.keys(statics), done = 0, chain = Promise.resolve();
          list.forEach(function (u) {
            chain = chain.then(function () {
              return fetch(u, { credentials: 'same-origin', cache: 'no-store' }).then(function (r) { if (r.ok) return cache.put(u, r); }).catch(function () {}).then(function () { done++; report(80 + Math.round(done * 20 / list.length), 'Arquivos de apoio ' + done + ' de ' + list.length); });
            });
          });
          return chain.then(function () { return list.length; });
        });
      }).then(function (nStatic) {
        if (!ok) throw new Error('Nenhum formulário pôde ser preparado; confira a sessão.');
        var label = new Date().toLocaleString('pt-BR');
        lsSet(PREP_KEY, String(Date.now())); lsSet(PREP_LABEL, label); lsSet('sp-offline-prepared-user', userId);
        var persist = (navigator.storage && navigator.storage.persist) ? navigator.storage.persist().catch(function () { return false; }) : Promise.resolve(false);
        return persist.then(function (persisted) {
          report(100, 'Concluído');
          return { ok: ok, total: (manifest.paths || []).length, failed: failed, statics: nStatic, persisted: persisted, at: label };
        });
      });
    });
  }
  // Atualiza a preparação em segundo plano (formulários mudam de versão).
  function autoPrepare() {
    var ts = Number(lsGet(PREP_KEY) || 0);
    if (!ts || !userId || Date.now() - ts < 12 * 3600 * 1000) return;
    if (lsGet('sp-offline-prepared-user') && lsGet('sp-offline-prepared-user') !== userId) return;
    reachable().then(function (ok) { if (ok) prepare(null, { recent: true }).catch(function () {}); });
  }

  // ---------- Rascunhos abertos recentemente ----------
  function recentEdits() { try { return JSON.parse(lsGet(RECENT_KEY) || '[]'); } catch (e) { return []; } }
  function rememberEdit() {
    if (!/^\/(apr\/\d+\/edit|vehicle\/\d+\/edit|(?:permit|rac|inspection)\/[^\/]+\/\d+\/edit)$/.test(location.pathname)) return;
    var list = recentEdits().filter(function (r) { return r.path !== location.pathname; });
    list.unshift({ path: location.pathname, title: headingText() || document.title, at: new Date().toISOString(), user: userId });
    lsSet(RECENT_KEY, JSON.stringify(list.slice(0, 20)));
  }

  // Busca de colaboradores sem internet: usa a lista guardada na preparação (sem CPF no aparelho).
  (function () {
    var orig = window.fetch.bind(window);
    function norm(v) { return String(v || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/\s+/g, ' ').trim(); }
    function offlineLookup(body) {
      var dir = null; try { dir = JSON.parse(lsGet('sp-offline-people') || 'null'); } catch (e) {}
      var people = (dir && dir.people) || [];
      var name = body && body.get ? String(body.get('name') || '') : '', cpf = body && body.get ? String(body.get('cpf') || '') : '';
      var res;
      if (!people.length) res = { found: false, message: 'Sem internet e sem lista de colaboradores no aparelho. Prepare o aparelho com internet.' };
      else if (cpf && !name) res = { found: false, message: 'Sem internet: pesquise pelo NOME. O CPF será confirmado na assinatura.' };
      else {
        var q = norm(name), list = people.filter(function (p) { return norm(p.full_name).indexOf(q) >= 0; }).slice(0, 12)
          .map(function (p) { return { found: true, participant_id: p.participant_id, user_id: p.user_id, cpf: '', full_name: p.full_name, job_title: p.job_title, company: p.company, can_sign: true, message: 'Localizado no aparelho (sem internet). O CPF será confirmado na assinatura.' }; });
        var exact = list.filter(function (p) { return norm(p.full_name) === q; });
        if (exact.length === 1) res = exact[0]; else if (list.length === 1) res = list[0];
        else if (list.length) res = { found: false, multiple: true, matches: list, message: 'Sem internet: selecione o colaborador.' };
        else res = { found: false, message: 'Nome não encontrado na lista guardada no aparelho.' };
      }
      return new Response(JSON.stringify(res), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    window.fetch = function (input, init) {
      var url = typeof input === 'string' ? input : (input && input.url) || '';
      var isLookup = /\/api\/participants\/lookup$/.test(url.split('?')[0]);
      if (isLookup && !navigator.onLine) return Promise.resolve(offlineLookup(init && init.body));
      var p = orig(input, init);
      return isLookup ? p.catch(function () { return offlineLookup(init && init.body); }) : p;
    };
  })();

  window.SafetyPlusOffline = { sync: sync, refresh: refresh, prepare: prepare, recentEdits: recentEdits, reachable: reachable, instance: instance };
  // Compatibilidade com a tela antiga do Modo Offline.
  window.safetyPlusOfflineSendNow = function () { return sync(true); };
  window.safetyPlusOfflineRefresh = refresh;

  if (location.pathname === '/login' && 'caches' in window) caches.delete(OB.PAGES_CACHE).catch(function () {});
  window.addEventListener('online', function () { lastOk = 0; sync(false); refresh(); });
  window.addEventListener('offline', function () { lastOk = 0; refresh(); });
  if (navigator.serviceWorker) navigator.serviceWorker.addEventListener('message', function (e) { if (e.data && e.data.type === 'SP_OUTBOX_SYNCED') { refresh(); if (e.data.sent) toast(e.data.sent + ' envio(s) sincronizado(s)', 'Os registros feitos sem internet chegaram ao servidor.', 'ok', 8000); } });
  function start() {
    rememberEdit();
    migrateLegacy().then(refresh).then(function () { if (navigator.onLine && userId) sync(false); });
    setTimeout(autoPrepare, 8000);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
