/* Safety Plus: feedback de envio sem desativar campos do formulario. */
(function () {
  function setup() {
    document.querySelectorAll('form[data-submit-feedback="true"]').forEach(function (form) {
      if (form.dataset.feedbackReady === '1') return;
      form.dataset.feedbackReady = '1';
      var sending = false;
      var originalButtons = [];
      var notice = document.createElement('div');
      notice.className = 'sp-submit-feedback';
      notice.setAttribute('role', 'status');
      notice.setAttribute('aria-live', 'polite');
      notice.hidden = true;
      notice.textContent = 'Gerando o documento… Aguarde e não feche esta página.';
      form.appendChild(notice);
      form.addEventListener('submit', function (event) {
        if (sending) {
          event.preventDefault();
          return;
        }
        if (event.defaultPrevented) return;
        sending = true;
        // Evita submissões duplicadas sem desativar inputs (incluindo fotos e rubricas).
        requestAnimationFrame(function () {
          notice.hidden = false;
          originalButtons = Array.from(form.querySelectorAll('button[type="submit"], button[data-finish-period]')).map(function (btn) {
            var state = {btn: btn, disabled: btn.disabled};
            btn.disabled = true;
            return state;
          });
        });
      });
      window.addEventListener('pageshow', function () {
        sending = false;
        notice.hidden = true;
        originalButtons.forEach(function (state) { state.btn.disabled = state.disabled; });
        originalButtons = [];
      });
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', setup);
  else setup();
}());
