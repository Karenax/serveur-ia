/* Experimental, one-record-at-a-time recovery; callers retain every source. */
(function (root, factory) {
  const recovery = typeof module !== 'undefined' && module.exports
    ? require('./portal_origin_recovery.js') : root.kiaraPortalOriginRecovery;
  const api = factory(recovery);
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.kiaraPortalOriginTransfer = api;
})(globalThis, function (recovery) {
  'use strict';
  const MAX_BYTES = 16 * 1024 * 1024;
  const INLINE_AUDIO_BYTES = 1024 * 1024;
  const SEGMENT_BYTES = 512 * 1024;
  const MAX_STREAM_BYTES = 512 * 1024 * 1024;
  const ID = /^[0-9a-f]{32}$/, HASH = /^[0-9a-f]{64}$/, ARCHIVE_ID = /^(?:audio-)?[0-9a-f]{64}$/;
  const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
  class TransferConflict extends Error {
    constructor() {super('Une autre version existe déjà. Les données d’origine sont conservées.');this.name='TransferConflict';}
  }
  class TransferRestart extends Error {
    constructor() {super('Les copies doivent être vérifiées après redémarrage.');this.name='TransferRestart';}
  }
  async function digest(bytes, subtle) {
    const hash = await subtle.digest('SHA-256', bytes);
    return Array.from(new Uint8Array(hash), value => value.toString(16).padStart(2, '0')).join('');
  }
  function localRecord(key, value) {
    if (typeof key !== 'string' || typeof value !== 'string') throw new TypeError('Entrée locale invalide.');
    return {type:'local', key, value};
  }
  function encodeAudio(bytes) {
    if (bytes.byteLength > Math.floor(MAX_BYTES * 3 / 4))
      throw new Error('Donnée trop volumineuse pour cette récupération.');
    const parts=[];
    // A multiple of three lets independently encoded chunks concatenate safely.
    for (let offset=0;offset<bytes.length;offset+=24576)
      parts.push(btoa(String.fromCharCode(...bytes.subarray(offset,offset+24576))));
    return parts.join('');
  }
  function decodeAudio(value) {
    if (typeof value !== 'string' || value.length > MAX_BYTES || value.length % 4 !== 0
        || !/^[A-Za-z0-9+/]*={0,2}$/.test(value)) throw new Error('Fragment audio invalide.');
    let binary;
    try {binary=atob(value);} catch {throw new Error('Fragment audio invalide.');}
    const bytes=new Uint8Array(binary.length);
    for (let i=0;i<binary.length;i++) bytes[i]=binary.charCodeAt(i);
    return bytes;
  }
  async function audioRecord(record, subtle = globalThis.crypto?.subtle) {
    const prepared = await recovery.prepareAudio(record, subtle);
    return wireAudio(prepared);
  }
  function wireAudio(prepared) {
    if (prepared.bytes.byteLength > MAX_STREAM_BYTES)
      throw new Error('Fragment audio trop volumineux pour cette récupération.');
    if (prepared.bytes.byteLength > INLINE_AUDIO_BYTES)
      return {type:'audio-stream',meta:prepared.meta,mime:prepared.mime,bytes:prepared.bytes};
    return {type:'audio',meta:prepared.meta,mime:prepared.mime,data:encodeAudio(prepared.bytes)};
  }
  function audioArchiveRecord(saved) {
    if (!exact(saved,['id','current','incoming']) || !HASH.test(saved.id))
      throw new Error('Copie audio invalide.');
    const side=value=>{
      if (!exact(value,['meta','mime','bytes']) || !(value.bytes instanceof Uint8Array)
          || value.bytes.byteLength>MAX_STREAM_BYTES || typeof value.mime!=='string' || !value.mime || value.mime.length>256)
        throw new Error('Copie audio invalide.');
      const meta=recovery.audioMetadata(value.meta);
      if (!exact(value.meta,Object.keys(meta))) throw new Error('Copie audio invalide.');
      return {meta,mime:value.mime,bytes:value.bytes};
    };
    return {type:'audio-archive-stream',id:saved.id,current:side(saved.current),incoming:side(saved.incoming)};
  }
  function storageKeys(storage) {
    const count=storage.length, keys=[];
    if (!Number.isSafeInteger(count) || count<0) throw new Error('Stockage local indisponible.');
    for (let index=0;index<count;index++) {
      const key=storage.key(index);
      if (typeof key!=='string') throw new Error('Stockage local modifié.');
      keys.push(key);
    }
    if (storage.length!==count || new Set(keys).size!==count) throw new Error('Stockage local modifié.');
    return keys.sort();
  }
  function sameList(left,right) {return left.length===right.length && left.every((value,index)=>value===right[index]);}
  function validInventory(value, includeArchives=false) {
    const fields=includeArchives ? ['localEntries','audioChunks','audioArchives'] : ['localEntries','audioChunks'];
    return exact(value,fields) && fields
      .every(key=>Number.isSafeInteger(value[key]) && value[key]>=0);
  }
  function audioKeys(values) {
    if (!Array.isArray(values) || values.some(value=>typeof value!=='string') || new Set(values).size!==values.length)
      throw new Error('Stockage audio modifié.');
    return values.slice().sort();
  }
  async function* sourceRecords(storage, store, inventory, subtle=globalThis.crypto?.subtle, options={}) {
    if (typeof inventory!=='function' || !subtle || typeof subtle.digest!=='function')
      throw new Error('Inventaire de récupération indisponible.');
    if (!options || typeof options!=='object' || Array.isArray(options)
        || Object.keys(options).some(key=>!['archiveAPI','archiveStore'].includes(key)))
      throw new Error('Inventaire de récupération indisponible.');
    const includeArchives=Object.hasOwn(options,'archiveAPI'),archive=options.archiveAPI,archiveStore=options.archiveStore;
    if (includeArchives && (!archive || typeof archive.list!=='function' || typeof archive.read!=='function'))
      throw new Error('Copies audio indisponibles.');
    if (!includeArchives && Object.hasOwn(options,'archiveStore')) throw new Error('Copies audio indisponibles.');
    try {
      const before=await inventory();
      if (!validInventory(before,includeArchives)) throw new Error('Inventaire de récupération invalide.');
      const keys=storageKeys(storage), ids=before.audioChunks ? audioKeys(await store.keys()) : [];
      if (keys.length!==before.localEntries || ids.length!==before.audioChunks)
        throw new Error('Les données locales ont changé pendant la vérification.');
      const archivedKeys=async()=>{
        if (!archiveStore) {if(before.audioArchives)throw new Error('Copies audio indisponibles.');return [];}
        const values=await archive.list(archiveStore);
        if (!Array.isArray(values) || values.some(item=>!item || typeof item.id!=='string' || !HASH.test(item.id)))
          throw new Error('Copies audio illisibles.');
        const found=values.map(item=>item.id);
        if (new Set(found).size!==found.length) throw new Error('Copies audio illisibles.');
        return found.sort();
      };
      const archives=includeArchives ? await archivedKeys() : [];
      if (includeArchives && archives.length!==before.audioArchives)
        throw new Error('Les copies audio ont changé pendant la vérification.');
      const localHashes=[], audioSummaries=[];
      for (const key of keys) {
        const value=storage.getItem(key);
        if (typeof value!=='string') throw new Error('Les données locales ont changé pendant la vérification.');
        localHashes.push(await digest(new TextEncoder().encode(value),subtle));
        yield localRecord(key,value);
      }
      for (const id of ids) {
        const prepared=await recovery.prepareAudio(await store.get(id),subtle);
        if (prepared.meta.id!==id) throw new Error('Les données audio ont changé pendant la vérification.');
        audioSummaries.push(JSON.stringify([prepared.meta,prepared.mime]));
        yield wireAudio(prepared);
      }
      for (const id of archives) yield audioArchiveRecord(await archive.read(archiveStore,id,subtle));
      const after=await inventory();
      if (!validInventory(after,includeArchives) || after.localEntries!==before.localEntries || after.audioChunks!==before.audioChunks
          || (includeArchives && after.audioArchives!==before.audioArchives)
          || !sameList(keys,storageKeys(storage)) || (ids.length && !sameList(ids,audioKeys(await store.keys()))))
        throw new Error('Les données locales ont changé pendant la récupération.');
      if (includeArchives && !sameList(archives,await archivedKeys()))
        throw new Error('Les copies audio ont changé pendant la récupération.');
      for (let i=0;i<keys.length;i++) {
        const value=storage.getItem(keys[i]);
        if (typeof value!=='string' || await digest(new TextEncoder().encode(value),subtle)!==localHashes[i])
          throw new Error('Les données locales ont changé pendant la récupération.');
      }
      for (let i=0;i<ids.length;i++) {
        const prepared=await recovery.prepareAudio(await store.get(ids[i]),subtle);
        if (JSON.stringify([prepared.meta,prepared.mime])!==audioSummaries[i])
          throw new Error('Les données audio ont changé pendant la récupération.');
      }
    } finally {
      if (typeof store.close==='function') store.close();
      if (archiveStore && typeof archiveStore.close==='function') archiveStore.close();
    }
  }
  function indexedAudioSource(indexedDB) {
    let db, opening;
    const open=()=>opening ??= new Promise((resolve,reject)=>{
      let request,settled=false;
      const timer=setTimeout(()=>fail(),5000);
      const fail=()=>{if(!settled){settled=true;clearTimeout(timer);reject(new Error('Stockage audio indisponible.'));}};
      try {request=indexedDB.open('agent-meeting-audio-v1');} catch {fail();return;}
      request.onupgradeneeded=()=>{try{request.transaction.abort();}catch{}};
      request.onblocked=request.onerror=fail;
      request.onsuccess=()=>{
        if(settled){request.result.close();return;}
        if(request.result.version!==1 || request.result.objectStoreNames.length!==1
            || !request.result.objectStoreNames.contains('chunks')){request.result.close();fail();return;}
        settled=true;clearTimeout(timer);db=request.result;resolve(db);
      };
    });
    const read=async operation=>{
      const database=await open();
      return new Promise((resolve,reject)=>{
        let settled=false,transaction;
        const finish=(error,result)=>{
          if(settled)return;settled=true;clearTimeout(timer);
          if(error)reject(error);else resolve(result);
        };
        const timer=setTimeout(()=>{try{transaction?.abort();}catch{}finish(new Error('Stockage audio illisible.'));},5000);
        try {
          transaction=database.transaction('chunks','readonly');
          const request=operation(transaction.objectStore('chunks'));
          let result;request.onsuccess=()=>{result=request.result;};
          request.onerror=()=>finish(new Error('Stockage audio illisible.'));
          transaction.oncomplete=()=>finish(null,result);
          transaction.onabort=transaction.onerror=()=>finish(new Error('Stockage audio illisible.'));
        } catch {finish(new Error('Stockage audio illisible.'));}
      });
    };
    return {keys:()=>read(store=>store.getAllKeys()),get:id=>read(store=>store.get(id)),close:()=>{
      if(db)db.close();db=undefined;opening=undefined;
    }};
  }
  async function sendOne(record, transport, options = {}) {
    const {subtle=globalThis.crypto?.subtle, cancelled=()=>false,
      sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms)), attempts=3000} = options;
    if (!subtle || typeof subtle.digest !== 'function' || typeof cancelled !== 'function'
        || !Number.isSafeInteger(attempts) || attempts < 1) throw new TypeError('Transfert indisponible.');
    if (record?.type==='audio-stream') throw new Error('Ce fragment doit être transmis par segments.');
    const encoded = new TextEncoder().encode(JSON.stringify(record));
    if (!encoded.length || encoded.length > MAX_BYTES) throw new Error('Donnée trop volumineuse pour cette récupération.');
    if (cancelled()) throw new Error('Récupération interrompue.');
    const hash = await digest(encoded, subtle);
    const staged = await transport.stage(encoded);
    if (!exact(staged,['id','sha256']) || !ID.test(staged.id) || staged.sha256 !== hash)
      throw new Error('Transfert non vérifié.');
    for (let attempt=0; attempt<attempts; attempt++) {
      if (cancelled()) throw new Error('Récupération interrompue.');
      const receipt = await transport.receipt(staged.id);
      if (receipt !== null) {
        if (!exact(receipt,['id','sha256','status']) || receipt.id !== staged.id
            || receipt.sha256 !== hash || !['copied','identical','conflict','preserved','archived','restart','unavailable'].includes(receipt.status))
          throw new Error('Confirmation non vérifiée.');
        if (receipt.status === 'conflict') throw new TransferConflict();
        if (receipt.status === 'restart') throw new TransferRestart();
        if (receipt.status === 'unavailable') throw new Error('La copie ne peut pas être vérifiée.');
        return receipt.status;
      }
      await sleep(100);
    }
    throw new Error('Confirmation de récupération absente.');
  }
  async function sendAll(records, transport, options = {}) {
    const result={copied:0,identical:0};
    for await (const record of records) {
      let status;
      if(record?.type==='audio-stream') {
        if (!(record.bytes instanceof Uint8Array) || record.bytes.length<=INLINE_AUDIO_BYTES
            || record.bytes.length>MAX_STREAM_BYTES) throw new Error('Fragment audio invalide.');
        await sendOne({type:'audio-begin',meta:record.meta,mime:record.mime,length:record.bytes.length},transport,options);
        for(let offset=0;offset<record.bytes.length;offset+=SEGMENT_BYTES) {
          const data=encodeAudio(record.bytes.subarray(offset,offset+SEGMENT_BYTES));
          await sendOne({type:'audio-part',id:record.meta.id,offset,data},transport,options);
        }
        status=await sendOne({type:'audio-end',id:record.meta.id},transport,options);
      } else if(record?.type==='audio-archive-stream') {
        if (!exact(record,['type','id','current','incoming'])) throw new Error('Copie audio invalide.');
        const copy=audioArchiveRecord({id:record.id,current:record.current,incoming:record.incoming});
        const header=value=>({meta:value.meta,mime:value.mime,length:value.bytes.length});
        await sendOne({type:'audio-archive-begin',id:copy.id,current:header(copy.current),incoming:header(copy.incoming)},transport,options);
        for (const side of ['current','incoming']) {
          const bytes=copy[side].bytes;
          for(let offset=0;offset<bytes.length;offset+=SEGMENT_BYTES)
            await sendOne({type:'audio-archive-part',id:copy.id,side,offset,data:encodeAudio(bytes.subarray(offset,offset+SEGMENT_BYTES))},transport,options);
        }
        status=await sendOne({type:'audio-archive-end',id:copy.id},transport,options);
      } else status=await sendOne(record,transport,options);
      if (status==='preserved' || status==='archived') result[status]=(result[status] || 0)+1;
      else result[status]++;
    }
    return result;
  }
  async function receiveOne(transport, storage, store, subtle = globalThis.crypto?.subtle, state = {audio:null}) {
    if (!subtle || typeof subtle.digest !== 'function') throw new Error('Vérification indisponible.');
    const transfer = await transport.read();
    if (transfer === null) return null;
    if (!exact(transfer,['id','sha256','body']) || !ID.test(transfer.id) || !HASH.test(transfer.sha256)
        || !(transfer.body instanceof Uint8Array) || !transfer.body.length || transfer.body.length > MAX_BYTES)
      throw new Error('Transfert invalide.');
    if (await digest(transfer.body, subtle) !== transfer.sha256) throw new Error('Empreinte du transfert invalide.');
    let record;
    try {record=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(transfer.body));}
    catch {throw new Error('Donnée transférée illisible.');}
    if (state.archive && !['audio-archive-begin','audio-archive-part','audio-archive-end'].includes(record?.type))
      throw new Error('Une copie audio est en cours de récupération.');
    let status,afterAck=()=>{};
    const handleAudioConflict=async (outcome, audio)=>{
      if (outcome!=='conflict' || typeof state.onAudioConflict!=='function') return outcome;
      try {
        const choice=await state.onAudioConflict(audio,{id:transfer.id,sha256:transfer.sha256});
        if (!['conflict','archived','restart'].includes(choice)) throw new Error('Décision de récupération invalide.');
        return choice;
      } catch {return 'unavailable';}
    };
    if (record?.type === 'local' && exact(record,['type','key','value'])) {
      status=recovery.copyLocalEntry(storage,record.key,record.value);
      if (status==='conflict' && typeof state.onLocalConflict==='function') {
        try {
          status=await state.onLocalConflict(record,{id:transfer.id,sha256:transfer.sha256});
          if (!['conflict','archived','restart'].includes(status)) throw new Error('Décision de récupération invalide.');
        } catch {status='unavailable';}
      }
    } else if (record?.type === 'audio' && exact(record,['type','meta','mime','data'])) {
      const audio={meta:record.meta,mime:record.mime,bytes:decodeAudio(record.data)};
      status=await handleAudioConflict(await recovery.applyAudio(store,audio,subtle),audio);
    } else if (record?.type === 'audio-begin' && exact(record,['type','meta','mime','length'])) {
      if (state.archive) throw new Error('Une copie audio est en cours de récupération.');
      const meta=recovery.audioMetadata(record.meta);
      if (!exact(record.meta,Object.keys(meta)) || typeof record.mime!=='string' || !record.mime || record.mime.length>256
          || !Number.isSafeInteger(record.length) || record.length<=INLINE_AUDIO_BYTES || record.length>MAX_STREAM_BYTES)
        throw new Error('Fragment audio invalide.');
      const previous=state.audio;
      const same=previous && JSON.stringify(previous.meta)===JSON.stringify(meta)
        && previous.mime===record.mime && previous.buffer.length===record.length;
      if (previous && !same) throw new Error('Un autre fragment est en cours de récupération.');
      if (same && previous.offset===0) status='identical';
      else {
        state.audio={meta,mime:record.mime,buffer:new Uint8Array(record.length),offset:0};
        status='copied';
      }
    } else if (record?.type === 'audio-part' && exact(record,['type','id','offset','data'])) {
      const current=state.audio;
      if (!current || record.id!==current.meta.id || !Number.isSafeInteger(record.offset) || record.offset<0)
        throw new Error('Segment audio inattendu.');
      const bytes=decodeAudio(record.data);
      if (!bytes.length || bytes.length>SEGMENT_BYTES || record.offset+bytes.length>current.buffer.length)
        throw new Error('Segment audio invalide.');
      if (record.offset===current.offset) {
        current.buffer.set(bytes,record.offset);current.offset+=bytes.length;status='copied';
      } else if (record.offset+bytes.length<=current.offset
          && bytes.every((byte,index)=>current.buffer[record.offset+index]===byte)) status='identical';
      else throw new Error('Segment audio incohérent.');
    } else if (record?.type === 'audio-end' && exact(record,['type','id'])) {
      const current=state.audio;
      if (!current || record.id!==current.meta.id || current.offset!==current.buffer.length)
        throw new Error('Fragment audio incomplet.');
      const audio={meta:current.meta,mime:current.mime,bytes:current.buffer};
      status=await handleAudioConflict(await recovery.applyAudio(store,audio,subtle),audio);
      afterAck=()=>{state.audio=null;};
    } else if (record?.type === 'audio-archive-begin' && exact(record,['type','id','current','incoming'])) {
      if (!state.archiveAPI || typeof state.archiveAPI.copy!=='function' || !state.archiveStore || state.audio || !HASH.test(record.id))
        throw new Error('Copies audio indisponibles.');
      const side=value=>{
        if (!exact(value,['meta','mime','length']) || typeof value.mime!=='string' || !value.mime || value.mime.length>256
            || !Number.isSafeInteger(value.length) || value.length<0 || value.length>MAX_STREAM_BYTES)
          throw new Error('Copie audio invalide.');
        const meta=recovery.audioMetadata(value.meta);
        if (!exact(value.meta,Object.keys(meta))) throw new Error('Copie audio invalide.');
        return {meta,mime:value.mime,length:value.length};
      };
      const current=side(record.current),incoming=side(record.incoming);
      const description=JSON.stringify({id:record.id,current,incoming}),previous=state.archive;
      if (previous && previous.description!==description) throw new Error('Une autre copie audio est en cours de récupération.');
      if (previous && previous.current.offset===0 && previous.incoming.offset===0) status='identical';
      else {
        const buffer=value=>({meta:value.meta,mime:value.mime,bytes:new Uint8Array(value.length),offset:0});
        state.archive={id:record.id,description,current:buffer(current),incoming:buffer(incoming)};status='copied';
      }
    } else if (record?.type === 'audio-archive-part' && exact(record,['type','id','side','offset','data'])) {
      const current=state.archive;
      if (!current || current.id!==record.id || !['current','incoming'].includes(record.side)
          || !Number.isSafeInteger(record.offset) || record.offset<0) throw new Error('Segment audio inattendu.');
      const target=current[record.side],bytes=decodeAudio(record.data);
      if (!bytes.length || bytes.length>SEGMENT_BYTES || record.offset+bytes.length>target.bytes.length)
        throw new Error('Segment audio invalide.');
      if (record.offset===target.offset) {target.bytes.set(bytes,record.offset);target.offset+=bytes.length;status='copied';}
      else if (record.offset+bytes.length<=target.offset && bytes.every((byte,index)=>target.bytes[record.offset+index]===byte)) status='identical';
      else throw new Error('Segment audio incohérent.');
    } else if (record?.type === 'audio-archive-end' && exact(record,['type','id'])) {
      const current=state.archive;
      if (!current || record.id!==current.id || current.current.offset!==current.current.bytes.length
          || current.incoming.offset!==current.incoming.bytes.length) throw new Error('Copie audio incomplète.');
      const item=side=>({meta:side.meta,mime:side.mime,bytes:side.bytes});
      status=await state.archiveAPI.copy(state.archiveStore,{id:current.id,current:item(current.current),incoming:item(current.incoming)},subtle);
      if (!['copied','identical'].includes(status)) throw new Error('Copie audio non vérifiée.');
      afterAck=()=>{state.archive=null;};
    } else throw new Error('Format de donnée inconnu.');
    await transport.ack(`${transfer.id}:${transfer.sha256}:${status}`);
    afterAck();
    return status;
  }
  function httpTransport(fetch, token) {
    if (typeof fetch !== 'function' || typeof token !== 'string' || !/^[0-9a-f]{64}$/.test(token))
      throw new TypeError('Canal de récupération invalide.');
    const call = async (path, body, missing=false) => {
      const response=await fetch('/recovery/'+path,{method:'POST',credentials:'omit',cache:'no-store',
        headers:{'X-Kiara-Recovery':token},...(body===undefined?{}:{body})});
      if (missing && response.status===404) return null;
      if (!response.ok) throw new Error('Canal de récupération indisponible.');
      return response;
    };
    return {
      stage:async body=>(await call('stage',body)).json(),
      receipt:async id=>{const response=await call('receipt',id,true);return response ? response.json() : null;},
      read:async()=>{const response=await call('read',undefined,true);return response ? {
        id:response.headers.get('X-Kiara-Transfer-ID'),sha256:response.headers.get('X-Kiara-Record-SHA256'),
        body:new Uint8Array(await response.arrayBuffer())} : null;},
      ack:async receipt=>{await call('ack',receipt);},
      review:async transfer=>{
        if (!exact(transfer,['id','sha256']) || !ID.test(transfer.id) || !HASH.test(transfer.sha256))
          throw new TypeError('Comparaison indisponible.');
        await call('review',`${transfer.id}:${transfer.sha256}`);
      },
      options:async()=>{
        const value=await (await call('options')).json();
        if (!exact(value,['review','preserve','required']) || typeof value.review!=='boolean' || typeof value.preserve!=='boolean'
            || !Array.isArray(value.required) || value.required.length>1024
            || value.required.some(id=>typeof id!=='string' || !ARCHIVE_ID.test(id))
            || new Set(value.required).size!==value.required.length || (!value.review && value.required.length))
          throw new Error('Options de récupération invalides.');
        return value;
      },
      markArchive:async(transfer,id)=>{
        if (!exact(transfer,['id','sha256']) || !ID.test(transfer.id) || !HASH.test(transfer.sha256) || !ARCHIVE_ID.test(id))
          throw new TypeError('Copie de récupération invalide.');
        await call('archive',`${transfer.id}:${transfer.sha256}:${id}`);
      },
      requiredOk:async()=>{await call('required-ok');},
      missingArchive:async()=>{await call('archive-unavailable');},
      fail:async()=>{await call('fail');},
    };
  }
  return {MAX_BYTES, INLINE_AUDIO_BYTES, SEGMENT_BYTES, MAX_STREAM_BYTES, TransferConflict, TransferRestart, localRecord, audioRecord, audioArchiveRecord, sourceRecords, indexedAudioSource,
    sendOne, sendAll, receiveOne, httpTransport};
});
