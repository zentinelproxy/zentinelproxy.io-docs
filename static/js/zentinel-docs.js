// Zentinel docs: behaviour the tanuki theme does not have. Loaded deferred
// after the theme's scripts (templates/page.html, section.html, 404.html).
//
// 1. Footer theme switch (partials/zentinel-footer.html). It drives tanuki's
//    own mechanism: localStorage `tanuki-theme` (auto | light | dark) and
//    data-theme / data-theme-setting on <html>, exactly as theme.js does, so
//    the header toggle and the switch stay in sync both ways. System = auto
//    = follow the OS (theme.js re-applies it when the OS setting changes).
// 2. Copy buttons on code blocks (created by js/code.js, which this file
//    leaves alone): give them the shared .z-copy control, mirror code.js's
//    `copied` class to data-copied, and announce the copy in #z-announce.
(function () {
  'use strict';

  var KEY = 'tanuki-theme';
  var root = document.documentElement;

  function announce(text) {
    var el = document.getElementById('z-announce');
    if (!el) return;
    el.textContent = '';
    setTimeout(function () { el.textContent = text; }, 30);
  }

  // ── Theme switch ──────────────────────────────────────────────────────

  function currentSetting() {
    var s = root.getAttribute('data-theme-setting');
    return s === 'light' || s === 'dark' ? s : 'auto';
  }

  function applySetting(s) {
    var effective = s === 'auto'
      ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
      : s;
    // Same as theme.js: no transitions while the colours swap.
    root.classList.add('theme-transition-off');
    root.setAttribute('data-theme', effective);
    root.setAttribute('data-theme-setting', s);
    void root.offsetHeight;
    root.classList.remove('theme-transition-off');
    try { localStorage.setItem(KEY, s); } catch (e) { /* storage blocked: applies to this page only */ }
  }

  var inputs = document.querySelectorAll('.zd-theme-switch input[name="zd-theme"]');

  function reflect() {
    var s = currentSetting();
    inputs.forEach(function (input) { input.checked = input.value === s; });
  }

  inputs.forEach(function (input) {
    input.addEventListener('change', function () {
      if (input.checked) applySetting(input.value);
    });
  });
  reflect();

  // The header toggle (theme.js) changes data-theme-setting: follow it.
  new MutationObserver(reflect).observe(root, { attributes: true, attributeFilter: ['data-theme-setting'] });

  // Another tab changed the setting.
  window.addEventListener('storage', function (e) {
    if (e.key === KEY) applySetting(e.newValue === 'light' || e.newValue === 'dark' ? e.newValue : 'auto');
  });

  // ── Copy buttons ──────────────────────────────────────────────────────

  function wire(btn) {
    if (btn.dataset.zWired) return;
    btn.dataset.zWired = '1';
    btn.classList.add('z-copy');
    btn.setAttribute('type', 'button');
    new MutationObserver(function () {
      if (btn.classList.contains('copied')) {
        if (!btn.hasAttribute('data-copied')) {
          btn.setAttribute('data-copied', '');
          announce('Code copied to the clipboard');
        }
      } else {
        btn.removeAttribute('data-copied');
      }
    }).observe(btn, { attributes: true, attributeFilter: ['class'] });
  }

  function wireAll(scope) {
    (scope.querySelectorAll ? scope : document).querySelectorAll('.copy-button').forEach(wire);
  }

  wireAll(document);
  // code.js can add blocks later (it re-runs on SPA navigation events).
  new MutationObserver(function (records) {
    records.forEach(function (r) {
      r.addedNodes.forEach(function (n) {
        if (n.nodeType !== 1) return;
        if (n.classList.contains('copy-button')) wire(n);
        else wireAll(n);
      });
    });
  }).observe(document.body, { childList: true, subtree: true });
})();
