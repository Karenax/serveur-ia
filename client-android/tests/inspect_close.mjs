/* Native gesture/close/persistence check, limited to explicit emulator fixtures. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {fileURLToPath} from 'node:url';
const args=process.argv.slice(2);
const option=(name,fallback)=>{const index=args.indexOf(name);return index<0?fallback:args[index+1];};
const port=Number(option('--port','9223')),serial=option('--serial','emulator-5554'),form=option('--form','phone');
const workspace=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const output=path.resolve(option('--output',path.join(workspace,'toolchain/android-tests')));
const adb=option('--adb',path.join(workspace,'toolchain/android-sdk/platform-tools/adb.exe'));
assert(Number.isInteger(port)&&port>0&&port<65536&&['phone','tablet'].includes(form),'Expected test port/form');
assert(/^emulator-[0-9]+$/.test(serial),'Native close checks require an explicit emulator');
await fs.mkdir(output,{recursive:true});
const run=promisify(execFile);
const adbCall=async(...command)=>{try{return(await run(adb,['-s',serial,...command],{encoding:'buffer',maxBuffer:32*1024*1024,timeout:15000})).stdout;}catch{throw new Error('ADB close check command failed: '+command[0]);}};
const sleep=milliseconds=>new Promise(resolve=>setTimeout(resolve,milliseconds));
async function until(check,label,timeout=15000){const end=Date.now()+timeout;while(Date.now()<end){if(await check())return;await sleep(200);}throw new Error('Timed out waiting for '+label);}
let socket,nextId=0,fixtureValidated=false;const pending=new Map(),errors=[];
async function connect(){
  let target;
  await until(async()=>{try{const targets=await(await fetch('http://127.0.0.1:'+port+'/json')).json();target=targets.find(value=>value.type==='page'&&value.webSocketDebuggerUrl&&value.url.startsWith('http://127.0.0.1:'));return Boolean(target);}catch{return false;}},'test WebView');
  socket=new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{socket.addEventListener('open',resolve,{once:true});socket.addEventListener('error',reject,{once:true});});
  socket.addEventListener('close',()=>{for(const waiter of pending.values()){clearTimeout(waiter.timer);waiter.reject(new Error('Test WebView disconnected'));}pending.clear();});
  socket.addEventListener('message',event=>{
    const message=JSON.parse(event.data);
    if(message.id){const waiter=pending.get(message.id);if(!waiter)return;pending.delete(message.id);clearTimeout(waiter.timer);message.error?waiter.reject(new Error('CDP close command failed')):waiter.resolve(message.result);return;}
    if(message.method==='Runtime.exceptionThrown')errors.push('Unhandled JavaScript exception');
    if(message.method==='Runtime.consoleAPICalled'&&message.params.type==='error')errors.push('JavaScript console error');
  });
  await call('Runtime.enable');
}
const call=(method,params={})=>new Promise((resolve,reject)=>{if(socket?.readyState!==WebSocket.OPEN)return reject(new Error('WebView unavailable'));const id=++nextId,timer=setTimeout(()=>{pending.delete(id);reject(new Error('CDP close check timeout'));},15000);pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params}));});
const evaluate=async expression=>{const result=await call('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(result.exceptionDetails)throw new Error('Close check evaluation failed');return result.result.value;};
const historyDigest=()=>evaluate("(async()=>{const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify({conversations:library,currentId})));return [...new Uint8Array(digest)].map(value=>value.toString(16).padStart(2,'0')).join('');})()");
const screenSize=(await adbCall('shell','wm','size')).toString().match(/(?:Override|Physical) size: (\d+)x(\d+)/);
assert(screenSize,'Expected emulator screen size');
async function backGesture(){const width=Number(screenSize[1]),height=Number(screenSize[2]);await adbCall('shell','input','swipe','1',String(Math.round(height/2)),String(Math.round(width/3)),String(Math.round(height/2)),'300');}
const dumpPath='/sdcard/fred-close-test.xml';
async function nativeXml(){await adbCall('shell','uiautomator','dump',dumpPath);return(await adbCall('shell','cat',dumpPath)).toString();}
async function waitDialog(text){let xml='';await until(async()=>{xml=await nativeXml();return xml.includes('text="'+text+'"');},'native dialog '+text);return xml;}
async function tapNative(xml,text){const node=[...xml.matchAll(/<node\s[^>]+/g)].find(match=>match[0].match(/\btext="([^"]*)"/)?.[1].toLocaleLowerCase('fr')===text.toLocaleLowerCase('fr'))?.[0];const box=node?.match(/bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"/);assert(box,'Expected native test button '+text);await adbCall('shell','input','tap',String(Math.round((Number(box[1])+Number(box[3]))/2)),String(Math.round((Number(box[2])+Number(box[4]))/2)));}
try{
  await connect();
  await until(()=>evaluate("typeof config!=='undefined'&&['fred-demo','fred-fixture'].includes(config.model)&&config.platform==='android'&&historyReady&&!historyBlocked&&!busy"),'idle explicit test fixture');
  fixtureValidated=true;
  assert(!(await evaluate("document.getElementById('android-onboarding').open||document.getElementById('connection-choice').open")),'Test onboarding must already be complete');
  await evaluate("document.activeElement?.blur();showView('chat');for(let attempt=0;attempt<12&&window.androidBack();attempt++){}historyBlocked=true;buttons();");
  await backGesture();
  let xml=await waitDialog('Fermer le client ?');
  await fs.writeFile(path.join(output,form+'-close-native.png'),await adbCall('exec-out','screencap','-p'));
  await tapNative(xml,'Fermer');
  xml=await waitDialog('Enregistrement non confirmé');
  assert(await evaluate('historyBlocked===true&&historyReady'),'Failed flush must leave the current WebView alive');
  await fs.writeFile(path.join(output,form+'-close-blocked-native.png'),await adbCall('exec-out','screencap','-p'));
  await tapNative(xml,'Rester');
  await evaluate("historyBlocked=false;error('');buttons();");
  assert.equal(await evaluate('window.androidFlush()'),true,'Healthy history should flush');
  const expected=await historyDigest();
  await backGesture();xml=await waitDialog('Fermer le client ?');await tapNative(xml,'Fermer');
  await until(async()=>{const state=(await adbCall('shell','dumpsys','activity','activities')).toString();return !/topResumedActivity=ActivityRecord\{[^\n]*net\.karenax\.fred/.test(state);},'finished native activity');
  socket.close();await sleep(100);
  await adbCall('shell','am','start','-n','net.karenax.fred/.MainActivity');
  const pid=(await adbCall('shell','pidof','net.karenax.fred')).toString().trim();assert(/^\d+$/.test(pid),'Expected resumed app process');
  await adbCall('forward','tcp:'+port,'localabstract:webview_devtools_remote_'+pid);
  await connect();
  await until(()=>evaluate("typeof historyReady!=='undefined'&&historyReady&&!historySyncPending&&typeof config!=='undefined'&&['fred-demo','fred-fixture'].includes(config.model)"),'reopened fixture history');
  assert.equal(await historyDigest(),expected,'Encrypted local history must survive native close and reopening unchanged');
  assert.deepEqual(errors,[],'No unhandled JavaScript or console errors');
  const result={form,checks:['real back gesture confirmation','blocked close keeps app open','healthy close finishes activity','encrypted history preserved after reopening'],errors:0,ok:true};
  await fs.writeFile(path.join(output,form+'-close-result.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
}finally{
  if(fixtureValidated&&socket?.readyState===WebSocket.OPEN)await evaluate("if(typeof historyBlocked!=='undefined'&&historyBlocked){historyBlocked=false;error('');buttons();}").catch(()=>{});
  socket?.close();for(const waiter of pending.values()){clearTimeout(waiter.timer);waiter.reject(new Error('Close check session closed'));}pending.clear();
}
