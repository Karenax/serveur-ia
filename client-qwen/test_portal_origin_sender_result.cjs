'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {run}=require('./portal_origin_sender_result.js');
function fixture(outcome,ok=true){
  const calls=[];class Conflict extends Error {} class Restart extends Error {}
  const api={TransferConflict:Conflict,TransferRestart:Restart,httpTransport:()=>({}),indexedAudioSource:()=>({}),sourceRecords:()=>({}),
    sendAll:async()=>{if(outcome==='conflict')throw new Conflict('private');if(outcome==='restart')throw new Restart('private');if(outcome==='error')throw Error('private');return {copied:2,identical:1};}};
  const root={__kiaraRecoveryReady:Promise.resolve(true),__kiaraRecoveryToken:'a'.repeat(64),
    kiaraPortalOriginTransfer:api,kiaraPortalOriginInventory:{inventory:()=>{}},localStorage:{},indexedDB:{},
    fetch:async(path,options)=>{calls.push({path,options});return {ok};}};
  return {root,calls};
}
test('seuls les comptes ou un état de panne sont transmis sur le canal de résultat',async()=>{
  for(const outcome of ['ok','conflict','restart','error']){
    const f=fixture(outcome);await run(f.root);assert.equal(f.calls.length,1);assert.equal(f.calls[0].path,'/recovery/result');
    assert.deepEqual(JSON.parse(f.calls[0].options.body),outcome==='ok'?{status:'ok',copied:2,identical:1}:{status:outcome==='error'?'unavailable':outcome});
  }
});
test('une fenêtre non protégée ou un refus du courtier ne confirme rien',async()=>{
  const f=fixture('ok');f.root.__kiaraRecoveryReady=Promise.resolve(false);await assert.rejects(run(f.root),/Protection/);assert.equal(f.calls.length,0);
  const denied=fixture('ok',false);await assert.rejects(run(denied.root),/non confirmé/);
});
