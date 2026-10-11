const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http'),crypto=require('node:crypto');
const {chromium}=require('C:/Users/karen/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'../../..'),web=path.join(root,'lanceur/web');
const proofArg=process.argv.indexOf('--proof'),proof=proofArg>=0?path.resolve(process.argv[proofArg+1]):null;
const adminToken='fixture-admin-'+crypto.randomUUID(),events=[],errors=[],checks=[];
const ids=['a','b','c','d','e'].map(c=>c.repeat(16));
const clients=ids.map((id,index)=>({id,name:'Compte synthétique '+(index+1),suspended:index===2,revoked:index===4,hermes_pending:index===3,hermes:{ready:index!==3},device_kind:'pc',device_owner:'Fixture',last_activity_epoch:0,reported_version:'fixture'}));
const modelIds=Array.from({length:80},(_,i)=>'fred-model-'+i.toString(16).padStart(24,'0'));
const nousIds=modelIds.slice(0,40),otherIds=modelIds.slice(40),offlineModel='fred-model-'+'f'.repeat(24);
let sharing={enabled:true,share_all:false,shared_accounts:[ids[0]],exposed_models:null,hermes_context:{profile:'Profil synthétique',main_model:'Modele principal synthétique',main_provider:'Fixture'},providers:[{label:'Nous Portal',model_count:40,available_model_count:40,configured:true,available:true},{label:'Fournisseur synthétique',model_count:40,available_model_count:40,configured:true,available:true},{label:'Fournisseur indisponible',model_count:3,available_model_count:0,configured:true,available:false},{label:'NON_CONFIGURE',model_count:0,configured:false}],models:modelIds.map((id,i)=>({id,name:'Modèle synthétique '+String(i+1).padStart(3,'0'),provider:i<40?'Nous Portal':'Fournisseur synthétique',available:true,exposed:true})).concat({id:offlineModel,name:'MODELE_INDISPONIBLE',provider:'Fixture',available:false,exposed:true})},rejectOnce=false;
const settings={context:8192,workers:15,prefill:256,vram_reserve:512,history_enabled:true,history_slots:2,history_every:16384,mtp_enabled:true,spec:3,spec_min_p:.5,layer_split:24,expert_cache:'auto',short_read:0,min_free_ram_gib:6,gpus:'0,1',host:'127.0.0.1',port:8080,api_key:'',model_name:'Fixture',cors_origins:'',trusted_origins:'',pack:'Fixture',native:'Fixture',tokenizer:'Fixture',expert_profile:'Fixture'};
const remote=()=>({clients,devices:clients,archived_clients:[],enabled:true,client_compiled:true,gateway_available:true,hermes:{available:true},connection:{message:'Fixture',public_host:'fixture.invalid',listen_port:51820,compiled:true,firewall:{state:'ready',port:51820,message:'Fixture'}}});
const reply=(res,body,status=200)=>{res.writeHead(status,{'Content-Type':'application/json; charset=utf-8'});res.end(JSON.stringify(body));};
const server=http.createServer(async(req,res)=>{try{
 const url=new URL(req.url,'http://127.0.0.1'),route=url.pathname;
 if(!route.startsWith('/api/')){
  const name=route==='/'?'index.html':route.slice(1);if(!['index.html','app.js','app.css','workspace.js','interface.js','interface.css','maintenance.js','maintenance.css','notifications.js','notifications.css','voice.js'].includes(name)){res.writeHead(404);return res.end();}
  let data=fs.readFileSync(path.join(web,name));if(name==='index.html')data=Buffer.from(data.toString('utf8').replace('__TOKEN__',adminToken));
  res.writeHead(200,{'Content-Type':name.endsWith('.js')?'text/javascript':name.endsWith('.css')?'text/css':'text/html'});return res.end(data);
 }
 let raw='';for await(const chunk of req)raw+=chunk;const body=raw?JSON.parse(raw):{};
 const authenticated=req.headers['x-launcher-token']===adminToken;
 events.push({path:route,query:url.search,method:req.method,authenticated,body});
 if(route!=='/api/voice'&&!authenticated)return reply(res,{error:'Fixture admin token required'},403);
 if(route==='/api/hermes/models')return reply(res,{...sharing,models:sharing.models.map(model=>({...model,exposed:sharing.exposed_models===null||sharing.exposed_models.includes(model.id)}))});
 if(route==='/api/hermes/models/configure'){
  assert.equal(req.method,'POST');assert(Object.keys(body).every(key=>['share_all','shared_accounts','exposed_models'].includes(key)));
  await new Promise(r=>setTimeout(r,250));
  if(rejectOnce){rejectOnce=false;return reply(res,{error:'Échec synthétique du partage'},400);}
  if('share_all'in body){assert.equal(typeof body.share_all,'boolean');sharing.share_all=body.share_all;}
  if('shared_accounts'in body){assert(Array.isArray(body.shared_accounts));sharing.shared_accounts=[...body.shared_accounts];}
  if('exposed_models'in body){assert(body.exposed_models===null||Array.isArray(body.exposed_models));sharing.exposed_models=body.exposed_models===null?null:[...body.exposed_models];}
  return reply(res,{message:'Fixture saved'});
 }
 if(route==='/api/remote'||route==='/api/devices')return reply(res,remote());
 if(route==='/api/settings'||route==='/api/defaults')return reply(res,settings);
 if(route==='/api/state')return reply(res,{status:'arrete',running:false,ram:{available_gib:64,total_gib:128,percent:50},gpus:[],disks:[],logs:'Fixture',queue:{},lan_ips:['127.0.0.1'],operations:{version:'fixture'}});
 if(route==='/api/operations')return reply(res,{startup:false,autoload:false,restart:false});
 if(route==='/api/releases')return reply(res,{server_version:'fixture',release:{version:'fixture'},verified:true});
 if(route==='/api/workspace')return reply(res,{owners:[],jobs:[],events:[],used_bytes:0,global_bytes:104857600,web_enabled:false,web_key_configured:false});
 if(route==='/api/client-storage')return reply(res,{root:'Fixture',transaction_database:'Fixture',clients:[]});
 if(route==='/api/backups')return reply(res,{config:{enabled:false,retention:{daily:7,weekly:4,monthly:6}},catalog:[],job:{state:'idle'},last_success:null});
 if(route==='/api/maintenance')return reply(res,{state:'idle',active:false});
 if(route==='/api/notifications')return reply(res,{items:[],unread_count:0,generation:'fixture',preferences:{types:{},revision:1},subscription:{enabled:false}});
 if(route==='/api/voice')return reply(res,{enabled:false});
 return reply(res,{error:'Unknown isolated fixture API'},404);
 }catch(error){errors.push('Fixture: '+error.message);reply(res,{error:'Fixture rejected'},500);}});
(async()=>{
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const base='http://127.0.0.1:'+server.address().port;
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 try{
  const context=await browser.newContext({viewport:{width:1440,height:1000}});
  await context.route('**/*',route=>{const url=new URL(route.request().url());return url.origin===base||url.protocol==='data:'?route.continue():route.abort();});
  const page=await context.newPage();page.on('pageerror',error=>errors.push(error.message));
  const check=async(name,work)=>{await work();checks.push({name,passed:true});};
  const provider=label=>page.locator('#hermes-provider-list input[data-provider="'+label+'"]');
  const waitSaved=()=>page.waitForFunction(()=>!document.getElementById('hermes-models-auto').disabled);
  const refreshCatalogue=async()=>{
   const previous=await page.locator('#hermes-models-auto').elementHandle();
   await page.getByRole('button',{name:'Actualiser les modèles',exact:true}).click();
   await page.waitForFunction(element=>!element.isConnected,previous);await previous.dispose();await waitSaved();
  };
  const assertGrants=()=>{assert.equal(sharing.share_all,false);assert.deepEqual(sharing.shared_accounts,[ids[1]]);};
  const assertModelOnlyPost=()=>{const event=events.filter(e=>e.path==='/api/hermes/models/configure').at(-1);assert(event.authenticated);assert.deepEqual(Object.keys(event.body),['exposed_models']);};
  await page.goto(base+'/#clients');await page.waitForSelector('#models-'+ids[1]);
  await check('Authenticated admin GET, unavailable-provider label and quota/separation notice',async()=>{
   assert(events.some(e=>e.path==='/api/hermes/models'&&e.method==='GET'&&e.authenticated));
   assert.equal(await page.locator('#clients').isVisible(),true);assert.equal(await page.locator('#hermes-model-sharing').isVisible(),true);
   const text=await page.locator('#hermes-model-sharing').innerText();assert(text.includes('mêmes abonnements, crédits et quotas'));assert(text.includes('conversations restent séparées'));assert(text.includes('Fournisseur synthétique'));assert(text.includes('connexion indisponible'));assert(!text.includes('NON_CONFIGURE'));
   assert(text.includes('Profil Hermes : Profil synthétique'));assert(text.includes('Modèle courant : Modele principal synthétique'));
  });
  await check('Initial individual grants and lifecycle restrictions',async()=>{
   assert.equal(await page.locator('#models-'+ids[0]).isChecked(),true);assert.equal(await page.locator('#models-'+ids[1]).isChecked(),false);
   assert.equal(await page.locator('#models-'+ids[0]).isDisabled(),false);assert.equal(await page.locator('#models-'+ids[1]).isDisabled(),false);
   assert.equal(await page.locator('#models-'+ids[2]).isDisabled(),true);assert.equal(await page.locator('#models-'+ids[3]).isDisabled(),true);assert.equal(await page.locator('#models-'+ids[4]).count(),0);
  });
  await check('Global checkbox POST and disabled per-account controls',async()=>{
   await page.locator('#hermes-share-all').check();assert.equal(await page.locator('#hermes-share-all').isDisabled(),true);
   await page.waitForFunction(()=>{const all=document.getElementById('hermes-share-all');return all?.checked&&!all.disabled;});
   for(const id of ids.slice(0,4)){assert.equal(await page.locator('#models-'+id).isChecked(),true);assert.equal(await page.locator('#models-'+id).isDisabled(),true);}
   assert(events.some(e=>e.path==='/api/hermes/models/configure'&&e.authenticated&&e.body.share_all===true));
  });
  await check('Disabling global sharing restores preserved individual grants',async()=>{
   await page.locator('#hermes-share-all').uncheck();await page.waitForFunction(()=>{const all=document.getElementById('hermes-share-all');return all&&!all.checked&&!all.disabled;});
   await page.waitForFunction(id=>!document.getElementById('models-'+id)?.disabled,ids[1]);
   assert.deepEqual(sharing.shared_accounts,[ids[0]]);assert.equal(await page.locator('#models-'+ids[0]).isChecked(),true);assert.equal(await page.locator('#models-'+ids[1]).isChecked(),false);
   assert.equal(await page.locator('#models-'+ids[2]).isDisabled(),true);assert.equal(await page.locator('#models-'+ids[3]).isDisabled(),true);
   assert(events.some(e=>e.path==='/api/hermes/models/configure'&&e.authenticated&&e.body.share_all===false));
  });
  await check('Per-account grant and removal POST only the individual list',async()=>{
   await page.locator('#models-'+ids[1]).check();await page.waitForFunction(id=>document.getElementById('models-'+id)?.checked&&!document.getElementById('models-'+id)?.disabled,ids[1]);
   assert.deepEqual(sharing.shared_accounts,[ids[0],ids[1]]);
   await page.locator('#models-'+ids[0]).uncheck();await page.waitForFunction(id=>!document.getElementById('models-'+id)?.checked&&!document.getElementById('models-'+id)?.disabled,ids[0]);
   assert.deepEqual(sharing.shared_accounts,[ids[1]]);assert(events.filter(e=>e.path==='/api/hermes/models/configure'&&Array.isArray(e.body.shared_accounts)).every(e=>Object.keys(e.body).length===1&&e.authenticated));
  });
  await check('Rejected save is visible and re-reads the authoritative grant state',async()=>{
   rejectOnce=true;await page.locator('#hermes-share-all').check();await page.waitForFunction(()=>document.getElementById('toast')?.textContent.includes('Échec synthétique'));
   await page.waitForFunction(()=>{const all=document.getElementById('hermes-share-all');return all&&!all.checked&&!all.disabled;});
   assert.equal(sharing.share_all,false);assert.deepEqual(sharing.shared_accounts,[ids[1]]);
  });
  await check('Automatic exposure keeps available models checked and hides unavailable models',async()=>{
   assert.equal(await page.locator('#hermes-models-auto').isChecked(),true);
   assert.equal(await page.locator('[data-model]').count(),80);
   assert.equal(await page.locator('[data-model]:checked').count(),80);
   assert.equal(await page.locator('[data-model]:disabled').count(),80);
   assert(!(await page.locator('#hermes-model-list').innerText()).includes('MODELE_INDISPONIBLE'));
   assert((await page.locator('#hermes-model-sharing').innerText()).includes('40 modèle(s) utilisable(s)'));
  });
  await check('Provider bulk disable exits automatic mode and retains other providers despite search',async()=>{
   assert.equal(await page.locator('#hermes-provider-list input[data-provider]').count(),2);
   for(const label of ['Nous Portal','Fournisseur synthétique']){assert.equal(await provider(label).isChecked(),true);assert.equal(await provider(label).isDisabled(),false);assert((await provider(label).locator('..').innerText()).includes('40 / 40'));}
   await page.locator('#hermes-model-search').fill('080');assert.equal(await page.locator('.hermes-model-row:visible').count(),1);
   await provider('Nous Portal').uncheck();assert.equal(await provider('Nous Portal').isDisabled(),true);assert.equal(await provider('Fournisseur synthétique').isDisabled(),true);assert.equal(await page.locator('#hermes-models-clear').isDisabled(),true);await waitSaved();
   assert.deepEqual(sharing.exposed_models,otherIds);assert.equal(await page.locator('#hermes-models-auto').isChecked(),false);
   assert.equal(await provider('Nous Portal').isChecked(),false);assert.equal(await provider('Fournisseur synthétique').isChecked(),true);
   assert.equal(await page.locator('[data-model]:checked').count(),40);assertModelOnlyPost();assertGrants();
  });
  await check('Provider bulk restore exposes its whole group',async()=>{
   await provider('Nous Portal').check();await waitSaved();assert.deepEqual(new Set(sharing.exposed_models),new Set(modelIds));
   assert.equal(await provider('Nous Portal').isChecked(),true);assert.equal(await provider('Fournisseur synthétique').isChecked(),true);
   assert.equal(await page.locator('[data-model]:checked').count(),80);assertModelOnlyPost();assertGrants();
  });
  await check('Partial providers are indeterminate; bulk actions ignore search and preserve offline IDs',async()=>{
   sharing.exposed_models=[...modelIds,offlineModel];await refreshCatalogue();
   await page.locator('[data-model="'+modelIds[0]+'"]').uncheck();await waitSaved();
   assert.deepEqual(await provider('Nous Portal').evaluate(el=>({checked:el.checked,indeterminate:el.indeterminate})),{checked:false,indeterminate:true});
   assert((await provider('Nous Portal').locator('..').innerText()).includes('39 / 40'));
   assert(sharing.exposed_models.includes(offlineModel));assert.equal(sharing.exposed_models.filter(id=>nousIds.includes(id)).length,39);
   await page.locator('#hermes-model-search').fill('080');assert.equal(await page.locator('.hermes-model-row:visible').count(),1);
   await provider('Nous Portal').click();await waitSaved();assert.deepEqual(new Set(sharing.exposed_models),new Set([...modelIds,offlineModel]));
   assert.equal(await provider('Nous Portal').evaluate(el=>el.indeterminate),false);
   await provider('Nous Portal').uncheck();await waitSaved();assert.deepEqual(new Set(sharing.exposed_models),new Set([...otherIds,offlineModel]));
   await provider('Nous Portal').check();await waitSaved();assert.deepEqual(new Set(sharing.exposed_models),new Set([...modelIds,offlineModel]));assertModelOnlyPost();assertGrants();
  });
  await check('Rejected provider bulk save restores the authoritative group and offline grants',async()=>{
   const before=[...sharing.exposed_models];rejectOnce=true;await provider('Nous Portal').uncheck();await waitSaved();
   assert.deepEqual(sharing.exposed_models,before);assert.equal(await provider('Nous Portal').isChecked(),true);
   assert((await page.locator('#toast').innerText()).includes('Échec synthétique'));assertModelOnlyPost();assertGrants();
  });
  await check('Clear all from automatic mode posts an exact empty allowlist and preserves account sharing',async()=>{
   await page.locator('#hermes-models-auto').check();await waitSaved();assert.equal(sharing.exposed_models,null);
   await page.locator('#hermes-models-clear').click();assert.equal(await page.locator('#hermes-models-clear').isDisabled(),true);await waitSaved();
   assert.deepEqual(sharing.exposed_models,[]);assert.equal(await page.locator('#hermes-models-auto').isChecked(),false);
   assert.equal(await page.locator('[data-model]:checked').count(),0);assert.equal(await page.locator('#hermes-provider-list input:checked').count(),0);
   assert.equal(await page.locator('#hermes-models-clear').isDisabled(),true);assertModelOnlyPost();assertGrants();
  });
  await check('Clear all from manual mode removes retained offline IDs as well',async()=>{
   for(const selected of [[...otherIds,offlineModel],[offlineModel]]){
    sharing.exposed_models=selected;await refreshCatalogue();
    assert.equal(await page.locator('#hermes-models-clear').isDisabled(),false);
    assert.equal(await page.locator('[data-model]:checked').count(),selected.length-1);
    await page.locator('#hermes-models-clear').click();assert.equal(await page.locator('#hermes-models-clear').isDisabled(),true);await waitSaved();assert.deepEqual(sharing.exposed_models,[]);
    assert.equal(await page.locator('[data-model]:checked').count(),0);assert.equal(await page.locator('#hermes-provider-list input:checked').count(),0);assertModelOnlyPost();assertGrants();
   }
  });
  await check('Rejected clear all restores model/provider selection and leaves sharing untouched',async()=>{
   sharing.exposed_models=[...modelIds,offlineModel];await refreshCatalogue();
   const before=[...sharing.exposed_models];rejectOnce=true;await page.locator('#hermes-models-clear').click();assert.equal(await page.locator('#hermes-models-clear').isDisabled(),true);await waitSaved();
   assert.deepEqual(sharing.exposed_models,before);assert.equal(await provider('Nous Portal').isChecked(),true);assert.equal(await provider('Fournisseur synthétique').isChecked(),true);
   assert.equal(await page.locator('#hermes-models-clear').isDisabled(),false);assert((await page.locator('#toast').innerText()).includes('Échec synthétique'));assertModelOnlyPost();assertGrants();
   await page.locator('#hermes-models-auto').check();await waitSaved();assert.equal(sharing.exposed_models,null);
  });
  await check('Explicit exposure writes the model allowlist and preserves sharing grants',async()=>{
   await page.locator('#hermes-models-auto').uncheck();
   await page.waitForFunction(()=>!document.getElementById('hermes-models-auto').checked&&!document.getElementById('hermes-models-auto').disabled);
   assert.deepEqual(sharing.exposed_models,modelIds);
   const first=page.locator('[data-model="'+modelIds[0]+'"]');await first.uncheck();
   await page.waitForFunction(id=>!document.querySelector('[data-model="'+id+'"]')?.checked&&!document.getElementById('hermes-models-auto').disabled,modelIds[0]);
   assert.equal(sharing.exposed_models.length,79);assert(!sharing.exposed_models.includes(modelIds[0]));
   assert.equal(sharing.share_all,false);assert.deepEqual(sharing.shared_accounts,[ids[1]]);
   assert(events.some(e=>e.path==='/api/hermes/models/configure'&&Array.isArray(e.body.exposed_models)&&e.body.exposed_models.length===79&&Object.keys(e.body).length===1));
  });
  await check('Large catalogue scrolls in its own panel and search narrows model/provider rows',async()=>{
   const list=page.locator('#hermes-model-list');await list.scrollIntoViewIfNeeded();
   const geometry=await list.evaluate(el=>({height:el.clientHeight,content:el.scrollHeight,overflow:getComputedStyle(el).overflowY}));
   assert(geometry.height<=360&&geometry.content>geometry.height&&geometry.overflow==='auto');
   await list.hover();await page.mouse.wheel(0,1800);await page.waitForFunction(()=>document.getElementById('hermes-model-list').scrollTop>300);
   await page.locator('#hermes-model-search').fill('080');assert.equal(await page.locator('.hermes-model-row:visible').count(),1);
   assert((await page.locator('.hermes-model-row:visible').innerText()).includes('080'));
   await page.locator('#hermes-model-search').fill('Fournisseur synthétique');assert.equal(await page.locator('.hermes-model-row:visible').count(),40);
   await page.locator('#hermes-model-search').fill('Introuvable');assert.equal(await page.locator('.hermes-model-row:visible').count(),0);
   await page.locator('#hermes-model-search').fill('');
  });
  await check('Rejected model exposure is re-read and restores its authoritative checkbox',async()=>{
   rejectOnce=true;const second=page.locator('[data-model="'+modelIds[1]+'"]');await second.uncheck();
   await page.waitForFunction(()=>document.getElementById('toast')?.textContent.includes('Échec synthétique'));
   await page.waitForFunction(id=>document.querySelector('[data-model="'+id+'"]')?.checked&&!document.getElementById('hermes-models-auto').disabled,modelIds[1]);
   assert.equal(sharing.exposed_models.length,79);
  });
  await check('Automatic exposure persists null and explicit refresh requests the native catalogue',async()=>{
   await page.locator('#hermes-models-auto').check();await page.waitForFunction(()=>document.getElementById('hermes-models-auto').checked&&!document.getElementById('hermes-models-auto').disabled);
   assert.equal(sharing.exposed_models,null);assert(events.some(e=>e.body.exposed_models===null));
   await page.getByRole('button',{name:'Actualiser les modèles',exact:true}).click();
   await page.waitForFunction(()=>document.querySelectorAll('[data-model]').length===80);
   assert(events.some(e=>e.path==='/api/hermes/models'&&e.query==='?refresh=1'&&e.authenticated));
   assert.equal(sharing.share_all,false);assert.deepEqual(sharing.shared_accounts,[ids[1]]);
  });
  await check('Native catalogue errors remain visible alongside the administration controls',async()=>{
   sharing.error='Catalogue synthétique indisponible';await page.getByRole('button',{name:'Actualiser les modèles',exact:true}).click();
   await page.waitForFunction(()=>document.getElementById('hermes-model-sharing').textContent.includes('Catalogue synthétique indisponible'));
   assert.equal(await page.locator('#hermes-share-all').isDisabled(),false);assert.equal(await page.locator('#hermes-models-auto').isDisabled(),false);
  });
  await check('No JavaScript errors and all sharing requests carry admin header',async()=>{
   assert.deepEqual(errors,[]);assert(events.filter(e=>e.path.startsWith('/api/hermes/models')).every(e=>e.authenticated));
  });
  const report={observed:new Date().toISOString(),fixture:true,live_console_used:false,full_console_scripts_loaded:true,checks,errors,source_sha256:Object.fromEntries(['app.js','app.css','index.html'].map(name=>[name,crypto.createHash('sha256').update(fs.readFileSync(path.join(web,name))).digest('hex')])),sharing_requests:events.filter(e=>e.path.startsWith('/api/hermes/models')).map(e=>({path:e.path,query:e.query,method:e.method,admin_header_present:e.authenticated,fields:Object.keys(e.body),...('share_all'in e.body?{share_all:e.body.share_all}:{}),...(Array.isArray(e.body.shared_accounts)?{shared_accounts_count:e.body.shared_accounts.length}:{}),...('exposed_models'in e.body?{exposed_models:e.body.exposed_models===null?null:{count:e.body.exposed_models.length}}:{})}))};
  if(proof){fs.mkdirSync(path.dirname(proof),{recursive:true});fs.writeFileSync(proof,JSON.stringify(report,null,2)+'\n');}console.log(JSON.stringify({checks:checks.length,passed:true,...(proof?{proof:path.relative(root,proof)}:{})}));
 }finally{await browser.close();server.close();}
})().catch(error=>{console.error(error.stack);server.close();process.exitCode=1;});
