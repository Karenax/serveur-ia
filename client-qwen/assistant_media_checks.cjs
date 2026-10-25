'use strict';
const assert=require('node:assert/strict');
module.exports=async({page,state,android,errors,voiceUI})=>{
  let wake={phase:'stopped',session:'',microphone_closed:true,installed:true};const order=[];
  await page.route('**/client/wakeword',async route=>{
    if(route.request().method()==='POST'){
      const body=route.request().postDataJSON();
      if(body.action==='start'){order.push('wake-start');wake={...wake,phase:'listening',session:'wake-fixture',microphone_closed:false};}
      if(body.action==='stop'){order.push('wake-stop');wake={...wake,phase:'stopped',microphone_closed:true};}
    }
    return route.fulfill({json:wake});
  });
  await page.route('**/v1/workspace/action',route=>route.fulfill({json:{accepted:true}}));
  await page.route('**/client/conversation',async route=>{if(route.request().method()==='POST'&&route.request().postDataJSON().action==='start')order.push('conversation-start');await route.continue();});
  if(android)await page.evaluate(()=>{
    AndroidClient.wakeRequest=function(body){const xhr=new XMLHttpRequest();xhr.open(body?'POST':'GET','/client/wakeword',false);xhr.setRequestHeader('Content-Type','application/json');xhr.send(body||null);return xhr.responseText;};
    AndroidClient.wakewordStatus=()=>AndroidClient.wakeRequest();AndroidClient.wakewordAction=body=>AndroidClient.wakeRequest(body);
  });
  if(android)await page.locator('#ui-sidebar-toggle').click();
  await page.locator('[data-view-button="voice"]').click();
  await voiceUI.check('#voice-wake-enable');
  await page.locator('#voice-settings-close').click();
  await page.waitForFunction(()=>document.getElementById('voice-wake-status').textContent.includes('En attente'));
  wake={...wake,phase:'detected',turns:[{id:1,text:'Kiara'}]};
  await page.waitForFunction(()=>window.conversationBusy===true);
  assert(order.indexOf('wake-stop')<order.indexOf('conversation-start'),'Keyword microphone closes before conversation capture');
  await page.locator('#conversation-start').click();
  await page.waitForFunction(()=>!window.conversationBusy);
  await page.evaluate(()=>attachmentCapabilities({images:true,files:[]}));
  const png=await page.evaluate(()=>{const c=document.createElement('canvas');c.width=c.height=8;const x=c.getContext('2d');x.fillStyle='blue';x.fillRect(0,0,8,8);return c.toDataURL('image/png').split(',')[1];});
  const image={name:'Image-fictive.png',mimeType:'image/png',buffer:Buffer.from(png,'base64')};
  let captures=0;
  await page.route('**/client/capture',route=>{captures++;return route.fulfill({json:{cancelled:false,image:'data:image/jpeg;base64,'+png}});});
  assert.equal(captures,0);
  if(!android){
    await page.locator('#voice-image-capture').click();
    await page.waitForFunction(()=>document.querySelectorAll('#voice-image-preview img').length===1);
    assert.equal(captures,1,'Native capture happens only after the explicit button');
    await page.locator('#voice-image-preview button').click();
  }
  await page.locator('#voice-image-input').setInputFiles(image);
  await page.waitForFunction(()=>document.querySelectorAll('#voice-image-preview img').length===1);
  assert.equal(await page.locator('#voice-image-camera').isVisible(),android);
  await page.locator('#conversation-start').click();await page.waitForFunction(()=>window.conversationBusy);
  state.native.turns=[{id:1,speech_id:1,text:'Quelle est la couleur de cette image ?'}];state.native.speech_id=1;
  await page.waitForFunction(()=>messages.some(m=>m.role==='assistant'&&m.content));
  assert.equal(state.chats.length,1);
  const user=state.chats[0].messages.findLast(m=>m.role==='user');
  assert(Array.isArray(user.content)&&user.content.some(p=>p.type==='image_url'),'Image and oral question share one user turn');
  await page.locator('#conversation-start').click();await page.waitForFunction(()=>!window.conversationBusy);
  // A capture finishing after a hangup must never become the next turn's image.
  await page.evaluate(()=>{window.__originalBitmap=createImageBitmap;window.createImageBitmap=file=>new Promise((resolve,reject)=>{window.__finishBitmap=()=>window.__originalBitmap(file).then(resolve,reject);});});
  await page.locator('#voice-image-input').setInputFiles(image);
  await page.waitForFunction(()=>typeof window.__finishBitmap==='function');
  await page.evaluate(async()=>{await window.voiceFinishForClose();window.__finishBitmap();window.createImageBitmap=window.__originalBitmap;});
  await page.waitForFunction(()=>document.getElementById('voice-image-status').textContent.includes('annulée'));
  assert.equal(await page.locator('#voice-image-preview img').count(),0);
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({passed:true,platform:android?'android':'windows',checks:['wakeword microphone handoff','single image and oral turn','late capture cancelled','Android photo control','no spontaneous capture'],simulation:'native event timing; real native keyword inference is tested separately'}));
};
