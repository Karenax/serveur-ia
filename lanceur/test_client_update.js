'use strict';
// Exercise the actual update controls while a conversation is generating.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'../client-qwen/chat.html'),'utf8');
const elements=new Map(),calls=[];
const element=id=>{if(!elements.has(id))elements.set(id,{});return elements.get(id);};
const update={available:true,busy:false,message:'Version disponible'};
const context=vm.createContext({
  $:element,busy:true,loggedIn:true,historyReady:true,historySaving:0,
  historySyncPending:false,endpointDirty:true,
  api:async route=>{calls.push(route);return {update,version:'test',connection:null};},
  flushHistory:async()=>calls.push('history-saved'),
  error:error=>{throw error;},
});
vm.runInContext(source.match(/^    async function clientState\(\).+$/m)[0],context);
vm.runInContext(source.match(/^    \$\('update-apply'\)\.onclick=.+$/m)[0],context);
(async()=>{
  await vm.runInContext('clientState()',context);
  assert.equal(element('update-apply').disabled,false,'Update must remain available during generation');
  assert.equal(element('update-check').disabled,false);
  calls.length=0;
  await element('update-apply').onclick();
  assert.deepEqual(calls.slice(0,2),['history-saved','/client/update/apply']);
  update.busy=true;
  await vm.runInContext('clientState()',context);
  assert.equal(element('update-apply').disabled,true,'Prevent duplicate installations');
  assert.equal(element('update-check').disabled,true);
  update.busy=false;update.available=false;
  await vm.runInContext('clientState()',context);
  assert.equal(element('update-apply').disabled,true,'No installation without an available release');
  console.log('Update during conversation: controls, history save and apply request passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
