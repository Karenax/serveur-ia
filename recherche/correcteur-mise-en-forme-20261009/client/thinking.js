'use strict';
const uiThinkingLabels={none:'Sans',low:'Faible',medium:'Moyen',high:'Élevé'};
let uiThinkingEffort='none',uiThinkingModes=[];
function thinkingEffort(){return uiThinkingEffort;}
function uiThinkingSet(value){
  uiThinkingEffort=Object.hasOwn(uiThinkingLabels,value)?value:'none';
  if(uiThinkingModes.length&&!uiThinkingModes.includes(uiThinkingEffort))uiThinkingEffort=uiThinkingModes.includes('none')?'none':uiThinkingModes[0];
  for(const input of $('thinking').querySelectorAll('input'))input.checked=input.value===uiThinkingEffort;
}
function thinkingCapabilities(value){
  uiThinkingModes=Array.isArray(value.reasoning_efforts)?Object.keys(uiThinkingLabels).filter(mode=>value.reasoning_efforts.includes(mode)):value.thinking===true?['none','high']:['none'];
  if(!uiThinkingModes.length)uiThinkingModes=['none'];
  for(const input of $('thinking').querySelectorAll('input'))input.parentElement.hidden=!uiThinkingModes.includes(input.value);
  $('thinking-note').textContent=uiThinkingModes.length===1?'Ce serveur ne propose pas de réflexion.':'Niveau de réflexion pour la prochaine réponse.';
  uiThinkingSet(uiThinkingEffort);
}
for(const [value,label] of Object.entries(uiThinkingLabels)){
  const item=wsElement('label',undefined,'thinking-segment'),input=wsElement('input');
  input.type='radio';input.name='thinking-effort';input.value=value;input.id='thinking-'+value;
  item.title={none:'Répondre directement',low:'Réflexion courte',medium:'Réflexion équilibrée',high:'Réflexion approfondie'}[value];
  item.append(input,wsElement('span',label));$('thinking-bar').append(item);
  input.addEventListener('change',()=>{if(busy)return;uiThinkingSet(value);uiPersistPreferences().catch(e=>error(e));});
}
uiThinkingSet('none');

const contextGauge=wsElement('div',undefined,'context-gauge');
contextGauge.innerHTML='<span id="context-label">Contexte · connexion requise</span><progress id="context-progress" aria-label="Utilisation du contexte" max="100" value="0"></progress>';
document.querySelector('.composer-bottom').prepend(contextGauge);
let contextTimer,contextRevision=0,contextPending=false,contextSignature='';
function contextRefresh(){
 clearTimeout(contextTimer);contextRevision++;
 contextTimer=setTimeout(contextCount,650);
}
async function contextCount(){
 if(contextPending)return;
 if(!connected){contextSignature='';$('context-label').textContent='Contexte · connexion requise';$('context-progress').value=0;return;}
 const history=messages.map(m=>({role:m.role,content:chatRequestContent(m),...(m.reasoning_content?{reasoning_content:m.reasoning_content}:{})}));
 const text=$('prompt').value.trim();
 if(text||chatAttachments.length)history.push({role:'user',content:chatRequestContent({content:text,attachments:chatAttachments})});
 if(!history.length)history.push({role:'user',content:''});
 const payload={...workspaceFields(),model:config.model,messages:history,reasoning_effort:thinkingEffort()};
 const signature=JSON.stringify(payload);if(signature===contextSignature)return;
 const revision=contextRevision;contextPending=true;contextSignature='';
 $('context-label').textContent='Contexte · calcul…';
 try{
  const result=await api('/v1/context',payload);
  if(revision!==contextRevision)return;
  const percent=Math.round(result.tokens/result.capacity*1000)/10;
  contextSignature=signature;
  $('context-progress').value=Math.min(100,percent);
  contextGauge.dataset.level=percent>=95?'full':percent>=80?'warning':'normal';
  $('context-label').textContent='Contexte '+(result.estimated?'≈ ':'')+percent+' % · '+result.tokens.toLocaleString('fr-FR')+' / '+result.capacity.toLocaleString('fr-FR');
  contextGauge.title='Historique, réflexion, fichiers, texte en cours et contexte du projet inclus.'+(result.estimated?' Les tokens visuels ne sont pas comptés.':' Comptage par le tokenizer du serveur.')+(percent>=95?' Contexte presque plein : ouvrez une nouvelle conversation.':'');
 }catch{if(revision===contextRevision){$('context-label').textContent='Contexte · comptage indisponible';$('context-progress').removeAttribute('value');}}
 finally{contextPending=false;if(revision!==contextRevision)contextRefresh();}
}
$('prompt').addEventListener('input',contextRefresh);
$('thinking').addEventListener('change',contextRefresh);
const contextRender=render;render=function(){contextRender();contextRefresh();};
const contextAttachments=attachmentRender;attachmentRender=function(){contextAttachments();contextRefresh();};
const contextCapabilities=thinkingCapabilities;thinkingCapabilities=function(value){contextCapabilities(value);contextRefresh();};
setInterval(()=>{if(busy)contextRefresh();},2500);
contextRefresh();
