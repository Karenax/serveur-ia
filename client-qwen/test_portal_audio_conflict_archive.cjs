'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {webcrypto} = require('node:crypto');
const audio = require('./portal_audio_conflict_archive.js');

class Store {
  constructor(records = []) {this.values = new Map(records.map(value => [value.id, structuredClone(value)]));}
  async get(id) {const value = this.values.get(id);return value && structuredClone(value);}
  async keys() {return [...this.values.keys()];}
  async add(value) {
    if (this.values.has(value.id)) throw Object.assign(new Error('exists'), {name:'ConstraintError'});
    this.values.set(value.id, structuredClone(value));
  }
}
async function record(bytes, changes = {}) {
  const data = new Uint8Array(bytes);
  const sha256 = Buffer.from(await webcrypto.subtle.digest('SHA-256', data)).toString('hex');
  return {id:'fictif:micro:1', session_id:'fictif', track:'microphone', seq:1,
    command_id:'commande', sha256, start_ms:0, duration_ms:100,
    created_at:'2026-11-17T00:00:00Z', blob:new Blob([data], {type:'audio/wav'}), ...changes};
}

test('conserve les deux versions vérifiées sans modifier le fragment en cours', async () => {
  const current = await record([1,2,3]), incoming = await record([4,5,6]);
  const chunks = new Store([current]), journal = new Store();
  const id = await audio.archive(journal, chunks, incoming, webcrypto.subtle);
  assert.match(id, /^[0-9a-f]{64}$/);
  assert.equal(await audio.archive(journal, chunks, incoming, webcrypto.subtle), id);
  const saved = await audio.read(journal, id, webcrypto.subtle);
  assert.deepEqual([...saved.current.bytes], [1,2,3]);
  assert.deepEqual([...saved.incoming.bytes], [4,5,6]);
  assert.deepEqual([...new Uint8Array(await (await chunks.get(current.id)).blob.arrayBuffer())], [1,2,3]);
  assert.equal(journal.values.size, 1);
});

test('refuse une copie modifiée ou illisible', async () => {
  const current = await record([1]), incoming = await record([2]);
  const chunks = new Store([current]), journal = new Store();
  const id = await audio.archive(journal, chunks, incoming, webcrypto.subtle);
  journal.values.get(id).incoming.bytes = new Uint8Array([9]).buffer;
  await assert.rejects(audio.read(journal, id, webcrypto.subtle));
  await assert.rejects(audio.archive(journal, chunks, incoming, webcrypto.subtle));
  assert.deepEqual([...new Uint8Array(await (await chunks.get(current.id)).blob.arrayBuffer())], [1]);
});

test('refuse des métadonnées de copie inconnues même si les octets sont valides', async () => {
  const current = await record([1]), incoming = await record([2]);
  const journal = new Store(), id = await audio.archive(journal, new Store([current]), incoming, webcrypto.subtle);
  journal.values.get(id).incoming.meta.future_field = 'à préserver';
  await assert.rejects(audio.read(journal, id, webcrypto.subtle), /inconnu|illisible/);
});

test('un contrôle en lecture ne crée pas une base absente ou inconnue', async () => {
  let opens = 0;
  const indexedDB = {databases:async () => [], open:() => {opens++;throw Error('must not open');}};
  await assert.rejects(audio.open(indexedDB));
  assert.equal(opens, 0);
  assert.equal(await audio.open(indexedDB,{allowMissing:true}),null);
  await assert.rejects(audio.open(indexedDB,{allowMissing:true,create:true}),/indisponible/);
  assert.equal(opens, 0);
  indexedDB.databases = async () => [{name:audio.DATABASE,version:2}];
  await assert.rejects(audio.open(indexedDB));
  assert.equal(opens, 0);
  indexedDB.databases = () => new Promise(() => {});
  await assert.rejects(audio.open(indexedDB, {timeout:5}));
  assert.equal(opens, 0);
});

test('retrouve la copie source même lorsque le fragment courant a évolué', async () => {
  const current = await record([1]), incoming = await record([2]), newer = await record([3]);
  const journal = new Store(), chunks = new Store([current]);
  assert.equal(await audio.find(journal, chunks, incoming, webcrypto.subtle), null);
  const id = await audio.archive(journal, chunks, incoming, webcrypto.subtle);
  chunks.values.set(current.id, newer);
  assert.equal(await audio.find(journal, chunks, incoming, webcrypto.subtle), id);
  const summaries=await audio.list(journal, webcrypto.subtle);
  assert.equal(summaries.length, 1);assert.equal(summaries[0].id, id);
  assert.equal(summaries[0].incoming.meta.id, current.id);
  assert.equal(Object.hasOwn(summaries[0].incoming, 'bytes'), false);
  assert.deepEqual([...new Uint8Array(await (await chunks.get(current.id)).blob.arrayBuffer())], [3]);
});

