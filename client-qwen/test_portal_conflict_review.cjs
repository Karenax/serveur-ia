'use strict';
const test = require('node:test'), assert = require('node:assert/strict');
const {JSDOM} = require('../agent/web/node_modules/jsdom');
const {webcrypto} = require('node:crypto');
const {archive, read} = require('./portal_conflict_archive.js');
const {show, preview} = require('./portal_conflict_review.js');

function fixture(current = 'version actuelle') {
  const dom = new JSDOM('<!doctype html><div id="screen"></div>', {url:'http://127.0.0.1:17841/'});
  const document = dom.window.document, storage = dom.window.localStorage;
  storage.setItem('draft', current);
  return {dom, document, storage, container:document.getElementById('screen')};
}
const archiveReal = (storage, key, value) => archive(storage, key, value, webcrypto.subtle);
const button = (document, text) => [...document.querySelectorAll('button')].find(node => node.textContent === text);

test('compare les deux valeurs sans interpréter le contenu et conserve la version courante', async () => {
  const f = fixture('<img src=x onerror=alert(1)>');
  const incoming = '<script>perte()</script>';
  const result = show({...f, key:'draft', incoming, archive:archiveReal});
  assert.equal(f.document.querySelectorAll('img, script').length, 0);
  const fields = [...f.document.querySelectorAll('textarea')];
  assert.deepEqual(fields.map(field => field.value), ['<img src=x onerror=alert(1)>', incoming]);
  assert.ok(fields.every(field => field.readOnly && field.getAttribute('aria-label')));
  assert.equal(f.document.activeElement.textContent, 'Interrompre');
  button(f.document, 'Conserver les deux').click();
  const saved = await result;
  assert.equal(saved.status, 'archived');
  assert.equal(f.storage.getItem('draft'), '<img src=x onerror=alert(1)>');
  assert.equal((await read(f.storage, saved.id, webcrypto.subtle)).incoming, incoming);
  f.dom.window.close();
});

test('permet d’interrompre au clavier sans modifier les données', async () => {
  const f = fixture();
  const result = show({...f, key:'draft', incoming:'autre', archive:archiveReal});
  f.document.dispatchEvent(new f.dom.window.KeyboardEvent('keydown', {key:'Escape', bubbles:true, cancelable:true}));
  assert.deepEqual(await result, {status:'cancel'});
  assert.equal(f.storage.getItem('draft'), 'version actuelle');
  assert.equal(f.storage.length, 1);
  f.dom.window.close();
});

test('une erreur de conservation reste visible et permet de réessayer ou interrompre', async () => {
  const f = fixture();
  let calls = 0;
  const result = show({...f, key:'draft', incoming:'autre', archive:async (...args) => {
    if (++calls === 1) throw new Error('quota');
    return archiveReal(...args);
  }});
  button(f.document, 'Conserver les deux').click();
  await new Promise(resolve => setImmediate(resolve));
  assert.match(f.document.querySelector('[role="status"]').textContent, /Impossible de conserver/);
  assert.equal(f.document.activeElement.textContent, 'Interrompre');
  assert.equal(f.storage.getItem('draft'), 'version actuelle');
  button(f.document, 'Conserver les deux').click();
  assert.equal((await result).status, 'archived');
  assert.equal(calls, 2);
  f.dom.window.close();
});

test('ne conserve pas une décision prise avant une modification de la version courante', async () => {
  const f = fixture();
  let called = false;
  const result = show({...f, key:'draft', incoming:'autre', archive:async()=>{called=true;return 'a'.repeat(64);}});
  f.storage.setItem('draft', 'nouvelle version');
  button(f.document, 'Conserver les deux').click();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(called, false);
  assert.equal(f.storage.getItem('draft'), 'nouvelle version');
  assert.match(f.document.querySelector('[role="status"]').textContent, /Impossible/);
  button(f.document, 'Interrompre').click();
  assert.deepEqual(await result, {status:'cancel'});
  f.dom.window.close();
});

test('désactive les actions pendant la conservation et refuse une confirmation invalide', async () => {
  const f = fixture();
  let complete;
  const result = show({...f, key:'draft', incoming:'autre', archive:()=>new Promise(resolve=>{complete=resolve;})});
  button(f.document, 'Conserver les deux').click();
  assert.ok([...f.document.querySelectorAll('button')].every(node => node.disabled));
  f.document.dispatchEvent(new f.dom.window.KeyboardEvent('keydown', {key:'Escape'}));
  complete('invalide');
  await new Promise(resolve => setImmediate(resolve));
  assert.ok([...f.document.querySelectorAll('button')].every(node => !node.disabled));
  button(f.document, 'Interrompre').click();
  assert.deepEqual(await result, {status:'cancel'});
  assert.equal(f.storage.getItem('draft'), 'version actuelle');
  f.dom.window.close();
});

test('présente une note structurée sans cacher sa version exacte', async () => {
  const note={title:'Réunion',content:{version:1,blocks:[
    {type:'heading',runs:[{text:'Décisions'}]},
    {type:'list',kind:'checklist',items:[{checked:false,runs:[{text:'Relire le dossier'}]}]},
    {type:'table',rows:[[[{text:'Équipe'}],[{text:'Vendredi'}]]]},
    {type:'image',caption:'Plan'},
  ]},pending:{command_id:'fictif'}};
  const other={...note,title:'Autre réunion'}, f=fixture(JSON.stringify(note));
  const result=show({...f,key:'draft',incoming:JSON.stringify(other),archive:archiveReal});
  // Unknown keys must remain literal, even if they happen to resemble a note.
  assert.equal(f.document.querySelector('textarea').value, JSON.stringify(note));
  button(f.document,'Interrompre').click();await result;
  f.storage.setItem('agent.notes.v1.fictif',JSON.stringify(note));
  const next=show({...f,key:'agent.notes.v1.fictif',incoming:JSON.stringify(other),archive:archiveReal});
  assert.match(f.document.querySelector('textarea').value, /Réunion\n\nDécisions\n\n\[ \] Relire le dossier/);
  assert.match(f.document.querySelector('textarea').value, /Équipe \| Vendredi/);
  assert.match(f.document.querySelector('textarea').value, /\[Image\] Plan/);
  assert.equal(f.document.querySelector('details textarea').value, JSON.stringify(note));
  assert.equal(f.document.querySelector('details').open, false);
  button(f.document,'Interrompre').click();await next;f.dom.window.close();
});

test('reconnaît les brouillons de réunion et refuse un format inconnu', () => {
  const markdown=JSON.stringify({format:1,text:'Texte en cours',base:{}});
  assert.equal(preview('agent.notes.markdown.v1.fixture',markdown),'Texte en cours');
  const publication=JSON.stringify({summary:{overview:'Résumé',decisions:[{text:'Décider'}],actions:[{text:'Agir'}],open_points:[]},fields:{text:'À ajouter'}});
  assert.match(preview('agent.meeting-publication.v1.fixture',publication), /Résumé[\s\S]*Décider[\s\S]*Agir[\s\S]*À ajouter/);
  const unknown=JSON.stringify({title:'Note',content:{version:1,blocks:[{type:'future',data:'ne pas ignorer'}]}});
  assert.equal(preview('agent.meeting-note.v1.fixture',unknown),null);
  assert.equal(preview('agent.meeting-note.v1.fixture','{invalide'),null);
});
