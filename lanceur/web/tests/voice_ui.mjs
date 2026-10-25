// Exercises the real local administration API through the rendered console.
// A child fixture owns a TemporaryDirectory and cannot see legacy processes.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {spawn} from 'node:child_process';
import readline from 'node:readline';
import {fileURLToPath} from 'node:url';

const tests=path.dirname(fileURLToPath(import.meta.url)),repo=path.resolve(tests,'../../..');
const output=path.resolve(process.argv[2]||path.join(repo,'preuves/voix-small-20261011/browser'));
await fs.mkdir(output,{recursive:true});
const downloadPath=path.join(output,'downloads-'+Date.now());
const python=path.join(repo,'Strata-src/.venv/Scripts/python.exe'),secret='Browser isolated recovery phrase 2026';
const fixture=spawn(python,['-u',path.join(tests,'lots6_8_fixture.py')],{cwd:repo,windowsHide:true,stdio:['pipe','pipe','pipe']});
const lines=readline.createInterface({input:fixture.stdout})[Symbol.asyncIterator]();let fixtureError='';fixture.stderr.on('data',d=>fixtureError+=d.toString());
const first=await lines.next();assert(!first.done,'La fixture doit démarrer. '+fixtureError);const instance=JSON.parse(first.value);assert.equal(instance.fixture,true);assert(new URL(instance.url).hostname==='127.0.0.1');assert(path.basename(instance.home).startsWith('fred-lots6-8-'));
async function command(action,values={}){fixture.stdin.write(JSON.stringify({action,...values})+'\n');const next=await lines.next();assert(!next.done,'La fixture reste active. '+fixtureError);const value=JSON.parse(next.value);assert(!value.error,value.error);return value;}
const chrome=spawn('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',['--headless=new','--no-first-run','--disable-gpu','--no-default-browser-check','--remote-debugging-address=127.0.0.1','--remote-debugging-port=0','--user-data-dir='+path.join(output,'chrome-fixture-profile'),'about:blank'],{windowsHide:true,stdio:['ignore','ignore','pipe']});
let stderr='';chrome.stderr.on('data',d=>stderr+=d.toString());const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
let browserUrl;for(let i=0;i<150;i++){browserUrl=stderr.match(/DevTools listening on (ws:\/\/[^\s]+)/)?.[1];if(browserUrl)break;await sleep(100);}assert(browserUrl,'Chrome DevTools');
const port=new URL(browserUrl).port,targets=await(await fetch('http://127.0.0.1:'+port+'/json/list')).json();const target=targets.find(t=>t.type==='page');
const ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});let seq=0;const pending=new Map(),errors=[],requests=[],checks=[];
ws.onmessage=({data})=>{const m=JSON.parse(data);if(m.id){const item=pending.get(m.id);pending.delete(m.id);m.error?item.reject(new Error(m.error.message)):item.resolve(m.result);}else if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.exception?.description||m.params.exceptionDetails.text);else if(m.method==='Network.responseReceived'){const r=m.params.response;if(r.url.startsWith(instance.url+'/v1/')||r.url.startsWith(instance.admin_url+'/api/'))requests.push({path:new URL(r.url).pathname,status:r.status});}};
function cdp(method,params={}){return new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});}
async function evaluate(expression){const r=await cdp('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;}
async function until(expression,label){for(let i=0;i<200;i++){if(await evaluate(expression))return;await sleep(100);}throw new Error('Timeout : '+label);}
async function click(selector){await evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});if(!e||e.disabled)throw new Error('Commande absente ou désactivée');e.click();})()`);}
async function fill(selector,value){await evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});if(!e)throw new Error('Champ absent');e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('input',{bubbles:true}));})()`);}
async function submit(selector){await evaluate(`document.querySelector(${JSON.stringify(selector)}).requestSubmit()`);}
async function shot(name){const r=await cdp('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});await fs.writeFile(path.join(output,name+'.png'),Buffer.from(r.data,'base64'));}
async function check(name,work){await work();checks.push({name,passed:true});}

try{
 await cdp('Runtime.enable');await cdp('Page.enable');await cdp('Network.enable');
 await cdp('Page.addScriptToEvaluateOnNewDocument',{source:`
   window.fakeVoice={phase:'idle',installed:true,session:'',text:'',model_bytes:487601967,message:'Dictée locale'};
   window.voiceCalls=[];window.confirm=()=>true;
   const originalFetch=window.fetch;
   window.fetch=async function(url,options){if(String(url)!=='/client/voice')return originalFetch.apply(this,arguments);
     const command=options?.body?JSON.parse(options.body):null;
     if(command){voiceCalls.push(command);if(command.action==='start')fakeVoice={...fakeVoice,phase:'listening',session:'qa-session',text:''};
       if(command.action==='stop')fakeVoice={...fakeVoice,phase:'finishing',message:'Microphone fermé. Finalisation…'};
       if(command.action==='cancel')fakeVoice={...fakeVoice,phase:'cancelled',text:''};}
     return new Response(JSON.stringify(fakeVoice),{status:200,headers:{'Content-Type':'application/json'}});
   }`});
 await cdp('Page.navigate',{url:instance.url+'/chat'});await until(`typeof historyReady!=='undefined'&&historyReady&&connected&&!conversationLocked()&&document.getElementById('voice-start')&&!document.getElementById('voice-start').disabled`,'Composer ready');
 await check('Le brouillon existant est conservé',async()=>{await fill('#prompt','Mon brouillon');await click('#voice-start');await until(`window.voiceBusy`,'Microphone');assert.equal(await evaluate(`document.getElementById('prompt').readOnly`),true);});
 await check('Texte provisoire, aucun envoi automatique',async()=>{await evaluate(`fakeVoice.text='Bonjour provisoire';fakeVoice.seconds=6`);await until(`document.getElementById('prompt').value.includes('Bonjour provisoire')`,'Partial text');assert.equal(await evaluate(`document.getElementById('prompt').value`),'Mon brouillon\nBonjour provisoire');assert.equal(await evaluate(`document.getElementById('send').disabled`),true);assert.equal(await evaluate(`document.getElementById('new').disabled`),true);await submit('#composer');assert.equal(requests.filter(r=>r.path==='/v1/chat/completions').length,0);await shot('01-dictee-provisoire');});
 await check('Terminer ferme le micro et attend le texte final',async()=>{await click('#voice-start');await until(`fakeVoice.phase==='finishing'`,'Finishing');assert.equal(await evaluate(`document.getElementById('send').disabled`),true);await evaluate(`fakeVoice.phase='ready';fakeVoice.text='Bonjour Kiara, texte final.';fakeVoice.message='Texte prêt. Corrigez puis envoyez.'`);await until(`!window.voiceBusy&&!document.getElementById('send').disabled`,'Final');assert.equal(await evaluate(`document.getElementById('prompt').value`),'Mon brouillon\nBonjour Kiara, texte final.');assert.equal(await evaluate(`document.getElementById('prompt').readOnly`),false);assert.equal(requests.filter(r=>r.path==='/v1/chat/completions').length,0);await shot('02-dictee-finale');});
 await check('Annuler restaure exactement le brouillon',async()=>{await fill('#prompt','Brouillon à conserver');await click('#voice-start');await evaluate(`fakeVoice.text='À jeter'`);await until(`document.getElementById('prompt').value.includes('À jeter')`,'Partial');await click('#voice-cancel');await until(`!window.voiceBusy`,'Cancelled');assert.equal(await evaluate(`document.getElementById('prompt').value`),'Brouillon à conserver');});
 await check('Une erreur de capture permet de reprendre le clavier',async()=>{await click('#voice-start');await evaluate(`fakeVoice.phase='error';fakeVoice.message='Microphone refusé';fakeVoice.text=''`);await until(`!window.voiceBusy`,'Capture error');assert.equal(await evaluate(`document.getElementById('prompt').readOnly`),false);assert.equal(await evaluate(`document.getElementById('prompt').value`),'Brouillon à conserver');});
 await check('Affichage téléphone et tablette sans débordement',async()=>{for(const [width,height] of [[390,844],[800,1280]]){await cdp('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:true});await evaluate(`document.querySelector('[data-view-button="chat"]')?.click();showView('chat')`);assert(await evaluate(`document.documentElement.scrollWidth<=innerWidth+1`));await shot('03-voice-'+width);}});
 assert.deepEqual(errors,[]);await fs.writeFile(path.join(output,'voice-ui.json'),JSON.stringify({passed:true,checks,errors,voiceTransport:'controlled fixture; native engine tested separately',requests},null,2));console.log(JSON.stringify({passed:checks.length,failed:0,evidence:output}));
}catch(error){await shot('failure');throw error;}finally{try{await Promise.race([cdp('Browser.close'),sleep(2000)]);}catch{}ws.close();if(chrome.exitCode===null)chrome.kill();fixture.stdin.write(JSON.stringify({action:'stop'})+'\n');fixture.stdin.end();await new Promise(resolve=>{if(fixture.exitCode!==null)resolve();else fixture.once('exit',resolve);});}
