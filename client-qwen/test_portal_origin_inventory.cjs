'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {inventory, InventoryUnavailable} = require('./portal_origin_inventory.js');
const empty = {length:0, key:()=>null};
const storage = keys => ({length:keys.length, key:i=>keys[i]});
const names = values => ({length:values.length, contains:value=>values.includes(value)});
function fakeDb({count=2, blocked=false, upgrade=false, stores=['chunks'], indexes=['session_id'], abort=false} = {}) {
  const state = {closed:false, opened:0, aborted:false};
  const indexedDB = {
    databases:async()=>[{name:'agent-meeting-audio-v1',version:1}],
    open:()=>{
      state.opened++;
      const request = {transaction:{abort:()=>{state.aborted=true;}}};
      setTimeout(()=>{
        if (blocked) return request.onblocked();
        if (upgrade) return request.onupgradeneeded();
        const tx = {objectStore:()=>({keyPath:'id',indexNames:names(indexes),
          index:()=>({keyPath:'session_id',unique:false,multiEntry:false}),
          count:()=>{const countRequest={};setTimeout(()=>{countRequest.result=count;countRequest.onsuccess();abort?tx.onabort():tx.oncomplete();},0);return countRequest;}})};
        request.result={version:1,objectStoreNames:names(stores),transaction:()=>tx,close:()=>{state.closed=true;}};
        request.onsuccess();
      },0);
      return request;
    },
  };
  return {indexedDB,state};
}

test('une origine vide est inventoriée sans créer de base', async () => {
  let opened=false;
  const result=await inventory(empty,{databases:async()=>[],open:()=>{opened=true;}});
  assert.deepEqual(result,{localEntries:0,audioChunks:0});assert.equal(opened,false);
});
test('un inventaire compte sans retourner les clés ni les données', async () => {
  const {indexedDB,state}=fakeDb({count:3});
  assert.deepEqual(await inventory(storage(['brouillon-secret','commande']),indexedDB),{localEntries:2,audioChunks:3});
  assert.equal(state.closed,true);assert.equal(state.opened,1);
});
test('les bases et versions inconnues restent non vérifiées', async () => {
  for(const list of [[{name:'inconnue',version:1}],[{name:'agent-meeting-audio-v1',version:2}],
    [{name:'agent-meeting-audio-v1',version:1},{name:'agent-meeting-audio-v1',version:1}], [{name:'x'}]]) {
    let opened=false;await assert.rejects(inventory(empty,{databases:async()=>list,open:()=>{opened=true;}}),InventoryUnavailable);assert.equal(opened,false);
  }
  for(const options of [{stores:['chunks','future']},{indexes:[]},{abort:true},{blocked:true}]) {
    const {indexedDB}=fakeDb(options);await assert.rejects(inventory(empty,indexedDB),InventoryUnavailable);
  }
});
test('les copies audio ne sont comptées que par un inventaire explicite et vérifié',async()=>{
  const db={databases:async()=>[{name:'kiara-recovery-audio-v1',version:1}]};
  let closed=0,opened=0;
  const api={open:async()=>{opened++;return {close:()=>closed++};},list:async()=>[{id:'a'.repeat(64)}]};
  await assert.rejects(inventory(empty,db),InventoryUnavailable);
  assert.deepEqual(await inventory(storage(['brouillon']),db,5000,{audioArchive:api}),
    {localEntries:1,audioChunks:0,audioArchives:1});
  assert.equal(opened,1);assert.equal(closed,1);
  const bad={...api,list:async()=>{throw Error('fictif');}};
  await assert.rejects(inventory(empty,db,5000,{audioArchive:bad}),InventoryUnavailable);
  assert.equal(closed,2);
  await assert.rejects(inventory(empty,db,5000,{audioArchive:{...api,list:async()=> 'bad'}}),InventoryUnavailable);
  await assert.rejects(inventory(empty,db,10,{audioArchive:{...api,list:()=>new Promise(()=>{})}}),InventoryUnavailable);
  assert.deepEqual(await inventory(empty,db,5000,{audioArchive:api,audioArchiveIds:true}),
    {localEntries:0,audioChunks:0,audioArchives:1,audioArchiveIds:['a'.repeat(64)]});
  await assert.rejects(inventory(empty,db,10,{audioArchive:api,audioArchiveIds:1}),/invalide/);
  await assert.rejects(inventory(empty,db,10,{audioArchiveIds:true}),/invalide/);
  await assert.rejects(inventory(empty,db,10,{audioArchive:{...api,list:async()=>[{id:'a'.repeat(64)},{id:'a'.repeat(64)}]},audioArchiveIds:true}),InventoryUnavailable);
});
test('une base de copies absente est reconnue sans ouverture et les options invalides échouent',async()=>{
  let opened=false;const api={open:async()=>{opened=true;},list:async()=>[]};
  assert.deepEqual(await inventory(empty,{databases:async()=>[]},10,{audioArchive:api}),
    {localEntries:0,audioChunks:0,audioArchives:0});
  assert.equal(opened,false);
  await assert.rejects(inventory(empty,{databases:async()=>[]},10,{audioArchive:false}),/invalide/);
  await assert.rejects(inventory(empty,{databases:async()=>[]},10,{future:true}),/invalide/);
});
test('une base disparue ne doit pas être recréée', async () => {
  const {indexedDB,state}=fakeDb({upgrade:true});
  await assert.rejects(inventory(empty,indexedDB),InventoryUnavailable);assert.equal(state.aborted,true);
});
test('les stockages indisponibles, changeants ou trop lents ne sont jamais déclarés vides', async () => {
  await assert.rejects(inventory({get length(){throw Error();}},{}),InventoryUnavailable);
  await assert.rejects(inventory({length:2,key:()=> 'duplicate'},{}),InventoryUnavailable);
  await assert.rejects(inventory(empty,{}),InventoryUnavailable);
  await assert.rejects(inventory(empty,{databases:async()=>{throw Error();}}),InventoryUnavailable);
  await assert.rejects(inventory(empty,{databases:()=>new Promise(()=>{})},10),InventoryUnavailable);
  await assert.rejects(inventory(empty,{databases:async()=>[{name:'agent-meeting-audio-v1',version:1}],open:()=>({})},10),InventoryUnavailable);
});
