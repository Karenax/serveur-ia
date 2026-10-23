'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../..'),web=path.join(root,'lanceur/web');
const {chromium,options}=require(path.join(root,'client-qwen/browser_test_support.cjs'));
const out=path.join(__dirname,'interface');fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch(options),errors=[],posts=[];
 let state={base_url:'http://192.168.1.41:8080/v1',subnet:'192.168.1.0/24',model:'qwen-test',
   authentication:false,pending:false,enabled:true,available:true,state:'enabled',can_disable:true,message:'Accès local activé.'};
 try{
  const context=await browser.newContext({viewport:{width:1440,height:1050},locale:'fr-FR',permissions:['clipboard-read','clipboard-write']});
  await context.route('**/*',async route=>{
   const req=route.request(),url=new URL(req.url());
   if(url.pathname==='/api/local-network'){
    if(req.method()==='POST'){
     const body=req.postDataJSON();posts.push(body);assert.equal(typeof body.enabled,'boolean');
     state={...state,pending:true,message:'Validation administrateur Windows en attente…'};
     return route.fulfill({json:{message:'Validez la demande administrateur Windows.'}});
    }
    return route.fulfill({json:state});
   }
   if(req.method()!=='GET')throw new Error('Unexpected mutation: '+url.pathname);
   const file=url.pathname==='/'?'index.html':url.pathname.slice(1);
   if(!file.includes('/')&&fs.existsSync(path.join(web,file))){
    const contentType=file.endsWith('.html')?'text/html':file.endsWith('.css')?'text/css':'application/javascript';
    return route.fulfill({body:fs.readFileSync(path.join(web,file)),contentType});
   }
   return route.continue();
  });
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8765/#network');
  const toggle=page.locator('#qwen-lan-toggle');
  await page.getByRole('button',{name:'Couper l’accès local',exact:true}).waitFor();
  assert.equal(await page.locator('#qwen-lan-url').inputValue(),state.base_url);
  assert.equal(await page.locator('#qwen-lan-model').inputValue(),'qwen-test');
  assert.equal(await page.locator('#qwen-lan-key').inputValue(),'Aucune');
  await page.getByRole('button',{name:'Copier les paramètres',exact:true}).click();
  assert.match(await page.evaluate(()=>navigator.clipboard.readText()),/Clé API : aucune/);
  await page.screenshot({path:path.join(out,'desktop.png'),fullPage:true});
  await toggle.click();await page.waitForFunction(()=>document.getElementById('qwen-lan-toggle').disabled);
  assert.equal(posts.length,1);assert.equal(posts[0].enabled,false);
  assert.equal(await page.locator('#qwen-lan-card').getAttribute('aria-busy'),'true');
  state={...state,pending:false,enabled:false,available:false,state:'disabled',can_disable:false,message:'Accès local coupé.'};
  await page.getByRole('button',{name:'Activer l’accès local',exact:true}).waitFor();
  await toggle.click();assert.equal(posts.at(-1).enabled,true);
  state={...state,pending:false,error:'Validation Windows annulée.',message:'Accès local coupé.'};
  await page.locator('#qwen-lan-error').getByText('Validation Windows annulée.').waitFor();
  assert.equal(await toggle.isEnabled(),true);
  state={...state,error:'',state:'unknown',message:'État de l’accès local indisponible. Réessayez.'};
  await page.waitForFunction(()=>document.getElementById('qwen-lan-status').textContent.includes('indisponible'));
  assert.equal(await toggle.isDisabled(),true);
  state={...state,state:'enabled',enabled:true,can_disable:true,available:false,message:'Accès local activé. Qwen est indisponible ; vérifiez le modèle dans Vue d’ensemble.'};
  await page.getByRole('button',{name:'Couper l’accès local',exact:true}).waitFor();
  // A real keyboard can reach the operation and its visible focus remains intact.
  await toggle.focus();assert.equal(await toggle.evaluate(e=>e===document.activeElement),true);
  await page.setViewportSize({width:390,height:844});
  await page.waitForFunction(()=>document.querySelector('.console-sidebar').getBoundingClientRect().right<=0);
  await page.locator('#qwen-lan-card').scrollIntoViewIfNeeded();
  await page.screenshot({path:path.join(out,'phone.png'),fullPage:true});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'No horizontal overflow');
  const box=await page.locator('#qwen-lan-card').boundingBox();assert(box.x>=0&&box.x+box.width<=390);
  assert.equal(errors.length,0,errors.join('\n'));
  fs.writeFileSync(path.join(out,'tests.json'),JSON.stringify({passed:true,states:['enabled','pending','disabled','cancelled','unknown','model_unavailable'],copy_verified:true,keyboard_focus:true,mobile_overflow:false,posts,production_mutations:false,errors},null,2));
  console.log('LAN UI: states, copy, actions, keyboard and mobile passed; production unchanged.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
