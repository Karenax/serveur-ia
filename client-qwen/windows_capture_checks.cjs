'use strict';
const assert=require('node:assert/strict');

module.exports=async({page,state,errors,until,voiceUI})=>{
 await voiceUI.click('[data-view-button="voice"]');
 state.captureTestImage=await page.evaluate(()=>{
  const canvas=document.createElement('canvas');canvas.width=1280;canvas.height=720;
  const context=canvas.getContext('2d');context.fillStyle='blue';context.fillRect(0,0,1280,720);
  return canvas.toDataURL('image/jpeg',.9);
 });
 for(const [width,height] of [[1280,720],[1920,1080],[2560,1440]]){
  await page.setViewportSize({width,height});await page.evaluate(()=>attachmentCapabilities({images:true,files:[]}));
  await page.locator('#voice-image-capture').click();
  const preview=page.locator('#voice-image-preview img');await until(async()=>await preview.count()===1,'aperçu Windows');
  assert.deepEqual(await preview.evaluate(image=>[image.naturalWidth,image.naturalHeight]),[1280,720]);
  assert.equal(await page.getByRole('dialog',{name:'Choisir la zone à joindre'}).count(),0);
  await page.getByRole('button',{name:'Retirer l’image'}).click();
 }
 assert.equal(state.chats.length,0);assert.deepEqual(errors,[]);
 console.log(JSON.stringify({platform:'windows',passed:true,resolutions:['1280x720','1920x1080','2560x1440'],checks:['aperçu de la zone fournie','aucun envoi prématuré']}));
};
