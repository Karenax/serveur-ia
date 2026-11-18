'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {run}=require('./portal_origin_manifest.js');
function fixture({copies=[],missing=false,error=false}={}) {
  const calls=[],store={close:()=>calls.push('close')};
  const root={__kiaraRecoveryReady:Promise.resolve(true),__kiaraRecoveryToken:'a'.repeat(64),indexedDB:{},
    kiaraPortalAudioConflictArchive:{open:async(_db,options)=>{assert.equal(options.allowMissing,true);return missing?null:store;},
      list:async()=>{if(error)throw Error('private');return copies;}},
    fetch:async(path,options)=>{calls.push([path,JSON.parse(options.body)]);return {ok:true};}};
  return {root,calls};
}
test('la destination transmet seulement les empreintes vérifiées et ferme sa base',async()=>{
  const f=fixture({copies:[{id:'b'.repeat(64)},{id:'a'.repeat(64)}]});await run(f.root);
  assert.deepEqual(f.calls,['close',['/recovery/result',{status:'manifest',audioArchiveIds:['a'.repeat(64),'b'.repeat(64)]}]]);
});
test('une base absente reste vide et une copie invalide est indisponible',async()=>{
  const empty=fixture({missing:true});await run(empty.root);
  assert.deepEqual(empty.calls,[['/recovery/result',{status:'manifest',audioArchiveIds:[]}]]);
  for(const options of [{error:true},{copies:[{id:'short'}]},{copies:[{id:'b'.repeat(64)},{id:'b'.repeat(64)}]}]) {
    const f=fixture(options);await run(f.root);assert.deepEqual(f.calls,['close',['/recovery/result',{status:'unavailable'}]]);
  }
});
