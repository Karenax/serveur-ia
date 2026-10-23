/* Real shared UI with a local deterministic Qwen transport; no private model. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const root=__dirname,read=name=>fs.readFileSync(path.join(root,name),'utf8');
const script=name=>'<script nonce="qa">'+read(name).replaceAll('</script','<\\/script')+'</script>';
const windows=read('chat.html').replace('__UI_CSS__',read('ui.css')).replace('</head>',()=>script('vendor/markdown-it.min.js')+script('markdown.js')+'</head>').replace('</body>',()=>read('workspace.html')+['ui.js','attachments.js','corrector.js','selection.js','thinking.js','voice.js','conversation.js'].map(script).join('')+'</body>');
const android=fs.readFileSync(path.join(root,'../client-android/app/src/main/assets/android-chat.html'),'utf8');
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function until(work){for(let i=0;i<200;i++){if(work())return;await sleep(25);}throw new Error('Local fixture request did not arrive');}
const results=[];

async function check(browser,platform){
  const config={key:'direct-corrector-test',model:'Qwen-test',version:platform+'-test',storage:'direct-corrector-'+platform,...(platform==='android'?{platform:'android'}:{})};
  const html=(platform==='android'?android:windows).replace('__CONFIG__',JSON.stringify(config)).replaceAll('__NONCE__','qa');
  const chatId='11111111-1111-4111-8111-111111111111',legacyId='22222222-2222-4222-8222-222222222222',archivedId='33333333-3333-4333-8333-333333333333',projectId='44444444444444448444444444444444';
  const state={history:{currentId:chatId,conversations:[
    {id:chatId,title:'Discussion habituelle',project_id:projectId,messages:[{role:'user',content:'Une question habituelle.'},{role:'assistant',content:'Réponse habituelle.'}]},
    {id:legacyId,title:'Correcteur · Reformuler professionnel · Ancien texte',project_id:projectId,messages:[{role:'user',content:'Reformuler professionnel :\n\nAncien texte à préserver.'},{role:'assistant',content:'Ancien résultat conservé.'}]},
    {id:archivedId,title:'Correcteur · Corriger · Texte archivé',archived:true,messages:[{role:'user',content:'Corriger :\n\nTexte archivé.'},{role:'assistant',content:'Résultat archivé.'}]}
  ]},revision:'1',preferences:{},calls:[],pending:null,format:'sse',fault:false};
  const json=(res,value)=>{res.writeHead(200,{'Content-Type':'application/json; charset=utf-8'});res.end(JSON.stringify(value));};
  const event=(res,value)=>res.write('data: '+JSON.stringify(value)+'\n\n');
  const server=http.createServer(async(req,res)=>{
    let raw='';for await(const chunk of req)raw+=chunk;const body=JSON.parse(raw||'{}');
    if(req.url==='/'){res.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});return res.end(html);}
    if(req.headers.authorization!=='Bearer '+config.key){res.writeHead(401);res.end();return;}
    state.calls.push({path:req.url,body,id:req.headers['x-qwen-request']});
    if(req.url==='/client/state')return json(res,{version:config.version,profile_required:false,profile:{name:'Test'},preferences:state.preferences,update:{available:false,busy:false,phase:'current',message:'À jour'},endpoint:'https://example.test',internet_endpoint:'example.test:51820',local_api:'http://127.0.0.1/v1',key:config.key,history:{message:'Enregistré',needs_merge:false},connection:{connected:true,connection_required:false,model:config.model,transport:'https',endpoint:'https://example.test',checked_at:Date.now()/1000}});
    if(req.url==='/client/history'&&req.method==='GET')return json(res,{history:state.history,revision:state.revision});
    if(req.url==='/client/history/sync'){state.history=state.history||body.initial;return json(res,{history:state.history,revision:state.revision,message:'Synchronisé'});}
    if(req.url==='/client/history'){state.history=body.history;state.revision=String(Number(state.revision)+1);return json(res,{saved:true,revision:state.revision});}
    if(req.url==='/client/history/flush')return json(res,{saved:true});
    if(req.url==='/client/preferences'){state.preferences=body;return json(res,{saved:true});}
    if(req.url==='/client/draft')return json(res,{draft:null});
    if(req.url==='/client/integrations')return json(res,{apps:[]});
    if(req.url==='/client/voice'||req.url==='/client/conversation')return json(res,{phase:'idle',installed:false});
    if(req.url==='/v1/models')return json(res,{data:[{id:config.model,capabilities:{thinking:true,reasoning_efforts:['none','low','medium','high']}}]});
    if(req.url==='/v1/status')return json(res,{protocol:3,agent_protocol:4});
    if(req.url==='/v1/workspace')return json(res,{projects:[{id:projectId,title:'Projet de test',instructions:'',documents:[],memories:[],conversations:state.history.conversations.filter(c=>c.project_id===projectId).map(c=>({id:c.id.replaceAll('-',''),title:c.title,archived:!!c.archived}))}],jobs:[]});
    if(req.url==='/v1/notifications')return json(res,{items:[],unread:0});
    if(req.url==='/v1/context')return json(res,{tokens:15,capacity:4096});
    if(req.url==='/v1/agent/action')return json(res,{request_id:body.request_id,conversation_id:body.conversation_id,status:'unknown'});
    if(req.url==='/v1/cancel'){assert.deepEqual(body,{text_transform:true});assert.equal(req.headers['x-qwen-request'],state.pending.id);return json(res,{cancelled:true});}
    if(req.url==='/v1/chat/completions'){
      if(!body.text_transform){assert(body.conversation_id&&body.turn_id);assert.equal(body.turn_id,req.headers['x-qwen-request']);res.writeHead(200,{'Content-Type':'text/event-stream; charset=utf-8'});event(res,{hermes_answer:{text:'Réponse Hermes ordinaire.',reasoning_content:'',final:true}});event(res,{hermes_run:{request_id:body.turn_id,conversation_id:body.conversation_id,status:'completed'}});return res.end('data: [DONE]\n\n');}
      assert.deepEqual(Object.keys(body).sort(),['stream','text_transform']);assert.equal(body.stream,true);assert.match(req.headers['x-qwen-request'],/^[a-f0-9]{32}$/);assert(['correct','professional','friendly'].includes(body.text_transform.mode));
      const saved=state.history.conversations.find(c=>c.id===state.history.currentId);assert(saved.messages[0].content.endsWith(body.text_transform.text),'Source must be saved before sending');assert.equal(saved.messages[0].turn_id,undefined);assert.equal(saved.messages[1].turn_id,undefined);
      if(state.format==='json')return json(res,{choices:[{message:{content:'Texte JSON corrigé entièrement.'},finish_reason:'stop'}]});
      res.writeHead(200,{'Content-Type':'text/event-stream; charset=utf-8'});event(res,{choices:[{delta:{content:'Texte corrigé'}}]});
      state.pending={id:req.headers['x-qwen-request'],res,finish(){event(res,{choices:[{delta:{content:' entièrement.'},finish_reason:'stop'}]});res.end('data: [DONE]\n\n');}};
      if(state.fault)res.end();return;
    }
    return json(res,{});
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const page=await browser.newPage({viewport:platform==='android'?{width:412,height:915}:{width:1440,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  if(platform==='android')await page.addInitScript(()=>{window.AndroidClient={notificationReady(){},copyText(){return '{"ok":true}';},openSettings(){},exportFile(){return '{"ok":true}';},installUpdate(){}};});
  const ready=()=>page.waitForFunction(()=>!busy&&!historySyncPending&&!historySaving);
  const sidebar=async()=>{if(await page.getAttribute('#ui-sidebar-toggle','aria-expanded')==='false')await page.click('#ui-sidebar-toggle');};
  const listIds=()=>page.locator('#conversation-list [data-conversation-id]').evaluateAll(nodes=>nodes.map(n=>n.dataset.conversationId));
  try{
    await page.goto('http://127.0.0.1:'+server.address().port);await page.waitForSelector('#send:not([disabled])');await ready();
    assert.deepEqual(await listIds(),[chatId],'Existing corrections must be absent from chat');
    await page.waitForSelector('#ws-sidebar-projects details',{state:'attached'});await page.evaluate(()=>{wsSidebarProjects.querySelector('details').open=true;ws.project=ws.data.projects[0].id;wsDrawProjectConversations();});
    assert.equal(await page.locator('#ws-sidebar-projects [data-conversation-id]').count(),1,'Project sidebar must exclude legacy corrections');assert.equal(await page.locator('#ws-conversations [data-conversation-id]').count(),1);
    await page.fill('#prompt','Brouillon de conversation à préserver.');await page.evaluate(()=>showView('corrector'));await sidebar();
    assert.deepEqual(await listIds(),[legacyId]);assert.equal(await page.isVisible('#ws-sidebar-projects'),false);assert.equal(await page.textContent('#new'),'Nouveau texte');
    const legacy=page.locator('#conversation-list [data-conversation-id="'+legacyId+'"]');await legacy.focus();await page.keyboard.press('Enter');
    assert.equal(await page.isVisible('[data-view="corrector"]'),true);assert.equal(await page.inputValue('#corrector-text'),'Ancien texte à préserver.');assert.equal((await page.textContent('#corrector-result')).trim(),'Ancien résultat conservé.');
    await sidebar();const evidence=path.join(root,'../maintenance/2026-10-23-listes-correcteur');fs.mkdirSync(evidence,{recursive:true});await page.screenshot({path:path.join(evidence,platform+'-correcteur.png'),animations:'disabled'});await page.evaluate(()=>uiCloseSidebar(false));
    await page.fill('#corrector-text','Brouillon de correction à préserver.');await page.evaluate(()=>showView('chat'));assert.equal(await page.inputValue('#prompt'),'Brouillon de conversation à préserver.');assert.deepEqual(await listIds(),[chatId]);
    await sidebar();await page.screenshot({path:path.join(evidence,platform+'-conversations.png'),animations:'disabled'});await page.evaluate(()=>uiCloseSidebar(false));
    await page.evaluate(()=>showView('corrector'));assert.equal(await page.inputValue('#corrector-text'),'Brouillon de correction à préserver.');await sidebar();
    await page.fill('#search-conversations','habituelle');assert.deepEqual(await listIds(),[],'Search must remain scoped');await page.evaluate(()=>showView('chat'));assert.equal(await page.inputValue('#search-conversations'),'');assert.deepEqual(await listIds(),[chatId]);
    await page.evaluate(()=>showView('corrector'));await sidebar();assert.equal(await page.inputValue('#search-conversations'),'habituelle');await page.fill('#search-conversations','');
    await page.selectOption('#conversation-filter','archived');assert.deepEqual(await listIds(),[archivedId]);await page.evaluate(()=>showView('chat'));assert.deepEqual(await listIds(),[chatId]);await page.evaluate(()=>showView('corrector'));await sidebar();assert.deepEqual(await listIds(),[archivedId]);await page.selectOption('#conversation-filter','active');
    const beforeNew=await page.evaluate(()=>library.length);await page.click('#new');assert.equal(await page.inputValue('#corrector-text'),'');assert.equal(await page.evaluate(()=>library.length),beforeNew,'New correction is saved only when run');assert.equal(await page.isVisible('[data-view="corrector"]'),true);
    await page.evaluate(()=>showView('chat'));await page.evaluate(()=>showView('corrector'));assert.equal(await page.inputValue('#corrector-text'),'','Returning must retain the new empty draft');
    for(const [button,mode] of [['corrector-correct','correct'],['corrector-pro','professional'],['corrector-friendly','friendly']]){
      const source='Je veut préserver mes informations.\n\nBudget : 4200 € — projet Orion.';const before=state.calls.length;await page.fill('#corrector-text','  '+source+'  ');await page.click('#'+button);await page.waitForFunction(()=>correctorAnswer.content==='Texte corrigé'&&document.getElementById('corrector-result').textContent.includes('Texte corrigé'));
      assert.equal(await page.evaluate(()=>correctorRunning),true,'A partial reply is visible before completion');assert.equal(await page.isVisible('#corrector-cancel'),true);assert((await page.textContent('#corrector-result')).includes('Texte corrigé'));
      const request=state.calls.slice(before).find(call=>call.path==='/v1/chat/completions');assert.deepEqual(request.body,{text_transform:{mode,text:source},stream:true});assert.equal(state.calls.slice(before,state.calls.indexOf(request)).filter(call=>call.path==='/client/history').length,1,'Only the new source/result save must precede Qwen');
      state.pending.finish();await ready();assert.equal(await page.evaluate(()=>correctorAnswer.content),'Texte corrigé entièrement.');assert.equal(state.history.conversations[0].messages[1].content,'Texte corrigé entièrement.');
    }
    if(platform==='android'){state.format='json';await page.fill('#corrector-text','Un résultat Android complet.');await page.click('#corrector-correct');await page.waitForFunction(()=>correctorAnswer.content==='Texte JSON corrigé entièrement.');await ready();state.format='sse';}
    await page.fill('#corrector-text','Une correction que je veux arrêter.');await page.click('#corrector-friendly');await page.waitForFunction(()=>correctorAnswer.content==='Texte corrigé');const cancelled=state.pending.id;await page.click('#corrector-cancel');await ready();assert((await page.textContent('#corrector-status')).includes('arrêtée'));assert.equal(await page.evaluate(()=>correctorAnswer.content),'Texte corrigé');assert.equal(state.history.conversations[0].messages[1].content,'Texte corrigé');assert.equal(state.calls.filter(call=>call.path==='/v1/cancel'&&call.id===cancelled).length,1);
    if(platform==='windows'){
      const prior=state.pending.id;await page.fill('#corrector-text','Une correction fermée avec la fenêtre.');await page.click('#corrector-pro');await until(()=>state.pending.id!==prior);await page.waitForFunction(()=>correctorRunning&&correctorAnswer.content==='Texte corrigé');const closeCode=/window\.evaluate_js\("((?:\\.|[^"])*)",callback=complete\)/.exec(read('client.py'))?.[1];assert(closeCode);const closeResult=await page.evaluate(closeCode);assert.equal(closeResult.saved,true);await ready();assert(state.calls.at(-1));assert.equal(state.calls.filter(call=>call.path==='/v1/cancel'&&call.id===state.pending.id).length,1);
    }
    const beforeFailure=state.calls.length;state.fault=true;await page.fill('#corrector-text','Une correction interrompue par le réseau.');await page.click('#corrector-correct');await until(()=>state.calls.slice(beforeFailure).some(call=>call.path==='/v1/chat/completions'));await page.waitForFunction(()=>!busy&&correctorAnswer.interrupted);await ready();assert.equal(await page.evaluate(()=>correctorAnswer.content),'Texte corrigé');assert((await page.textContent('#corrector-status')).includes('Connexion interrompue'));assert.equal(state.calls.slice(beforeFailure).filter(call=>call.path==='/v1/agent/action').length,0,'Direct failures must never reconcile Hermes');
    const count=state.history.conversations.filter(c=>c.title.startsWith('Correcteur ·')).length,failedId=state.history.currentId;await page.reload();await page.waitForSelector('#send:not([disabled])');await ready();await sleep(100);assert.equal(state.calls.slice(beforeFailure).filter(call=>call.path==='/v1/agent/action').length,0,'Reload must retain direct histories without Hermes recovery');assert.equal(state.history.conversations.filter(c=>c.title.startsWith('Correcteur ·')).length,count);assert.deepEqual(await listIds(),[chatId]);assert.equal(await page.evaluate(()=>messages.at(-1).content),'Réponse habituelle.');
    await page.evaluate(()=>showView('corrector'));await sidebar();assert.equal((await listIds()).length,count-1);await page.locator('#conversation-list [data-conversation-id="'+failedId+'"]').click();assert.equal((await page.textContent('#corrector-result')).trim(),'Texte corrigé');assert.equal(await page.inputValue('#corrector-text'),'Une correction interrompue par le réseau.');assert.match(await page.textContent('#corrector-status'),/partiel/);
    await page.evaluate(()=>showView('chat'));if(await page.getAttribute('#ui-sidebar-toggle','aria-expanded')==='false')await page.click('#ui-sidebar-toggle');await page.click('#new');await page.fill('#prompt','Cette conversation doit rester avec Hermes.');await page.click('#send');await page.waitForSelector('#send:not([disabled])');assert((await page.textContent('.message.assistant .content')).includes('Réponse Hermes ordinaire.'));
    await ready();await page.evaluate(()=>wsDeleteConversation(currentId));await ready();assert.equal(await page.evaluate(()=>currentId),chatId,'Deleting a chat must select another chat instead of the most recent correction');assert.equal(await page.evaluate(()=>messages.at(-1).content),'Réponse habituelle.');
    const direct=state.calls.filter(call=>call.body.text_transform&&call.path==='/v1/chat/completions');assert.equal(new Set(direct.map(call=>call.id)).size,direct.length);assert.deepEqual(errors,[]);
    results.push({platform,passed:true,modes:['correct','professional','friendly'],separate_sidebar_histories:true,legacy_results_reopen_in_corrector:true,project_lists_exclude_corrections:true,scoped_search_and_archives:true,contextual_new_button:true,chat_and_corrector_drafts_preserved:true,progressive_sse:true,json_fallback:platform==='android',partial_cancel:true,close_cancel:platform==='windows',failure_without_hermes_recovery:true,saved_history_survives_reload:true,ordinary_chat_stays_hermes:true,unique_request_ids:direct.length,simulation:'Local HTTP transport; no private user data or model'});
  }catch(error){console.error(JSON.stringify({platform,lastCalls:state.calls.slice(-8),ui:await page.evaluate(()=>({busy,historySyncPending,historySaving,correctorRunning,requestId,status:document.getElementById('corrector-status').textContent})),errors},null,2));throw error;}
  finally{await page.close();server.closeAllConnections?.();await new Promise(resolve=>server.close(resolve));}
}
async function main(){const {chromium,options}=require('./browser_test_support.cjs');const browser=await chromium.launch(options);try{for(const platform of ['windows','android'])await check(browser,platform);console.log(JSON.stringify({passed:true,checks:results},null,2));}finally{await browser.close();}}
main().catch(error=>{console.error(error);process.exitCode=1;});
