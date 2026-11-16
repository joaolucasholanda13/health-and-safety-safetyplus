/* Safety Plus — aviso de nova versão e janela "O que há de novo" */
(function () {
  const POLL_MS = 2 * 60 * 1000;
  let banner = null, dismissed = false, mBar = null, mTimer = null, mData = null;

  function current() { return (document.body && document.body.dataset.appVersion) || ''; }
  function uid() { return (document.body && document.body.dataset.userId) || ''; }
  function authed() { return document.body && document.body.dataset.authenticated === '1'; }

  function css() {
    if (document.getElementById('sp-upd-css')) return;
    const st = document.createElement('style'); st.id = 'sp-upd-css';
    st.textContent = `
.sp-upd{position:fixed;left:50%;bottom:18px;transform:translateX(-50%);z-index:99990;display:flex;gap:12px;align-items:center;flex-wrap:wrap;justify-content:center;background:#181818;color:#fff;border-radius:14px;padding:12px 16px;max-width:min(94vw,560px);box-shadow:0 12px 32px rgba(0,0,0,.35);border-left:5px solid var(--serena-coral,#FF5246);font-size:.86rem}
.sp-upd b{display:block}.sp-upd small{color:#C9C5C0}
.sp-upd button{border:0;border-radius:10px;padding:8px 14px;font-weight:700;cursor:pointer}
.sp-upd .go{background:var(--serena-coral,#FF5246);color:#fff}.sp-upd .later{background:transparent;color:#C9C5C0}
.sp-maint{display:flex;gap:10px;align-items:center;justify-content:center;background:#FFF3CD;color:#5C4400;border-bottom:2px solid #E0B100;padding:9px 14px;font-size:.84rem;line-height:1.4;text-align:left;position:sticky;top:0;z-index:99980}.sp-maint.urgent{background:#FDE7E5;color:#7A1710;border-color:#D23532}.sp-maint .ic{font-size:1.2rem}.sp-maint small{opacity:.85}\n.sp-mpop{position:fixed;inset:0;z-index:100010;background:rgba(24,24,24,.7);display:flex;align-items:center;justify-content:center;padding:16px}.sp-mpop-card{background:#fff;border-radius:18px;max-width:440px;width:100%;max-height:92vh;overflow:auto;padding:24px;text-align:center;border-top:6px solid #D23532;box-shadow:0 24px 60px rgba(0,0,0,.4)}.sp-mpop-ic{width:56px;height:56px;margin:0 auto 10px;border-radius:50%;background:#D23532;color:#fff;font-size:1.8rem;display:grid;place-items:center}.sp-mpop-card h2{margin:0 0 6px;font-size:1.15rem;color:#7A1710}.sp-mpop-left{margin:0 0 12px;font-size:.95rem}.sp-mpop-left b{color:#D23532;font-size:1.05rem}.sp-mpop-when{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px}.sp-mpop-when div{background:#FFF8F5;border:1px solid #F3C9C2;border-radius:10px;padding:8px}.sp-mpop-when small{display:block;font-size:.7rem;color:#6b6560}.sp-mpop-when b{font-size:.84rem}.sp-mpop-msg{font-size:.88rem;line-height:1.5;margin:0 0 10px}.sp-mpop-card ul{text-align:left;margin:0 0 16px;padding-left:20px;font-size:.84rem;line-height:1.5;color:#4a4540}
.sp-new{position:fixed;inset:0;z-index:100001;background:rgba(24,24,24,.62);display:flex;align-items:center;justify-content:center;padding:16px}
.sp-new-card{background:#fff;border-radius:18px;max-width:480px;width:100%;max-height:90vh;overflow:auto;border-top:6px solid var(--serena-coral-escuro,#D23532);padding:22px;box-shadow:0 24px 60px rgba(0,0,0,.35)}
.sp-new-card small{color:var(--cor-texto-secundario,#6b6560)}
.sp-new-card h2{margin:4px 0 12px;font-size:1.15rem}
.sp-new-card ul{margin:0 0 16px;padding-left:20px;display:grid;gap:8px;font-size:.88rem;line-height:1.45}
.sp-new-act{display:flex;gap:10px;flex-wrap:wrap}.sp-new-act .btn,.sp-new-act a{flex:1;min-width:130px;text-align:center}`;
    document.head.appendChild(st);
  }

  function pad(n) { return String(n).padStart(2, '0'); }
  function fmtLeft(ms) {
    const m = Math.max(0, Math.floor(ms / 60000)), d = Math.floor(m / 1440), h = Math.floor((m % 1440) / 60), mi = m % 60;
    return (d ? d + 'd ' : '') + (h || d ? h + 'h ' : '') + mi + 'min';
  }
  function renderMaint() {
    if (!mData || !authed()) { if (mBar) { mBar.remove(); mBar = null; } return; }
    const now = Date.now() / 1000;
    if (mData.end_ts <= now) { if (mBar) { mBar.remove(); mBar = null; } return; }
    css();
    if (!mBar) {
      mBar = document.createElement('div'); mBar.className = 'sp-maint'; mBar.setAttribute('role', 'alert');
      document.body.insertBefore(mBar, document.body.firstChild);
    }
    const started = mData.start_ts <= now;
    const esc = (t) => String(t == null ? '' : t).replace(/[&<>"]/g, (c) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
    const urgent = !started && (mData.start_ts - now) < 3600;
    mBar.classList.toggle('urgent', urgent || started);
    mBar.innerHTML = '<span class="ic">⚠</span><div><b>' + (started ? 'Manutenção em andamento' : 'Parada programada do sistema') + '</b> ' +
      (started ? 'Retorno previsto: ' + esc(mData.end_label) + '.' : 'Começa em <b>' + fmtLeft((mData.start_ts - now) * 1000) + '</b> (' + esc(mData.start_label) + ' até ' + esc(mData.end_label) + ').') +
      '<br><small>' + esc(mData.message) + '</small></div>';
  }
  // Caixa de aviso: aparece ao ver a programação e volta 1 hora e 10 minutos antes da parada.
  function maintPopup() {
    if (!mData || mData.popup === false || !authed() || document.querySelector('.sp-mpop')) return;
    const now = Date.now() / 1000, left = mData.start_ts - now;
    if (left <= 0 || mData.end_ts <= now) return;
    const rank = left <= 600 ? 3 : (left <= 3600 ? 2 : 1);
    const key = 'sp-maint-popup:' + uid() + ':' + mData.start_ts;
    let seen = 0; try { seen = parseInt(localStorage.getItem(key) || '0', 10); } catch (e) {}
    if (rank <= seen) return;
    css();
    const esc = (t) => String(t == null ? '' : t).replace(/[&<>"]/g, (c) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
    const box = document.createElement('div'); box.className = 'sp-mpop'; box.setAttribute('role', 'alertdialog'); box.setAttribute('aria-modal', 'true');
    box.innerHTML = '<div class="sp-mpop-card"><div class="sp-mpop-ic">⚠</div><h2>Atenção: o sistema vai entrar em manutenção</h2>' +
      '<p class="sp-mpop-left">Começa em <b id="sp-mpop-left">' + fmtLeft(left * 1000) + '</b></p>' +
      '<div class="sp-mpop-when"><div><small>Início</small><b>' + esc(mData.start_label) + '</b></div><div><small>Retorno previsto</small><b>' + esc(mData.end_label) + '</b></div></div>' +
      '<p class="sp-mpop-msg">' + esc(mData.message) + '</p>' +
      '<ul><li>Finalize e salve o que está preenchendo antes do horário.</li><li>Durante a parada o acesso fica bloqueado para todos.</li></ul>' +
      '<button type="button" class="btn btn-primario" style="width:100%">Estou ciente</button></div>';
    box.querySelector('button').onclick = () => { try { localStorage.setItem(key, String(rank)); } catch (e) {} clearInterval(t); box.remove(); };
    document.body.appendChild(box);
    const t = setInterval(() => { const el = document.getElementById('sp-mpop-left'); if (!el) return clearInterval(t); el.textContent = fmtLeft((mData.start_ts - Date.now() / 1000) * 1000); }, 30000);
  }

  function setMaint(m) {
    mData = m; renderMaint(); maintPopup();
    if (!mTimer) mTimer = setInterval(() => { renderMaint(); maintPopup(); }, 30000);
  }

  function showBanner() {
    if (banner || dismissed || !authed()) return;
    css();
    banner = document.createElement('div'); banner.className = 'sp-upd'; banner.setAttribute('role', 'status');
    banner.innerHTML = '<div><b>Nova versão disponível</b><small>Salve o que está preenchendo antes de atualizar.</small></div><button class="go" type="button">Atualizar agora</button><button class="later" type="button">Depois</button>';
    banner.querySelector('.go').onclick = () => location.reload();
    banner.querySelector('.later').onclick = () => { dismissed = true; banner.remove(); banner = null; };
    document.body.appendChild(banner);
  }

  async function check() {
    if (!navigator.onLine) return;
    try {
      const r = await fetch('/api/app-version', {cache: 'no-store'});
      if (!r.ok) return;
      const d = await r.json();
      if (d.version && current() && d.version !== current()) showBanner();
      setMaint(d.maintenance || null);
    } catch (e) {}
  }

  // O service worker novo assumiu o controle enquanto a página estava aberta.
  if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
    navigator.serviceWorker.addEventListener('controllerchange', () => setTimeout(check, 500));
  }

  function updateBadge() {
    const el = document.getElementById('sp-ver-new'); if (!el) return;
    let seen = null; try { seen = localStorage.getItem('sp-release-seen:' + uid()); } catch (e) {}
    el.hidden = (seen === current());
  }
  function seenKey() { return 'sp-release-seen:' + uid(); }
  function whatsNew() {
    if (!authed() || !uid()) return;
    let rel; try { rel = JSON.parse(document.getElementById('sp-release').textContent); } catch (e) { return; }
    if (!rel || !rel.version) return;
    let seen = null; try { seen = localStorage.getItem(seenKey()); } catch (e) {}
    if (seen === rel.version) return;
    const mark = () => { try { localStorage.setItem(seenKey(), rel.version); } catch (e) {} updateBadge(); };
    // Primeiro acesso do aparelho: o pedido de permissões vem antes; a janela de novidades não compete com ele.
    if (document.querySelector('.sp-perms')) { return; }
    if (!seen) { let permsDone = false; try { permsDone = !!JSON.parse(localStorage.getItem('sp-perms-v1:' + uid()) || '{}').done; } catch (e) {} if (!permsDone) { mark(); return; } }
    css();
    const box = document.createElement('div'); box.className = 'sp-new'; box.setAttribute('role', 'dialog'); box.setAttribute('aria-modal', 'true');
    const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
    box.innerHTML = '<div class="sp-new-card"><small>Versão ' + esc(rel.version) + ' · ' + esc(rel.date || '') + '</small><h2>O que há de novo</h2><p style="margin:0 0 10px;font-weight:600">' + esc(rel.title || '') + '</p><ul>' +
      (rel.items || []).map((i) => '<li>' + esc(i) + '</li>').join('') + '</ul><div class="sp-new-act"><button type="button" class="btn btn-primario">Entendi</button><a class="btn btn-fantasma" href="/novidades">Ver histórico</a></div></div>';
    box.querySelector('button').onclick = () => { mark(); box.remove(); };
    box.querySelector('a').addEventListener('click', mark);
    document.body.appendChild(box);
  }

  document.addEventListener('DOMContentLoaded', function () {
    try { setMaint(JSON.parse(document.getElementById('sp-maint').textContent)); } catch (e) {}
    updateBadge();
    if (location.pathname === '/novidades') { try { localStorage.setItem(seenKey(), current()); } catch (e) {} updateBadge(); }
    setTimeout(whatsNew, 2500);
    setTimeout(check, 4000);
    setInterval(check, POLL_MS);
    document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') check(); });
  });
  window.SafetyPlusUpdates = {check: check};
})();
