/* Experimental sender. It never deletes the source or reports data values. */
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
      const inventory=()=>root.kiaraPortalOriginInventory.inventory(root.localStorage,root.indexedDB);
      const counts=await api.sendAll(api.sourceRecords(root.localStorage,store,inventory),transport);
      result={type:'result',status:'ok',copied:counts.copied,identical:counts.identical};
    } catch (error) {
      result={type:'result',status:error instanceof api.TransferConflict ? 'conflict' : 'unavailable'};
    }
    await transport.stage(new TextEncoder().encode(JSON.stringify(result)));
  }
  return {run};
});
