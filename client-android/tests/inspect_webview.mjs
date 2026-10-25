/* Run only against the explicitly enabled local Android demo, never a personal profile. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const args=process.argv.slice(2);
const option=(name,fallback)=>{const index=args.indexOf(name);return index<0?fallback:args[index+1];};
const port=Number(option('--port','9222'));
const form=option('--form','phone');
const skipBlockedHistory=args.includes('--skip-blocked-history');
assert(Number.isInteger(port)&&port>0&&port<65536,'Expected a valid local CDP port');
assert(['phone','tablet'].includes(form),'Expected --form phone or tablet');
const workspace=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const output=path.resolve(option('--output',path.join(workspace,'toolchain/android-tests')));
await fs.mkdir(output,{recursive:true});
const targets=await (await fetch('http://127.0.0.1:'+port+'/json')).json();
const target=targets.find(target=>target.type==='page'&&target.webSocketDebuggerUrl&&target.url.startsWith('http://127.0.0.1:'));
assert(target,'No local Kiara WebView found on the forwarded CDP port');
const socket=new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve,reject)=>{socket.addEventListener('open',resolve,{once:true});socket.addEventListener('error',reject,{once:true});});
let nextId=0;const pending=new Map();const errors=[];
const redact=value=>String(value).replace(/(?:local_[A-Za-z0-9_-]+|qwen_[A-Za-z0-9_-]+)/g,'[credential]').replace(/https?:\/\/[^\s"']+/g,'[url]').slice(0,400);
socket.addEventListener('close',()=>{for(const waiter of pending.values()){clearTimeout(waiter.timer);waiter.reject(new Error('The Android WebView CDP connection closed'));}pending.clear();});
socket.addEventListener('message',event=>{
  const message=JSON.parse(event.data);
  if(message.id){const waiter=pending.get(message.id);if(!waiter)return;pending.delete(message.id);clearTimeout(waiter.timer);if(message.error)waiter.reject(new Error(redact(message.error.message)));else waiter.resolve(message.result);return;}
  if(message.method==='Runtime.exceptionThrown')errors.push({type:'exception',message:redact(message.params.exceptionDetails.exception?.description||message.params.exceptionDetails.text)});
  if(message.method==='Runtime.consoleAPICalled'&&message.params.type==='error')errors.push({type:'console',message:redact(message.params.args.map(arg=>arg.value||arg.description||'').join(' '))});
});
const call=(method,params={})=>new Promise((resolve,reject)=>{if(socket.readyState!==WebSocket.OPEN)return reject(new Error('The Android WebView CDP connection is unavailable'));const id=++nextId;const timer=setTimeout(()=>{pending.delete(id);reject(new Error('CDP command timed out: '+method));},45000);pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params}));});
const evaluate=async expression=>{
  const result=await call('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});
  if(result.exceptionDetails)throw new Error(redact(result.exceptionDetails.exception?.description||result.exceptionDetails.text));
  return result.result.value;
};
const sleep=milliseconds=>new Promise(resolve=>setTimeout(resolve,milliseconds));
async function until(expression,label,timeout=30000){const end=Date.now()+timeout;while(Date.now()<end){if(await evaluate(expression))return;await sleep(120);}throw new Error('Timed out waiting for '+label);}
async function click(selector){
  const point=await evaluate(`(()=>{const element=document.querySelector(${JSON.stringify(selector)});if(!element||element.hidden||element.disabled)throw new Error('Unavailable test control');element.scrollIntoView({block:'center'});const box=element.getBoundingClientRect();return {x:box.x+box.width/2,y:box.y+box.height/2};})()`);
  await call('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:point.x,y:point.y}]});
  await call('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
}
const fill=(id,value)=>evaluate(`(()=>{const element=document.getElementById(${JSON.stringify(id)});element.value=${JSON.stringify(value)};element.dispatchEvent(new Event('input',{bubbles:true}));element.dispatchEvent(new Event('change',{bubbles:true}));})()`);
const show=name=>evaluate(`showView(${JSON.stringify(name)})`);
async function screenshot(name){const capture=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});const file=path.join(output,form+'-'+name+'.png');await fs.writeFile(file,Buffer.from(capture.data,'base64'));return file;}
const checks=[];
try{
  await call('Page.enable');await call('Runtime.enable');
  await until("typeof config!=='undefined'&&config.model==='fred-demo'&&typeof historyReady!=='undefined'&&historyReady&&!historySyncPending&&document.getElementById('send')&&!document.getElementById('send').disabled",'the explicit local demo');
  assert(await evaluate("document.getElementById('android-profile-name').textContent.includes('Démonstration locale')"),'Refusing UI mutations outside the local demo');
  assert(!(await evaluate("document.getElementById('android-onboarding').open||document.getElementById('connection-choice').open")),'Demo should already have its local connection');
  await evaluate("ws.bootstrapDone?Promise.resolve():wsBootstrap()");
  await show('chat');
  await click('#new');
  await until('!conversationLocked()','new conversation');
  await fill('prompt','Vérification Android : une réponse de démonstration suffit.');
  await click('#send');
  await until('busy','stream start',5000);
  await until("messages.some(message=>message.role==='assistant'&&message.content.length>10)",'incremental SSE text',8000);
  await until("!busy&&messages.some(message=>message.role==='assistant'&&message.content.includes('démonstration'))",'completed chat');
  checks.push('chat SSE');
  await until("/^Contexte .* % · .* \\/ /.test(document.getElementById('context-label').textContent)&&!document.getElementById('context-label').textContent.includes('NaN')",'context capacity gauge');
  assert(await evaluate("Number.isFinite(document.getElementById('context-progress').value)&&document.getElementById('context-progress').hasAttribute('value')"),'Native context tokens/capacity should produce a numeric gauge');
  checks.push('context capacity');
  assert(await evaluate("(()=>{const node=document.createElement('div');renderMarkdown(node,'**Android**\\n\\n- Téléphone\\n- Tablette');return node.querySelector('strong')?.textContent==='Android'&&node.querySelectorAll('li').length===2;})()"),'Shared Markdown renderer');
  checks.push('Markdown');
  await screenshot('conversation');
  await show('projects');
  await evaluate("document.getElementById('ws-create-project').hidden=true");
  await click('#ui-project-create');
  const projectTitle='Validation '+form+' '+Date.now();
  await fill('ws-project-name',projectTitle);
  await click('#ws-create-project button');
  await until("ws.data?.projects.some(project=>project.title==="+JSON.stringify(projectTitle)+"&&project.id===ws.project)&&document.getElementById('ws-project-detail').hidden===false",'project creation');
  const projectId=await evaluate('ws.project');
  await click('#ws-new-document');
  await until("ws.document&&!document.getElementById('ws-document-editor').hidden",'document creation');
  await fill('ws-document-title','Note de vérification Android');
  await fill('ws-document-text','Une note modifiée depuis le '+(form==='phone'?'téléphone':'format tablette')+'.\nLes caractères français : é, è, à, ç.');
  await evaluate('wsFlush()');
  assert(await evaluate("!ws.dirty&&document.getElementById('ws-document-status').textContent.includes('Enregistré')"),'Document should be saved');
  const documentId=await evaluate('ws.document.id');
  await evaluate(`wsOpenDocument(${JSON.stringify(documentId)})`);
  assert((await evaluate("document.getElementById('ws-document-text').value")).includes('é, è, à, ç'),'Saved document should reload with UTF-8 text');
  checks.push('projects/documents');
  await screenshot('projet-document');
  await show('tasks');
  await evaluate("document.getElementById('ui-task-create').open=true");
  await evaluate(`document.getElementById('ws-task-project').value=${JSON.stringify(projectId)}`);
  await fill('ws-task-prompt','Préparer une tâche locale de vérification Android.');
  await click('#ws-task-form button[type=submit], #ws-task-form > .ws-toolbar button:first-child');
  await until("ws.data.jobs.some(job=>job.project==="+JSON.stringify(projectId)+"&&job.state==='completed')",'completed local job');
  const jobId=await evaluate("ws.data.jobs.find(job=>job.project==="+JSON.stringify(projectId)+").id");
  await evaluate(`wsOpenJob(${JSON.stringify(jobId)})`);
  assert((await evaluate("document.getElementById('ws-job-content').textContent")).includes('démonstration'),'Job result should be accessible');
  checks.push('tasks/results');
  await screenshot('taches');
  await show('corrector');
  await fill('corrector-text','Je veut vérifier le correcteur sur Android.');
  await click('#corrector-correct');
  await until('correctorRunning','corrector stream start',5000);
  await until("!correctorRunning&&correctorAnswer.content.length>20",'corrector result');
  assert((await evaluate("document.getElementById('corrector-status').textContent")).includes('terminé'),'Corrector should complete');
  checks.push('corrector');
  await screenshot('correcteur');
  await until('!conversationLocked()&&connected','corrector JSON fixture readiness');
  await evaluate("window.__fredTestOriginalFetch=window.fetch;window.__fredTestMockedJson=false;window.fetch=function(input,init){if(input==='/v1/chat/completions'){window.__fredTestMockedJson=true;return Promise.resolve(new Response(JSON.stringify({choices:[{message:{role:'assistant',content:'Je veux vérifier le correcteur JSON sur Android. É, è, à, ç.',reasoning_content:''}}]}),{status:200,headers:{'Content-Type':'application/json'}}));}return window.__fredTestOriginalFetch.call(this,input,init);}");
  await fill('corrector-text','Je veut vérifier le correcteur JSON sur Android.');
  await click('#corrector-correct');
  await until("window.__fredTestMockedJson&&!correctorRunning&&correctorAnswer.content.includes('correcteur JSON sur Android')",'corrector JSON fallback');
  assert((await evaluate("document.getElementById('corrector-status').textContent")).includes('terminé'),'Corrector JSON response should complete and save');
  assert(await evaluate("library.some(conversation=>conversation.messages.some(message=>message.role==='assistant'&&message.content.includes('correcteur JSON sur Android')))"),'Corrector JSON result should be stored in history');
  await evaluate('window.fetch=window.__fredTestOriginalFetch;delete window.__fredTestOriginalFetch;delete window.__fredTestMockedJson');
  checks.push('corrector JSON fallback');
  await show('chat');
  await click('#new');await until('!conversationLocked()','new cancellation conversation');
  await fill('prompt','Vérification de l’arrêt de la réponse.');
  await click('#send');await until('busy','cancellable stream',5000);
  await until("messages[messages.length-1]?.content.length>15",'partial answer',5000);
  await click('#cancel');await until('!busy','stream cancellation',8000);
  assert(await evaluate("messages[messages.length-1]?.interrupted===true&&messages[messages.length-1]?.content.length>0"),'Cancellation must preserve the partial answer');
  checks.push('cancel/partial preservation');
  assert(await evaluate('window.androidFlush()'),'Local history/preferences should flush');
  if(!skipBlockedHistory){
    assert.equal(await evaluate("(async()=>{const previous=historyBlocked;try{historyBlocked=true;return await window.androidFlush();}finally{historyBlocked=previous;error('');buttons();}})()"),false,'Blocked history must refuse the native close save confirmation');
    checks.push('blocked history close');
  }
  assert(!(await evaluate('document.documentElement.scrollWidth>innerWidth+1')),'WebView should not scroll horizontally');
  assert.deepEqual(errors,[],'No unhandled JavaScript or console errors');
  const result={form,checks,...(skipBlockedHistory?{skipped:['blocked history close (validated by browser fixture)']}:{}),errors:0,ok:true};
  await fs.writeFile(path.join(output,form+'-webview-result.json'),JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify(result));
}finally{await evaluate('if(window.__fredTestOriginalFetch){window.fetch=window.__fredTestOriginalFetch;delete window.__fredTestOriginalFetch;delete window.__fredTestMockedJson;}').catch(()=>{});socket.close();for(const waiter of pending.values()){clearTimeout(waiter.timer);waiter.reject(new Error('CDP session closed'));}pending.clear();}
