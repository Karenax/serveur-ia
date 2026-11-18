'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {JSDOM}=require('../agent/web/node_modules/jsdom');
const {webcrypto}=require('node:crypto');
const archive=require('./portal_audio_conflict_archive.js');
const {install}=require('./portal_audio_conflict_library.js');

async function makeRecord(bytes,changes={}) {
  const data=new Uint8Array(bytes),sha256=Buffer.from(await webcrypto.subtle.digest('SHA-256',data)).toString('hex');
  return {id:'fiction',session_id:'fiction',track:'mic',seq:1,command_id:'fiction',sha256,start_ms:0,
    duration_ms:500,created_at:'2026-11-17T00:00:00Z',stableBytes:data.buffer,stableMime:'audio/wav',...changes};
}
async function fixture({present=true}={}) {
  const dom=new JSDOM('<!doctype html><section class="chat-view"><p>Conversation fictive</p></section>',{url:'http://127.0.0.1:17841/'});
  const root=dom.window,values=new Map(),current=await makeRecord([1,2,3]),incoming=await makeRecord([4,5,6]);
  root.indexedDB={};
  const store={get:async id=>values.get(id),keys:async()=>[...values.keys()],add:async value=>values.set(value.id,value),close:()=>{}};
  const chunk={get:async()=>current},id=present?await archive.archive(store,chunk,incoming,webcrypto.subtle):null;
  const created=[],revoked=[];
  root.URL.createObjectURL=blob=>{created.push(blob);return `blob:fiction-${created.length}`;};
  root.URL.revokeObjectURL=url=>revoked.push(url);
  root.kiaraPortalAudioConflictArchive={...archive,open:async(_db,options)=>present?store:options?.allowMissing?null:Promise.reject(Error('absente')),
    list:value=>archive.list(value,webcrypto.subtle),read:(value,key)=>archive.read(value,key,webcrypto.subtle)};
  root.HTMLDialogElement.prototype.showModal=function(){this.open=true;};
  root.HTMLDialogElement.prototype.close=function(){this.open=false;this.dispatchEvent(new root.Event('close'));};
  const button=text=>[...root.document.querySelectorAll('button')].find(item=>item.textContent===text);
  return {dom,root,document:root.document,values,store,chunk,current,incoming,id,created,revoked,button};
}
async function waitFor(check) {
  for(let i=0;i<100;i++){if(check())return;await new Promise(resolve=>setTimeout(resolve,5));}
  throw Error('Chargement incomplet');
}

test('aucune base de copies ne modifie la conversation',async()=>{
  const f=await fixture({present:false});assert.equal(await install(f.root),false);
  assert.equal(f.document.querySelector('.chat-view').textContent,'Conversation fictive');f.dom.window.close();
});
test('une base vide ne signale pas de fragment conservé',async()=>{
  const f=await fixture();f.values.clear();assert.equal(await install(f.root),false);
  assert.equal(f.document.querySelector('.chat-view').textContent,'Conversation fictive');f.dom.window.close();
});
test('les deux fragments sont vérifiés, écoutables et téléchargeables sans écriture',async()=>{
  const f=await fixture(),before=f.values.get(f.id);
  assert.equal(await install(f.root),true);const trigger=f.button('Consulter les audios');trigger.click();
  await waitFor(()=>f.document.querySelectorAll('dialog audio').length===2);
  assert.deepEqual([...f.document.querySelectorAll('dialog audio')].map(x=>x.getAttribute('aria-label')),
    ['Version présente à la récupération','Autre version conservée']);
  assert.deepEqual([...f.document.querySelectorAll('dialog a')].map(x=>x.download),['version-presente.wav','autre-version.wav']);
  assert.equal(f.created.length,2);assert.deepEqual(f.created.map(x=>x.size),[3,3]);
  assert.match(f.document.querySelector('dialog select option').textContent,/microphone/);
  assert.equal(f.values.get(f.id),before);f.button('Fermer').click();
  assert.equal(f.document.activeElement,trigger);assert.equal(f.document.querySelectorAll('dialog audio').length,0);
  assert.deepEqual(f.revoked,['blob:fiction-1','blob:fiction-2']);f.dom.window.close();
});
test('une copie altérée est signalée sans être effacée',async()=>{
  const f=await fixture();f.values.get(f.id).incoming.bytes=new Uint8Array([0]).buffer;
  await install(f.root);f.button('Consulter les audios').click();
  await waitFor(()=>/Impossible de lire/.test(f.document.querySelector('dialog [role="status"]').textContent));
  assert.equal(f.values.size,1);assert.equal(f.created.length,0);f.button('Fermer').click();f.dom.window.close();
});
test('une fermeture pendant la lecture ne recrée ni lecteur ni adresse',async()=>{
  const f=await fixture();let finish;
  f.root.kiaraPortalAudioConflictArchive.read=()=>new Promise(resolve=>{finish=resolve;});
  await install(f.root);f.button('Consulter les audios').click();await waitFor(()=>typeof finish==='function');
  f.button('Fermer').click();finish({current:{bytes:new Uint8Array([1]),mime:'audio/wav'},incoming:{bytes:new Uint8Array([2]),mime:'audio/wav'}});
  await new Promise(resolve=>setImmediate(resolve));assert.equal(f.created.length,0);
  assert.equal(f.document.querySelectorAll('dialog audio').length,0);f.dom.window.close();
});
test('changer de fragment pendant une lecture ignore la réponse arrivée trop tard',async()=>{
  const f=await fixture();await archive.archive(f.store,f.chunk,await makeRecord([7,8,9]),webcrypto.subtle);
  const waiting=[];
  f.root.kiaraPortalAudioConflictArchive.read=(_store,id)=>new Promise(resolve=>waiting.push({id,resolve}));
  await install(f.root);f.button('Consulter les audios').click();
  await waitFor(()=>waiting.length===1);
  const select=f.document.querySelector('dialog select');select.value='1';select.dispatchEvent(new f.root.Event('change'));
  await waitFor(()=>waiting.length===2);
  waiting[1].resolve(await archive.read(f.store,waiting[1].id,webcrypto.subtle));
  await waitFor(()=>f.created.length===2);
  waiting[0].resolve(await archive.read(f.store,waiting[0].id,webcrypto.subtle));
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(f.created.length,2);assert.equal(f.document.querySelectorAll('dialog audio').length,2);
  f.button('Fermer').click();assert.equal(f.revoked.length,2);f.dom.window.close();
});
test('une base inaccessible reste signalée et peut être réessayée',async()=>{
  const f=await fixture();f.root.kiaraPortalAudioConflictArchive.open=async()=>{throw Error('indisponible');};
  assert.equal(await install(f.root),true);assert.match(f.document.querySelector('.chat-view [role="status"]').textContent,/vérifiées/);
  f.button('Consulter les audios').click();await waitFor(()=>/Impossible de lire/.test(f.document.querySelector('dialog [role="status"]').textContent));
  assert.equal(f.values.size,1);f.button('Fermer').click();f.dom.window.close();
});
