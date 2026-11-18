/* Read-only origin inventory: no values leave local storage during scanning. */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else {
    root.kiaraPortalOriginScan = api;
    api.run(root).catch(() => {
      const status = root.document.getElementById('status');
      if (status) status.textContent = 'Vérification interrompue. Les données locales sont conservées.';
    });
  }
})(globalThis, function () {
  'use strict';
  const ports = Array.from({length: 10}, (_, index) => 17841 + index);

  async function advance({port, safe, inventory, post, navigate, display}) {
    if (!ports.includes(port) || !safe()) throw new Error('Fenêtre de vérification non protégée.');
    const request = async (path, body) => {
      if (!safe()) throw new Error('Fenêtre de vérification non protégée.');
      return post(path, body);
    };
    const move = target => {
      if (!ports.includes(target) || !safe()) throw new Error('Origine de vérification invalide.');
      navigate(`http://127.0.0.1:${target}/recovery/scan`);
    };
    let status = await request('/recovery/status');
    if (status.state === 'scanning') {
      if (!ports.includes(status.nextPort)) throw new Error('Inventaire incohérent.');
      if (status.nextPort !== port) return move(status.nextPort);
      display('Vérification des données locales en cours…');
      let report;
      try {report = await inventory();} catch {report = {unavailable: true};}
      status = await request('/recovery/inventory', report);
    }
    if (status.state === 'scanning') return move(status.nextPort);
    if (status.state === 'ready') {
      if (!ports.includes(status.port)) throw new Error('Origine de vérification invalide.');
      if (status.port !== port) return move(status.port);
      await request('/recovery/complete');
      display('Vérification terminée. Ouverture de Kiara…');
      return;
    }
    if (status.state === 'needsRecovery') {
      display('Préparation de la récupération des données locales…');
      return;
    }
    if (status.state === 'unavailable') {
      display('Les données locales ne peuvent pas être vérifiées. Elles sont conservées.');
      return;
    }
    throw new Error('Inventaire incohérent.');
  }

  async function run(root) {
    const element = root.document.getElementById('status');
    if (await root.__kiaraRecoveryReady !== true)
      throw new Error('Fenêtre de vérification non protégée.');
    const post = async (path, body) => {
      const response = await root.fetch(path, {
        method: 'POST', credentials: 'omit', cache: 'no-store',
        headers: {'X-Kiara-Recovery': root.__kiaraRecoveryToken,
          ...(body === undefined ? {} : {'Content-Type': 'application/json'})},
        ...(body === undefined ? {} : {body: JSON.stringify(body)}),
      });
      if (!response.ok) throw new Error('Vérification locale impossible.');
      return response.json();
    };
    return advance({port: Number(root.location.port),
      safe: () => root.__kiaraRecoveryNavigationSafe === true,
      inventory: () => root.kiaraPortalAudioConflictArchive
        ? root.kiaraPortalOriginInventory.inventory(root.localStorage,root.indexedDB,5000,
                                                   {audioArchive:root.kiaraPortalAudioConflictArchive,audioArchiveIds:true})
        : root.kiaraPortalOriginInventory.inventory(root.localStorage, root.indexedDB),
      post, navigate: url => root.location.assign(url),
      display: message => {if (element) element.textContent = message;}});
  }

  return {advance, run};
});
