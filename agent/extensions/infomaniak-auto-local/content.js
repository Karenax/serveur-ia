/* Isolated world, restricted to the Infomaniak mail frame. */
'use strict';
(()=>{
 const C=MailAutoCore;let token=0,timer,latest;const ownRequests=new Set();
 const normalize=s=>String(s||'').replace(/\s+/g,' ').trim();
 function visible(node){return !!node&&node.getClientRects().length>0&&getComputedStyle(node).visibility!=='hidden'&&getComputedStyle(node).display!=='none';}
 function rendered(subject){
 const body=document.querySelector('app-mail-view app-mail-body');
 const header=document.querySelector('app-mail-view .message-header--open');
 const content=document.querySelector('app-mail-content');
 return visible(body)&&visible(header)&&visible(content)&&normalize(content.innerText).includes(normalize(subject));
 }
 function current(t,route,subject){return token===t&&location.href===route&&rendered(subject);}
 browser.runtime.onMessage.addListener(r=>{if(r.type==='confirm')return Promise.resolve({current:current(r.token,r.route,r.subject)});});
 function metadata(url){return new Promise((resolve,reject)=>{
 ownRequests.add(url);const xhr=new XMLHttpRequest();xhr.open('GET',url,true);xhr.withCredentials=true;xhr.timeout=20000;
 xhr.onload=()=>{try{if(xhr.status!==200)throw Error('Métadonnées HTTP '+xhr.status);resolve(JSON.parse(xhr.responseText).data);}catch(e){reject(e);}};
 xhr.onerror=()=>reject(Error('Métadonnées inaccessibles'));xhr.ontimeout=()=>reject(Error('Délai métadonnées dépassé'));xhr.send();
 });}
 async function process(candidate,t,route){
 try{
 if(t!==token||location.href!==route)return;
 const data=await metadata(candidate.url);if(data?.is_draft)return;
 const m=C.message(candidate,data);
 for(let i=0;i<15;i++){
 if(t!==token||location.href!==route)return;
 if(current(t,route,m.subject)){await browser.runtime.sendMessage({type:'export',detail:candidate.url,data,token:t,route});return;}
 await new Promise(resolve=>setTimeout(resolve,200));
 }
 }catch(e){await browser.runtime.sendMessage({type:'error',error:e.message}).catch(()=>{});}
 }
 const observer=new PerformanceObserver(list=>{
 for(const entry of list.getEntries()){
 if(ownRequests.delete(entry.name))continue;
 const detail=C.detail(entry.name);if(!detail)continue;
 latest=detail;token++;clearTimeout(timer);
 const t=token,route=location.href,candidate=latest;timer=setTimeout(()=>process(candidate,t,route),1000);
 }
 });
 observer.observe({type:'resource',buffered:true});

 // Manual export deliberately uses the application's current-message action,
 // never the last network detail (which may belong to a cached/thread sibling).
 const manualLabel='Télécharger ce mail (.eml)';
 const menuSelector='ik-actions-menu';
 const items=(root,label)=>Array.from(root.querySelectorAll('button, [role="menuitem"]')).filter(n=>visible(n)&&!n.disabled&&normalize(n.getAttribute('aria-label')||n.textContent)===label);
 const menus=()=>Array.from(document.querySelectorAll(menuSelector)).filter(visible);
 function manualTarget(actions){
  const headers=Array.from(document.querySelectorAll('app-mail-content app-mail-view .message-header--open')).filter(visible);
  const bodies=Array.from(document.querySelectorAll('app-mail-content app-mail-view app-mail-body')).filter(visible);
  if(headers.length!==1||bodies.length!==1||!headers[0].contains(actions)||!visible(actions)||actions.closest('app-mail-body')||headers[0].closest('app-mail-view')!==bodies[0].closest('app-mail-view'))throw Error('Aucun message unique affiché. Ouvrez un seul mail puis réessayez.');
  return {header:headers[0],body:bodies[0]};
 }
 let manualBusy=false;
 async function manual(actions,status,button){
  if(manualBusy)return;
  manualBusy=true;button.disabled=true;
  try{
   status.textContent='Préparation du téléchargement…';
   const target=manualTarget(actions),route=location.href,bodyHTML=target.body.innerHTML;
   const subject=()=>normalize(target.header.querySelector('app-message-header-subject')?.textContent);
   const subjectText=subject();
   const check=()=>{
    const now=manualTarget(actions);
    if(location.href!==route||now.header!==target.header||now.body!==target.body||target.body.innerHTML!==bodyHTML||subject()!==subjectText)throw Error('Le message a changé. Réessayez sur le mail affiché.');
   };
   if(menus().length)throw Error('Fermez le menu déjà ouvert puis réessayez.');
   const triggers=items(actions,"Plus d'options");
   if(triggers.length!==1)throw Error('Menu du message introuvable. Utilisez le menu natif.');
   triggers[0].click();
   let otherClicked=false;
   for(let i=0;i<20;i++){
    await new Promise(resolve=>setTimeout(resolve,50));
    check();
    const open=menus();
    if(open.some(m=>m.closest('app-mail-body')||!['more-option','other-actions'].includes(m.dataset.menuId)))throw Error('Menu ambigu : fermez les menus puis réessayez.');
    const downloads=open.flatMap(m=>items(m,"Télécharger l'e-mail"));
    if(downloads.length===1){downloads[0].click();status.textContent='Téléchargement demandé à Infomaniak — vérifiez les téléchargements Firefox.';return;}
    const other=open.flatMap(m=>items(m,'Autres actions'));
    if(!otherClicked&&other.length===1){other[0].click();otherClicked=true;}
   }
   throw Error('Action Télécharger l’e-mail introuvable. Utilisez le menu natif.');
  }catch(e){status.textContent='Erreur : '+e.message;}
  finally{manualBusy=false;button.disabled=false;}
 }
 function installButtons(){
  for(const actions of document.querySelectorAll('app-mail-content app-mail-view .message-header--open app-message-header-actions')){
   if(!visible(actions)||actions.querySelector('[data-mail-auto-download]'))continue;
   const button=document.createElement('button');button.type='button';button.dataset.mailAutoDownload='';button.textContent=manualLabel;
   button.style.cssText='padding:6px 10px;margin:4px;border:1px solid currentColor;border-radius:4px;background:transparent;color:inherit;cursor:pointer;font:inherit;';
   const status=document.createElement('span');status.dataset.mailAutoStatus='';status.setAttribute('role','status');status.setAttribute('aria-live','polite');status.style.cssText='display:block;font-size:12px;white-space:normal;';
   button.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();void manual(actions,status,button);});
   actions.append(button,status);
  }
 }
 if(typeof MutationObserver!=='undefined'){
  new MutationObserver(installButtons).observe(document,{childList:true,subtree:true,attributes:true,attributeFilter:['class','hidden']});
  installButtons();
 }
})();
