/* Experimental fingerprint of an origin; no content or identifiers leave it. */
(function (root, factory) {
  const api=factory();
  if (typeof module!=='undefined' && module.exports) module.exports=api;
  else api.run(root).catch(()=>{});
})(globalThis,function () {
  'use strict';
  const MAX_ENTRIES=10000,MAX_SUMMARY_BYTES=4*1024*1024;
  async function digest(value,subtle) {
    const bytes=new TextEncoder().encode(value);
    const hash=await subtle.digest('SHA-256',bytes);
    return Array.from(new Uint8Array(hash),byte=>byte.toString(16).padStart(2,'0')).join('');
  }
  async function snapshot(records,subtle=globalThis.crypto?.subtle,options={}) {
    if (!subtle || typeof subtle.digest!=='function') throw new Error('Vérification indisponible.');
    if (!options || typeof options!=='object' || Array.isArray(options)
        || Object.keys(options).some(key=>key!=='audioArchive')) throw new Error('Vérification indisponible.');
    const includeArchives=Object.hasOwn(options,'audioArchive');
    if (includeArchives && (!options.audioArchive || typeof options.audioArchive.verify!=='function'))
      throw new Error('Vérification indisponible.');
    const entries=[];let localEntries=0,audioChunks=0,audioArchives=0,size=0;
    for await (const record of records) {
      let entry;
      if (record?.type==='local' && typeof record.key==='string' && typeof record.value==='string') {
        entry=['local',record.key,await digest(record.value,subtle)];localEntries++;
      } else if ((record?.type==='audio' || record?.type==='audio-stream') && record.meta && typeof record.mime==='string') {
        entry=['audio',record.meta,record.mime];audioChunks++;
      } else if (record?.type==='audio-archive-stream' && includeArchives) {
        const saved=await options.audioArchive.verify({id:record.id,current:record.current,incoming:record.incoming},subtle);
        entry=['audio-archive',saved.id];audioArchives++;
      } else throw new Error('Donnée locale inconnue.');
      size+=new TextEncoder().encode(JSON.stringify(entry)).length;
      if (entries.length>=MAX_ENTRIES || size>MAX_SUMMARY_BYTES) throw new Error('Inventaire trop volumineux.');
      entries.push(entry);
    }
    return {status:'snapshot',localEntries,audioChunks,...(includeArchives ? {audioArchives} : {}),
      digest:await digest(JSON.stringify({format:includeArchives ? 2 : 1,entries}),subtle)};
  }
  async function run(root) {
    if (await root.__kiaraRecoveryReady!==true) throw new Error('Protection indisponible.');
    const api=root.kiaraPortalOriginTransfer;let result;
    try {
      const archive=root.kiaraPortalAudioConflictArchive;
      const journal=archive ? await archive.open(root.indexedDB,{allowMissing:true}) : null;
      const inventory=()=>archive
        ? root.kiaraPortalOriginInventory.inventory(root.localStorage,root.indexedDB,5000,{audioArchive:archive})
        : root.kiaraPortalOriginInventory.inventory(root.localStorage,root.indexedDB);
      const store=api.indexedAudioSource(root.indexedDB);
      const records=archive ? api.sourceRecords(root.localStorage,store,inventory,root.crypto?.subtle,{archiveAPI:archive,archiveStore:journal})
                            : api.sourceRecords(root.localStorage,store,inventory);
      result=await snapshot(records,root.crypto?.subtle,archive ? {audioArchive:archive} : {});
    } catch {result={status:'unavailable'};}
    const response=await root.fetch('/recovery/result',{method:'POST',credentials:'omit',cache:'no-store',
      headers:{'X-Kiara-Recovery':root.__kiaraRecoveryToken},body:JSON.stringify(result)});
    if (!response.ok) throw new Error('Vérification non confirmée.');
  }
  return {snapshot,run};
});
