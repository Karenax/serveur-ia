'use strict';
const test = require('node:test'), assert = require('node:assert/strict');
const {webcrypto} = require('node:crypto');
const {PREFIX, archive, read, list, find} = require('./portal_conflict_archive.js');
const subtle = webcrypto.subtle;

class Storage {
  constructor(entries = []) {this.values = new Map(entries);}
  getItem(key) {return this.values.has(key) ? this.values.get(key) : null;}
  setItem(key, value) {this.values.set(key, value);}
  get length() {return this.values.size;}
  key(index) {return [...this.values.keys()][index] ?? null;}
}

test('garde les deux versions sans modifier la version courante et se rejoue', async () => {
  const storage = new Storage([['draft', 'version Tauri']]);
  const id = await archive(storage, 'draft', 'version Qt', subtle);
  assert.equal(storage.getItem('draft'), 'version Tauri');
  assert.deepEqual(await read(storage, id, subtle),
    {version:1, key:'draft', current:'version Tauri', incoming:'version Qt'});
  assert.equal(await archive(storage, 'draft', 'version Qt', subtle), id);
  assert.equal((await read(storage, id, subtle)).current, 'version Tauri');
  assert.equal(storage.getItem('draft'), 'version Tauri');
});

test('conserve les deux versions même si la version courante évolue', async () => {
  const storage = new Storage([['draft', 'avant']]);
  const id = await archive(storage, 'draft', 'autre', subtle);
  storage.setItem('draft', 'nouvelle saisie');
  assert.equal(storage.getItem('draft'), 'nouvelle saisie');
  assert.equal((await read(storage, id, subtle)).incoming, 'autre');
  assert.equal((await read(storage, id, subtle)).current, 'avant');
});

test('ne remplace rien si la copie est altérée ou si le stockage refuse son écriture', async () => {
  const storage = new Storage([['draft', 'avant']]);
  const id = await archive(storage, 'draft', 'autre', subtle);
  storage.setItem(PREFIX + id, '{"version":1}');
  await assert.rejects(read(storage, id, subtle), /illisible/);
  await assert.rejects(archive(storage, 'draft', 'autre', subtle), /incohérente/);
  assert.equal(storage.getItem('draft'), 'avant');
  const full = new Storage([['draft', 'avant']]);
  full.setItem = () => {throw new Error('quota');};
  await assert.rejects(archive(full, 'draft', 'autre', subtle), /quota/);
  assert.equal(full.getItem('draft'), 'avant');
});

test('une modification pendant le calcul empêche la confirmation de la copie', async () => {
  const storage = new Storage([['draft', 'avant']]);
  let resolveDigest;
  const delayed = {digest: (...args) => new Promise(resolve => {
    resolveDigest = async () => resolve(await subtle.digest(...args));
  })};
  const pending = archive(storage, 'draft', 'autre', delayed);
  storage.setItem('draft', 'modifié');
  await resolveDigest();
  await assert.rejects(pending, /changé/);
  assert.equal(storage.getItem('draft'), 'modifié');
  assert.equal(storage.values.size, 1);
});

test('les enregistrements réservés et les valeurs identiques ne sont pas des conflits', async () => {
  const storage = new Storage([['draft', 'même']]);
  await assert.rejects(archive(storage, 'draft', 'même', subtle), /invalide/);
  await assert.rejects(archive(storage, PREFIX + 'x', 'autre', subtle), /invalide/);
  await assert.rejects(read(storage, 'wrong', subtle), /invalide/);
  assert.equal(storage.values.size, 1);
});

test('retrouve toutes les copies et refuse un enregistrement réservé illisible', async () => {
  const storage = new Storage([['draft', 'A'], ['other', 'B']]);
  const first = await archive(storage, 'draft', 'A2', subtle);
  const second = await archive(storage, 'other', 'B2', subtle);
  const items = await list(storage, subtle);
  assert.deepEqual(new Set(items.map(item => item.id)), new Set([first, second]));
  assert.equal(items.find(item => item.id === first).incoming, 'A2');
  storage.setItem(PREFIX + 'illisible', 'ne pas ignorer');
  await assert.rejects(list(storage, subtle), /invalide/);
  assert.equal(storage.getItem('draft'), 'A');
  assert.equal(storage.getItem('other'), 'B');
});

test('refuse une copie modifiée pendant la vérification de son empreinte', async () => {
  const storage = new Storage([['draft', 'A']]);
  const id = await archive(storage, 'draft', 'B', subtle);
  let finish;
  const delayed = {digest: (...args) => new Promise(resolve => {
    finish = async () => resolve(await subtle.digest(...args));
  })};
  const pending = read(storage, id, delayed);
  storage.setItem(PREFIX + id, 'altéré');
  await finish();
  await assert.rejects(pending, /non vérifiée/);
  assert.equal(storage.getItem('draft'), 'A');
});

test('ne remplace pas une autre copie même en cas de collision d’empreinte', async () => {
  const storage = new Storage([['first', 'A'], ['second', 'B']]);
  const collision = {digest: async () => new Uint8Array(32).buffer};
  const id = await archive(storage, 'first', 'A2', collision);
  const original = storage.getItem(PREFIX + id);
  await assert.rejects(archive(storage, 'second', 'B2', collision), /incohérente/);
  assert.equal(storage.getItem(PREFIX + id), original);
  assert.equal(storage.getItem('first'), 'A');
  assert.equal(storage.getItem('second'), 'B');
});

test('ne confirme pas une écriture de copie silencieusement refusée', async () => {
  const storage = new Storage([['draft', 'A']]);
  storage.setItem = () => {};
  await assert.rejects(archive(storage, 'draft', 'B', subtle), /vérifiée/);
  assert.equal(storage.getItem('draft'), 'A');
  assert.equal(storage.length, 1);
});

test('retrouve une copie approuvée même si le brouillon courant a évolué', async () => {
  const storage = new Storage([['draft', 'première version']]);
  assert.equal(await find(storage, 'draft', 'autre version', subtle), null);
  const id = await archive(storage, 'draft', 'autre version', subtle);
  assert.equal(await find(storage, 'draft', 'autre version', subtle), id);
  storage.setItem('draft', 'saisie plus récente');
  assert.equal(await find(storage, 'draft', 'autre version', subtle), id);
  assert.equal(await find(storage, 'draft', 'source modifiée', subtle), null);
  assert.equal(storage.getItem('draft'), 'saisie plus récente');
});

test('une copie illisible ou une version courante modifiée ne confirme pas le conflit', async () => {
  const storage = new Storage([['draft', 'avant']]);
  const id = await archive(storage, 'draft', 'autre', subtle);
  storage.setItem(PREFIX+id, 'illisible');
  await assert.rejects(find(storage, 'draft', 'autre', subtle), /illisible/);
  assert.equal(storage.getItem('draft'), 'avant');
  const clean = new Storage([['draft', 'avant']]);
  await archive(clean, 'draft', 'autre', subtle);
  let release;
  const delayed = {digest: (...args) => new Promise(resolve => {release = async () => resolve(await subtle.digest(...args));})};
  const pending = find(clean, 'draft', 'autre', delayed);
  clean.setItem('draft', 'modifié');
  await release();
  // find re-reads archives after enumeration, so release the next hash too.
  await new Promise(resolve=>setImmediate(resolve));
  await release();
  await assert.rejects(pending, /changé/);
  assert.equal(clean.getItem('draft'), 'modifié');
});
