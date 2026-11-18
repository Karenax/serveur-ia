/* Building blocks for a future origin recovery flow. This module is not loaded
 * by the client yet. Callers must hold exclusive access to the profile and
 * preserve the old origin until recovery and rollback have been verified. */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.kiaraPortalOriginRecovery = api;
})(globalThis, function () {
  'use strict';
  const FIELDS = ['id', 'session_id', 'track', 'seq', 'command_id', 'sha256', 'start_ms', 'duration_ms', 'created_at'];
  const ALLOWED = new Set([...FIELDS, 'blob', 'stableBytes', 'stableMime']);

  function copyLocalEntry(storage, key, value) {
    if (typeof key !== 'string' || typeof value !== 'string') throw new TypeError('Entrée locale invalide.');
    const current = storage.getItem(key);
    if (current !== null) return current === value ? 'identical' : 'conflict';
    // The caller must prevent concurrent writers: localStorage has no compare-and-swap.
    storage.setItem(key, value);
    if (storage.getItem(key) !== value) throw new Error('La copie locale ne peut pas être vérifiée.');
    return 'copied';
  }

  function metadata(record) {
    if (!record || typeof record !== 'object' || Array.isArray(record)) throw new TypeError('Fragment audio invalide.');
    if (Object.keys(record).some(key => !ALLOWED.has(key))) throw new Error('Format du fragment inconnu.');
    const out = {};
    for (const field of FIELDS) {
      const value = record[field];
      if (['seq', 'start_ms', 'duration_ms'].includes(field)) {
        if (!Number.isSafeInteger(value) || value < 0) throw new TypeError('Métadonnées audio invalides.');
      } else if (typeof value !== 'string' || !value) throw new TypeError('Métadonnées audio invalides.');
      out[field] = value;
    }
    if (!/^[a-f0-9]{64}$/i.test(out.sha256)) throw new TypeError('Empreinte audio invalide.');
    if (record.stableMime !== undefined && typeof record.stableMime !== 'string') throw new TypeError('Type audio invalide.');
    return out;
  }

  async function digest(bytes, subtle) {
    const hash = await subtle.digest('SHA-256', bytes);
    return Array.from(new Uint8Array(hash), byte => byte.toString(16).padStart(2, '0')).join('');
  }

  async function prepareAudio(record, subtle = globalThis.crypto?.subtle) {
    const meta = metadata(record);
    if (!subtle || typeof subtle.digest !== 'function') throw new Error('Vérification audio indisponible.');
    if (record.stableBytes !== undefined && !(record.stableBytes instanceof ArrayBuffer)) throw new TypeError('Copie audio invalide.');
    if (record.blob !== undefined && !(record.blob instanceof Blob)) throw new TypeError('Fragment audio illisible.');
    const matches = async bytes => await digest(bytes, subtle) === meta.sha256.toLowerCase();
    const result = (bytes, mime) => ({meta, bytes: bytes.slice(), mime: mime || 'application/octet-stream'});
    // Prefer the durable WebKit copy without depending on its potentially broken Blob.
    if (record.stableBytes instanceof ArrayBuffer) {
      const bytes = new Uint8Array(record.stableBytes);
      if (await matches(bytes)) return result(bytes, record.stableMime || record.blob?.type);
    }
    if (record.blob instanceof Blob) {
      const bytes = new Uint8Array(await record.blob.arrayBuffer());
      if (await matches(bytes)) return result(bytes, record.blob.type || record.stableMime);
    }
    throw new Error('Les octets du fragment ne correspondent pas à leur empreinte.');
  }

  async function applyAudio(store, transfer, subtle = globalThis.crypto?.subtle) {
    if (!transfer || !(transfer.bytes instanceof Uint8Array) || typeof transfer.mime !== 'string' || !transfer.mime)
      throw new TypeError('Transfert audio invalide.');
    // Revalidate the transfer before any write, including its SHA-256.
    const copied = transfer.bytes.slice();
    const candidate = {...transfer.meta, blob: new Blob([copied], {type: transfer.mime}),
      stableBytes: copied.buffer, stableMime: transfer.mime};
    const prepared = await prepareAudio(candidate, subtle);
    const classify = async current => {
      if (!current) return null;
      try {
        const old = await prepareAudio(current, subtle);
        return JSON.stringify(old.meta) === JSON.stringify(prepared.meta) && old.mime === prepared.mime
          ? 'identical' : 'conflict';
      } catch {return 'conflict';} // Preserve an unreadable existing record, too.
    };
    const existing = await classify(await store.get(prepared.meta.id));
    if (existing) return existing;
    try {await store.add(candidate);} catch (error) {
      // IDB add is atomic. If another writer won the race, do not overwrite it.
      if (error?.name !== 'ConstraintError') throw error;
      const raced = await classify(await store.get(prepared.meta.id));
      if (raced) return raced;
      throw error;
    }
    if (await classify(await store.get(prepared.meta.id)) !== 'identical')
      throw new Error('La copie audio ne peut pas être vérifiée.');
    return 'copied';
  }

  return {copyLocalEntry, audioMetadata:metadata, prepareAudio, applyAudio};
});
