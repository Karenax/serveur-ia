'use strict';
const C=MailAutoCore,inflight=new Set();
async function enabled(){return (await browser.storage.local.get('enabled')).enabled!==false;}
async function badge(error){const on=await enabled();await browser.browserAction.setBadgeText({text:on?'ON':'OFF'});await browser.browserAction.setBadgeBackgroundColor({color:on?'#167044':'#666666'});await browser.browserAction.setTitle({title:error?'Infomaniak Auto Local — '+error:'Infomaniak Auto Local — '+(on?'actif':'arrêté')});}
browser.browserAction.onClicked.addListener(async()=>{await browser.storage.local.set({enabled:!(await enabled())});await badge();});
void badge();
function completion(id){return new Promise((resolve,reject)=>{
 let timer;const finish=(error)=>{clearTimeout(timer);browser.downloads.onChanged.removeListener(change);error?reject(Error(error)):resolve();};
 const change=d=>{if(d.id!==id)return;if(d.error)finish(d.error.current);else if(d.state?.current==='complete')finish();else if(d.state?.current==='interrupted')finish('Téléchargement interrompu');};
 browser.downloads.onChanged.addListener(change);timer=setTimeout(()=>finish('Téléchargement non confirmé (5 minutes)'),300000);
 browser.downloads.search({id}).then(items=>{if(items[0]?.state==='complete')finish();else if(items[0]?.state==='interrupted')finish('Téléchargement interrompu');},e=>finish(e.message));
});}
browser.runtime.onMessage.addListener((request,sender)=>{
 if(!sender.url?.startsWith('https://mail.infomaniak.com/'))return;
 if(request.type==='error')return badge(String(request.error).slice(0,180));
 if(request.type!=='export')return;
 return (async()=>{
 let key,url,locked=false;
 try{
 if(!(await enabled()))return {skipped:true};
 const m=C.message(C.detail(request.detail),request.data);
 const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(m.key));
 const hash=Array.from(new Uint8Array(bytes),x=>x.toString(16).padStart(2,'0')).join('');key='done:'+hash;
 if(inflight.has(key))return {skipped:true};inflight.add(key);locked=true;
 if((await browser.storage.local.get(key))[key])return {skipped:true};
 const response=await fetch(m.download,{credentials:'include',redirect:'error',cache:'no-store'});
 if(!response.ok)throw Error('Original HTTP non valide');
 const blob=await response.blob();if(!C.eml(await blob.slice(0,262144).text(),response.headers.get('content-type')||''))throw Error('Réponse non EML (connexion expirée ?)');
 const state=await browser.tabs.sendMessage(sender.tab.id,{type:'confirm',token:request.token,route:request.route,subject:m.subject},{frameId:sender.frameId});
 if(!state?.current||!(await enabled()))return {skipped:true};
 url=URL.createObjectURL(blob);
 const id=await browser.downloads.download({url,filename:C.filename(m.subject,hash.slice(0,16),new Date().toISOString().slice(0,10)),saveAs:false,conflictAction:'uniquify'});
 await completion(id);await browser.storage.local.set({[key]:true});await badge();return {ok:true};
 }catch(e){await badge(e.message);return {error:e.message};}
 finally{if(locked)inflight.delete(key);if(url)URL.revokeObjectURL(url);}
 })();
});
