'use strict';
const test = require('node:test'), assert = require('node:assert/strict');
const {JSDOM} = require('../agent/web/node_modules/jsdom');
const {show} = require('./portal_audio_conflict_review.js');
const tick = () => new Promise(resolve => setImmediate(resolve));

function fixture() {
  const dom = new JSDOM('<!doctype html><div id="recovery-review"></div>');
  const document = dom.window.document, container = document.querySelector('#recovery-review');
  const created = [], revoked = [];
  const urls = {createObjectURL:blob => {created.push(blob);return `blob:fiction-${created.length}`;},
    revokeObjectURL:url => revoked.push(url)};
  const current = {bytes:new Uint8Array([1,2,3]),mime:'audio/wav',meta:{duration_ms:2500}};
  const incoming = {bytes:new Uint8Array([4,5,6]),mime:'audio/wav',meta:{duration_ms:62000}};
  const button = text => [...document.querySelectorAll('button')].find(item => item.textContent === text);
  return {dom,document,container,urls,created,revoked,current,incoming,button};
}

test('écoute les deux versions puis conserve explicitement et libère les adresses', async () => {
  const f=fixture();let calls=0;
  const result=show({...f,archive:async()=>{calls++;return 'a'.repeat(64);},restartRequired:true});
  assert.equal(f.created.length,2);
  assert.deepEqual([...f.document.querySelectorAll('audio')].map(el=>el.getAttribute('aria-label')),
    ['Version actuelle','Autre version']);
  assert.match(f.container.textContent,/relancez-le/);
  assert.match(f.container.textContent,/1 min 02 s/);
  assert.equal(f.document.activeElement,f.button('Interrompre'));
  f.button('Conserver les deux').click();
  assert.deepEqual(await result,{status:'archived',id:'a'.repeat(64)});assert.equal(calls,1);
  assert.deepEqual(f.revoked,['blob:fiction-1','blob:fiction-2']);f.dom.window.close();
});

test('Échap interrompt sans conservation', async () => {
  const f=fixture();let calls=0;
  const result=show({...f,archive:async()=>{calls++;return 'a'.repeat(64);}});
  f.document.dispatchEvent(new f.dom.window.KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}));
  assert.deepEqual(await result,{status:'cancel'});assert.equal(calls,0);assert.equal(f.revoked.length,2);f.dom.window.close();
});

test('un échec de conservation reste visible et permet une interruption', async () => {
  const f=fixture();const result=show({...f,archive:async()=>{throw Error('quota');}});
  f.button('Conserver les deux').click();await tick();
  assert.match(f.document.querySelector('[role="status"]').textContent,/Impossible de conserver/);
  assert.equal(f.button('Interrompre').disabled,false);assert.equal(f.revoked.length,0);
  f.button('Interrompre').click();assert.deepEqual(await result,{status:'cancel'});
  assert.equal(f.revoked.length,2);f.dom.window.close();
});

test('empêche une interruption ou une seconde écriture pendant la conservation', async () => {
  const f=fixture();let finish,calls=0;
  const result=show({...f,archive:()=>{calls++;return new Promise(resolve=>{finish=resolve;});}});
  f.button('Conserver les deux').click();f.button('Conserver les deux').click();f.button('Interrompre').click();
  f.document.dispatchEvent(new f.dom.window.KeyboardEvent('keydown',{key:'Escape'}));
  assert.equal(calls,1);assert.equal(f.revoked.length,0);
  finish('b'.repeat(64));assert.equal((await result).status,'archived');assert.equal(f.revoked.length,2);f.dom.window.close();
});
