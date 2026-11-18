'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {webcrypto} = require('node:crypto');
const {copyLocalEntry, prepareAudio, applyAudio} = require('./portal_origin_recovery.js');

class MemoryStorage {
  constructor(entries = []) {this.values = new Map(entries);}
  getItem(key) {return this.values.has(key) ? this.values.get(key) : null;}
  setItem(key, value) {this.values.set(key, value);}
}
class MemoryChunks {
  constructor(records = []) {this.records = new Map(records.map(record => [record.id, record]));}
  async get(id) {return this.records.get(id);}
  async add(record) {
    if (this.records.has(record.id)) throw Object.assign(new Error('exists'), {name: 'ConstraintError'});
    this.records.set(record.id, record);
  }
}
async function makeRecord(bytes = [1, 8, 9], changes = {}) {
  const data = new Uint8Array(bytes);
  const hash = Buffer.from(await webcrypto.subtle.digest('SHA-256', data)).toString('hex');
  return {id:'fiction:microphone:1', session_id:'fiction', track:'microphone', seq:1,
    command_id:'command-fictive', sha256:hash, start_ms:10, duration_ms:20,
    created_at:'2026-11-17T00:00:00Z', blob:new Blob([data], {type:'audio/wav'}), ...changes};
}

test('les copies locales sont vérifiées, rejouables et ne remplacent aucune version', () => {
  const storage = new MemoryStorage([['conflict', 'valeur existante']]);
  assert.equal(copyLocalEntry(storage, 'draft', 'brouillon fictif'), 'copied');
  assert.equal(copyLocalEntry(storage, 'draft', 'brouillon fictif'), 'identical');
  assert.equal(copyLocalEntry(storage, 'conflict', 'autre valeur'), 'conflict');
  assert.equal(storage.getItem('conflict'), 'valeur existante');
  assert.throws(() => copyLocalEntry({getItem:()=>null, setItem:()=>{throw Error('quota');}}, 'draft', 'v'), /quota/);
  assert.throws(() => copyLocalEntry({getItem:()=>null, setItem:()=>{}}, 'draft', 'v'), /vérifiée/);
});

test('la copie audio vérifie les octets et reste idempotente après interruption', async () => {
  const original = await makeRecord();
  const transfer = await prepareAudio(original, webcrypto.subtle);
  const store = new MemoryChunks();
  assert.equal(await applyAudio(store, transfer, webcrypto.subtle), 'copied');
  assert.equal(await applyAudio(store, transfer, webcrypto.subtle), 'identical');
  const stored = await store.get(original.id);
  assert.deepEqual(Array.from(new Uint8Array(await stored.blob.arrayBuffer())), [1,8,9]);
  assert.deepEqual(Array.from(new Uint8Array(stored.stableBytes)), [1,8,9]);
  assert.equal(stored.command_id, original.command_id);
  assert.deepEqual(Array.from(new Uint8Array(await original.blob.arrayBuffer())), [1,8,9]);
});

test('un conflit audio et un format inconnu conservent la version existante', async () => {
  const original = await makeRecord(), other = await makeRecord([2, 8, 9]);
  const store = new MemoryChunks([other]);
  const transfer = await prepareAudio(original, webcrypto.subtle);
  assert.equal(await applyAudio(store, transfer, webcrypto.subtle), 'conflict');
  assert.equal(await store.get(other.id), other);
  const unknown = {...other, future_field:'do not discard'};
  const unknownStore = new MemoryChunks([unknown]);
  assert.equal(await applyAudio(unknownStore, transfer, webcrypto.subtle), 'conflict');
  assert.equal(await unknownStore.get(other.id), unknown);
  await assert.rejects(prepareAudio(unknown, webcrypto.subtle), /inconnu/);
});

test('une copie WebKit valide reste utilisable si le Blob est cassé, et inversement', async () => {
  const record = await makeRecord();
  const valid = await record.blob.arrayBuffer();
  const brokenBlob = new Blob([[0,0,0]], {type:'audio/wav'});
  brokenBlob.arrayBuffer = async () => {throw Error('Blob illisible');};
  const first = await prepareAudio({...record, blob:brokenBlob, stableBytes:valid, stableMime:'audio/wav'}, webcrypto.subtle);
  assert.deepEqual(Array.from(first.bytes), [1,8,9]);
  const second = await prepareAudio({...record, stableBytes:new Uint8Array([9]).buffer}, webcrypto.subtle);
  assert.deepEqual(Array.from(second.bytes), [1,8,9]);
  const fallback = await prepareAudio({...record, stableBytes:new Uint8Array([9]).buffer, stableMime:'audio/other'}, webcrypto.subtle);
  assert.equal(fallback.mime, 'audio/wav');
  await assert.rejects(prepareAudio({...record, blob:new Blob(['wrong'])}, webcrypto.subtle), /empreinte/);
});

test('un transfert altéré ou une écriture concurrente ne remplace aucune donnée', async () => {
  const record = await makeRecord(), other = await makeRecord([3,4,5]);
  const transfer = await prepareAudio(record, webcrypto.subtle), store = new MemoryChunks();
  const altered = {...transfer, bytes:new Uint8Array([0])};
  await assert.rejects(applyAudio(store, altered, webcrypto.subtle), /empreinte/);
  assert.equal(await store.get(record.id), undefined);
  let first = true;
  const racing = {get:async id => first ? undefined : other, add:async () => {first=false;throw Object.assign(new Error('race'), {name:'ConstraintError'});}};
  assert.equal(await applyAudio(racing, transfer, webcrypto.subtle), 'conflict');
  assert.equal(await racing.get(record.id), other);
});

test('un échec de stockage ne supprime pas la source et ne masque pas l’erreur', async () => {
  const record = await makeRecord(), transfer = await prepareAudio(record, webcrypto.subtle);
  const store = {get:async () => undefined, add:async () => {throw new Error('quota indisponible');}};
  await assert.rejects(applyAudio(store, transfer, webcrypto.subtle), /quota/);
  assert.deepEqual(Array.from(new Uint8Array(await record.blob.arrayBuffer())), [1,8,9]);
});
