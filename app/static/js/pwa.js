/* Safety Plus — instalação PWA + splash de aplicativo */
(function () {
  let deferredPrompt = null;

  function isStandalone() {
    return window.matchMedia('(display-mode: standalone)').matches ||
      window.matchMedia('(display-mode: fullscreen)').matches ||
      window.navigator.standalone === true;
  }

  function detectBrowser() {
    const ua = navigator.userAgent || '';
    if (/Edg\//i.test(ua) || /EdgA|EdgiOS/i.test(ua)) return 'edge';
    if (/OPR\/|Opera/i.test(ua)) return 'opera';
    if (/SamsungBrowser/i.test(ua)) return 'samsung';
    if (/Firefox|FxiOS/i.test(ua)) return 'firefox';
    if (/Chrome|CriOS|Chromium/i.test(ua)) return 'chrome';
    if (/Safari/i.test(ua)) return 'safari';
    return 'other';
  }
  function detectPlatform() {
    const ua = navigator.userAgent || '';
    if (/iPad/i.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)) return 'ipad';
    if (/iPhone|iPod/i.test(ua)) return 'iphone';
    if (/Android/i.test(ua)) return 'android';
    return 'pc';
  }

  // Instruções para a plataforma escolhida (botões PC / Android / iPhone / iPad) no navegador em uso
  function platformHint(plat) {
    plat = plat || detectPlatform();
    const br = detectBrowser();
    const cur = detectPlatform();
    const same = plat === cur;
    if (plat === 'iphone' || plat === 'ipad') {
      const dev = plat === 'ipad' ? 'iPad' : 'iPhone';
      if (same && br !== 'safari') return 'No ' + dev + ' a instalação é feita pelo Safari: abra este mesmo endereço no Safari, toque em Compartilhar (quadrado com seta) e depois em “Adicionar à Tela de Início”. (Chrome e Edge recentes também têm Compartilhar → “Adicionar à Tela de Início”.)';
      return 'No ' + dev + ' (Safari): toque em Compartilhar (quadrado com seta para cima), role a lista e escolha “Adicionar à Tela de Início” e depois “Adicionar”.';
    }
    if (plat === 'android') {
      if (same && br === 'firefox') return 'No Firefox do Android: toque no menu (⋮) e escolha “Instalar” (ou “Adicionar à tela inicial”).';
      if (same && br === 'samsung') return 'No Samsung Internet: toque no menu (☰) e escolha “Adicionar página a” → “Tela inicial” (ou “Instalar aplicativo”, quando aparecer).';
      if (same && br === 'edge') return 'No Edge do Android: toque no menu (⋯) e escolha “Adicionar ao telefone” / “Instalar aplicativo”.';
      return 'No Chrome do Android: toque no menu (⋮) e escolha “Instalar aplicativo” (ou “Adicionar à tela inicial”).';
    }
    // PC
    if (same && br === 'firefox') return 'O Firefox no computador não instala aplicativos. Use o Chrome ou o Edge para instalar, ou continue usando o Safety Plus normalmente no navegador (dica: fixe a aba).';
    if (same && br === 'safari') return 'No Safari (Mac): menu Arquivo → “Adicionar ao Dock”.';
    if (same && br === 'edge') return 'No Edge: clique no menu (⋯) → Aplicativos → “Instalar este site como um aplicativo” (ou no ícone de instalação na barra de endereço).';
    return 'No Chrome / Edge / Opera: clique no ícone de instalação (monitor com seta) na barra de endereço, ou no menu (⋮) → “Instalar Safety Plus” / “Salvar e compartilhar” → “Instalar página como aplicativo”.';
  }

  function ensureInstallModal() {
    let modal = document.getElementById('pwa-install-modal');
    if (modal) return modal;
    modal = document.createElement('div');
    modal.id = 'pwa-install-modal';
    modal.innerHTML = `
      <div class="pwa-modal-backdrop" data-close-pwa></div>
      <div class="pwa-modal-card" role="dialog" aria-modal="true" aria-labelledby="pwa-title">
        <div class="pwa-logo"><img src="/static/icons/safety-plus-icon-192-v361831.png" alt=""></div>
        <h3 id="pwa-title">Instalar Safety Plus</h3>
        <p id="pwa-install-text"></p>
        <div class="pwa-modal-actions">
          <button type="button" class="btn btn-secundario" data-close-pwa>Fechar</button>
          <button type="button" class="btn btn-primario" id="pwa-modal-install" style="display:none">Instalar agora</button>
        </div>
      </div>`;
    const style = document.createElement('style');
    style.textContent = `
      #pwa-install-modal{position:fixed;inset:0;z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px}
      #pwa-install-modal[hidden]{display:none}
      .pwa-modal-backdrop{position:absolute;inset:0;background:rgba(0,0,0,.48)}
      .pwa-modal-card{position:relative;background:#fff;border-radius:18px;padding:24px;max-width:420px;width:100%;box-shadow:0 24px 70px rgba(0,0,0,.24);text-align:center}
      .pwa-modal-card h3{margin:10px 0 8px;font-size:1.18rem}.pwa-modal-card p{color:#666;line-height:1.45;font-size:.9rem}
      .pwa-logo img{width:72px;height:72px;border-radius:18px}.pwa-modal-actions{display:flex;justify-content:flex-end;gap:10px;margin-top:18px}
      .pwa-install-link{border:0;background:none;color:inherit;font:inherit;cursor:pointer;text-align:left;width:100%}
      .pwa-splash{position:fixed;inset:0;z-index:10000;background:#FF5246;display:flex;align-items:center;justify-content:center;flex-direction:column;color:white;transition:opacity .28s ease}
      .pwa-splash img{width:112px;height:112px;border-radius:28px;box-shadow:0 14px 36px rgba(0,0,0,.14)}
      .pwa-splash strong{font:700 1.55rem/1.2 system-ui,-apple-system,"Segoe UI",sans-serif;margin-top:18px}.pwa-splash span{font:500 .85rem/1.2 system-ui,-apple-system,"Segoe UI",sans-serif;opacity:.86;margin-top:4px}
    `;
    document.head.appendChild(style);
    document.body.appendChild(modal);
    modal.querySelectorAll('[data-close-pwa]').forEach(el => el.addEventListener('click', () => modal.hidden = true));
    modal.hidden = true;
    return modal;
  }

  async function installSafetyPlus(plat) {
    if (isStandalone()) return;
    // Instalação direta só quando a plataforma escolhida é a do dispositivo atual
    if (deferredPrompt && (!plat || plat === detectPlatform())) {
      const prompt = deferredPrompt;
      deferredPrompt = null;
      await prompt.prompt();
      try { await prompt.userChoice; } catch (e) {}
      refreshInstallButtons();
      return;
    }
    const modal = ensureInstallModal();
    modal.querySelector('#pwa-install-text').textContent = platformHint(plat);
    modal.querySelector('#pwa-modal-install').style.display = 'none';
    modal.hidden = false;
  }

  function refreshInstallButtons() {
    document.querySelectorAll('.pwa-install-action').forEach(btn => {
      btn.style.display = isStandalone() ? 'none' : '';
    });
  }

  function showSplash() {
    if (!isStandalone()) return;
    try { if (sessionStorage.getItem('safetyplus-splash-shown')) return; sessionStorage.setItem('safetyplus-splash-shown','1'); } catch (e) {}
    const splash = document.createElement('div');
    splash.className = 'pwa-splash';
    splash.innerHTML = '<img src="/static/icons/safety-plus-icon-192-v361831.png" alt=""><strong>Safety Plus</strong><span>Serena</span>';
    document.body.appendChild(splash);
    setTimeout(() => { splash.style.opacity='0'; setTimeout(() => splash.remove(), 300); }, 850);
  }

  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault();
    deferredPrompt = event;
    refreshInstallButtons();
  });
  window.addEventListener('appinstalled', () => { deferredPrompt = null; refreshInstallButtons(); });
  window.installSafetyPlus = installSafetyPlus;

  document.addEventListener('DOMContentLoaded', () => {
    refreshInstallButtons();
    showSplash();
    if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js', { updateViaCache: 'none' }).then((reg) => reg.update()).catch(() => {});
  });
})();
