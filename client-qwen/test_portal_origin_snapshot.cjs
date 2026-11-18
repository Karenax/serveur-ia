'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {webcrypto}=require('node:crypto');
const {snapshot,run}=require('./portal_origin_snapshot.js');
const archive=require('./portal_audio_conflict_archive.js');
const {audioArchiveRecord}=require('./portal_origin_transfer.js');
async function* source(value='texte fictif') {
  yield {type:'local',key:'brouillon',value};
  yield {type:'audio-stream',meta:{id:'fragment',sha256:'a'.repeat(64)},mime:'audio/wav',bytes:new Uint8Array([1,2,3])};
}
test('empreinte stable, sensible aux modifications et sans valeur personnelle',async()=>{
  const first=await snapshot(source(),webcrypto.subtle),same=await snapshot(source(),webcrypto.subtle);
  const changed=await snapshot(source('autre texte'),webcrypto.subtle);
  assert.deepEqual(first,same);assert.equal(first.localEntries,1);assert.equal(first.audioChunks,1);
  assert.match(first.digest,/^[0-9a-f]{64}$/);assert.notEqual(first.digest,changed.digest);
  assert.doesNotMatch(JSON.stringify(first),/brouillon|texte|fragment/);
});
test('une source interrompue ou inconnue ne produit pas une empreinte valide',async()=>{
  async function* broken(){yield {type:'local',key:'x',value:'y'};throw Error('panne privée');}
  async function* unknown(){yield {type:'unknown'};}
  await assert.rejects(snapshot(broken(),webcrypto.subtle));await assert.rejects(snapshot(unknown(),webcrypto.subtle));
});
test('le résumé étendu vérifie les deux fragments archivés et détecte une altération',async()=>{
  const make=async bytes=>{const data=new Uint8Array(bytes),sha=Buffer.from(await webcrypto.subtle.digest('SHA-256',data)).toString('hex');
    return {id:'fiction',session_id:'fiction',track:'mic',seq:1,command_id:'c',sha256:sha,start_ms:0,duration_ms:10,
      created_at:'fiction',blob:new Blob([data],{type:'audio/wav'})};};
  const values=new Map(),store={get:async id=>values.get(id),add:async item=>values.set(item.id,item)};
  const current=await make([1]),incoming=await make([2]);
  const id=await archive.archive(store,{get:async()=>current},incoming,webcrypto.subtle);
  const item=audioArchiveRecord(await archive.read(store,id,webcrypto.subtle));
  async function* records(){yield item;}
  await assert.rejects(snapshot(records(),webcrypto.subtle),/inconnue/);
  const result=await snapshot(records(),webcrypto.subtle,{audioArchive:archive});
  assert.deepEqual(Object.keys(result).sort(),['audioArchives','audioChunks','digest','localEntries','status'].sort());
  assert.equal(result.audioArchives,1);assert.equal(result.audioChunks,0);assert.doesNotMatch(JSON.stringify(result),/fiction/);
  item.incoming.bytes[0]=0;
  await assert.rejects(snapshot(records(),webcrypto.subtle,{audioArchive:archive}));
});
test('le résultat de la fenêtre ne transmet que le résumé ou une erreur générique',async()=>{
  const sent=[];const root={__kiaraRecoveryReady:Promise.resolve(true),__kiaraRecoveryToken:'a'.repeat(64),crypto:webcrypto,
    localStorage:{},indexedDB:{},kiaraPortalOriginInventory:{inventory:()=>{}},
    kiaraPortalOriginTransfer:{indexedAudioSource:()=>({}),sourceRecords:()=>source()},
    fetch:async(path,options)=>{sent.push([path,JSON.parse(options.body)]);return {ok:true};}};
  await run(root);assert.equal(sent[0][0],'/recovery/result');assert.equal(sent[0][1].status,'snapshot');
  root.kiaraPortalOriginTransfer.sourceRecords=()=>{throw Error('donnée privée');};
  await run(root);assert.deepEqual(sent[1][1],{status:'unavailable'});
});
