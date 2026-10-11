'use strict';
const uiThinkingLabels={none:'Sans',minimal:'Minimal',low:'Faible',medium:'Moyen',high:'Élevé',xhigh:'Très élevé',max:'Maximum',ultra:'Ultra',on:'Activée'};
const uiThinkingTitles={none:'Répondre sans réflexion activée',minimal:'Réflexion minimale',low:'Réflexion courte',medium:'Réflexion équilibrée',high:'Réflexion approfondie',xhigh:'Réflexion très approfondie',max:'Réflexion maximale',ultra:'Niveau ultra du modèle',on:'Activer la réflexion de ce modèle'};
let uiThinkingEffort=null,uiThinkingModes=[],uiThinkingModel='',uiThinkingPreferred='none',uiThinkingByModel=Object.create(null);
function thinkingEffort(){return uiThinkingEffort;}
function thinkingRequest(){return uiThinkingEffort===null?{}:{reasoning_effort:uiThinkingEffort};}
function thinkingCanDisable(){return uiThinkingModes.includes('none');}
function uiThinkingRemember(model,effort){
  if(typeof model!=='string'||!model.trim()||model.length>512||/[\x00-\x1f]/.test(model)||!effort)return;
  if(!Object.hasOwn(uiThinkingByModel,model)&&Object.keys(uiThinkingByModel).length>=512)delete uiThinkingByModel[Object.keys(uiThinkingByModel)[0]];
  uiThinkingByModel[model]=effort;
}
function uiThinkingPreferences(){return {thinking_by_model:{...uiThinkingByModel},...(uiThinkingEffort===null?{}:{thinking_effort:uiThinkingEffort,thinking:uiThinkingEffort!=='none'})};}
function uiThinkingLoad(values){
  uiThinkingByModel=Object.create(null);
  if(values.thinking_by_model&&typeof values.thinking_by_model==='object'&&!Array.isArray(values.thinking_by_model))for(const [model,effort] of Object.entries(values.thinking_by_model).slice(0,512))if(model.trim()&&model.length<=512&&!/[\x00-\x1f]/.test(model)&&typeof effort==='string'&&Object.hasOwn(uiThinkingLabels,effort))uiThinkingByModel[model]=effort;
  const preferred=values.thinking_effort||(values.thinking?'high':'none');
  uiThinkingPreferred=Object.hasOwn(uiThinkingLabels,preferred)?preferred:'none';
  uiThinkingSet(uiThinkingByModel[uiThinkingModel]||uiThinkingPreferred);
}
function uiThinkingSet(value){
  if(Object.hasOwn(uiThinkingLabels,value))uiThinkingPreferred=value;
  uiThinkingEffort=uiThinkingModes.includes(value)?value:uiThinkingModes.includes('none')?'none':uiThinkingModes[0]||null;
  if(uiThinkingEffort!==null){uiThinkingPreferred=uiThinkingEffort;uiThinkingRemember(uiThinkingModel,uiThinkingEffort);}
  for(const input of $('thinking').querySelectorAll('input'))input.checked=input.value===uiThinkingEffort;
}
function thinkingCapabilities(value){
  if(busy)return;
  const previousModel=uiThinkingModel,previousEffort=uiThinkingEffort;
  uiThinkingModel=typeof conversationModel==='function'?conversationModel():'';
  const remembered=uiThinkingByModel[uiThinkingModel];
  uiThinkingModes=Array.isArray(value.reasoning_efforts)?[...new Set(value.reasoning_efforts.filter(mode=>Object.hasOwn(uiThinkingLabels,mode)))]:[];
  $('thinking').dataset.mode=uiThinkingModes.length?(value.reasoning_mode==='toggle'?'toggle':'effort'):'none';
  for(const input of $('thinking').querySelectorAll('input'))input.parentElement.hidden=!uiThinkingModes.includes(input.value);
  for(const mode of uiThinkingModes)$('thinking-bar').append($('thinking-'+mode).parentElement);
  $('thinking-bar').hidden=!uiThinkingModes.length;
  $('thinking-note').textContent=!uiThinkingModes.length?(typeof conversationModelAvailable==='function'&&conversationModelAvailable()?'Réflexion automatique selon le modèle · aucun niveau réglable.':'Choisissez un modèle disponible pour connaître ses réglages de réflexion.'):value.reasoning_mode==='toggle'?(uiThinkingModes.includes('none')&&uiThinkingModes.includes('on')?'Activer ou désactiver la réflexion de ce modèle.':uiThinkingModes.includes('on')?'Réflexion activée pour ce modèle.':'Réflexion désactivée pour ce modèle.'):'Niveau de réflexion pour la prochaine réponse.';
  uiThinkingSet(remembered||uiThinkingPreferred);
  if(uiThinkingModes.length&&typeof uiPreferencesLoaded!=='undefined'&&uiPreferencesLoaded&&(previousModel!==uiThinkingModel||previousEffort!==uiThinkingEffort||remembered!==uiThinkingByModel[uiThinkingModel]))uiPersistPreferences().catch(e=>error(e));
}
for(const [value,label] of Object.entries(uiThinkingLabels)){
  const item=wsElement('label',undefined,'thinking-segment'),input=wsElement('input');
  input.type='radio';input.name='thinking-effort';input.value=value;input.id='thinking-'+value;
  item.title=uiThinkingTitles[value];item.hidden=true;
  item.append(input,wsElement('span',label));$('thinking-bar').append(item);
  input.addEventListener('change',()=>{if(busy)return;uiThinkingSet(value);uiPersistPreferences().catch(e=>error(e));});
}
thinkingCapabilities({});

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
 if(!connected||!conversationModelAvailable()){contextSignature='';$('context-label').textContent=connected?'Contexte · choisissez un modèle disponible':'Contexte · connexion requise';$('context-progress').value=0;return;}
 const history=messages.map(m=>({role:m.role,content:chatRequestContent(m),...(m.reasoning_content?{reasoning_content:m.reasoning_content}:{})}));
 const text=$('prompt').value.trim();
 if(text||chatAttachments.length)history.push({role:'user',content:chatRequestContent({content:text,attachments:chatAttachments})});
 if(!history.length)history.push({role:'user',content:''});
 const payload={...workspaceFields(),model:conversationModel(),messages:history,...thinkingRequest()};
 const signature=JSON.stringify(payload);if(signature===contextSignature)return;
 const revision=contextRevision;contextPending=true;contextSignature='';
 $('context-label').textContent='Contexte · calcul…';
 try{
  const result=await api('/v1/context',payload);
  if(revision!==contextRevision)return;
  if(typeof result.tokens!=='number'||!Number.isFinite(result.tokens)||result.tokens<0)throw new Error('Comptage invalide.');
  contextSignature=signature;
  if(typeof result.capacity!=='number'||!Number.isFinite(result.capacity)||result.capacity<=0){
    $('context-progress').removeAttribute('value');contextGauge.dataset.level='normal';
    $('context-label').textContent='Contexte '+(result.estimated?'≈ ':'')+result.tokens.toLocaleString('fr-FR')+' tokens · capacité non connue';
    contextGauge.title='Estimation du contexte visible. La capacité de ce modèle n’est pas annoncée par le serveur.';return;
  }
  const percent=Math.round(result.tokens/result.capacity*1000)/10;
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