test('ne masque pas une autre copie audio altérée et détecte un changement du fragment', async () => {
  const current = await record([1]), incoming = await record([2]), newer = await record([3]);
  const journal = new Store(), chunks = new Store([current]);
  await audio.archive(journal, chunks, incoming, webcrypto.subtle);
  journal.values.set('f'.repeat(64), {id:'f'.repeat(64)});
  await assert.rejects(audio.find(journal, chunks, incoming, webcrypto.subtle));
  journal.values.delete('f'.repeat(64));
  const get = chunks.get.bind(chunks);let reads=0;
  chunks.get = async id => ++reads===1 ? get(id) : newer;
  await assert.rejects(audio.find(journal, chunks, incoming, webcrypto.subtle), /changé/);
});

test('refuse un fragment courant modifié pendant la conservation', async () => {
  const current = await record([1]), incoming = await record([2]), newer = await record([3]);
  const chunks = new Store([current]), journal = new Store();
  const add = journal.add.bind(journal);
  journal.add = async value => {await add(value);chunks.values.set(current.id, newer);};
  await assert.rejects(audio.archive(journal, chunks, incoming, webcrypto.subtle), /changé/);
  assert.deepEqual([...new Uint8Array(await (await chunks.get(current.id)).blob.arrayBuffer())], [3]);
  assert.equal(journal.values.size, 1);
});

test('refuse un fragment courant illisible et propage les erreurs de stockage', async () => {
  const current = await record([1]), incoming = await record([2]);
  const invalid = {...current, future_field:'à conserver'};
  await assert.rejects(audio.archive(new Store(), new Store([invalid]), incoming, webcrypto.subtle));
  const journal = new Store();journal.add = async () => {throw Error('quota');};
  await assert.rejects(audio.archive(journal, new Store([current]), incoming, webcrypto.subtle), /quota/);
  assert.deepEqual([...new Uint8Array(await incoming.blob.arrayBuffer())], [2]);
});

test('une écriture concurrente identique est vérifiée, une écriture incohérente est refusée', async () => {
  const current = await record([1]), incoming = await record([2]);
  const chunks = new Store([current]), journal = new Store();
  const add = journal.add.bind(journal);
  journal.add = async value => {await add(value);throw Object.assign(new Error('race'), {name:'ConstraintError'});};
  const id = await audio.archive(journal, chunks, incoming, webcrypto.subtle);
  assert.equal((await audio.read(journal, id, webcrypto.subtle)).id, id);
  const bad = new Store();
  bad.add = async value => {bad.values.set(value.id, {id:value.id});throw Object.assign(new Error('race'), {name:'ConstraintError'});};
  await assert.rejects(audio.archive(bad, chunks, incoming, webcrypto.subtle));
});

test('une archive audio est copiée et rejouée sans altérer sa source',async()=>{
  const current=await record([1,2,3]),incoming=await record([4,5,6]),source=new Store(),destination=new Store();
  const id=await audio.archive(source,new Store([current]),incoming,webcrypto.subtle);
  const transfer=await audio.read(source,id,webcrypto.subtle);
  assert.equal(await audio.copy(destination,transfer,webcrypto.subtle),'copied');
  assert.equal(await audio.copy(destination,transfer,webcrypto.subtle),'identical');
  assert.deepEqual([...(await audio.read(destination,id,webcrypto.subtle)).incoming.bytes],[4,5,6]);
  assert.deepEqual([...(await audio.read(source,id,webcrypto.subtle)).current.bytes],[1,2,3]);
});

test('une archive altérée ou une destination incohérente ne sont jamais remplacées',async()=>{
  const source=new Store(),chunks=new Store([await record([1])]),id=await audio.archive(source,chunks,await record([2]),webcrypto.subtle);
  const transfer=await audio.read(source,id,webcrypto.subtle),destination=new Store();
  transfer.current.bytes[0]=9;
  await assert.rejects(audio.copy(destination,transfer,webcrypto.subtle));assert.equal(destination.values.size,0);
  const intact=await audio.read(source,id,webcrypto.subtle);destination.values.set(id,{id,unknown:'preserve'});
  await assert.rejects(audio.copy(destination,intact,webcrypto.subtle));
  assert.deepEqual(destination.values.get(id),{id,unknown:'preserve'});
  assert.deepEqual([...(await audio.read(source,id,webcrypto.subtle)).incoming.bytes],[2]);
});

test('une écriture interrompue se reprend sans doublon et un quota est propagé',async()=>{
  const source=new Store(),id=await audio.archive(source,new Store([await record([1])]),await record([2]),webcrypto.subtle);
  const transfer=await audio.read(source,id,webcrypto.subtle),destination=new Store(),add=destination.add.bind(destination);
  destination.add=async value=>{await add(value);throw Error('confirmation perdue');};
  await assert.rejects(audio.copy(destination,transfer,webcrypto.subtle),/confirmation perdue/);
  destination.add=add;assert.equal(await audio.copy(destination,transfer,webcrypto.subtle),'identical');
  const quota=new Store();quota.add=async()=>{throw Error('quota');};
  await assert.rejects(audio.copy(quota,transfer,webcrypto.subtle),/quota/);assert.equal(quota.values.size,0);
});
