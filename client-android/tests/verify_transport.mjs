// Test only the synthetic transport_fixture.py profile; refuse personal accounts.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const args=process.argv.slice(2),opt=(key,fallback)=>args.includes(key)?args[args.indexOf(key)+1]:fallback;
const port=Number(opt('--port','9223'));
let pages=[];
const readyUntil=Date.now()+20000;
while(Date.now()<readyUntil){
  try{pages=await(await fetch(`http://127.0.0.1:${port}/json`)).json();if(pages.some(p=>p.type==='page'))break;}catch{}
  await new Promise(resolve=>setTimeout(resolve,100));
}
const page=pages.find(p=>p.type==='page'&&p.url.startsWith('http://127.0.0.1:'));
assert(page,'Expected local WebView');
const socket=new WebSocket(page.webSocketDebuggerUrl);
await new Promise((resolve,reject)=>{socket.addEventListener('open',resolve,{once:true});socket.addEventListener('error',reject,{once:true});});
let seq=0;const pending=new Map(),errors=[];
socket.addEventListener('message',event=>{const value=JSON.parse(event.data);if(value.id){const request=pending.get(value.id);if(request){clearTimeout(request.timer);pending.delete(value.id);value.error?request.reject(new Error('CDP failure')):request.resolve(value.result);}}else if(value.method==='Runtime.exceptionThrown')errors.push('WebView exception');});
const call=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq,timer=setTimeout(()=>{pending.delete(id);reject(new Error('CDP timeout'));},40000);pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params}));});
const evaluate=async expression=>{const result=await call('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});assert(!result.exceptionDetails,'WebView evaluation failed');return result.result.value;};
const until=async expression=>{const end=Date.now()+30000;while(Date.now()<end){if(await evaluate(expression))return;await new Promise(resolve=>setTimeout(resolve,100));}throw new Error('Fixture UI timeout');};
const output=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../toolchain/android-tests');
try{
  await call('Runtime.enable');await call('Page.enable');
  await until("typeof config!=='undefined'&&config.model==='fred-fixture'&&typeof historyReady!=='undefined'&&historyReady&&!historySyncPending");
  assert(await evaluate("document.getElementById('android-profile-name').textContent.startsWith('Fixture Android')"),'Refusing mutations outside isolated fixture');
  const state=await evaluate("api('/client/state').then(s=>({transport:s.connection.transport,hasProfile:!s.profile_required}))");
  assert(state.hasProfile,'Imported fixture');
  assert.equal(state.transport,'wireguard','Real tunnel selected');
  if(args.includes('--oversize-check')){
    for(const route of ['/v1/context','/v1/chat/completions']){
      const rejected=await evaluate(`api(${JSON.stringify(route)},{messages:[{role:'user',content:'A'.repeat(2*1024*1024)}]}).then(()=>({status:200})).catch(e=>({status:e.status,message:e.message}))`);
      assert.equal(rejected.status,413,'Large tunnel request rejected before sending');
      assert(rejected.message.includes('2 Mo')&&rejected.message.includes('WireGuard'),'Actionable structured error');
    }
  }
  if(!args.includes('--read-only')){
    await evaluate("showView('chat');document.getElementById('new').click()");
    await until('!conversationLocked()');
    await evaluate("(()=>{const input=document.getElementById('prompt');input.value='Vérifie le tunnel Android.';input.dispatchEvent(new Event('input',{bubbles:true}));document.getElementById('send').click();})()");
    await until("busy&&messages.some(m=>m.role==='assistant'&&m.content.length>5)");
    await until("!busy&&messages.some(m=>m.role==='assistant'&&m.content.includes('WireGuard vérifiée'))");
    assert(await evaluate('window.androidFlush()'),'Encrypted local history saved');
  }else assert(await evaluate("messages.some(m=>m.role==='assistant'&&m.content.includes('WireGuard vérifiée'))"),'Conversation persisted after restart');
  assert(await evaluate("document.getElementById('messages').querySelector('strong')?.textContent.includes('Réponse de test')"),'Markdown rendered across real tunnel');
  assert.equal(errors.length,0,'No WebView exception');
  if(args.includes('--export-history'))await evaluate("androidSaveFile('verification-fred.json',JSON.stringify({version:1,conversations:library},null,2),'application/json')");
  const capture=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
  await fs.writeFile(path.join(output,'wireguard-transport.png'),Buffer.from(capture.data,'base64'));
  const result={passed:true,checks:['installed WireGuard executable','authenticated UDP tunnel','incremental chat SSE','Markdown','encrypted history persistence'],reopened:args.includes('--read-only')};
  if(args.includes('--oversize-check'))result.checks.push('structured tunnel size errors for chat/context');
  await fs.writeFile(path.join(output,'wireguard-ui-result.json'),JSON.stringify(result,null,2));
  console.log(JSON.stringify(result));
}finally{socket.close();}
