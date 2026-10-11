/* Syntax and optional browser checks for the generated, shared Android UI. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const http=require('node:http');
const root=path.resolve(__dirname,'..');
const source=fs.readFileSync(path.join(root,'app/src/main/assets/android-chat.html'),'utf8');
const config={key:'android-ui-test-local-key',model:'Fred-test',version:'Android-test',storage:'ui-test',platform:'android'};
const html=source.replace('__CONFIG__',JSON.stringify(config)).replaceAll('__NONCE__','android-ui-test');
const scripts=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(match=>match[1]);
assert.equal(scripts.length,11,'All shared scripts and the Android layer must be assembled');
scripts.forEach((script,index)=>new vm.Script(script,{filename:'android-inline-'+index+'.js'}));
assert(!source.includes('__UI_CSS__'));
assert(!source.includes("'/client/update/"));
assert(!source.includes("'/client/integrations"));
assert(!source.includes('EXE'));
console.log('Android inline JavaScript syntax verified ('+scripts.length+' scripts)');
if(!process.argv.includes('--browser'))process.exit(0);

async function browserCheck(){
  const playwrightPath=process.env.PLAYWRIGHT_MODULE||'playwright';
  const {chromium}=require(playwrightPath);
  const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH||'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const state={profile:false,required:true,transport:'https',history:null,revision:'1',draft:null,preferences:{},requests:[],jsonFallback:false};
  const project={id:'project-1',title:'Projet mobile',instructions:'',archived:false,revision:1,documents:[],memories:[],conversations:[]};
  const respond=(res,value,status=200)=>{res.writeHead(status,{'Content-Type':'application/json; charset=utf-8'});res.end(JSON.stringify(value));};
  const server=http.createServer(async(req,res)=>{
    let raw='';for await(const chunk of req)raw+=chunk;let body={};try{body=JSON.parse(raw||'{}');}catch{}
    if(req.url==='/'){res.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});return res.end(html);}
    if(req.url==='/__bridge/import'){state.profile=true;state.required=true;return respond(res,{ok:true});}
    if(req.url==='/__bridge/mode'){state.transport=body.mode;state.required=false;return respond(res,{ok:true});}
    state.requests.push({path:req.url,method:req.method});
    if(req.headers.authorization!=='Bearer '+config.key)return respond(res,{error:{message:'Clé locale manquante'}},401);
    if(req.url==='/client/state')return respond(res,{version:'Android-test',profile_required:!state.profile,profile:{name:'Profil mobile de test'},preferences:state.preferences,history:{message:'Historique enregistré',needs_merge:false},endpoint:'https://example.test',connection:{transport:state.transport,endpoint:'https://example.test',connected:state.profile&&!state.required,connection_required:state.required,checked_at:Date.now()/1000}});
    if(req.url==='/client/history'&&req.method==='GET')return respond(res,{history:state.history,revision:state.revision});
    if(req.url==='/client/history/sync'){state.history=state.history||body.initial;return respond(res,{history:state.history,revision:state.revision,message:'Historique synchronisé',merged:false});}
    if(req.url==='/client/history'){state.history=body.history;state.revision=String(Number(state.revision)+1);return respond(res,{saved:true,revision:state.revision,message:'Historique enregistré'});}
    if(req.url==='/client/preferences'){state.preferences=body;return respond(res,{saved:true});}
    if(req.url==='/client/draft'){if(req.method==='POST')state.draft=body.draft;return respond(res,{draft:state.draft});}
    if(req.url==='/v1/models')return respond(res,{data:[{id:'Fred-test',capabilities:{images:false,files:['txt','md','pdf','docx'],thinking:true,reasoning_efforts:['none','low','medium','high']}}]});
    if(req.url==='/v1/status')return respond(res,{protocol:3,version:'test'});
    if(req.url==='/v1/workspace')return respond(res,{projects:[project],jobs:[]});
    if(req.url==='/v1/context')return respond(res,{tokens:15,capacity:4096,estimated:false});
    if(req.url==='/v1/chat/completions'){
      if(state.jsonFallback)return respond(res,{choices:[{message:{role:'assistant',content:'Le correcteur accepte une réponse JSON.'},finish_reason:'stop'}]});
      res.writeHead(200,{'Content-Type':'text/event-stream; charset=utf-8','Cache-Control':'no-cache'});
      res.write('data: '+JSON.stringify({choices:[{delta:{content:'Bonjour depuis '}}]})+'\n\n');
      setTimeout(()=>{res.write('data: '+JSON.stringify({choices:[{delta:{content:'**Android**.'},finish_reason:'stop'}]})+'\n\n');res.end('data: [DONE]\n\n');},80);return;
    }
    if(req.url==='/v1/workspace/action'){
      if(body.action==='attachment_extract')return respond(res,{text:Buffer.from(body.data,'base64').toString('utf8')});
      if(body.action==='project_create')return respond(res,{id:project.id});
      return respond(res,{});
    }
    if(req.url==='/v1/cancel')return respond(res,{cancelled:true});
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
        importProfile(){window.__androidCalls.push({method:'importProfile'});nativeRequest('/__bridge/import');location.reload();},
        setConnectionMode(mode){window.__androidCalls.push({method:'setConnectionMode',mode});return nativeRequest('/__bridge/mode',{mode});},
        openSettings(){window.__androidCalls.push({method:'openSettings'});},
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
    await page.click('#choose-https');
    await page.waitForSelector('#send:not([disabled])');
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
    await page.click('#export-conversations');
    await page.waitForFunction(()=>window.__androidCalls.some(call=>call.method==='exportFile'));
    const exported=await page.evaluate(()=>window.__androidCalls.find(call=>call.method==='exportFile'));
    assert.equal(exported.name,'conversations-fred.json');assert.equal(exported.mime,'application/json');
    assert.equal(JSON.parse(Buffer.from(exported.data,'base64')).conversations[0].messages.length,2);
    assert.equal(JSON.parse(Buffer.from(exported.data,'base64')).conversations[0].messages[0].attachments[0].name,'note-mobile.txt');
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
    const blockedFlush=await page.evaluate(async()=>{const previous=historyBlocked;try{historyBlocked=true;return await window.androidFlush();}finally{historyBlocked=previous;error('');buttons();}});
    assert.equal(blockedFlush,false,'Blocked history must prevent the native close from accepting a false save confirmation');
    assert.equal(await page.evaluate(()=>window.androidFlush()),true,'Healthy history should still flush');
    assert(!(await page.evaluate(()=>[...document.querySelectorAll('[data-view-button]')].some(button=>['updates','api'].includes(button.dataset.viewButton)))));
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
    console.log('Android browser checks passed: onboarding, explicit HTTPS/WireGuard choice, streamed chat, attachments, multiline keyboard, clipboard, history import/export, projects, corrector JSON fallback, blocked history close, resized keyboard composer, phone/tablet layout');
    await page.close();
  }finally{await browser.close();await new Promise(resolve=>server.close(resolve));}
}
browserCheck().catch(error=>{console.error(error);process.exitCode=1;});
