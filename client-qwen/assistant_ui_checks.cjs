'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
module.exports=async({page,state,android,errors})=>{
  const project='a'.repeat(32),proof=require('./test_artifacts.cjs').directory('assistant');
  fs.mkdirSync(proof,{recursive:true});
  const records={memories:[],reminders:[],legacy_memories:[],tasks:[]},requests=[];
  let fail=false,sequence=0;
  await page.route('**/v1/workspace',route=>route.fulfill({json:{projects:[{id:project,title:'Projet Orion',archived:false,documents:[],memories:[],conversations:[]}],jobs:[]}}));
  await page.route('**/v1/workspace/action',async route=>{
    const v=route.request().postDataJSON();requests.push(v);
    if(fail){fail=false;return route.fulfill({status:503,json:{error:{message:'Enregistrement indisponible. Réessayez.'}}});}
    let result;
    if(v.operation==='list')result={...records,memories:records.memories.filter(m=>m.project===v.project),reminders:records.reminders.filter(m=>m.project===v.project)};
    else if(v.operation==='memory_add'){records.memories.push({id:String(++sequence).padStart(32,'0'),text:v.text,category:v.category,revision:'v1',project:v.project});result={message:'Souvenir enregistré.'};}
    else if(v.operation==='memory_update'){const m=records.memories.find(m=>m.id===v.id);Object.assign(m,{text:v.text,revision:'v2'});result={message:'Souvenir enregistré.'};}
    else if(v.operation==='memory_forget'){records.memories=records.memories.filter(m=>m.id!==v.id);result={message:'Souvenir oublié. La discussion source reste dans votre historique.'};}
    else if(v.operation==='reminder_create'){records.reminders.push({id:String(++sequence).padStart(32,'0'),text:v.text,due:Date.now()/1000+3600,timezone:v.timezone,repeat:v.repeat,kind:v.kind,revision:1,state:'scheduled',project:v.project});result={message:'Programmation enregistrée.'};}
    else if(v.operation==='reminder_cancel'){records.reminders.find(r=>r.id===v.id).state='cancelled';result={message:'Rappel annulé.'};}
    else if(v.operation==='brief_get')result={title:'Projet Orion',message:'Bilan actualisé : Projet Orion.',updated:Date.now()/1000,decisions:[],memories:[],tasks:[],documents:[],conversations:[]};
    else return route.fulfill({status:400,json:{error:{message:'Commande non prévue par la fixture.'}}});
    return route.fulfill({json:result});
  });
  if(android)await page.locator('#ui-sidebar-toggle').click();
  await page.locator('[data-view-button="assistant"]').click();
  await page.waitForFunction(()=>document.getElementById('assistant-status').textContent==='À jour.');
  assert.equal(await page.locator('#assistant-memories').innerText(),'Aucun souvenir dans cet espace.');
  await page.locator('#assistant-memory-add summary').click();
  await page.locator('#assistant-memory-text').fill('Je préfère les réponses courtes.');
  fail=true;await page.locator('#assistant-memory-form button[type="submit"]').click();
  await page.waitForFunction(()=>document.getElementById('assistant-status').textContent.includes('indisponible'));
  assert.equal(await page.locator('#assistant-memory-text').inputValue(),'Je préfère les réponses courtes.');
  await page.locator('#assistant-memory-form button[type="submit"]').click();
  await page.waitForFunction(()=>document.getElementById('assistant-status').textContent==='Souvenir enregistré.');
  const attempts=requests.filter(v=>v.operation==='memory_add');assert.equal(attempts[0].request_key,attempts[1].request_key,'Retry retains the logical command key');
  await page.locator('#assistant-memories button').filter({hasText:'Modifier'}).click();
  assert.equal(await page.evaluate(()=>document.activeElement.id),'assistant-memory-text');
  await page.locator('#assistant-memory-text').fill('Je préfère les réponses détaillées.');
  await page.locator('#assistant-memory-form button[type="submit"]').click();
  await page.waitForFunction(()=>document.getElementById('assistant-memories').textContent.includes('détaillées'));
  await page.locator('#assistant-reminder-add summary').click();
  await page.locator('#assistant-reminder-text').fill('Reprendre le dossier Orion');
  await page.locator('#assistant-reminder-at').fill('2027-01-04T18:00');
  await page.locator('#assistant-reminder-form button[type="submit"]').click();
  await page.waitForFunction(()=>document.getElementById('assistant-reminders').textContent.includes('Orion'));
  await page.locator('#assistant-reminders button').filter({hasText:'Annuler ce rappel'}).click();
  await page.waitForFunction(()=>document.getElementById('assistant-reminders').textContent.includes('Aucun rappel'));
  await page.locator('#assistant-project').selectOption(project);
  await page.waitForFunction(()=>document.getElementById('assistant-status').textContent==='À jour.');
  assert.equal(await page.locator('#assistant-memories').innerText(),'Aucun souvenir dans cet espace.');
  await page.locator('#assistant-brief-refresh').click();
  await page.waitForFunction(()=>document.getElementById('assistant-brief').textContent.includes('Décisions confirmées'));
  for(const [name,width,height] of [['desktop',1440,1000],['phone',390,844],['tablet',768,1024]]){
    await page.setViewportSize({width,height});
    await page.evaluate(()=>{document.querySelector('[data-view="assistant"]').scrollTop=0;document.getElementById('assistant-memory-add').open=false;document.getElementById('assistant-reminder-add').open=false;uiCloseSidebar(false);});
    await new Promise(resolve=>setTimeout(resolve,300));
    await page.screenshot({path:path.join(proof,`${android?'android':'windows'}-${name}.png`),fullPage:true});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'No horizontal overflow');
  }
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({passed:true,platform:android?'android':'windows',checks:['memory CRUD','failed save keeps draft','retry identity','scope separation','reminder cancellation','project brief','three viewports','focus']}));
};
