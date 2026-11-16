/* Safety Plus — notificações no navegador/celular (Web Push + fallback em tela) */
(function () {
  const POLL_MS = 15000;
  const seenPrefix = 'safetyplus-notification-seen:';

  function csrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : '';
  }

  function isAuthenticated() {
    return document.body && document.body.dataset.authenticated === '1';
  }

  function isStandalone() {
    return window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
  }

  function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = atob(base64);
    return Uint8Array.from([...rawData].map(ch => ch.charCodeAt(0)));
  }

  async function getRegistration() {
    if (!('serviceWorker' in navigator)) throw new Error('Este navegador não oferece Service Worker.');
    let reg = await navigator.serviceWorker.getRegistration('/');
    if (!reg) reg = await navigator.serviceWorker.register('/sw.js');
    await navigator.serviceWorker.ready;
    return reg;
  }

  async function pushStatus() {
    const result = {
      supported: ('Notification' in window) && ('serviceWorker' in navigator) && ('PushManager' in window),
      permission: ('Notification' in window) ? Notification.permission : 'unsupported',
      subscribed: false,
      backendAvailable: null,
      serverDevices: 0,
      standalone: isStandalone(),
      ios: /iPhone|iPad|iPod/i.test(navigator.userAgent || '')
    };
    if (!result.supported) return result;
    try {
      const reg = await getRegistration();
      result.subscribed = !!(await reg.pushManager.getSubscription());
    } catch (e) {}
    try {
      const resp = await fetch('/api/notifications/push/status', {credentials:'same-origin', cache:'no-store'});
      if (resp.ok) {
        const server = await resp.json();
        result.backendAvailable = server.backend_available !== false;
        result.serverDevices = server.devices || 0;
      }
    } catch (e) {}
    return result;
  }

  async function saveSubscriptionForCurrentUser(sub) {
    if (!sub || !isAuthenticated()) return false;
    const saveResp = await fetch('/api/notifications/push/subscribe', {
      method: 'POST',
      credentials: 'same-origin',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({csrf_token: csrfToken(), subscription: sub.toJSON()})
    });
    const saved = await saveResp.json().catch(() => ({}));
    if (!saveResp.ok || !saved.ok) throw new Error(saved.detail || saved.message || 'Não foi possível registrar este celular.');
    return true;
  }

  async function syncExistingSubscription() {
    if (!isAuthenticated() || !('Notification' in window) || Notification.permission !== 'granted' || !('PushManager' in window)) return;
    try {
      const reg = await getRegistration();
      const sub = await reg.pushManager.getSubscription();
      if (sub) await saveSubscriptionForCurrentUser(sub);
    } catch (e) {}
  }

  async function enablePushNotifications() {
    if (!isAuthenticated()) throw new Error('Entre novamente no Safety Plus.');
    if (!('Notification' in window) || !('serviceWorker' in navigator) || !('PushManager' in window)) {
      throw new Error('Este navegador não suporta notificações push.');
    }
    const ios = /iPhone|iPad|iPod/i.test(navigator.userAgent || '');
    if (ios && !isStandalone()) {
      throw new Error('No iPhone/iPad, instale o Safety Plus na Tela de Início e abra pelo ícone antes de ativar as notificações.');
    }
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') {
      throw new Error('A permissão de notificações não foi concedida.');
    }
    const keyResp = await fetch('/api/notifications/push/public-key', {credentials:'same-origin', cache:'no-store'});
    if (!keyResp.ok) throw new Error('Não foi possível obter a chave de notificações do servidor.');
    const keyData = await keyResp.json();
    if (!keyData.public_key) throw new Error('Notificações push ainda não estão configuradas no servidor.');
    if (keyData.backend_available === false) throw new Error('O módulo de envio push ainda não está instalado no servidor. Atualize as dependências do Safety Plus.');
    let reg;
    try { reg = await getRegistration(); }
    catch (e) { throw new Error('Etapa Service Worker: ' + (e.message || e) + ' (o site precisa estar em HTTPS).'); }
    let sub = await reg.pushManager.getSubscription();
    if (!sub) {
      try {
        sub = await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(keyData.public_key)
        });
      } catch (e) {
        if (e && e.name === 'AbortError') throw new Error('O serviço de push do navegador recusou o cadastro (comum no Brave, em modo anônimo ou sem serviços do Google). Use Chrome, Edge ou Firefox normais.');
        if (e && e.name === 'NotAllowedError') throw new Error('O navegador bloqueou o cadastro de push. Libere as notificações do site no cadeado.');
        throw new Error('Etapa inscrição push: ' + ((e && e.message) || e));
      }
    }
    try { await saveSubscriptionForCurrentUser(sub); }
    catch (e) { throw new Error('Etapa registro no servidor: ' + ((e && e.message) || e)); }
    return await pushStatus();
  }

  async function disablePushNotifications() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return await pushStatus();
    const reg = await getRegistration();
    const sub = await reg.pushManager.getSubscription();
    if (sub) {
      try {
        await fetch('/api/notifications/push/unsubscribe', {
          method: 'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({csrf_token: csrfToken(), endpoint: sub.endpoint})
        });
      } catch (e) {}
      try { await sub.unsubscribe(); } catch (e) {}
    }
    return await pushStatus();
  }

  function markLocalSeen(id) {
    try { localStorage.setItem(seenPrefix + id, '1'); } catch (e) {}
  }
  function wasLocalSeen(id) {
    try { return localStorage.getItem(seenPrefix + id) === '1'; } catch (e) { return false; }
  }

  async function showForegroundNotification(item) {
    if (!item || !item.id || wasLocalSeen(item.id)) return;
    markLocalSeen(item.id);
    if (!('Notification' in window) || Notification.permission !== 'granted' || document.visibilityState !== 'visible') return;
    try {
      const reg = await getRegistration();
      await reg.showNotification(item.title || 'Safety Plus', {
        body: item.message || '',
        icon: '/static/icons/safety-plus-icon-192-v361831.png',
        badge: '/static/icons/safety-plus-favicon-64-v361831.png',
        tag: item.tag || ('safety-plus-notification-' + item.id),
        data: {url: item.url || '/notifications', notification_id: item.id}
      });
    } catch (e) {}
  }

  async function pollUnread() {
    if (!isAuthenticated() || document.visibilityState === 'hidden') return;
    try {
      const resp = await fetch('/api/notifications/unread?limit=10', {credentials:'same-origin', cache:'no-store'});
      if (!resp.ok) return;
      const data = await resp.json();
      const bell = document.querySelector('.bell');
      if (bell) {
        let dot = bell.querySelector('.dot');
        if ((data.count || 0) > 0 && !dot) {
          dot = document.createElement('span'); dot.className = 'dot'; bell.appendChild(dot);
        } else if (!(data.count || 0) && dot) dot.remove();
      }
      const items = Array.isArray(data.items) ? data.items : [];
      for (const item of items.reverse()) await showForegroundNotification(item);
    } catch (e) {}
  }

  async function sendTestNotification() {
    const resp = await fetch('/api/notifications/push/test', {method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({csrf_token: csrfToken()})});
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) throw new Error(data.detail || 'Não foi possível enviar o teste.');
    return data;
  }

  window.SafetyPlusNotifications = {test: sendTestNotification, status: pushStatus, enable: enablePushNotifications, disable: disablePushNotifications, poll: pollUnread};

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.addEventListener('message', function (event) {
      const data = event.data || {};
      if (data.type === 'PUSH_DELIVERED' && data.notification_id) markLocalSeen(data.notification_id);
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    if (!isAuthenticated()) return;
    setTimeout(pollUnread, 2500);
    setTimeout(syncExistingSubscription, 1200);
    setInterval(pollUnread, POLL_MS);
    document.addEventListener('visibilitychange', function () { if (document.visibilityState === 'visible') pollUnread(); });
  });
})();
