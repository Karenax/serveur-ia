'use strict';
const assert=require('node:assert/strict');

module.exports=async({page,state,errors,until,voiceUI})=>{
 await voiceUI.click('[data-view-button="voice"]');
 state.captureTestImage=await page.evaluate(()=>{
  const canvas=document.createElement('canvas');canvas.width=1280;canvas.height=720;
  const context=canvas.getContext('2d');context.fillStyle='red';context.fillRect(0,0,640,720);
  context.fillStyle='blue';context.fillRect(640,0,640,720);return canvas.toDataURL('image/jpeg',.9);
 });
 const capture=page.locator('#voice-image-capture'),preview=page.locator('#voice-image-preview img');
 for(const [width,height] of [[1280,720],[1920,1080],[2560,1440]]){
  await page.setViewportSize({width,height});
  await page.evaluate(()=>attachmentCapabilities({images:true,files:[]}));
  assert.equal(await capture.isVisible(),true);
  await capture.click();
  let dialog=page.getByRole('dialog',{name:'Choisir la zone à joindre'});await dialog.waitFor();
  assert.equal(await preview.count(),0,'aucune image ne doit être jointe avant confirmation');
  const box=await dialog.locator('canvas').boundingBox();
  await page.mouse.move(box.x+box.width*.72,box.y+box.height*.18);
  await page.mouse.down();await page.mouse.move(box.x+box.width*.92,box.y+box.height*.78,{steps:4});await page.mouse.up();
  assert(Number(await dialog.getByLabel('Gauche').inputValue())>640);
  await dialog.getByRole('button',{name:'Utiliser cette zone'}).click();
  await until(async()=>await preview.count()===1,'aperçu de la zone sélectionnée');
  const result=await preview.evaluate(async image=>{
   await image.decode();const canvas=document.createElement('canvas');canvas.width=image.naturalWidth;canvas.height=image.naturalHeight;
   const context=canvas.getContext('2d');context.drawImage(image,0,0);return {width:canvas.width,height:canvas.height,pixel:[...context.getImageData(Math.floor(canvas.width/2),Math.floor(canvas.height/2),1,1).data]};
  });
  assert(result.width>8&&result.width<640&&result.height>8&&result.height<720);
  assert(result.pixel[2]>200&&result.pixel[0]<30,'seule la zone bleue doit être conservée');
  await page.getByRole('button',{name:'Retirer l’image'}).click();
  await capture.click();dialog=page.getByRole('dialog',{name:'Choisir la zone à joindre'});await dialog.waitFor();
  await dialog.getByLabel('Gauche',{exact:true}).fill('700');await dialog.getByLabel('Haut',{exact:true}).fill('20');
  await dialog.getByLabel('Largeur').fill('200');await dialog.getByLabel('Hauteur').fill('100');
  await dialog.getByRole('button',{name:'Utiliser cette zone'}).click();
  await until(async()=>await preview.count()===1,'aperçu après saisie des coordonnées');
  assert.deepEqual(await preview.evaluate(image=>[image.naturalWidth,image.naturalHeight]),[200,100]);
  await page.getByRole('button',{name:'Retirer l’image'}).click();
  await capture.click();dialog=page.getByRole('dialog',{name:'Choisir la zone à joindre'});await dialog.waitFor();
  await page.keyboard.press('Escape');await dialog.waitFor({state:'detached'});
  assert.equal(await preview.count(),0,'annulation sans pièce jointe');
 }
 assert.equal(state.chats.length,0,'aucune image ne doit être transmise pendant la sélection');
 assert.deepEqual(errors,[]);
 console.log(JSON.stringify({platform:'linux',passed:true,resolutions:['1280x720','1920x1080','2560x1440'],checks:['bouton visible','sélection souris','coordonnées clavier','annulation','aucun envoi prématuré']}));
};
