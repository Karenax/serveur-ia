// Exercises the real local administration API through the rendered console.
// A child fixture owns a TemporaryDirectory and cannot see legacy processes.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {spawn} from 'node:child_process';
import readline from 'node:readline';
import {fileURLToPath} from 'node:url';

const tests=path.dirname(fileURLToPath(import.meta.url)),repo=path.resolve(tests,'../../..');
const output=path.resolve(process.argv[2]||path.join(repo,'preuves/conversation-windows-20261011/browser'));
await fs.mkdir(output,{recursive:true});
const downloadPath=path.join(output,'downloads-'+Date.now());
const python=path.join(repo,'Strata-src/.venv/Scripts/python.exe'),secret='Browser isolated recovery phrase 2026';
const fixture=spawn(python,['-u',path.join(tests,'conversation_fixture.py')],{cwd:repo,windowsHide:true,stdio:['pipe','pipe','pipe']});
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
async function evaluate(expression){const r=await cdp('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true,userGesture:true});if(r.exceptionDetails)throw new Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;}
async function until(expression,label){for(let i=0;i<200;i++){if(await evaluate(expression))return;await sleep(100);}throw new Error('Timeout : '+label);}
async function click(selector){await evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});if(!e||e.disabled)throw new Error('Commande absente ou désactivée');e.click();})()`);}
async function fill(selector,value){await evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});if(!e)throw new Error('Champ absent');e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('input',{bubbles:true}));})()`);}
async function submit(selector){await evaluate(`document.querySelector(${JSON.stringify(selector)}).requestSubmit()`);}
async function shot(name){const r=await cdp('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});await fs.writeFile(path.join(output,name+'.png'),Buffer.from(r.data,'base64'));}
async function check(name,work){await work();checks.push({name,passed:true});}

try{
 await cdp('Runtime.enable');await cdp('Page.enable');await cdp('Network.enable');
 await cdp('Page.addScriptToEvaluateOnNewDocument',{source:`
   window.fakeConversation={phase:'idle',installed:true,session:'',partial:'',turns:[],speech_id:0};window.conversationCalls=[];
   const originalFetch=window.fetch;
   window.fetch=async function(url,options){if(String(url)!=='/client/conversation')return originalFetch.apply(this,arguments);
     const value=options?.body?JSON.parse(options.body):null;
     if(value){conversationCalls.push(value);if(value.action==='start')fakeConversation={...fakeConversation,phase:'listening',session:'qa-conversation',turns:[],speech_id:0};if(value.action==='stop')fakeConversation={...fakeConversation,phase:'stopped',turns:[]};if(value.action==='ack')fakeConversation.turns=fakeConversation.turns.filter(t=>t.id>value.turn);}
     return new Response(JSON.stringify(fakeConversation),{status:200,headers:{'Content-Type':'application/json'}});
   }`});
 await cdp('Page.navigate',{url:instance.url+'/chat'});
 await until(`typeof historyReady!=='undefined'&&historyReady&&connected&&!conversationLocked()&&document.getElementById('conversation-start')&&!document.getElementById('conversation-start').disabled`,'Composer ready');
 await check('Un brouillon empêche le démarrage sans perdre son texte',async()=>{await fill('#prompt','Brouillon à garder');await click('#conversation-start');await sleep(300);assert.equal(await evaluate(`window.conversationBusy`),false);assert.equal(await evaluate(`document.getElementById('prompt').value`),'Brouillon à garder');await fill('#prompt','');});
 await check('Le mode garde le projet sélectionné pour le chat',async()=>{await until(`document.getElementById('ws-chat-project')?.options.length>1`,'Project choices');await evaluate(`document.getElementById('ws-chat-project').value=${JSON.stringify(instance.project)};document.getElementById('ws-chat-project').dispatchEvent(new Event('change'))`);await until(`wsCurrent()?.project_id===${JSON.stringify(instance.project)}`,'Project selected');});
 await check('La session ferme les changements de conversation et la dictée',async()=>{await until(`!document.getElementById('conversation-start').disabled&&!conversationActionPending&&!historySyncPending`,'Project change completed');await click('#conversation-start');await until(`window.conversationBusy`,'Conversation active');assert(await evaluate(`document.getElementById('new').disabled&&document.getElementById('voice-start').disabled&&document.getElementById('prompt').readOnly`));await shot('01-ecoute');});
 await check('Un tour final part automatiquement par le chat existant',async()=>{await evaluate(`fakeConversation.partial='Quelle est la livraison ?';fakeConversation.speech_id=1;fakeConversation.turns=[{id:1,text:'Quelle est la livraison du projet Orion ?'}]`);await until(`messages.some(m=>m.role==='user'&&m.content.includes('Orion'))&&busy`,'Automatic chat');assert.equal(await evaluate(`conversationCalls.filter(c=>c.action==='ack'&&c.turn===1).length`),1);});
 await check('La réponse commence à parler avant la fin du LLM',async()=>{await until(`busy&&document.getElementById('conversation-status').textContent.includes('Fred répond')`,'Progressive server speech');assert(requests.some(r=>r.path==='/v1/voice/speech'&&r.status===200));await shot('02-reponse-vocale');});
 await check('Reprendre la parole annule audio et génération',async()=>{await evaluate(`fakeConversation.speech_id=2;fakeConversation.partial='Non, attends';`);await until(`!busy`,'Generation interrupted');assert(await evaluate(`messages.some(m=>m.role==='assistant'&&m.interrupted)`));assert(requests.some(r=>r.path==='/v1/cancel'));await shot('03-interruption');});
 await check('Raccrocher ferme la session et rend le clavier',async()=>{await click('#conversation-start');await until(`!window.conversationBusy&&!document.getElementById('prompt').readOnly`,'Hung up');assert.equal(await evaluate(`fakeConversation.phase`),'stopped');});
 await check('Une erreur microphone ferme le mode conversation',async()=>{await until(`!document.getElementById('conversation-start').disabled`,'Conversation ready after hangup');await click('#conversation-start');await until(`window.conversationBusy`,'Restart');await evaluate(`fakeConversation.phase='error';fakeConversation.message='Microphone interrompu'`);await until(`!window.conversationBusy`,'Mic error');assert.equal(await evaluate(`document.getElementById('prompt').readOnly`),false);});
 await check('La console affiche le service vocal séparé',async()=>{await cdp('Page.navigate',{url:instance.admin_url});await until(`document.getElementById('voice-service-state')?.textContent.includes('prête')`,'Voice admin');await evaluate(`document.querySelector('[data-tab="exploitation"]').click()`);});
 await check('Désactiver puis réactiver charge et arrête la vraie voix CPU',async()=>{await click('#voice-service-stop');await until(`document.getElementById('voice-service-state').textContent.includes('désactivée')&&!document.getElementById('voice-service-start').disabled`,'Voice disabled');await click('#voice-service-start');await until(`document.getElementById('voice-service-state').textContent.includes('prête')&&!document.getElementById('voice-service-stop').disabled`,'Voice restarted');await evaluate(`document.getElementById('voice-service').scrollIntoView({block:'center'})`);await shot('04-console-voix');});
 assert.deepEqual(errors,[]);await fs.writeFile(path.join(output,'conversation-ui.json'),JSON.stringify({passed:true,checks,errors,requests,transport:'real WireGuard UDP + real Pocket TTS CPU; controlled local ASR and LLM'},null,2));console.log(JSON.stringify({passed:checks.length,evidence:output}));
}catch(error){await shot('failure');throw error;}finally{try{await Promise.race([cdp('Browser.close'),sleep(2000)]);}catch{}ws.close();if(chrome.exitCode===null)chrome.kill();fixture.stdin.write(JSON.stringify({action:'stop'})+'\n');fixture.stdin.end();await new Promise(resolve=>{if(fixture.exitCode!==null)resolve();else fixture.once('exit',resolve);});}
