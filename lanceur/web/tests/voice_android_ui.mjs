// Real HTTPS model installation in the disposable debug app; no user profile.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
const root=process.cwd(),adb=path.join(root,'toolchain/android-sdk/platform-tools/adb.exe'),device=process.argv[2]||'emulator-5554',app='net.karenax.fred.voiceqa';
const run=(...args)=>execFileSync(adb,['-s',device,...args],{encoding:'utf8',windowsHide:true}).trim();
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
run('shell','am','start','-n',app+'/net.karenax.fred.MainActivity','--ez','fred_demo','true');
let pid='';for(let i=0;i<50&&!pid;i++){try{pid=run('shell','pidof',app);}catch{}await sleep(100);}
assert(pid);const port=run('forward','tcp:0','localabstract:webview_devtools_remote_'+pid);
let target;for(let i=0;i<100;i++){try{target=(await(await fetch('http://127.0.0.1:'+port+'/json')).json()).find(t=>t.type==='page'&&t.url.startsWith('http://127.0.0.1:'));}catch{}if(target)break;await sleep(100);}
assert(target,'Debug WebView must be local');
const ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});let sequence=0;const pending=new Map();
ws.onmessage=event=>{const value=JSON.parse(event.data);if(!value.id)return;const job=pending.get(value.id);pending.delete(value.id);if(value.error)job.reject(new Error(value.error.message));else job.resolve(value.result);};
async function evaluate(expression){const id=++sequence;const result=await new Promise((resolve,reject)=>{pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method:'Runtime.evaluate',params:{expression,returnByValue:true,awaitPromise:true}}));});assert(!result.exceptionDetails,'Native bridge exception');return result.result.value;}
async function status(){return JSON.parse(await evaluate('AndroidClient.voiceStatus()'));}
async function action(command){const result=JSON.parse(await evaluate('AndroidClient.voiceAction('+JSON.stringify(JSON.stringify(command))+')'));assert(!result.error,result.error);return result;}

const errors=[];ws.onmessage=event=>{const value=JSON.parse(event.data);if(value.method==='Runtime.exceptionThrown')errors.push(value.params.exceptionDetails.text);if(!value.id)return;const job=pending.get(value.id);pending.delete(value.id);if(value.error)job.reject(new Error(value.error.message));else job.resolve(value.result);};
async function command(method,params){const id=++sequence;return new Promise((resolve,reject)=>{pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});}
try{
 await command('Runtime.enable',{});await command('Page.enable',{});
 await evaluate(`AndroidClient.setConnectionMode('https');window.androidConnectionChanged?.()`);
 for(let i=0;i<150;i++){if(await evaluate(`typeof historyReady!=='undefined'&&historyReady&&document.getElementById('voice-start')`))break;await sleep(100);}
 assert(await evaluate(`document.getElementById('voice-start')?.textContent==='Dicter'`),'Small should be installed');
 assert(await evaluate(`document.documentElement.scrollWidth<=innerWidth+1`),'Native WebView overflow');
 assert(await evaluate(`(()=>{const b=document.getElementById('voice-start');return b.scrollWidth<=b.clientWidth&&b.getBoundingClientRect().height>=44;})()`),'Microphone label and touch target must fit');
 if(process.argv.includes('--microphone-background')){
  assert(await evaluate(`!document.getElementById('voice-start').disabled`),'Dictation must be usable');
  await evaluate(`document.getElementById('voice-start').click()`);let end=Date.now()+40000;
  while(Date.now()<end){if((await status()).phase==='listening')break;await sleep(100);}
  assert.equal((await status()).phase,'listening');await sleep(300);
  assert(await evaluate(`(()=>{const b=document.getElementById('voice-start');return b.textContent==='Terminer la dictée'&&b.scrollWidth<=b.clientWidth&&document.getElementById('send').disabled;})()`),'Listening UI label and send gate');
  const listening=await command('Page.captureScreenshot',{format:'png'});await fs.writeFile(path.join(root,'preuves/voix-small-20261011',device+'-microphone-listening.png'),Buffer.from(listening.data,'base64'));
  run('shell','input','keyevent','KEYCODE_HOME');end=Date.now()+120000;
  while(Date.now()<end){const current=await status();assert.notEqual(current.phase,'error',current.message);if(current.phase==='ready')break;await sleep(200);}
  assert.equal((await status()).phase,'ready','Real Activity.onPause must finalize microphone capture');
  run('shell','am','start','-n',app+'/net.karenax.fred.MainActivity','--ez','fred_demo','true');await sleep(800);
 }
 const captured=await command('Page.captureScreenshot',{format:'png'});await fs.writeFile(path.join(root,'preuves/voix-small-20261011',device+'-voice-ui.png'),Buffer.from(captured.data,'base64'));
 assert.deepEqual(errors,[]);console.log(JSON.stringify({passed:true,device,installed:true,no_overflow:true,no_js_errors:true}));
}finally{ws.close();run('forward','--remove','tcp:'+port);}
