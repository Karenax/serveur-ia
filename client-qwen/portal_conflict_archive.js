/* Experimental conflict journal. The caller must hold exclusive profile access.
 * Records stay in the destination browser storage; no data is logged or sent.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.kiaraPortalConflictArchive = api;
})(globalThis, function () {
  'use strict';
  const PREFIX = 'kiara:recovery:conflict:v1:';
  const MAX_BYTES = 32 * 1024 * 1024;
  const ID = /^[0-9a-f]{64}$/;

  function encoded(record) {
    const text = JSON.stringify(record);
    const bytes = new TextEncoder().encode(text);
    if (bytes.length > MAX_BYTES) throw new Error('Conflit trop volumineux pour être conservé.');
    return {text, bytes};
  }

  async function fingerprint(bytes, subtle) {
    if (!subtle || typeof subtle.digest !== 'function') throw new Error('Vérification indisponible.');
    return Array.from(new Uint8Array(await subtle.digest('SHA-256', bytes)),
      byte => byte.toString(16).padStart(2, '0')).join('');
  }

  function validate(record) {
    if (!record || typeof record !== 'object' || Array.isArray(record)
        || Object.keys(record).length !== 4 || record.version !== 1
        || typeof record.key !== 'string' || typeof record.current !== 'string'
        || typeof record.incoming !== 'string' || record.current === record.incoming
        || record.key.startsWith(PREFIX)) throw new Error('Conflit local invalide.');
    return {version: 1, key: record.key, current: record.current, incoming: record.incoming};
  }

  async function read(storage, id, subtle = globalThis.crypto?.subtle) {
    if (typeof id !== 'string' || !ID.test(id)) throw new Error('Identifiant de conflit invalide.');
    const saved = storage.getItem(PREFIX + id);
    if (typeof saved !== 'string') throw new Error('Copie de conflit indisponible.');
    let record;
    try {record = validate(JSON.parse(saved));} catch {throw new Error('Copie de conflit illisible.');}
    const {text, bytes} = encoded(record);
    if (saved !== text || await fingerprint(bytes, subtle) !== id || storage.getItem(PREFIX + id) !== saved)
      throw new Error('Copie de conflit non vérifiée.');
    return record;
  }

  function archiveKeys(storage) {
    const count = storage.length, result = [];
    if (!Number.isSafeInteger(count) || count < 0) throw new Error('Stockage local indisponible.');
    for (let index = 0; index < count; index++) {
      const key = storage.key(index);
      if (typeof key !== 'string') throw new Error('Stockage local modifié.');
      if (key.startsWith(PREFIX)) result.push(key);
    }
    if (storage.length !== count || new Set(result).size !== result.length || result.length > 10000)
      throw new Error('Stockage local modifié.');
    return result.sort();
  }

  async function list(storage, subtle = globalThis.crypto?.subtle) {
    const keys = archiveKeys(storage), result = [];
    for (const key of keys) {
      const id = key.slice(PREFIX.length);
      result.push({id, ...(await read(storage, id, subtle))});
    }
    const after = archiveKeys(storage);
    if (keys.length !== after.length || keys.some((key, index) => key !== after[index]))
      throw new Error('Les copies de conflit ont changé.');
    // Re-read each archived value after enumeration, not just the key list.
    for (const item of result) {
      const record = await read(storage, item.id, subtle);
      if (JSON.stringify(record) !== JSON.stringify({version:item.version, key:item.key,
                                                     current:item.current, incoming:item.incoming}))
        throw new Error('Les copies de conflit ont changé.');
    }
    return result;
  }

  async function archive(storage, key, incoming, subtle = globalThis.crypto?.subtle) {
    if (typeof key !== 'string' || typeof incoming !== 'string' || key.startsWith(PREFIX))
      throw new Error('Conflit local invalide.');
    const current = storage.getItem(key);
    const record = validate({version: 1, key, current, incoming});
    const {text, bytes} = encoded(record);
    const id = await fingerprint(bytes, subtle), archiveKey = PREFIX + id;
    if (storage.getItem(key) !== current) throw new Error('La version courante a changé.');
    const previous = storage.getItem(archiveKey);
    if (previous !== null && previous !== text) throw new Error('Copie de conflit incohérente.');
    if (previous === null) storage.setItem(archiveKey, text);
    if (storage.getItem(archiveKey) !== text || storage.getItem(key) !== current)
      throw new Error('La conservation du conflit ne peut pas être vérifiée.');
    await read(storage, id, subtle);
    if (storage.getItem(key) !== current) throw new Error('La version courante a changé.');
    return id;
  }

  async function find(storage, key, incoming, subtle = globalThis.crypto?.subtle) {
    if (typeof key !== 'string' || typeof incoming !== 'string' || key.startsWith(PREFIX))
      throw new Error('Conflit local invalide.');
    const current = storage.getItem(key);
    if (typeof current !== 'string' || current === incoming) throw new Error('Conflit local invalide.');
    const saved = await list(storage, subtle);
    if (storage.getItem(key) !== current) throw new Error('La version courante a changé.');
    const found = saved.find(item => item.key === key && item.incoming === incoming);
    return found ? found.id : null;
  }

  // A successful synchronous localStorage read does not prove that a browser
  // has flushed its database to disk. This journal deliberately provides no
  // replacement operation until persistence across process restart is proven.
  return {PREFIX, archive, read, list, find};
});
