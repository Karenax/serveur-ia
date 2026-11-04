'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const root=__dirname,read=name=>fs.readFileSync(path.join(root,name),'utf8');
const script=name=>'<script nonce="qa">'+read(name).replaceAll('</script','<\\/script')+'</script>';
const config={key:'fixture-codex-local-key',storage:'codex-ui',version:'test'};
const html=read('chat.html').replace('__UI_CSS__',read('ui.css')).replace('__CONFIG__',JSON.stringify(config)).replaceAll('__NONCE__','qa')
 .replace('</head>',()=>script('vendor/markdown-it.min.js')+script('markdown.js')+'</head>')
 .replace('</body>',()=>read('workspace.html')+['ui.js','attachments.js','corrector.js','selection.js','thinking.js','voice.js','conversation.js'].map(script).join('')+'</body>');
async function main(){
 const state={history:null,revision:'1',calls:[],fail:false,hold:false,pending:null};
 const json=(res,value,status=200)=>{res.writeHead(status,{'Content-Type':'application/json; charset=utf-8'});res.end(JSON.stringify(value));};
 const server=http.createServer(async(req,res)=>{
  let raw='';for await(const block of req)raw+=block;const body=JSON.parse(raw||'{}');
  if(req.url==='/'){res.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});res.end(html);return;}
  if(req.headers.authorization!=='Bearer '+config.key)return json(res,{},401);
  if(req.url==='/client/state')return json(res,{version:'test',preferences:{},update:{message:'À jour'},local_api:'http://127.0.0.1:8000/v1',key:config.key,connection:{connected:true,model:'fred-qwen',transport:'https',checked_at:Date.now()/1000}});
  if(req.url==='/v1/models')return json(res,{source:'hermes',default_model:'fred-qwen',data:[{id:'fred-qwen',label:'Qwen local',available:true,capabilities:{thinking:false}},{id:'cloud',label:'Cloud de test',available:true,capabilities:{thinking:false}}]});
  if(req.url==='/client/history'&&req.method==='GET')return json(res,{history:state.history,revision:state.revision});
  if(req.url==='/client/history/sync'){state.history=state.history||body.initial;return json(res,{history:state.history,revision:state.revision,message:'Synchronisé'});}
  if(req.url==='/client/history'){state.history=body.history;return json(res,{saved:true,revision:state.revision});}
  if(req.url==='/client/draft')return json(res,{draft:null});
  if(req.url==='/client/integrations')return json(res,{apps:Object.fromEntries(['codex','hermes','opencode'].map(name=>[name,{installed:true,supported:true}]))});
  if(req.url==='/client/integrations/apply'){
   state.calls.push(body);
   const finish=()=>state.fail?json(res,{error:{message:'Téléchargement Codex interrompu. Réessayez.'}},503):json(res,{message:'Fournisseur Kiara ajouté. Les réglages ChatGPT par défaut sont conservés.',backups:['C:/fixture/.codex/config.toml.before-kiara-test']});
   if(state.hold)state.pending=finish;else finish();return;
  }
  if(req.url==='/client/voice'||req.url==='/client/conversation')return json(res,{phase:'idle',installed:false});
  if(req.url==='/v1/workspace')return json(res,{projects:[],jobs:[]});
  if(req.url==='/v1/notifications')return json(res,{items:[],unread:0});
  if(req.url==='/v1/status')return json(res,{protocol:4});
  return json(res,{});
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const {chromium,options}=require('./browser_test_support.cjs'),browser=await chromium.launch(options);
 const output=require('./test_artifacts.cjs').directory('codex-integration');
 try{
  const page=await browser.newPage({viewport:{width:1280,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:'+server.address().port);await page.waitForSelector('#send:not([disabled])');
  await page.evaluate(()=>showView('api'));await page.waitForSelector('#integration-codex:not([disabled])');
  assert.equal(await page.textContent('#integration-codex'),'Ajouter à Codex');
  await page.locator('#integration-codex-guide summary').click();
  assert((await page.textContent('#integration-codex-guide')).includes('télécharge et vérifie'));
  await page.locator('[data-view="api"] .settings-card:last-child').screenshot({path:path.join(output,'desktop.png')});
  state.hold=true;await page.click('#integration-codex');await page.waitForFunction(()=>document.getElementById('integration-result').textContent.includes('Téléchargement'));
  assert(await page.isDisabled('#integration-hermes'));assert(await page.isDisabled('#integration-opencode'));assert(await page.isDisabled('#integration-codex'));
  assert.equal(state.calls.length,1);state.pending();state.hold=false;
  await page.waitForFunction(()=>document.getElementById('integration-result').textContent.includes('Fournisseur Kiara ajouté'));
  assert.deepEqual(state.calls[0],{app:'codex',model:'fred-qwen'});assert(!('key' in state.calls[0]));
  assert(await page.isVisible('#integration-backup'));await page.locator('#integration-backup summary').click();
  assert((await page.textContent('#integration-backup-path')).includes('before-kiara'));
  state.fail=true;await page.evaluate(()=>document.getElementById('integration-codex-guide').open=false);await page.click('#integration-codex');
  await page.waitForFunction(()=>document.getElementById('integration-result').textContent.includes('interrompu'));
  assert(await page.evaluate(()=>document.getElementById('integration-codex-guide').open));assert(await page.isEnabled('#integration-codex'));
  await page.evaluate(()=>{connected=false;uiIntegrationButtons();});assert(await page.isDisabled('#integration-codex'));
  await page.evaluate(()=>{connected=true;const previous=conversationModel;conversationModel=()=> 'cloud';uiIntegrationButtons();conversationModel=previous;});
  assert(await page.isDisabled('#integration-codex'));assert((await page.textContent('#integration-codex-state')).includes('Qwen local'));
  await page.evaluate(()=>uiIntegrationButtons());await page.setViewportSize({width:390,height:844});
  await page.evaluate(()=>uiCloseSidebar(false));
  await page.waitForFunction(()=>document.querySelector('.sidebar').getBoundingClientRect().right<=1);
  await page.locator('[data-view="api"] .settings-card:last-child').screenshot({path:path.join(output,'narrow.png')});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.focus('#integration-codex');assert(await page.locator('#integration-codex').evaluate(el=>el===document.activeElement));
  assert.deepEqual(errors,[]);console.log('Codex integration UI passed: download state, result, backup, recovery, model guard, keyboard and narrow width.');
 }finally{await browser.close();await new Promise(resolve=>server.close(resolve));}
}
main().catch(e=>{console.error(e);process.exitCode=1;});
