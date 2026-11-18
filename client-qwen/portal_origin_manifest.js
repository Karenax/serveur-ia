/* Read-only manifest of verified audio copies on the selected origin. */
(function (root, factory) {
  const api=factory();
  if (typeof module!=='undefined' && module.exports) module.exports=api;
  else api.run(root).catch(()=>{});
})(globalThis,function () {
  'use strict';
  async function run(root) {
    if (await root.__kiaraRecoveryReady!==true) throw new Error('Protection indisponible.');
    let result,store;
    try {
      const archive=root.kiaraPortalAudioConflictArchive;
      if (!archive || typeof archive.open!=='function' || typeof archive.list!=='function') throw new Error();
      store=await archive.open(root.indexedDB,{allowMissing:true});
      const copies=store ? await archive.list(store) : [];
      const ids=copies.map(item=>item.id);
      if (ids.length>3000 || ids.some(id=>typeof id!=='string' || !/^[0-9a-f]{64}$/.test(id))
          || new Set(ids).size!==ids.length) throw new Error();
      result={status:'manifest',audioArchiveIds:ids.sort()};
    } catch {result={status:'unavailable'};}
    finally {if(store)store.close();}
    const response=await root.fetch('/recovery/result',{method:'POST',credentials:'omit',cache:'no-store',
      headers:{'X-Kiara-Recovery':root.__kiaraRecoveryToken},body:JSON.stringify(result)});
    if (!response.ok) throw new Error('Vérification non confirmée.');
  }
  return {run};
});
