/* Compatibilidade: páginas preparadas em versões anteriores carregam este arquivo.
   A partir da V36.18.95 a fila offline fica em offline-core.js + offline-sync.js. */
(function () {
  if (window.SafetyPlusOffline || window.__spOfflineShim) return; window.__spOfflineShim = 1;
  function load(src, cb) { var s = document.createElement('script'); s.src = src; s.onload = cb; document.head.appendChild(s); }
  load('/static/js/offline-core.js?v=361917', function () { load('/static/js/offline-sync.js?v=361920'); });
})();
