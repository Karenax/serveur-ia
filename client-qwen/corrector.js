'use strict';
const correctorPane=wsElement('section',undefined,'corrector-view');correctorPane.dataset.view='corrector';correctorPane.hidden=true;
correctorPane.innerHTML='<div class="corrector-heading"><div><h2>Correcteur de français</h2><p>Écrivez ou collez votre texte, puis choisissez le ton.</p></div><span class="access-badge">Vos textes restent sur votre serveur</span></div><div class="corrector-layout"><section class="corrector-source" aria-labelledby="corrector-source-label"><label id="corrector-source-label" for="corrector-text">Votre texte</label><textarea id="corrector-text" maxlength="100000" placeholder="Collez ici le texte à corriger ou à reformuler…"></textarea><div class="corrector-actions"><button id="corrector-correct" class="secondary primary" type="button">Corriger</button><button id="corrector-pro" class="secondary" type="button">Reformuler professionnel</button><button id="corrector-friendly" class="secondary" type="button">Reformuler amical</button><button id="corrector-cancel" class="secondary" type="button" hidden>Arrêter</button></div><p id="corrector-status" role="status" class="muted">Orthographe, grammaire et ponctuation, en conservant le sens de votre texte.</p></section><section id="corrector-result-card" class="corrector-result-card" aria-labelledby="corrector-result-title"><div class="corrector-result-heading"><h3 id="corrector-result-title">Votre texte retravaillé</h3><div class="actions"><button id="corrector-copy" class="secondary" type="button" disabled>Copier le texte</button><button id="corrector-reuse" class="secondary" type="button" disabled>Reprendre ce texte</button></div></div><p id="corrector-result-empty">Le résultat apparaîtra ici. Vous pourrez comparer les deux textes, le copier ou le reprendre.</p><div id="corrector-result" class="content markdown" hidden></div></section></div>';
document.querySelector('.workspace').append(correctorPane);
uiPaths.corrector='M4 20l4-1L21 6l-3-3L5 16l-1 4M9 8l2 2 4-4M4 3h5';uiNavTitles.corrector='Correcteur';
const correctorNav=wsElement('button','Correcteur','nav-button');correctorNav.dataset.viewButton='corrector';correctorNav.onclick=()=>showView('corrector');
document.querySelector('#client-navigation').insertBefore(correctorNav,document.querySelector('[data-view-button="tasks"]'));uiDecorateNavigation();
let correctorRunning=false,correctorDirty=false,correctorDraftTimer=null,correctorAnswer={content:''};
window.generationCancelBody=()=>correctorRunning?{text_transform:true}:{};
function correctorResultDisplay(){const show=correctorRunning||!!correctorAnswer.content;$('corrector-result-empty').hidden=show;$('corrector-result').hidden=!show;}
const correctorModes={
  correct:{label:'Corriger'},
  professional:{label:'Reformuler professionnel'},
  friendly:{label:'Reformuler amical'}
};
const correctorButtonsOnce=buttons;buttons=function(){correctorButtonsOnce();for(const id of ['corrector-correct','corrector-pro','corrector-friendly'])$(id).disabled=busy||historySyncPending||!connected;$('corrector-text').readOnly=correctorRunning;$('corrector-cancel').hidden=!correctorRunning;$('corrector-reuse').disabled=correctorRunning||!correctorAnswer.content;$('corrector-copy').disabled=!correctorAnswer.content;};
const correctorShowOnce=showView;showView=function(name){correctorShowOnce(name);if(name==='corrector'){$('workspace-heading').textContent='Correcteur de français';if(!correctorRunning&&!correctorAnswer.content){const recent=library.find(c=>c.title.startsWith('Correcteur ·'));const answer=recent?.messages.findLast(m=>m.role==='assistant');if(answer?.content){correctorAnswer=answer;renderMarkdown($('corrector-result'),answer.content);$('corrector-result-card').hidden=false;correctorResultDisplay();}}}};
$('corrector-text').oninput=()=>{correctorDirty=true;clearTimeout(correctorDraftTimer);correctorDraftTimer=setTimeout(()=>uiPersistPreferences().catch(e=>error(e)),500);};
$('corrector-copy').onclick=async()=>{try{await copyText(correctorAnswer.content);$('corrector-status').textContent='Texte copié.';}catch{error('Copie impossible. Sélectionnez le texte du résultat.');}};
$('corrector-reuse').onclick=()=>{$('corrector-text').value=correctorAnswer.content.slice(0,100000);correctorDirty=true;uiPersistPreferences().catch(e=>error(e));$('corrector-text').focus();};
$('corrector-cancel').onclick=()=>{$('cancel').click();};
async function correctorRun(mode){
  if(busy||historySyncPending||!connected)return;const source=$('corrector-text').value.trim();if(!source){$('corrector-status').textContent='Saisissez le texte à retravailler.';$('corrector-text').focus();return;}
  if(library.length>=200){error('Exportez puis supprimez une conversation pour enregistrer ce résultat.');return;}
  try{await uiPersistPreferences();}catch(e){error(e);return;}
  const instruction=correctorModes[mode];currentId=crypto.randomUUID();correctorAnswer={role:'assistant',content:'',reasoning_content:''};
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
    $('corrector-status').textContent=instruction.label+' · terminé. Résultat enregistré dans vos conversations.';
  }catch(e){correctorAnswer.interrupted=true;if(e.name==='TypeError')e.code='connection_error';$('corrector-status').textContent=e.name==='AbortError'?'Correction arrêtée. Le texte reçu est conservé.':e.message;if(e.name!=='AbortError')error(e);}
  finally{correctorRunning=false;correctorResultDisplay();controller=null;cancelPending=false;renderMarkdown($('corrector-result'),correctorAnswer.content);save();try{await flushHistory();serverHistoryReady=false;await syncServerHistory(true);}catch(e){error(e);}busy=false;render();drawLibrary();buttons();$('queue-state').textContent='';models();}
}
for(const [id,mode] of [['corrector-correct','correct'],['corrector-pro','professional'],['corrector-friendly','friendly']])$(id).onclick=()=>correctorRun(mode);
buttons();
