/* Safety Plus — núcleo offline (V36.18.95)
   Compartilhado entre as páginas e o Service Worker (importScripts).
   Fila de envio (outbox) em IndexedDB, histórico de envios e sincronização
   conservadora: só remove da fila depois de confirmar o resultado no servidor. */
(function (root) {
  'use strict';
  var DB_NAME = 'safetyplus-outbox', DB_VERSION = 1;
  var PAGES_CACHE = 'sp-pages-v3', STATIC_CACHE = 'sp-static-v7';
  var HISTORY_LIMIT = 40;
  // APR e PT têm etapas com horário do servidor, assinaturas e aprovação:
  // offline elas sempre sincronizam como RASCUNHO. RAC e inspeções enviam a ação escolhida.
  var DRAFT_ONLY = /^\/(apr|permit)\/(?!offline-bundle)/;
  var SAVE_RE = /^\/(apr|vehicle|permit\/[^\/]+|rac\/[^\/]+|inspection\/[^\/]+)(\/\d+)?\/save$/;

  function openDb() {
    return new Promise(function (resolve, reject) {
      if (!root.indexedDB) { reject(new Error('IndexedDB indisponível neste navegador.')); return; }
      var req = root.indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = function () {
        var db = req.result;
        if (!db.objectStoreNames.contains('outbox')) db.createObjectStore('outbox', { keyPath: 'id' });
        if (!db.objectStoreNames.contains('history')) db.createObjectStore('history', { keyPath: 'hid', autoIncrement: true });
        if (!db.objectStoreNames.contains('map')) db.createObjectStore('map', { keyPath: 'instance' });
      };
      req.onsuccess = function () { resolve(req.result); };
      req.onerror = function () { reject(req.error); };
    });
  }
  function run(store, mode, fn) {
    return openDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(store, mode), out;
        try { out = fn(tx.objectStore(store)); } catch (e) { reject(e); return; }
        tx.oncomplete = function () { db.close(); resolve(out && 'result' in out ? out.result : undefined); };
        tx.onerror = function () { db.close(); reject(tx.error); };
        tx.onabort = function () { db.close(); reject(tx.error); };
      });
    });
  }
  var api = {
    SAVE_RE: SAVE_RE, DRAFT_ONLY: DRAFT_ONLY, PAGES_CACHE: PAGES_CACHE, STATIC_CACHE: STATIC_CACHE,
    put: function (item) { return run('outbox', 'readwrite', function (s) { return s.put(item); }); },
    get: function (id) { return run('outbox', 'readonly', function (s) { return s.get(id); }); },
    remove: function (id) { return run('outbox', 'readwrite', function (s) { return s.delete(id); }); },
    list: function () { return run('outbox', 'readonly', function (s) { return s.getAll(); }).then(function (r) { return (r || []).sort(function (a, b) { return String(a.created_at).localeCompare(String(b.created_at)); }); }); },
    history: function () { return run('history', 'readonly', function (s) { return s.getAll(); }).then(function (r) { return (r || []).reverse(); }); },
    clearHistory: function () { return run('history', 'readwrite', function (s) { return s.clear(); }); },
    addHistory: function (h) {
      return run('history', 'readwrite', function (s) { return s.add(h); }).then(function () {
        return run('history', 'readwrite', function (s) {
          var req = s.getAllKeys();
          req.onsuccess = function () { var keys = req.result || []; keys.slice(0, Math.max(0, keys.length - HISTORY_LIMIT)).forEach(function (k) { s.delete(k); }); };
          return req;
        });
      });
    },
    getMap: function (instance) { return run('map', 'readonly', function (s) { return s.get(instance); }); },
    setMap: function (instance, saveUrl) { return run('map', 'readwrite', function (s) { return s.put({ instance: instance, save: saveUrl, at: new Date().toISOString() }); }); }
  };

  function decode(t) {
    return String(t || '').replace(/&#39;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&').replace(/\s+/g, ' ').trim();
  }
  function flashes(html) {
    var out = [], re = /class="flash flash-(\w+)"[^>]*>([\s\S]*?)<\/div>/g, m;
    while ((m = re.exec(html))) out.push({ level: m[1], message: decode(m[2].replace(/<[^>]+>/g, '')) });
    return out;
  }
  function docIdFrom(path) { var m = /\/(\d+)\/(edit|pdf|pts|assinar|aprovar)\b/.exec(path) || /^\/document\/(\d+)/.exec(path); return m ? m[1] : ''; }
  function editUrlFor(item, finalPath) {
    if (/\/edit$/.test(finalPath) || /^\/document\//.test(finalPath)) return finalPath;
    return finalPath;
  }

  function syncToken() {
    return fetch('/api/offline/sync-token', { credentials: 'same-origin', cache: 'no-store' }).then(function (r) {
      if (r.status === 401 || r.redirected) return { login: true };
      if (!r.ok) throw new Error('Servidor indisponível (' + r.status + ').');
      return r.json();
    });
  }

  function csrfFailure(text) {
    return /token inv|csrf/i.test(String(text || ''));
  }

  var flushing = null;
  // Envia a fila. Retorna {sent, attention, pending, login, otherUser, error}.
  api.flush = function (opts) {
    opts = opts || {};
    if (flushing) return flushing;
    var result = { sent: 0, attention: 0, pending: 0, login: false, otherUser: 0, error: '' };
    flushing = api.list().then(function (items) {
      var queue = items.filter(function (i) {
        // Versões anteriores colocavam sessão expirada em revisão permanente.
        return i.status !== 'attention' || opts.includeAttention ||
          (String(i.error || '').indexOf('O servidor recusou o envio (sessão ou permissão)') === 0 && csrfFailure(i.error)) ||
          /formulário chegou incompleto ao servidor/i.test(String(i.error || ''));
      });
      if (opts.only) queue = queue.filter(function (i) { return i.id === opts.only; });
      if (!queue.length) return result;
      return syncToken().then(function (tok) {
        if (tok.login) { result.login = true; return; }
        var chain = Promise.resolve(), stop = false;
        queue.forEach(function (item) {
          chain = chain.then(function () {
            if (stop) return;
            if (item.user_id && tok.user_id && String(item.user_id) !== String(tok.user_id)) { result.otherUser++; return; }
            return api.getMap(item.instance).catch(function () { return null; }).then(function (map) {
              var target = (map && map.save && !/\/\d+\/save$/.test(item.action)) ? map.save : item.action;
              var fd = new FormData();
              fd.append('csrf_token', tok.csrf_token);  // primeiro campo: nunca se perde em envios grandes
              (item.entries || []).forEach(function (p) {
                if (p[0] === 'csrf_token') return;
                if (p[0] === 'action' && DRAFT_ONLY.test(item.action)) return;
                fd.append(p[0], p[1]);
              });
              if (DRAFT_ONLY.test(item.action)) fd.append('action', 'draft');
              var ctrl = ('AbortController' in self) ? new AbortController() : null, tmo = ctrl ? setTimeout(function () { ctrl.abort(); }, 120000) : null;
              // Sem anexos reais, usa a mesma codificação do formulário HTML.
              // Evita o parser multipart para checklists e assinaturas em texto.
              // Campos repetidos e arquivos vazios mantêm a mesma contagem.
              var doPost = function () {
                var hasFiles = false;
                fd.forEach(function (value) {
                  if (typeof value !== 'string' && (value.size > 0 || value.name)) hasFiles = true;
                });
                var body = fd;
                if (!hasFiles) {
                  body = new URLSearchParams();
                  fd.forEach(function (value, key) { body.append(key, typeof value === 'string' ? value : ''); });
                }
                return fetch(target, { method: 'POST', body: body, credentials: 'same-origin', redirect: 'follow', headers: { 'X-SP-Offline-Sync': '1', 'X-CSRF-Token': fd.get('csrf_token'), 'X-SP-Offline-Field-Count': String(Array.from(fd.keys()).filter(function (key) { return key !== 'csrf_token'; }).length) }, signal: ctrl ? ctrl.signal : undefined }); };
              return doPost()
                .then(function (r) {
                  if (r.status !== 403) return r;
                  // 403 por token: busca um token novo e tenta uma vez mais.
                  return r.clone().text().then(function (t) {
                    if (!csrfFailure(t)) return r;
                    return syncToken().then(function (t2) {
                      if (!t2 || t2.login) { result.login = true; return r; }
                      if (!t2.csrf_token) return r;
                      if (item.user_id && String(item.user_id) !== String(t2.user_id)) {
                        result.otherUser++; stop = true;
                        throw new Error('A conta conectada mudou durante o envio. Entre com a conta que criou o registro.');
                      }
                      tok = t2;
                      fd.set('csrf_token', t2.csrf_token);
                      return doPost();
                    }, function () { return r; });
                  }, function () { return r; });
                })
                .then(function (r) { if (tmo) clearTimeout(tmo); return r; }, function (e) { if (tmo) clearTimeout(tmo); if (e && e.name === 'AbortError') throw new Error('tempo esgotado: o servidor não respondeu em 2 minutos (sinal fraco ou anexos grandes)'); throw e; })
                .then(function (r) {
                  var finalPath = ''; try { finalPath = new URL(r.url).pathname; } catch (e) {}
                  if (finalPath.indexOf('/login') === 0 || r.status === 401) { stop = true; result.login = true; return; }
                  if (r.status === 403) {
                    return r.text().then(function (t) { return t; }, function () { return ''; }).then(function (t) {
                      var why = '';
                      try { var j = JSON.parse(t); why = j.detail || j.message || ''; } catch (e) { why = decode(String(t || '').replace(/<style[\s\S]*?<\/style>|<script[\s\S]*?<\/script>/gi, '').replace(/<[^>]+>/g, ' ')).slice(0, 220); }
                      if (result.login || csrfFailure(why)) {
                        stop = true; result.pending++;
                        item.status = 'pending'; item.attempts = (item.attempts || 0) + 1;
                        item.error = 'Não foi possível renovar a sessão' + (why ? ': ' + String(why).slice(0, 300) : '.') + ' Faça login novamente com a conta que criou este registro e tente enviar. Os dados continuam guardados no aparelho.';
                        result.error = item.error;
                        return api.put(item);
                      }
                      item.entries = (item.entries || []).filter(function (p) { return p[0] !== 'offline_leader_password'; });
                      item.status = 'attention';
                      item.error = 'O servidor recusou o envio (sessão ou permissão)' + (why ? ': ' + why : '') + ' [alvo: ' + target + ']. Abra o formulário online e confira.';
                      result.attention++; return api.put(item);
                    });
                  }
                  if (!r.ok) {
                    return r.text().then(function (body) {
                      var detail = '';
                      try {
                        var payload = JSON.parse(body);
                        if (typeof payload.detail === 'string') detail = payload.detail;
                        else if (typeof payload.message === 'string') detail = payload.message;
                      } catch (e) {}
                      var review = [400, 404, 405, 413, 422].indexOf(r.status) >= 0;
                      item.attempts = (item.attempts || 0) + 1;
                      item.error = 'Servidor respondeu ' + r.status + (detail ? ': ' + detail.slice(0, 300) : '.') +
                        (review ? ' Revise o registro antes de reenviar.' : ' Nova tentativa automática.');
                      item.status = review ? 'attention' : 'pending';
                      if (review) result.attention++; else result.pending++;
                      result.error = item.error;
                      return api.put(item);
                    });
                  }
                  return r.text().then(function (html) {
                    var fl = flashes(html), err = fl.filter(function (f) { return f.level === 'error'; });
                    var id = docIdFrom(finalPath), saveUrl = '';
                    if (id && !/\/\d+\/save$/.test(item.action)) saveUrl = item.action.replace(/\/save$/, '/' + id + '/save');
                    var p = saveUrl ? api.setMap(item.instance, saveUrl) : Promise.resolve();
                    return p.then(function () {
                      if (err.length) {
                        item.entries = (item.entries || []).filter(function (p) { return p[0] !== 'offline_leader_password'; });
                        item.status = 'attention'; item.error = err.map(function (f) { return f.message; }).join(' ');
                        item.result_url = editUrlFor(item, finalPath); item.synced_at = new Date().toISOString();
                        result.attention++;
                        return api.put(item);
                      }
                      var ok = fl.filter(function (f) { return f.level !== 'error'; }).map(function (f) { return f.message; }).join(' ');
                      result.sent++;
                      return api.addHistory({ title: item.title, kind: item.kind_label || '', action: item.action, url: finalPath, message: ok || (DRAFT_ONLY.test(item.action) ? 'Salvo no servidor como rascunho.' : 'Enviado ao servidor.'), draft_only: DRAFT_ONLY.test(item.action), captured_at: item.created_at, synced_at: new Date().toISOString() })
                        .then(function () { return api.remove(item.id); });
                    });
                  });
                })
                .catch(function (e) {
                  stop = true; result.pending++;
                  var why = (e && (e.message || e.name)) ? String(e.message || e.name) : '';
                  result.error = navigator.onLine === false ? 'Sem conexão com o servidor.' : 'Falha ao enviar' + (why ? ' (' + why + ')' : '') + '.';
                  item.attempts = (item.attempts || 0) + 1; item.error = result.error + ' Toque em Enviar para tentar de novo.';
                  return api.put(item).catch(function () {});
                });
            });
          });
        });
        return chain;
      }).catch(function (e) { result.error = e.message || 'Falha de conexão.'; });
    }).then(function () { flushing = null; return result; }, function (e) { flushing = null; result.error = e.message; return result; });
    return flushing;
  };

  root.SafetyPlusOutbox = api;
})(typeof self !== 'undefined' ? self : this);
