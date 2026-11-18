/* Experimental audio conflict journal. The caller must hold exclusive profile
 * access and verify the journal again after a browser restart before migration. */
(function (root, factory) {
  const recovery = typeof module !== 'undefined' && module.exports
    ? require('./portal_origin_recovery.js') : root.kiaraPortalOriginRecovery;
  const api = factory(recovery);
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.kiaraPortalAudioConflictArchive = api;
})(globalThis, function (recovery) {
  'use strict';
  const ID = /^[0-9a-f]{64}$/;
  const MAX_AUDIO_BYTES = 512 * 1024 * 1024;
  const DATABASE = 'kiara-recovery-audio-v1';
  const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));

  function description(prepared) {return {meta:prepared.meta, mime:prepared.mime};}
  function stored(prepared) {
    return {meta:prepared.meta, mime:prepared.mime, bytes:prepared.bytes.slice().buffer};
  }
  async function prepare(value, subtle) {
    if (!exact(value, ['meta','mime','bytes']) || !(value.bytes instanceof ArrayBuffer)
        || value.bytes.byteLength > MAX_AUDIO_BYTES
        || typeof value.mime !== 'string' || !value.mime || value.mime.length > 256)
      throw new Error('Copie audio illisible.');
    const meta = recovery.audioMetadata(value.meta);
    if (!exact(value.meta, Object.keys(meta))) throw new Error('Copie audio illisible.');
    const item = await recovery.prepareAudio({...meta, stableBytes:value.bytes, stableMime:value.mime}, subtle);
    if (item.mime !== value.mime) throw new Error('Copie audio illisible.');
    return item;
  }
  async function fingerprint(current, incoming, subtle) {
    if (!subtle || typeof subtle.digest !== 'function') throw new Error('Vérification audio indisponible.');
    const bytes = new TextEncoder().encode(JSON.stringify({version:1,current:description(current),incoming:description(incoming)}));
    return Array.from(new Uint8Array(await subtle.digest('SHA-256', bytes)), byte => byte.toString(16).padStart(2, '0')).join('');
  }
  function same(left, right) {return JSON.stringify(description(left)) === JSON.stringify(description(right));}

  async function read(store, id, subtle = globalThis.crypto?.subtle) {
    if (typeof id !== 'string' || !ID.test(id)) throw new Error('Identifiant audio invalide.');
    const record = await store.get(id);
    if (!exact(record, ['id','version','current','incoming']) || record.id !== id || record.version !== 1)
      throw new Error('Copie audio indisponible.');
    const current = await prepare(record.current, subtle), incoming = await prepare(record.incoming, subtle);
    if (current.meta.id !== incoming.meta.id || same(current, incoming)
        || await fingerprint(current, incoming, subtle) !== id)
      throw new Error('Copie audio non vérifiée.');
    return {id, current, incoming};
  }

  async function verify(value, subtle = globalThis.crypto?.subtle) {
    if (!exact(value,['id','current','incoming']) || typeof value.id !== 'string' || !ID.test(value.id))
      throw new Error('Copie audio invalide.');
    const candidate = side => {
      if (!exact(side,['meta','mime','bytes']) || !(side.bytes instanceof Uint8Array)
          || side.bytes.byteLength > MAX_AUDIO_BYTES) throw new Error('Copie audio invalide.');
      const meta=recovery.audioMetadata(side.meta);
      if (!exact(side.meta,Object.keys(meta))) throw new Error('Copie audio invalide.');
      return {meta,mime:side.mime,bytes:side.bytes.slice().buffer};
    };
    // Snapshot both transfers before awaiting any operation; the caller may
    // reuse its buffers as soon as copying has completed.
    const rawCurrent=candidate(value.current), rawIncoming=candidate(value.incoming);
    const current=await prepare(rawCurrent,subtle), incoming=await prepare(rawIncoming,subtle);
    if (current.meta.id!==incoming.meta.id || same(current,incoming)
        || await fingerprint(current,incoming,subtle)!==value.id) throw new Error('Copie audio non vérifiée.');
    return {id:value.id,current,incoming};
  }

  async function copy(store, value, subtle = globalThis.crypto?.subtle) {
    const {id,current,incoming}=await verify(value,subtle);
    let outcome='identical';
    if (!(await store.get(id))) {
      try {await store.add({id,version:1,current:stored(current),incoming:stored(incoming)});outcome='copied';}
      catch (error) {if (error?.name!=='ConstraintError') throw error;}
    }
    const saved=await read(store,id,subtle);
    if (!same(saved.current,current) || !same(saved.incoming,incoming)) throw new Error('Copie audio incohérente.');
    return outcome;
  }

  async function archive(store, chunks, incomingRecord, subtle = globalThis.crypto?.subtle) {
    const incoming = await recovery.prepareAudio(incomingRecord, subtle);
    const current = await recovery.prepareAudio(await chunks.get(incoming.meta.id), subtle);
    if ([current, incoming].some(item => item.bytes.byteLength > MAX_AUDIO_BYTES || item.mime.length > 256))
      throw new Error('Fragment audio trop volumineux pour cette récupération.');
    if (current.meta.id !== incoming.meta.id || same(current, incoming))
      throw new Error('Conflit audio invalide.');
    const id = await fingerprint(current, incoming, subtle);
    const ensureCurrent = async () => {
      const latest = await recovery.prepareAudio(await chunks.get(incoming.meta.id), subtle);
      if (!same(current, latest)) throw new Error('Le fragment audio courant a changé.');
    };
    await ensureCurrent();
    const existing = await store.get(id);
    if (!existing) {
      try {await store.add({id, version:1, current:stored(current), incoming:stored(incoming)});}
      catch (error) {
        if (error?.name !== 'ConstraintError') throw error;
      }
    }
    const saved = await read(store, id, subtle);
    if (!same(saved.current, current) || !same(saved.incoming, incoming))
      throw new Error('Copie audio incohérente.');
    await ensureCurrent();
    return id;
  }

  async function keys(store) {
    if (!store || typeof store.keys !== 'function') throw new Error('Copies audio indisponibles.');
    const values = await store.keys();
    if (!Array.isArray(values) || values.length > 3000
        || values.some(id => typeof id !== 'string' || !ID.test(id))
        || new Set(values).size !== values.length) throw new Error('Copies audio illisibles.');
    return values.slice().sort();
  }

  async function find(store, chunks, incomingRecord, subtle = globalThis.crypto?.subtle) {
    const incoming = await recovery.prepareAudio(incomingRecord, subtle);
    const current = await recovery.prepareAudio(await chunks.get(incoming.meta.id), subtle);
    if (current.meta.id !== incoming.meta.id || same(current, incoming)) throw new Error('Conflit audio invalide.');
    const before = await keys(store);
    let found = null;
    // Check all entries, including those after a match: an unreadable archived
    // copy must never be silently ignored by a successful recovery.
    for (const id of before) {
      const saved = await read(store, id, subtle);
      if (same(saved.incoming, incoming) && found === null) found = id;
    }
    const after = await keys(store);
    if (JSON.stringify(before) !== JSON.stringify(after)) throw new Error('Les copies audio ont changé.');
    const latest = await recovery.prepareAudio(await chunks.get(incoming.meta.id), subtle);
    if (!same(current, latest)) throw new Error('Le fragment audio courant a changé.');
    if (found !== null && !same((await read(store, found, subtle)).incoming, incoming))
      throw new Error('La copie audio a changé.');
    return found;
  }

  async function list(store, subtle = globalThis.crypto?.subtle) {
    const before = await keys(store), result = [];
    for (const id of before) {
      const saved = await read(store, id, subtle);
      // Keep the audio bytes out of the list; read only the selected copy when
      // it is needed. A pair may contain up to a gigabyte in total.
      result.push({id, current:description(saved.current), incoming:description(saved.incoming)});
    }
    const after = await keys(store);
    if (JSON.stringify(before) !== JSON.stringify(after)) throw new Error('Les copies audio ont changé.');
    return result;
  }

  async function open(indexedDB, {create = false, allowMissing = false, timeout = 5000} = {}) {
    if (!indexedDB || typeof indexedDB.open !== 'function' || typeof indexedDB.databases !== 'function'
        || !Number.isSafeInteger(timeout) || timeout < 1 || typeof create !== 'boolean'
        || typeof allowMissing !== 'boolean' || (create && allowMissing))
      throw new TypeError('Stockage audio indisponible.');
    // WebKit may leave an empty database even when a creation transaction is
    // aborted. Check for the name before any read-only open. Exclusive profile
    // access is still necessary between enumeration and opening the database.
    let databases, enumerationTimer;
    try {
      databases = await Promise.race([
        Promise.resolve().then(() => indexedDB.databases()),
        new Promise((_, reject) => {enumerationTimer = setTimeout(() => reject(new Error()), timeout);}),
      ]);
    } catch {throw new Error('Copies audio indisponibles.');}
    finally {clearTimeout(enumerationTimer);}
    if (!Array.isArray(databases) || databases.some(item => !item || typeof item.name !== 'string'
        || !Number.isSafeInteger(item.version) || item.version < 1)
        || new Set(databases.map(item => item.name)).size !== databases.length)
      throw new Error('Copies audio indisponibles.');
    const existing = databases.find(item => item.name === DATABASE);
    if (!existing && allowMissing) return null;
    if ((!create && !existing) || (existing && existing.version !== 1))
      throw new Error('Copies audio indisponibles.');
    return new Promise((resolve, reject) => {
      let request, settled = false;
      const fail = () => {
        if (!settled) {settled = true;clearTimeout(timer);reject(new Error('Copies audio indisponibles.'));}
      };
      const timer = setTimeout(fail, timeout);
      try {request = indexedDB.open(DATABASE, 1);} catch {fail();return;}
      request.onupgradeneeded = event => {
        try {
          if (!create || event.oldVersion !== 0) {request.transaction.abort();return;}
          request.result.createObjectStore('copies', {keyPath:'id'});
        } catch {try {request.transaction.abort();} catch {}}
      };
      request.onblocked = request.onerror = fail;
      request.onsuccess = () => {
        const db = request.result;
        if (settled) {db.close();return;}
        try {
          if (db.version !== 1 || db.objectStoreNames.length !== 1 || !db.objectStoreNames.contains('copies')) throw new Error();
          const store = db.transaction('copies', 'readonly').objectStore('copies');
          if (store.keyPath !== 'id' || store.indexNames.length !== 0) throw new Error();
        } catch {db.close();fail();return;}
        settled = true;clearTimeout(timer);
        db.onversionchange = () => db.close();
        const transaction = (mode, action) => new Promise((resolveOperation, rejectOperation) => {
          let tx, result, done = false;
          const finish = (error) => {
            if (done) return;done = true;clearTimeout(operationTimer);
            if (error) rejectOperation(error);else resolveOperation(result);
          };
          const operationTimer = setTimeout(() => {try {tx?.abort();} catch {}finish(new Error('Copies audio indisponibles.'));}, timeout);
          try {
            tx = db.transaction('copies', mode);
            const query = action(tx.objectStore('copies'));
            query.onsuccess = () => {result = query.result;};
            tx.oncomplete = () => finish();
            tx.onabort = tx.onerror = () => finish(tx.error || query.error || new Error('Copies audio indisponibles.'));
          } catch (error) {finish(error);}
        });
        resolve({get:id => transaction('readonly', store => store.get(id)),
          add:value => transaction('readwrite', store => store.add(value)),
          keys:() => transaction('readonly', store => store.getAllKeys()), close:() => db.close()});
      };
    });
  }
  return {DATABASE, archive, read, verify, copy, find, list, open};
});
