/* Windows shared UI: server-agent events, voice output, decisions and corrector. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http'),vm=require('node:vm');
const root=__dirname,read=name=>fs.readFileSync(path.join(root,name),'utf8');
const config={key:'windows-hermes-test-key',model:'Fred-test',version:'Windows-test',storage:'hermes-ui-test'};
const script=name=>'<script nonce="test">'+read(name).replaceAll('</script','<\\/script')+'</script>';
const html=read('chat.html').replace('__UI_CSS__',read('ui.css')).replace('__CONFIG__',JSON.stringify(config)).replaceAll('__NONCE__','test')
  .replace('</head>',()=>script('vendor/markdown-it.min.js')+script('markdown.js')+'</head>')
  .replace('</body>',()=>read('workspace.html')+['ui.js','attachments.js','corrector.js','selection.js','thinking.js','voice.js','conversation.js'].map(script).join('')+'</body>');
[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].forEach((match,index)=>new vm.Script(match[1],{filename:'windows-inline-'+index+'.js'}));

async function main(){
  const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
  const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH||'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const state={history:null,revision:'1',preferences:{},requests:[],pending:null,approval:false,disconnectApproval:false,runs:new Map()};
  const json=(res,value,status=200)=>{res.writeHead(status,{'Content-Type':'application/json'});res.end(JSON.stringify(value));};
  const server=http.createServer(async(req,res)=>{
    let raw='';for await(const chunk of req)raw+=chunk;const body=JSON.parse(raw||'{}');
    if(req.url==='/'){res.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});res.end(html);return;}
    state.requests.push({path:req.url,body,requestId:req.headers['x-qwen-request']});
    if(req.headers.authorization!=='Bearer '+config.key)return json(res,{error:{message:'Unauthorized'}},401);
    if(req.url==='/client/state')return json(res,{version:'test',preferences:state.preferences,update:{message:'À jour',available:false,busy:false},endpoint:'https://example.test',internet_endpoint:'example.test:51820',local_api:'http://127.0.0.1/v1',key:config.key,connection:{connected:true,model:'Fred-test',transport:'https',endpoint:'https://example.test',checked_at:Date.now()/1000}});
    if(req.url==='/client/history'&&req.method==='GET')return json(res,{history:state.history,revision:state.revision});
    if(req.url==='/client/history/sync'){state.history=state.history||body.initial;return json(res,{history:state.history,revision:state.revision,message:'Synchronisé'});}
    if(req.url==='/client/history'){state.history=body.history;state.revision=String(Number(state.revision)+1);return json(res,{saved:true,revision:state.revision});}
    if(req.url==='/client/preferences'){state.preferences=body;return json(res,{saved:true});}
    if(req.url==='/client/integrations')return json(res,{apps:[]});
    if(req.url==='/client/draft')return json(res,{draft:null});
    if(req.url==='/client/voice'||req.url==='/client/conversation')return json(res,{phase:'idle',installed:false});
    if(req.url==='/v1/models')return json(res,{data:[{id:'Fred-test',capabilities:{images:false,thinking:true,reasoning_efforts:['none','low','medium','high']}}]});
    if(req.url==='/v1/status')return json(res,{protocol:4,version:'test'});
    if(req.url==='/v1/workspace')return json(res,{projects:[],jobs:[]});
    if(req.url==='/v1/notifications')return json(res,{items:[],unread:0});
    if(req.url==='/v1/context')return json(res,{tokens:15,capacity:4096,estimated:true});
    if(req.url==='/v1/agent/action'&&body.action==='approval'){
      const pending=state.pending;assert(['once','deny'].includes(body.decision));assert.equal(body.request_id,pending.approval.request_id);assert.notEqual(body.request_id,pending.turn_id);assert.equal(req.headers['x-qwen-request'],pending.turn_id);assert.equal(body.conversation_id,pending.conversation_id);state.runs.set(pending.turn_id,{request_id:pending.turn_id,conversation_id:pending.conversation_id,status:'running',text:''});json(res,{accepted:true});const text=body.decision==='once'?'Action autorisée et résultat vérifié.':'Action refusée, aucun fichier modifié.';if(state.disconnectApproval)setTimeout(()=>pending.finish(text),1800);else pending.finish(text);return;
    }
    if(req.url==='/v1/chat/completions'){
      assert.equal(body.turn_id,req.headers['x-qwen-request']);assert(body.conversation_id);assert.equal(typeof body.history_revision,'string');
      res.writeHead(200,{'Content-Type':'text/event-stream; charset=utf-8'});
      const event=value=>res.write('data: '+JSON.stringify(value)+'\n\n');
      event({hermes_status:{phase:'tool',message:'Recherche dans vos documents'}});
      event({hermes_answer:{text:'',reasoning_content:''}});
      const finish=text=>{state.runs.set(body.turn_id,{request_id:body.turn_id,conversation_id:body.conversation_id,status:'completed',text,reasoning_content:'',sources:[]});if(res.destroyed||res.writableEnded)return;event({hermes_answer:{text,reasoning_content:'',final:true}});event({choices:[{delta:{},finish_reason:'stop'}]});event({hermes_run:{request_id:body.turn_id,conversation_id:body.conversation_id,status:'completed'}});res.end('data: [DONE]\n\n');};
      if(state.approval){const approval={request_id:'receipt_'+body.turn_id,description:'Modifier le document <script>alert(1)</script>',expires_epoch:Date.now()/1000+60};state.pending={...body,approval,finish};state.runs.set(body.turn_id,{request_id:body.turn_id,conversation_id:body.conversation_id,status:'waiting_for_approval',text:'',approval});event({hermes_approval:approval});setTimeout(()=>{if(res.destroyed)return;event({hermes_status:{phase:'approval',message:'Votre accord est toujours attendu.'}});if(state.disconnectApproval)res.end();},50);return;}
      setTimeout(()=>finish('Voici uniquement la réponse finale.'),50);return;
    }
    if(req.url==='/v1/agent/action'&&body.action==='reconcile')return json(res,state.runs.get(body.request_id)||{request_id:body.request_id,conversation_id:body.conversation_id,status:'unknown',text:''});
    return json(res,{});
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  try{
    const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    await page.goto('http://127.0.0.1:'+server.address().port);await page.waitForSelector('#send:not([disabled])');
    await page.evaluate(()=>{window.__spoken=[];window.conversationDelta=text=>window.__spoken.push(text);});
    await page.fill('#prompt','Une question simple.');await page.click('#send');await page.waitForSelector('#send:not([disabled])');
    assert.equal((await page.textContent('.message.assistant .content')).trim(),'Voici uniquement la réponse finale.');
    assert.deepEqual(await page.evaluate(()=>window.__spoken),['Voici uniquement la réponse finale.'],'Voice must receive final text once and no tool progress');
    const chat=state.requests.find(request=>request.path==='/v1/chat/completions');assert.equal(state.history.conversations[0].messages[0].turn_id,chat.body.turn_id);
    state.approval=true;await page.click('#new');await page.fill('#prompt','Modifie le document.');await page.click('#send');await page.waitForSelector('#agent-approval:not([hidden])');
    await page.waitForFunction(()=>document.getElementById('queue-state').textContent.includes('toujours'));assert(await page.isVisible('#agent-approval'),'An approval heartbeat must preserve the opaque receipt');
    assert.equal(await page.locator('#agent-approval script').count(),0);assert((await page.textContent('#agent-approval')).includes('<script>alert(1)</script>'));await page.click('#agent-deny');await page.waitForSelector('#send:not([disabled])');
    assert.equal((await page.textContent('.message.assistant .content')).trim(),'Action refusée, aucun fichier modifié.');
    await page.click('#new');await page.fill('#prompt','Autorise cette action une fois.');await page.click('#send');await page.waitForFunction(()=>document.getElementById('queue-state').textContent.includes('toujours'));assert(await page.isVisible('#agent-approval'));await page.click('#agent-approve');await page.waitForSelector('#send:not([disabled])');assert((await page.textContent('.message.assistant .content')).includes('résultat vérifié'));
    state.disconnectApproval=true;await page.click('#new');await page.fill('#prompt','Une action à reprendre après fermeture.');await page.click('#send');await page.waitForFunction(()=>replyProgress.agentStatus==='waiting_for_approval');await page.evaluate(()=>{messages.at(-1).content='Une réponse encore incomplète';return flushHistory();});const pendingTurn=state.pending.turn_id,pendingConversation=state.pending.conversation_id,chatCount=state.requests.filter(request=>request.path==='/v1/chat/completions').length;
    await page.reload();await page.waitForSelector('#agent-approval:not([hidden])');assert.equal(await page.evaluate(()=>requestId),pendingTurn);assert.equal(await page.evaluate(()=>currentId),pendingConversation);assert.equal(state.requests.filter(request=>request.path==='/v1/chat/completions').length,chatCount,'Reload must follow the original run without starting another chat');
    await page.click('#agent-approve');await page.waitForSelector('#send:not([disabled])');assert.equal(await page.locator('.message.assistant').count(),1);assert((await page.textContent('.message.assistant .content')).includes('résultat vérifié'));state.disconnectApproval=false;
    state.approval=false;await page.evaluate(()=>showView('corrector'));await page.fill('#corrector-text','Je veut un texte correct.');await page.click('#corrector-correct');await page.waitForFunction(()=>document.getElementById('corrector-status').textContent.includes('terminé'));await page.waitForFunction(()=>!busy&&!historySyncPending);
    const correction=state.requests.filter(request=>request.path==='/v1/chat/completions').at(-1);const row=state.history.conversations.find(c=>c.id===correction.body.conversation_id);
    assert.equal(correction.body.messages[1].content,row.messages[0].content);assert.equal(row.messages[1].turn_id,correction.body.turn_id);assert(correction.body.messages[0].content.includes('Corrige'));assert.deepEqual(errors,[]);
    console.log('Windows Hermes UI verified: final-only voice, stable turns, opaque approvals across heartbeat/disconnect/reload, once/refusal, corrector and shared scripts.');
    await page.close();
  }finally{await browser.close();await new Promise(resolve=>server.close(resolve));}
}
main().catch(error=>{console.error(error);process.exitCode=1;});
