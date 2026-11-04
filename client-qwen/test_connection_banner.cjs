'use strict';
const assert=require('node:assert/strict'),path=require('node:path'),{spawn}=require('node:child_process');
const {chromium,options}=require('./browser_test_support.cjs');
(async()=>{
  const child=spawn(process.execPath,[path.join(__dirname,'test_conversation_ui.cjs'),'--preview'],{windowsHide:true,stdio:['ignore','pipe','pipe']});
  let browser;
  try{
    const url=await new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>reject(new Error('Fixture startup timeout')),15000);
      child.stdout.on('data',chunk=>{const match=String(chunk).match(/http:\/\/127\.0\.0\.1:\d+/);if(match){clearTimeout(timer);resolve(match[0]);}});
      child.on('exit',code=>reject(new Error('Fixture exit '+code)));
    });
    browser=await chromium.launch(options);
    const page=await browser.newPage();const errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    let initial=false;
    await page.route('**/v1/models',async route=>{
      if(initial){initial=false;return route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:{code:'connecting',message:'Connexion au serveur IA…'}})});}
      await route.continue();
    });
    await page.goto(url);
    await page.waitForFunction(()=>connected&&historyReady&&!modelsPending&&!historySyncPending);
    initial=true;
    await page.evaluate(async()=>{await models();});
    await page.waitForFunction(()=>!modelsPending&&!$('error').hidden&&$('error').textContent==='Connexion au serveur IA…');
    assert.equal(await page.evaluate(()=>connected),false);
    await page.evaluate(async()=>{await models();});
    assert.equal(await page.evaluate(()=>connected),true);
    assert.equal(await page.locator('#error').isVisible(),false,'Successful connection must clear the temporary catalogue error');
    assert(await page.locator('#connection').evaluate(node=>node.classList.contains('online')));
    await page.evaluate(async()=>{error('Enregistrement impossible : réessayez.');await models();});
    assert.equal(await page.locator('#error').textContent(),'Enregistrement impossible : réessayez.','Model refresh must preserve an unrelated save error');
    await page.evaluate(()=>error({code:'access_revoked',message:'Accès révoqué.'}));
    assert.equal(await page.evaluate(()=>connected),false);
    assert.equal(await page.locator('#error').textContent(),'Accès révoqué.');
    assert.equal(await page.locator('#connection').evaluate(node=>node.classList.contains('online')),false);
    await page.evaluate(async()=>{await models();});
    assert.equal(await page.locator('#error').isVisible(),false);
    assert.deepEqual(errors,[]);
    console.log(JSON.stringify({passed:true,platform:'windows',checks:['startup connecting error cleared after successful catalogue','healthy connection indicator','unrelated save error preserved','revoked access remains red until authenticated recovery']}));
  }finally{await browser?.close();child.kill();}
})().catch(error=>{console.error(error);process.exitCode=1;});
