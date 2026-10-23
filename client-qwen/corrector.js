'use strict';
const correctorPane=wsElement('section',undefined,'corrector-view');correctorPane.dataset.view='corrector';correctorPane.hidden=true;
correctorPane.innerHTML='<div class="corrector-heading"><div><h2>Correcteur de français</h2><p>Écrivez ou collez votre texte, puis choisissez le ton.</p></div><span class="access-badge">Vos textes restent sur votre serveur</span></div><div class="corrector-layout"><section class="corrector-source" aria-labelledby="corrector-source-label"><label id="corrector-source-label" for="corrector-text">Votre texte</label><textarea id="corrector-text" maxlength="100000" placeholder="Collez ici le texte à corriger ou à reformuler…"></textarea><div class="corrector-actions"><button id="corrector-correct" class="secondary primary" type="button">Corriger</button><button id="corrector-pro" class="secondary" type="button">Reformuler professionnel</button><button id="corrector-friendly" class="secondary" type="button">Reformuler amical</button><button id="corrector-cancel" class="secondary" type="button" hidden>Arrêter</button></div><p id="corrector-status" role="status" class="muted">Orthographe, grammaire et ponctuation, en conservant le sens de votre texte.</p></section><section id="corrector-result-card" class="corrector-result-card" aria-labelledby="corrector-result-title"><div class="corrector-result-heading"><h3 id="corrector-result-title">Votre texte retravaillé</h3><div class="actions"><button id="corrector-copy" class="secondary" type="button" disabled>Copier le texte</button><button id="corrector-reuse" class="secondary" type="button" disabled>Reprendre ce texte</button></div></div><p id="corrector-result-empty">Le résultat apparaîtra ici. Vous pourrez comparer les deux textes, le copier ou le reprendre.</p><div id="corrector-result" class="content markdown" hidden></div></section></div>';
document.querySelector('.workspace').append(correctorPane);
uiPaths.corrector='M4 20l4-1L21 6l-3-3L5 16l-1 4M9 8l2 2 4-4M4 3h5';uiNavTitles.corrector='Correcteur';
const correctorNav=wsElement('button','Correcteur','nav-button');correctorNav.dataset.viewButton='corrector';correctorNav.onclick=()=>showView('corrector');
document.querySelector('#client-navigation').insertBefore(correctorNav,document.querySelector('[data-view-button="tasks"]'));uiDecorateNavigation();
let correctorRunning=false,correctorDirty=false,correctorDraftTimer=null,correctorAnswer={content:''},correctorSelectedId,correctorChatId=null;
window.correctorSelection=()=>correctorSelectedId;
window.generationCancelBody=()=>correctorRunning?{text_transform:true}:{};
function correctorResultDisplay(){const show=correctorRunning||!!correctorAnswer.content;$('corrector-result-empty').hidden=show;$('corrector-result').hidden=!show;}
const correctorModes={
  correct:{label:'Corriger'},
  professional:{label:'Reformuler professionnel'},
  friendly:{label:'Reformuler amical'}
};
const correctorButtonsOnce=buttons;buttons=function(){correctorButtonsOnce();for(const id of ['corrector-correct','corrector-pro','corrector-friendly'])$(id).disabled=busy||historySyncPending||!connected;$('corrector-text').readOnly=correctorRunning;$('corrector-cancel').hidden=!correctorRunning;$('corrector-reuse').disabled=correctorRunning||!correctorAnswer.content;$('corrector-copy').disabled=!correctorAnswer.content;};
function correctorLoad(c){
  correctorSelectedId=c.id;correctorAnswer=c.messages.findLast(m=>m.role==='assistant')||{content:''};
  $('corrector-text').value=c.messages.find(m=>m.role==='user').content.replace(/^(Corriger|Reformuler professionnel|Reformuler amical) :\n\n/,'');
  correctorDirty=true;renderMarkdown($('corrector-result'),correctorAnswer.content);correctorResultDisplay();
  $('corrector-status').textContent=correctorAnswer.interrupted?'Résultat partiel conservé. Vous pouvez relancer la correction.':'Résultat enregistré.';buttons();
}
window.correctorOpen=c=>{if(conversationLocked())return;save();if(!isCorrection(library.find(c=>c.id===currentId)))correctorChatId=currentId;currentId=c.id;messages=c.messages;correctorLoad(c);render();showView('corrector');drawLibrary();error('');};
const correctorShowOnce=showView;showView=function(name){
  const current=library.find(c=>c.id===currentId);
  if(name==='corrector'&&!isCorrection(current))correctorChatId=currentId;
  if(name==='chat'&&isCorrection(current)){
    if(conversationLocked()){error('Attendez la fin de l’action en cours pour ouvrir une conversation.');return;}
    let chat=library.find(c=>c.id===correctorChatId&&!isCorrection(c))||library.find(c=>!isCorrection(c)&&!c.archived)||library.find(c=>!isCorrection(c));
    if(!chat&&library.length>=200){error('Exportez puis supprimez un texte pour créer une conversation.');return;}
    save();if(!chat){chat={id:crypto.randomUUID(),title:'Nouvelle conversation',messages:[]};library.unshift(chat);}currentId=chat.id;messages=chat.messages;chatAttachments=[];attachmentRender();render();save();
  }
  correctorShowOnce(name);
  if(name==='corrector'){$('workspace-heading').textContent='Correcteur de français';drawLibrary();}
};
const correctorNewOnce=$('new').onclick;$('new').onclick=()=>{
  if(historyView!=='corrector')return correctorNewOnce();if(conversationLocked())return;
  correctorSelectedId=null;correctorAnswer={content:''};$('corrector-text').value='';correctorDirty=true;
  renderMarkdown($('corrector-result'),'');correctorResultDisplay();$('corrector-status').textContent='Saisissez le texte à corriger ou à reformuler.';drawLibrary();buttons();uiPersistPreferences().catch(e=>error(e));uiCloseSidebar(false);$('corrector-text').focus();
};
window.historyBootstrapView=()=>{if(isCorrection(library.find(c=>c.id===currentId))){if(library.some(c=>!isCorrection(c))||library.length<200)showView('chat');else{correctorLoad(library.find(c=>c.id===currentId));showView('corrector');}}};
$('corrector-text').oninput=()=>{correctorDirty=true;clearTimeout(correctorDraftTimer);correctorDraftTimer=setTimeout(()=>uiPersistPreferences().catch(e=>error(e)),500);};
$('corrector-copy').onclick=async()=>{try{await copyText(correctorAnswer.content);$('corrector-status').textContent='Texte copié.';}catch{error('Copie impossible. Sélectionnez le texte du résultat.');}};
$('corrector-reuse').onclick=()=>{$('corrector-text').value=correctorAnswer.content.slice(0,100000);correctorDirty=true;uiPersistPreferences().catch(e=>error(e));$('corrector-text').focus();};
$('corrector-cancel').onclick=()=>{$('cancel').click();};
async function correctorRun(mode){
  if(busy||historySyncPending||!connected)return;const source=$('corrector-text').value.trim();if(!source){$('corrector-status').textContent='Saisissez le texte à retravailler.';$('corrector-text').focus();return;}
  if(library.length>=200){error('Exportez puis supprimez une conversation pour enregistrer ce résultat.');return;}
  try{await uiPersistPreferences();}catch(e){error(e);return;}
  save();const instruction=correctorModes[mode];currentId=crypto.randomUUID();correctorSelectedId=currentId;correctorAnswer={role:'assistant',content:'',reasoning_content:''};
  messages=[{role:'user',content:instruction.label+' :\n\n'+source},correctorAnswer];library.unshift({id:currentId,title:'Correcteur · '+instruction.label+' · '+source.slice(0,40),messages});
  error('');correctorRunning=true;busy=true;replyProgress={phase:'requesting',started:Date.now(),lastEvent:Date.now()};controller=new AbortController();requestId=crypto.randomUUID().replaceAll('-','');cancelPending=false;buttons();save();
  $('corrector-result-card').hidden=false;correctorResultDisplay();renderMarkdown($('corrector-result'),'');$('corrector-status').textContent=instruction.label+' · en cours…';
  const details=wsElement('details'),reasoning=wsElement('div');details.hidden=true;
  const view={content:$('corrector-result'),details,reasoning};
  try{
    await flushHistory();const response=await fetch('/v1/chat/completions',{method:'POST',headers:{Authorization:'Bearer '+config.key,'Content-Type':'application/json','X-Qwen-Request':requestId},signal:controller.signal,body:JSON.stringify({text_transform:{mode,text:source},stream:true})});
    if(!response.ok){let value;try{value=await response.json();}catch{}throw Object.assign(new Error(value?.error?.message||'Le serveur a refusé la correction.'),{code:value?.error?.code});}
    const reader=response.body.getReader(),decoder=new TextDecoder();let pending='',complete=false;
    while(true){const {value,done}=await reader.read();pending+=done?decoder.decode():decoder.decode(value,{stream:true});const frames=pending.split(/\r?\n\r?\n/);pending=frames.pop();for(const frame of frames)complete=delta(frame,correctorAnswer,view)||complete;if(done){if(pending.trim())complete=delta(pending,correctorAnswer,view)||complete;if(!complete)throw Object.assign(new Error('Connexion interrompue pendant la correction. Le résultat partiel est conservé.'),{code:'connection_error'});break;}}
    if(!correctorAnswer.content.trim())throw new Error('Le modèle n’a pas renvoyé de texte corrigé. Réessayez.');
    $('corrector-status').textContent=instruction.label+' · terminé. Résultat enregistré dans le Correcteur.';
  }catch(e){correctorAnswer.interrupted=true;if(e.name==='TypeError')e.code='connection_error';$('corrector-status').textContent=e.name==='AbortError'?'Correction arrêtée. Le texte reçu est conservé.':e.message;if(e.name!=='AbortError')error(e);}
  finally{correctorRunning=false;correctorResultDisplay();controller=null;cancelPending=false;renderMarkdown($('corrector-result'),correctorAnswer.content);save();try{await flushHistory();serverHistoryReady=false;await syncServerHistory(true);}catch(e){error(e);}busy=false;render();drawLibrary();buttons();$('queue-state').textContent='';models();}
}
for(const [id,mode] of [['corrector-correct','correct'],['corrector-pro','professional'],['corrector-friendly','friendly']])$(id).onclick=()=>correctorRun(mode);
buttons();
