/* Run only on the explicit Android debug demo; never open a personal profile. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const args=process.argv.slice(2),option=(name,fallback)=>{const index=args.indexOf(name);return index<0?fallback:args[index+1];};
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..'),port=Number(option('--port','9338')),serial=option('--serial','emulator-5554');
const output=path.resolve(option('--output',path.join(root,'toolchain/android-tests/model-picker-webview')));
assert(/^emulator-\d+$/.test(serial));assert(Number.isInteger(port)&&port>0&&port<65536);await fs.mkdir(output,{recursive:true});
const adb=(...commands)=>execFileSync(path.join(root,'toolchain/android-sdk/platform-tools/adb.exe'),['-s',serial,...commands],{windowsHide:true,maxBuffer:12*1024*1024});
const targets=await(await fetch('http://127.0.0.1:'+port+'/json')).json(),target=targets.find(item=>item.type==='page'&&item.webSocketDebuggerUrl&&item.url.startsWith('http://127.0.0.1:'));
assert(target,'No local WebView found');const socket=new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve,reject)=>{socket.addEventListener('open',resolve,{once:true});socket.addEventListener('error',reject,{once:true});});
let next=0;const pending=new Map(),errors=[],checks=[];
socket.addEventListener('message',event=>{const message=JSON.parse(event.data);if(message.id){const waiter=pending.get(message.id);if(!waiter)return;pending.delete(message.id);clearTimeout(waiter.timer);message.error?waiter.reject(new Error(message.error.message)):waiter.resolve(message.result);}else if(message.method==='Runtime.exceptionThrown')errors.push(message.params.exceptionDetails.text);});
const call=(method,params={})=>new Promise((resolve,reject)=>{const id=++next,timer=setTimeout(()=>{pending.delete(id);reject(new Error('CDP timed out: '+method));},30000);pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params}));});
const evaluate=async expression=>{const result=await call('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});assert(!result.exceptionDetails,result.exceptionDetails?.text);return result.result.value;};
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function until(expression,label){const end=Date.now()+20000;while(Date.now()<end){if(await evaluate(expression))return;await sleep(150);}throw new Error('Timed out: '+label);}
const nativeTree=()=>{adb('shell','uiautomator','dump','/sdcard/fred-model-picker-fixture.xml');return adb('exec-out','cat','/sdcard/fred-model-picker-fixture.xml').toString('utf8');};
function nodes(xml){return [...xml.matchAll(/<node\s+([^>]+)/g)].map(match=>Object.fromEntries([...match[1].matchAll(/([\w-]+)="([^"]*)"/g)].map(item=>[item[1],item[2]])));}
const bounds=node=>node.bounds.match(/\d+/g).map(Number);
let prepared=false;
try{
 await call('Runtime.enable');await until("typeof config!=='undefined'&&config.model==='fred-demo'&&historyReady&&!conversationLocked()&&connected",'explicit local demo');
 assert(await evaluate("document.getElementById('android-profile-name').textContent.includes('Démonstration locale')"),'Refusing UI mutations outside the local demo');
 await evaluate(`(()=>{window.__pickerOriginalFetch=window.fetch;window.__pickerHistory=JSON.parse(JSON.stringify({library,currentId}));window.__pickerCatalogueCalls=0;window.__pickerRows=[{id:'fred-demo',name:'Démonstration locale',provider:'Fixture',available:true},...Array.from({length:120},(_,i)=>({id:'fred-model-'+i.toString(16).padStart(24,'0'),name:'Modèle synthétique '+String(i+1).padStart(3,'0'),provider:'Fixture',available:true,capabilities:{context_length:131072}})),{id:'fred-model-'+ 'f'.repeat(24),name:'Modèle indisponible synthétique',provider:'Fixture',available:false}];window.fetch=function(input,init){if(input==='/v1/models'){window.__pickerCatalogueCalls++;const response=new Response(JSON.stringify({object:'list',data:window.__pickerRows,source:'hermes',default_model:'fred-demo'}),{status:200,headers:{'Content-Type':'application/json'}});return window.__pickerHold?window.__pickerHold.then(()=>response):Promise.resolve(response);}return window.__pickerOriginalFetch.call(this,input,init);};showView('chat');library.find(c=>c.id===currentId).model='fred-demo';return models();})()`);prepared=true;
 assert.equal(await evaluate("document.getElementById('conversation-model').options.length"),121);checks.push('121 available options; unavailable model hidden');
 const point=await evaluate("(()=>{const control=document.getElementById('conversation-model');control.scrollIntoView({block:'center'});window.__pickerNodes=[...control.options];const b=control.getBoundingClientRect();return{x:b.x+b.width/2,y:b.y+b.height/2};})()");
 await call('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[point]});await call('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await sleep(500);
 let tree=nativeTree();assert(tree.includes('Modèle synthétique'),'Native select popup opened');checks.push('Native Android popup opens the long catalogue');
 const callsBefore=await evaluate('__pickerCatalogueCalls');for(let i=0;i<5;i++)await evaluate('models()');
 const popupState=await evaluate("({focused:document.activeElement===document.getElementById('conversation-model'),active:document.activeElement?.id,identical:__pickerNodes.every((node,i)=>node===document.getElementById('conversation-model').options[i]),options:document.getElementById('conversation-model').options.length,selected:conversationModel()})");
 console.log(JSON.stringify({native_popup_poll_state:popupState}));
 assert(popupState.identical,'Polling must preserve native option nodes');
 assert.equal(await evaluate('__pickerCatalogueCalls'),callsBefore,'Focused popup must defer catalogue requests');
 tree=nativeTree();assert(tree.includes('Modèle synthétique'));checks.push('Five attempted catalogue polls defer requests and preserve native popup and option nodes');
 let scroll=nodes(tree).find(node=>node.scrollable==='true'&&node.class==='android.widget.ListView');assert(scroll,'Native options list is scrollable');
 const [left,top,right,bottom]=bounds(scroll),x=Math.round((left+right)/2),start=Math.round(top+(bottom-top)*.85),end=Math.round(top+(bottom-top)*.15);
 const beforeRows=nodes(tree).filter(node=>node.text?.startsWith('Modèle synthétique')).map(node=>node.text);
 for(let i=0;i<4;i++)adb('shell','input','swipe',String(x),String(start),String(x),String(end),'200');
 tree=nativeTree();const visibleRows=nodes(tree).filter(node=>node.text?.startsWith('Modèle synthétique'));
 assert(visibleRows.length);assert.notDeepEqual(visibleRows.map(node=>node.text),beforeRows);checks.push('Four native swipe gestures move the options list');
 const row=visibleRows[Math.floor(visibleRows.length/2)],index=Number(row.text.match(/synthétique (\d+)/)[1])-1,expected='fred-model-'+index.toString(16).padStart(24,'0');
 const [l,t,r,b]=bounds(row);adb('shell','input','tap',String(Math.round((l+r)/2)),String(Math.round((t+b)/2)));
 await until(`conversationModel()===${JSON.stringify(expected)}`,'native selected model');checks.push('Native tap commits the scrolled model into its conversation');
 await evaluate("document.getElementById('conversation-model').focus();window.__pickerNodes=[...document.getElementById('conversation-model').options];__pickerRows.push({id:'fred-model-'+ 'e'.repeat(24),name:'Modèle ajouté synthétique',available:true});models();");
 assert(await evaluate("document.getElementById('conversation-model').options.length===121&&__pickerNodes.every((node,i)=>node===document.getElementById('conversation-model').options[i])"));
 await evaluate("document.getElementById('prompt').focus()");await until("document.getElementById('conversation-model').options.length===122&&!modelsPending",'deferred catalogue applied on blur');checks.push('Changed catalogue waits for blur before changing the option list');
 await evaluate("__pickerRows.push({id:'fred-model-'+ 'd'.repeat(24),name:'Modèle en vol synthétique',available:true});window.__pickerHold=new Promise(resolve=>window.__pickerRelease=resolve);window.__pickerFlight=models();true");
 const flightPoint=await evaluate("(()=>{const control=document.getElementById('conversation-model');control.scrollIntoView({block:'center'});window.__pickerFlightNodes=[...control.options];const b=control.getBoundingClientRect();return{x:b.x+b.width/2,y:b.y+b.height/2};})()");
 await call('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[flightPoint]});await call('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
 assert(nativeTree().includes('Modèle synthétique'));await evaluate('__pickerRelease();window.__pickerHold=null;true');await evaluate('__pickerFlight');
 assert(nativeTree().includes('Modèle synthétique'),'An in-flight catalogue response must leave the native popup open');
 assert(await evaluate("__pickerFlightNodes.every((node,i)=>node===document.getElementById('conversation-model').options[i])"));
 adb('shell','input','keyevent','4');await evaluate("document.getElementById('prompt').focus()");await until("document.getElementById('conversation-model').options.length===123&&!modelsPending",'in-flight catalogue applied after popup closes');checks.push('A request started before opening the popup also waits for blur before applying its result');
 assert(await evaluate('document.documentElement.scrollWidth<=innerWidth+1'));assert.deepEqual(errors,[]);checks.push('No horizontal overflow or unhandled WebView errors');
 const report={passed:true,synthetic_only:true,real_webview:true,real_native_popup:true,debug_demo_no_server:true,serial,checks,exceptions:0,available_options:121,native_swipes:4,deferred_poll_attempts:5,inflight_result_deferred:true,native_popup_dom_focus:popupState.focused,selected_model_index:index+1};
 await fs.writeFile(path.join(output,'android-webview-picker.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
}finally{
 if(prepared)await evaluate("(async()=>{window.__pickerRelease?.();window.__pickerHold=null;window.fetch=__pickerOriginalFetch;library=__pickerHistory.library;currentId=__pickerHistory.currentId;messages=library.find(c=>c.id===currentId).messages;document.getElementById('prompt').blur();await models();await flushHistory();for(const name of ['__pickerOriginalFetch','__pickerHistory','__pickerRows','__pickerNodes','__pickerFlightNodes','__pickerFlight','__pickerRelease','__pickerHold','__pickerCatalogueCalls'])delete window[name];})()").catch(()=>{});
 adb('shell','rm','-f','/sdcard/fred-model-picker-fixture.xml');socket.close();for(const waiter of pending.values())clearTimeout(waiter.timer);
}
