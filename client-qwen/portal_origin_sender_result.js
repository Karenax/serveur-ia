/* Experimental sender: the final result contains only counts or an error. */
(function (root, factory) {
  const api=factory();
  if (typeof module!=='undefined' && module.exports) module.exports=api;
  else api.run(root).catch(()=>{});
})(globalThis,function () {
  'use strict';
  async function run(root) {
    if (await root.__kiaraRecoveryReady!==true) throw new Error('Protection indisponible.');
    const api=root.kiaraPortalOriginTransfer;
    const transport=api.httpTransport(root.fetch.bind(root),root.__kiaraRecoveryToken);
    let result;
    try {
      const store=api.indexedAudioSource(root.indexedDB);
      const archive=root.kiaraPortalAudioConflictArchive;
      const journal=archive ? await archive.open(root.indexedDB,{allowMissing:true}) : null;
      const inventory=()=>archive
        ? root.kiaraPortalOriginInventory.inventory(root.localStorage,root.indexedDB,5000,{audioArchive:archive})
        : root.kiaraPortalOriginInventory.inventory(root.localStorage,root.indexedDB);
      const records=archive ? api.sourceRecords(root.localStorage,store,inventory,root.crypto?.subtle,{archiveAPI:archive,archiveStore:journal})
                            : api.sourceRecords(root.localStorage,store,inventory);
      const counts=await api.sendAll(records,transport);
      result={status:'ok',copied:counts.copied,identical:counts.identical,
        ...(counts.preserved ? {preserved:counts.preserved} : {}),
        ...(counts.archived ? {archived:counts.archived} : {})};
    } catch (error) {
      result={status:error instanceof api.TransferConflict ? 'conflict' : error instanceof api.TransferRestart ? 'restart' : 'unavailable'};
    }
    const response=await root.fetch('/recovery/result',{method:'POST',credentials:'omit',cache:'no-store',
      headers:{'X-Kiara-Recovery':root.__kiaraRecoveryToken},body:JSON.stringify(result)});
    if (!response.ok) throw new Error('Résultat non confirmé.');
  }
  return {run};
});
