'use strict';
const correctorPane=wsElement('section',undefined,'corrector-view');correctorPane.dataset.view='corrector';correctorPane.hidden=true;
correctorPane.innerHTML='<div class="corrector-heading"><div><h2>Correcteur de français</h2><p>Collez votre texte : ses couleurs et ses polices sont conservées.</p></div><span class="access-badge">Vos textes restent sur votre serveur</span></div><div class="corrector-layout"><section class="corrector-source" aria-labelledby="corrector-source-label"><label id="corrector-source-label">Votre texte</label><div id="corrector-text" class="corrector-rich" contenteditable="true" role="textbox" aria-multiline="true" aria-labelledby="corrector-source-label" data-placeholder="Collez ici le texte à corriger ou à reformuler…"></div><div class="corrector-actions"><button id="corrector-correct" class="secondary primary" type="button">Corriger</button><button id="corrector-pro" class="secondary" type="button">Reformuler professionnel</button><button id="corrector-friendly" class="secondary" type="button">Reformuler amical</button><button id="corrector-cancel" class="secondary" type="button" hidden>Arrêter</button></div><p id="corrector-status" role="status" class="muted">Orthographe, grammaire et ponctuation. Votre original reste intact.</p></section><section id="corrector-result-card" class="corrector-result-card" aria-labelledby="corrector-result-title"><div class="corrector-result-heading"><h3 id="corrector-result-title">Votre texte retravaillé</h3><div class="actions"><button id="corrector-copy" class="secondary" type="button" disabled>Copier avec la mise en forme</button><button id="corrector-reuse" class="secondary" type="button" disabled>Reprendre ce texte</button></div></div><p id="corrector-result-empty">Le résultat conservera la mise en forme de votre texte.</p><div id="corrector-result" class="content corrector-rich" hidden></div></section></div>';
document.querySelector('.workspace').append(correctorPane);
correctorPane.querySelector('.access-badge').textContent='Prototype · réponses simulées';
uiPaths.corrector='M4 20l4-1L21 6l-3-3L5 16l-1 4M9 8l2 2 4-4M4 3h5';uiNavTitles.corrector='Correcteur';
const correctorNav=wsElement('button','Correcteur','nav-button');correctorNav.dataset.viewButton='corrector';correctorNav.onclick=()=>showView('corrector');
document.querySelector('#client-navigation').insertBefore(correctorNav,document.querySelector('[data-view-button="tasks"]'));uiDecorateNavigation();
let correctorRunning=false,correctorDirty=false,correctorDraftTimer=null,correctorAnswer={content:''},correctorResultHTML='',correctorResultText='';
function correctorText(){return FredRichText.plain($('corrector-text'));}
function correctorPreferences(){return {version:1,source_html:FredRichText.sanitize($('corrector-text').innerHTML).innerHTML,result_html:correctorResultHTML,result_text:correctorResultText};}
function correctorRestore(values){
  if(correctorDirty||correctorRunning||document.activeElement===$('corrector-text'))return;
  try{
    if(values.corrector_document?.version===1){
      const saved=values.corrector_document;FredRichText.display($('corrector-text'),saved.source_html);
      if(saved.result_html&&saved.result_text){
        const root=FredRichText.sanitize(saved.result_html);
        if(FredRichText.plain(root)!==saved.result_text)throw new Error('Le résultat enregistré est incohérent.');
        correctorResultHTML=root.innerHTML;correctorResultText=saved.result_text;correctorAnswer={content:saved.result_text};correctorDisplay();
      }
    }else if(typeof values.corrector_text==='string')$('corrector-text').textContent=values.corrector_text;
  }catch(e){error('Le brouillon enrichi n’a pas pu être restauré : '+e.message);}
}
function correctorDisplay(){
  const show=!!correctorAnswer.content;$('corrector-result-empty').hidden=show;$('corrector-result').hidden=!show;
  if(show)FredRichText.display($('corrector-result'),correctorResultHTML||FredRichText.fromText(correctorAnswer.content).innerHTML);
}
const correctorModes={
  correct:{label:'Corriger',instruction:'Corrige l’orthographe, la grammaire, la conjugaison, les accords et la ponctuation du texte français. Conserve son sens, son registre et ses informations.'},
  professional:{label:'Reformuler professionnel',instruction:'Reformule le texte en français professionnel, clair, poli et naturel. Conserve toutes les informations et le sens exact. N’ajoute aucun fait ni engagement.'},
  friendly:{label:'Reformuler amical',instruction:'Reformule le texte en français amical, naturel et chaleureux, avec tutoiement. Corrige aussi les fautes. Conserve toutes les informations et le sens exact, sans ajouter de fait ni engagement.'}
};
const correctorButtonsOnce=buttons;buttons=function(){correctorButtonsOnce();for(const id of ['corrector-correct','corrector-pro','corrector-friendly'])$(id).disabled=busy||historySyncPending||!connected;const editor=$('corrector-text');editor.contentEditable=correctorRunning?'false':'true';editor.setAttribute('aria-readonly',String(correctorRunning));$('corrector-cancel').hidden=!correctorRunning;$('corrector-reuse').disabled=correctorRunning||!correctorAnswer.content;$('corrector-copy').disabled=correctorRunning||!correctorAnswer.content;};
const correctorShowOnce=showView;showView=function(name){correctorShowOnce(name);if(name==='corrector'){$('workspace-heading').textContent='Correcteur de français';if(!correctorRunning&&!correctorAnswer.content){const recent=library.find(c=>c.title.startsWith('Correcteur ·'));const answer=recent?.messages.findLast(m=>m.role==='assistant');if(answer?.content){correctorAnswer=answer;correctorDisplay();}}}};
function correctorChanged(){correctorDirty=true;clearTimeout(correctorDraftTimer);correctorDraftTimer=setTimeout(()=>uiPersistPreferences().catch(e=>error(e)),500);}
$('corrector-text').oninput=()=>{if(correctorText().length>FredRichText.MAX_TEXT){$('corrector-status').textContent='Le texte dépasse 100 000 caractères. Raccourcissez-le avant de corriger.';return;}correctorChanged();};
function correctorPaste(event){
  if(correctorRunning)return;event.preventDefault();
  try{
    const html=event.clipboardData?.getData('text/html'),text=event.clipboardData?.getData('text/plain')||'';
    const content=html?FredRichText.sanitize(html):FredRichText.fromText(text);
    if(correctorText().length+FredRichText.plain(content).length>FredRichText.MAX_TEXT)throw new Error('Le texte est limité à 100 000 caractères.');
    if(!content.textContent.trim()&&text.trim())content.textContent=text;
    const editor=$('corrector-text');editor.focus();FredRichText.insert(editor,content);correctorChanged();
    $('corrector-status').textContent=html?'Texte collé avec sa mise en forme.':'Texte collé. Le presse-papiers ne contenait pas de mise en forme.';
  }catch(e){$('corrector-status').textContent=e.message;}
}
$('corrector-text').addEventListener('paste',correctorPaste);
$('corrector-text').addEventListener('drop',event=>event.preventDefault());
$('corrector-copy').onclick=async()=>{try{const rich=await FredRichText.copy(correctorResultHTML||FredRichText.fromText(correctorAnswer.content).innerHTML,correctorAnswer.content,$('corrector-result'));$('corrector-status').textContent=rich?'Texte copié avec la mise en forme.':'Texte copié sans mise en forme : la copie enrichie n’est pas disponible ici.';}catch{error('Copie impossible. Sélectionnez le texte du résultat.');}};
$('corrector-reuse').onclick=()=>{FredRichText.display($('corrector-text'),correctorResultHTML||FredRichText.fromText(correctorAnswer.content).innerHTML);correctorChanged();uiPersistPreferences().catch(e=>error(e));$('corrector-text').focus();};
$('corrector-cancel').onclick=()=>{$('cancel').click();};
async function correctorRun(mode){
  if(busy||historySyncPending||!connected)return;
  let snapshot;try{snapshot=FredRichText.snapshot($('corrector-text').innerHTML);}catch(e){$('corrector-status').textContent=e.message;return;}
  if(!snapshot.fragments.length){$('corrector-status').textContent='Saisissez le texte à retravailler.';$('corrector-text').focus();return;}
  if(library.length>=200){error('Exportez puis supprimez une conversation pour enregistrer ce résultat.');return;}
  try{await uiPersistPreferences();await flushHistory();}catch(e){error(e);return;}
  const instruction=correctorModes[mode],old={answer:correctorAnswer,html:correctorResultHTML,text:correctorResultText};
  const answer={role:'assistant',content:'',reasoning_content:''};let candidateId=null;
  error('');correctorRunning=true;busy=true;replyProgress={phase:'requesting',started:Date.now(),lastEvent:Date.now()};controller=new AbortController();requestId=crypto.randomUUID().replaceAll('-','');buttons();
  $('corrector-status').textContent=instruction.label+' · en cours, mise en forme conservée…';
  const structure=' Le texte est fourni comme une liste JSON de fragments dans leur ordre de lecture. Les fragments ayant le même numéro de paragraphe forment un passage : lis-les ensemble pour corriger avec le contexte. Retourne uniquement un objet JSON {"fragments":[{"id":"f0","text":"texte corrigé"},...]}. Retourne exactement tous les identifiants fournis, une seule fois chacun. Conserve les espaces de début et de fin de chaque fragment. Ne supprime aucun fragment. Ne fusionne pas les fragments et ne déplace pas d’information entre les paragraphes. Répartis les mots corrigés ou reformulés dans les fragments correspondants, car chaque fragment garde sa mise en forme originale. N’ajoute ni balises HTML, ni Markdown, ni commentaire, ni clé supplémentaire.';
  try{
    const response=await fetch('/v1/chat/completions',{method:'POST',headers:{Authorization:'Bearer '+config.key,'Content-Type':'application/json','X-Qwen-Request':requestId},signal:controller.signal,body:JSON.stringify({model:config.model,messages:[{role:'system',content:instruction.instruction+structure},{role:'user',content:JSON.stringify({fragments:snapshot.fragments})}],stream:true,chat_template_kwargs:{enable_thinking:false}})});
    if(!response.ok){let value;try{value=await response.json();}catch{}throw Object.assign(new Error(value?.error?.message||'Le serveur a refusé la correction.'),{code:value?.error?.code});}
    const reader=response.body.getReader(),decoder=new TextDecoder();let pending='',complete=false,raw='';
    function frame(value){
      replyProgress.lastEvent=Date.now();
      const data=value.split(/\r?\n/).filter(line=>line.startsWith('data:')).map(line=>line.slice(5).trimStart()).join('\n');
      if(data==='[DONE]'){complete=true;return;}if(!data)return;
      const event=JSON.parse(data);if(event.error)throw new Error(event.error.message||'La correction a échoué.');
      const choice=event.choices?.[0];if(choice?.finish_reason)replyProgress.finish=choice.finish_reason;
      raw+=choice?.delta?.content||'';replyProgress.phase='answering';
      if(raw.length>1500000)throw new Error('Le résultat dépasse la taille autorisée.');
    }
    while(true){const {value,done}=await reader.read();pending+=done?decoder.decode():decoder.decode(value,{stream:true});const frames=pending.split(/\r?\n\r?\n/);pending=frames.pop();for(const value of frames)frame(value);if(done){if(pending.trim())frame(pending);break;}}
    if(!complete||replyProgress.finish==='length')throw new Error('La réponse est incomplète. Votre original et le dernier résultat sont conservés.');
    const result=FredRichText.apply(snapshot,FredRichText.parseResponse(raw));
    answer.content=result.text;correctorAnswer=answer;correctorResultHTML=result.html;correctorResultText=result.text;
    currentId=crypto.randomUUID();candidateId=currentId;messages=[{role:'user',content:instruction.label+' :\n\n'+snapshot.text},answer];
    library.unshift({id:currentId,title:('Correcteur · '+instruction.label+' · '+snapshot.text.slice(0,40)).slice(0,120),messages});
    save();await uiPersistPreferences();$('corrector-status').textContent=instruction.label+' · terminé. Mise en forme conservée ; résultat enregistré.';
  }catch(e){
    if(!candidateId){correctorAnswer=old.answer;correctorResultHTML=old.html;correctorResultText=old.text;}
    if(e.name==='TypeError')e.code='connection_error';$('corrector-status').textContent=e.name==='AbortError'?'Correction arrêtée. Votre original et le dernier résultat sont conservés.':e.message;if(e.name!=='AbortError')error(e);
  }finally{correctorRunning=false;correctorDisplay();busy=false;controller=null;render();drawLibrary();buttons();$('queue-state').textContent='';models();}
}
for(const [id,mode] of [['corrector-correct','correct'],['corrector-pro','professional'],['corrector-friendly','friendly']])$(id).onclick=()=>correctorRun(mode);
buttons();
if(location.hash==='#corrector')showView('corrector');
