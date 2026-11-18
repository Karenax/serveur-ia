'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const script=fs.readFileSync(require('node:path').join(__dirname,'portal_origin_window.js'),'utf8');
function load(role,mode){
  const added=[],head={appendChild:item=>added.push(item)},document={head,createElement:name=>({name})};
  vm.runInNewContext(script,{window:{__kiaraRecoveryRole:role,__kiaraRecoveryMode:mode},document});return added;
}
test('la fenêtre charge seulement le script associé à son rôle validé',()=>{
  assert.deepEqual(load('sender','transfer'),[{name:'script',src:'/portal_origin_sender_result.js'}]);
  assert.deepEqual(load('sender','snapshot'),[{name:'script',src:'/portal_origin_snapshot.js'}]);
  assert.deepEqual(load('sender','manifest'),[{name:'script',src:'/portal_origin_manifest.js'}]);
  assert.deepEqual(load('receiver','manifest'),[]);
  assert.deepEqual(load('receiver','transfer'),[{name:'script',src:'/portal_origin_receiver.js'}]);
  assert.deepEqual(load('receiver','snapshot'),[{name:'script',src:'/portal_origin_receiver.js'}]);
  for(const role of [undefined,'other','/attacker'])assert.deepEqual(load(role,'transfer'),[]);
  for(const mode of [undefined,'other','/attacker'])assert.deepEqual(load('sender',mode),[]);
});
