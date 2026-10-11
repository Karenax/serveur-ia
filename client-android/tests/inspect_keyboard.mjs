/* Focused on-device keyboard/close checks for explicit Android test fixtures. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {fileURLToPath} from 'node:url';

const args=process.argv.slice(2);
const option=(name,fallback)=>{const index=args.indexOf(name);return index<0?fallback:args[index+1];};
const port=Number(option('--port','9223'));
const serial=option('--serial','emulator-5554');
const form=option('--form','phone');
const workspace=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const output=path.resolve(option('--output',path.join(workspace,'toolchain/android-tests')));
const adb=option('--adb',path.join(workspace,'toolchain/android-sdk/platform-tools/adb.exe'));
assert(Number.isInteger(port)&&port>0&&port<65536,'Expected a local CDP port');
assert(['phone','tablet'].includes(form),'Expected phone or tablet');
assert(/^[A-Za-z0-9_.:-]+$/.test(serial),'Expected a device serial');
await fs.mkdir(output,{recursive:true});
const run=promisify(execFile);
const adbCall=async(...command)=>{try{return(await run(adb,['-s',serial,...command],{encoding:'buffer',maxBuffer:32*1024*1024})).stdout;}catch(error){
  // Some emulator images return 255 after dumping valid IME state and debug history.
  if(command.join(' ')==='shell dumpsys input_method'&&error.stdout?.toString().startsWith('Input Method Manager Service state:')&&/\bmInputShown=(true|false)\b/.test(error.stdout.toString()))return error.stdout;
  throw new Error('ADB test command failed: '+command[0]);
}};
const imeShown=async()=>(await adbCall('shell','dumpsys','input_method')).toString().match(/\bmInputShown=(true|false)\b/)?.[1]==='true';
const targets=await (await fetch('http://127.0.0.1:'+port+'/json')).json();
const target=targets.find(value=>value.type==='page'&&value.webSocketDebuggerUrl&&value.url.startsWith('http://127.0.0.1:'));
assert(target,'No local Android WebView found');
const socket=new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve,reject)=>{socket.addEventListener('open',resolve,{once:true});socket.addEventListener('error',reject,{once:true});});
let nextId=0;const pending=new Map();const errors=[];
socket.addEventListener('close',()=>{for(const waiter of pending.values()){clearTimeout(waiter.timer);waiter.reject(new Error('The test WebView disconnected'));}pending.clear();});
socket.addEventListener('message',event=>{
  const message=JSON.parse(event.data);
  if(message.id){const waiter=pending.get(message.id);if(!waiter)return;pending.delete(message.id);clearTimeout(waiter.timer);message.error?waiter.reject(new Error('CDP command failed')):waiter.resolve(message.result);return;}
  if(message.method==='Runtime.exceptionThrown')errors.push('Unhandled JavaScript exception');
  if(message.method==='Runtime.consoleAPICalled'&&message.params.type==='error')errors.push('JavaScript console error');
});
const call=(method,params={})=>new Promise((resolve,reject)=>{if(socket.readyState!==WebSocket.OPEN)return reject(new Error('WebView unavailable'));const id=++nextId;const timer=setTimeout(()=>{pending.delete(id);reject(new Error('CDP timeout: '+method));},15000);pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params}));});
const evaluate=async expression=>{const result=await call('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(result.exceptionDetails)throw new Error('Test evaluation failed');return result.result.value;};
const sleep=milliseconds=>new Promise(resolve=>setTimeout(resolve,milliseconds));
async function until(check,label,timeout=10000){const end=Date.now()+timeout;while(Date.now()<end){if(await check())return;await sleep(160);}throw new Error('Timed out waiting for '+label);}
const bounds=()=>evaluate("(()=>{const rect=id=>{const r=document.getElementById(id).getBoundingClientRect();return {top:Math.round(r.top),bottom:Math.round(r.bottom),height:Math.round(r.height)};};return {height:innerHeight,visualHeight:Math.round(visualViewport?.height||innerHeight),keyboard:document.body.classList.contains('android-keyboard'),focused:document.activeElement?.id,prompt:rect('prompt'),send:rect('send'),overflow:document.documentElement.scrollWidth>innerWidth+1};})()");
try{
  await call('Runtime.enable');
  assert(await evaluate("typeof config!=='undefined'&&['fred-demo','fred-fixture'].includes(config.model)&&config.platform==='android'&&window.AndroidClient&&historyReady&&!historyBlocked&&!busy"),'Refusing checks outside an idle explicit Android test fixture');
  assert(!(await evaluate("document.getElementById('android-onboarding').open||document.getElementById('connection-choice').open")),'Test fixture must have completed onboarding');
  if(await imeShown()){await adbCall('shell','input','keyevent','KEYCODE_BACK');await until(async()=>!await imeShown(),'initial keyboard dismissal');}
  await evaluate("document.activeElement?.blur();showView('chat');document.body.classList.remove('sidebar-open');uiSyncSidebar();");
  await sleep(350);
  const before=await bounds();
  const point=await evaluate("(()=>{const element=document.getElementById('prompt');element.scrollIntoView({block:'nearest'});const box=element.getBoundingClientRect();return {x:box.x+box.width/2,y:box.y+box.height/2};})()");
  await call('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[point]});
  await call('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
  await until(imeShown,'the real Android keyboard');
  await until(async()=>{const value=await bounds();return value.height<before.height-120&&value.focused==='prompt';},'WebView height reduced by the native IME insets');
  await sleep(250);
  const keyboard=await bounds();
  const capture=await adbCall('exec-out','screencap','-p');
  await fs.writeFile(path.join(output,form+'-keyboard-native.png'),capture);
  assert(keyboard.keyboard,'Mobile keyboard layout should be active');
  for(const name of ['prompt','send']){
    assert(keyboard[name].height>=40,name+' should remain a usable touch target');
    assert(keyboard[name].top>=0&&keyboard[name].bottom<=keyboard.visualHeight+1,name+' should remain above the real keyboard');
  }
  assert(!keyboard.overflow,'No horizontal scroll while keyboard is open');
  await adbCall('shell','input','keyevent','KEYCODE_BACK');
  await until(async()=>!await imeShown(),'keyboard dismissal');
  await until(async()=>{const value=await bounds();return value.height>=before.height-2;},'restored full WebView height');
  const restored=await bounds();
  assert.equal(await evaluate("(async()=>{const previous=historyBlocked;try{historyBlocked=true;return await window.androidFlush();}finally{historyBlocked=previous;error('');buttons();}})()"),false,'Blocked history must prevent native close');
  assert.equal(await evaluate('window.androidFlush()'),true,'Healthy history must flush before native close');
  assert.deepEqual(errors,[],'No console errors or unhandled JavaScript exceptions');
  const result={form,before,keyboard,restored,checks:['native IME visibility','WebView height reduction','prompt/send above keyboard','keyboard dismissal','blocked close refuses save','healthy close flush'],errors:0,ok:true};
  await fs.writeFile(path.join(output,form+'-keyboard-result.json'),JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify(result));
}finally{socket.close();for(const waiter of pending.values()){clearTimeout(waiter.timer);waiter.reject(new Error('Test session closed'));}pending.clear();}
