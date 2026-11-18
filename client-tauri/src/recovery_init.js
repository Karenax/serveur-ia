/* Injected only into a future recovery window. Values are replaced by native
 * code after validation; the normal Kiara window must not use this script. */
(() => {
  'use strict';
  const token = '__TOKEN__';
  const ports = new Set([__PORTS__]);
  const requireNavigationApi = __REQUIRE_NAVIGATION__;
  let navigationSafe = !requireNavigationApi;
  let workerSafe = false;
  Object.defineProperty(window, '__kiaraRecoveryNavigationSafe', {get: () => navigationSafe && workerSafe, configurable: false});
  if (window.navigation && typeof window.navigation.addEventListener === 'function') {
    navigationSafe = true;
    window.navigation.addEventListener('navigate', event => {
    let allowed = false;
    try {
      const url = new URL(event.destination.url);
      allowed = url.protocol === 'http:' && url.hostname === '127.0.0.1'
        && ports.has(Number(url.port)) && !url.username && !url.password
        && ['/recovery','/recovery/scan','/recovery/transfer'].includes(url.pathname)
        && url.href === `http://127.0.0.1:${url.port}${url.pathname}`;
    } catch {/* malformed destinations are denied */}
    if (!allowed) {
      if (!event.cancelable) navigationSafe = false;
      event.preventDefault();
    }
    });
  }
  // An old service worker can replace a navigation response before its CSP is
  // applied. Do not expose the token or alter registrations in that situation.
  const ready = (async () => {
    try {
      if (!navigationSafe) return false;
      const workers = window.navigator?.serviceWorker;
      if (workers) {
        if (workers.controller || typeof workers.getRegistrations !== 'function') return false;
        let timer;
        let registrations;
        try {
          registrations = await Promise.race([
            workers.getRegistrations(),
            new Promise((_, reject) => {timer = setTimeout(() => reject(new Error()), 5000);}),
          ]);
        } finally {clearTimeout(timer);}
        if (!Array.isArray(registrations) || registrations.length || workers.controller) return false;
      }
      if (!navigationSafe) return false;
      Object.defineProperty(window, '__kiaraRecoveryToken', {value: token, writable: false, configurable: false});
      workerSafe = true;
      return true;
    } catch {return false;}
  })();
  Object.defineProperty(window, '__kiaraRecoveryReady', {value: ready, writable: false, configurable: false});
})();
