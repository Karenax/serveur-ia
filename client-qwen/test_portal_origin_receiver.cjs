'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const {localConflictHandler,audioConflictHandler,verifyRequired}=require('./portal_origin_receiver.js');
const {webcrypto}=require('node:crypto');
const recovery=require('./portal_origin_recovery.js'),audioArchive=require('./portal_audio_conflict_archive.js');

function fixture({found=null,preserve=false,result={status:'archived'}}={}) {
  const calls=[],container={};
  const root={localStorage:{},document:{getElementById:id=>id==='recovery-review'?container:null},
    kiaraPortalConflictArchive:{find:async(...args)=>{calls.push(['find',...args.slice(1)]);return found;},archive:()=>{}},
    kiaraPortalConflictReview:{show:async options=>{calls.push(['show',options]);return result;}}};
  const transport={review:async offer=>calls.push(['review',offer]),markArchive:async(offer,id)=>calls.push(['mark',offer,id])};
  return {root,calls,handler:localConflictHandler(root,transport,{preserve})};
}
const record={type:'local',key:'draft',value:'source fictive'};
const offer={id:'a'.repeat(32),sha256:'b'.repeat(64)};

test('une copie retrouvée est confirmée sans demander un nouveau choix',async()=>{
  const f=fixture({found:'c'.repeat(64)});
  assert.equal(await f.handler(record,offer),'archived');
  assert.deepEqual(f.calls.map(call=>call[0]),['find','mark']);
  assert.deepEqual(f.calls[1].slice(1),[offer,'c'.repeat(64)]);
});
test('une source déjà vérifiée peut laisser la version courante sans ouvrir de fenêtre',async()=>{
  const f=fixture({preserve:true});
  assert.equal(await f.handler(record,offer),'conflict');
  assert.deepEqual(f.calls.map(call=>call[0]),['find']);
});
test('un nouveau choix demande l’affichage puis le redémarrage pour vérification',async()=>{
  const f=fixture();assert.equal(await f.handler(record,offer),'restart');
  assert.deepEqual(f.calls.map(call=>call[0]),['find','review','show']);
  assert.deepEqual(f.calls[1][1],offer);assert.equal(f.calls[2][1].restartRequired,true);
});
test('une annulation laisse le conflit ouvert et une réponse invalide échoue',async()=>{
  assert.equal(await fixture({result:{status:'cancel'}}).handler(record,offer),'conflict');
  await assert.rejects(fixture({result:{status:'unexpected'}}).handler(record,offer),/invalide/);
});
test('une panne de la fenêtre de réception est signalée au contrôleur',async()=>{
  let failed=0;
  const root={__kiaraRecoveryReady:Promise.resolve(true),__kiaraRecoveryToken:'a'.repeat(64),
    fetch:async()=>({}),kiaraPortalOriginTransfer:{httpTransport:()=>({
      options:async()=>{throw Error('fixture');},fail:async()=>{failed++;},
    })}};
  const source=fs.readFileSync(path.join(__dirname,'portal_origin_receiver.js'),'utf8');
  vm.runInNewContext(source,{globalThis:root});
  for(let i=0;i<20&&!failed;i++)await new Promise(resolve=>setImmediate(resolve));
  assert.equal(failed,1);
});
test('toutes les copies requises sont vérifiées avant de confirmer la reprise',async()=>{
  const calls=[],root={localStorage:{},kiaraPortalConflictArchive:{read:async(_storage,id)=>{calls.push(id);}}};
  const transport={requiredOk:async()=>{calls.push('ok');}};
  await verifyRequired(root,transport,{required:['a'.repeat(64),'b'.repeat(64)]});
  assert.deepEqual(calls,['a'.repeat(64),'b'.repeat(64),'ok']);
  calls.length=0;root.kiaraPortalConflictArchive.read=async(_storage,id)=>{calls.push(id);throw Error('absente');};
  await assert.rejects(verifyRequired(root,transport,{required:['a'.repeat(64)]}),/indisponibles/);
  assert.deepEqual(calls,['a'.repeat(64)]);
});
test('les copies audio et locales sont vérifiées avant la reprise et la base est fermée',async()=>{
  const calls=[],store={close:()=>calls.push('close')};
  const root={localStorage:{},indexedDB:{},kiaraPortalConflictArchive:{read:async(_storage,id)=>calls.push('local:'+id)},
    kiaraPortalAudioConflictArchive:{open:async()=>{calls.push('open');return store;},read:async(_store,id)=>calls.push('audio:'+id)}};
  const transport={requiredOk:async()=>calls.push('ok')};
  await verifyRequired(root,transport,{required:['a'.repeat(64),'audio-'+'b'.repeat(64),'audio-'+'c'.repeat(64)]});
  assert.deepEqual(calls,['local:'+'a'.repeat(64),'open','audio:'+'b'.repeat(64),'audio:'+'c'.repeat(64),'close','ok']);
  calls.length=0;root.kiaraPortalAudioConflictArchive.read=async()=>{calls.push('missing');throw Error('absent');};
  await assert.rejects(verifyRequired(root,transport,{required:['audio-'+'b'.repeat(64)]}),/indisponibles/);
  assert.deepEqual(calls,['open','missing','close']);
});
test('une copie requise absente reçoit un signal distinct',async()=>{
  let missing=0,failed=0;
  const root={__kiaraRecoveryReady:Promise.resolve(true),__kiaraRecoveryToken:'a'.repeat(64),
    fetch:async()=>({}),localStorage:{},kiaraPortalConflictArchive:{read:async()=>{throw Error('absente');}},
    kiaraPortalOriginTransfer:{httpTransport:()=>({options:async()=>({required:['b'.repeat(64)]}),
      requiredOk:async()=>{},missingArchive:async()=>{missing++;},fail:async()=>{failed++;}})}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'portal_origin_receiver.js'),'utf8'),{globalThis:root});
  for(let i=0;i<20&&!missing;i++)await new Promise(resolve=>setImmediate(resolve));
  assert.equal(missing,1);assert.equal(failed,0);
});

