'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {run}=require('./portal_origin_sender.js');

function fixture(outcome) {
  const staged=[];class Conflict extends Error {}
  const transport={stage:async body=>staged.push(JSON.parse(new TextDecoder().decode(body)))};
  const api={TransferConflict:Conflict,httpTransport:()=>transport,indexedAudioSource:()=>({}),sourceRecords:()=>({}),
    sendAll:async()=>{if(outcome==='conflict')throw new Conflict('private');if(outcome==='error')throw Error('private value');return {copied:2,identical:1};}};
  return {staged,root:{__kiaraRecoveryReady:Promise.resolve(true),__kiaraRecoveryToken:'a'.repeat(64),
    kiaraPortalOriginTransfer:api,kiaraPortalOriginInventory:{inventory:()=>{}},localStorage:{},indexedDB:{},fetch:()=>{}}};
}
test('signale seulement les comptes après une copie vérifiée',async()=>{
  const f=fixture('ok');await run(f.root);assert.deepEqual(f.staged,[{type:'result',status:'ok',copied:2,identical:1}]);
});
test('un conflit ou une panne ne révèlent pas les données dans le résultat',async()=>{
  for(const status of ['conflict','error']){
    const f=fixture(status);await run(f.root);
    assert.deepEqual(f.staged,[{type:'result',status:status==='conflict'?'conflict':'unavailable'}]);
  }
});
test('une fenêtre non protégée ne démarre aucun transfert',async()=>{
  const f=fixture('ok');f.root.__kiaraRecoveryReady=Promise.resolve(false);
  await assert.rejects(run(f.root),/Protection/);assert.deepEqual(f.staged,[]);
});
