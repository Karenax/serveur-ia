// Real HTTPS model installation in the disposable debug app; no user profile.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
const root=process.cwd(),adb=path.join(root,'toolchain/android-sdk/platform-tools/adb.exe'),device='emulator-5554',app='net.karenax.fred.voiceqa';
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
const report={device,app,public_model_only:true,stages:[]};
try{
  await action({action:'remove'});let installed=await action({action:'install'});const session=installed.session;let end=Date.now()+60000;
  while(Date.now()<end){installed=await status();assert.notEqual(installed.phase,'error',installed.message);if(installed.downloaded_bytes>1024*1024)break;await sleep(100);}
  assert(installed.downloaded_bytes>1024*1024);await action({action:'cancel',session});end=Date.now()+30000;
  while(Date.now()<end){installed=await status();if(installed.phase==='cancelled')break;await sleep(200);}
  assert.equal(installed.phase,'cancelled');assert.equal(installed.installed,false);report.stages.push({stage:'cancel_real_https_download',bytes:installed.downloaded_bytes,passed:true});
  await sleep(200);await action({action:'install'});end=Date.now()+600000;let resumed=false;
  while(Date.now()<end){const current=await status();assert.notEqual(current.phase,'error',current.message);if(current.downloaded_bytes>=installed.downloaded_bytes)resumed=true;if(current.phase==='idle'&&current.installed){report.stages.push({stage:'resume_and_verify_sha256',bytes:current.model_bytes,resumed,passed:true});break;}await sleep(500);}
  assert.equal(report.stages.length,2,'Installation timeout');assert(resumed);report.passed=true;
  await fs.writeFile(path.join(root,'preuves/voix-small-20261011/android-real-install.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
}finally{ws.close();run('forward','--remove','tcp:'+port);}
