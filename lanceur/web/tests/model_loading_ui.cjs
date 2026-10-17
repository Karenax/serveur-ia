'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'../../..'),web=path.join(root,'lanceur/web');
const source=fs.readFileSync(path.join(web,'app.js'),'utf8'),scope={};
vm.runInNewContext(source.slice(source.indexOf('function modelLoadProgress('),source.indexOf('function renderState(')),scope);
const progress=scope.modelLoadProgress;
const allocation='FileExpertSource: allocating 51.55 GiB pageable resident cache complement';
const copied='FileExpertSource: copied cache complement through layer 16/48 (20.13 GiB, 1128 s)';
const state={status:'chargement',running:true,elapsed_seconds:1300,logs:allocation+'\n'+copied};
assert.equal(progress(state).step,2);assert.equal(Math.floor(progress(state).percent),39);
assert.match(progress(state).detail,/20,13 \/ 51,55 Go/);
assert(Math.abs(progress({...state,logs:copied}).percent-100/3)<1e-8);
assert.equal(progress({...state,logs:'strata generate: pre-filled 2323 of 2323 slots from the profile in 120.0 s'}).step,1);
assert.equal(progress({...state,logs:allocation+'\n'+copied+'\nFileExpertSource: pageable resident cache complement ready: resident 51.55 GiB'}).step,3);
assert.equal(progress({...state,status:'validation_cuda'}).percent,null);
assert.equal(progress({...state,status:'pret'}).percent,100);
assert.equal(progress({...state,status:'pret'}).visible,false);
assert.equal(progress({...state,status:'arrete'}).visible,false);
assert.match(progress({...state,status:'erreur',error:'Manque de RAM'}).detail,/Manque de RAM/);
assert.equal(progress({...state,logs:''}).percent,null);

const {chromium,options}=require(path.join(root,'client-qwen/browser_test_support.cjs'));
const proof=path.resolve(process.argv[2]||path.join(root,'maintenance/2026-10-15-progression'));
fs.mkdirSync(proof,{recursive:true});
(async()=>{
 const browser=await chromium.launch(options),errors=[],mutations=[];
 let fixtureState=state,observedState=null;
 try{
  const context=await browser.newContext({viewport:{width:1440,height:1000},locale:'fr-FR'});
  await context.route('**/*',async route=>{
   const request=route.request(),url=new URL(request.url());
   if(request.method()!=='GET'){mutations.push(url.pathname);return route.abort();}
   if(url.pathname==='/api/state'){
    const response=await route.fetch();observedState=await response.json();
    return route.fulfill({response,json:{...observedState,...fixtureState}});
   }
   return route.continue();
  });
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8765/#overview');
  await page.waitForFunction(()=>document.getElementById('server-state').textContent==='Chargement');
  // Simulate states only in the browser; all production API calls remain GET requests.
  async function show(value){fixtureState=value;await page.evaluate(s=>renderState(s),{...observedState,...value});}
  await show(state);
  const bar=page.getByRole('progressbar');
  assert.equal(await bar.getAttribute('aria-valuenow'),'39');
  assert.match(await page.locator('#model-load-detail').innerText(),/couche 16 \/ 48/);
  assert.match(await page.locator('#model-load-time').innerText(),/21 min 40 s/);
  await page.screenshot({path:path.join(proof,'chargement-desktop.png')});
  await show({...state,status:'validation_cuda'});
  assert.equal(await bar.getAttribute('aria-valuenow'),null);
  assert.match(await page.locator('#model-load-title').innerText(),/Validation/);
  await show({...state,status:'erreur',error:'Protection RAM : chargement arrêté.'});
  assert.equal(await page.locator('#model-load-meter').evaluate(e=>e.classList.contains('indeterminate')),false);
  assert.match(await page.locator('#model-load-detail').innerText(),/Protection RAM/);
  await show({...state,status:'pret'});
  assert.equal(await page.locator('#model-load-progress').isVisible(),false);
  await show({...state,status:'arrete',running:false});
  assert.equal(await page.locator('#model-load-progress').isVisible(),false);
  await page.setViewportSize({width:390,height:844});
  await page.waitForTimeout(500);
  await show(state);
  const bounds=await page.locator('#model-load-progress').boundingBox();
  assert(bounds.x+bounds.width<=390,'Loading widget stays inside the mobile viewport: '+JSON.stringify(bounds));
  await page.screenshot({path:path.join(proof,'chargement-mobile.png')});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  assert.equal(await page.locator('#model-load-progress').evaluate(e=>e.scrollWidth<=e.clientWidth),true);
  await page.emulateMedia({reducedMotion:'reduce'});
  await show({...state,logs:''});
  assert.equal(await bar.locator('i').evaluate(e=>getComputedStyle(e).animationName),'none');
  assert.deepEqual(errors,[]);assert.deepEqual(mutations,[]);
  const result={passed:true,parser_checks:10,browser_checks:12,viewports:[1440,390],production_requests_read_only:true,model_restarted:false};
  fs.writeFileSync(path.join(proof,'validation.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
