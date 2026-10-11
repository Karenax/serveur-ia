/* Shared Windows UI, deterministic native ASR and server PCM, delayed history. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http'),{execFileSync}=require('node:child_process');
const root=__dirname,read=name=>fs.readFileSync(path.join(root,name),'utf8');
const baseline=process.argv.includes('--baseline'),config={key:'conversation-regression-local',model:'Fred-test',version:'Windows-test',storage:'conversation-regression'};
const script=name=>'<script nonce="qa">'+(baseline&&name==='conversation.js'?execFileSync('git',['show','0354e91:client-qwen/conversation.js'],{cwd:root,encoding:'utf8'}):read(name)).replaceAll('</script','<\\/script')+'</script>';
const html=read('chat.html').replace('__UI_CSS__',read('ui.css')).replace('__CONFIG__',JSON.stringify(config)).replaceAll('__NONCE__','qa')
  .replace('</head>',()=>script('vendor/markdown-it.min.js')+script('markdown.js')+'</head>')
  .replace('</body>',()=>read('workspace.html')+['ui.js','attachments.js','corrector.js','selection.js','thinking.js','voice.js','conversation.js'].map(script).join('')+'</body>');
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function until(work,label){for(let i=0;i<400;i++){if(await work())return;await sleep(25);}throw new Error('Timeout: '+label);}

async function main(){
  const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
  const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH||'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const state={history:null,revision:'1',preferences:{},native:{phase:'idle',installed:true,session:'',speech_id:0,partial:'',turns:[]},calls:[],chats:[],runs:new Map(),syncDelay:0,syncActive:0,acks:[],stops:0,cancels:[],voiceCancels:[],speech:[],timers:new Set(),holdChat:false,longVoice:false,pendingChat:null};
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
      if(body.action==='start')state.native={...state.native,phase:'listening',session:'qa-conversation',turns:[],speech_id:0};
      if(body.action==='ack'){assert.equal(body.session,state.native.session);state.acks.push(body.turn);state.native.turns=state.native.turns.filter(turn=>turn.id>body.turn);}
      if(body.action==='stop'){assert.equal(body.session,state.native.session);state.stops++;state.native={...state.native,phase:'stopped',turns:[],partial:''};}
      return json(res,state.native);
    }
    if(req.url==='/v1/models')return json(res,{data:[{id:'Fred-test',capabilities:{images:false,thinking:true,reasoning_efforts:['none','low','medium','high']}}]});
    if(req.url==='/v1/status')return json(res,{protocol:3,agent_protocol:4,version:'test'});
    if(req.url==='/v1/workspace')return json(res,{projects:[],jobs:[]});
    if(req.url==='/v1/notifications')return json(res,{items:[],unread:0});
    if(req.url==='/v1/context')return json(res,{tokens:15,capacity:4096,estimated:true});
    if(req.url==='/v1/agent/action')return json(res,state.runs.get(body.request_id)||{request_id:body.request_id,conversation_id:body.conversation_id,status:'unknown'});
    if(req.url==='/v1/voice/status')return json(res,{ready:true,enabled:true});
    if(req.url==='/v1/voice/cancel'){state.voiceCancels.push(body.request_id);return json(res,{cancelled:true});}
    if(req.url==='/v1/voice/speech'){
      state.speech.push({id:body.request_id,text:body.text});res.writeHead(200,{'Content-Type':'text/event-stream; charset=utf-8'});
      const pcm=Buffer.alloc(4800*2).toString('base64'),frames=state.longVoice?30:3;
      for(let i=0;i<frames;i++)later(()=>event(res,{id:body.request_id,rate:24000,pcm}),50+i*30);
      later(()=>{event(res,{id:body.request_id,done:true});if(!res.destroyed&&!res.writableEnded)res.end();},50+frames*30);return;
    }
    if(req.url==='/v1/cancel'){
      state.cancels.push(req.headers['x-qwen-request']);const pending=state.pendingChat;
      if(pending&&pending.body.turn_id===req.headers['x-qwen-request']){state.runs.set(pending.body.turn_id,{request_id:pending.body.turn_id,conversation_id:pending.body.conversation_id,status:'cancelled',text:''});if(!pending.res.destroyed&&!pending.res.writableEnded)pending.res.end('data: [DONE]\n\n');state.pendingChat=null;}
      return json(res,{cancelled:true});
    }
    if(req.url==='/v1/chat/completions'){
      assert.equal(body.turn_id,req.headers['x-qwen-request']);state.chats.push(body);state.runs.set(body.turn_id,{request_id:body.turn_id,conversation_id:body.conversation_id,status:'running',text:''});
      res.writeHead(200,{'Content-Type':'text/event-stream; charset=utf-8'});event(res,{hermes_status:{phase:'working',message:'Hermes prépare la réponse'}});
      if(state.holdChat){state.pendingChat={body,res};return;}
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
    await page.goto('http://127.0.0.1:'+server.address().port);await page.waitForSelector('#conversation-start:not([disabled])');await page.click('#conversation-start');await page.waitForFunction(()=>window.conversationBusy);
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
    state.native.speech_id=6;state.native.partial='Stop.';await until(()=>state.voiceCancels.includes(speechId),'barge-in cancels the correct speech');assert(await page.evaluate(()=>window.__audio.stopped>0));await page.waitForFunction(()=>!busy&&!historySyncPending);
    await page.click('#conversation-start');await page.waitForFunction(()=>!window.conversationBusy&&!document.getElementById('prompt').readOnly);assert.equal(state.native.phase,'stopped');assert.equal(state.stops,1);assert.deepEqual(errors,[]);
    console.log(JSON.stringify({passed:true,source:baseline?'0354e91':'working-tree',checks:['Hermes final + delayed sync preserves session and complete text','all three PCM frames finish without automatic cancellation','second ASR turn waits for history sync and submits exactly once','same conversation with unique turn IDs','real new speech during calculation cancels original turn','speech playback barge-in cancels correct audio and scheduled sources','hangup returns controls'],chats:state.chats.length,acks:state.acks,simulation:'native ASR and PCM timing; no hardware microphone or server models'},null,2));
  }catch(error){console.error(JSON.stringify({passed:false,source:baseline?'0354e91':'working-tree',snapshot,native:state.native,stops:state.stops,cancels:state.cancels,voiceCancels:state.voiceCancels},null,2));throw error;}
  finally{for(const timer of state.timers)clearTimeout(timer);await browser.close();server.closeAllConnections?.();await new Promise(resolve=>server.close(resolve));}
}
main().catch(error=>{console.error(error);process.exitCode=1;});
