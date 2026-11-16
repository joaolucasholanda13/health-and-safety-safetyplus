/* Safety Plus — pedido de permissões no primeiro acesso (câmera, microfone, notificações) */
(function () {
  const SNOOZE_MS = 3 * 24 * 3600 * 1000;
  const ROWS = [
    {key: 'camera', icon: '📷', title: 'Câmera', text: 'Ler QR Code e tirar fotos para anexar nos documentos.'},
    {key: 'microphone', icon: '🎙️', title: 'Microfone', text: 'Gravar áudio e ditar observações e justificativas.'},
    {key: 'notifications', icon: '🔔', title: 'Notificações', text: 'Receber avisos de assinaturas, aprovações e pendências.'}
  ];
  let root = null;

  function uid() { return (document.body && document.body.dataset.userId) || ''; }
  function storeKey() { return 'sp-perms-v1:' + uid(); }
  function load() { try { return JSON.parse(localStorage.getItem(storeKey()) || '{}'); } catch (e) { return {}; } }
  function save(v) { try { localStorage.setItem(storeKey(), JSON.stringify(v)); } catch (e) {} }

  async function state(key) {
    if (key === 'notifications') {
      if (!('Notification' in window)) return 'unsupported';
      if (Notification.permission !== 'granted') return Notification.permission === 'default' ? 'prompt' : Notification.permission;
      try {
        const reg = await navigator.serviceWorker.getRegistration('/');
        const sub = reg && await reg.pushManager.getSubscription();
        return sub ? 'granted' : 'prompt';
      } catch (e) { return 'prompt'; }
    }
    if (!window.isSecureContext || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return 'unsupported';
    try {
      const r = await navigator.permissions.query({name: key});
      return r.state;
    } catch (e) { return 'prompt'; }
  }

  async function askMedia(constraints) {
    const s = await navigator.mediaDevices.getUserMedia(constraints);
    s.getTracks().forEach(t => t.stop());
  }

  async function ask(key) {
    if (key === 'camera') return askMedia({video: true});
    if (key === 'microphone') return askMedia({audio: true});
    if (!window.SafetyPlusNotifications) throw new Error('Notificações indisponíveis.');
    return window.SafetyPlusNotifications.enable();
  }

  function css() {
    if (document.getElementById('sp-perms-css')) return;
    const st = document.createElement('style'); st.id = 'sp-perms-css';
    st.textContent = `
.sp-perms{position:fixed;inset:0;z-index:100000;background:rgba(24,24,24,.62);display:flex;align-items:center;justify-content:center;padding:16px}
.sp-perms-card{background:#fff;border-radius:18px;max-width:460px;width:100%;max-height:92vh;overflow:auto;box-shadow:0 24px 60px rgba(0,0,0,.35);border-top:6px solid var(--serena-coral-escuro,#D23532);padding:22px}
.sp-perms-card h2{margin:0 0 4px;font-size:1.15rem}
.sp-perms-card>p{margin:0 0 14px;font-size:.88rem;line-height:1.5;color:var(--cor-texto-secundario,#6b6560)}
.sp-perm{display:flex;gap:12px;align-items:center;padding:11px 12px;border:1px solid #E8E3DC;border-radius:12px;margin-bottom:8px}
.sp-perm .ic{font-size:1.5rem;flex:0 0 32px;text-align:center}
.sp-perm .tx{flex:1;min-width:0}.sp-perm .tx b{display:block;font-size:.92rem}.sp-perm .tx span{font-size:.8rem;color:var(--cor-texto-secundario,#6b6560);line-height:1.4}
.sp-perm .tx em{display:block;font-style:normal;font-size:.76rem;color:#B42318;margin-top:3px}
.sp-chip{font-size:.72rem;font-weight:700;border-radius:999px;padding:4px 10px;white-space:nowrap;background:#F1EEE9;color:#6b6560}
.sp-chip.granted{background:#E3F4E6;color:#1F7A2E}.sp-chip.denied{background:#FDE7E5;color:#B42318}
.sp-perms-act{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}.sp-perms-act .btn{flex:1;min-width:140px}
.sp-perms-note{font-size:.74rem;color:var(--cor-texto-secundario,#6b6560);margin-top:10px;line-height:1.4}`;
    document.head.appendChild(st);
  }

  const LABEL = {granted: 'Permitido', denied: 'Bloqueado', prompt: 'Pendente', unsupported: 'Indisponível'};

  async function paint(errors) {
    for (const r of ROWS) {
      const s = await state(r.key);
      const chip = root.querySelector('[data-chip="' + r.key + '"]');
      chip.textContent = LABEL[s] || 'Pendente'; chip.className = 'sp-chip ' + s;
      const err = root.querySelector('[data-err="' + r.key + '"]');
      let msg = (errors && errors[r.key]) || '';
      if (!msg && s === 'denied') msg = 'Bloqueado no navegador. Libere em Configurações do site (ícone de cadeado).';
      if (!msg && s === 'unsupported' && r.key !== 'notifications') msg = 'Precisa de conexão segura (HTTPS) e navegador compatível.';
      err.textContent = msg;
    }
  }

  function close() { if (root) { root.remove(); root = null; } }

  async function open() {
    if (root) return;
    css();
    root = document.createElement('div'); root.className = 'sp-perms'; root.setAttribute('role', 'dialog'); root.setAttribute('aria-modal', 'true');
    root.innerHTML = '<div class="sp-perms-card"><h2>Vamos liberar os acessos do Safety Plus</h2>' +
      '<p>Para usar todos os recursos no celular ou computador, o navegador vai pedir sua permissão. Você pode alterar depois nas configurações do navegador.</p>' +
      ROWS.map(r => '<div class="sp-perm"><div class="ic">' + r.icon + '</div><div class="tx"><b>' + r.title + '</b><span>' + r.text + '</span><em data-err="' + r.key + '"></em></div><span class="sp-chip" data-chip="' + r.key + '">…</span></div>').join('') +
      '<div class="sp-perms-act"><button type="button" class="btn btn-primario" id="sp-perms-go">Permitir acessos</button><button type="button" class="btn btn-fantasma" id="sp-perms-later">Agora não</button></div>' +
      '<div class="sp-perms-note">Anexar fotos da galeria não precisa de permissão. A câmera só é usada quando você tocar em ler QR Code ou tirar foto. No iPhone/iPad, instale o app na Tela de Início para receber notificações.</div></div>';
    document.body.appendChild(root);
    await paint();
    root.querySelector('#sp-perms-later').onclick = () => { const v = load(); v.snooze = Date.now() + SNOOZE_MS; save(v); close(); };
    root.querySelector('#sp-perms-go').onclick = async function () {
      const btn = this; btn.disabled = true; btn.textContent = 'Aguardando permissões…';
      const errors = {};
      // Notificações primeiro: o navegador só aceita esse pedido logo após o toque do usuário.
      const order = [ROWS[2], ROWS[0], ROWS[1]];
      for (const r of order) {
        if (r.key === 'notifications' && 'Notification' in window && Notification.permission === 'denied') continue;
        if (r.key !== 'notifications' && (await state(r.key)) !== 'prompt') continue;
        try { await ask(r.key); } catch (e) {
          errors[r.key] = (e && e.name === 'NotFoundError') ? 'Dispositivo não encontrado.' : ((e && e.message) || 'Não foi possível ativar.');
          if (r.key === 'notifications') errors[r.key] += ' Os avisos continuam aparecendo dentro do sistema.';
        }
        await paint(errors);
      }
      await paint(errors);
      const v = load(); v.done = true; save(v);
      btn.disabled = false; btn.textContent = 'Concluir'; btn.onclick = close;
      if ((await state('notifications')) === 'granted' && window.SafetyPlusNotifications && window.SafetyPlusNotifications.test) {
        const t = document.createElement('button'); t.type = 'button'; t.className = 'btn btn-secundario'; t.textContent = 'Enviar notificação de teste';
        const msg = root.querySelector('[data-err="notifications"]');
        t.onclick = async function () {
          t.disabled = true; msg.style.color = '#6b6560'; msg.textContent = 'Enviando teste…';
          try { await window.SafetyPlusNotifications.test(); msg.style.color = '#1F7A2E'; msg.textContent = 'Teste enviado. Deve aparecer em instantes.'; }
          catch (e) { msg.style.color = '#B42318'; msg.textContent = e.message || 'Falha no teste.'; }
          t.disabled = false;
        };
        root.querySelector('.sp-perms-act').appendChild(t);
      }
      root.querySelector('#sp-perms-later').hidden = true;
    };
  }

  async function maybeOpen() {
    if (!document.body || document.body.dataset.authenticated !== '1' || !uid()) return;
    const v = load();
    if (v.done || (v.snooze && v.snooze > Date.now())) return;
    const sts = await Promise.all(ROWS.map(r => state(r.key)));
    if (!sts.includes('prompt')) { v.done = true; save(v); return; }
    open();
  }

  window.SafetyPlusPermissions = {open: open, reset: function () { try { localStorage.removeItem(storeKey()); } catch (e) {} }};
  document.addEventListener('DOMContentLoaded', function () { setTimeout(maybeOpen, 1200); });
})();
