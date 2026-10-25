/* Syntax and optional browser checks for the generated, shared Android UI. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const http=require('node:http');
const root=path.resolve(__dirname,'..');
const source=fs.readFileSync(path.join(root,'app/src/main/assets/android-chat.html'),'utf8');
const config={key:'android-ui-test-local-key',model:'Kiara-test',version:'Android-test',storage:'ui-test',platform:'android'};
const html=source.replace('__CONFIG__',JSON.stringify(config)).replaceAll('__NONCE__','android-ui-test');
const scripts=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(match=>match[1]);
assert.equal(scripts.length,12,'All shared scripts and the Android layer must be assembled');
scripts.forEach((script,index)=>new vm.Script(script,{filename:'android-inline-'+index+'.js'}));
assert(!source.includes('__UI_CSS__'));
assert(!source.includes("'/client/update/apply"));
assert(!source.includes("'/client/integrations"));
assert(!source.includes('EXE'));
console.log('Android inline JavaScript syntax verified ('+scripts.length+' scripts)');
if(!process.argv.includes('--browser'))process.exit(0);

async function browserCheck(){
  const playwrightPath=process.env.PLAYWRIGHT_MODULE||'playwright';
  const {chromium}=require(playwrightPath);
  const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH||'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const state={profile:false,required:true,transport:'https',history:null,revision:'1',draft:null,preferences:{},requests:[],pendingModels:1,jsonFallback:false,chatMode:'normal',runs:new Map(),pendingAgent:null,update:{phase:'current',message:'À jour.',available:false}};
  const project={id:'project-1',title:'Projet mobile',instructions:'',archived:false,revision:1,documents:[],memories:[],conversations:[]};
  const respond=(res,value,status=200)=>{res.writeHead(status,{'Content-Type':'application/json; charset=utf-8'});res.end(JSON.stringify(value));};
  const server=http.createServer(async(req,res)=>{
    let raw='';for await(const chunk of req)raw+=chunk;let body={};try{body=JSON.parse(raw||'{}');}catch{}
    if(req.url==='/'){res.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});return res.end(html);}
    if(req.url==='/__bridge/import'){state.profile=true;state.required=true;return respond(res,{ok:true});}
    if(req.url==='/__bridge/mode'){state.transport=body.mode;state.required=false;return respond(res,{ok:true});}
    state.requests.push({path:req.url,method:req.method,body,request_id:req.headers['x-qwen-request']});
    if(req.headers.authorization!=='Bearer '+config.key)return respond(res,{error:{message:'Clé locale manquante'}},401);
    if(req.url==='/client/state')return respond(res,{version:'Android-test',profile_required:!state.profile,profile:{name:'Profil mobile de test'},preferences:state.preferences,update:state.update,history:{message:'Historique enregistré',needs_merge:false},endpoint:'https://example.test',connection:{transport:state.transport,endpoint:'https://example.test',connected:state.profile&&!state.required,connection_required:state.required,checked_at:Date.now()/1000}});
    if(req.url==='/client/update/check'){state.update={phase:'ready',available:true,version:'1.0.6',message:'Mise à jour prête.'};return respond(res,state.update);}
    if(req.url==='/client/history'&&req.method==='GET')return respond(res,{history:state.history,revision:state.revision});
    if(req.url==='/client/history/sync'){state.history=state.history||body.initial;return respond(res,{history:state.history,revision:state.revision,message:'Historique synchronisé',merged:false});}
    if(req.url==='/client/history'){state.history=body.history;state.revision=String(Number(state.revision)+1);return respond(res,{saved:true,revision:state.revision,message:'Historique enregistré'});}
    if(req.url==='/client/preferences'){state.preferences=body;return respond(res,{saved:true});}
    if(req.url==='/client/draft'){if(req.method==='POST')state.draft=body.draft;return respond(res,{draft:state.draft});}
    if(req.url==='/v1/models'){
      if(state.pendingModels>0){state.pendingModels--;return respond(res,{error:{code:'connecting',message:'Connexion au serveur IA…'}},503);}
      return respond(res,{data:[{id:'Kiara-test',capabilities:{images:false,files:['txt','md','pdf','docx'],thinking:true,reasoning_efforts:['none','low','medium','high']}}]});
    }
    if(req.url==='/v1/status')return respond(res,{protocol:4,version:'test'});
    if(req.url==='/v1/agent/state')return respond(res,{enabled:true,available:true,status:'ready',runs:[...state.runs.values()]});
    if(req.url==='/v1/agent/action'){
      if(body.action==='reconcile')return respond(res,state.runs.get(body.request_id)||{request_id:body.request_id,conversation_id:body.conversation_id,status:'unknown',text:''});
      if(body.action==='approval'){
        const pending=state.pendingAgent;if(!pending||pending.id!==body.request_id||pending.conversation!==body.conversation_id)return respond(res,{error:{message:'Action expirée'}},409);
        assert.notEqual(body.request_id,pending.turn);assert.equal(req.headers['x-qwen-request'],pending.turn);
        state.runs.set(pending.turn,{request_id:pending.turn,conversation_id:pending.conversation,status:'running',text:''});respond(res,{accepted:true});const text=body.decision==='once'?'Action autorisée et résultat vérifié.':'Action refusée, aucun changement.';if(state.chatMode==='approval-disconnected')setTimeout(()=>pending.finish(text),1800);else pending.finish(text);state.pendingAgent=null;return;
      }
    }
    if(req.url==='/v1/workspace')return respond(res,{projects:[project],jobs:[]});
    if(req.url==='/v1/context')return respond(res,{tokens:15,capacity:4096,estimated:false});
    if(req.url==='/v1/chat/completions'){
      if(body.text_transform){assert.deepEqual(body,{text_transform:{mode:'correct',text:'Je veut vérifier la réponse JSON complète.'},stream:true});assert(state.jsonFallback);return respond(res,{choices:[{message:{role:'assistant',content:'Le correcteur accepte une réponse JSON.'},finish_reason:'stop'}]});}
      assert.equal(body.turn_id,req.headers['x-qwen-request']);assert.equal(typeof body.history_revision,'string');assert(body.conversation_id);
      if(state.jsonFallback)return respond(res,{choices:[{message:{role:'assistant',content:'Le correcteur accepte une réponse JSON.'},finish_reason:'stop'}]});
      res.writeHead(200,{'Content-Type':'text/event-stream; charset=utf-8','Cache-Control':'no-cache'});
      const finish=text=>{const final={request_id:body.turn_id,conversation_id:body.conversation_id,status:'completed',text,reasoning_content:'',sources:[]};state.runs.set(body.turn_id,final);if(res.destroyed||res.writableEnded)return;res.write('data: '+JSON.stringify({choices:[{delta:{content:text},finish_reason:'stop'}]})+'\n\n');res.write('data: '+JSON.stringify({hermes_run:final})+'\n\n');res.end('data: [DONE]\n\n');};
      res.write('data: '+JSON.stringify({hermes_status:{phase:'tool',message:'Recherche dans vos documents'}})+'\n\n');
      if(state.chatMode.startsWith('approval')){
        const approval={request_id:'receipt_'+body.turn_id,description:'Créer le document « Bilan » <img src=x onerror=alert(1)>',expires_epoch:Date.now()/1000+60};state.pendingAgent={id:approval.request_id,turn:body.turn_id,conversation:body.conversation_id,finish};state.runs.set(body.turn_id,{request_id:body.turn_id,conversation_id:body.conversation_id,status:'waiting_for_approval',text:'',approval});res.write('data: '+JSON.stringify({hermes_approval:approval})+'\n\n');setTimeout(()=>{if(res.destroyed)return;res.write('data: '+JSON.stringify({hermes_status:{phase:'approval',message:'Votre accord est toujours attendu.'}})+'\n\n');if(state.chatMode==='approval-disconnected')res.end();},50);return;
      }
      if(state.chatMode==='interrupted'){
        state.runs.set(body.turn_id,{request_id:body.turn_id,conversation_id:body.conversation_id,status:'completed',text:'Réponse finale retrouvée sur le serveur.',reasoning_content:'',sources:[]});res.write('data: '+JSON.stringify({choices:[{delta:{content:'Réponse partielle'}}]})+'\n\n');res.end();return;
      }
      if(state.chatMode==='waiting'){
        state.pendingAgent={id:body.turn_id,conversation:body.conversation_id,stop(){state.runs.set(body.turn_id,{request_id:body.turn_id,conversation_id:body.conversation_id,status:'cancelled',text:''});res.write('data: '+JSON.stringify({hermes_run:{request_id:body.turn_id,status:'cancelled'}})+'\n\n');res.end('data: [DONE]\n\n');}};return;
      }
      res.write('data: '+JSON.stringify({choices:[{delta:{content:'Bonjour depuis '}}]})+'\n\n');
      setTimeout(()=>{state.runs.set(body.turn_id,{request_id:body.turn_id,conversation_id:body.conversation_id,status:'completed',text:'Bonjour depuis **Android**.',reasoning_content:'',sources:[]});res.write('data: '+JSON.stringify({choices:[{delta:{content:'**Android**.'},finish_reason:'stop'}]})+'\n\n');res.end('data: [DONE]\n\n');},80);return;
    }
    if(req.url==='/v1/workspace/action'){
      if(body.action==='attachment_extract')return respond(res,{text:Buffer.from(body.data,'base64').toString('utf8')});
      if(body.action==='project_create')return respond(res,{id:project.id});
      return respond(res,{});
    }
    if(req.url==='/v1/cancel'){state.pendingAgent?.stop?.();state.pendingAgent=null;return respond(res,{cancelled:true});}
    return respond(res,{error:{message:'Unexpected route '+req.url}},404);
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const origin='http://127.0.0.1:'+server.address().port;
  try{
    const page=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
    const errors=[];page.on('pageerror',error=>errors.push(error.message));
    await page.addInitScript(()=>{
      window.__androidCalls=[];
      function nativeRequest(route,value){const request=new XMLHttpRequest();request.open('POST',route,false);request.setRequestHeader('Content-Type','application/json');request.send(JSON.stringify(value||{}));return request.responseText;}
      window.AndroidClient={
        installUpdate(){window.__androidCalls.push({method:'installUpdate'});},
        importProfile(){window.__androidCalls.push({method:'importProfile'});nativeRequest('/__bridge/import');location.reload();},
        setConnectionMode(mode){window.__androidCalls.push({method:'setConnectionMode',mode});return nativeRequest('/__bridge/mode',{mode});},
        openSettings(){window.__androidCalls.push({method:'openSettings'});},
        notificationReady(){window.__androidCalls.push({method:'notificationReady'});},
        exportFile(name,mime,data){window.__androidCalls.push({method:'exportFile',name,mime,data});return JSON.stringify({ok:true});},
        copyText(text){window.__androidCalls.push({method:'copyText',text});return JSON.stringify({ok:true});},
        openUrl(url){window.__androidCalls.push({method:'openUrl',url});}
      };
    });
    await page.goto(origin);
    await page.waitForSelector('#android-onboarding[open]');
    assert.equal(state.requests.some(request=>request.path==='/v1/models'),false,'No remote API before profile import');
    await page.click('#android-import-profile');
    await page.waitForSelector('#connection-choice[open]');
    assert.equal(state.requests.some(request=>request.path==='/v1/models'),false,'No remote API before explicit transport choice');
    const initialCatalogue=page.waitForResponse(response=>response.url().endsWith('/v1/models')&&response.status()===503);
    await page.click('#choose-https');await initialCatalogue;
    await page.waitForFunction(()=>!modelsPending);
    assert.equal(await page.isVisible('#error'),false,'A native connecting response is progress, not a red error');
    await page.evaluate(()=>models());
    await page.waitForSelector('#send:not([disabled])');
    assert.equal(await page.isVisible('#error'),false,'Successful connection must not leave a startup error behind');
    await page.evaluate(()=>error({message:'Historique non enregistré. Réessayez.',code:'history_conflict'}));
    state.pendingModels=1;await page.evaluate(()=>models());
    assert.equal(await page.textContent('#error'),'Historique non enregistré. Réessayez.','Connecting must preserve unrelated save errors');
    await page.evaluate(()=>models());
    assert.equal(await page.textContent('#error'),'Historique non enregistré. Réessayez.','Recovery must preserve unrelated save errors');
    await page.evaluate(()=>error({message:'Accès révoqué.',code:'access_revoked'}));
    assert.equal(await page.isVisible('#error'),true,'Real access errors stay visible');
    await page.evaluate(()=>models());
    assert.equal(await page.isVisible('#error'),false,'A confirmed reconnection clears its own network error');
    assert.equal(state.transport,'https');
    await page.setInputFiles('#chat-file-input',{name:'note-mobile.txt',mimeType:'text/plain',buffer:Buffer.from('Texte joint depuis le sélecteur Android.')});
    await page.waitForSelector('#chat-attachments .attachment-chip');
    assert((await page.textContent('#chat-attachments')).includes('note-mobile.txt'));
    await page.fill('#prompt','Message sur deux lignes');
    await page.press('#prompt','End');await page.press('#prompt','Enter');
    assert((await page.inputValue('#prompt')).includes('\n'),'Phone Enter must create a newline');
    await page.click('#send');
    await page.waitForSelector('.message.assistant .content strong');
    assert.equal((await page.textContent('.message.assistant .content')).trim(),'Bonjour depuis Android.');
    await page.waitForSelector('#send:not([disabled])');
    await page.click('.message.assistant .message-copy');
    assert((await page.evaluate(()=>window.__androidCalls)).some(call=>call.method==='copyText'&&call.text.includes('Android')));
    await page.evaluate(()=>showView('access'));
    assert.equal(await page.isVisible('#android-update-banner'),false,'No installation banner while up to date');
    await page.click('#android-update-check');
    await page.waitForSelector('#android-update-banner:not([hidden])');
    await page.click('#android-update-install');
    await page.waitForFunction(()=>window.__androidCalls.some(call=>call.method==='installUpdate'));
    const blockedInstall=await page.evaluate(async()=>{historyBlocked=true;androidUpdateState({phase:'ready',available:true,version:'1.0.6'});const disabled=document.getElementById('android-update-install').disabled;historyBlocked=false;androidUpdateState({phase:'ready',available:true,version:'1.0.6'});return disabled;});
    assert(blockedInstall,'Blocked history must disable installation');
    assert.equal(await page.locator('#retry').count(),0,'The removed response retry button must stay absent');
    await page.click('#export-conversations');
    await page.waitForFunction(()=>window.__androidCalls.some(call=>call.method==='exportFile'));
    const exported=await page.evaluate(()=>window.__androidCalls.find(call=>call.method==='exportFile'));
    assert.equal(exported.name,'conversations-kiara.json');assert.equal(exported.mime,'application/json');
    assert.equal(JSON.parse(Buffer.from(exported.data,'base64')).conversations[0].messages.length,2);
    assert.equal(JSON.parse(Buffer.from(exported.data,'base64')).conversations[0].messages[0].attachments[0].name,'note-mobile.txt');
    const firstChat=state.requests.find(request=>request.path==='/v1/chat/completions');const exportedMessages=JSON.parse(Buffer.from(exported.data,'base64')).conversations[0].messages;
    assert.equal(firstChat.body.turn_id,firstChat.request_id);assert.equal(exportedMessages[0].turn_id,firstChat.body.turn_id);assert.equal(exportedMessages[1].turn_id,firstChat.body.turn_id);
    const imported={version:1,conversations:[{title:'Discussion importée',messages:[{role:'user',content:'Bonjour depuis un autre appareil.'}]}]};
    await page.setInputFiles('#import-file',{name:'historique.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(imported))});
    await page.waitForFunction(()=>[...document.querySelectorAll('#conversation-list .conversation-item')].some(button=>button.textContent.includes('Discussion importée')));
    await page.evaluate(()=>showView('projects'));
    await page.click('#ws-project-list button');
    await page.waitForSelector('#ws-project-detail:not([hidden])');
    await page.evaluate(()=>showView('corrector'));
    assert(await page.isVisible('#corrector-text'));
    state.jsonFallback=true;
    await page.fill('#corrector-text','Je veut vérifier la réponse JSON complète.');
    await page.click('#corrector-correct');
    await page.waitForFunction(()=>document.getElementById('corrector-status').textContent.includes('terminé'));
    assert((await page.textContent('#corrector-result')).includes('Le correcteur accepte une réponse JSON.'));
    state.jsonFallback=false;
    await page.evaluate(()=>showView('chat'));state.chatMode='approval';await page.click('#ui-sidebar-toggle');await page.click('#new');await page.fill('#prompt','Prépare un bilan.');await page.click('#send');await page.waitForSelector('#agent-approval:not([hidden])');
    await page.waitForFunction(()=>document.getElementById('queue-state').textContent.includes('toujours'));assert(await page.isVisible('#agent-approval'),'An approval heartbeat must preserve its opaque receipt');
    assert((await page.textContent('#agent-approval')).includes('<img src=x onerror=alert(1)>'),'Approval effects must be rendered as plain text');assert.equal(await page.locator('#agent-approval img').count(),0);
    assert.equal(await page.textContent('.message.assistant .content'),'','Tool progress and approval must stay out of the answer');
    await page.click('#agent-approve');await page.waitForFunction(()=>document.querySelector('.message.assistant .content')?.textContent.includes('résultat vérifié'));await page.waitForSelector('#send:not([disabled])');
    assert(state.requests.some(request=>request.path==='/v1/agent/action'&&request.body.decision==='once'));
    const approvalChat=state.requests.filter(request=>request.path==='/v1/chat/completions').at(-1);await page.fill('#prompt','Continue cette conversation.');await page.click('#send');await page.waitForFunction(()=>document.getElementById('queue-state').textContent.includes('toujours'));assert(await page.isVisible('#agent-approval'));await page.click('#agent-deny');await page.waitForFunction(()=>document.querySelectorAll('.message.assistant .content')[1]?.textContent.includes('aucun changement'));await page.waitForSelector('#send:not([disabled])');
    const continuation=state.requests.filter(request=>request.path==='/v1/chat/completions').at(-1);assert.equal(continuation.body.conversation_id,approvalChat.body.conversation_id);assert.notEqual(continuation.body.turn_id,approvalChat.body.turn_id);assert(state.requests.some(request=>request.body.decision==='deny'));
    state.chatMode='approval-disconnected';await page.click('#ui-sidebar-toggle');await page.click('#new');await page.evaluate(()=>{library.find(c=>c.id===currentId).project_id='project-1';});await page.fill('#prompt','Une action du projet à reprendre.');await page.click('#send');await page.waitForFunction(()=>replyProgress.agentStatus==='waiting_for_approval');await page.evaluate(()=>flushHistory());const waitingTurn=state.pendingAgent.turn,waitingConversation=state.pendingAgent.conversation,chatCount=state.requests.filter(request=>request.path==='/v1/chat/completions').length;
    await page.reload();await page.waitForSelector('#agent-approval:not([hidden])');assert.equal(await page.evaluate(()=>requestId),waitingTurn);assert.equal(await page.evaluate(()=>currentId),waitingConversation);assert.equal(await page.evaluate(()=>library.find(c=>c.id===currentId).project_id),'project-1');assert.equal(state.requests.filter(request=>request.path==='/v1/chat/completions').length,chatCount,'Reconnect must preserve the original project run');await page.click('#agent-deny');await page.waitForSelector('#send:not([disabled])');assert.equal(await page.locator('.message.assistant').count(),1);assert((await page.textContent('.message.assistant .content')).includes('aucun changement'));
    state.chatMode='interrupted';await page.click('#ui-sidebar-toggle');await page.click('#new');await page.fill('#prompt','Retrouve le résultat après une coupure.');await page.click('#send');await page.waitForFunction(()=>document.querySelector('.message.assistant .content')?.textContent.trim()==='Réponse finale retrouvée sur le serveur.');await page.waitForSelector('#send:not([disabled])');
    assert.equal(await page.evaluate(()=>messages.at(-1).interrupted),undefined,'An authoritative final result must remove the interrupted flag');assert(state.requests.some(request=>request.path==='/v1/agent/action'&&request.body.action==='reconcile'));
    await page.reload();await page.waitForSelector('#send:not([disabled])');assert.equal(await page.locator('.message.assistant').count(),1,'Reconnecting must retain one final answer');assert.equal((await page.textContent('.message.assistant .content')).trim(),'Réponse finale retrouvée sur le serveur.');
    state.chatMode='waiting';await page.click('#ui-sidebar-toggle');await page.click('#new');await page.fill('#prompt','Une demande à arrêter.');await page.click('#send');await page.waitForFunction(()=>document.getElementById('queue-state').textContent.includes('Recherche'));await page.click('#cancel');await page.waitForSelector('#send:not([disabled])');assert(state.requests.some(request=>request.path==='/v1/cancel'));assert.equal(await page.locator('#agent-approval:not([hidden])').count(),0);state.chatMode='normal';
    const blockedFlush=await page.evaluate(async()=>{const previous=historyBlocked;try{historyBlocked=true;return await window.androidFlush();}finally{historyBlocked=previous;error('');buttons();}});
    assert.equal(blockedFlush,false,'Blocked history must prevent the native close from accepting a false save confirmation');
    assert.equal(await page.evaluate(()=>window.androidFlush()),true,'Healthy history should still flush');
    assert.equal(await page.locator('[data-view-button="updates"]').count(),0);
    assert.equal(await page.locator('[data-view-button="api"]').count(),1,'Android keeps its local API settings');
    assert.equal(await page.title(),'Accès serveur Kiara');
    assert.equal(await page.textContent('.brand .logo'),'K');
    const phoneOverflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);
    assert(!phoneOverflow,'Phone must not scroll horizontally');
    await page.screenshot({path:path.join(root,'mobile-ui-phone-test.png')});
    await page.evaluate(()=>showView('chat'));
    await page.focus('#prompt');
    await page.setViewportSize({width:390,height:500});
    await page.waitForFunction(()=>document.body.classList.contains('android-keyboard'));
    assert(await page.evaluate(()=>['prompt','send'].every(id=>{const box=document.getElementById(id).getBoundingClientRect();return box.top>=0&&box.bottom<=innerHeight+1;})),'Composer input and send must fit the viewport after native keyboard shrinking');
    await page.setViewportSize({width:1280,height:800});
    await page.evaluate(()=>showView('chat'));
    await page.click('#ui-sidebar-toggle');
    await page.waitForTimeout(100);
    await page.screenshot({path:path.join(root,'mobile-ui-tablet-test.png')});
    await page.evaluate(()=>showView('connection'));
    await page.selectOption('#connection-mode','wireguard');
    await page.click('#endpoint-form button[type=submit]');
    await page.waitForFunction(()=>document.getElementById('connection-transfer-status').textContent.includes('WireGuard'));
    assert.equal(state.transport,'wireguard');
    assert.deepEqual(errors,[],'No runtime JS errors');
    console.log('Android browser checks passed: onboarding, explicit HTTPS/WireGuard choice, streamed chat, durable Hermes turn IDs, approvals once/deny, plain-text effects, conversation continuity, cut-stream reconciliation/reload, confirmed cancellation, attachments, multiline keyboard, clipboard, history import/export, projects, corrector JSON fallback, blocked history close, resized keyboard composer, phone/tablet layout');
    await page.close();
  }finally{await browser.close();await new Promise(resolve=>server.close(resolve));}
}
browserCheck().catch(error=>{console.error(error);process.exitCode=1;});
