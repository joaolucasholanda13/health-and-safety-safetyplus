/* Safety Plus — Service Worker (V36.18.95)
   - Formulários novos preparados e rascunhos abertos recentemente disponíveis sem internet.
   - Arquivos estáticos do app guardados no aparelho (o app abre com visual completo offline).
   - Background Sync: envia a fila do aparelho quando a conexão volta, mesmo com a aba fechada (Chrome/Android). */
importScripts('/static/js/offline-core.js?v=361919');
const PAGES_CACHE = 'sp-pages-v3', APP_VERSION = '__APP_VERSION__', STATIC_CACHE = 'sp-static-' + APP_VERSION;
const OFFLINE_HOME = '/offline';
const OLD_CACHES = ['sp-pages-v1','sp-pages-v2','sp-static-v1','sp-static-v2','sp-static-v3','sp-static-v4','sp-static-v5','sp-static-v6','sp-static-v7','sp-static-v8'];
const SHELL = [
  '/offline', '/static/offline.html', '/static/css/serena-tokens.css?v=361895', '/static/css/serena-admin.css?v=361895',
  '/static/fonts/Serena-Variable.woff2', '/static/js/offline-core.js?v=361919', '/static/js/offline-sync.js?v=361920',
  '/static/js/offline-drafts.js?v=361895', '/static/js/offline-center.js?v=361918', '/static/js/offline-apr.js?v=361901', '/static/js/pwa.js?v=' + APP_VERSION, '/static/js/sigsmooth.js?v=' + APP_VERSION, '/static/js/notifications-push.js?v=' + APP_VERSION, '/static/js/permissions-onboarding.js?v=' + APP_VERSION, '/static/js/app-updates.js?v=' + APP_VERSION,
  '/static/icons/safety-plus-icon-192-v361831.png', '/static/icons/safety-plus-favicon-64-v361831.png'
];
const EDIT_PAGE = /^\/(apr\/\d+\/edit|vehicle\/\d+\/edit|(?:permit|rac|inspection)\/[^/]+\/\d+\/edit)$/;
const NEW_PAGE = /^\/(apr\/new|vehicle\/new|(?:permit|rac|inspection)\/[^/]+\/new)$/;
const MAX_EDIT_PAGES = 30;

self.addEventListener('install', (event) => event.waitUntil((async () => {
  const cache = await caches.open(STATIC_CACHE);
  // Cada item é tentado separadamente: um arquivo indisponível não impede a instalação.
  await Promise.all(SHELL.map((u) => cache.add(new Request(u, { credentials: 'same-origin', cache: 'reload' })).catch(() => {})));
  await self.skipWaiting();
})()));

self.addEventListener('activate', (event) => event.waitUntil((async () => {
  const keys = await caches.keys();
  // Reaproveita arquivos estáticos da versão anterior antes de apagá-la.
  const prevs = keys.filter((k) => k.startsWith('sp-static-') && k !== STATIC_CACHE);
  for (const prev of prevs) {
    try {
      const from = await caches.open(prev), to = await caches.open(STATIC_CACHE);
      for (const req of await from.keys()) { if (!(await to.match(req))) { const r = await from.match(req); if (r) await to.put(req, r); } }
    } catch (e) {}
  }
  await Promise.all(keys.filter((k) => OLD_CACHES.includes(k) || prevs.includes(k)).map((k) => caches.delete(k)));
  await self.clients.claim();
})()));

// ---------------- Notificações push (inalterado) ----------------
self.addEventListener('push', (event) => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; }
  catch (e) { try { data = { body: event.data ? event.data.text() : '' }; } catch (_) { data = {}; } }
  const title = data.title || 'Safety Plus';
  const options = {
    body: data.body || data.message || '',
    icon: data.icon || '/static/icons/safety-plus-icon-192-v361831.png',
    badge: data.badge || '/static/icons/safety-plus-favicon-64-v361831.png',
    tag: data.tag || 'safety-plus-notification',
    renotify: true,
    data: { url: data.url || '/notifications', notification_id: data.notification_id || null }
  };
  event.waitUntil((async () => {
    await self.registration.showNotification(title, options);
    try {
      const openClients = await clients.matchAll({ type: 'window', includeUncontrolled: true });
      for (const client of openClients) client.postMessage({ type: 'PUSH_DELIVERED', notification_id: data.notification_id || null });
    } catch (e) {}
  })());
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const raw = (event.notification.data && event.notification.data.url) || '/notifications';
  const target = new URL(raw, self.location.origin).href;
  event.waitUntil((async () => {
    const clientsList = await clients.matchAll({ type: 'window', includeUncontrolled: true });
    for (const client of clientsList) {
      try {
        if ('focus' in client) {
          if ('navigate' in client) await client.navigate(target);
          await client.focus();
          return;
        }
      } catch (e) {}
    }
    if (clients.openWindow) await clients.openWindow(target);
  })());
});

