/* Shared Windows UI, deterministic native ASR and server PCM, delayed history. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http'),{execFileSync}=require('node:child_process');
const root=__dirname,read=name=>fs.readFileSync(path.join(root,name),'utf8');
const baseline=process.argv.includes('--baseline'),automaticReasoning=process.argv.includes('--automatic-reasoning'),config={key:'conversation-regression-local',model:'Fred-test',version:'Windows-test',storage:'conversation-regression'};
const script=name=>'<script nonce="qa">'+(baseline&&name==='conversation.js'?execFileSync('git',['show','0354e91:client-qwen/conversation.js'],{cwd:root,encoding:'utf8'}):read(name)).replaceAll('</script','<\\/script')+'</script>';
const html=read('chat.html').replace('__UI_CSS__',read('ui.css')).replace('__CONFIG__',JSON.stringify(config)).replaceAll('__NONCE__','qa')
  .replace('</head>',()=>script('vendor/markdown-it.min.js')+script('markdown.js')+'</head>')
  .replace('</body>',()=>read('workspace.html')+['ui.js','attachments.js','corrector.js','selection.js','thinking.js','voice.js','conversation.js'].map(script).join('')+'</body>');
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function until(work,label){for(let i=0;i<400;i++){if(await work())return;await sleep(25);}throw new Error('Timeout: '+label);}

async function main(){
  const {chromium,options}=require('./browser_test_support.cjs');
  const browser=await chromium.launch(options);
  const state={history:null,revision:'1',preferences:{},native:{phase:'idle',installed:true,session:'',speech_id:0,partial:'',turns:[]},calls:[],chats:[],runs:new Map(),syncDelay:0,syncActive:0,acks:[],stops:0,cancels:[],voiceCancels:[],speech:[],timers:new Set(),holdChat:false,longVoice:false,pendingChat:null,delayedReply:false,failStop:false};
  const json=(res,value,status=200)=>{res.writeHead(status,{'Content-Type':'application/json; charset=utf-8'});res.end(JSON.stringify(value));};
  const event=(res,value)=>{if(!res.destroyed&&!res.writableEnded)res.write('data: '+JSON.stringify(value)+'\n\n');};
  const later=(work,ms)=>{const timer=setTimeout(()=>{state.timers.delete(timer);work();},ms);state.timers.add(timer);};
  const server=http.createServer(async(req,res)=>{
    let raw='';for await(const chunk of req)raw+=chunk;const body=JSON.parse(raw||'{}');
    if(req.url==='/'){res.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});return res.end(html);}
    state.calls.push({path:req.url,body,requestId:req.headers['x-qwen-request']});
    if(req.headers.authorization!=='Bearer '+config.key)return json(res,{error:{message:'Unauthorized'}},401);
    if(req.url==='/client/state')return json(res,{version:'test',preferences:state.preferences,update:{message:'À jour',available:false,busy:false},endpoint:'https://example.test',internet_endpoint:'example.test:51820',local_api:'http://127.0.0.1/v1',key:config.key,history:{message:'Copie locale enregistrée',needs_merge:false},connection:{connected:true,model:'Fred-test',transport:'https',endpoint:'https://example.test',checked_at:Date.now()/1000}});
    if(req.url==='/client/history'&&req.method==='GET')return json(res,{history:state.history,revision:state.revision});
    if(req.url==='/client/history/sync'){state.syncActive++;await sleep(state.syncDelay);state.history=state.history||body.initial;state.syncActive--;return json(res,{history:state.history,revision:state.revision,message:'Synchronisé'});}
    if(req.url==='/client/history'){state.history=body.history;state.revision=String(Number(state.revision)+1);return json(res,{saved:true,revision:state.revision});}
    if(req.url==='/client/preferences'){state.preferences=body;return json(res,{saved:true});}
    if(req.url==='/client/draft')return json(res,{draft:null});
    if(req.url==='/client/integrations')return json(res,{apps:[]});
    if(req.url==='/client/voice')return json(res,{phase:'idle',installed:false});
    if(req.url==='/client/conversation'){
      if(body.action==='start')state.native={...state.native,phase:'listening',session:'qa-conversation',turns:[],speech_id:0,muted:false,microphone_closed:false,mute_pending:false};
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
    if(req.url==='/v1/models')return json(res,{source:'hermes',default_model:'Fred-test',data:[{id:'Fred-test',provider:'Qwen local',name:'Modèle local',available:true,capabilities:{images:false,thinking:true,reasoning_efforts:['none','low','medium','high']}},{id:'fred-test-cloud',name:'Modèle vocal choisi',provider:'Cloud de test',available:true,capabilities:{vision:false,thinking:true,reasoning_mode:automaticReasoning?'none':'effort',reasoning_efforts:automaticReasoning?[]:['none','xhigh','max']}}]});
    if(req.url==='/v1/status')return json(res,{protocol:3,agent_protocol:4,version:'test'});
    if(req.url==='/v1/workspace')return json(res,{projects:[],jobs:[]});
    if(req.url==='/v1/notifications')return json(res,{items:[],unread:0});
    if(req.url==='/v1/context')return json(res,{tokens:15,capacity:4096,estimated:true});
    if(req.url==='/v1/agent/action')return json(res,state.runs.get(body.request_id)||{request_id:body.request_id,conversation_id:body.conversation_id,status:'unknown'});
    if(req.url==='/v1/voice/status')return json(res,{ready:true,enabled:true});
    if(req.url==='/v1/voice/cancel'){state.voiceCancels.push(body.request_id);return json(res,{cancelled:true});}
    if(req.url==='/v1/voice/speech'){
      if(state.failSpeech){state.failSpeech=false;return json(res,{error:{message:'Lecture temporairement interrompue'}},503);}
      state.speech.push({id:body.request_id,text:body.text});res.writeHead(200,{'Content-Type':'text/event-stream; charset=utf-8'});
      const pcm=Buffer.alloc(4800*2).toString('base64'),frames=state.longVoice?30:3;
      for(let i=0;i<frames;i++)later(()=>event(res,{id:body.request_id,rate:24000,pcm}),50+i*30);
      later(()=>{event(res,{id:body.request_id,done:true});if(!res.destroyed&&!res.writableEnded)res.end();},50+frames*30);return;
    }
    if(req.url==='/v1/cancel'){
      assert.equal(body.voice_conversation,true);state.cancels.push(req.headers['x-qwen-request']);const pending=state.pendingChat;
      if(pending&&pending.body.turn_id===req.headers['x-qwen-request']){state.runs.set(pending.body.turn_id,{request_id:pending.body.turn_id,conversation_id:pending.body.conversation_id,status:'cancelled',text:''});if(!pending.res.destroyed&&!pending.res.writableEnded)pending.res.end('data: [DONE]\n\n');state.pendingChat=null;}
      return json(res,{cancelled:true});
    }
    if(req.url==='/v1/chat/completions'){
      assert.equal(body.model,'Fred-test','Native ASR must keep the chosen local model');assert.equal(body.voice_conversation,true,'Oral requests must bypass Hermes');
      assert.equal(body.reasoning_effort,'none','Oral replies disable thinking without changing the written-chat preference');
      assert.equal(body.turn_id,req.headers['x-qwen-request']);state.chats.push(body);if(!body.voice_conversation)state.runs.set(body.turn_id,{request_id:body.turn_id,conversation_id:body.conversation_id,status:'running',text:''});
      res.writeHead(200,{'Content-Type':'text/event-stream; charset=utf-8'});event(res,{hermes_status:{phase:'working',message:'Hermes prépare la réponse'}});
      if(state.holdChat){state.pendingChat={body,res};return;}
      if(state.delayedReply){event(res,{choices:[{delta:{content:'Oui. '}}]});later(()=>{event(res,{choices:[{delta:{content:'Je t’entends bien.'}}]});event(res,{choices:[{delta:{},finish_reason:'stop'}]});if(!res.destroyed&&!res.writableEnded)res.end('data: [DONE]\n\n');},1800);return;}
      later(()=>{const text=state.chats.length===1?'La livraison du projet Orion est prévue le 23 novembre.':'Le budget du projet Orion est de 4200 euros.';state.runs.set(body.turn_id,{request_id:body.turn_id,conversation_id:body.conversation_id,status:'completed',text,reasoning_content:'',sources:[]});event(res,{choices:[{delta:{content:text}}]});event(res,{hermes_run:{request_id:body.turn_id,conversation_id:body.conversation_id,status:'completed'}});event(res,{choices:[{delta:{},finish_reason:'stop'}]});if(!res.destroyed&&!res.writableEnded)res.end('data: [DONE]\n\n');},150);return;
    }
    return json(res,{});
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  let page,snapshot;
  try{
    page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];page.on('pageerror',error=>errors.push(error.message));
    await page.addInitScript(()=>{
      window.__audio={started:0,ended:0,stopped:0};
      window.AudioContext=class{
        constructor(){this.origin=performance.now();this.destination={};}
        get currentTime(){return (performance.now()-this.origin)/1000;}
        async resume(){}async close(){}
        createBuffer(_channels,length,rate){const values=new Float32Array(length);return {duration:length/rate,getChannelData(){return values;}};}
        createBufferSource(){const context=this,source={connect(){},start(time){window.__audio.started++;this.timer=setTimeout(()=>{window.__audio.ended++;this.onended?.();},Math.max(0,(time-context.currentTime+this.buffer.duration)*1000));},stop(){clearTimeout(this.timer);window.__audio.stopped++;this.onended?.();}};return source;}
      };
    });
    await page.goto('http://127.0.0.1:'+server.address().port);await page.waitForSelector('#conversation-start:not([disabled])');await page.selectOption('#conversation-model','fred-test-cloud');await page.click('#conversation-start');await page.waitForFunction(()=>document.getElementById('conversation-status').textContent.includes('Qwen local'));assert.equal(await page.evaluate(()=>window.conversationBusy),false);await page.selectOption('#conversation-model','Fred-test');if(!automaticReasoning)await page.locator('.thinking-segment:has(#thinking-high)').click();await page.click('#conversation-start');await page.waitForFunction(()=>window.conversationBusy);assert.equal(await page.isDisabled('#conversation-model'),true,'Model choice stays bound during a voice session');
    assert.equal(await page.isVisible('#conversation-mute'),true);
    assert.equal(await page.getAttribute('#conversation-mute','aria-pressed'),'false');
    state.failMute=true;await page.click('#conversation-mute');
    await page.waitForFunction(()=>!document.getElementById('conversation-mute').disabled);
    assert.equal(await page.getAttribute('#conversation-mute','aria-pressed'),'false','A failed command must never claim the microphone is muted');
    assert.equal(await page.evaluate(()=>window.conversationBusy),true);
    state.syncDelay=1200;state.native.speech_id=1;state.native.turns=[{id:1,text:'Quelle est la livraison du projet Orion ?'}];
    await page.waitForFunction(()=>historySyncPending&&messages.some(message=>message.role==='assistant'&&message.content));await sleep(350);
    snapshot=await page.evaluate(()=>({active:window.conversationBusy,busy,historySyncPending,text:messages.at(-1).content,status:document.getElementById('conversation-status').textContent}));
    assert.equal(snapshot.active,true,'A routine history sync must keep the voice session open');assert.equal(state.stops,0);assert.equal(state.cancels.length,0);assert.equal(state.voiceCancels.length,0);assert.equal(state.native.speech_id,1,'No new speech onset occurred');
    await page.waitForFunction(()=>window.__audio.ended===3&&!busy&&!historySyncPending);assert.equal(await page.evaluate(()=>messages.at(-1).content),'La livraison du projet Orion est prévue le 23 novembre.');assert.equal(await page.evaluate(()=>messages.at(-1).interrupted),undefined);assert.equal(state.acks.filter(id=>id===1).length,1);

    // An idle history refresh blocks submission: acknowledge once, keep the turn queued.
    const before=state.chats.length;await page.evaluate(()=>{serverHistoryReady=false;window.__qaSync=syncServerHistory();});await page.waitForFunction(()=>historySyncPending&&!busy);
    state.native.speech_id=2;state.native.turns=[{id:2,text:'Et le budget du même projet ?'}];await until(()=>state.acks.includes(2),'second native turn acknowledged');await sleep(250);assert.equal(state.chats.length,before,'The second turn must wait for history synchronization');
    await until(()=>state.chats.length===before+1,'queued turn submitted');await page.waitForFunction(()=>!busy&&!historySyncPending&&window.__audio.ended===6);assert.equal(state.acks.filter(id=>id===2).length,1);assert.equal(state.chats.at(-1).messages.at(-1).content,'Et le budget du même projet ?');assert.equal(state.chats[0].conversation_id,state.chats[1].conversation_id);assert.notEqual(state.chats[0].turn_id,state.chats[1].turn_id);

    // A genuine new speech onset during calculation must still cancel the original run.
    state.holdChat=true;state.native.speech_id=3;state.native.turns=[{id:3,text:'Une question longue à interrompre.'}];await until(()=>state.pendingChat,'long calculation started');await page.waitForFunction(()=>busy);const heldTurn=state.pendingChat.body.turn_id;
    state.native.speech_id=4;state.native.partial='Non, attends.';await until(()=>state.cancels.includes(heldTurn),'barge-in cancels the correct run');await page.waitForFunction(()=>!busy&&!historySyncPending);assert(await page.evaluate(()=>messages.at(-1).interrupted));assert.equal(state.acks.filter(id=>id===3).length,1);assert.equal(await page.evaluate(()=>window.conversationBusy),true);

    // Interrupt actual scheduled PCM, then hang up and recover normal controls.
    state.holdChat=false;state.longVoice=true;const previousSources=await page.evaluate(()=>window.__audio.started);state.native.partial='';state.native.speech_id=5;state.native.turns=[{id:4,text:'Une réponse à interrompre pendant sa lecture.'}];await page.waitForFunction(previous=>window.__audio.started>previous,previousSources);const speechId=state.speech.at(-1).id;
    // Muting the capture must keep scheduled playback and the call running.
    const stopsBeforeMute=state.stops,voiceCancelsBeforeMute=state.voiceCancels.length;
    await page.focus('#conversation-mute');await page.keyboard.press('Space');
    await page.waitForFunction(()=>document.getElementById('conversation-mute').getAttribute('aria-pressed')==='true'&&!document.getElementById('conversation-mute').disabled);
    assert.equal(state.native.microphone_closed,true);
    const chatsWhileMuted=state.chats.length;
    state.native.speech_id=6;state.native.partial='Une parole qui ne doit pas interrompre Fred.';
    await sleep(450);assert.equal(state.voiceCancels.length,voiceCancelsBeforeMute);
    assert.equal(state.stops,stopsBeforeMute);assert.equal(state.chats.length,chatsWhileMuted);
    assert.equal(await page.evaluate(()=>window.conversationBusy),true);
    assert.match(await page.textContent('#conversation-status'),/microphone coupé/i);
    state.native.partial='';await page.focus('#conversation-mute');await page.keyboard.press('Space');
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
    await page.click('#conversation-start');await page.waitForFunction(()=>!window.conversationBusy&&!document.getElementById('prompt').readOnly);assert.equal(state.native.phase,'stopped');assert.equal(await page.isVisible('#conversation-mute'),false);assert.equal(state.stops,1);assert.deepEqual(errors,[]);
    if(!automaticReasoning)assert.equal(await page.evaluate(()=>thinkingEffort()),'high','Written reasoning preference survives an oral call');

    // Losing a health probe must not cancel a reply or close the microphone.
    state.longVoice=false;state.delayedReply=true;state.syncDelay=0;
    await page.click('#conversation-start');await page.waitForFunction(()=>window.conversationBusy);
    const stopsBeforeDrop=state.stops,cancelsBeforeDrop=state.cancels.length;
    const audioBeforeDrop=await page.evaluate(()=>window.__audio.started);
    state.native.speech_id=1;state.native.turns=[{id:1,text:'Une réponse pendant la reconnexion.'}];
    await page.waitForFunction(previous=>busy&&window.__audio.started>previous,audioBeforeDrop);
    state.failModels=true;await page.evaluate(()=>connectionFailure({code:'connection_error',message:'Coupure temporaire'}));
    await sleep(400);assert.equal(await page.evaluate(()=>window.conversationBusy),true);
    assert.equal(state.stops,stopsBeforeDrop);assert.equal(state.cancels.length,cancelsBeforeDrop);
    await page.waitForFunction(()=>!busy&&!historySyncPending);
    assert.equal(await page.evaluate(()=>messages.at(-1).content),'Oui. Je t’entends bien.');
    const chatsBeforeReconnect=state.chats.length;
    state.native.speech_id=2;state.native.turns=[{id:2,text:'Une question conservée pendant la coupure.'}];
    await until(()=>state.acks.includes(2),'offline utterance retained');await sleep(300);
    assert.equal(state.chats.length,chatsBeforeReconnect);
    state.failModels=false;await page.evaluate(()=>models());
    await until(()=>state.chats.length===chatsBeforeReconnect+1,'queued utterance resumes once');
    await page.waitForFunction(()=>!busy&&!historySyncPending);
    assert.equal(state.chats.at(-1).messages.at(-1).content,'Une question conservée pendant la coupure.');
    assert.equal(state.stops,stopsBeforeDrop);await page.click('#conversation-start');
    await page.waitForFunction(()=>!window.conversationBusy);

    // An audio transport error keeps the complete text and the microphone.
    await page.click('#conversation-start');await page.waitForFunction(()=>window.conversationBusy);
    const stopsBeforeAudioFailure=state.stops,cancelsBeforeAudioFailure=state.cancels.length;
    state.failSpeech=true;state.native.speech_id=1;state.native.turns=[{id:1,text:'La voix coupe, mais continue le texte.'}];
    const chatsBeforeAudioFailure=state.chats.length;
    await until(()=>state.chats.length>chatsBeforeAudioFailure,'audio failure answer requested');
    await page.waitForFunction(()=>!busy&&!historySyncPending);
    assert.equal(await page.evaluate(()=>messages.at(-1).content),'Oui. Je t’entends bien.');
    assert.equal(await page.evaluate(()=>messages.at(-1).interrupted),undefined);
    assert.equal(await page.evaluate(()=>window.conversationBusy),true);
    assert.equal(state.stops,stopsBeforeAudioFailure);assert.equal(state.cancels.length,cancelsBeforeAudioFailure);
    await page.click('#conversation-start');await page.waitForFunction(()=>!window.conversationBusy);

    // A short first sentence is spoken before the next sentence or end arrives.
    state.longVoice=false;state.delayedReply=true;state.syncDelay=0;
    await page.click('#conversation-start');await page.waitForFunction(()=>window.conversationBusy);
    const audioBefore=await page.evaluate(()=>window.__audio.started);
    state.native.speech_id=1;state.native.turns=[{id:1,text:'Tu m’entends bien ?'}];
    await page.waitForFunction(previous=>busy&&window.__audio.started>previous,audioBefore);
    assert.equal(state.speech.at(-1).text,'Oui.');
    await page.waitForFunction(()=>!busy&&!historySyncPending);assert.equal(await page.evaluate(()=>messages.at(-1).content),'Oui. Je t’entends bien.');
    state.failStop=true;await page.click('#conversation-start');
    await page.waitForFunction(()=>document.getElementById('conversation-start').textContent==='Réessayer le raccrochage'&&!document.getElementById('conversation-start').disabled);
    assert.equal(await page.evaluate(()=>messages.at(-1).content),'Oui. Je t’entends bien.','Hangup or transport failure must not erase a completed reply');
    await page.click('#conversation-start');await page.waitForFunction(()=>!window.conversationBusy&&!document.getElementById('prompt').readOnly);
    await page.click('#conversation-start');await page.waitForFunction(()=>window.conversationBusy);
    await page.evaluate(()=>connectionFailure({code:'access_revoked',message:'Accès révoqué'}));
    await page.waitForFunction(()=>!window.conversationBusy);assert.equal(state.native.phase,'stopped');
    console.log(JSON.stringify({passed:true,source:baseline?'0354e91':'working-tree',reasoning:'oral none, written preference preserved',checks:['direct Qwen + delayed sync preserves session and complete text','all three PCM frames finish without automatic cancellation','second ASR turn waits for history sync and submits exactly once','same conversation with unique turn IDs','real new speech during calculation cancels original turn','speech playback barge-in cancels correct audio and scheduled sources','hangup returns controls','local requests bypass Hermes; oral reasoning disabled','short first sentence is spoken before LLM completion','hangup failure keeps completed text and offers retry','network probe failure preserves reply and microphone','offline utterance resumes exactly once after reconnection','audio transport failure preserves full text and microphone','revoked access still closes microphone','keyboard mute/unmute preserves playback and session','muted recognition never interrupts or submits','failed mute never reports microphone closed'],chats:state.chats.length,acks:state.acks,simulation:'native ASR and PCM timing; no hardware microphone or server models'},null,2));
  }catch(error){console.error(JSON.stringify({passed:false,source:baseline?'0354e91':'working-tree',snapshot,current:await page.evaluate(()=>({active:window.conversationBusy,busy,button:document.getElementById('conversation-start').textContent,disabled:document.getElementById('conversation-start').disabled,status:document.getElementById('conversation-status').textContent})),recent:state.calls.slice(-12),native:state.native,stops:state.stops,cancels:state.cancels,voiceCancels:state.voiceCancels},null,2));throw error;}
  finally{for(const timer of state.timers)clearTimeout(timer);await browser.close();server.closeAllConnections?.();await new Promise(resolve=>server.close(resolve));}
}
main().catch(error=>{console.error(error);process.exitCode=1;});
