/* Experimental receiver. Conflicts are acknowledged without replacing data. */
(function (root, factory) {
  const api=factory();
  if (typeof module!=='undefined' && module.exports) module.exports=api;
  else api.run(root).catch(async error=>{
    try {
      if (await root.__kiaraRecoveryReady===true) {
        const transport=root.kiaraPortalOriginTransfer.httpTransport(root.fetch.bind(root),root.__kiaraRecoveryToken);
        if (error instanceof api.RequiredArchiveUnavailable) await transport.missingArchive();
        else await transport.fail();
      }
    } catch {/* The controller still has its bounded timeout. */}
  });
})(globalThis,function () {
  'use strict';
  class RequiredArchiveUnavailable extends Error {}
  function localConflictHandler(root,transport,options) {
    if (!root.kiaraPortalConflictArchive || !root.kiaraPortalConflictReview
        || typeof transport.review!=='function' || typeof transport.markArchive!=='function' || typeof options.preserve!=='boolean')
      throw new Error('Comparaison indisponible.');
    return async (record,transfer)=>{
      const archive=root.kiaraPortalConflictArchive;
      const existing=await archive.find(root.localStorage,record.key,record.value);
      if (existing) {await transport.markArchive(transfer,existing);return 'archived';}
      if (options.preserve) return 'conflict';
      await transport.review(transfer);
      const result=await root.kiaraPortalConflictReview.show({document:root.document,
        container:root.document.getElementById('recovery-review'),storage:root.localStorage,
        key:record.key,incoming:record.value,archive:archive.archive,restartRequired:true});
      if (!result || !['archived','cancel'].includes(result.status)) throw new Error('Décision invalide.');
      return result.status==='archived' ? 'restart' : 'conflict';
    };
  }
  function audioConflictHandler(root,transport,chunks) {
    const archive=root.kiaraPortalAudioConflictArchive, review=root.kiaraPortalAudioConflictReview;
    const recovery=root.kiaraPortalOriginRecovery;
    if (!archive || !review || !recovery || typeof archive.open!=='function' || typeof archive.find!=='function'
        || typeof archive.archive!=='function' || typeof review.show!=='function' || typeof recovery.prepareAudio!=='function'
        || typeof chunks?.get!=='function' || typeof transport.review!=='function' || typeof transport.markArchive!=='function')
      throw new Error('Comparaison audio indisponible.');
    const subtle=root.crypto?.subtle;
    return async (audio,transfer)=>{
      if (!audio || !(audio.bytes instanceof Uint8Array) || typeof audio.mime!=='string')
        throw new Error('Fragment audio invalide.');
      const incomingRecord={...audio.meta,stableBytes:audio.bytes.slice().buffer,stableMime:audio.mime};
      const incoming=await recovery.prepareAudio(incomingRecord,subtle);
      const current=await recovery.prepareAudio(await chunks.get(incoming.meta.id),subtle);
      const description=item=>JSON.stringify({meta:item.meta,mime:item.mime});
      const expected=description(current);
      let existing,store=await archive.open(root.indexedDB,{allowMissing:true});
      if (store) {
        try {existing=await archive.find(store,chunks,incomingRecord,subtle);}
        finally {store.close();}
      }
      if (existing) {await transport.markArchive(transfer,'audio-'+existing);return 'archived';}
      await transport.review(transfer);
      const result=await review.show({document:root.document,container:root.document.getElementById('recovery-review'),
        current,incoming,urls:root.URL,restartRequired:true,archive:async()=>{
          const before=await recovery.prepareAudio(await chunks.get(incoming.meta.id),subtle);
          if (description(before)!==expected) throw new Error('Le fragment courant a changé.');
          const destination=await archive.open(root.indexedDB,{create:true});
          try {
            const id=await archive.archive(destination,chunks,incomingRecord,subtle);
            const after=await recovery.prepareAudio(await chunks.get(incoming.meta.id),subtle);
            if (description(after)!==expected) throw new Error('Le fragment courant a changé.');
            return id;
          } finally {destination.close();}
        }});
      if (!result || !['archived','cancel'].includes(result.status)) throw new Error('Décision invalide.');
      return result.status==='archived' ? 'restart' : 'conflict';
    };
  }
  async function verifyRequired(root,transport,options) {
    if (!Array.isArray(options.required)) throw new Error('Copies conservées indisponibles.');
    if (!options.required.length) return;
    if (!root.kiaraPortalConflictArchive || typeof root.kiaraPortalConflictArchive.read!=='function'
        || typeof transport.requiredOk!=='function') throw new RequiredArchiveUnavailable('Copies conservées indisponibles.');
    let audioStore;
    try {
      for (const id of options.required) {
        if (typeof id!=='string') throw new Error('Copie invalide.');
        if (id.startsWith('audio-')) {
          const archive=root.kiaraPortalAudioConflictArchive;
          if (!/^audio-[0-9a-f]{64}$/.test(id) || !archive || typeof archive.open!=='function' || typeof archive.read!=='function')
            throw new Error('Copie audio indisponible.');
          audioStore ??= await archive.open(root.indexedDB);
          await archive.read(audioStore,id.slice(6));
        } else await root.kiaraPortalConflictArchive.read(root.localStorage,id);
      }
    }
    catch {throw new RequiredArchiveUnavailable('Copies conservées indisponibles.');}
    finally {if (audioStore) audioStore.close();}
    await transport.requiredOk();
  }
  async function run(root) {
    if (await root.__kiaraRecoveryReady!==true) throw new Error('Protection indisponible.');
    const api=root.kiaraPortalOriginTransfer;
    const transport=api.httpTransport(root.fetch.bind(root),root.__kiaraRecoveryToken);
    const options=await transport.options();
    await verifyRequired(root,transport,options);
    let db,opening;
    const open=()=>opening ??= new Promise((resolve,reject)=>{
      let settled=false,request;
      const timer=setTimeout(()=>fail(),5000);
      const fail=()=>{if(!settled){settled=true;clearTimeout(timer);reject(new Error('Stockage audio indisponible.'));}};
      try {request=root.indexedDB.open('agent-meeting-audio-v1',1);} catch {fail();return;}
      request.onupgradeneeded=()=>{try{const store=request.result.createObjectStore('chunks',{keyPath:'id'});store.createIndex('session_id','session_id');}catch{try{request.transaction.abort();}catch{}}};
      request.onerror=request.onblocked=fail;
      request.onsuccess=()=>{
        const value=request.result;
        if(settled){value.close();return;}
        try {
          if(value.version!==1 || value.objectStoreNames.length!==1 || !value.objectStoreNames.contains('chunks'))throw new Error();
          const store=value.transaction('chunks','readonly').objectStore('chunks');
          if(store.keyPath!=='id' || store.indexNames.length!==1 || !store.indexNames.contains('session_id'))throw new Error();
          const index=store.index('session_id');
          if(index.keyPath!=='session_id' || index.unique || index.multiEntry)throw new Error();
        } catch {value.close();fail();return;}
        settled=true;clearTimeout(timer);db=value;resolve(db);
      };
    });
    const store={
      get:async id=>{
        const database=await open();
        return new Promise((resolve,reject)=>{
          const request=database.transaction('chunks','readonly').objectStore('chunks').get(id);
          request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(new Error('Stockage audio illisible.'));
        });
      },
      add:async record=>{
        const database=await open();
        return new Promise((resolve,reject)=>{
          const transaction=database.transaction('chunks','readwrite');transaction.objectStore('chunks').add(record);
          transaction.oncomplete=()=>resolve();transaction.onabort=transaction.onerror=()=>reject(transaction.error || new Error('Écriture audio impossible.'));
        });
      },
    };
    const state={audio:null};let journal,openingJournal;
    const archive=root.kiaraPortalAudioConflictArchive;
    if (archive) {
      const openJournal=()=>openingJournal ??= archive.open(root.indexedDB,{create:true}).then(value=>{journal=value;return value;});
      state.archiveAPI=archive;
      state.archiveStore={get:async id=>(await openJournal()).get(id),add:async value=>(await openJournal()).add(value)};
    }
    if (options.review) {
      state.onLocalConflict=localConflictHandler(root,transport,options);
      if (archive) state.onAudioConflict=audioConflictHandler(root,transport,store);
    }
    try {
      for (;;) {
        const status=await api.receiveOne(transport,root.localStorage,store,undefined,state);
        if (status===null) await new Promise(resolve=>setTimeout(resolve,100));
      }
    } finally {if(db)db.close();if(journal)journal.close();}
  }
  return {run,localConflictHandler,audioConflictHandler,verifyRequired,RequiredArchiveUnavailable};
});
