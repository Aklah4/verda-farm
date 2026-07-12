// Toast auto-dismiss, matching the 2.4s timeout in the design.
(function () {
  var toast = document.getElementById('toast');
  if (toast) {
    setTimeout(function () { toast.remove(); }, 2400);
  }
})();

// Hamburger menus. One handler drives both the site header and the dashboard
// sidebar: each toggle names the panel it owns via data-nav-toggle, and the
// open state lives on aria-expanded, which the CSS reads to draw the × as well.
(function () {
  var toggles = document.querySelectorAll('[data-nav-toggle]');

  function close(toggle, panel) {
    toggle.setAttribute('aria-expanded', 'false');
    panel.classList.remove('is-open');
  }

  toggles.forEach(function (toggle) {
    var panel = document.getElementById(toggle.dataset.navToggle);
    if (!panel) return;

    toggle.addEventListener('click', function () {
      var open = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', String(!open));
      panel.classList.toggle('is-open', !open);
    });

    // Escape closes it, and so does following a link — otherwise the menu is
    // still hanging open behind the page you just navigated to on a back-swipe.
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') close(toggle, panel);
    });

    panel.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () { close(toggle, panel); });
    });

    // Resizing past the breakpoint reveals the desktop layout; a panel left
    // open would otherwise keep its is-open class and reappear on the next
    // resize back down.
    window.addEventListener('resize', function () {
      if (window.innerWidth > 900) close(toggle, panel);
    });
  });
})();

// Confirm before anything irreversible. Driven by data-confirm rather than an
// inline onsubmit handler, so the Content-Security-Policy can forbid inline
// script outright — that is what stops an injected payload from ever executing.
(function () {
  document.querySelectorAll('[data-confirm]').forEach(function (form) {
    form.addEventListener('submit', function (event) {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });
})();

// Product page quantity stepper — keeps the subtotal live without a round trip.
(function () {
  var form = document.getElementById('buy-form');
  if (!form) return;

  var input = form.querySelector('#qty');
  var subtotal = document.getElementById('subtotal');
  var price = Number(form.dataset.price);

  function render() {
    var qty = Math.max(1, parseInt(input.value, 10) || 1);
    input.value = qty;
    subtotal.textContent = '₦' + (price * qty).toLocaleString('en-US');
  }

  form.querySelectorAll('[data-step]').forEach(function (button) {
    button.addEventListener('click', function () {
      input.value = (parseInt(input.value, 10) || 1) + Number(button.dataset.step);
      render();
    });
  });

  input.addEventListener('input', render);
  render();
})();
