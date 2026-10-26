/* Shared Windows UI, deterministic native ASR and server PCM, delayed history. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http'),{execFileSync}=require('node:child_process');
const voiceSource=process.argv.find(value=>value.startsWith('--voice-source='))?.slice(15);
const root=__dirname,read=name=>fs.readFileSync(name==='conversation.js'&&voiceSource?voiceSource:path.join(root,name),'utf8');
const android=process.argv.includes('--android');
const preRestoreLow=process.argv.includes('--pre-restore-low');
const baseline=process.argv.includes('--baseline'),automaticReasoning=process.argv.includes('--automatic-reasoning'),config={key:'conversation-regression-local',model:'Kiara-test',version:'Windows-test',storage:'conversation-regression'};
const script=name=>{let source=baseline&&name==='conversation.js'?execFileSync('git',['show','0354e91:client-qwen/conversation.js'],{cwd:root,encoding:'utf8'}):read(name);if(preRestoreLow&&name==='conversation.js')source=source.replace("if(native.quality!=='max')return classicLowSplitSpeech(final);",'').replace("if(native.quality!=='max')return classicLowSpeak(text,token);",'').replace("if(quality.value==='low')return classicLowRefresh();",'').replace("options.hidden=quality.value==='low';",'');if(!baseline&&name==='conversation.js')source=source.replace('setInterval(refresh,200);refresh();','window.__qaVoice=()=>({listening:!responding()&&!native.capture_paused,ignoredSpeech,pendingTurns,firstSpeechQueued,speechBuffer,speechRunning,listenAfter});setInterval(refresh,200);refresh();');return '<script nonce="qa">'+source.replaceAll('</script','<\\/script')+'</script>';};
const renderHtml=()=>android?fs.readFileSync(path.join(root,'../client-android/app/src/main/assets/android-chat.html'),'utf8').replace('__CONFIG__',JSON.stringify({...config,platform:'android'})).replaceAll('__NONCE__','qa').replace('setInterval(refresh,200);refresh();','window.__qaVoice=()=>({listening:!responding()&&!native.capture_paused,ignoredSpeech,pendingTurns,speechRunning});setInterval(refresh,200);refresh();').replace('</head>',`<script nonce="qa">window.AndroidClient={conversationStatus(){return this.request()},conversationAction(body){return this.request(body)},request(body){const xhr=new XMLHttpRequest();xhr.open(body?'POST':'GET','/client/conversation',false);xhr.setRequestHeader('Authorization','Bearer ${config.key}');xhr.setRequestHeader('Content-Type','application/json');xhr.send(body||null);return xhr.responseText;},notificationReady(){},voiceStatus(){return JSON.stringify({phase:'idle',installed:true})},voiceAction(){return '{}'}};</script></head>`):read('chat.html').replace('__UI_CSS__',read('ui.css')).replace('__CONFIG__',JSON.stringify(config)).replaceAll('__NONCE__','qa')
  .replace('</head>',()=>script('vendor/markdown-it.min.js')+script('markdown.js')+'</head>')
  .replace('</body>',()=>read('workspace.html')+['ui.js','attachments.js','corrector.js','selection.js','thinking.js','voice.js','conversation.js'].map(script).join('')+'</body>');
const html=renderHtml();
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const webEvents=process.argv.includes('--web-events');
const maxVoice=process.argv.includes('--max');
const maxGpu=process.argv.includes('--max-gpu');
const maxInstall=process.argv.includes('--max-install')||maxGpu;
const maxStreaming=process.argv.includes('--max-stream');
async function until(work,label){for(let i=0;i<400;i++){if(await work())return;await sleep(25);}throw new Error('Timeout: '+label);}

async function main(){
  const {chromium,options}=require('./browser_test_support.cjs');
  const browser=process.argv.includes('--preview')?null:await chromium.launch(options);
  const state={history:null,revision:'1',preferences:{},native:{phase:'idle',installed:true,aec_supported:!process.argv.includes('--no-aec'),session:'',speech_id:0,partial:'',turns:[]},calls:[],chats:[],runs:new Map(),syncDelay:0,syncActive:0,acks:[],stops:0,cancels:[],voiceCancels:[],speech:[],timers:new Set(),holdChat:false,longVoice:false,pendingChat:null,delayedReply:false,failStop:false};
  if(process.argv.includes('--voice-workspace'))state.preferences={voice_animation_style:'constellation'};
  if(maxGpu){
    state.installation={phase:'ready',hardware:{checked:true,eligible:true,cards:[{vendor:'amd',name:'AMD Radeon Graphics'},{vendor:'amd',name:'AMD Radeon RX 7800 XT'}]}};
    state.gpuCards=[{id:'a'.repeat(24),name:'Vulkan0',description:'AMD Radeon Graphics',kind:'integrated',total_bytes:64*2**30,free_bytes:48*2**30},
                    {id:'b'.repeat(24),name:'Vulkan1',description:'AMD Radeon RX 7800 XT',kind:'dedicated',total_bytes:16*2**30,free_bytes:2*2**30}];
    state.maxPC={installed:true,available:true,progressive:true,message:'Max installé',device_loaded:false,gpu:{supported:true,selection:'auto',checked:false,cards:[],error:''}};
  }
  const json=(res,value,status=200)=>{res.writeHead(status,{'Content-Type':'application/json; charset=utf-8'});res.end(JSON.stringify(value));};
  const event=(res,value)=>{if(!res.destroyed&&!res.writableEnded)res.write('data: '+JSON.stringify(value)+'\n\n');};
  const later=(work,ms)=>{const timer=setTimeout(()=>{state.timers.delete(timer);work();},ms);state.timers.add(timer);};
  const server=http.createServer(async(req,res)=>{
    let raw='';for await(const chunk of req)raw+=chunk;const body=JSON.parse(raw||'{}');
    if(req.url==='/'){res.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});return res.end(process.argv.includes('--preview')?renderHtml():html);}
    state.calls.push({path:req.url,body,requestId:req.headers['x-qwen-request']});
    if(req.headers.authorization!=='Bearer '+config.key)return json(res,{error:{message:'Unauthorized'}},401);
    if(process.argv.includes('--preview')&&req.url==='/__fixture'){
      if(body.native)Object.assign(state.native,body.native);
      if(body.workspace)state.workspace=body.workspace;
      if(body.installation)state.installation=body.installation;
      if(body.maxPC)state.maxPC=body.maxPC;
      for(const name of ['holdChat','longVoice','failSpeech','failModels','failStop'])if(typeof body[name]==='boolean')state[name]=body[name];
      if(body.completeReply&&state.pendingChat){const pending=state.pendingChat;event(pending.res,{choices:[{delta:{content:'La livraison du projet Orion est prévue le 23 novembre.'},finish_reason:'stop'}]});pending.res.end('data: [DONE]\n\n');state.pendingChat=null;}
      return json(res,{native:state.native});
    }
    if(req.url==='/client/state')return json(res,{version:'test',preferences:state.preferences,update:{message:'À jour',available:false,busy:false},endpoint:'https://example.test',internet_endpoint:'example.test:51820',local_api:'http://127.0.0.1/v1',key:config.key,history:{message:'Copie locale enregistrée',needs_merge:false},connection:{connected:true,model:'Kiara-test',transport:'https',endpoint:'https://example.test',checked_at:Date.now()/1000}});
    if(req.url==='/client/history'&&req.method==='GET')return json(res,{history:state.history,revision:state.revision});
    if(req.url==='/client/history/sync'){state.syncActive++;await sleep(state.syncDelay);state.history=state.history||body.initial;state.syncActive--;return json(res,{history:state.history,revision:state.revision,message:'Synchronisé'});}
    if(req.url==='/client/history'&&state.failHistory)return json(res,{error:{message:'Historique temporairement indisponible'}},503);
    if(req.url==='/client/history'){state.history=body.history;state.revision=String(Number(state.revision)+1);return json(res,{saved:true,revision:state.revision});}
    if(req.url==='/client/preferences'){
      if(state.failPreferences)return json(res,{error:{message:'Enregistrement indisponible'}},503);
      const drafts={...state.preferences.conversation_drafts};
      for(const [id,text] of Object.entries(body.conversation_drafts||{})){if(text)drafts[id]=text;else delete drafts[id];}
      state.preferences={...state.preferences,...body,conversation_drafts:drafts};return json(res,{saved:true});
    }
    if(req.url==='/client/voice/max'&&maxInstall)return json(res,{pc:{installed:state.installation?.phase==='ready',available:state.installation?.phase==='ready',progressive:true,message:'Mode Max non installé',...state.maxPC},server:{installed:false,available:false,message:'Mode Max non installé'},installation:state.installation||{phase:'idle',hardware:{checked:true,eligible:true,cards:[{vendor:'amd',name:'AMD Radeon RX 7800 XT'}]}}});
    if(req.url==='/client/voice/max/open-folder'){assert.deepEqual(body,{});return json(res,{opened:true});}
    if(req.url==='/client/voice/max/remove'){
      assert.deepEqual(body,{confirm:true});
      if(state.failRemove)return json(res,{error:{message:'Un fichier Max est encore utilisé. Fermez les autres clients Kiara puis réessayez.'}},400);
      state.installation={...state.installation,phase:'idle',message:'Tous les fichiers Max ont été supprimés.',storage:{...state.installation.storage,exists:false,bytes:0}};
      state.maxPC=null;return json(res,state.installation);
    }
    if(req.url==='/client/voice/max/devices'){
      assert.deepEqual(body,{});state.maxPC.gpu={...state.maxPC.gpu,checked:true,cards:state.gpuCards,recommended:state.gpuCards.find(card=>card.kind==='dedicated')?.id||state.gpuCards[0]?.id,error:''};return json(res,state.maxPC);
    }
    if(req.url==='/client/voice/max/gpu'){
      assert.deepEqual(Object.keys(body),['device']);
      if(state.failGpu)return json(res,{error:{message:'Enregistrement temporairement indisponible.'}},503);
      assert(body.device==='auto'||state.gpuCards.some(card=>card.id===body.device));
      state.maxPC={...state.maxPC,device:null,device_loaded:false,gpu:{...state.maxPC.gpu,selection:body.device}};return json(res,state.maxPC);
    }
    if(req.url==='/client/voice/max/plan')return json(res,{plan:'fixture-plan',download_bytes:1876042928,required_disk_bytes:2400000000,reused_bytes:679801808});
    if(req.url==='/client/voice/max/install'){
      assert.equal(body.plan,'fixture-plan');state.installation={phase:'downloading',downloaded_bytes:250000000,download_bytes:1876042928,message:'Téléchargement de Max…',hardware:{checked:true,eligible:true,cards:[{vendor:'amd',name:'AMD Radeon RX 7900 XT'}]}};return json(res,state.installation);
    }
    if(req.url==='/client/voice/max/install-cancel'){state.installation={...state.installation,phase:'cancelled',message:'Installation Max arrêtée. Vous pouvez la relancer.'};return json(res,state.installation);}
    if(req.url==='/client/voice/max')return json(res,process.argv.includes('--max-unavailable')?{pc:{installed:false,available:false,message:'Mode Max non installé'},server:{installed:true,available:false,message:'Mode Max trop lent sur cet appareil. Low est conseillé.'}}:{pc:{installed:true,available:true,latency_ms:1200,message:'Mode Max prêt'},server:{installed:true,available:true,latency_ms:600,message:'Mode Max prêt'}});
    if(req.url==='/client/draft')return json(res,{draft:null});
    if(req.url==='/client/integrations')return json(res,{apps:[]});
    if(req.url==='/client/voice')return json(res,{phase:'idle',installed:false});
    if(req.url==='/client/conversation'){
      if(body.action==='playback'){assert.equal(body.session,state.native.session);assert.equal(typeof body.playing,'boolean');state.native.playback_paused=body.playing&&!body.interruptions;if(android)state.native.microphone_closed=state.native.muted||state.native.playback_paused;else state.native.capture_paused=state.native.playback_paused;}
      if(body.action==='start')state.native={...state.native,phase:'listening',session:'qa-conversation',turns:[],speech_id:0,muted:false,microphone_closed:false,mute_pending:false,quality:body.quality||'low',execution:body.execution==='auto'?'server':body.execution||'pc'};
      if(body.action==='start'&&body.quality==='max'&&maxGpu){state.maxPC.device=state.gpuCards.find(card=>card.id===(state.maxPC.gpu.selection==='auto'?state.maxPC.gpu.recommended:state.maxPC.gpu.selection));state.maxPC.device_loaded=true;}
      if(body.action==='mute'){
        assert.equal(body.session,state.native.session);assert.equal(typeof body.muted,'boolean');
        if(state.failMute){state.failMute=false;return json(res,{error:{message:'État du microphone non modifié. Réessayez.'}},503);}
        state.native={...state.native,muted:body.muted,microphone_closed:body.muted,mute_pending:false,partial:''};
      }
      if(body.action==='ack'){assert.equal(body.session,state.native.session);state.acks.push(body.turn);state.native.turns=state.native.turns.filter(turn=>turn.id>body.turn);}
      if(body.action==='stop'){assert.equal(body.session,state.native.session);if(state.failStop){state.failStop=false;return json(res,{error:{message:'Raccrochage temporairement indisponible'}},503);}state.stops++;state.native={...state.native,phase:'stopped',turns:[],partial:'',muted:false,microphone_closed:true,mute_pending:false};}
      return json(res,state.native);
    }
    if(req.url==='/v1/models'&&state.failModels)return json(res,{error:{code:'connection_error',message:'Connexion temporairement indisponible'}},503);
    if(req.url==='/v1/models')return json(res,{source:'hermes',default_model:'Kiara-test',data:[{id:'Kiara-test',provider:'Qwen local',name:'Modèle local',available:true,capabilities:{images:false,thinking:true,reasoning_efforts:['none','low','medium','high']}},{id:'fred-test-cloud',name:'Modèle vocal choisi',provider:'Cloud de test',available:true,capabilities:{vision:false,thinking:true,reasoning_mode:automaticReasoning?'none':'effort',reasoning_efforts:automaticReasoning?[]:['none','xhigh','max']}}]});
    if(req.url==='/v1/status')return json(res,{protocol:3,agent_protocol:4,version:'test'});
    if(req.url==='/v1/workspace')return json(res,state.workspace||{projects:[],jobs:[]});
    if(req.url==='/v1/notifications')return json(res,{items:[],unread:0});
    if(req.url==='/v1/context')return json(res,{tokens:15,capacity:4096,estimated:true});
    if(req.url==='/v1/agent/action')return json(res,state.runs.get(body.request_id)||{request_id:body.request_id,conversation_id:body.conversation_id,status:'unknown'});
    if(req.url==='/v1/voice/status')return json(res,{ready:true,enabled:true});
    if(['/v1/voice/cancel','/client/voice/max/cancel'].includes(req.url)){if(req.url.includes('/max/'))assert.equal(body.session,state.native.session);state.voiceCancels.push(body.request_id);return json(res,{cancelled:true});}
    if(['/v1/voice/speech','/client/voice/max/speech'].includes(req.url)){
      if(req.url.includes('/max/'))assert.equal(body.session,state.native.session);
      if(state.failSpeech){state.failSpeech=false;return json(res,{error:{message:'Lecture temporairement interrompue'}},503);}
      state.speech.push({id:body.request_id,text:body.text});res.writeHead(200,{'Content-Type':'text/event-stream; charset=utf-8'});
      if(state.failAfterPCM){state.failAfterPCM=false;for(let i=0;i<5;i++)event(res,{id:body.request_id,rate:24000,pcm:Buffer.alloc(4800*2).toString('base64')});res.end();return;}
      const pcm=Buffer.alloc(4800*2).toString('base64'),frames=state.voiceFrames||(state.longVoice?30:3);
      for(let i=0;i<frames;i++)later(()=>event(res,{id:body.request_id,rate:24000,pcm}),50+i*30);
      later(()=>{event(res,{id:body.request_id,done:true});if(!res.destroyed&&!res.writableEnded)res.end();},50+frames*30);return;
    }
    if(req.url==='/v1/cancel'){
      assert.equal(body.voice_conversation,true);state.cancels.push(req.headers['x-qwen-request']);const pending=state.pendingChat;
      if(pending&&pending.body.turn_id===req.headers['x-qwen-request']){state.runs.set(pending.body.turn_id,{request_id:pending.body.turn_id,conversation_id:pending.body.conversation_id,status:'cancelled',text:''});if(!pending.res.destroyed&&!pending.res.writableEnded)pending.res.end('data: [DONE]\n\n');state.pendingChat=null;}
      return json(res,{cancelled:true});
    }
    if(req.url==='/v1/chat/completions'){
      assert.equal(body.model,'Kiara-test','Native ASR must keep the chosen local model');assert.equal(body.voice_conversation,true,'Oral requests must bypass Hermes');
      assert.equal(body.reasoning_effort,'none','Oral replies disable thinking without changing the written-chat preference');
      assert.equal(body.turn_id,req.headers['x-qwen-request']);state.chats.push(body);if(!body.voice_conversation)state.runs.set(body.turn_id,{request_id:body.turn_id,conversation_id:body.conversation_id,status:'running',text:''});
      res.writeHead(200,{'Content-Type':'text/event-stream; charset=utf-8'});event(res,{hermes_status:{phase:'working',message:'Hermes prépare la réponse'}});
      event(res,{voice_context:{capacity:16384,input_tokens:480,output_tokens:512,omitted_messages:0}});
      if(webEvents){event(res,{hermes_status:{phase:'tool',message:'Recherche sur Internet…'}});event(res,{workspace_sources:[{url:'https://example.org/source',title:'Source publique',text:'Passage vérifié.',origin:'hermes-web',retrieved:true}]});}
      if(state.holdChat){state.pendingChat={body,res};return;}
      if(state.prefixReply){event(res,{choices:[{delta:{content:'Je vous propose une courte réponse pour commencer, '}}]});later(()=>{event(res,{choices:[{delta:{content:'puis nous préciserons les détails.'},finish_reason:'stop'}]});if(!res.destroyed&&!res.writableEnded)res.end('data: [DONE]\n\n');},1800);return;}
      if(state.delayedReply){event(res,{choices:[{delta:{content:'Oui. '}}]});later(()=>{event(res,{choices:[{delta:{content:'Je t’entends bien.'}}]});event(res,{choices:[{delta:{},finish_reason:'stop'}]});if(!res.destroyed&&!res.writableEnded)res.end('data: [DONE]\n\n');},1800);return;}
      later(()=>{const text=state.chats.length===1?'La livraison du projet Orion est prévue le 23 novembre.':'Le budget du projet Orion est de 4200 euros.';state.runs.set(body.turn_id,{request_id:body.turn_id,conversation_id:body.conversation_id,status:'completed',text,reasoning_content:'',sources:[]});event(res,{choices:[{delta:{content:text}}]});event(res,{hermes_run:{request_id:body.turn_id,conversation_id:body.conversation_id,status:'completed'}});event(res,{choices:[{delta:{},finish_reason:'stop'}]});if(!res.destroyed&&!res.writableEnded)res.end('data: [DONE]\n\n');},150);return;
    }
    return json(res,{});
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  if(process.argv.includes('--preview')){
    console.log('Isolated voice fixture: http://127.0.0.1:'+server.address().port);
    await new Promise(()=>{});
  }
  let page,snapshot;
  try{
    page=await browser.newPage({viewport:android?{width:390,height:844}:{width:1440,height:1000}});const errors=[];page.on('pageerror',error=>errors.push(error.message));
    await page.addInitScript(()=>{
      window.__audio={started:0,ended:0,stopped:0,gain:1,analysed:0};
      window.AudioContext=class{
        constructor(){this.origin=performance.now();this.destination={};}
        get currentTime(){return (performance.now()-this.origin)/1000;}
        async resume(){}async close(){}
        createGain(){const gain={get value(){return window.__audio.gain;},set value(value){window.__audio.gain=value;}};return {gain,connect(){}};}
        createAnalyser(){return {fftSize:256,connect(){},getByteTimeDomainData(values){window.__audio.analysed++;for(let i=0;i<values.length;i++)values[i]=128+Math.round(Math.sin(i)*24*window.__audio.gain);}};}
        createBuffer(_channels,length,rate){const values=new Float32Array(length);return {duration:length/rate,getChannelData(){return values;}};}
        createBufferSource(){const context=this,source={connect(){},start(time){window.__audio.started++;this.timer=setTimeout(()=>{window.__audio.ended++;this.onended?.();},Math.max(0,(time-context.currentTime+this.buffer.duration)*1000));},stop(){clearTimeout(this.timer);window.__audio.stopped++;this.onended?.();}};return source;}
      };
    });
    const voiceUI={};
    async function revealVoiceControl(selector){
      if(!await page.locator('#voice-settings-dialog').count())return;
      const inside=await page.evaluate(sel=>!!document.querySelector(sel)?.closest('#voice-settings-dialog'),selector);
      const opened=await page.locator('#voice-settings-dialog').evaluate(el=>el.open);
      if(inside&&!opened)await page.locator('#voice-settings-toggle').click();
      if(!inside&&opened)await page.locator('#voice-settings-close').click();
    }
    for(const name of ['click','selectOption','check','uncheck','focus','fill'])voiceUI[name]=async(selector,...args)=>{
      await revealVoiceControl(selector);return page.locator(selector)[name](...args);
    };
    await page.goto('http://127.0.0.1:'+server.address().port);await page.waitForFunction(()=>!document.getElementById('conversation-start')?.disabled);
    if(process.argv.includes('--realtime-loop'))return await require('./voice_realtime_checks.cjs')({page,state,errors,until,sleep,event,voiceUI});
    if(process.argv.includes('--assistant-integration'))return await require('./assistant_ui_checks.cjs')({page,state,android,errors});
    if(process.argv.includes('--assistant-media'))return await require('./assistant_media_checks.cjs')({page,state,android,errors,voiceUI});
    if(process.argv.includes('--voice-workspace'))return await require('./voice_workspace_checks.cjs')({page,state,android,errors,until,sleep,event});
    if(maxGpu){
      await voiceUI.click('[data-view-button="voice"]');await voiceUI.selectOption('#voice-quality','max');
      await page.waitForFunction(()=>document.getElementById('voice-gpu-status').textContent.includes('En automatique : AMD Radeon RX 7800 XT'));
      assert.equal(await page.inputValue('#voice-gpu'),'auto');
      assert.match(await page.locator('#voice-gpu option').filter({hasText:'RX 7800 XT'}).textContent(),/dédiée · 16 Go/);
      assert.match(await page.locator('#voice-gpu option').filter({hasText:'Radeon Graphics'}).textContent(),/intégrée · mémoire partagée/);
      await voiceUI.selectOption('#voice-execution','pc');
      await voiceUI.selectOption('#voice-gpu','b'.repeat(24));await page.waitForFunction(()=>document.getElementById('voice-gpu-status').textContent.includes('Choisie : AMD Radeon RX 7800 XT'));
      assert.equal(state.maxPC.gpu.selection,'b'.repeat(24));
      await voiceUI.selectOption('#voice-animation-style','constellation');await page.evaluate(()=>uiPreferencesWrites);assert.equal(state.maxPC.gpu.selection,'b'.repeat(24));
      await voiceUI.click('#conversation-start');await page.waitForFunction(()=>window.conversationBusy);
      await page.waitForFunction(()=>document.getElementById('voice-gpu-status').textContent.includes('Utilisée : AMD Radeon RX 7800 XT'));
      assert.equal(await page.isDisabled('#voice-gpu'),true);assert.equal(await page.isDisabled('#voice-gpu-refresh'),true);
      await voiceUI.click('#conversation-start');await page.waitForFunction(()=>!window.conversationBusy);
      state.gpuCards.reverse();await voiceUI.click('#voice-gpu-refresh');await page.waitForFunction(()=>!document.getElementById('voice-gpu').disabled);
      assert.equal(await page.inputValue('#voice-gpu'),'b'.repeat(24),'Enumeration order must not replace the saved GPU');
      state.failGpu=true;await voiceUI.selectOption('#voice-gpu','a'.repeat(24));await page.waitForFunction(()=>document.getElementById('voice-gpu-status').textContent.includes('Carte non modifiée'));
      assert.equal(await page.inputValue('#voice-gpu'),'b'.repeat(24));assert.equal(state.maxPC.gpu.selection,'b'.repeat(24));state.failGpu=false;
      await voiceUI.selectOption('#voice-gpu','a'.repeat(24));await page.waitForFunction(()=>document.getElementById('voice-gpu-status').textContent.includes('Choisie : AMD Radeon Graphics'));
      await voiceUI.selectOption('#voice-gpu','b'.repeat(24));await page.waitForFunction(()=>!document.getElementById('voice-gpu').disabled);await page.evaluate(()=>uiPreferencesWrites);
      await page.reload();await page.waitForFunction(()=>!document.getElementById('conversation-start')?.disabled);await voiceUI.click('[data-view-button="voice"]');
      await page.waitForFunction(()=>document.getElementById('voice-gpu').value==='b'.repeat(24));
      state.gpuCards=state.gpuCards.filter(card=>card.kind!=='dedicated');await voiceUI.click('#voice-gpu-refresh');await page.waitForFunction(()=>document.getElementById('voice-gpu-status').textContent.includes('introuvable'));
      assert.equal(state.maxPC.gpu.selection,'b'.repeat(24));assert.equal(await page.inputValue('#voice-gpu'),'b'.repeat(24),'A missing adapter cannot silently switch to the integrated GPU');
      await voiceUI.selectOption('#voice-gpu','auto');await page.waitForFunction(()=>!document.getElementById('voice-gpu').disabled);
      await voiceUI.selectOption('#voice-execution','server');assert.equal(await page.isVisible('#voice-gpu'),false);
      await voiceUI.selectOption('#voice-quality','low');assert.equal(await page.isVisible('#voice-gpu'),false);assert.equal(await page.isVisible('#conversation-interruptions'),true);
      state.maxPC.gpu.supported=false;state.maxPC.update_recommended=true;await voiceUI.selectOption('#voice-quality','max');await voiceUI.selectOption('#voice-execution','pc');
      await page.waitForFunction(()=>document.getElementById('voice-gpu-status').textContent.includes('Mettez le complément Max à jour'));
      assert.equal(await page.isDisabled('#voice-gpu'),true);assert.equal(await page.textContent('#voice-max-plan'),'Mettre à jour Max');
      assert.deepEqual(errors,[]);console.log(JSON.stringify({passed:true,checks:['dedicated automatic recommendation','explicit choice and real loaded adapter','locked during a call','persistent choice across reordering and reload','save failure and retry','manual integrated choice allowed','no silent fallback if selected GPU disappears','Low/interruption/animation preserved','server has independent GPU settings','old pack update is explained']}));return;
    }
    if(process.argv.includes('--interruptions')){
      const noAEC=process.argv.includes('--no-aec');
      const enter=async()=>{if(android)await voiceUI.click('#ui-sidebar-toggle');await voiceUI.click('[data-view-button="voice"]');};
      const recognize=(speech,turn,text,partial='')=>Object.assign(state.native,{speech_id:speech,partial_speech_id:speech,partial,turns:turn?[{id:turn,speech_id:speech,text}]:[]});
      await enter();if(maxVoice){await voiceUI.selectOption('#voice-quality','max');await voiceUI.selectOption('#voice-execution','pc');}
      assert.equal(await page.isVisible('#conversation-interruptions'),true,'The interruption choice must be visible in Low and Max');
      assert.equal(await page.isChecked('#conversation-interruptions'),false);
      if(noAEC){assert.equal(await page.isDisabled('#conversation-interruptions'),true);assert.match(await page.textContent('#voice-interruptions-note'),/Cet appareil/);}
      else assert.match(await page.textContent('#voice-interruptions-note'),/termine sa réponse/);
      await voiceUI.selectOption('#voice-animation-style','constellation');assert.equal(await page.isChecked('#conversation-interruptions'),false);
      state.holdChat=true;state.voiceFrames=8;state.syncDelay=2400;
      await voiceUI.click('#conversation-start');await page.waitForFunction(()=>window.conversationBusy);
      recognize(1,1,'Une réponse à laisser terminer.');await until(()=>!!state.pendingChat,'protected answer starts');
      const held=state.pendingChat,firstTurn=held.body.turn_id,cancelCount=state.cancels.length,voiceCancelCount=state.voiceCancels.length;
      recognize(2,2,'Un bruit pendant la réflexion.','Stop');await until(()=>state.acks.includes(2),'speech during calculation discarded');
      assert.equal(state.cancels.length,cancelCount);assert.equal(state.chats.length,1);assert.equal(await page.evaluate(()=>busy),true);
      state.holdChat=false;state.native.partial='';state.pendingChat=null;
      event(held.res,{choices:[{delta:{content:'Cette réponse doit être lue jusqu’au dernier mot.'},finish_reason:'stop'}]});held.res.end('data: [DONE]\n\n');
      await page.waitForFunction(()=>window.__audio.started>0);const stoppedAudio=await page.evaluate(()=>window.__audio.stopped);
      recognize(3,3,'Une parole qui ne doit pas couper Kiara.','Non attends');await until(()=>state.acks.includes(3),'speech during playback discarded');
      assert.equal(state.voiceCancels.length,voiceCancelCount);assert.equal(state.cancels.length,cancelCount);assert.equal(state.chats.length,1);
      assert.equal(await page.evaluate(()=>window.__audio.stopped),stoppedAudio);
      if(android){const playback=state.calls.filter(call=>call.body.action==='playback'&&call.body.playing);assert(playback.length>0);assert(playback.every(call=>call.body.interruptions===false),'Android must pause capture when interruption is disabled');}
      state.native.partial='';await page.waitForFunction(()=>document.querySelector('.voice-view').dataset.state==='listening'&&!window.__qaVoice().speechRunning);
      if(maxVoice)await page.waitForFunction(()=>window.__qaVoice().listening);
      assert.equal(await page.evaluate(()=>messages.find(m=>m.role==='assistant').content),'Cette réponse doit être lue jusqu’au dernier mot.');
      recognize(3,4,'Une transcription arrivée en retard.');await until(()=>state.acks.includes(4),'late speech discarded');assert.equal(state.chats.length,1);
      recognize(4,5,'Oui');await until(()=>state.chats.length===2,'first short reply after playback is accepted');
      assert.equal(state.chats[1].messages.at(-1).content,'Oui');assert(!state.cancels.includes(firstTurn));
      await page.waitForFunction(()=>!busy&&!historySyncPending&&!window.__qaVoice().speechRunning);state.syncDelay=0;
      await voiceUI.click('#conversation-start');await page.waitForFunction(()=>!window.conversationBusy);
      await page.reload();await page.waitForFunction(()=>!document.getElementById('conversation-start')?.disabled);await enter();
      assert.equal(await page.isVisible('#conversation-interruptions'),true);assert.equal(await page.isChecked('#conversation-interruptions'),false);
      if(!noAEC){
        await voiceUI.check('#conversation-interruptions');await page.evaluate(()=>uiPreferencesWrites);state.holdChat=true;
        await voiceUI.click('#conversation-start');await page.waitForFunction(()=>window.conversationBusy);
        recognize(1,1,'Une nouvelle réponse à interrompre.');await until(()=>!!state.pendingChat,'interruptible answer starts');const turn=state.pendingChat.body.turn_id;
        recognize(2,0,'','Non attends');await until(()=>state.cancels.includes(turn),'enabled interruption cancels calculation');
        await page.waitForFunction(()=>!busy&&!historySyncPending);state.holdChat=false;
        const audioCount=await page.evaluate(()=>window.__audio.started);recognize(2,2,'Voici ma nouvelle question.');await page.waitForFunction(count=>window.__audio.started>count,audioCount);
        const speech=state.speech.at(-1).id;recognize(3,3,maxVoice?'Non attends':'Oui');await until(()=>state.voiceCancels.includes(speech),'enabled interruption cancels playback');
        await voiceUI.click('#conversation-start');await page.waitForFunction(()=>!window.conversationBusy);
        await voiceUI.selectOption('#voice-animation-style','orb');await page.evaluate(()=>uiPreferencesWrites);assert.equal(state.preferences.voice_interruptions,true);
        await page.reload();await page.waitForFunction(()=>!document.getElementById('conversation-start')?.disabled);await enter();assert.equal(await page.isChecked('#conversation-interruptions'),true);
      }
      assert.deepEqual(errors,[]);console.log(JSON.stringify({passed:true,platform:android?'android':'windows',quality:maxVoice?'max':'low',aec:!noAEC,checks:['option visible and disabled by default','animation keeps choice','protected calculation','complete playback without cancellation','late recognition discarded','next short reply accepted','choice survives reload',...(noAEC?['capture protection without AEC']:['enabled interruption during calculation and playback','enabled choice survives reload'])]}));return;
    }
    if(process.argv.includes('--animation')){
      const enter=async()=>{if(android)await voiceUI.click('#ui-sidebar-toggle');await voiceUI.click('[data-view-button="voice"]');};
      const picture=()=>page.evaluate(()=>document.getElementById('voice-constellation').toDataURL());
      await enter();assert.equal(await page.inputValue('#voice-animation-style'),'waves');await voiceUI.selectOption('#voice-animation-style','orb');
      const oldHeight=await page.locator('.voice-orb').evaluate(el=>el.getBoundingClientRect().height);
      await voiceUI.focus('#voice-animation-style');await page.keyboard.press('End');await page.keyboard.press('Enter');await page.evaluate(()=>uiPreferencesWrites);
      assert.equal(state.preferences.voice_animation_style,'constellation');
      assert.equal(await page.isVisible('.voice-orb svg'),false);assert.equal(await page.isVisible('#voice-constellation'),true);
      assert.equal(await page.locator('.voice-orb').evaluate(el=>el.getBoundingClientRect().height),oldHeight,'Switching animations keeps the stage height');
      await page.reload();await page.waitForFunction(()=>!document.getElementById('conversation-start')?.disabled);await enter();
      assert.equal(await page.inputValue('#voice-animation-style'),'constellation');
      await voiceUI.click('#conversation-start');await page.waitForFunction(()=>document.querySelector('.voice-view').dataset.state==='listening');
      const listen=await picture();await sleep(150);assert.notEqual(await picture(),listen,'Constellation moves during listening');
      await page.evaluate(()=>{window.__paintFrames=0;const clear=CanvasRenderingContext2D.prototype.clearRect;CanvasRenderingContext2D.prototype.clearRect=function(...args){window.__paintFrames++;return clear.apply(this,args);};});
      await voiceUI.click('#voice-back');const hiddenFrames=await page.evaluate(()=>window.__paintFrames);await sleep(400);assert.equal(await page.evaluate(()=>window.__paintFrames),hiddenFrames,'Leaving Vocal stops rendering');await voiceUI.click('#voice-ongoing');
      await voiceUI.uncheck('#voice-animation');await page.evaluate(()=>uiPreferencesWrites);const paused=await picture();await sleep(250);assert.equal(await picture(),paused,'Disabled movement freezes the canvas');
      await voiceUI.check('#voice-animation');await page.evaluate(()=>uiPreferencesWrites);await page.emulateMedia({reducedMotion:'reduce'});await sleep(100);
      const reduced=await picture();await sleep(250);assert.equal(await picture(),reduced,'Reduced motion freezes the canvas');
      await page.emulateMedia({reducedMotion:'no-preference'});
      state.native.speech_id=1;state.native.partial_speech_id=1;state.native.partial='Un essai vocal';
      await page.waitForFunction(()=>document.querySelector('.voice-view').dataset.state==='hearing');
      state.holdChat=true;state.native.partial='';state.native.turns=[{id:1,speech_id:1,text:'Quel jour aura lieu la livraison ?'}];
      await until(()=>!!state.pendingChat,'Animation fixture waits for a reply');
      await page.waitForFunction(()=>document.querySelector('.voice-view').dataset.state==='thinking');
      const thinking=await picture();await sleep(150);assert.notEqual(await picture(),thinking);
      state.longVoice=true;const pending=state.pendingChat;state.pendingChat=null;
      event(pending.res,{choices:[{delta:{content:'La livraison du projet Orion est prévue le 23 novembre.'},finish_reason:'stop'}]});pending.res.end('data: [DONE]\n\n');
      await page.waitForFunction(()=>document.querySelector('.voice-view').dataset.state==='speaking');
      await sleep(120);assert(await page.evaluate(()=>window.__audio.analysed>0),'Speech animation samples the output audio');
      const beforeDark=await picture();await page.evaluate(()=>uiSetTheme('dark'));await sleep(250);assert.notEqual(await picture(),beforeDark);
      assert.equal(await page.evaluate(()=>document.body.scrollWidth<=innerWidth),true);
      await voiceUI.selectOption('#voice-animation-style','orb');assert.equal(await page.isVisible('#voice-constellation'),false);assert.equal(await page.isVisible('.voice-orb svg'),true);
      assert.equal(await page.evaluate(()=>window.conversationBusy),true,'Animation choice never interrupts the call');
      await voiceUI.selectOption('#voice-animation-style','constellation');await page.evaluate(()=>uiPreferencesWrites);
      await voiceUI.click('#conversation-start');await page.waitForFunction(()=>!window.conversationBusy);
      state.failPreferences=true;await voiceUI.selectOption('#voice-animation-style','orb');
      await page.waitForFunction(()=>!document.getElementById('voice-preferences-retry').hidden);
      assert.match(await page.textContent('#voice-preferences-status'),/non enregistrés/);
      state.failPreferences=false;await voiceUI.click('#voice-preferences-retry');await page.waitForFunction(()=>document.getElementById('voice-preferences-retry').hidden);
      assert.equal(state.preferences.voice_animation_style,'orb');
      await voiceUI.selectOption('#voice-animation-style','constellation');await voiceUI.uncheck('#voice-animation');await page.evaluate(()=>uiPreferencesWrites);
      await page.reload();await page.waitForFunction(()=>!document.getElementById('conversation-start')?.disabled);await enter();
      assert.equal(await page.inputValue('#voice-animation-style'),'constellation');assert.equal(await page.isChecked('#voice-animation'),false);
      assert.deepEqual(errors,[]);console.log(JSON.stringify({passed:true,platform:android?'android':'windows',checks:['keyboard choice','one animation visible','stable stage','preference reload','listening/hearing/thinking/speaking','output PCM amplitude','pause and reduced motion','theme and overflow','switch during call','failed save and retry','paused preference reload']}));return;
    }
    if(!maxVoice&&!maxInstall&&!maxStreaming&&!baseline){
      assert(await page.isVisible('#voice-start'),'Dictation stays in chat');
      assert(!(await page.isVisible('#conversation-start')),'Vocal has its own page');
      if(android)await voiceUI.click('#ui-sidebar-toggle');
      await voiceUI.click('[data-view-button="voice"]');
      assert.equal(await page.inputValue('#voice-quality'),'low');
      assert.equal(await page.isVisible('#conversation-options'),true,'Low keeps its interruption choice');
      await voiceUI.check('#conversation-interruptions');await page.evaluate(()=>uiPreferencesWrites);
      await voiceUI.click('#conversation-start');await page.waitForFunction(()=>window.conversationBusy);
      const nativeTrace=process.argv.find(v=>v.startsWith('--native-trace='));
      const recognized=nativeTrace?JSON.parse(fs.readFileSync(nativeTrace.slice(15),'utf8')).final.turns[0].text:'Quand aura lieu la livraison du projet Orion ?';
      state.native.speech_id=1;state.native.partial_speech_id=1;state.native.partial=recognized;
      await page.waitForFunction(()=>document.getElementById('conversation-status').textContent.startsWith('Vous :'));
      state.native.partial='';state.native.turns=[{id:1,speech_id:1,text:recognized}];
      await until(()=>state.chats.length===1,'Classic Low submits recognized text');
      await until(()=>state.speech.length>0,'Phonon speech requested');
      await page.waitForFunction(()=>window.__audio.started>0);
      // Low accepts an immediate short reply, including during preceding playback.
      state.native.speech_id=2;state.native.partial_speech_id=2;state.native.turns=[{id:2,speech_id:2,text:'Oui'}];
      await until(()=>state.chats.length===2,'Classic Low accepts immediate one-word reply');
      assert.equal(state.acks.filter(id=>id===2).length,1);
      await until(()=>state.speech.length>=2,'Second Phonon reply');
      if(webEvents){assert.equal(await page.evaluate(()=>ws.lastSources?.[0]?.url),'https://example.org/source');await page.evaluate(()=>document.getElementById('voice-transcript').open=true);await page.waitForSelector('#voice-sources');}
      await voiceUI.click('#conversation-mute');await page.waitForFunction(()=>document.getElementById('conversation-mute').getAttribute('aria-pressed')==='true');
      assert.equal(state.native.microphone_closed,true);
      await voiceUI.click('#conversation-mute');await page.waitForFunction(()=>document.getElementById('conversation-mute').getAttribute('aria-pressed')==='false');
      await page.waitForFunction(()=>!busy&&!historySyncPending);
      assert.equal(state.chats[0].voice_conversation,true);assert.equal(state.chats[0].reasoning_effort,'none');
      assert.equal(state.chats[0].messages.at(-1).content,recognized);
      assert(state.calls.some(call=>call.path==='/v1/voice/speech'));
      assert(!state.calls.some(call=>call.path==='/client/voice/max/speech'));
      await page.evaluate(()=>window.conversationSuspend());await page.waitForFunction(()=>!window.conversationBusy);
      assert.equal(state.native.phase,'stopped');assert(state.native.microphone_closed);
      state.native.phase='error';state.native.message='Microphone refusé. Autorisez-le dans les paramètres puis réessayez.';
      await page.waitForFunction(()=>document.getElementById('conversation-status').textContent.includes('Microphone refusé'));
      await voiceUI.click('#conversation-start');await page.waitForFunction(()=>window.conversationBusy);
      await voiceUI.click('#conversation-start');await page.waitForFunction(()=>!window.conversationBusy);
      assert.deepEqual(errors,[]);
      console.log(JSON.stringify({passed:true,platform:android?'android':'windows',engine:'classic Low / Phonon',realAsrTrace:!!nativeTrace,checks:['dictation remains separate','3.5.39 recognized-turn loop','first recognized phrase','immediate one-word reply retained','Phonon PCM playback','mute/unmute','oral Qwen and history','background hangup','microphone error and retry',...(webEvents?['web sources and Phonon coexist']:[])]},null,2));return;
    }
    if(maxStreaming){
      await voiceUI.click('[data-view-button="voice"]');await voiceUI.selectOption('#voice-quality','max');
      state.longVoice=true;state.delayedReply=true;
      await voiceUI.click('#conversation-start');await page.waitForFunction(()=>window.conversationBusy);
      state.native.speech_id=1;state.native.turns=[{id:1,text:'Une réponse avec deux phrases.'}];
      await until(()=>state.speech.length>=2,'next sentence synthesis overlaps preceding playback');
      const audio=await page.evaluate(()=>window.__audio);
      assert(audio.started>audio.ended,'The next synthesis must begin before all preceding playback has completed');
      await voiceUI.check('#conversation-interruptions');
      state.native.speech_id=2;state.native.partial_speech_id=2;state.native.partial='Attends une seconde';
      await until(()=>state.voiceCancels.length>0,'barge-in cancels the prefetched response');
      assert.equal(await page.evaluate(()=>messages.at(-1).content),'[Réponse interrompue avant la fin de sa première phrase.]','Prefetched audio must not enter heard history before playback');
      await voiceUI.click('#conversation-start');await page.waitForFunction(()=>!window.conversationBusy);
      assert.deepEqual(errors,[]);console.log(JSON.stringify({passed:true,checks:['Max synthesizes next sentence during playback','prefetched audio cancelled on interruption','heard history excludes unplayed audio']}));return;
    }
    if(maxInstall&&!maxGpu){
      await voiceUI.click('[data-view-button="voice"]');await voiceUI.selectOption('#voice-quality','max');
      await page.waitForSelector('#voice-max-plan',{state:'visible'});
      assert(!state.calls.some(call=>call.path==='/client/voice/max/plan'||call.path==='/client/voice/max/install'),'Opening Max must not download or request consent implicitly');
      await voiceUI.click('#voice-max-plan');await page.waitForSelector('#voice-max-confirm',{state:'visible'});
      assert.match(await page.textContent('#voice-max-size'),/1,9 Go/);assert.match(await page.textContent('#voice-max-size'),/2,4 Go/);
      assert(!state.calls.some(call=>call.path==='/client/voice/max/install'),'Size must precede installation');
      assert.equal(await page.evaluate(()=>document.activeElement.id),'voice-max-install');
      await voiceUI.click('#voice-max-decline');assert.equal(await page.evaluate(()=>document.activeElement.id),'voice-max-plan');
      assert(!state.calls.some(call=>call.path==='/client/voice/max/install'));
      await voiceUI.click('#voice-max-plan');await voiceUI.click('#voice-max-install');await page.waitForSelector('#voice-max-progress',{state:'visible'});
      assert.equal(state.calls.filter(call=>call.path==='/client/voice/max/install').length,1);
      await voiceUI.click('#conversation-start');assert.match(await page.textContent('#conversation-status'),/fin de l’installation/);
      assert(!state.calls.some(call=>call.path==='/client/conversation'&&call.body.action==='start'));
      await voiceUI.click('#voice-max-install-cancel');await page.waitForFunction(()=>document.getElementById('voice-max-install-status').textContent.includes('arrêtée'));
      await voiceUI.selectOption('#voice-execution','server');assert.equal(await page.isVisible('#voice-max-plan'),false);
      await voiceUI.selectOption('#voice-execution','pc');await voiceUI.selectOption('#voice-quality','low');assert.equal(await page.isVisible('#voice-max-plan'),false);
      state.installation={phase:'ready',hardware:{checked:true,eligible:true,cards:[{vendor:'amd',name:'AMD Radeon RX 7800 XT'}]},storage:{path:'C:\\Users\\Utilisateur\\AppData\\Local\\QwenClient\\voice-max',exists:true,bytes:3800000000,removable:true}};
      state.maxPC={message:'Test lent. Vous pouvez utiliser Max ; la réponse peut prendre plus de temps.',performance:'limited',test_passed:false,update_recommended:true};
      await voiceUI.selectOption('#voice-quality','max');await page.waitForFunction(()=>document.getElementById('voice-max-status').textContent.includes('Test lent'));
      assert.match(await page.textContent('#voice-max-disk'),/3,8 Go/);
      assert.match(await page.textContent('#voice-max-folder'),/QwenClient\\voice-max/);
      assert.equal(await page.textContent('#voice-max-plan'),'Mettre à jour Max');
      await voiceUI.click('#voice-max-open-folder');await page.waitForFunction(()=>document.getElementById('voice-max-storage-status').textContent==='Dossier ouvert.');
      await voiceUI.click('#conversation-start');await page.waitForFunction(()=>window.conversationBusy);
      assert.equal(state.native.quality,'max');assert.equal(state.native.execution,'pc');
      assert.equal(await page.isDisabled('#voice-max-remove'),true,'An active call protects its Max files');
      await voiceUI.click('#conversation-start');await page.waitForFunction(()=>!window.conversationBusy);
      page.once('dialog',dialog=>dialog.dismiss());await voiceUI.click('#voice-max-remove');
      assert(!state.calls.some(call=>call.path==='/client/voice/max/remove'));
      state.failRemove=true;page.once('dialog',dialog=>dialog.accept());await voiceUI.click('#voice-max-remove');
      await page.waitForFunction(()=>document.getElementById('voice-max-storage-status').textContent.includes('encore utilisé'));
      assert.equal(await page.isDisabled('#voice-max-remove'),false,'A failed removal can be retried');
      state.failRemove=false;page.once('dialog',dialog=>{assert.match(dialog.message(),/Low et la dictée sont conservés/);dialog.accept();});await voiceUI.click('#voice-max-remove');
      await page.waitForFunction(()=>document.getElementById('voice-max-storage-status').textContent.includes('ont été supprimés'));
      assert.equal(await page.isDisabled('#voice-max-remove'),true);assert.equal(await page.isDisabled('#voice-max-open-folder'),true);
      assert.equal(await page.inputValue('#voice-quality'),'max','Removal never silently changes the chosen quality');
      assert.equal(await page.textContent('#voice-max-plan'),'Installer Max sur ce PC');
      await voiceUI.selectOption('#voice-quality','low');assert.equal(await page.isVisible('#voice-max-storage'),false);
      assert.deepEqual(errors,[]);console.log(JSON.stringify({passed:true,checks:['offer AMD pack','size before consent','progress and cancellation','slow benchmark still allows explicit PC Max','local folder and disk size','confirmation before removal','active-call protection','retry failed removal','reinstallation offered','Low remains independent']}));return;
    }
    if(!baseline){
      assert.equal(await page.isVisible('#voice-start'),true,'Dictation stays in chat');
      assert.equal(await page.isVisible('#conversation-start'),false,'Vocal controls belong to a separate page');
      await voiceUI.fill('#prompt','Un brouillon à conserver');await page.evaluate(()=>uiPersistPreferences());
      await voiceUI.click('[data-view-button="voice"]');await voiceUI.click('#conversation-start');
      assert.match(await page.textContent('#conversation-status'),/brouillon/);
      await voiceUI.click('#voice-back');assert.equal(await page.inputValue('#prompt'),'Un brouillon à conserver');
      await voiceUI.fill('#prompt','');await page.evaluate(()=>uiPersistPreferences());
    }
    await voiceUI.selectOption('#conversation-model','fred-test-cloud');if(!baseline)await voiceUI.click('[data-view-button="voice"]');if(maxVoice){await voiceUI.selectOption('#voice-quality','max');await page.evaluate(()=>uiPreferencesWrites);}await voiceUI.click('#conversation-start');await page.waitForFunction(()=>document.getElementById('conversation-status').textContent.includes('Qwen local'));assert.equal(await page.evaluate(()=>window.conversationBusy),false);
    if(!baseline)await voiceUI.click('#voice-back');await voiceUI.selectOption('#conversation-model','Kiara-test');if(!automaticReasoning)await page.locator('.thinking-segment:has(#thinking-high)').click();if(!baseline)await voiceUI.click('[data-view-button="voice"]');await voiceUI.click('#conversation-start');await page.waitForFunction(()=>window.conversationBusy);assert.equal(await page.isDisabled('#conversation-model'),true,'Model choice stays bound during a voice session');
    if(!baseline){
      await page.waitForFunction(()=>document.querySelector('.voice-view').dataset.state==='listening');
      assert.equal(await page.isDisabled('#voice-quality'),true,'Quality cannot switch mid-call');
      if(maxVoice){assert.equal(state.native.execution,'server');assert.match(await page.textContent('#voice-engine-location'),/serveur Kiara/);}
      await voiceUI.click('#voice-back');assert.equal(await page.isVisible('#voice-ongoing'),true);assert.equal(await page.isVisible('#voice-start'),true);assert.equal(await page.isDisabled('#voice-start'),true);
      await voiceUI.click('#voice-ongoing');assert.equal(await page.getAttribute('[data-view-button="voice"]','aria-current'),'page');
      await voiceUI.fill('#voice-volume','35');await page.locator('#voice-volume').dispatchEvent('change');await page.evaluate(()=>uiPreferencesWrites);
      assert.equal(state.preferences.voice_volume,35);assert.equal(await page.evaluate(()=>window.__audio.gain),.35);
      await voiceUI.uncheck('#voice-animation');await page.evaluate(()=>uiPreferencesWrites);
      const still=await page.locator('.voice-contour').first().getAttribute('d');await sleep(150);assert.equal(await page.locator('.voice-contour').first().getAttribute('d'),still);
      await voiceUI.check('#voice-animation');await page.evaluate(()=>uiPreferencesWrites);
      await page.emulateMedia({reducedMotion:'reduce'});await sleep(80);
      const reduced=await page.locator('.voice-contour').first().getAttribute('d');await sleep(150);assert.equal(await page.locator('.voice-contour').first().getAttribute('d'),reduced);
      await page.emulateMedia({reducedMotion:'no-preference'});
      await voiceUI.click('#voice-transcript > summary');
    }
    assert.equal(await page.isVisible('#conversation-mute'),true);assert.equal(await page.isVisible('#thinking'),false,'Written reasoning is hidden during the voice call');
    assert.equal(await page.isVisible('.context-gauge'),false);assert.match(await page.textContent('#conversation-context'),/16 384/);assert.match(await page.textContent('#model'),/16/);
    assert.equal(await page.getAttribute('#conversation-mute','aria-pressed'),'false');
    assert.equal(await page.isChecked('#conversation-interruptions'),false,'Vocal interruption is opt-in');
    state.failMute=true;await voiceUI.click('#conversation-mute');
    await page.waitForFunction(()=>!document.getElementById('conversation-mute').disabled);
    assert.equal(await page.getAttribute('#conversation-mute','aria-pressed'),'false','A failed command must never claim the microphone is muted');
    assert.equal(await page.evaluate(()=>window.conversationBusy),true);
    state.syncDelay=1200;state.native.speech_id=1;state.native.turns=[{id:1,text:'Quelle est la livraison du projet Orion ?'}];
    await page.waitForFunction(()=>historySyncPending&&messages.some(message=>message.role==='assistant'&&message.content));await sleep(350);
    if(!baseline){assert.match(await page.textContent('#voice-transcript-content'),/Orion/);assert(await page.evaluate(()=>window.__audio.analysed>0),'Speaking visualization measures output PCM');}
    snapshot=await page.evaluate(()=>({active:window.conversationBusy,busy,historySyncPending,text:messages.at(-1).content,status:document.getElementById('conversation-status').textContent}));
    assert.equal(snapshot.active,true,'A routine history sync must keep the voice session open');assert.equal(state.stops,0);assert.equal(state.cancels.length,0);assert.equal(state.voiceCancels.length,0);assert.equal(state.native.speech_id,1,'No new speech onset occurred');
    await page.waitForFunction(()=>window.__audio.ended===3&&!busy&&!historySyncPending);assert.equal(await page.evaluate(()=>messages.at(-1).content),'La livraison du projet Orion est prévue le 23 novembre.');assert.equal(await page.evaluate(()=>messages.at(-1).interrupted),undefined);assert.equal(state.acks.filter(id=>id===1).length,1);
    assert.match(await page.textContent('#conversation-context'),/480.*16 384/);
    if(webEvents){await page.waitForSelector(baseline?'.context-details':'#voice-sources');assert.equal(await page.evaluate(()=>ws.lastSources[0].url),'https://example.org/source');assert(state.speech.length>0,'Web sources and progress must preserve spoken output');if(!baseline){await voiceUI.click('#voice-sources');assert.equal(await page.isVisible('#ws-side'),true);await voiceUI.click('#ws-side-close');}}

    // An idle history refresh blocks submission: acknowledge once, keep the turn queued.
    const before=state.chats.length;await page.evaluate(()=>{serverHistoryReady=false;window.__qaSync=syncServerHistory();});await page.waitForFunction(()=>historySyncPending&&!busy);
    state.native.speech_id=2;state.native.turns=[{id:2,text:'Et le budget du même projet ?'}];await until(()=>state.acks.includes(2),'second native turn acknowledged');await sleep(250);assert.equal(state.chats.length,before,'The second turn must wait for history synchronization');
    await until(()=>state.chats.length===before+1,'queued turn submitted');await page.waitForFunction(()=>!busy&&!historySyncPending&&window.__audio.ended===6);assert.equal(state.acks.filter(id=>id===2).length,1);assert.equal(state.chats.at(-1).messages.at(-1).content,'Et le budget du même projet ?');assert.equal(state.chats[0].conversation_id,state.chats[1].conversation_id);assert.notEqual(state.chats[0].turn_id,state.chats[1].turn_id);

    // A genuine new speech onset during calculation must still cancel the original run.
    await voiceUI.focus('#conversation-interruptions');await page.keyboard.press('Space');await page.evaluate(()=>uiPreferencesWrites);
    assert.equal(state.preferences.voice_interruptions,true);
    state.holdChat=true;state.native.speech_id=3;state.native.turns=[{id:3,text:'Une question longue à interrompre.'}];await until(()=>state.pendingChat,'long calculation started');await page.waitForFunction(()=>busy);const heldTurn=state.pendingChat.body.turn_id;
    if(!baseline)await page.waitForFunction(()=>document.querySelector('.voice-view').dataset.state==='thinking');
    state.native.speech_id=4;state.native.partial='Non, attends.';await until(()=>state.cancels.includes(heldTurn),'barge-in cancels the correct run');await page.waitForFunction(()=>!busy&&!historySyncPending);assert(await page.evaluate(()=>messages.at(-1).interrupted));assert.equal(state.acks.filter(id=>id===3).length,1);assert.equal(await page.evaluate(()=>window.conversationBusy),true);

    // Interrupt actual scheduled PCM, then hang up and recover normal controls.
    state.holdChat=false;state.longVoice=true;const previousSources=await page.evaluate(()=>window.__audio.started);state.native.partial='';state.native.speech_id=5;state.native.turns=[{id:4,text:'Une réponse à interrompre pendant sa lecture.'}];await page.waitForFunction(previous=>window.__audio.started>previous,previousSources);const speechId=state.speech.at(-1).id;
    // Muting the capture must keep scheduled playback and the call running.
    const stopsBeforeMute=state.stops,voiceCancelsBeforeMute=state.voiceCancels.length;
    await voiceUI.focus('#conversation-mute');await page.keyboard.press('Space');
    await page.waitForFunction(()=>document.getElementById('conversation-mute').getAttribute('aria-pressed')==='true'&&!document.getElementById('conversation-mute').disabled);
    assert.equal(state.native.microphone_closed,true);
    if(!baseline)assert.equal(await page.evaluate(()=>document.activeElement.id),'conversation-mute','Keyboard focus returns after microphone confirmation');
    const chatsWhileMuted=state.chats.length;
    state.native.speech_id=6;state.native.partial='Une parole qui ne doit pas interrompre Kiara.';
    await sleep(450);assert.equal(state.voiceCancels.length,voiceCancelsBeforeMute);
    assert.equal(state.stops,stopsBeforeMute);assert.equal(state.chats.length,chatsWhileMuted);
    assert.equal(await page.evaluate(()=>window.conversationBusy),true);
    assert.match(await page.textContent('#conversation-status'),/microphone coupé/i);
    state.native.partial='';await voiceUI.focus('#conversation-mute');await page.keyboard.press('Space');
    await page.waitForFunction(()=>document.getElementById('conversation-mute').getAttribute('aria-pressed')==='false'&&!document.getElementById('conversation-mute').disabled);
    assert.equal(state.native.microphone_closed,false);
    const cancelsBeforeEcho=state.voiceCancels.length,chatsBeforeEcho=state.chats.length;
    state.native.speech_id=6;state.native.partial='';await sleep(350);
    assert.equal(state.voiceCancels.length,cancelsBeforeEcho,'A bare VAD onset must not cancel spoken audio');
    state.native.partial=state.speech.at(-1).text;await sleep(300);
    assert.equal(state.voiceCancels.length,cancelsBeforeEcho,'Recognized playback echo must not cancel audio');
    state.native.turns=[{id:5,speech_id:6,text:state.speech.at(-1).text}];await until(()=>state.acks.includes(5),'echo acknowledged');
    assert.equal(state.chats.length,chatsBeforeEcho,'Playback echo must never become a new user message');
    state.native.speech_id=7;state.native.partial='';await sleep(300);
    assert.equal(state.voiceCancels.length,cancelsBeforeEcho,'Wait for the delayed transcript of the new utterance');
    state.native.partial='Stop.';await until(()=>state.voiceCancels.includes(speechId),'barge-in cancels the correct speech');assert(await page.evaluate(()=>window.__audio.stopped>0));await page.waitForFunction(()=>!busy&&!historySyncPending);
    await voiceUI.click('#conversation-start');await page.waitForFunction(()=>!window.conversationBusy&&!document.getElementById('prompt').readOnly);assert.equal(state.native.phase,'stopped');assert.equal(await page.isVisible('#conversation-mute'),false);assert.equal(await page.evaluate(()=>document.getElementById('thinking').hidden),false,'Written reasoning returns after hangup');assert.equal(state.stops,1);assert.deepEqual(errors,[]);
    if(!automaticReasoning)assert.equal(await page.evaluate(()=>thinkingEffort()),'high','Written reasoning preference survives an oral call');

    // Opt-out rejects partials, final noise and late ASR without cancelling or
    // queuing a new message. The next phrase after playback still works.
    await voiceUI.uncheck('#conversation-interruptions');await page.evaluate(()=>uiPreferencesWrites);
    state.holdChat=true;state.longVoice=true;state.syncDelay=0;
    await voiceUI.click('#conversation-start');await page.waitForFunction(()=>window.conversationBusy);
    state.native.speech_id=1;state.native.turns=[{id:1,speech_id:1,text:'Une réponse qui doit aller jusqu’au bout.'}];await until(()=>state.pendingChat,'protected calculation started');
    const protectedChat=state.pendingChat,chatsProtected=state.chats.length,cancelsProtected=state.cancels.length,voicesProtected=state.voiceCancels.length;
    const proof=require('./test_artifacts.cjs').directory('conversation');await page.screenshot({path:path.join(proof,'windows-interruptions-desactivees.png'),animations:'disabled'});
    state.native.speech_id=2;state.native.partial='Stop.';state.native.turns=[{id:2,speech_id:2,text:'Un bruit transcrit pendant le calcul.'}];await until(()=>state.acks.at(-1)===2,'noise dropped while calculating');
    await sleep(250);assert.equal(state.cancels.length,cancelsProtected);assert.equal(state.chats.length,chatsProtected);assert.equal(await page.evaluate(()=>busy),true);
    state.native.partial='';state.holdChat=false;event(protectedChat.res,{choices:[{delta:{content:'Cette réponse va bien jusqu’au bout.'},finish_reason:'stop'}]});protectedChat.res.end('data: [DONE]\n\n');state.pendingChat=null;
    const protectedAudio=await page.evaluate(()=>window.__audio.started);await page.waitForFunction(previous=>window.__audio.started>previous,protectedAudio);
    state.native.speech_id=3;state.native.partial='Une phrase qui ne doit pas couper la voix.';state.native.turns=[{id:3,speech_id:3,text:'Une phrase qui ne doit pas couper la voix.'}];await until(()=>state.acks.at(-1)===3,'speech dropped during playback');
    assert.equal(state.voiceCancels.length,voicesProtected);assert.equal(state.chats.length,chatsProtected);
    state.native.partial='';await page.waitForFunction(()=>!busy&&!historySyncPending&&window.__qaVoice().listening);
    state.native.turns=[{id:4,speech_id:3,text:'Transcription tardive du même bruit.'}];await until(()=>state.acks.at(-1)===4,'late transcript discarded');await sleep(250);assert.equal(state.chats.length,chatsProtected);assert.equal(state.cancels.length,cancelsProtected);
    state.longVoice=false;state.syncDelay=1600;state.native.speech_id=4;state.native.turns=[{id:5,speech_id:4,text:'Voici ma vraie question après la réponse.'}];await until(()=>state.chats.length===chatsProtected+1,'listening resumes after protected playback');
    await page.waitForFunction(()=>busy&&window.__qaVoice().listening);
    state.native.speech_id=5;state.native.turns=[{id:6,speech_id:5,text:'Ma question suivante attend la sauvegarde.'}];await until(()=>state.acks.at(-1)===6,'post-playback speech survives the remaining history save');
    await until(()=>state.chats.length===chatsProtected+2,'post-playback question submitted once');await page.waitForFunction(()=>!busy&&!historySyncPending);state.syncDelay=0;
    await voiceUI.click('#conversation-start');await page.waitForFunction(()=>!window.conversationBusy);

    // Losing a health probe must not cancel a reply or close the microphone.
    state.longVoice=false;state.delayedReply=true;state.syncDelay=0;
    await voiceUI.click('#conversation-start');await page.waitForFunction(()=>window.conversationBusy);
    const stopsBeforeDrop=state.stops,cancelsBeforeDrop=state.cancels.length;
    const audioBeforeDrop=await page.evaluate(()=>window.__audio.started);
    state.native.speech_id=1;state.native.turns=[{id:1,text:'Une réponse pendant la reconnexion.'}];
    await page.waitForFunction(previous=>busy&&window.__audio.started>previous,audioBeforeDrop);
    state.failModels=true;await page.evaluate(()=>connectionFailure({code:'connection_error',message:'Coupure temporaire'}));
    await sleep(400);assert.equal(await page.evaluate(()=>window.conversationBusy),true);
    assert.equal(state.stops,stopsBeforeDrop);assert.equal(state.cancels.length,cancelsBeforeDrop);
    await page.waitForFunction(()=>!busy&&!historySyncPending);
    assert.equal(await page.evaluate(()=>messages.at(-1).content),'Oui. Je t’entends bien.');
    await page.waitForFunction(()=>window.__qaVoice().listening);
    const chatsBeforeReconnect=state.chats.length;
    state.native.speech_id=2;state.native.turns=[{id:2,text:'Une question conservée pendant la coupure.'}];
    await until(()=>state.acks.includes(2),'offline utterance retained');await sleep(300);
    assert.equal(state.chats.length,chatsBeforeReconnect);
    state.failModels=false;await page.evaluate(()=>models());
    await until(()=>state.chats.length===chatsBeforeReconnect+1,'queued utterance resumes once');
    await page.waitForFunction(()=>!busy&&!historySyncPending);
    assert.equal(state.chats.at(-1).messages.at(-1).content,'Une question conservée pendant la coupure.');
    assert.equal(state.stops,stopsBeforeDrop);await voiceUI.click('#conversation-start');
    await page.waitForFunction(()=>!window.conversationBusy);

    // An audio transport error keeps the complete text and the microphone.
    await voiceUI.click('#conversation-start');await page.waitForFunction(()=>window.conversationBusy);
    const stopsBeforeAudioFailure=state.stops,cancelsBeforeAudioFailure=state.cancels.length;
    state.failSpeech=true;state.native.speech_id=1;state.native.turns=[{id:1,text:'La voix coupe, mais continue le texte.'}];
    const chatsBeforeAudioFailure=state.chats.length;
    await until(()=>state.chats.length>chatsBeforeAudioFailure,'audio failure answer requested');
    await page.waitForFunction(()=>!busy&&!historySyncPending);
    assert.equal(await page.evaluate(()=>messages.at(-1).content),'Oui. Je t’entends bien.');
    assert.equal(await page.evaluate(()=>messages.at(-1).interrupted),undefined);
    assert.equal(await page.evaluate(()=>window.conversationBusy),true);
    assert.equal(state.stops,stopsBeforeAudioFailure);assert.equal(state.cancels.length,cancelsBeforeAudioFailure);
    await voiceUI.click('#conversation-start');await page.waitForFunction(()=>!window.conversationBusy);

    // A short first sentence is spoken before the next sentence or end arrives.
    state.longVoice=false;state.delayedReply=true;state.syncDelay=0;
    await voiceUI.click('#conversation-start');await page.waitForFunction(()=>window.conversationBusy);
    const audioBefore=await page.evaluate(()=>window.__audio.started);
    state.native.speech_id=1;state.native.turns=[{id:1,text:'Tu m’entends bien ?'}];
    await page.waitForFunction(previous=>busy&&window.__audio.started>previous,audioBefore);
    assert.equal(state.speech.at(-1).text,'Oui.');
    await page.waitForFunction(()=>!busy&&!historySyncPending);assert.equal(await page.evaluate(()=>messages.at(-1).content),'Oui. Je t’entends bien.');
    state.failStop=true;await voiceUI.click('#conversation-start');
    await page.waitForFunction(()=>document.getElementById('conversation-start').textContent==='Réessayer le raccrochage'&&!document.getElementById('conversation-start').disabled);
    assert.equal(await page.evaluate(()=>messages.at(-1).content),'Oui. Je t’entends bien.','Hangup or transport failure must not erase a completed reply');
    await voiceUI.click('#conversation-start');await page.waitForFunction(()=>!window.conversationBusy&&!document.getElementById('prompt').readOnly);
    state.prefixReply=true;state.delayedReply=false;await voiceUI.click('#conversation-start');await page.waitForFunction(()=>window.conversationBusy);
    const prefixAudio=await page.evaluate(()=>window.__audio.started);state.native.speech_id=1;state.native.turns=[{id:1,text:'Une réponse dont la première phrase tarde à se terminer.'}];
    await page.waitForFunction(previous=>busy&&window.__audio.started>previous,prefixAudio);
    assert.equal(state.speech.at(-1).text,'Je vous propose une courte réponse pour commencer,','Speak a natural clause before the model finishes');
    await page.waitForFunction(()=>!busy&&!historySyncPending);assert.equal(await page.evaluate(()=>messages.at(-1).content),'Je vous propose une courte réponse pour commencer, puis nous préciserons les détails.');
    await voiceUI.click('#conversation-start');await page.waitForFunction(()=>!window.conversationBusy);state.prefixReply=false;
    await voiceUI.click('#conversation-start');await page.waitForFunction(()=>window.conversationBusy);
    await page.evaluate(()=>connectionFailure({code:'access_revoked',message:'Accès révoqué'}));
    await page.waitForFunction(()=>!window.conversationBusy);assert.equal(state.native.phase,'stopped');
    await page.reload();await page.waitForFunction(()=>!document.getElementById('conversation-start')?.disabled);if(!baseline)await voiceUI.click('[data-view-button="voice"]');assert.equal(await page.isChecked('#conversation-interruptions'),false,'Opt-out survives reload');
    await voiceUI.check('#conversation-interruptions');await page.evaluate(()=>uiPreferencesWrites);await page.reload();await page.waitForFunction(()=>!document.getElementById('conversation-start')?.disabled);if(!baseline)await voiceUI.click('[data-view-button="voice"]');assert.equal(await page.isChecked('#conversation-interruptions'),true,'Explicit opt-in survives reload');
    if(!baseline)assert.equal(await page.inputValue('#voice-volume'),'35','Volume survives reload');
    if(maxVoice){assert.equal(await page.inputValue('#voice-quality'),'max');assert(state.calls.some(call=>call.path==='/client/voice/max/speech'));assert(!state.calls.some(call=>call.path==='/v1/voice/speech'),'Max must use its own speech engine');}
    console.log(JSON.stringify({passed:true,source:baseline?'0354e91':'working-tree',reasoning:'oral none, written preference preserved',checks:['direct Qwen + delayed sync preserves session and complete text','all three PCM frames finish without automatic cancellation','second ASR turn waits for history sync and submits exactly once','same conversation with unique turn IDs','real new speech during calculation cancels original turn','speech playback barge-in cancels correct audio and scheduled sources','hangup returns controls','local requests bypass Hermes; oral reasoning disabled','short first sentence is spoken before LLM completion','hangup failure keeps completed text and offers retry','network probe failure preserves reply and microphone','offline utterance resumes exactly once after reconnection','audio transport failure preserves full text and microphone','revoked access still closes microphone','keyboard mute/unmute preserves playback and session','muted recognition never interrupts or submits','failed mute never reports microphone closed','interruptions disabled by default','noise and late transcripts neither cancel nor submit while disabled','listening resumes after playback','interruption setting survives reload both ways','first natural clause spoken before model finishes','reasoning hidden during voice and restored unchanged after hangup','speech after playback remains queued during history save'],chats:state.chats.length,acks:state.acks,simulation:'native ASR and PCM timing; no hardware microphone or server models'},null,2));
  }catch(error){console.error(JSON.stringify({passed:false,source:baseline?'0354e91':'working-tree',snapshot,current:await page.evaluate(()=>({active:window.conversationBusy,busy,button:document.getElementById('conversation-start').textContent,disabled:document.getElementById('conversation-start').disabled,status:document.getElementById('conversation-status').textContent,voice:window.__qaVoice?.()})),recent:state.calls.slice(-12),native:state.native,stops:state.stops,cancels:state.cancels,voiceCancels:state.voiceCancels},null,2));throw error;}
  finally{for(const timer of state.timers)clearTimeout(timer);await browser.close();server.closeAllConnections?.();await new Promise(resolve=>server.close(resolve));}
}
main().catch(error=>{console.error(error);process.exitCode=1;});
