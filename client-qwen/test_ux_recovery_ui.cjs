/* Regression scenarios for drafts, navigation and memory edits, using only synthetic data. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http'),{execFileSync}=require('node:child_process');
const {chromium,options}=require('./browser_test_support.cjs');
const read=name=>fs.readFileSync(path.join(__dirname,name),'utf8');
const script=name=>'<script nonce="ux">'+read(name).replaceAll('</script','<\\/script')+'</script>';
const windows=read('chat.html').replace('__UI_CSS__',read('ui.css')).replace('</head>',()=>script('vendor/markdown-it.min.js')+script('markdown.js')+'</head>').replace('</body>',()=>read('workspace.html')+['ui.js','attachments.js','corrector.js','selection.js','thinking.js','voice.js','conversation.js'].map(script).join('')+'</body>');
const python=process.env.PYTHON_EXE||path.join(__dirname,'../toolchain/eg2-python/Scripts/python.exe');
const android=execFileSync(python,['-c',"import importlib.util,sys; from pathlib import Path; s=importlib.util.spec_from_file_location('assets',sys.argv[1]); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); print(m.prepare(Path(sys.argv[2])),end='')",path.join(__dirname,'../client-android/scripts/Prepare-Assets.py'),__dirname],{encoding:'utf8',maxBuffer:6e6,env:{...process.env,PYTHONIOENCODING:'utf-8'}});
async function check(browser,platform){
 const config={key:'synthetic-ux',storage:'ux-'+platform,model:'model-ux',version:'fixture',...(platform==='android'?{platform}:{})};
 const html=(platform==='android'?android:windows).replace('__CONFIG__',JSON.stringify(config)).replaceAll('__NONCE__','ux');
 const project={id:'a'.repeat(32),title:'Projet fictif UX',instructions:'',revision:1,documents:[],memories:[],conversations:[]};
 const state={history:null,revision:'1',preferences:{},failPreferences:false,failDelete:false};
 const json=(res,value,status=200)=>{res.writeHead(status,{'Content-Type':'application/json; charset=utf-8'});res.end(JSON.stringify(value));};
 const server=http.createServer(async(req,res)=>{
  let raw='';for await(const chunk of req)raw+=chunk;const body=JSON.parse(raw||'{}');
  if(req.url==='/'){res.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});return res.end(html);}
  if(req.headers.authorization!=='Bearer '+config.key)return json(res,{error:{message:'Fixture auth required'}},401);
  if(req.url==='/client/state')return json(res,{version:'fixture',preferences:state.preferences,profile_required:false,profile:{name:'Accès fictif'},update:{message:'À jour'},endpoint:'https://example.test',internet_endpoint:'example.test',local_api:'http://127.0.0.1/v1',key:config.key,connection:{connected:true,transport:'https',model:config.model,endpoint:'https://example.test'}});
  if(req.url==='/client/history'&&req.method==='GET')return json(res,{history:state.history,revision:state.revision});
  if(req.url==='/client/history/sync'){state.history=state.history||body.initial;return json(res,{history:state.history,revision:state.revision,message:'Synchronisé'});}
  if(req.url==='/client/history'){state.history=body.history;state.revision=String(Number(state.revision)+1);return json(res,{saved:true,revision:state.revision});}
  if(req.url==='/client/preferences'){
   if(state.failPreferences)return json(res,{error:{message:'Échec fictif de sauvegarde'}},503);
   const drafts={...state.preferences.conversation_drafts};for(const [id,text]of Object.entries(body.conversation_drafts||{})){if(text)drafts[id]=text;else delete drafts[id];}
   state.preferences={...state.preferences,...body,conversation_drafts:drafts};return json(res,{saved:true});
  }
  if(req.url==='/client/draft')return json(res,{draft:null});
  if(req.url==='/client/integrations')return json(res,{apps:[]});
  if(req.url==='/client/voice'||req.url==='/client/conversation')return json(res,{installed:false,phase:'idle'});
  if(req.url==='/v1/models')return json(res,{data:[{id:config.model,name:'Modèle fictif',available:true,capabilities:{thinking:false,context_length:4096}}]});
  if(req.url==='/v1/status')return json(res,{protocol:4,agent_protocol:4});
  if(req.url==='/v1/context')return json(res,{tokens:5,capacity:4096,estimated:true});
  if(req.url==='/v1/workspace')return json(res,{projects:[project],jobs:[]});
  if(req.url==='/v1/notifications'||req.url==='/v1/notifications/action')return json(res,{items:[],unread:0,preferences:{types:{}}});
  if(req.url==='/v1/workspace/action'){
   if(body.action==='project_save'){project.instructions=body.instructions;project.title=body.title;project.revision++;return json(res,{saved:true,revision:project.revision});}
   if(body.action==='memory_create'){project.memories.push({id:'b'.repeat(32),text:body.text});return json(res,{id:'b'.repeat(32)});}
   if(body.action==='memory_save'){project.memories.find(m=>m.id===body.id).text=body.text;return json(res,{saved:true});}
   if(body.action==='memory_delete'){if(state.failDelete)return json(res,{error:{message:'Suppression fictive refusée'}},503);project.memories=project.memories.filter(m=>m.id!==body.id);return json(res,{deleted:true});}
   if(body.action==='source_get')return json(res,{title:'Passage fictif',revision:1,status:'current',text:'Extrait synthétique'});
  }
  return json(res,{});
 });
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const context=await browser.newContext({viewport:{width:1440,height:900}}),page=await context.newPage(),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 if(platform==='android')await page.addInitScript(()=>{window.AndroidClient={notificationReady(){},notificationStatus(){return '{"enabled":false}';}};});
 const ready=()=>page.waitForFunction(()=>connected&&historyReady&&serverHistoryReady&&!historySyncPending&&!historySaving&&!uiPreferencesPending);
 const draftSaved=()=>page.waitForFunction(()=>!uiDraftDirty&&!uiPreferencesPending);
 const sidebar=async()=>{if(await page.locator('#ui-sidebar-toggle').getAttribute('aria-expanded')==='false')await page.locator('#ui-sidebar-toggle').click();};
 try{
  await page.goto('http://127.0.0.1:'+server.address().port);await ready();
  const first=await page.evaluate(()=>currentId);await page.locator('#prompt').fill('Brouillon de la conversation A');await draftSaved();
  await page.locator('#new').click();await ready();assert.equal(await page.locator('#prompt').inputValue(),'');
  const second=await page.evaluate(()=>currentId);assert.notEqual(first,second);await page.locator('#prompt').fill('Brouillon de la conversation B');await draftSaved();
  await page.locator('[data-conversation-id="'+first+'"]').click();await ready();assert.equal(await page.locator('#prompt').inputValue(),'Brouillon de la conversation A');
  await page.reload();await ready();assert.equal(await page.locator('#prompt').inputValue(),'Brouillon de la conversation A');
  await page.locator('[data-conversation-id="'+second+'"]').click();await ready();assert.equal(await page.locator('#prompt').inputValue(),'Brouillon de la conversation B');
  state.failPreferences=true;await page.locator('#prompt').fill('Brouillon après une panne');await page.waitForFunction(()=>document.getElementById('error').textContent.includes('Échec fictif'));
  assert(await page.evaluate(()=>uiDraftDirty));assert.equal(await page.locator('#prompt').inputValue(),'Brouillon après une panne');
  let warned=false;page.once('dialog',async d=>{warned=d.type()==='beforeunload';await d.dismiss();});await page.reload({timeout:1500}).catch(()=>{});assert(warned,'Unsaved drafts must warn before reload');
  state.failPreferences=false;await page.locator('#ui-draft-retry').click();await draftSaved();assert(!await page.locator('#ui-draft-retry').isVisible());await page.reload();await ready();assert.equal(await page.locator('#prompt').inputValue(),'Brouillon après une panne');
  await page.locator('#prompt').fill('');await draftSaved();await page.reload();await ready();assert.equal(await page.locator('#prompt').inputValue(),'');assert(!state.preferences.conversation_drafts[second]);
  await page.locator('#prompt').fill('Brouillon à restaurer après annulation');await draftSaved();await page.locator('#ui-conversation-menu summary').click();await page.locator('#delete-conversation').click();await ready();await draftSaved();assert(!state.preferences.conversation_drafts[second]);await page.locator('#undo-delete').click();await ready();assert.equal(await page.locator('#prompt').inputValue(),'Brouillon à restaurer après annulation');await page.locator('#prompt').fill('');await draftSaved();
  await page.locator('[data-view-button="projects"]').click();await page.locator('#ws-project-list button').click();await page.locator('[data-project-tab="instructions"]').click();await page.locator('#ws-project-instructions').fill('Consigne à enregistrer');
  warned=false;page.once('dialog',async d=>{warned=d.type()==='beforeunload';await d.dismiss();});await page.reload({timeout:1500}).catch(()=>{});assert(warned,'Unsaved instructions must warn');
  await page.locator('#ws-project-form button').first().click();await page.waitForFunction(()=>!ws.projectDirty);
  await page.locator('[data-project-tab="memory"]').click();assert.equal(await page.locator('[data-project-tab="memory"]').getAttribute('aria-current'),'page');
  await page.locator('#ws-memory-text').fill('Mémoire synthétique');await page.locator('#ws-memory-form button').click();await page.locator('#ws-memories textarea').waitFor();
  assert(await page.locator('#ws-memories textarea').evaluate(e=>e.labels.length===1));await page.locator('#ws-memories textarea').fill('Modification en attente');await page.evaluate(()=>wsRefresh());assert.equal(await page.locator('#ws-memories textarea').inputValue(),'Modification en attente');
  await page.locator('#ws-memories button').filter({hasText:'Enregistrer'}).click();await page.waitForFunction(()=>!uiMemoryEditsPending());
  page.once('dialog',d=>d.dismiss());await page.locator('#ws-memories button').filter({hasText:'Supprimer'}).click();assert.equal(project.memories.length,1);
  state.failDelete=true;page.once('dialog',d=>d.accept());await page.locator('#ws-memories button').filter({hasText:'Supprimer'}).click();await page.waitForFunction(()=>document.getElementById('ws-memory-status').textContent.includes('non supprimée'));assert.equal(await page.locator('#ws-memories textarea').count(),1);
  state.failDelete=false;page.once('dialog',d=>d.accept());await page.locator('#ws-memories button').filter({hasText:'Supprimer'}).click();await page.waitForFunction(()=>document.querySelectorAll('#ws-memories textarea').length===0);assert.equal(await page.evaluate(()=>document.activeElement.id),'ws-memory-text');
  await page.evaluate(()=>wsOpenSource('source-fixture'));assert(await page.getByRole('dialog',{name:'Passage fictif'}).isVisible());await page.keyboard.press('Escape');
  for(const width of [390,768]){
   await page.setViewportSize({width,height:width===390?844:1024});
   // Let the resize/media-query handler settle before opening the mobile drawer.
   await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
   await page.locator('#ui-sidebar-toggle').focus();await page.keyboard.press('Enter');assert.equal(await page.evaluate(()=>document.activeElement.id),'ui-sidebar-close');
   for(let i=0;i<20;i++){await page.keyboard.press('Tab');assert(await page.evaluate(()=>!!document.activeElement.closest('.sidebar')));}
   await page.keyboard.press('Escape');assert.equal(await page.evaluate(()=>document.activeElement.id),'ui-sidebar-toggle');assert(!await page.locator('#fred-main').evaluate(e=>e.inert));
   await sidebar();await page.locator('[data-view-button="projects"]').click();assert.equal(await page.evaluate(()=>document.activeElement.id),'workspace-heading');assert.equal(await page.getByRole('main').count(),1);
  }
  await page.setViewportSize({width:390,height:844});await sidebar();await page.locator('[data-view-button="chat"]').click();await page.waitForTimeout(250);
  const send=await page.locator('#send').boundingBox();assert(send.x>300&&send.x+send.width<=390,'Send remains at the right edge');
  assert.deepEqual(errors,[]);console.log(JSON.stringify({platform,passed:true,scenarios:['per-conversation drafts and reload','failed persistence blocks silent reload','cleared draft stays cleared','instructions unload warning','memory edit survives refresh','delete cancel/error/success','named source dialog','drawer focus at 390 and 768','one main landmark','right-aligned send']}));
 }finally{await context.close();await new Promise(r=>server.close(r));}
}
(async()=>{const browser=await chromium.launch(options);try{await check(browser,'windows');await check(browser,'android');}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