// ---------------- Envio da fila em segundo plano ----------------
async function flushOutbox() {
  if (!self.SafetyPlusOutbox) return;
  const r = await self.SafetyPlusOutbox.flush({});
  try {
    const list = await clients.matchAll({ type: 'window', includeUncontrolled: true });
    for (const c of list) c.postMessage({ type: 'SP_OUTBOX_SYNCED', sent: r.sent, attention: r.attention, login: r.login });
  } catch (e) {}
  if (r.pending && !r.login) throw new Error('Ainda há envios pendentes');  // o navegador tenta de novo depois
}
self.addEventListener('sync', (event) => { if (event.tag === 'sp-outbox-sync') event.waitUntil(flushOutbox()); });
self.addEventListener('message', (event) => { if (event.data && event.data.type === 'SP_FLUSH_OUTBOX') event.waitUntil(flushOutbox().catch(() => {})); });

async function trimEditPages(cache) {
  const keys = (await cache.keys()).filter((k) => EDIT_PAGE.test(new URL(k.url).pathname));
  for (const k of keys.slice(0, Math.max(0, keys.length - MAX_EDIT_PAGES))) await cache.delete(k);
}

// ---------------- Requisições ----------------
self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  let url;
  try { url = new URL(req.url); } catch (e) { return; }
  if (url.origin !== self.location.origin) return;

  // Formulários novos e rascunhos abertos: rede primeiro, cópia local sem internet.
  // Nunca guarda PDFs, assinaturas públicas, login ou respostas de API.
  const isNew = NEW_PAGE.test(url.pathname), isEdit = EDIT_PAGE.test(url.pathname);
  if (req.mode === 'navigate' && (isNew || isEdit)) {
    event.respondWith((async () => {
      try {
        const res = await fetch(req);
        if (res.ok && !res.redirected && (res.headers.get('content-type') || '').includes('text/html')) {
          const cache = await caches.open(PAGES_CACHE);
          const key = new Request(url.pathname);
          await cache.put(key, res.clone()).catch(() => {});
          if (isEdit) trimEditPages(cache).catch(() => {});
        }
        return res;
      } catch (e) {
        const cache = await caches.open(PAGES_CACHE);
        return (await cache.match(url.pathname, { ignoreSearch: true })) ||
          (await caches.match(OFFLINE_HOME, { ignoreSearch: true })) || new Response('Sem conexão', { status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
      }
    })());
    return;
  }

  // Demais páginas sem internet: Central Offline.
  if (req.mode === 'navigate' && !url.pathname.startsWith('/login')) {
    event.respondWith(fetch(req).catch(async () =>
      (await caches.match(OFFLINE_HOME, { ignoreSearch: true })) ||
      (await caches.match('/static/offline.html', { ignoreSearch: true })) ||
      new Response('Sem conexão', { status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8' } })));
    return;
  }

  // O código da fila precisa da versão atual antes de reenviar documentos.
  // Uma cópia antiga pode continuar recusando tokens mesmo após recarregar.
  if (/^\/static\/js\/(?:offline-[a-z-]+|pwa)\.js$/.test(url.pathname)) {
    event.respondWith((async () => {
      const cache = await caches.open(STATIC_CACHE);
      try {
        const res = await fetch(new Request(req, { cache: 'no-store' }));
        if (res.ok) {
          await cache.put(req, res.clone()).catch(() => {});
          return res;
        }
      } catch (e) {}
      return (await cache.match(req)) || (await cache.match(req, { ignoreSearch: true })) ||
        (await caches.match(req, { ignoreSearch: true })) || new Response('', { status: 504 });
    })());
    return;
  }

  // Arquivos estáticos: cópia local imediata e atualização em segundo plano.
  // Se a versão (?v=) não estiver guardada, usa a mesma URL com outra versão.
  if (url.pathname.startsWith('/static/')) {
    event.respondWith((async () => {
      const cache = await caches.open(STATIC_CACHE);
      const cached = (await cache.match(req)) || null;
      const network = fetch(req).then((res) => { if (res && res.status === 200) cache.put(req, res.clone()).catch(() => {}); return res; }).catch(() => null);
      if (cached) { event.waitUntil(network); return cached; }
      const res = await network;
      if (res) return res;
      return (await cache.match(req, { ignoreSearch: true })) || (await caches.match(req, { ignoreSearch: true })) || new Response('', { status: 504 });
    })());
  }
});
