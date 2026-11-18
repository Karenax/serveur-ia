'use strict';
const test = require('node:test'), assert = require('node:assert/strict');
const {JSDOM} = require('../agent/web/node_modules/jsdom');
const {webcrypto} = require('node:crypto');
const archive = require('./portal_conflict_archive.js');
const review = require('./portal_conflict_review.js');
const {install} = require('./portal_conflict_library.js');

function fixture() {
  const dom = new JSDOM('<!doctype html><section class="chat-view"><p>Conversation fictive</p></section>',
    {url:'http://127.0.0.1:17841/'});
  const root = dom.window;
  root.kiaraPortalConflictArchive = {...archive, list:storage=>archive.list(storage, webcrypto.subtle)};
  root.kiaraPortalConflictReview = review;
  root.HTMLDialogElement.prototype.showModal = function() {this.open = true;};
  root.HTMLDialogElement.prototype.close = function() {this.open = false;this.dispatchEvent(new root.Event('close'));};
  return {dom,root,document:root.document,storage:root.localStorage};
}
const tick = () => new Promise(resolve=>setImmediate(resolve));
const button = (document, text) => [...document.querySelectorAll('button')].find(item=>item.textContent===text);
async function waitForSelect(document) {
  for (let i=0; i<100; i++) {
    const value=document.querySelector('dialog select');
    if (value) return value;
    await new Promise(resolve=>setTimeout(resolve,5));
  }
  throw new Error('Copies non chargées');
}

test('ne change pas les conversations quand aucune copie n’existe', async () => {
  const f = fixture();
  assert.equal(await install(f.root),false);
  assert.equal(f.document.querySelector('.chat-view').textContent,'Conversation fictive');
  assert.equal(f.document.querySelector('dialog'),null); f.dom.window.close();
});

test('retrouve les deux versions sans modifier le brouillon actif et permet de les copier', async () => {
  const f = fixture();
  f.storage.setItem('draft','version initiale');
  await archive.archive(f.storage,'draft','<script>autre</script>',webcrypto.subtle);
  f.storage.setItem('draft','nouveau brouillon');
  assert.equal(await install(f.root),true);
  const trigger=button(f.document,'Consulter');trigger.focus();trigger.click();
  await waitForSelect(f.document);
  assert.equal(f.document.querySelector('dialog').open,true);
  const fields=[...f.document.querySelectorAll('dialog textarea')];
  assert.deepEqual(fields.map(item=>item.value),['nouveau brouillon','version initiale','<script>autre</script>']);
  assert.ok(fields.every(item=>item.readOnly));
  assert.equal(f.document.querySelectorAll('script').length,0);
  button(f.document,'Fermer').click();
  assert.equal(f.document.querySelector('dialog').open,false);
  assert.equal(f.document.activeElement,trigger);
  assert.equal(f.storage.getItem('draft'),'nouveau brouillon');
  assert.equal(f.document.querySelector('dialog textarea'),null);
  f.dom.window.close();
});

test('permet de choisir une autre copie sans exposer les identifiants techniques', async () => {
  const f=fixture();
  f.storage.setItem('draft','A');await archive.archive(f.storage,'draft','A2',webcrypto.subtle);
  f.storage.setItem('note','B');await archive.archive(f.storage,'note','B2',webcrypto.subtle);
  await install(f.root);button(f.document,'Consulter').click();
  const select=await waitForSelect(f.document);assert.equal(select.options.length,2);
  assert.ok([...select.options].every(item=>!item.textContent.includes(archive.PREFIX)));
  const before=[...f.document.querySelectorAll('dialog textarea')].map(item=>item.value);
  select.value='1';select.dispatchEvent(new f.root.Event('change'));
  assert.notDeepEqual([...f.document.querySelectorAll('dialog textarea')].map(item=>item.value),before);
  assert.equal(f.storage.getItem('draft'),'A');assert.equal(f.storage.getItem('note'),'B');
  f.dom.window.close();
});

test('signale une copie illisible sans la supprimer ni toucher au brouillon', async () => {
  const f=fixture();f.storage.setItem('draft','A');
  const id=await archive.archive(f.storage,'draft','B',webcrypto.subtle);
  f.storage.setItem(archive.PREFIX+id,'corrompu');
  await install(f.root);button(f.document,'Consulter').click();await tick();await tick();
  assert.match(f.document.querySelector('dialog [role="status"]').textContent,/Impossible de lire/);
  assert.equal(f.storage.getItem('draft'),'A');assert.equal(f.storage.getItem(archive.PREFIX+id),'corrompu');
  button(f.document,'Fermer').click();f.dom.window.close();
});

test('fermer pendant le chargement ne rouvre pas les copies', async () => {
  const f=fixture();f.storage.setItem(archive.PREFIX+'a'.repeat(64),'fixture');
  let finish;
  f.root.kiaraPortalConflictArchive.list=()=>new Promise(resolve=>{finish=resolve;});
  await install(f.root);button(f.document,'Consulter').click();
  button(f.document,'Fermer').click();finish([]);await tick();
  assert.equal(f.document.querySelector('dialog').open,false);
  assert.equal(f.document.querySelector('dialog [role="status"]').textContent,'');
  f.dom.window.close();
});