async function audioFixture() {
  const make=async bytes=>{const data=new Uint8Array(bytes),hash=Buffer.from(await webcrypto.subtle.digest('SHA-256',data)).toString('hex');
    return {id:'fiction',session_id:'fiction',track:'microphone',seq:1,command_id:'fiction',sha256:hash,
      start_ms:0,duration_ms:10,created_at:'fiction',stableBytes:data.buffer,stableMime:'audio/wav'};};
  const current=await make([1]),incoming=await make([2]),newer=await make([3]),values=new Map();let exists=false;
  const journal={get:async id=>values.get(id),keys:async()=>[...values.keys()],add:async value=>values.set(value.id,value),close:()=>{}};
  const chunks={record:current,get:async function(){return this.record;}};
  const calls=[],root={indexedDB:{},crypto:webcrypto,URL:{},document:{getElementById:()=>({})},kiaraPortalOriginRecovery:recovery,
    kiaraPortalAudioConflictArchive:{...audioArchive,open:async(_db,options)=>{
      if(options.create)exists=true;return exists?journal:null;}},
    kiaraPortalAudioConflictReview:{show:async options=>{calls.push('show');return {status:'archived',id:await options.archive()};}}};
  const transport={review:async()=>calls.push('review'),markArchive:async(_transfer,id)=>calls.push('marked:'+id)};
  const data={meta:recovery.audioMetadata(incoming),mime:'audio/wav',bytes:new Uint8Array(incoming.stableBytes)};
  return {root,chunks,calls,values,data,current,incoming,newer,handler:audioConflictHandler(root,transport,chunks)};
}
test('un conflit audio est conservé puis reconnu au rejeu sans remplacer le fragment courant',async()=>{
  const f=await audioFixture();
  assert.equal(await f.handler(f.data,offer),'restart');
  assert.deepEqual(f.calls,['review','show']);assert.equal(f.values.size,1);assert.equal(f.chunks.record,f.current);
  f.calls.length=0;f.chunks.record=f.newer;
  assert.equal(await f.handler(f.data,offer),'archived');
  assert.equal(f.calls.length,1);assert.match(f.calls[0],/^marked:audio-[0-9a-f]{64}$/);
  assert.equal(f.chunks.record,f.newer);
});
test('un changement après la comparaison empêche la conservation et ne valide rien',async()=>{
  const f=await audioFixture();
  f.root.kiaraPortalAudioConflictReview.show=async options=>{f.chunks.record=f.newer;await options.archive();};
  await assert.rejects(f.handler(f.data,offer),/changé/);
  assert.deepEqual(f.calls,['review']);assert.equal(f.values.size,0);assert.equal(f.chunks.record,f.newer);
});
test('interrompre la comparaison audio ne crée aucune archive',async()=>{
  const f=await audioFixture();f.root.kiaraPortalAudioConflictReview.show=async()=>({status:'cancel'});
  assert.equal(await f.handler(f.data,offer),'conflict');
  assert.equal(f.values.size,0);assert.equal(f.chunks.record,f.current);
});
