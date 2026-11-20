/* Regression scenarios for drafts, navigation and memory edits, using only synthetic data. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http'),{execFileSync,spawn}=require('node:child_process');
const {chromium,options}=require('./browser_test_support.cjs');
const read=name=>fs.readFileSync(path.join(__dirname,name),'utf8');
const script=name=>'<script nonce="ux">'+read(name).replaceAll('</script','<\\/script')+'</script>';
const windows=read('chat.html').replace('__UI_CSS__',read('ui.css')).replace('</head>',()=>script('vendor/markdown-it.min.js')+script('markdown.js')+'</head>').replace('</body>',()=>read('workspace.html')+['ui.js','attachments.js','corrector.js','selection.js','thinking.js','voice.js','conversation.js','project-conversation.js'].map(script).join('')+'</body>');
const windowsShell=process.env.KIARA_UX_WINDOWS_EXE;
const desktopAudit=process.argv.includes('--desktop-audit');
const linuxOnly=process.argv.includes('--linux-only');
const windowsOnly=Boolean(windowsShell)||process.argv.includes('--windows-only')||linuxOnly;
const python=process.env.PYTHON_EXE||path.join(__dirname,'../toolchain/eg2-python/Scripts/python.exe');
const modernWindows=execFileSync(python,['-B','-c',
 "import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); from kiara_shared.conversation_shell import modern_chat; root=Path(sys.argv[2]); print(modern_chat(sys.stdin.read(), (root / 'kiara-shell.html').read_text(encoding='utf-8')),end='')",
 path.join(__dirname,'../shared'),__dirname],{input:windows,encoding:'utf8',maxBuffer:6e6,env:{...process.env,PYTHONIOENCODING:'utf-8'}});
const android=windowsOnly?null:execFileSync(python,['-c',"import importlib.util,sys; from pathlib import Path; s=importlib.util.spec_from_file_location('assets',sys.argv[1]); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); print(m.prepare(Path(sys.argv[2])),end='')",path.join(__dirname,'../client-android/scripts/Prepare-Assets.py'),__dirname],{encoding:'utf8',maxBuffer:6e6,env:{...process.env,PYTHONIOENCODING:'utf-8'}});
async function checkWindowsOriginal(page){
 const url=page.url();
 await page.getByRole('button',{name:'Voir la source',exact:true}).click();
 const source=page.getByRole('dialog',{name:'Notice de recette'});
 await source.getByText('Texte indexé de la notice.').waitFor();
 const [download]=await Promise.all([
  page.waitForEvent('download',{timeout:10000}),
  source.getByRole('link',{name:'Télécharger l’original'}).click()
 ]);
 assert.equal(download.suggestedFilename(),'notice.txt');
 assert.equal(fs.readFileSync(await download.path(),'utf8'),'Original fictif');
 await source.getByRole('button',{name:'Fermer',exact:true}).click();
 assert.equal(page.url(),url);
 assert(await page.getByRole('checkbox',{name:'Éphémère'}).isChecked());
}
async function check(browser,platform){
 const config={key:'synthetic-ux',storage:'ux-'+platform,model:'model-ux',version:'fixture',...(['android','linux'].includes(platform)?{platform}:{})};
 const base=platform==='linux'?windows.replace('</body>',()=>script('linux_features.js')+'</body>'):(platform==='android'?android:windows);
 const html=base.replace('__CONFIG__',JSON.stringify(config)).replaceAll('__NONCE__','ux');
 // Ouvre un menu discret (détails) avant d'interagir avec un contrôle qu'il contient.
 const openMenu=(target,selector)=>target.locator(selector).evaluate(d=>{if(!d.open)d.open=true;});
 const project={id:'a'.repeat(32),title:'Projet fictif UX',instructions:'',revision:1,documents:[],memories:[],conversations:[]};
 const managed={id:'11111111-2222-3333-4444-555555555555',title:'Projet Agent fictif',code:'ERP-42',instructions:'',can_edit:true,documents:[],memories:[],conversations:[]};
 const state={history:null,revision:'1',preferences:{},failPreferences:false,failDelete:false};
 const json=(res,value,status=200)=>{res.writeHead(status,{'Content-Type':'application/json; charset=utf-8'});res.end(JSON.stringify(value));};
 const server=http.createServer(async(req,res)=>{
  let raw='';for await(const chunk of req)raw+=chunk;const body=JSON.parse(raw||'{}');
  if(req.url==='/'||req.url==='/chat'){
   res.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});
   return res.end((desktopAudit || state.modernNavigation) && platform!=='android'
    ? (platform==='linux'?modernWindows.replace('</body>',()=>script('linux_features.js')+'</body>'):modernWindows).replace('__CONFIG__',JSON.stringify(config)).replaceAll('__NONCE__','ux') : html);
  }
  if(state.projectConversation){
   if(platform==='android'&&req.headers.authorization!=='Bearer '+config.key)return json(res,{error:{message:'Fixture auth required'}},401);
   const threadPath='/api/v1/workspace/assistant-threads';
   if(req.url==='/api/v1/project-catalogue')return json(res,[{...managed,brain_project_id:'brain-recette'},
     {id:'projet-a-relier',title:'Projet sans sources',brain_project_id:null}]);
   if(req.url==='/api/v1/brain/projects')return json(res,[{id:'brain-autonome',name:'Projet de connaissance'}]);
   if(req.url==='/api/v1/projects/projet-a-relier/brain/ensure'){
    assert.equal(req.method,'POST');
    state.projectLinks++;
    return json(res,{linked:true,brain_project_id:'brain-relie'});
   }
   if(req.url.startsWith(threadPath)){
    if(req.method==='GET')return json(res,req.url.includes('/historical')?state.projectThread:{items:[state.projectThread]});
    if(state.projectConflict)return json(res,{detail:'Révision modifiée par un autre poste.'},409);
    state.projectWrites++;
    assert.equal(body.expected_revision,state.projectThread.revision);
    state.projectThread={...state.projectThread,messages:body.messages,revision:state.projectThread.revision+1};
    return json(res,state.projectThread);
   }
   if(req.url==='/v1/sources/source-recette')return json(res,{metadata:{filename:'Notice de recette'},
     artifacts:[{text:'Texte indexé de la notice.'}]});
   if(req.url==='/v1/sources/source-recette/raw'){
    res.writeHead(200,{'Content-Type':'text/plain','Content-Disposition':'attachment; filename="notice.txt"'});
    return res.end('Original fictif');
   }
   if(req.url==='/v1/projects/chat/stream'){
    assert.equal(body.project_id,'brain-recette');
    assert.equal(body.include_evidence,false);
    res.writeHead(200,{'Content-Type':'text/event-stream'});
    if(body.query==='Question à interrompre'){
     res.write('event: delta\ndata: {"text":"Fragment de réponse"}\n\n');
     return;
    }
    return res.end('event: done\ndata: {"answer":"Réponse de recette","citations":[{"source_id":"source-recette","excerpt":"Extrait de recette."}],"warnings":["Certaines sources sont indisponibles."]}\n\n');
   }
  }
  if(req.headers.authorization!=='Bearer '+config.key)return json(res,{error:{message:'Fixture auth required'}},401);
  if(req.url==='/client/state'){
   if(state.stateGate)await state.stateGate;
   if(state.failState)return json(res,{error:{message:'Réglages fictifs indisponibles'}},503);
   const preferences=state.preferencesOverride===undefined?state.preferences:state.preferencesOverride;
   return json(res,{version:'fixture',preferences,profile_required:false,profile:{name:'Accès fictif'},update:{message:'À jour'},endpoint:'https://example.test',internet_endpoint:'example.test',local_api:'http://127.0.0.1/v1',key:config.key,connection:{connected:true,transport:'https',model:config.model,endpoint:'https://example.test'}});
  }
  if(req.url==='/client/history'&&req.method==='GET'){
   if(state.historyGate)await state.historyGate;
   if(state.failHistory)return json(res,{error:{message:'Lecture fictive indisponible'}},503);
   return json(res,{history:state.historyOverride===undefined?state.history:state.historyOverride,revision:state.revision});
  }
  if(req.url==='/client/history/sync'){state.history=state.history||body.initial;return json(res,{history:state.history,revision:state.revision,message:'Synchronisé'});}
  if(req.url==='/client/history'){
   if(body.revision!==state.revision)return json(res,{error:{message:'Conflit fictif de révision'}},409);
   state.history=body.history;state.revision=String(Number(state.revision)+1);return json(res,{saved:true,revision:state.revision});
  }
  if(req.url==='/client/preferences'){
   if(state.failPreferences)return json(res,{error:{message:'Échec fictif de sauvegarde'}},503);
   const drafts={...state.preferences.conversation_drafts};for(const [id,text]of Object.entries(body.conversation_drafts||{})){if(text)drafts[id]=text;else delete drafts[id];}
   state.preferences={...state.preferences,...body,conversation_drafts:drafts};return json(res,{saved:true});
  }
  if(req.url==='/client/draft')return json(res,{draft:null});
  if(req.url==='/client/project-session')return state.projectConversation&&!state.failProjectSession?json(res,{url:'/app'}):json(res,{error:{message:'Le service Projets est indisponible.'}},503);
  if(req.url==='/client/integrations')return json(res,{apps:[]});
  if(req.url==='/client/voice'||req.url==='/client/conversation')return json(res,{installed:false,phase:'idle'});
  if(req.url==='/v1/models')return json(res,{data:[{id:config.model,name:'Modèle fictif',available:true,capabilities:{thinking:false,context_length:4096}}]});
  if(req.url==='/v1/status')return json(res,{protocol:4,agent_protocol:4,command_nonce_version:2,server_time_ms:Date.now()});
  if(req.url==='/v1/context')return json(res,{tokens:5,capacity:4096,estimated:true});
  if(req.url==='/v1/workspace'){
   if(state.workspaceGate)await state.workspaceGate;
   return json(res,state.managed?{projects:state.managed==='ready'?[managed]:[],jobs:[],project_catalogue:{provider:'agent',state:state.managed,can_create:state.managed==='ready',...(state.modernNavigation?{interface:'projects-v1',navigation:'kiara-v1'}:{})}}:{projects:[project],jobs:[]});
  }
  if(req.url==='/v1/notifications'||req.url==='/v1/notifications/action'){
   const visible=state.transcription===true;
   const item={id:'e'.repeat(32),sequence:1,type:'transcription_ready',title:'Transcription disponible',created:1700000000,target:{kind:'agent_project',project:managed.id}};
   if(body.action==='get')return visible&&body.id===item.id?json(res,{notification:item}):json(res,{error:{message:'Notification indisponible'}},404);
   return json(res,{items:visible&&!body.after?[item]:[],cursor:1,generation:'fixture',agent_scope:visible?'allowed':'empty',
    retained_ids:visible?[item.id]:[],preferences:{types:{}},subscription:{enabled:true}});
  }
  if(req.url==='/v1/workspace/action'){
   if(body.action==='memory_create'&&body.project===managed.id){managed.memories.push({id:'c'.repeat(32),text:body.text,revision:'1'});return json(res,{revision:'1'});}
   if(body.action==='conversation_save'&&body.project===managed.id){managed.conversations=[{id:body.id,title:body.title,revision:1,archived:false}];return json(res,{revision:1});}
   if(body.action==='project_archive'&&body.id===managed.id){managed.archived=body.archived;return json(res,{id:managed.id});}
   if(body.action==='project_save'){project.instructions=body.instructions;project.title=body.title;project.revision++;return json(res,{saved:true,revision:project.revision});}
   if(body.action==='memory_create'){project.memories.push({id:'b'.repeat(32),text:body.text,revision:'1'});return json(res,{id:'b'.repeat(32)});}
   if(body.action==='memory_save'||body.action==='memory_delete'){
    const memory=project.memories.find(m=>m.id===body.id);
    if(body.revision!==memory.revision)return json(res,{error:{message:'Ce souvenir a changé. Rechargez sa version actuelle.'}},409);
    if(body.action==='memory_save'){memory.text=body.text;memory.revision=String(Number(memory.revision)+1);return json(res,{saved:true,revision:memory.revision});}
    if(state.failDelete)return json(res,{error:{message:'Suppression fictive refusée'}},503);
    project.memories=project.memories.filter(m=>m.id!==body.id);return json(res,{deleted:true});
   }
   if(body.action==='source_get')return json(res,{title:'Passage fictif',revision:1,status:'current',text:'Extrait synthétique'});
  }
  return json(res,{});
 });
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 if(windowsShell){
  const profile=fs.mkdtempSync(path.join(require('node:os').tmpdir(),'kiara-webview-'));
  const probe=http.createServer();
  await new Promise(resolve=>probe.listen(0,'127.0.0.1',resolve));
  const debugPort=probe.address().port;
  await new Promise(resolve=>probe.close(resolve));
  state.managed='ready';
  state.projectConversation=true;
  let resumeWorkspace;
  if(desktopAudit){
   state.modernNavigation=true;
   state.workspaceGate=new Promise(resolve=>{resumeWorkspace=resolve;});
  }
  const shell=spawn(windowsShell,['--local-url','http://127.0.0.1:'+server.address().port+'/chat','--hidden'],{
   env:{...process.env,WEBVIEW2_USER_DATA_FOLDER:profile,WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:'--remote-debugging-port='+debugPort},windowsHide:true
  });
  try{
   const debugUrl='http://127.0.0.1:'+debugPort;
   for(let i=0;i<100;i++){
    if(shell.exitCode!==null)throw new Error('Kiara a quitté la recette WebView2.');
    if(await fetch(debugUrl+'/json/version').then(response=>response.ok).catch(()=>false))break;
    await new Promise(resolve=>setTimeout(resolve,100));
   }
   const webview=await chromium.connectOverCDP(debugUrl,{timeout:5000});
   try{
    const context=webview.contexts()[0];
    context.setDefaultTimeout(10000);
    const page=context.pages()[0]||await context.waitForEvent('page',{timeout:5000});
    if(desktopAudit){
      await page.getByRole('button',{name:'Activité',exact:true}).waitFor();
      assert.deepEqual(await page.locator('#client-navigation .nav-button:visible').allTextContents(),['Conversations','Projets','Notes','Mails','Réunions','Activité']);
      const toolbar=page.locator('.conversation-toolbar');
      const assistant=toolbar.getByRole('button',{name:'Assistant de projet',exact:true});
      assert(await assistant.isDisabled());
      const beforeCatalogue=await toolbar.boundingBox();
      resumeWorkspace();
      await page.waitForFunction(()=>!document.getElementById('project-conversation-toggle').disabled);
      assert.deepEqual(await toolbar.boundingBox(),beforeCatalogue);
      if(process.env.UI_PROOF_DIRECTORY)fs.mkdirSync(process.env.UI_PROOF_DIRECTORY,{recursive:true});
      for(const [width,height] of [[1280,720],[1920,1080],[2560,1440]]){
        await page.setViewportSize({width,height});
        await page.getByLabel('Modèle de cette conversation').waitFor({state:'visible'});
        assert.equal((await page.locator('.sidebar').boundingBox()).width,216);
        const vocal=page.getByRole('button',{name:'Vocal',exact:true});
        await vocal.click({trial:true});
        if(process.env.UI_PROOF_DIRECTORY)await page.screenshot({path:path.join(process.env.UI_PROOF_DIRECTORY,`webview2-${width}x${height}.png`)});
        await vocal.press('Enter');
        assert.equal(await page.evaluate(()=>document.activeElement.id),'voice-title');
        const start=await page.locator('#conversation-start').boundingBox();
        assert(start && start.y>=0 && start.y+start.height<=height,'Vocal must start without scrolling');
        if(process.env.UI_PROOF_DIRECTORY)await page.screenshot({path:path.join(process.env.UI_PROOF_DIRECTORY,`vocal-webview2-${width}x${height}.png`)});
        await page.getByRole('button',{name:'Conversations',exact:true}).click();
        for(const [section,title] of [['vocal','Conversation vocale'],['dictee','Dictée'],['notifications','Notifications']]){
          await page.evaluate(section=>{location.hash='#reglages-'+section;},section);
          const panel=page.locator('.device-preferences');
          await panel.getByRole('heading',{name:title,exact:true}).waitFor();
          assert.equal(await page.locator('.settings-subnav').isVisible(),false);
          assert(await page.locator('#device-settings-back').isVisible());
          if(process.env.UI_PROOF_DIRECTORY)await page.screenshot({path:path.join(process.env.UI_PROOF_DIRECTORY,section+'-reglages-'+width+'x'+height+'.png')});
        }
        await page.getByRole('button',{name:'Conversations',exact:true}).click();
      }
    }
    await page.getByRole('button',{name:'Assistant de projet',exact:true}).click();
    await page.getByRole('combobox',{name:'Projet',exact:true}).selectOption('brain-recette');
    await openMenu(page,'.project-conversation-options');
    await page.getByRole('checkbox',{name:'Inclure les sources à confirmer'}).uncheck();
    await page.locator('#prompt').fill('Contrôle du document original');
    await page.locator('#composer').evaluate(form=>form.requestSubmit());
    await page.getByRole('region',{name:'Conversation de projet'}).getByText('Sources',{exact:true}).click();
    await checkWindowsOriginal(page);
    console.log(JSON.stringify({platform:'windows-webview2',passed:true,checks:['source preview','original bytes','ephemeral exchange remains open']}));
   }finally{await webview.close();}
  }finally{
   resumeWorkspace?.();
   shell.kill();
   server.closeAllConnections();
   await new Promise(resolve=>server.close(resolve));
  }
  return;
 }
 const context=await browser.newContext({viewport:{width:1440,height:900}}),page=await context.newPage(),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 if(platform==='android')await page.addInitScript(()=>{
  window.AndroidClient={notificationReady(){},notificationStatus(){return '{"enabled":false}';},
   downloadProjectOriginal(path,filename){window.lastOriginalDownload={path,filename};}};
 });
 const ready=()=>page.waitForFunction(()=>connected&&historyReady&&serverHistoryReady&&!historySyncPending&&!historySaving&&!uiPreferencesPending);
 const draftSaved=()=>page.waitForFunction(()=>!uiDraftDirty&&!uiPreferencesPending);
 const sidebar=async()=>{if(await page.locator('#ui-sidebar-toggle').getAttribute('aria-expanded')==='false')await page.locator('#ui-sidebar-toggle').click();};
 try{
  await page.goto('http://127.0.0.1:'+server.address().port);await ready();
  assert.match(await page.evaluate(()=>clientRequestId()),/^v2_[a-f0-9]{32}$/);
  await page.evaluate(()=>commandNonceVersion=1);assert.match(await page.evaluate(()=>clientRequestId()),/^[a-f0-9]{32}$/);await page.evaluate(()=>commandNonceVersion=2);
  assert.deepEqual(await page.evaluate(()=>[...document.querySelectorAll('#client-navigation .nav-button')].map(b=>b.dataset.viewButton)),platform!=='android'?['chat','projects','notifications']:['chat','voice','projects','corrector','assistant','notifications']);
  if(platform!=='android'){
   for(const view of ['voice','corrector']){
    await openMenu(page,'#ui-composer-options-menu');
    await page.locator('#composer [data-view-button="'+view+'"]').click();
    await page.locator('[data-view="'+view+'"]:not([hidden])').waitFor();
    await sidebar();await page.locator('[data-view-button="chat"]').click();
   }
   await sidebar();await page.locator('[data-view-button="settings"]').click();
   await page.getByRole('navigation',{name:'Réglages du client'}).getByRole('button',{name:'Mémoire et rappels'}).click();
   await page.locator('[data-view="settings"] [data-view="assistant"]:not([hidden])').waitFor();
   await sidebar();await page.locator('[data-view-button="chat"]').click();
  }
  if(platform!=='android'){
   await page.locator('#prompt').fill('Brouillon avant ouverture de Projets');await draftSaved();
   await sidebar();await page.locator('[data-view-button="projects"]').click();
   await page.getByRole('button',{name:'Ouvrir le portefeuille'}).click();
   await page.waitForFunction(()=>document.getElementById('error').textContent.includes('Le service Projets est indisponible.'));
   await sidebar();await page.locator('[data-view-button="chat"]').click();
   assert.equal(await page.locator('#prompt').inputValue(),'Brouillon avant ouverture de Projets');
   await page.locator('#prompt').fill('');await draftSaved();
  }
  assert.equal(await page.locator('#ui-document-controls').isVisible(),false);
  await openMenu(page,'#ui-composer-options-menu');
  await page.locator('#ws-chat-project').selectOption(project.id);await page.waitForFunction(()=>!conversationActionPending&&document.getElementById('ui-document-controls').hidden===false);await ready();
  assert.equal(await page.locator('#ui-document-controls').isVisible(),true);assert.equal(await page.locator('#ws-publish').isVisible(),true);
  await openMenu(page,'#ui-composer-options-menu');
  await page.locator('#ws-chat-project').selectOption('');await page.waitForFunction(()=>!conversationActionPending&&document.getElementById('ui-document-controls').hidden===true);await ready();
  assert.equal(await page.locator('#ui-document-controls').isVisible(),false);
  const first=await page.evaluate(()=>currentId);await page.locator('#prompt').fill('Brouillon de la conversation A');await draftSaved();
  if(platform!=='android'){
   let release;state.stateGate=new Promise(resolve=>{release=resolve;});
   try{
    await page.reload({waitUntil:'domcontentloaded'});
    await page.waitForFunction(()=>historyReady&&!uiDraftsLoaded);
    assert.equal(await page.locator('#prompt').evaluate(node=>node.readOnly),true,'La saisie attend la récupération des brouillons.');
    assert.equal(await page.locator('#send').isDisabled(),true,'L’envoi attend la récupération des brouillons.');
    assert.equal(await page.getByRole('button',{name:'Assistant de projet',exact:true,includeHidden:true}).isDisabled(),true);
    await page.locator('#prompt').focus();await page.keyboard.type('texte prématuré');
    assert.equal(await page.locator('#prompt').inputValue(),'');
   }finally{state.stateGate=null;release();}
   await page.waitForFunction(()=>uiDraftsLoaded);await ready();
   assert.equal(await page.locator('#prompt').inputValue(),'Brouillon de la conversation A');
   state.historyGate=new Promise(resolve=>{release=resolve;});
   try{
    await page.reload({waitUntil:'domcontentloaded'});
    await page.waitForFunction(()=>uiDraftsLoaded&&!historyReady);
    assert.equal(await page.locator('#prompt').evaluate(node=>node.readOnly),true,'La saisie attend aussi la récupération de la conversation.');
    assert.equal(await page.locator('#send').isDisabled(),true);
   }finally{state.historyGate=null;release();}
   await ready();assert.equal(await page.locator('#prompt').inputValue(),'Brouillon de la conversation A');
   state.failHistory=true;
   try{
    await page.reload({waitUntil:'domcontentloaded'});await page.waitForFunction(()=>historyBlocked&&uiDraftsLoaded);
    assert.equal(await page.locator('#prompt').evaluate(node=>node.readOnly),true,'La saisie reste bloquée si l’historique est illisible.');
    assert.equal(await page.locator('#send').isDisabled(),true);
   }finally{state.failHistory=false;}
   await page.reload();await ready();assert.equal(await page.locator('#prompt').inputValue(),'Brouillon de la conversation A');
   state.preferences.corrector_text='Correction fictive à préserver';
   state.preferencesOverride={conversation_drafts:'données invalides'};
   try{
    const response=page.waitForResponse(result=>result.url().endsWith('/client/state'));
    await page.reload({waitUntil:'domcontentloaded'});await response;
    await page.waitForFunction(()=>document.getElementById('error').textContent.includes('Brouillons locaux invalides'));
    assert.equal(await page.evaluate(()=>uiDraftsLoaded),false);
    assert.equal(await page.locator('#prompt').evaluate(node=>node.readOnly),true);
    assert.equal(await page.locator('#corrector-text').evaluate(node=>node.readOnly),true,'Le correcteur attend lui aussi ses données locales.');
    assert.equal(state.preferences.conversation_drafts[first],'Brouillon de la conversation A');
   }finally{state.preferencesOverride=undefined;}
   await page.waitForFunction(()=>uiDraftsLoaded);await ready();
   assert.equal(await page.locator('#prompt').inputValue(),'Brouillon de la conversation A');
   assert.equal(await page.locator('#corrector-text').inputValue(),'Correction fictive à préserver');
   state.failState=true;
   try{
    await page.reload({waitUntil:'domcontentloaded'});
    await page.waitForFunction(()=>document.getElementById('error').textContent.includes('Réglages fictifs indisponibles'));
    assert.equal(await page.evaluate(()=>uiDraftsLoaded),false);
    assert.equal(await page.locator('#prompt').evaluate(node=>node.readOnly),true);
    assert.equal(await page.locator('#corrector-text').evaluate(node=>node.readOnly),true);
   }finally{state.failState=false;}
   await page.waitForFunction(()=>uiDraftsLoaded);await ready();
   assert.equal(await page.locator('#prompt').inputValue(),'Brouillon de la conversation A');
   assert.equal(await page.locator('#corrector-text').inputValue(),'Correction fictive à préserver');
   state.historyGate=new Promise(resolve=>{release=resolve;});
   try{
    await page.reload({waitUntil:'domcontentloaded'});
    await page.waitForFunction(()=>!historyReady&&!uiDraftsLoaded);
    await page.evaluate(()=>uiPersistPreferences());
    assert.equal(state.preferences.corrector_text,'Correction fictive à préserver','Un enregistrement précoce conserve le texte du correcteur.');
   }finally{state.historyGate=null;release();}
   await ready();
   assert.equal(await page.locator('#prompt').inputValue(),'Brouillon de la conversation A','Le brouillon est restauré après un enregistrement précoce des réglages.');
   assert.equal(await page.locator('#corrector-text').inputValue(),'Correction fictive à préserver');
  }
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
  await openMenu(page,'#ui-composer-options-menu');
  await page.evaluate(async()=>{const old=historyRevision;historyRevision='stale';try{await flushHistory();}catch{}});
  assert.equal(await page.evaluate(()=>historyBlocked),true);assert.equal(await page.locator('#history-conflict-merge').isVisible(),true);assert.equal(await page.locator('#send').isDisabled(),true);
  await page.getByRole('button',{name:'Fusionner et reprendre l’historique'}).click();await ready();
  assert.equal(await page.evaluate(()=>historyBlocked),false);assert.equal(await page.locator('#history-conflict-merge').isVisible(),false);assert.equal(await page.locator('#send').isDisabled(),false);
  await page.locator('[data-view-button="projects"]').click();await page.locator('#ws-project-list button').click();await page.locator('[data-project-tab="instructions"]').click();await page.locator('#ws-project-instructions').fill('Consigne à enregistrer');
  warned=false;page.once('dialog',async d=>{warned=d.type()==='beforeunload';await d.dismiss();});await page.reload({timeout:1500}).catch(()=>{});assert(warned,'Unsaved instructions must warn');
  await page.locator('#ws-project-form button').first().click();await page.waitForFunction(()=>!ws.projectDirty);
  await page.locator('[data-project-tab="memory"]').click();assert.equal(await page.locator('[data-project-tab="memory"]').getAttribute('aria-current'),'page');
  await page.locator('#ws-memory-text').fill('Mémoire synthétique');await page.locator('#ws-memory-form button').click();await page.locator('#ws-memories textarea').waitFor();
  assert(await page.locator('#ws-memories textarea').evaluate(e=>e.labels.length===1));await page.locator('#ws-memories textarea').fill('Modification en attente');await page.evaluate(()=>wsRefresh());assert.equal(await page.locator('#ws-memories textarea').inputValue(),'Modification en attente');
  await page.locator('#ws-memories button').filter({hasText:'Enregistrer'}).click();await page.waitForFunction(()=>!uiMemoryEditsPending());
  await page.locator('#ws-memories textarea').fill('Brouillon concurrent à conserver');
  project.memories[0].text='Modification récente sur un autre appareil';project.memories[0].revision=String(Number(project.memories[0].revision)+1);
  await page.evaluate(()=>wsRefresh());
  await page.locator('#ws-memories button').filter({hasText:'Enregistrer'}).click();
  await page.waitForFunction(()=>document.getElementById('ws-memory-status').textContent.includes('a changé'));
  assert.equal(await page.locator('#ws-memory-status').evaluate(e=>e.classList.contains('ws-warning')),true);
  assert.equal(await page.locator('#ws-memories textarea').inputValue(),'Brouillon concurrent à conserver');
  assert.equal(project.memories[0].text,'Modification récente sur un autre appareil');
  page.once('dialog',d=>d.accept());await page.getByRole('button',{name:'Recharger la version du serveur'}).click();
  await page.waitForFunction(()=>document.querySelector('#ws-memories textarea').dataset.revision===ws.data.projects[0].memories[0].revision);
  assert.equal(await page.locator('#ws-memory-status').evaluate(e=>e.classList.contains('ws-warning')),false);
  page.once('dialog',d=>d.dismiss());await page.locator('#ws-memories button').filter({hasText:'Supprimer'}).click();assert.equal(project.memories.length,1);
  state.failDelete=true;page.once('dialog',d=>d.accept());await page.locator('#ws-memories button').filter({hasText:'Supprimer'}).click();await page.waitForFunction(()=>document.getElementById('ws-memory-status').textContent.includes('non supprimée'));assert.equal(await page.locator('#ws-memory-status').evaluate(e=>e.classList.contains('ws-warning')),true);assert.equal(await page.locator('#ws-memories textarea').count(),1);
  state.failDelete=false;page.once('dialog',d=>d.accept());await page.locator('#ws-memories button').filter({hasText:'Supprimer'}).click();await page.waitForFunction(()=>document.querySelectorAll('#ws-memories textarea').length===0);assert.equal(await page.evaluate(()=>document.activeElement.id),'ws-memory-text');
  await page.evaluate(()=>wsOpenSource('source-fixture'));assert(await page.getByRole('dialog',{name:'Passage fictif'}).isVisible());await page.keyboard.press('Escape');
  await page.locator('#connection').click();assert.equal(await page.locator('#connection-panel').isVisible(),true);assert.equal(await page.evaluate(()=>document.activeElement.id),'connection-close');
  await page.keyboard.press('Escape');assert.equal(await page.locator('#connection-panel').isVisible(),false);assert.equal(await page.evaluate(()=>document.activeElement.id),'connection');
  if(platform==='android'){
   await page.evaluate(()=>showView('voice'));await page.locator('#voice-settings-toggle').click();assert.equal(await page.evaluate(()=>document.getElementById('voice-settings-dialog').open),true);
   assert.equal(await page.evaluate(()=>window.androidBack()),true);assert.equal(await page.evaluate(()=>document.getElementById('voice-settings-dialog').open),false);
   await page.evaluate(()=>showView('chat'));
  }
  if(!desktopAudit){
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
  } else {await page.setViewportSize({width:1280,height:720});await page.evaluate(()=>showView('chat'));}
  state.managed='ready';await page.evaluate(()=>wsRefresh());
  await openMenu(page,'#ui-composer-options-menu');
  await page.locator('#ws-chat-project').selectOption(managed.id);
  await page.waitForFunction(id=>wsCurrent().project_id===id&&!conversationActionPending,managed.id);
  assert(await page.locator('#ws-publish').isEnabled());
  await page.locator('#ws-publish').click();
  await page.waitForFunction(()=>wsCurrent().server_revision===1&&!conversationActionPending);
  assert.equal(managed.conversations.length,1);
  await page.evaluate(()=>showView('projects'));
  await page.locator('#ws-project-search').fill('ERP-42');
  await page.locator('#ws-project-list button').click();
  await page.locator('[data-project-pane="conversations"]').waitFor();
  assert.equal(await page.locator('#ws-agent-project-open').isVisible(),platform!=='android');
  await page.locator('[data-project-tab="memory"]').click();
  await page.locator('#ws-memory-text').fill('Mémoire privée Agent');
  await page.locator('#ws-memory-form button').click();
  await page.locator('#ws-memories textarea').waitFor();
  assert.equal(await page.locator('#ws-memories textarea').inputValue(),'Mémoire privée Agent');
  for(const allowed of [true,false,true]){
   state.transcription=allowed;
   await page.waitForFunction(()=>!fredInbox.busy);
   await page.evaluate(()=>fredInboxLoad());
   assert.equal(await page.locator('#fred-inbox-list [data-notification-id]').count(),allowed?1:0);
  }
  await page.locator('#ws-agent-project-archive').click();
  await page.waitForFunction(()=>ws.data.projects[0].archived);
  assert(await page.locator('#ws-project-chat').isDisabled());
  state.managed='unavailable';await page.evaluate(()=>wsRefresh());
  assert(await page.locator('#ui-project-create').isDisabled());
  assert.match(await page.locator('#ws-project-list').textContent(),/Projets indisponibles/);
  {
   state.managed='ready';state.projectConversation=true;state.projectWrites=0;state.projectLinks=0;
   state.projectThread={id:'historical',title:'Échange historique',project_id:'brain-recette',revision:2,
    messages:[{role:'user',text:'Première question'},{role:'assistant',text:'Première réponse'}]};
   await page.evaluate(async()=>{showView('chat');await wsRefresh();});
   await page.locator('#prompt').fill('Brouillon personnel à préserver');await draftSaved();
   await page.getByRole('button',{name:'Assistant de projet',exact:true}).click();
   const projects=page.getByRole('combobox',{name:'Projet',exact:true});
   await projects.selectOption('erp:projet-a-relier');
   assert.equal(state.projectLinks,0);
   assert(await page.getByRole('button',{name:'Envoyer le message'}).isDisabled());
   await page.locator('#prompt').fill('Brouillon du projet à relier');
   await page.getByRole('button',{name:'Relier les sources du projet'}).click();
   await page.waitForFunction(()=>document.querySelector('.project-conversation-controls select').value==='brain-relie');
   assert.equal(state.projectLinks,1);
   assert.equal(await page.locator('#prompt').inputValue(),'Brouillon du projet à relier');
   await projects.selectOption('brain-autonome');
   await page.getByRole('combobox',{name:'Projet',exact:true}).selectOption('brain-recette');
   assert(await page.getByRole('checkbox',{name:'Éphémère'}).isChecked());
   await openMenu(page,'.project-conversation-options');
   await page.getByRole('checkbox',{name:'Inclure les sources à confirmer'}).uncheck();
   await page.locator('#prompt').fill('Ne pas conserver cet échange');
   await page.locator('#composer').evaluate(form=>form.requestSubmit());
   await page.getByText('Réponse de recette',{exact:true}).waitFor();
   await page.getByText('Recherche de sources partielle',{exact:true}).click();
   await page.getByText('Certaines sources sont indisponibles.',{exact:true}).waitFor();
   await page.getByRole('region',{name:'Conversation de projet'}).getByText('Sources',{exact:true}).click();
   if(platform==='android'){
    await page.getByRole('button',{name:'Voir la source',exact:true}).click();
    const source=page.getByRole('dialog',{name:'Notice de recette'});
    await source.getByText('Texte indexé de la notice.').waitFor();
    await source.getByRole('button',{name:'Télécharger l’original',exact:true}).click();
    assert.deepEqual(await page.evaluate(()=>window.lastOriginalDownload),
      {path:'/v1/sources/source-recette/raw',filename:'Notice de recette'});
    await source.getByRole('button',{name:'Fermer',exact:true}).click();
   }else await checkWindowsOriginal(page);
   await page.getByRole('button',{name:'Conversations personnelles'}).click();
   assert.equal(await page.locator('#prompt').inputValue(),'Brouillon personnel à préserver');
   assert.equal(state.projectWrites,0);
   assert(!JSON.stringify(state.preferences).includes('Ne pas conserver'));
   assert(!JSON.stringify(state.history).includes('Ne pas conserver'));
   await page.getByRole('button',{name:'Assistant de projet',exact:true}).click();
   await page.getByRole('combobox',{name:'Historique de projet'}).selectOption('historical');
   await page.getByText('Première réponse',{exact:true}).waitFor();
   assert.equal(await page.getByRole('checkbox',{name:'Éphémère'}).isChecked(),false);
   await page.locator('#prompt').fill('Suite du fil enregistré');
   await page.locator('#composer').evaluate(form=>form.requestSubmit());
   await page.waitForFunction(()=>!document.querySelector('.project-conversation-switch button').disabled);
   assert.equal(state.projectWrites,1);
   assert(state.projectThread.messages.some(message=>message.text==='Suite du fil enregistré'));
   assert(!state.projectThread.messages.some(message=>message.text==='Ne pas conserver cet échange'));
   state.projectConflict=true;
   await page.locator('#prompt').fill('Suite en conflit');
   await page.locator('#composer').evaluate(form=>form.requestSubmit());
   await page.getByText('Révision modifiée par un autre poste.',{exact:true}).waitFor();
   assert.equal(state.projectWrites,1);
   page.once('dialog',dialog=>dialog.accept());
   await page.getByRole('button',{name:'Relire la version enregistrée'}).click();
   await page.waitForFunction(()=>!document.querySelector('.project-conversation-switch button').disabled);
   assert.equal(await page.getByText('Suite en conflit',{exact:true}).count(),0);
   await page.getByText('Suite du fil enregistré',{exact:true}).waitFor();
   await page.locator('#prompt').fill('Question à interrompre');
   await page.locator('#composer').evaluate(form=>form.requestSubmit());
   await page.getByText('Fragment de réponse',{exact:true}).waitFor();
   await page.getByRole('button',{name:'Arrêter la réponse',exact:true}).click();
   await page.waitForFunction(()=>!document.querySelector('.project-conversation-switch button').disabled);
   assert.equal(await page.locator('#prompt').inputValue(),'Question à interrompre');
   assert.equal(state.projectWrites,1);
   await page.getByRole('button',{name:'Conversations personnelles'}).click();
   assert.equal(await page.locator('#prompt').inputValue(),'Brouillon personnel à préserver');
  }
  if(platform==='windows'||platform==='linux'){
   state.modernNavigation=true;
   await page.reload();await ready();
   managed.archived=false;
   await page.evaluate(async()=>{showView('projects');await wsRefresh();});
   assert.equal(await page.locator('#ws-open-portfolio').isVisible(),false);
   assert.deepEqual(await page.locator('#client-navigation .nav-button:visible').allTextContents(),['Conversations','Projets','Notes','Mails','Réunions','Activité']);
   assert.equal(await page.locator('.brand strong').textContent(),'Kiara');
   const navigationGeometry=await page.locator('#client-navigation [data-view-button="chat"]').evaluate(node=>{
    const box=node.getBoundingClientRect(),css=getComputedStyle(node);return {x:box.x,width:box.width,height:box.height,font:css.fontSize,padding:css.padding};
   });
   const settingsGeometry=await page.locator('.sidebar-settings [data-view-button="settings"]').evaluate(node=>{
    const box=node.getBoundingClientRect(),css=getComputedStyle(node);return {x:box.x,width:box.width,height:box.height,font:css.fontSize,padding:css.padding};
   });
   assert.deepEqual(settingsGeometry,navigationGeometry,'Le bouton Réglages conserve la même géométrie que la navigation.');
   assert.equal(await page.locator('.conversation-toolbar #new').count(),1);
   assert.equal(await page.locator('.conversation-history-menu #conversation-list').count(),1);
   state.managed='unavailable';await page.evaluate(()=>wsRefresh());
   assert.deepEqual(await page.locator('#client-navigation .nav-button:visible').allTextContents(),['Conversations','Projets','Notes','Mails','Réunions','Activité']);
   state.managed='ready';await page.evaluate(()=>wsRefresh());
   if(process.env.UI_PROOF_DIRECTORY){
    fs.mkdirSync(process.env.UI_PROOF_DIRECTORY,{recursive:true});
    const previousViewport=page.viewportSize();await page.evaluate(()=>showView('chat'));
    for(const [width,height] of (desktopAudit?[[1280,720],[1920,1080],[2560,1440]]:[[1440,900],[390,844]])){
      await page.setViewportSize({width,height});if(width<850)await sidebar();
      await page.screenshot({path:path.join(process.env.UI_PROOF_DIRECTORY,`${platform}-${width}x${height}.png`)});
      if(width<850)await page.evaluate(()=>uiCloseSidebar(false));
    }
    await page.setViewportSize({width:1280,height:720});
    await page.locator('.conversation-history-menu > summary').click();
    await page.screenshot({path:path.join(process.env.UI_PROOF_DIRECTORY,`${platform}-historique.png`)});
    await page.keyboard.press('Escape');assert.equal(await page.locator('.conversation-history-menu > summary').evaluate(el=>document.activeElement===el),true);
    await page.setViewportSize(previousViewport);
   }
   assert.equal(await page.locator('#client-navigation [data-view-button="notifications"]').count(),0);
   await page.locator('.workspace-top [data-view-button="notifications"]').click();
   await page.locator('[data-view="notifications"]:not([hidden])').waitFor();
   await page.route('**/app/projets',route=>route.fulfill({body:'Portefeuille de recette'}));
   await sidebar();await page.locator('[data-view-button="chat"]').click();
   const conversationId=await page.evaluate(()=>currentId);
   const draft='Brouillon à reprendre après le portefeuille';
   const chatUrl=page.url();
   state.failPreferences=true;
   await page.locator('#prompt').fill(draft);
   await sidebar();await page.locator('[data-view-button="projects"]').click();
   await page.getByText('Échec fictif de sauvegarde',{exact:false}).waitFor();
   assert.equal(page.url(),chatUrl);
   assert.equal(await page.locator('#prompt').inputValue(),draft);
   state.failPreferences=false;
   await page.locator('[data-view-button="projects"]').click();
   await page.waitForURL('**/app/projets');
   assert.equal(state.preferences.conversation_drafts[conversationId],draft);
   await page.goto(chatUrl);await ready();
   assert.equal(await page.locator('#prompt').inputValue(),draft);
   await page.route('**/app/settings',route=>route.fulfill({body:'Réglages Kiara de recette'}));
   await sidebar();await page.locator('[data-view-button="settings"]').click();
   await page.waitForURL('**/app/settings');
   await page.goto(chatUrl);await ready();
   state.failProjectSession=true;
   try {
    await sidebar();await page.locator('[data-view-button="settings"]').click();
    await page.locator('[data-view="access"]:not([hidden])').waitFor();
    assert(await page.locator('.settings-subnav').isVisible());
    await page.getByText('Le service Projets est indisponible.',{exact:false}).waitFor();
   }finally{state.failProjectSession=false;}
   assert.equal(state.preferences.conversation_drafts[conversationId],draft);
   await page.goto(new URL('/chat#reglages',chatUrl).href);await ready();
   await page.locator('[data-view="access"]:not([hidden])').waitFor();
   for(const [slug,title] of [['vocal','Conversation vocale'],['dictee','Dictée'],['notifications','Notifications']]){
     await page.goto(new URL('/chat#reglages-'+slug,chatUrl).href);
     await page.locator('.device-preferences').getByRole('heading',{name:title,exact:true}).waitFor();
     assert.equal(await page.locator('.settings-subnav').isVisible(),false);
     assert(await page.locator('#device-settings-back').isVisible());
     assert.equal(await page.locator('[data-view="chat"]').isVisible(),false);
   }
   await page.goto(chatUrl);await ready();assert.equal(await page.locator('#prompt').inputValue(),draft);
   const overviewPath='/app/projets/'+managed.id+'/vue-ensemble';
   await page.route('**'+overviewPath,route=>route.fulfill({body:'Vue d’ensemble du projet de recette'}));
   await sidebar();
   await page.evaluate(()=>uiCloseSidebar(false));
   await page.locator('.conversation-history-menu > summary').click();
   const projectGroup=page.locator('#ws-sidebar-projects details').filter({hasText:managed.title});
   await projectGroup.locator('summary').click();
   await projectGroup.getByRole('button',{name:'Ouvrir le projet',exact:true}).click();
   await page.waitForURL('**'+overviewPath);
   await page.goto(chatUrl);await ready();
   assert.equal(await page.locator('#prompt').inputValue(),draft);
   const meetingsPath='/app/projets/'+managed.id+'/reunions';
   await page.route('**'+meetingsPath,route=>route.fulfill({body:'Réunions du projet de recette'}));
   await page.locator('.workspace-top [data-view-button="notifications"]').click();
   await page.locator('#fred-inbox-list article').getByRole('button',{name:'Ouvrir',exact:true}).click();
   await page.waitForURL('**'+meetingsPath);
   const linkedConversation=new URL('/chat#projet='+managed.id,chatUrl).href;
   state.failProjectSession=true;
   await page.goto(linkedConversation);await ready();
   await page.getByText('Le service Projets est indisponible.',{exact:false}).waitFor();
   assert.equal(page.url(),linkedConversation);
   assert.equal(await page.locator('#prompt').inputValue(),draft);
   state.failProjectSession=false;
   await page.getByRole('button',{name:'Assistant de projet',exact:true}).click();
   const projectPicker=page.getByRole('combobox',{name:'Projet',exact:true});
   await projectPicker.waitFor();
   assert.equal(await projectPicker.inputValue(),'brain-recette');
   await openMenu(page,'.project-conversation-options');
   assert(await page.getByRole('checkbox',{name:'Éphémère'}).isChecked());
   await page.waitForURL(new URL('/chat',chatUrl).href);
   await page.getByRole('button',{name:'Conversations personnelles'}).click();
   assert.equal(await page.locator('#prompt').inputValue(),draft);
   await page.evaluate(()=>workspaceShowSources([{title:'Source de recette',agent_source_id:'source-recette',text:'Passage de recette'}]));
   await openMenu(page,'#ui-composer-options-menu');
   await page.getByRole('button',{name:'Sources · 1',exact:true}).click();
   await page.locator('#ws-side').getByRole('button',{name:'Voir la source',exact:true}).click();
   const citedSource=page.getByRole('dialog',{name:'Notice de recette'});
   await citedSource.getByText('Texte indexé de la notice.').waitFor();
   await citedSource.getByRole('button',{name:'Fermer',exact:true}).click();
   assert.equal(await page.locator('#prompt').inputValue(),draft);
   assert.equal(new URL(page.url()).pathname,'/chat');
  }
  if(platform==='windows'||platform==='linux'){
   // A portal change shares this local preference; an older server value must
   // not undo it when Conversations is reopened.
   state.preferences.sidebar_collapsed=true;
   await page.evaluate(()=>localStorage.setItem('fred-sidebar-collapsed','false'));
   await page.goto(new URL('/chat',page.url()).href);await ready();
   assert.equal(await page.evaluate(()=>document.body.classList.contains('sidebar-collapsed')),false);
   state.preferences.sidebar_collapsed=false;
   await page.goto(new URL('/chat#apparence',page.url()).href);
   const theme=page.getByLabel('Thème de l’interface');
   await theme.waitFor();
   assert(await page.locator('.device-preferences > h2').evaluate(node=>node===document.activeElement));
   await theme.selectOption('dark');
   await page.waitForFunction(()=>document.documentElement.dataset.theme==='dark'&&!uiPreferencesPending);
   assert.equal(state.preferences.theme,'dark');
  }
  if(platform==='windows'||platform==='linux'){
   await page.close();
   const corrections=Array.from({length:200},(_,index)=>({id:'fiction-'+index,title:'Correcteur · correction '+index,
    messages:[{role:'user',content:'Corriger :\n\nTexte ancien '+index},{role:'assistant',content:'Résultat ancien '+index}]}));
   state.historyOverride=state.history={conversations:corrections,currentId:corrections[0].id};
   state.preferences.corrector_text='Brouillon du correcteur à conserver';
   let release;state.historyGate=new Promise(resolve=>{release=resolve;});
   const recovered=await context.newPage();recovered.on('pageerror',e=>errors.push(e.message));
   try{
    await recovered.goto('http://127.0.0.1:'+server.address().port,{waitUntil:'domcontentloaded'});
    await recovered.waitForFunction(()=>!historyReady&&!uiDraftsLoaded);
    await recovered.evaluate(()=>uiPersistPreferences());
    assert.equal(state.preferences.corrector_text,'Brouillon du correcteur à conserver');
   }finally{state.historyGate=null;release();}
   await recovered.waitForFunction(()=>historyReady&&uiDraftsLoaded);
   assert.equal(await recovered.evaluate(()=>library.length),200,'La recette utilise un historique de 200 corrections.');
   assert.equal(await recovered.locator('#corrector-text').inputValue(),'Brouillon du correcteur à conserver','Une correction historique ne doit pas remplacer un brouillon pendant le démarrage.');
   await recovered.evaluate(()=>uiPersistPreferences());
   assert.equal(state.preferences.corrector_text,'Brouillon du correcteur à conserver');
   await recovered.close();
   delete state.preferences.corrector_text;
   const withoutDraft=await context.newPage();withoutDraft.on('pageerror',e=>errors.push(e.message));
   await withoutDraft.goto('http://127.0.0.1:'+server.address().port,{waitUntil:'domcontentloaded'});
   await withoutDraft.waitForFunction(()=>historyReady&&uiDraftsLoaded&&historyView==='corrector');
   assert.equal(await withoutDraft.locator('#corrector-text').inputValue(),'Texte ancien 0','Sans brouillon enregistré, la correction historique reste consultable.');
   await withoutDraft.close();
   state.preferences.corrector_text='Brouillon du correcteur à conserver';
   const chat={id:'chat-fictif',title:'Conversation fictive',messages:[]};
   state.historyOverride=state.history={conversations:[corrections[0],chat],currentId:corrections[0].id};
   state.preferences.conversation_drafts={[chat.id]:'Brouillon de conversation conservé'};
   state.stateGate=new Promise(resolve=>{release=resolve;});
   const delayed=await context.newPage();delayed.on('pageerror',e=>errors.push(e.message));
   try{
    await delayed.goto('http://127.0.0.1:'+server.address().port,{waitUntil:'domcontentloaded'});
    await delayed.waitForFunction(()=>historyReady&&!uiDraftsLoaded);
    assert.equal(await delayed.evaluate(()=>currentId),'fiction-0');
    assert.equal(await delayed.locator('#prompt').evaluate(node=>node.readOnly),true);
   }finally{state.stateGate=null;release();}
   await delayed.waitForFunction(()=>historyReady&&uiDraftsLoaded&&currentId==='chat-fictif');
   assert.equal(await delayed.locator('#prompt').inputValue(),'Brouillon de conversation conservé');
   assert.equal(await delayed.locator('#corrector-text').inputValue(),'Brouillon du correcteur à conserver');
   await delayed.close();
  }
  assert.deepEqual(errors,[]);console.log(JSON.stringify({platform,passed:true,scenarios:['per-conversation drafts and reload','failed persistence blocks silent reload','cleared draft stays cleared','instructions unload warning','memory edit survives refresh','delete cancel/error/success','named source dialog',...(desktopAudit?['desktop 720p through WQHD']:['drawer focus at 390 and 768','right-aligned send']),'one main landmark','project history and ephemeral privacy',...(platform!=='android'?['single project entry opens the current portfolio','shared appearance link']:[])]}));
 }finally{await context.close();await new Promise(r=>server.close(r));}
}
(async()=>{if(windowsShell)return check(null,'windows');const browser=await chromium.launch(options);try{if(!linuxOnly)await check(browser,'windows');if(linuxOnly)await check(browser,'linux');else if(!windowsOnly)await check(browser,'android');}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
