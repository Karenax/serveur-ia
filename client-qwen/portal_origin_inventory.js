/* Read-only building block for a future portal recovery flow. The caller must
 * hold exclusive access to the profile for the full inventory and migration. */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.kiaraPortalOriginInventory = api;
})(globalThis, function () {
  'use strict';
  const AUDIO_DB = 'agent-meeting-audio-v1';
  const ARCHIVE_DB = 'kiara-recovery-audio-v1';
  class InventoryUnavailable extends Error {
    constructor(message) {super(message); this.name = 'InventoryUnavailable';}
  }

  function localKeys(storage) {
    try {
      const length = storage.length, keys = [], seen = new Set();
      if (!Number.isSafeInteger(length) || length < 0) throw new Error();
      for (let i = 0; i < length; i++) {
        const key = storage.key(i);
        if (typeof key !== 'string' || seen.has(key)) throw new Error();
        keys.push(key); seen.add(key);
      }
      if (storage.length !== length) throw new Error();
      return keys;
    } catch {throw new InventoryUnavailable('Les données locales ne peuvent pas être inventoriées.');}
  }

  function countAudio(indexedDB, timeoutMs) {
    return new Promise((resolve, reject) => {
      let settled = false, dbHandle;
      const finish = (error, count) => {
        if (settled) return;
        settled = true; clearTimeout(timer);
        if (dbHandle) {dbHandle.close(); dbHandle = undefined;}
        error ? reject(error) : resolve(count);
      };
      const unavailable = () => new InventoryUnavailable('La base audio locale ne peut pas être inventoriée.');
      const timer = setTimeout(() => finish(unavailable()), timeoutMs);
      let request;
      try {request = indexedDB.open(AUDIO_DB);} catch {finish(unavailable()); return;}
      request.onupgradeneeded = () => {
        // A disappeared database must not be recreated by an inventory.
        try {request.transaction.abort();} catch {}
        finish(unavailable());
      };
      request.onblocked = request.onerror = () => finish(unavailable());
      request.onsuccess = () => {
        const db = request.result;
        if (settled) {db.close(); return;}
        dbHandle = db;
        try {
          if (db.version !== 1 || db.objectStoreNames.length !== 1 || !db.objectStoreNames.contains('chunks')) throw new Error();
          const tx = db.transaction('chunks', 'readonly'), store = tx.objectStore('chunks');
          if (store.keyPath !== 'id' || store.indexNames.length !== 1 || !store.indexNames.contains('session_id')) throw new Error();
          const index = store.index('session_id');
          if (index.keyPath !== 'session_id' || index.unique || index.multiEntry) throw new Error();
          const count = store.count();
          let result;
          count.onsuccess = () => {result = count.result;};
          count.onerror = () => finish(unavailable());
          tx.oncomplete = () => Number.isSafeInteger(result) && result >= 0 ? finish(null, result) : finish(unavailable());
          tx.onabort = tx.onerror = () => finish(unavailable());
        } catch {finish(unavailable());}
      };
    });
  }

  async function inventory(storage, indexedDB, timeoutMs = 5000, options = {}) {
    if (!Number.isSafeInteger(timeoutMs) || timeoutMs < 1) throw new TypeError('Délai invalide.');
    if (!options || typeof options !== 'object' || Array.isArray(options)
        || Object.keys(options).some(key => !['audioArchive','audioArchiveIds'].includes(key))
        || (Object.hasOwn(options,'audioArchiveIds') && typeof options.audioArchiveIds!=='boolean')) throw new TypeError('Inventaire invalide.');
    const includeArchives=Object.hasOwn(options,'audioArchive');
    const includeIds=options.audioArchiveIds===true;
    if (includeIds && !includeArchives) throw new TypeError('Inventaire invalide.');
    if (includeArchives && (!options.audioArchive || typeof options.audioArchive.open !== 'function'
        || typeof options.audioArchive.list !== 'function')) throw new TypeError('Inventaire invalide.');
    const keys = localKeys(storage);
    if (!indexedDB || typeof indexedDB.databases !== 'function')
      throw new InventoryUnavailable('La liste des bases locales est indisponible.');
    let databases, timer;
    try {
      databases = await Promise.race([
        Promise.resolve().then(() => indexedDB.databases()),
        new Promise((_, reject) => {timer = setTimeout(() => reject(new Error()), timeoutMs);}),
      ]);
    } catch {throw new InventoryUnavailable('La liste des bases locales est indisponible.');}
    finally {clearTimeout(timer);}
    if (!Array.isArray(databases) || databases.some(db => !db || typeof db.name !== 'string' || !Number.isSafeInteger(db.version) || db.version < 1))
      throw new InventoryUnavailable('La liste des bases locales est illisible.');
    if (new Set(databases.map(db => db.name)).size !== databases.length)
      throw new InventoryUnavailable('La liste des bases locales est incohérente.');
    const archive = databases.find(db => db.name === ARCHIVE_DB);
    if (databases.some(db => ![AUDIO_DB,ARCHIVE_DB].includes(db.name) || db.version !== 1)
        || (archive && !includeArchives))
      throw new InventoryUnavailable('Une base locale utilise un format inconnu.');
    const audioChunks = databases.some(db => db.name === AUDIO_DB) ? await countAudio(indexedDB, timeoutMs) : 0;
    let audioArchiveIds = [];
    if (includeArchives) {
      const api=options.audioArchive;
      if (archive) {
        let timer;
        try {
          audioArchiveIds=await Promise.race([
            (async()=>{const store=await api.open(indexedDB);try{const copies=await api.list(store);
              if (!Array.isArray(copies) || copies.length>3000 || copies.some(item=>!item || typeof item.id!=='string'
                  || !/^[0-9a-f]{64}$/.test(item.id))) throw new Error();
              const ids=copies.map(item=>item.id);if(new Set(ids).size!==ids.length)throw new Error();return ids.sort();
            }finally{store.close();}})(),
            new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error()),timeoutMs);}),
          ]);
        } catch {throw new InventoryUnavailable('Les copies audio ne peuvent pas être inventoriées.');}
        finally {clearTimeout(timer);}
      }
    }
    // No values, identifiers or audio contents are returned by the inventory.
    return {localEntries: keys.length, audioChunks,...(includeArchives ? {audioArchives:audioArchiveIds.length} : {}),
      ...(includeIds ? {audioArchiveIds} : {})};
  }

  return {inventory, InventoryUnavailable};
});
