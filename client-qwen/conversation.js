/* Explicit conversation session, local microphone, server speech. */
(()=>{
  const android=!!window.AndroidClient;
  const row=document.querySelector('.send-row'),prompt=$('prompt');if(!row||!prompt)return;
  // The written composer remains the submission transport, with dictation in chat.
  const page=wsElement('section',undefined,'voice-view');page.dataset.view='voice';page.hidden=true;
  page.setAttribute('aria-labelledby','voice-title');
  page.innerHTML=`<header class="voice-heading"><div class="voice-heading-name"><h2 id="voice-title">Vocal</h2><p id="voice-conversation-name"></p></div><div class="voice-heading-actions"><button id="voice-new" type="button" class="secondary">Nouvelle conversation</button><button id="voice-history" type="button" class="secondary">Historique</button><details class="menu" id="voice-conversation-menu"><summary aria-label="Actions de la conversation vocale">···</summary><div class="menu-body"><button id="voice-rename" type="button" class="secondary">Renommer</button><button id="voice-archive" type="button" class="secondary">Archiver</button><button id="voice-delete" type="button" class="secondary danger">Supprimer</button></div></details><button id="voice-settings-toggle" type="button" class="secondary" aria-controls="voice-settings-dialog" aria-expanded="false">Réglages</button><button id="voice-back" type="button" class="secondary">Ouvrir le chat</button></div></header>
    <form id="voice-rename-form" class="voice-rename-form" hidden><label for="voice-rename-input">Nom de la conversation</label><input id="voice-rename-input" maxlength="120" required><button type="submit" class="secondary primary">Enregistrer</button><button id="voice-rename-cancel" type="button" class="secondary">Annuler</button></form>
    <div class="voice-context-bar"><span id="voice-session-summary"></span><span id="voice-archived" hidden>Conversation archivée</span><button id="voice-update-notice" class="voice-text-button" type="button" hidden>Mettre le complément Max à jour</button></div><p id="voice-management-status" role="status" aria-live="polite"></p>
    <div class="voice-layout"><div class="voice-main"><div class="voice-stage">
      <div class="voice-orb" aria-hidden="true"><svg viewBox="0 0 320 320"><defs><radialGradient id="voice-orb-fill"><stop offset="0" stop-color="currentColor" stop-opacity=".12"/><stop offset="1" stop-color="currentColor" stop-opacity=".025"/></radialGradient></defs><circle cx="160" cy="160" r="98" fill="url(#voice-orb-fill)"/><g fill="none" stroke="currentColor"><path class="voice-contour"/><path class="voice-contour"/><path class="voice-contour"/></g></svg><canvas id="voice-constellation" width="320" height="320" hidden></canvas><canvas id="voice-waves" width="960" height="360" hidden></canvas></div>
      <div id="voice-wave-legend" class="voice-wave-legend"><span class="voice-wave-user"><i aria-hidden="true"></i>Votre micro <meter id="voice-mic-level" min="0" max="1" value="0" aria-label="Niveau de votre microphone"></meter></span><span class="voice-wave-ai"><i aria-hidden="true"></i>Voix de Kiara <meter id="voice-ai-level" min="0" max="1" value="0" aria-label="Niveau de la voix de Kiara"></meter></span></div>
      <h3 id="voice-state" role="status" aria-live="polite">Prêt à discuter</h3><div id="voice-status-slot"></div><div id="voice-actions" class="voice-actions"></div><div id="voice-quick-interruptions"></div>
    </div><details id="voice-transcript" class="voice-transcript"><summary>Échanges écrits</summary><p id="voice-transcript-empty" class="muted">Vos échanges apparaîtront ici pendant la conversation.</p><div id="voice-transcript-content"></div><button id="voice-sources" type="button" class="secondary" hidden>Voir les sources</button></details></div>
    <aside class="voice-settings" aria-labelledby="voice-settings-title"><h3 id="voice-settings-title">Réglages du vocal</h3>
      <fieldset><legend>Qualité</legend><label for="voice-quality" class="sr-only">Qualité vocale</label><select id="voice-quality"><option value="low">Low · Léger</option><option value="max">Max · Vocal avancé</option></select><p id="voice-quality-description" class="muted">Moteur léger sur le PC, voix sur le serveur.</p><div id="voice-execution-options" hidden><label for="voice-execution">Traiter le vocal sur</label><select id="voice-execution"><option value="auto">Automatique · PC ou serveur</option><option value="pc">Ce PC</option><option value="server">Serveur Kiara</option></select><button id="voice-test-max" type="button" class="secondary">Tester le PC et le serveur</button><p id="voice-max-status" role="status"></p><small>Si le serveur est choisi, le son du micro lui est transmis pour transcription.</small></div></fieldset>
      <fieldset><legend>Microphone</legend><p class="muted">Microphone choisi dans les réglages Windows.</p><div id="voice-interruptions-slot"></div></fieldset>
      <fieldset><legend>Voix de Kiara</legend><label for="voice-volume">Volume <output id="voice-volume-value" for="voice-volume">100 %</output></label><input id="voice-volume" type="range" min="0" max="100" value="100"><p class="muted">La voix française utilise la sortie audio de Windows.</p></fieldset>
      <fieldset><legend>Affichage</legend><label for="voice-animation-style">Animation</label><select id="voice-animation-style"><option value="waves">Ondes vocales 3D</option><option value="orb">Orbe</option><option value="constellation">Constellation</option></select><label class="voice-check voice-motion"><input id="voice-animation" type="checkbox" checked> Activer les mouvements</label><p class="muted" id="voice-motion-note">Les mouvements réduits de votre appareil sont respectés.</p></fieldset>
      <details class="voice-diagnostics"><summary>Informations vocales</summary><p>La conversation vocale utilise Qwen local.</p><p id="voice-engine-location"></p><p id="voice-last-latency" hidden></p><div id="voice-context-slot"></div></details>
      <p id="voice-preferences-status" role="status"></p><button id="voice-preferences-retry" type="button" class="secondary" hidden>Réessayer l’enregistrement</button>
    </aside></div>`;
  document.querySelector('.workspace').append(page);
  const navigation=wsElement('button','Vocal','nav-button');navigation.dataset.viewButton='voice';
  document.querySelector('[data-view-button="chat"]').after(navigation);
  uiNavTitles.voice='Vocal';uiPaths.voice='M9 5a3 3 0 0 1 6 0v7a3 3 0 0 1-6 0V5m-3 6v1a6 6 0 0 0 12 0v-1M12 18v4m-4 0h8';
  navigation.onclick=()=>showView('voice');
  const ongoing=wsElement('button','Vocal en cours','secondary');ongoing.id='voice-ongoing';ongoing.type='button';ongoing.hidden=true;
  ongoing.onclick=()=>{showView('voice');$('voice-title').tabIndex=-1;$('voice-title').focus();};document.querySelector('.workspace-top').append(ongoing);
  $('voice-back').onclick=()=>{showView('chat');prompt.focus();};
  const showPreviousView=showView;showView=function(name){if(name==='voice'&&isCorrection(library.find(c=>c.id===currentId))){if(conversationLocked()){error('Terminez la correction avant d’ouvrir le vocal.');return;}showPreviousView('chat');}showPreviousView(name);if(!page.hidden){$('workspace-heading').textContent='Vocal';if(!android&&!maxInfo&&!maxChecking)refreshMax();}else if(settingsDialog.open)settingsDialog.close();drawVoice();};
  const button=document.createElement('button');button.id='conversation-start';button.type='button';button.className='secondary voice-button';button.textContent='Conversation';
  const muteButton=document.createElement('button');muteButton.id='conversation-mute';muteButton.type='button';muteButton.className='secondary voice-button';muteButton.textContent='Muet';muteButton.hidden=true;muteButton.setAttribute('aria-pressed','false');
  const status=document.createElement('span');status.id='conversation-status';status.className='voice-status';status.setAttribute('role','status');status.setAttribute('aria-live','polite');
  $('voice-actions').append(button,muteButton);$('voice-status-slot').append(status);
  const options=document.createElement('div');options.className='controls';options.id='conversation-options';
  const interruptionLabel=document.createElement('label'),allowInterruptions=document.createElement('input');allowInterruptions.id='conversation-interruptions';allowInterruptions.type='checkbox';
  interruptionLabel.className='voice-check';interruptionLabel.append(allowInterruptions,document.createTextNode('Interrompre Kiara en parlant'));options.append(interruptionLabel);$('voice-interruptions-slot').append(options);
  const interruptionNote=wsElement('p',undefined,'muted');interruptionNote.id='voice-interruptions-note';options.append(interruptionNote);allowInterruptions.setAttribute('aria-describedby',interruptionNote.id);
  let voiceCapacity=null;
  const contextNote=document.createElement('span');contextNote.id='conversation-context';contextNote.textContent='Contexte vocal · capacité du modèle';contextNote.hidden=true;$('voice-context-slot').append(contextNote);
  window.conversationContext=value=>{if(active&&Number.isInteger(value?.capacity)&&value.capacity>0&&Number.isInteger(value.input_tokens)){voiceCapacity=value.capacity;contextNote.textContent='Contexte vocal · '+value.input_tokens.toLocaleString('fr-FR')+' / '+voiceCapacity.toLocaleString('fr-FR')+' tokens';}};
  async function persistVoice(){try{await uiPersistPreferences();$('voice-preferences-status').textContent='Réglages enregistrés';$('voice-preferences-retry').hidden=true;}catch(e){$('voice-preferences-status').textContent='Réglages non enregistrés. Réessayez.';$('voice-preferences-retry').hidden=false;error(e);}}
  allowInterruptions.onchange=()=>{syncAndroidPlayback();persistVoice();};$('voice-preferences-retry').onclick=persistVoice;
  const volume=$('voice-volume'),animation=$('voice-animation'),animationStyle=$('voice-animation-style');
  const quality=$('voice-quality'),execution=$('voice-execution');
  const gpuPanel=wsElement('div',undefined,'voice-gpu-options');gpuPanel.id='voice-gpu-options';gpuPanel.hidden=true;
  gpuPanel.innerHTML=`<label for="voice-gpu">Carte graphique de ce PC</label><select id="voice-gpu" aria-describedby="voice-gpu-status"><option value="auto">Automatique · carte dédiée en priorité</option></select><button id="voice-gpu-refresh" type="button" class="secondary">Actualiser les cartes</button><p id="voice-gpu-status" role="status" aria-live="polite"></p>`;
  $('voice-test-max').before(gpuPanel);
  const gpuSelect=$('voice-gpu');let gpuWorking='',gpuPendingSelection=null,gpuError='',gpuOptionsSignature='';
  if(android){
    quality.querySelector('[value="max"]').remove();execution.value='pc';
    page.querySelectorAll('fieldset')[1].querySelector('p').textContent='Microphone de cet appareil. L’écoute s’arrête en arrière-plan.';
    page.querySelectorAll('fieldset')[2].querySelector('p').textContent='La voix française utilise la sortie audio de votre appareil.';
  }
  const installPanel=wsElement('div',undefined,'voice-max-install');installPanel.hidden=true;
  installPanel.innerHTML=`<p id="voice-max-install-description" class="muted"></p><button id="voice-max-plan" type="button" class="secondary">Installer Max sur ce PC</button><div id="voice-max-confirm" hidden><p id="voice-max-size"></p><button id="voice-max-install" type="button" class="secondary primary">Télécharger et installer</button><button id="voice-max-decline" type="button" class="secondary">Plus tard</button></div><progress id="voice-max-progress" max="100" value="0" aria-label="Installation de Max" hidden></progress><p id="voice-max-install-status" role="status" aria-live="polite"></p><button id="voice-max-install-cancel" type="button" class="secondary" hidden>Arrêter l’installation Max</button>`;
  $('voice-execution-options').append(installPanel);
  const storagePanel=wsElement('fieldset');storagePanel.id='voice-max-storage';storagePanel.hidden=true;
  storagePanel.innerHTML=`<legend>Fichiers Max sur ce PC</legend><p id="voice-max-disk" class="muted"></p><p id="voice-max-folder" class="voice-folder"></p><div class="voice-actions"><button id="voice-max-open-folder" type="button" class="secondary">Ouvrir le dossier</button><button id="voice-max-remove" type="button" class="secondary danger">Supprimer Max de ce PC</button></div><p id="voice-max-storage-status" role="status" aria-live="polite"></p>`;
  $('voice-execution-options').closest('fieldset').after(storagePanel);
  $('voice-quick-interruptions').append(options);
  const settingsDialog=wsElement('dialog',undefined,'voice-settings-dialog');settingsDialog.id='voice-settings-dialog';settingsDialog.setAttribute('aria-labelledby','voice-settings-title');
  const settingsHeading=wsElement('header',undefined,'voice-settings-heading'),settingsClose=wsElement('button','Fermer','secondary');settingsClose.id='voice-settings-close';settingsClose.type='button';settingsClose.setAttribute('aria-label','Fermer les réglages du vocal');
  const settingsPane=page.querySelector('.voice-settings');settingsHeading.append($('voice-settings-title'),settingsClose);settingsDialog.append(settingsHeading,settingsPane);
  const settingsFooter=wsElement('footer',undefined,'voice-settings-footer'),settingsStop=wsElement('button','Raccrocher','secondary danger');settingsStop.type='button';settingsStop.id='voice-settings-stop';settingsStop.hidden=true;settingsFooter.append(settingsStop);settingsDialog.append(settingsFooter);document.body.append(settingsDialog);
  function openSettings(){if(!settingsDialog.open)settingsDialog.showModal();$('voice-settings-toggle').setAttribute('aria-expanded','true');}
  $('voice-settings-toggle').onclick=openSettings;settingsClose.onclick=()=>settingsDialog.close();settingsStop.onclick=()=>stop().catch(error);
  settingsDialog.addEventListener('close',()=>{$('voice-settings-toggle').setAttribute('aria-expanded','false');if(!page.hidden)$('voice-settings-toggle').focus();});
  $('voice-update-notice').onclick=()=>{openSettings();$('voice-max-plan').scrollIntoView({block:'center'});$('voice-max-plan').focus();};
  const managementStatus=$('voice-management-status');
  async function voiceAction(run){if(conversationLocked())return;try{managementStatus.textContent='';$('voice-conversation-menu').open=false;await run();drawVoice();}catch(e){managementStatus.textContent=e.message;}}
  function newVoiceConversation(){
    if(conversationLocked())return;if(library.length>=200){managementStatus.textContent='Limite de 200 conversations atteinte. Exportez puis supprimez une ancienne conversation.';return;}
    const model=conversationModel();save();currentId=crypto.randomUUID();messages=[];chatAttachments=[];attachmentRender();library.unshift({id:currentId,title:'Nouvelle conversation vocale',messages,...(model?{model}:{})});
    $('conversation-filter').value='active';save();render();drawLibrary();showView('voice');$('conversation-start').focus();
  }
  $('voice-new').onclick=()=>voiceAction(newVoiceConversation);
  const previousNew=$('new').onclick;$('new').onclick=()=>page.hidden?previousNew():voiceAction(newVoiceConversation);
  const previousOpen=openHistoryRecord;openHistoryRecord=function(record){const vocal=!page.hidden&&!isCorrection(record);previousOpen(record);if(vocal&&currentId===record?.id){managementStatus.textContent='';$('voice-rename-form').hidden=true;showView('voice');}};
  const previousUndo=$('undo-delete').onclick;$('undo-delete').onclick=async()=>{await previousUndo();if(!deletedConversation)managementStatus.textContent='Conversation restaurée.';drawVoice();};
  button.addEventListener('click',()=>{managementStatus.textContent='';});
  let voiceHistoryFocus=false;const closeSidebarBeforeVoice=uiCloseSidebar;uiCloseSidebar=function(restore=true){const returnToVoice=voiceHistoryFocus&&uiSidebarModal();closeSidebarBeforeVoice(restore);voiceHistoryFocus=false;if(restore&&returnToVoice&&!page.hidden)$('voice-history').focus();};
  $('voice-history').onclick=()=>{if(uiSidebarModal())return;voiceHistoryFocus=true;document.body.classList.remove('sidebar-collapsed');if(matchMedia('(max-width:850px)').matches)document.body.classList.add('sidebar-open');uiSyncSidebar();$('search-conversations').focus();};
  $('voice-rename').onclick=()=>{if(conversationLocked())return;$('voice-conversation-menu').open=false;$('voice-rename-form').hidden=false;$('voice-rename-input').value=library.find(c=>c.id===currentId)?.title||'';$('voice-rename-input').focus();$('voice-rename-input').select();};
  $('voice-rename-cancel').onclick=()=>{$('voice-rename-form').hidden=true;managementStatus.textContent='';$('voice-conversation-menu').querySelector('summary').focus();};
  $('voice-rename-form').onsubmit=event=>{event.preventDefault();voiceAction(async()=>{const name=$('voice-rename-input').value.trim();if(!name)throw new Error('Donnez un nom à la conversation.');await wsConversationAction(async()=>{library.find(c=>c.id===currentId).title=name.slice(0,120);});$('voice-rename-form').hidden=true;managementStatus.textContent='Nom enregistré.';});};
  $('voice-archive').onclick=()=>voiceAction(async()=>{const archived=!!library.find(c=>c.id===currentId)?.archived;await wsArchiveConversation(currentId);$('conversation-filter').value=archived?'active':'archived';drawLibrary();managementStatus.textContent=archived?'Conversation restaurée.':'Conversation archivée. Retrouvez-la dans l’historique, filtre Archivées.';});
  $('voice-delete').onclick=()=>{if(conversationLocked())return;const title=library.find(c=>c.id===currentId)?.title||'cette conversation';if(!confirm('Supprimer « '+title+' » et ses échanges ?'))return;voiceAction(async()=>{await wsDeleteConversation(currentId);managementStatus.textContent='Conversation supprimée. Vous pouvez annuler la suppression.';});};
  let maxInfo=null,maxChecking=false,maxTestTimer=null,maxPlan=null,maxPlanning=false,maxRemoving=false;
  const maxInstalling=()=>['downloading','verifying','testing'].includes(maxInfo?.installation?.phase);
  function downloadSize(bytes){return new Intl.NumberFormat('fr-FR',{maximumFractionDigits:1}).format(bytes/(bytes<1000**3?1000**2:1000**3))+(bytes<1000**3?' Mo':' Go');}
  function drawInstallation(locked){
    const info=maxInfo?.installation,device=info?.hardware;
    installPanel.hidden=!info||quality.value!=='max'||execution.value==='server'||!device?.eligible&&!maxInfo?.pc?.installed;
    if(installPanel.hidden)return;
    const installing=maxInstalling(),installed=maxInfo.pc?.installed;
    $('voice-max-install-description').textContent='Max se télécharge séparément. Carte détectée : '+((device?.cards||[]).map(card=>card.name).join(', ')||'détection indisponible')+'. AMD et NVIDIA utilisent le moteur Vulkan.';
    $('voice-max-plan').hidden=installing||!!maxPlan;
    $('voice-max-plan').disabled=locked||maxPlanning||maxRemoving||!!gpuWorking;
    $('voice-max-plan').textContent=maxPlanning?'Calcul du téléchargement…':installed?(maxInfo.pc.update_recommended?'Mettre à jour Max':'Réinstaller Max'):'Installer Max sur ce PC';
    $('voice-max-confirm').hidden=!maxPlan||installing;
    $('voice-max-install').disabled=locked||maxPlanning||!!gpuWorking;
    $('voice-max-install-cancel').hidden=!installing;
    $('voice-max-install-status').textContent=info.message||'';
    const progress=$('voice-max-progress');progress.hidden=!installing;
    if(installing&&info.phase==='downloading')progress.value=Math.min(100,100*(info.downloaded_bytes||0)/Math.max(1,info.download_bytes||1));
    else if(installing)progress.removeAttribute('value');
  }
  function drawQuality(){
    const locked=active||window.conversationBusy||acting||native.phase==='installing';
    options.hidden=false;
    quality.disabled=execution.disabled=locked||maxRemoving||!!gpuWorking;$('voice-test-max').disabled=locked||maxRemoving||!!gpuWorking||maxInstalling()||maxChecking||!!(maxInfo?.pc?.testing||maxInfo?.server?.testing);
    $('voice-execution-options').hidden=quality.value!=='max';
    const description=android?'Low · écoute sur cet appareil, voix sur le serveur.':active&&native.quality==='max'?'Max · traitement sur '+(native.execution==='server'?'le serveur Kiara.':'ce PC.'):quality.value==='low'?'Moteur léger sur le PC, voix sur le serveur.':'Écoute progressive et voix avancée.';
    if($('voice-quality-description').textContent!==description)$('voice-quality-description').textContent=description;
    const selected=execution.value==='auto'?['pc','server']:[execution.value];
    if(maxInfo){
      const message=selected.map(target=>(target==='pc'?'PC : ':'Serveur : ')+(maxInfo[target]?.message||'Mode Max indisponible')).join(' · ');
      if($('voice-max-status').textContent!==message)$('voice-max-status').textContent=message;
    }
    $('voice-engine-location').textContent=android?'Low · reconnaissance française sur cet appareil, voix sur le serveur':native.quality==='max'?'Max · '+(native.execution==='server'?'traitement sur le serveur Kiara':'traitement sur ce PC'):'Low · écoute sur ce PC, voix sur le serveur';
    if(android){allowInterruptions.disabled=!!native.installed&&native.aec_supported!==true;if(allowInterruptions.disabled)allowInterruptions.checked=false;}
    const interruptionHelp=allowInterruptions.disabled?'Cet appareil reprend l’écoute après la réponse de Kiara.':allowInterruptions.checked?'Vous pouvez couper sa réponse en parlant.':'Kiara termine sa réponse avant de vous écouter.';
    if(interruptionNote.textContent!==interruptionHelp)interruptionNote.textContent=interruptionHelp;
    $('voice-last-latency').hidden=(active?native.quality:quality.value)!=='max'||!maxLatency;
    drawInstallation(locked);
    gpuPanel.hidden=android||quality.value!=='max'||execution.value==='server';
    if(!gpuPanel.hidden){
      const gpu=maxInfo?.pc?.gpu,cards=gpu?.cards||[],choice=gpuPendingSelection??gpu?.selection??'auto';
      const values=[['auto','Automatique · carte dédiée en priorité'],...cards.map(card=>[card.id,card.description+(card.kind==='dedicated'?' · dédiée · '+Math.round(card.total_bytes/2**30)+' Go':card.kind==='integrated'?' · intégrée · mémoire partagée':'')])];
      if(choice!=='auto'&&!cards.some(card=>card.id===choice))values.push([choice,'Carte choisie indisponible']);
      const signature=JSON.stringify(values);if(signature!==gpuOptionsSignature){gpuOptionsSignature=signature;gpuSelect.replaceChildren(...values.map(([value,label])=>new Option(label,value)));}
      gpuSelect.value=choice;gpuSelect.title=gpuSelect.selectedOptions[0]?.textContent||'';
      gpuSelect.disabled=locked||maxRemoving||!!gpuWorking||maxInstalling()||!!maxInfo?.pc?.testing||!gpu?.supported;
      $('voice-gpu-refresh').disabled=gpuSelect.disabled;
      gpuPanel.setAttribute('aria-busy',String(!!gpuWorking));
      const chosen=cards.find(card=>card.id===choice),recommended=cards.find(card=>card.id===gpu?.recommended),used=maxInfo?.pc?.device;
      const message=gpuWorking==='detecting'?'Détection des cartes graphiques…':gpuWorking==='saving'?'Enregistrement de la carte…':gpuError||gpu?.error||
        (!maxInfo?.pc?.installed?'Installez Max pour détecter les cartes utilisables.':!gpu?.supported?'Mettez le complément Max à jour pour choisir la carte graphique.':
         choice!=='auto'&&!chosen?'La carte choisie est introuvable. Actualisez les cartes ou choisissez Automatique.':
         maxInfo.pc.device_loaded&&used?.description?'Utilisée : '+used.description+'.':chosen?'Choisie : '+chosen.description+'. Elle sera utilisée au prochain appel.':
         recommended?'En automatique : '+recommended.description+'.':gpu?.checked?'Aucune carte AMD ou NVIDIA accessible. Vérifiez le pilote Vulkan.':'Actualisez les cartes pour choisir celle à utiliser.');
      if($('voice-gpu-status').textContent!==message)$('voice-gpu-status').textContent=message;
    }
    const storage=maxInfo?.installation?.storage;
    storagePanel.hidden=android||quality.value!=='max';
    if(!storagePanel.hidden){
      $('voice-max-folder').textContent=storage?.path||'Dossier en cours de recherche…';
      $('voice-max-disk').textContent=!storage?'Recherche des fichiers Max…':storage.message|| (storage.exists?(Number.isFinite(storage.bytes)?downloadSize(storage.bytes)+' utilisés sur ce PC.':'Taille du dossier indisponible.'):'Aucun fichier Max sur ce PC.');
      $('voice-max-open-folder').disabled=!storage?.exists||maxRemoving;
      $('voice-max-remove').disabled=locked||maxInstalling()||maxRemoving||!!gpuWorking||maxChecking||!!maxInfo?.pc?.testing||!storage?.exists||storage?.removable===false;
      $('voice-max-remove').textContent=maxRemoving?'Suppression en cours…':'Supprimer Max de ce PC';
    }
  }
  async function refreshMax(){
    if(android)return;
    if(maxChecking)return;maxChecking=true;
    try{maxInfo=await api('/client/voice/max');}
    catch{maxInfo={pc:{available:false,message:'État Max indisponible'},server:{available:false,message:'État Max indisponible'}};}
    finally{maxChecking=false;drawQuality();}
    clearTimeout(maxTestTimer);if(maxInfo?.pc?.testing||maxInfo?.server?.testing||maxInstalling()||maxInfo?.installation?.hardware?.checked===false)maxTestTimer=setTimeout(refreshMax,2000);
    else if(active&&native.quality==='max'&&native.execution==='pc'&&!maxInfo?.pc?.device_loaded)maxTestTimer=setTimeout(refreshMax,1000);
    if(quality.value==='max'&&execution.value!=='server'&&maxInfo?.pc?.gpu?.supported&&!maxInfo.pc.gpu.checked&&!maxInfo.pc.gpu.error&&!maxInfo.pc.testing&&!gpuWorking&&!active&&!acting&&!maxInstalling())refreshGpu();
  }
  async function refreshGpu(){
    if(active||acting||gpuWorking||maxRemoving||maxInstalling()||maxInfo?.pc?.testing||window.conversationBusy)return;
    gpuWorking='detecting';gpuError='';drawQuality();
    try{maxInfo.pc=await api('/client/voice/max/devices',{});}
    catch(e){gpuError=e.message;if(maxInfo?.pc?.gpu)maxInfo.pc.gpu.error=e.message;}
    finally{gpuWorking='';drawQuality();}
  }
  $('voice-gpu-refresh').onclick=refreshGpu;
  gpuSelect.onchange=async()=>{
    if(active||acting||gpuWorking||maxRemoving||maxInstalling()||window.conversationBusy)return;
    gpuPendingSelection=gpuSelect.value;gpuWorking='saving';gpuError='';drawQuality();
    try{maxInfo.pc=await api('/client/voice/max/gpu',{device:gpuPendingSelection});}
    catch(e){gpuError='Carte non modifiée : '+e.message;}
    finally{gpuWorking='';gpuPendingSelection=null;drawQuality();if(!page.hidden)gpuSelect.focus();}
  };
  $('voice-max-plan').onclick=async()=>{
    if(active||acting||maxPlanning||gpuWorking||window.conversationBusy)return;
    maxPlanning=true;drawQuality();
    try{
      maxPlan=await api('/client/voice/max/plan',{});
      $('voice-max-size').textContent='À télécharger : '+downloadSize(maxPlan.download_bytes)+'. Espace libre nécessaire : '+downloadSize(maxPlan.required_disk_bytes)+'. Le test de performance est indicatif ; vous pourrez utiliser Max quel que soit son résultat.'+(maxPlan.reused_bytes?' Les modèles déjà présents sont réutilisés.':'');
      $('voice-max-install-status').textContent='';
      $('voice-max-install').textContent='Télécharger et installer · '+downloadSize(maxPlan.download_bytes);
      $('voice-max-confirm').hidden=false;$('voice-max-install').focus();
    }catch(e){maxPlan=null;if(maxInfo?.installation)maxInfo.installation.message=e.message;}
    finally{maxPlanning=false;drawQuality();if(maxPlan)$('voice-max-install').focus();}
  };
  $('voice-max-decline').onclick=()=>{maxPlan=null;drawQuality();$('voice-max-plan').focus();};
  $('voice-max-install').onclick=async()=>{
    if(!maxPlan||active||acting||gpuWorking||window.conversationBusy)return;
    try{const plan=maxPlan;maxPlan=null;maxInfo.installation=await api('/client/voice/max/install',{plan:plan.plan});await refreshMax();$('voice-max-install-cancel').focus();}
    catch(e){if(maxInfo?.installation)maxInfo.installation.message=e.message;drawQuality();}
  };
  $('voice-max-install-cancel').onclick=async()=>{try{maxInfo.installation=await api('/client/voice/max/install-cancel',{});await refreshMax();}catch(e){error(e);}};
  $('voice-max-open-folder').onclick=async()=>{try{await api('/client/voice/max/open-folder',{});$('voice-max-storage-status').textContent='Dossier ouvert.';}catch(e){$('voice-max-storage-status').textContent=e.message;}};
  $('voice-max-remove').onclick=async()=>{
    if(active||acting||gpuWorking||maxRemoving||maxInstalling()||window.conversationBusy)return;
    const storage=maxInfo?.installation?.storage;
    if(!storage?.exists||!confirm('Supprimer tous les fichiers Max de ce PC'+(Number.isFinite(storage.bytes)?' ('+downloadSize(storage.bytes)+')':'')+' ? Modèles, téléchargements et anciennes versions seront supprimés. Low et la dictée sont conservés.'))return;
    maxRemoving=true;drawQuality();$('voice-max-storage-status').textContent='Suppression des fichiers Max…';
    try{maxInfo.installation=await api('/client/voice/max/remove',{confirm:true});maxPlan=null;await refreshMax();$('voice-max-storage-status').textContent='Les fichiers Max de ce PC ont été supprimés.';}
    catch(e){$('voice-max-storage-status').textContent=e.message;}
    finally{maxRemoving=false;drawQuality();if(!page.hidden)$('voice-quality').focus();}
  };
  quality.onchange=()=>{drawQuality();if(quality.value==='max')refreshMax();persistVoice();};execution.onchange=()=>{drawQuality();persistVoice();};
  $('voice-test-max').onclick=async()=>{
    if(active||window.conversationBusy||acting)return;
    await refreshMax();const failures=[];
    for(const target of ['pc','server']){
      if(!maxInfo[target]?.installed){failures.push((target==='pc'?'PC':'Serveur')+' : moteur Max non installé');continue;}
      try{await api('/client/voice/max/test',{execution:target});}catch(e){failures.push(e.message);}
    }
    await refreshMax();if(failures.length)$('voice-max-status').textContent=failures.join(' · ');
  };
  volume.oninput=()=>{$('voice-volume-value').value=volume.value+' %';if(outputGain)outputGain.gain.value=Number(volume.value)/100;};
  volume.onchange=persistVoice;animation.onchange=()=>{drawVoice();persistVoice();};
  animationStyle.onchange=()=>{drawVoice();persistVoice();};
  window.conversationContextCapacity=()=>active?voiceCapacity:null;
  window.conversationPreferences=()=>({voice_interruptions:allowInterruptions.checked,voice_volume:Number(volume.value),voice_animation:animation.checked,voice_animation_style:animationStyle.value,voice_visual_version:2,voice_quality:quality.value,voice_execution:execution.value});
  window.conversationApplyPreferences=value=>{allowInterruptions.checked=value?.voice_interruptions===true;volume.value=Number.isInteger(value?.voice_volume)?value.voice_volume:100;volume.oninput();animation.checked=value?.voice_animation!==false;animationStyle.value=value?.voice_visual_version===2&&['waves','orb','constellation'].includes(value?.voice_animation_style)?value.voice_animation_style:'waves';quality.value=!android&&value?.voice_quality==='max'?'max':'low';execution.value=android?'pc':['pc','server'].includes(value?.voice_execution)?value.voice_execution:'auto';drawVoice();};
  let native={phase:'idle',installed:false},session='',active=false,acting=false,polling=false,seenSpeech=0,seenTurn=0;
  let context=null,sources=new Set(),nextAudio=0,epoch=0,speechQueue=[],speechBuffer='',speechRunning=false,currentSpeech='',speechAbort=null;
  let answerRef=null,heard='',interrupted=false,llmDone=false,pendingTurns=[],voiceRequestId='';
  let readingText='',playbackReferences=[];
  let heardCompletions=[];
  function flushHeard(){while(heardCompletions.length&&heardCompletions[0].token===epoch&&context&&context.currentTime>=heardCompletions[0].end-.01){const item=heardCompletions.shift();heard+=(heard?' ':'')+item.text;}}
  let maxLatency=null;
  function updateLatency(){
    if(!maxLatency)return;
    const fields=[];
    if(Number.isFinite(maxLatency.stt_final_ms))fields.push('Transcription : '+Math.round(maxLatency.stt_final_ms)+' ms');
    if(Number.isFinite(maxLatency.tts_first_audio_ms))fields.push('Préparation de la voix : '+Math.round(maxLatency.tts_first_audio_ms)+' ms');
    if(Number.isFinite(maxLatency.first_text_ms))fields.push('Premier texte : '+Math.round(maxLatency.first_text_ms)+' ms');
    if(Number.isFinite(maxLatency.speech_to_playback_ms))fields.push('Fin de parole → début de lecture estimé : '+Math.round(maxLatency.speech_to_playback_ms)+' ms');
    const label=$('voice-last-latency');label.hidden=!fields.length;label.textContent=fields.join(' · ');
    window.conversationMaxLatency={...maxLatency};
  }
  let muting=false;
  let sharedControlsSignature='';
  let ignoredSpeech=0,listenAfter=0,speechTimer=null,firstSpeechQueued=false,speechFailed=false;
  let outputGain=null,analyser=null,audioValues=null,animationFrame=null,lastFrame=0,orbStrength=2,transcriptSignature='';
  const reducedMotion=window.matchMedia('(prefers-reduced-motion: reduce)'),contours=[...page.querySelectorAll('.voice-contour')];
  const constellation=$('voice-constellation'),orb=page.querySelector('.voice-orb'),orbSvg=orb.querySelector('svg');
  const particleContext=constellation.getContext('2d');
  const waveCanvas=$('voice-waves'),waveContext=waveCanvas.getContext('2d'),waveLevels={mic:0,ai:0};
  let waveMic=0,waveAi=0,waveClock=0,waveLastTime=null,waveSignature='',wavePalette='',waveUserColor='',waveAiColor='';
  function paintWaves(time,moving,aiLevel){
    const ctx=waveContext;if(!ctx)return;
    const timestamp=Number(native.audio_level_at),fresh=!timestamp||Date.now()/1000-timestamp<.7;
    const listening=active&&!native.muted&&!native.mute_pending&&!native.microphone_closed&&!native.capture_paused&&(allowInterruptions.checked||!responding());
    const rms=listening&&fresh&&Number.isFinite(native.audio_level)?Math.max(0,native.audio_level-.006):0;
    waveLevels.mic=Math.min(1,rms*14);waveLevels.ai=active?aiLevel:0;
    if(moving){const dt=waveLastTime===null?0:Math.min(.08,Math.max(0,time-waveLastTime));waveLastTime=time;waveClock+=dt;waveMic+=(waveLevels.mic-waveMic)*.22;waveAi+=(waveLevels.ai-waveAi)*.22;}else{waveLastTime=null;waveMic=waveAi=0;}
    const ratio=Math.min(window.devicePixelRatio||1,1.5),width=960,height=360,pixels=Math.round(width*ratio);
    const palette=document.documentElement.dataset.theme||'light';
    if(palette!==wavePalette){wavePalette=palette;const css=getComputedStyle(page);waveUserColor=css.getPropertyValue('--voice-user').trim();waveAiColor=css.getPropertyValue('--voice-ai').trim();waveSignature='';}
    const quiet=waveMic<.002&&waveAi<.002,signature=palette+'|'+pixels;
    if(quiet&&waveSignature===signature)return;waveSignature=quiet?signature:'';
    if(waveCanvas.width!==pixels){waveCanvas.width=pixels;waveCanvas.height=Math.round(height*ratio);}
    ctx.setTransform(ratio,0,0,ratio,0,0);ctx.clearRect(0,0,width,height);
    const rows=android?7:10,steps=android?56:84;
    for(const [band,energy,color] of [[0,waveMic,waveUserColor],[1,waveAi,waveAiColor]]){
      const phase=waveClock*(band?3.8:4.4),amplitude=Math.pow(Math.min(1,energy),.64)*62,base=band?258:112,lines=[];
      for(let row=0;row<rows;row++){
        const z=(row/(rows-1)-.5)*70,line=[];
        for(let i=0;i<=steps;i++){
          const u=i/steps,x=(u-.5)*770,envelope=Math.pow(Math.sin(u*Math.PI),1.4);
          const signal=.65*Math.sin(u*22-phase+row*.19)+.25*Math.sin(u*39+phase*.6-row*.12)+.1*Math.cos(u*63-phase*.4);
          const y=signal*amplitude*envelope*(.8+row/(rows-1)*.2),ry=y*.77-z*.64,depth=y*.64+z*.77,scale=900/(900+depth);
          line.push({x:480+x*scale,y:base+ry*scale});
        }
        lines.push(line);
      }
      ctx.strokeStyle=ctx.fillStyle=color;ctx.lineWidth=energy>.03?1.3:.8;
      for(let row=0;row<lines.length;row++){
        const line=lines[row];
        if(row){ctx.beginPath();line.forEach((p,i)=>i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y));for(let i=lines[row-1].length-1;i>=0;i--)ctx.lineTo(lines[row-1][i].x,lines[row-1][i].y);ctx.closePath();ctx.globalAlpha=.025+energy*.045;ctx.fill();}
        ctx.beginPath();line.forEach((p,i)=>i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y));ctx.globalAlpha=.12+row/rows*.24+energy*.42;ctx.stroke();
      }
      ctx.globalAlpha=.07+energy*.14;ctx.lineWidth=.65;
      for(let col=0;col<=steps;col+=4){ctx.beginPath();lines.forEach((line,i)=>i?ctx.lineTo(line[col].x,line[col].y):ctx.moveTo(line[col].x,line[col].y));ctx.stroke();}
    }
    ctx.globalAlpha=1;
  }
  if(!particleContext){animationStyle.querySelector('[value="constellation"]').disabled=true;$('voice-motion-note').textContent='Constellation indisponible sur cet appareil. L’orbe reste disponible.';}
  let particleEnergy=0,particlePalette='',particleInk='',particleAccent='',particleClock=0,particleRotation=0,particleSpeed=.12,particleLastTime=null;
  let particleStaticSignature='';
  const particleBands=android?10:12,particleSteps=android?48:60;
  // Only the visible scene is rendered, with a fixed particle budget and no 3D library.
  function paintConstellation(t,state,moving,level){
    const ctx=particleContext,ratio=Math.min(window.devicePixelRatio||1,2),pixels=Math.round(320*ratio);
    const palette=document.documentElement.dataset.theme+'|'+state;
    if(!moving){const signature=palette+'|'+pixels;if(signature===particleStaticSignature)return;particleStaticSignature=signature;}else particleStaticSignature='';
    if(moving){const dt=particleLastTime===null?0:Math.min(.08,Math.max(0,t-particleLastTime));particleLastTime=t;particleSpeed+=((state==='thinking'?.48:.12)-particleSpeed)*Math.min(1,dt*4);particleClock+=dt;particleRotation+=dt*particleSpeed;}else particleLastTime=null;
    if(constellation.width!==pixels){constellation.width=constellation.height=pixels;}
    ctx.setTransform(ratio,0,0,ratio,0,0);ctx.clearRect(0,0,320,320);
    if(palette!==particlePalette){particlePalette=palette;particleInk=getComputedStyle(orb).color;particleAccent=getComputedStyle(page).getPropertyValue('--text').trim();}
    const target=state==='speaking'?level:state==='hearing'?.48:state==='thinking'?.3:state==='listening'?.12:0;
    if(moving)particleEnergy+=(target-particleEnergy)*.16;
    const phase=particleClock,rotation=particleRotation,tilt=.35+Math.sin(phase*.23)*.12;
    const cosY=Math.cos(rotation),sinY=Math.sin(rotation),cosX=Math.cos(tilt),sinX=Math.sin(tilt);
    const radius=99+particleEnergy*13+Math.sin(phase*1.4)*2,points=[],bands=[];
    function project(x,y,z){const rx=x*cosY+z*sinY,rz=z*cosY-x*sinY,ry=y*cosX-rz*sinX,depth=y*sinX+rz*cosX,scale=380/(380-depth);return {x:160+rx*scale,y:160+ry*scale,z:depth,scale};}
    ctx.fillStyle=particleInk;ctx.globalAlpha=.09;
    const halo=ctx.createRadialGradient(160,160,12,160,160,139);halo.addColorStop(0,particleInk);halo.addColorStop(1,'transparent');ctx.fillStyle=halo;ctx.fillRect(0,0,320,320);
    for(let band=0;band<particleBands;band++){
      const latitude=(band+.5)/particleBands*Math.PI,sinLat=Math.sin(latitude),cosLat=Math.cos(latitude),line=[];
      for(let step=0;step<particleSteps;step++){
        const a=step/particleSteps*Math.PI*2,twist=a+.2*Math.sin(latitude*3+phase*.4);
        const ripple=5*Math.sin(a*3+latitude*4+phase*.9)+particleEnergy*8*Math.sin(a*5-phase*2+latitude);
        const p=project((radius+ripple)*sinLat*Math.cos(twist),radius*cosLat+4*sinLat*Math.sin(a*2+phase*.6),(radius+ripple)*sinLat*Math.sin(twist));
        p.size=.55+(step%7===0?.65:.12);p.band=band;line.push(p);points.push(p);
      }
      bands.push(line);
    }
    // Sparse inner points give the surface depth without covering the voice state.
    for(let i=0;i<80;i++){const y=1-2*(i+.5)/80,a=i*2.399963+phase*.07,r=radius*(.3+.4*((i*17%31)/31)),s=Math.sqrt(1-y*y);const p=project(r*s*Math.cos(a),r*y,r*s*Math.sin(a));p.size=.5;p.inner=true;points.push(p);}
    ctx.strokeStyle=particleInk;ctx.lineWidth=.55;
    for(const band of bands){ctx.beginPath();band.forEach((p,i)=>i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y));ctx.closePath();ctx.globalAlpha=state==='muted'?.07:.14;ctx.stroke();}
    points.sort((a,b)=>a.z-b.z);
    for(const p of points){const depth=(p.z+115)/230;ctx.fillStyle=p.z>45&&state==='thinking'?particleAccent:particleInk;ctx.globalAlpha=(p.inner?.2:.22)+Math.max(0,depth)*.64;ctx.beginPath();ctx.arc(p.x,p.y,p.size*p.scale*(1+particleEnergy*.3),0,Math.PI*2);ctx.fill();}
    // A few orbiting lights mark activity; reduced-motion views stay still.
    for(let i=0;i<5;i++){
      const a=rotation*1.5+i*Math.PI*2/5;
      for(let tail=8;tail>=0;tail--){const angle=a-tail*.025,p=project(118*Math.cos(angle),26*Math.sin(angle*2+i),118*Math.sin(angle));ctx.fillStyle=particleInk;ctx.globalAlpha=(1-tail/9)*.52;ctx.beginPath();ctx.arc(p.x,p.y,(tail===0?1.8:.75)*p.scale,0,Math.PI*2);ctx.fill();}
    }
    ctx.globalAlpha=1;
  }
  function visualState(){
    if(acting)return !active&&window.conversationBusy?'closing':'connecting';
    if(!active&&window.conversationBusy)return 'closing';
    if(!active)return native.phase==='installing'?'connecting':native.phase==='error'?'error':'idle';
    if(!connected)return 'connecting';
    if(sources.size)return 'speaking';
    if(responding()||pendingTurns.length)return 'thinking';
    if(native.muted||native.mute_pending)return 'muted';
    if(native.partial)return 'hearing';
    return native.phase==='listening'?'listening':'connecting';
  }
  function paintOrb(time=0){
    const state=page.dataset.state,moving=animation.checked&&!reducedMotion.matches&&active&&!document.hidden&&!page.hidden;
    const t=moving?time/1000:0;let level=0;
    if(state==='speaking'&&analyser){analyser.getByteTimeDomainData(audioValues);let sum=0;for(const value of audioValues)sum+=((value-128)/128)**2;level=Math.min(1,Math.sqrt(sum/audioValues.length)*4);}
    if(animationStyle.value==='waves'&&waveContext){paintWaves(t,moving,level);return;}
    if(animationStyle.value==='constellation'&&particleContext){paintConstellation(t,state,moving,level);return;}
    const target=!moving?2:state==='speaking'?4+level*20:state==='thinking'?8:state==='hearing'?10:state==='listening'?4:2;
    orbStrength=moving?orbStrength+(target-orbStrength)*.18:target;const strength=orbStrength;
    for(let layer=0;layer<contours.length;layer++){
      const points=[];
      for(let i=0;i<=120;i++){const angle=i/120*Math.PI*2,radius=91+layer*10+strength*(.55*Math.sin(angle*3+t*(state==='thinking'?2.4:.9)+layer)+.45*Math.cos(angle*5-t*1.3+layer));points.push((160+Math.cos(angle)*radius).toFixed(2)+','+(160+Math.sin(angle)*radius).toFixed(2));}
      contours[layer].setAttribute('d','M'+points.join('L')+'Z');
    }
  }
  function animateOrb(time){animationFrame=null;if(page.hidden||document.hidden||!active||!animation.checked||reducedMotion.matches)return;if(time-lastFrame>=32){paintOrb(time);lastFrame=time;}animationFrame=requestAnimationFrame(animateOrb);}
  function drawVoice(){
    drawQuality();
    const state=visualState();page.dataset.state=state;
    const particles=animationStyle.value==='constellation'&&!!particleContext;
    const waves=animationStyle.value==='waves'&&!!waveContext;
    page.dataset.animation=waves?'waves':particles?'constellation':'orb';orbSvg.toggleAttribute('hidden',particles||waves);constellation.hidden=!particles;waveCanvas.hidden=!waves;$('voice-wave-legend').hidden=!waves;
    const label=({idle:'Prêt à discuter',connecting:'Connexion au vocal…',closing:'Fermeture du microphone…',listening:'Kiara vous écoute',hearing:'Vous parlez',thinking:'Kiara prépare sa réponse',speaking:'Kiara parle',muted:'Microphone coupé',error:'Vocal indisponible'})[state];
    if($('voice-state').textContent!==label)$('voice-state').textContent=label;
    ongoing.hidden=page.hidden?!(active||window.conversationBusy):true;
    const title=library.find(c=>c.id===currentId)?.title||'Conversation actuelle';
    if($('voice-conversation-name').textContent!==title)$('voice-conversation-name').textContent=title;
    const current=library.find(c=>c.id===currentId),locked=conversationLocked()||acting;
    for(const id of ['voice-new','voice-rename','voice-archive','voice-delete'])$(id).disabled=locked;
    $('voice-archive').textContent=current?.archived?'Restaurer':'Archiver';$('voice-archived').hidden=!current?.archived;
    settingsStop.hidden=!active&&!window.conversationBusy;settingsStop.disabled=acting;settingsFooter.hidden=settingsStop.hidden;
    const summary=(active?native.quality:quality.value)==='max'?'Max · '+((active?native.execution:execution.value)==='server'?'Serveur Kiara':execution.value==='auto'&&!active?'PC ou serveur automatique':'Ce PC'):'Low · voix sur le serveur';
    if($('voice-session-summary').textContent!==summary)$('voice-session-summary').textContent=summary;
    $('voice-update-notice').hidden=quality.value!=='max'||execution.value==='server'||!maxInfo?.pc?.update_recommended;
    for(const [id,value] of [['voice-mic-level',waveLevels.mic],['voice-ai-level',waveLevels.ai]])if(Math.abs($(id).value-value)>.01)$(id).value=value;
    if(!page.hidden&&!document.hidden){
      if($('voice-transcript').open){
        const exchanges=messages.filter(m=>['user','assistant'].includes(m.role)&&m.content),signature=JSON.stringify(exchanges.map(m=>[m.role,m.content]));
        if(signature!==transcriptSignature){transcriptSignature=signature;$('voice-transcript-content').replaceChildren(...exchanges.map(m=>{const entry=wsElement('div',undefined,'voice-exchange');entry.append(wsElement('strong',m.role==='user'?'Vous':'Kiara'),wsElement('p',m.content));return entry;}));}
        $('voice-transcript-empty').hidden=exchanges.length>0;
        $('voice-sources').hidden=!ws.lastSources?.length;
      }
      paintOrb(performance.now());
    }
    const moving=!page.hidden&&!document.hidden&&active&&animation.checked&&!reducedMotion.matches;
    if(!moving&&animationFrame!==null){cancelAnimationFrame(animationFrame);animationFrame=null;}
    if(moving&&animationFrame===null)animationFrame=requestAnimationFrame(animateOrb);
  }
  $('voice-transcript').ontoggle=drawVoice;$('voice-sources').onclick=()=>uiOriginalSources(ws.lastSources||[]);
  reducedMotion.addEventListener('change',drawVoice);document.addEventListener('visibilitychange',drawVoice);
  function responding(){return busy&&!llmDone||speechRunning||sources.size||speechQueue.length||speechBuffer.trim();}
  function responseStatus(){return native.muted?'Lecture en cours · microphone coupé':allowInterruptions.checked?'Vous pouvez l’interrompre en parlant':'L’écoute reprend après la réponse';}
  window.conversationBusy=false;
  window.conversationConnectionFailure=value=>{
    if(active&&['access_denied','access_revoked','access_suspended','access_expired','remote_disabled'].includes(value?.code))stop(value.message||'Conversation arrêtée : accès indisponible.').catch(error);
  };
  function needsRepair(){return native.phase==='error'&&native.message?.includes('corrompu');}
  function localModel(){return modelSource!=='hermes'||conversationModel()==='fred-qwen'||conversationModelEntry()?.provider==='Qwen local';}
  function refreshButtons(){const shared=JSON.stringify([active,window.conversationBusy,connected,conversationLocked()]);if(shared!==sharedControlsSignature){sharedControlsSignature=shared;buttons();drawLibrary();}const closing=!active&&window.conversationBusy,recognitionReady=native.installed||quality.value==='max'&&(maxInfo?.pc?.available&&maxInfo.pc.progressive&&execution.value!=='server'||native.max_tools_installed&&maxInfo?.server?.available&&execution.value!=='pc');if(active||closing)$('voice-start').disabled=true;button.textContent=active?'Raccrocher':closing?'Réessayer le raccrochage':native.phase==='installing'?'Arrêter l’installation':needsRepair()?'Réparer le vocal':recognitionReady?'Démarrer la conversation':quality.value==='max'?'Préparer le vocal Max'+(maxInfo?.server?.available?' · '+downloadSize(native.max_tools_bytes||9323036):''):'Installer le vocal';button.disabled=acting||!!gpuWorking||(!active&&!closing&&native.phase!=='installing'&&(conversationLocked()||!conversationModelAvailable()));button.title='Conversation orale directe avec Qwen local';button.setAttribute('aria-pressed',String(active));$('thinking').hidden=active||closing;contextNote.hidden=!active;const gauge=document.querySelector('.context-gauge');if(gauge)gauge.hidden=active||closing;muteButton.hidden=!active;muteButton.disabled=acting||muting||native.mute_pending;muteButton.textContent=native.muted?'Réactiver le micro':'Couper le micro';muteButton.setAttribute('aria-pressed',String(!!native.muted));muteButton.title=native.muted?'Réactiver le microphone':'Couper le microphone';drawVoice();}
  async function transportConversation(body){
    if(android&&AndroidClient.conversationStatus){const result=JSON.parse(body?AndroidClient.conversationAction(JSON.stringify(body)):AndroidClient.conversationStatus());if(result.error)throw new Error(result.error);return result;}
    return api('/client/conversation',body);
  }
  async function command(action,extra={}){return transportConversation({action,...(['stop','ack','mute','playback'].includes(action)?{session}:{}),...extra});}
  let playbackState='';
  function syncAndroidPlayback(){
    if((!android&&native.quality!=='max')||!active||!session)return;
    const interruptions=allowInterruptions.checked;
    const playing=!!responding(),key=session+':'+playing+':'+interruptions;
    if(key===playbackState)return;playbackState=key;
    command('playback',{playing,interruptions}).catch(e=>{playbackState='';stop(e.message).catch(error);});
  }
  muteButton.onclick=async()=>{
    if(!active||acting||muting)return;
    const desired=!native.muted,owner=session,restoreFocus=document.activeElement===muteButton;muting=true;refreshButtons();
    status.textContent=desired?'Coupure du microphone…':'Réactivation du microphone…';
    try{
      native=await command('mute',{muted:desired});const deadline=Date.now()+5000;
      while(active&&session===owner&&(native.mute_pending||native.muted!==desired||desired&&!native.microphone_closed)&&Date.now()<deadline){await new Promise(r=>setTimeout(r,50));native=await transportConversation();}
      if(!active||session!==owner)return;
      if(native.mute_pending||native.muted!==desired||desired&&!native.microphone_closed)throw new Error('L’état du microphone n’est pas confirmé. Réessayez.');
      status.textContent=desired?'Microphone coupé · vous entendez Kiara':'Microphone actif · je vous écoute';
    }catch(e){error(e);}finally{muting=false;refreshButtons();if(restoreFocus&&document.activeElement===document.body&&!page.hidden&&active)muteButton.focus();}
  };
  function stopAudio(){
    flushHeard();heardCompletions=[];
    clearTimeout(speechTimer);speechTimer=null;
    epoch++;speechQueue=[];speechBuffer='';speechAbort?.abort();
    for(const source of sources){try{source.stop();}catch{}}sources.clear();nextAudio=context?.currentTime||0;
    if(currentSpeech)api(native.quality==='max'?'/client/voice/max/cancel':'/v1/voice/cancel',{request_id:currentSpeech,...(native.quality==='max'?{session}:{})}).catch(()=>{});
  }
  function interrupt(reported=true){
    flushHeard();
    const outstanding=busy||speechRunning||sources.size||speechQueue.length||speechBuffer.trim();
    if(native.quality==='max'&&llmDone&&answerRef)answerRef=messages.find(message=>message.role==='assistant'&&message.turn_id===answerRef.turn_id)||answerRef;
    if(outstanding&&reported){interrupted=true;if(llmDone&&answerRef){answerRef.content=heard||'[Réponse interrompue avant la fin de sa première phrase.]';answerRef.interrupted=true;save();render();}}
    stopAudio();if(busy)$('cancel').click();status.textContent='Je vous écoute · réponse interrompue';
  }
  async function stop(message='Conversation terminée.'){ 
    if(!voiceImageAcquiring||!document.hidden)voiceImageClear();
    if(!active&&!window.conversationBusy&&native.phase!=='installing')return;
    const restoreFocus=document.activeElement===button||document.activeElement===muteButton;
    active=false;acting=true;interrupt(false);pendingTurns=[];status.textContent='Fermeture du microphone…';refreshButtons();let stopped=false;
    try{
      await command('stop');const deadline=Date.now()+7000;
      do{native=await transportConversation();if(!['permission','loading','listening','stopping','installing'].includes(native.phase))break;await new Promise(r=>setTimeout(r,100));}while(Date.now()<deadline);
      if(['permission','loading','listening','stopping','installing'].includes(native.phase))throw new Error('Le microphone se ferme encore. Réessayez dans un instant.');
      window.conversationBusy=false;if(typeof contextRefresh==='function')contextRefresh();await context?.close();context=null;outputGain=analyser=audioValues=null;nextAudio=0;stopped=true;
    }finally{acting=false;refreshButtons();status.textContent=stopped?message:'Fermeture du microphone non confirmée. Réessayez le raccrochage.';if(restoreFocus&&document.activeElement===document.body&&!page.hidden)button.focus();}
  }
  function plain(text){return text.replace(/```[\s\S]*?```/g,' ').replace(/https?:\/\/\S+/g,' ').replace(/\[([^\]]+)\]\([^)]*\)/g,'$1').replace(/[*_`#>|]/g,' ').replace(/\s+/g,' ').trim();}
  function words(text){return text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().match(/[a-z0-9]+/g)||[];}
  function echo(text){
    const candidate=words(text).slice(-80);if(candidate.length<2)return false;
    playbackReferences=playbackReferences.filter(reference=>reference.until>Date.now()).slice(-8);
    return playbackReferences.some(reference=>{
      const spoken=words(reference.text);
      if(spoken.join(' ').includes(candidate.join(' ')))return true;
      if(candidate.length<4)return false;
      // Allow a few recognition substitutions while keeping word order. This
      // supplements acoustic AEC; an unrelated utterance must still interrupt.
      let best=0;
      for(let start=0;start<spoken.length;start++){
        let at=start,matched=0;
        for(const word of candidate){const next=spoken.indexOf(word,at);if(next>=0&&next<start+candidate.length+4){matched++;at=next+1;}}
        best=Math.max(best,matched);
      }
      return best>=3&&best/candidate.length>=.82;
    });
  }
  function confirmedSpeech(text){const tokens=words(text);return tokens.length>=2||/^(stop|arrete|attends|pause|non)$/.test(tokens[0]||'');}
  function enqueue(text){
    text=plain(text);if(!text)return;
    while(text){
      const boundary=text.length>600?text.lastIndexOf(' ',600):-1;
      const end=text.length>600?(boundary>0?boundary:600):text.length;
      const part=text.slice(0,end);text=text.slice(end).trimStart();
      if(speechQueue.length>=24){
        const last=speechQueue.at(-1);if(last&&last.length+part.length+1<=600){speechQueue[speechQueue.length-1]=last+' '+part;continue;}
      }
      speechQueue.push(part);
    }
    pump();
  }

  // Low keeps Phonon and the classic short-turn loop, respecting the interruption choice.
  function classicLowSplitSpeech(final=false){
    while(speechBuffer){
      const fences=speechBuffer.match(/```/g)||[];if(fences.length%2&&!final)return;
      let length=0;const match=[...speechBuffer.matchAll(/[.!?;:\n](?:\s|$)/g)].find(value=>value.index>=2);
      if(match&&match.index<600)length=match.index+1;
      else if(speechBuffer.length>300)length=speechBuffer.lastIndexOf(' ',280)>40?speechBuffer.lastIndexOf(' ',280):280;
      else if(final)length=speechBuffer.length;else return;
      const text=speechBuffer.slice(0,length);speechBuffer=speechBuffer.slice(length).trimStart();enqueue(text);
    }
  }
  async function classicLowSpeak(text,token){
    const id=crypto.randomUUID().replaceAll('-','');currentSpeech=id;readingText=text;speechAbort=new AbortController();
    let response;
    for(let attempt=0;attempt<4;attempt++){
      if(!active||epoch!==token)return;
      response=await fetch('/v1/voice/speech',{method:'POST',headers:{Authorization:'Bearer '+config.key,'Content-Type':'application/json'},body:JSON.stringify({request_id:id,text,stream:true}),signal:speechAbort.signal});
      if(response.status!==429||attempt===3)break;
      await response.body?.cancel();await new Promise(resolve=>setTimeout(resolve,150*(attempt+1)));
    }
    if(!response.ok){let detail;try{detail=await response.json();}catch{}throw new Error(detail?.error?.message||'Lecture vocale indisponible.');}
    const reader=response.body.getReader(),decoder=new TextDecoder();let pending='',done=false;
    try{
      while(active&&epoch===token){const value=await reader.read();pending+=value.done?decoder.decode():decoder.decode(value.value,{stream:true});
        const frames=pending.split(/\r?\n\r?\n/);pending=frames.pop();
        if(pending.length>100000)throw new Error('Trame vocale trop volumineuse.');
        for(const event of frames){const line=event.split(/\r?\n/).find(l=>l.startsWith('data: '));if(!line)continue;const frame=JSON.parse(line.slice(6));if(frame.id!==id)throw new Error('Session audio invalide.');if(frame.error)throw new Error(frame.error);if(frame.pcm)await pcm(frame,token);if(frame.done){done=true;if(frame.cancelled&&epoch===token)throw new Error('Synthèse interrompue sur le serveur.');}}
        if(value.done)break;
      }
      if(active&&epoch===token&&!done){const incomplete=new Error('Connexion audio interrompue.');incomplete.audioIncomplete=true;throw incomplete;}
      while(active&&epoch===token&&context.currentTime<nextAudio)await new Promise(r=>setTimeout(r,30));
      if(active&&epoch===token)heard+=(heard?' ':'')+text;
    }finally{reader.cancel().catch(()=>{});if(currentSpeech===id)currentSpeech='';}
  }
  async function classicLowRefresh(){
    if(polling||acting||muting)return;polling=true;
    try{
      native=await transportConversation();
      if(!active&&native.phase==='installing')status.textContent='Installation des modèles · '+Math.floor(100*(native.downloaded_bytes||0)/native.model_bytes)+' %';
      else if(!active&&native.message)status.textContent=native.message;
      if(active){
        // A normal history sync follows every answer. It pauses new sends,
        // while the microphone and the completed answer's audio stay active.
        if(historyBlocked||conversationActionPending){await stop('Conversation arrêtée : vérifiez la synchronisation.');return;}
        if(!connected)status.textContent='Connexion interrompue · reconnexion en cours…';
        if(connected&&!conversationModelAvailable()&&!busy&&!speechRunning&&!sources.size){await stop('Conversation arrêtée : choisissez un modèle disponible.');return;}
        if(native.session!==session||['stopped','error'].includes(native.phase)){await stop(native.message||'Conversation arrêtée.');return;}
        if(native.muted)status.textContent=busy||speechRunning||sources.size?'Kiara répond · microphone coupé':'Microphone coupé · vous entendez Kiara';
        else if(connected&&native.phase==='listening'&&!busy&&!speechRunning&&!native.partial&&!pendingTurns.length)status.textContent='Je vous écoute · Qwen local · microphone actif';
        const partialSpeech=native.partial_speech_id??native.speech_id;
        const speechBlocked=!allowInterruptions.checked&&!!responding();
        if(speechBlocked)ignoredSpeech=Math.max(ignoredSpeech,native.speech_id||0,partialSpeech||0);
        if(!speechBlocked&&!native.muted&&!native.mute_pending&&!muting&&partialSpeech>Math.max(seenSpeech,ignoredSpeech)&&confirmedSpeech(native.partial||'')&&!echo(native.partial)){
          seenSpeech=partialSpeech;if(responding())interrupt();
        }
        if(!speechBlocked&&!native.muted&&!native.mute_pending&&native.partial&&partialSpeech>ignoredSpeech&&!busy&&!speechRunning)status.textContent='Vous : '+native.partial;
        for(const turn of native.turns||[]){
          if(native.muted||native.mute_pending||muting)break;
          if(turn.id<=seenTurn)continue;
          // Acknowledge before advancing the local cursor: a failed ACK is
          // retried and cannot discard a phrase which was never submitted.
          await command('ack',{turn:turn.id});seenTurn=turn.id;
          seenSpeech=Math.max(seenSpeech,turn.speech_id??native.speech_id??0);
          if(speechBlocked||(turn.speech_id??native.speech_id??0)<=ignoredSpeech)continue;
          if(echo(turn.text))continue;
          if(responding())interrupt();pendingTurns.push(turn);
        }
        if(connected&&!native.muted&&!native.mute_pending&&!busy&&!historySyncPending&&!historySaving&&!agentRecoveryPending&&conversationModelAvailable()&&pendingTurns.length)await submitTurn(pendingTurns.shift());
      }
      refreshButtons();
    }catch(e){if(active)await stop(e.message).catch(()=>{});else status.textContent=e.message;}
    finally{polling=false;}
  }
  function splitSpeech(final=false){
    if(native.quality!=='max')return classicLowSplitSpeech(final);
    while(speechBuffer){
      const fence=speechBuffer.indexOf('```');
      if(fence===0){const end=speechBuffer.indexOf('```',3);if(end<0){if(final)speechBuffer='';return;}speechBuffer=speechBuffer.slice(end+3).trimStart();continue;}
      const safe=fence>0?speechBuffer.slice(0,fence):speechBuffer;
      let length=0;
      for(const match of safe.matchAll(/[.!?](?=\s)/g)){
        if(match.index<2)continue;
        const prefix=safe.slice(0,match.index+1),last=prefix.match(/([^\s]+)$/)?.[1]||'';
        if(/^(?:[a-zà-ÿ]|m|mme|mlle|dr|pr|etc|env|ex|cf|p)\.$/i.test(last)||/^(?:[a-z]\.){2,}$/i.test(last)||/^\s*\d{1,3}\.$/.test(prefix))continue;
        length=match.index+1;break;
      }
      if(!length){
        const clause=[...safe.matchAll(/[,;:](?=\s)/g)].find(match=>match.index>=(firstSpeechQueued?100:36));
        if(clause)length=clause.index+1;
      }
      if(!length&&safe.length>280){const end=safe.lastIndexOf(' ',260);length=end>80?end:260;}
      if(!length&&(final||fence>0))length=safe.length;
      if(!length)return;
      firstSpeechQueued=true;
      const text=speechBuffer.slice(0,length);speechBuffer=speechBuffer.slice(length).trimStart();enqueue(text);
    }
  }
  async function pcm(frame,token){
    if(!active||epoch!==token||!context)return;
    if(frame.rate!==24000||typeof frame.pcm!=='string'||frame.pcm.length>24000)throw new Error('Trame audio serveur invalide.');
    const binary=atob(frame.pcm);if(binary.length%2)throw new Error('Trame audio incomplète.');
    const buffer=context.createBuffer(1,binary.length/2,frame.rate),values=buffer.getChannelData(0);
    for(let i=0;i<values.length;i++){let n=binary.charCodeAt(i*2)|(binary.charCodeAt(i*2+1)<<8);if(n>=32768)n-=65536;values[i]=n/32768;}
    while(active&&epoch===token&&nextAudio-context.currentTime>4)await new Promise(r=>setTimeout(r,50));
    if(!active||epoch!==token)return;
    const source=context.createBufferSource();source.buffer=buffer;source.connect(outputGain||context.destination);sources.add(source);
    source.onended=()=>{sources.delete(source);flushHeard();syncAndroidPlayback();drawVoice();};const start=Math.max(context.currentTime+.03,nextAudio);nextAudio=start+buffer.duration;source.start(start);drawVoice();
    if(native.quality==='max'&&maxLatency&&!maxLatency.playback_started){
      maxLatency.playback_started=true;
      if(Number.isFinite(maxLatency.speech_end_unix_ms))maxLatency.speech_to_playback_ms=Math.max(0,Date.now()-maxLatency.speech_end_unix_ms+(start-context.currentTime+(context.baseLatency||0)+(context.outputLatency||0))*1000);
      updateLatency();
    }
    listenAfter=Date.now()+Math.max(0,nextAudio-context.currentTime)*1000+350;
    if(readingText){const previous=playbackReferences.at(-1),until=Date.now()+Math.max(0,nextAudio-context.currentTime)*1000+3000;if(previous?.text===readingText)previous.until=until;else playbackReferences.push({text:readingText,until});playbackReferences=playbackReferences.slice(-8);}
    status.textContent=responseStatus();
  }
  async function speak(text,token){
    if(native.quality!=='max')return classicLowSpeak(text,token);
    const id=crypto.randomUUID().replaceAll('-','');currentSpeech=id;readingText=text;speechAbort=new AbortController();
    let response;
    for(let attempt=0;attempt<4;attempt++){
      if(!active||epoch!==token)return;
      response=await fetch(native.quality==='max'?'/client/voice/max/speech':'/v1/voice/speech',{method:'POST',headers:{Authorization:'Bearer '+config.key,'Content-Type':'application/json'},body:JSON.stringify({request_id:id,text,stream:true,...(native.quality==='max'?{session}:{})}),signal:speechAbort.signal});
      if(response.status!==429||attempt===3)break;
      await response.body?.cancel();await new Promise(resolve=>setTimeout(resolve,150*(attempt+1)));
    }
    if(!response.ok){let detail;try{detail=await response.json();}catch{}throw new Error(detail?.error?.message||'Lecture vocale indisponible.');}
    const reader=response.body.getReader(),decoder=new TextDecoder();let pending='',done=false;
    try{
      while(active&&epoch===token){const value=await reader.read();pending+=value.done?decoder.decode():decoder.decode(value.value,{stream:true});
        const frames=pending.split(/\r?\n\r?\n/);pending=frames.pop();
        if(pending.length>100000)throw new Error('Trame vocale trop volumineuse.');
        for(const event of frames){const line=event.split(/\r?\n/).find(l=>l.startsWith('data: '));if(!line)continue;const frame=JSON.parse(line.slice(6));if(frame.id!==id)throw new Error('Session audio invalide.');if(frame.error)throw new Error(frame.error);if(frame.pcm)await pcm(frame,token);if(native.quality==='max'&&maxLatency&&Number.isFinite(frame.metrics?.first_audio_ms)&&maxLatency.tts_first_audio_ms===undefined){maxLatency.tts_first_audio_ms=frame.metrics.first_audio_ms;updateLatency();}if(frame.done){done=true;if(frame.cancelled&&epoch===token)throw new Error('Synthèse interrompue sur le serveur.');}}
        if(value.done)break;
      }
      if(active&&epoch===token&&!done){const incomplete=new Error('Connexion audio interrompue.');incomplete.audioIncomplete=true;throw incomplete;}
      if(active&&epoch===token&&native.quality==='max'){
        // Generate the next sentence while this one plays. Only completed
        // playback enters the heard transcript used after an interruption.
        heardCompletions.push({token,text,end:nextAudio});flushHeard();return;
      }
      while(active&&epoch===token&&context.currentTime<nextAudio)await new Promise(r=>setTimeout(r,30));
      if(active&&epoch===token)heard+=(heard?' ':'')+text;
    }finally{reader.cancel().catch(()=>{});if(currentSpeech===id)currentSpeech='';}
  }
  async function pump(){
    if(speechRunning)return;speechRunning=true;
    try{while(active&&speechQueue.length){const token=epoch,text=speechQueue.shift();try{await speak(text,token);}catch(e){if(e.name==='AbortError'||token!==epoch)continue;speechFailed=true;speechQueue=[];speechBuffer='';if(!e.audioIncomplete)stopAudio();error(e);status.textContent='Lecture interrompue · le texte reste disponible';break;}}}
    finally{speechRunning=false;syncAndroidPlayback();if(active&&llmDone&&!sources.size)status.textContent=native.muted?'Microphone coupé · vous entendez Kiara':'Je vous écoute · microphone actif';}
  }
  window.conversationOnReplyStart=answer=>{if(!active)return;clearTimeout(speechTimer);speechTimer=null;firstSpeechQueued=false;speechFailed=false;contextNote.textContent='Contexte vocal · capacité du modèle';answerRef=answer;voiceRequestId=answer.turn_id;heard='';heardCompletions=[];if(native.quality==='max'&&maxLatency)maxLatency.request_started=performance.now();interrupted=false;llmDone=false;speechBuffer='';status.textContent=native.quality!=='max'?'Kiara prépare sa réponse':allowInterruptions.checked?'Vous pouvez l’interrompre en parlant':'L’écoute reprend après la réponse';};
  window.conversationDelta=text=>{if(active&&!interrupted&&!speechFailed){if(native.quality==='max'&&maxLatency&&text&&maxLatency.first_text_ms===undefined){maxLatency.first_text_ms=performance.now()-maxLatency.request_started;updateLatency();}speechBuffer+=text;splitSpeech();}};
  window.conversationOnReplyEnd=answer=>{
    if(answer!==answerRef)return;
    voiceRequestId='';
    llmDone=true;
    if(interrupted){answer.content=heard||'[Réponse interrompue avant la fin de sa première phrase.]';answer.interrupted=true;}
    else if(active&&!speechFailed)splitSpeech(true);
    syncAndroidPlayback();
  };
  async function submitTurn(turn){
    if(!active)return;
    if(voiceImageAcquiring||voiceImageLoading||busy||historySyncPending||historySaving||agentRecoveryPending||conversationActionPending||!conversationModelAvailable()){pendingTurns.unshift(turn);return;}
    if(native.quality==='max'){maxLatency={...turn.latency};updateLatency();}
    const image=voiceImagePending?.conversation===currentId?voiceImagePending:null;
    if(image)chatAttachments=[structuredClone(image.attachment)];
    const before=messages.length;
    prompt.value=turn.text;window.conversationSubmitting=true;
    try{$('composer').requestSubmit();if(image&&messages.length>before)voiceImageClear();}finally{window.conversationSubmitting=false;}
  }
  async function refresh(){
    syncAndroidPlayback();if(quality.value==='low')return classicLowRefresh();if(polling||acting||muting)return;polling=true;
    try{
      native=await transportConversation();
      if(!active&&native.phase==='installing')status.textContent='Installation des modèles · '+Math.floor(100*(native.downloaded_bytes||0)/native.model_bytes)+' %';
      else if(!active&&native.message)status.textContent=native.message;
      if(active){
        // A normal history sync follows every answer. It pauses new sends,
        // while the microphone and the completed answer's audio stay active.
        if(historyBlocked||conversationActionPending){await stop('Conversation arrêtée : vérifiez la synchronisation.');return;}
        if(!connected)status.textContent='Connexion interrompue · reconnexion en cours…';
        if(connected&&!conversationModelAvailable()&&!busy&&!speechRunning&&!sources.size){await stop('Conversation arrêtée : choisissez un modèle disponible.');return;}
        if(native.session!==session||['stopped','error'].includes(native.phase)){await stop(native.message||'Conversation arrêtée.');return;}
        if(native.muted)status.textContent=busy||speechRunning||sources.size?'Kiara répond · microphone coupé':'Microphone coupé · vous entendez Kiara';
        else if(connected&&native.phase==='listening'&&!busy&&!speechRunning&&!native.partial&&!pendingTurns.length)status.textContent='Microphone actif';
        const partialSpeech=native.partial_speech_id??native.speech_id;
        const speechBlocked=!allowInterruptions.checked&&!!responding();
        if(speechBlocked)ignoredSpeech=Math.max(ignoredSpeech,native.speech_id||0,partialSpeech||0);
        if(allowInterruptions.checked&&!native.muted&&!native.mute_pending&&!muting&&partialSpeech>Math.max(seenSpeech,ignoredSpeech)&&confirmedSpeech(native.partial||'')&&!echo(native.partial)){
          seenSpeech=partialSpeech;if(responding())interrupt();
        }
        if(!native.muted&&!native.mute_pending&&native.partial&&!busy&&!speechRunning)status.textContent='Vous : '+native.partial;
        for(const turn of native.turns||[]){
          if(native.muted||native.mute_pending||muting)break;
          if(turn.id<=seenTurn)continue;
          // Acknowledge before advancing the local cursor: a failed ACK is
          // retried and cannot discard a phrase which was never submitted.
          await command('ack',{turn:turn.id});seenTurn=turn.id;
          seenSpeech=Math.max(seenSpeech,turn.speech_id??native.speech_id??0);
          if(speechBlocked||(turn.speech_id??native.speech_id??0)<=ignoredSpeech)continue;
          if(echo(turn.text))continue;
          if(responding()&&!confirmedSpeech(turn.text))continue;
          if(responding())interrupt();pendingTurns.push(turn);
        }
        if(connected&&!native.muted&&!native.mute_pending&&!busy&&!historySyncPending&&!historySaving&&!agentRecoveryPending&&conversationModelAvailable()&&pendingTurns.length)await submitTurn(pendingTurns.shift());
      }
      refreshButtons();
    }catch(e){if(active)await stop(e.message).catch(()=>{});else status.textContent=e.message;}
    finally{polling=false;}
  }
  button.onclick=async()=>{
    if(acting||maxRemoving||gpuWorking)return;if(active||window.conversationBusy||native.phase==='installing'){await stop().catch(error);return;}
    if(conversationLocked()||!connected||!conversationModelAvailable())return;
    if(!localModel()){status.textContent='Choisissez Qwen local pour la conversation orale.';return;}
    if(prompt.value.trim()||chatAttachments.length){status.textContent='Envoyez ou conservez votre brouillon avant de démarrer une conversation vocale.';return;}
    const restoreFocus=document.activeElement===button;acting=true;refreshButtons();
    try{
      if(quality.value==='max'&&maxInstalling())throw new Error('Attendez la fin de l’installation Max.');
      const localMaxReady=quality.value==='max'&&maxInfo?.pc?.available&&(maxInfo.pc.progressive||native.installed)&&execution.value!=='server',serverMaxReady=quality.value==='max'&&maxInfo?.server?.available&&execution.value!=='pc';
      if(quality.value==='max'&&!localMaxReady&&!serverMaxReady){openSettings();status.textContent='Installez Max sur ce PC ou choisissez un serveur disponible.';$('voice-max-plan').focus();return;}
      if((!native.installed&&!localMaxReady&&!(serverMaxReady&&native.max_tools_installed))||needsRepair()){if(android&&!confirm('Installer la reconnaissance française sur cet appareil ? '+Math.ceil((native.model_bytes||487601967)/1000000)+' Mo à télécharger. Le modèle de dictée est réutilisé.'))return;native=await command('install',quality.value==='max'?{quality:'max'}:{});session=native.session;status.textContent='Installation des modèles de conversation…';return;}
      context=new AudioContext({sampleRate:24000});nextAudio=0;await context.resume();
      outputGain=context.createGain?.()||null;analyser=context.createAnalyser?.()||null;
      if(analyser){analyser.fftSize=256;audioValues=new Uint8Array(analyser.fftSize);analyser.connect(context.destination);}
      if(outputGain){outputGain.gain.value=Number(volume.value)/100;outputGain.connect(analyser||context.destination);}
      if(quality.value==='low'){const server=await api('/v1/voice/status');if(!server.ready)throw new Error(server.error||'Activez la voix dans la console serveur et attendez son chargement.');}
      native=await command('start',quality.value==='max'?{quality:'max',execution:execution.value}:{});session=native.session;active=true;window.conversationBusy=true;
      if(native.quality==='max')refreshMax();
      playbackState='';seenSpeech=seenTurn=ignoredSpeech=0;listenAfter=0;pendingTurns=[];playbackReferences=[];status.textContent=native.phase==='permission'?native.message:'Ouverture du microphone…';
    }catch(e){status.textContent=e.message;if(context){await context.close();context=null;}outputGain=analyser=audioValues=null;}
    finally{acting=false;refreshButtons();if(restoreFocus&&document.activeElement===document.body&&!page.hidden)button.focus();}
  };
  const closeDictation=window.voiceFinishForClose;
  const cancelBody=window.generationCancelBody;
  window.generationCancelBody=()=>active||busy&&requestId===voiceRequestId?{voice_conversation:true}:cancelBody?.()||{};
  window.conversationRequest=()=>active?{voice_conversation:true,reasoning_effort:'none',voice_realtime:true}:{};
  window.conversationSuspend=()=>{if(native.phase!=='permission')return stop('Conversation arrêtée au passage en arrière-plan.').catch(error);};
  window.voiceFinishForClose=async()=>{await stop();await closeDictation?.();};
  document.addEventListener('visibilitychange',()=>{if(document.hidden&&active&&native.phase!=='permission')stop('Conversation arrêtée au passage en arrière-plan.').catch(error);});
  window.addEventListener('pagehide',()=>{stopAudio();if(android&&session){command('stop').catch(()=>{});return;}if(active&&session)fetch('/client/conversation',{method:'POST',headers:{Authorization:'Bearer '+config.key,'Content-Type':'application/json'},body:JSON.stringify({action:'stop',session}),keepalive:true}).catch(()=>{});});
  let voiceImagePending=null,voiceImageLoading=false,voiceImageAcquiring=false,voiceImageEpoch=0;
  const imageTools=wsElement('div',undefined,'voice-image-tools');
  imageTools.innerHTML='<button id="voice-image-pick" class="secondary" type="button">Choisir une image</button><button id="voice-image-camera" class="secondary" type="button">Prendre une photo</button><button id="voice-image-capture" class="secondary" type="button">Choisir une capture</button><input id="voice-image-input" type="file" accept="image/png,image/jpeg,image/webp" hidden><input id="voice-camera-input" type="file" accept="image/jpeg" capture="environment" hidden><div id="voice-image-preview"></div><p id="voice-image-status" role="status" aria-live="polite"></p>';
  page.querySelector('.voice-main').append(imageTools);
  $('voice-image-capture').hidden=android;
  $('voice-image-camera').hidden=!android;
  function voiceImageClear(){voiceImageEpoch++;voiceImagePending=null;voiceImageAcquiring=false;$('voice-image-preview').replaceChildren();$('voice-image-status').textContent='';}
  function voiceImageBegin(){voiceImageClear();voiceImageAcquiring=true;return {conversation:currentId,epoch:voiceImageEpoch};}
  async function voiceImageChoose(file,conversation,token){
    if(voiceImageLoading||busy)throw new Error('Attendez la fin de la réponse avant de joindre une image.');
    if(!chatCapabilities.images)throw new Error('Le modèle actuel ne prend pas en charge les images.');
    if(!['image/png','image/jpeg','image/webp'].includes(file.type)||file.size>20*1024*1024)throw new Error('Choisissez une image PNG, JPEG ou WebP de moins de 20 Mo.');
    voiceImageLoading=true;
    try{
      const bitmap=await createImageBitmap(file),canvas=document.createElement('canvas');
      try{const scale=Math.min(1,2048/Math.max(bitmap.width,bitmap.height));canvas.width=Math.max(1,Math.round(bitmap.width*scale));canvas.height=Math.max(1,Math.round(bitmap.height*scale));canvas.getContext('2d').drawImage(bitmap,0,0,canvas.width,canvas.height);}finally{bitmap.close();}
      const url=canvas.toDataURL('image/jpeg',.82);
      if(url.length>2700000)throw new Error('Cette image reste trop volumineuse. Choisissez une zone plus petite.');
      if(conversation!==currentId||token!==voiceImageEpoch)throw new Error('Cette capture a été annulée. Joignez de nouveau l’image.');
      voiceImagePending={conversation,attachment:{kind:'image',name:(file.name||'Capture.jpg').slice(0,180),url}};
      const preview=$('voice-image-preview');preview.replaceChildren();attachmentDraw(preview,[voiceImagePending.attachment]);
      const remove=wsElement('button','Retirer l’image','secondary');remove.type='button';remove.onclick=()=>{voiceImageClear();$('voice-image-pick').focus();};preview.append(remove);
      $('voice-image-status').textContent='Cette image sera jointe à votre prochaine question et conservée dans la discussion.';
    }finally{voiceImageLoading=false;}
  }
  for(const [buttonId,inputId] of [['voice-image-pick','voice-image-input'],['voice-image-camera','voice-camera-input']]){
    const input=$(inputId);$(buttonId).onclick=()=>{if(busy||voiceImageLoading)return;input.kiaraCapture=voiceImageBegin();input.click();};
    input.onchange=async()=>{const file=input.files[0],capture=input.kiaraCapture||{conversation:currentId,epoch:voiceImageEpoch};input.value='';try{if(file)await voiceImageChoose(file,capture.conversation,capture.epoch);}catch(e){$('voice-image-status').textContent=e.message;}finally{if(capture.epoch===voiceImageEpoch)voiceImageAcquiring=false;}};
    input.addEventListener('cancel',()=>{voiceImageAcquiring=false;$('voice-image-status').textContent='Choix de l’image annulé.';});
  }
  $('voice-image-capture').onclick=async()=>{
    if(busy||voiceImageLoading||voiceImageAcquiring)return;
    if(!chatCapabilities.images){$('voice-image-status').textContent='Le modèle actuel ne prend pas en charge les images.';return;}
    const capture=voiceImageBegin(),conversation=capture.conversation;let stream;
    try{
      try{
        const result=await api('/client/capture',{});
        if(result.cancelled)return;
        if(!/^data:image\/jpeg;base64,[A-Za-z0-9+/=]+$/.test(result.image||''))throw new Error('Capture impossible. Réessayez.');
        const raw=atob(result.image.split(',')[1]),bytes=Uint8Array.from(raw,c=>c.charCodeAt(0));
        await voiceImageChoose(new File([bytes],'Capture.jpg',{type:'image/jpeg'}),conversation,capture.epoch);
        return;
      }catch(e){if(e.status!==404)throw e;}
      if(!navigator.mediaDevices?.getDisplayMedia)throw new Error('La capture n’est pas disponible ici. Joignez une image enregistrée.');
      stream=await navigator.mediaDevices.getDisplayMedia({video:true,audio:false});
      const video=document.createElement('video');video.srcObject=stream;await video.play();
      const canvas=document.createElement('canvas');canvas.width=video.videoWidth;canvas.height=video.videoHeight;canvas.getContext('2d').drawImage(video,0,0);
      const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',.85));
      if(!blob)throw new Error('Capture impossible. Réessayez.');
      await voiceImageChoose(new File([blob],'Capture.jpg',{type:'image/jpeg'}),conversation,capture.epoch);
    }catch(e){$('voice-image-status').textContent=e.name==='NotAllowedError'?'Capture annulée. Vous pouvez choisir une image.':e.message;}
    finally{for(const track of stream?.getTracks()||[])track.stop();if(capture.epoch===voiceImageEpoch)voiceImageAcquiring=false;}
  };
  const imageClose=window.voiceFinishForClose;
  window.voiceFinishForClose=async()=>{voiceImageClear();await imageClose?.();};
  setInterval(()=>{if(voiceImagePending&&voiceImagePending.conversation!==currentId)voiceImageClear();},250);
  const wakeControls=wsElement('fieldset');
  wakeControls.innerHTML='<legend>Activation vocale · essai</legend><label class="voice-check"><input id="voice-wake-enable" type="checkbox"> Attendre « Bonjour Kiara » sur cet appareil</label><p class="muted">Laissez Kiara ouverte. La détection est locale et garde le microphone actif jusqu’à l’appel ou à l’arrêt. La reconnaissance reste à vérifier avec votre voix.</p>';
  $('voice-settings-dialog').querySelector('aside').append(wakeControls);
  const wakeStatus=wsElement('p',undefined);wakeStatus.id='voice-wake-status';wakeStatus.setAttribute('role','status');wakeStatus.setAttribute('aria-live','polite');imageTools.after(wakeStatus);
  let wakeArmed=false,wakePolling=false,wakeSession='';
  async function wakeRequest(value){
    if(android){if(!AndroidClient.wakewordAction||!AndroidClient.wakewordStatus)throw new Error('Mettez le client Android à jour pour essayer le mot d’appel.');const result=JSON.parse(value?AndroidClient.wakewordAction(JSON.stringify(value)):AndroidClient.wakewordStatus());if(result.error)throw new Error(result.error);return result;}
    return api('/client/wakeword',value);
  }
  async function wakeStop(message='Activation vocale arrêtée.'){
    wakeArmed=false;$('voice-wake-enable').checked=false;
    if(wakeSession){
      await wakeRequest({action:'stop',session:wakeSession});const deadline=Date.now()+8000;
      let state;
      do{state=await wakeRequest();if(!['permission','loading','listening','stopping'].includes(state.phase)&&state.microphone_closed!==false)break;await new Promise(resolve=>setTimeout(resolve,100));}while(Date.now()<deadline);
      if(['permission','loading','listening','stopping'].includes(state.phase)||state.microphone_closed===false)throw new Error('Le microphone se ferme encore. Réessayez.');
      wakeSession='';
    }
    wakeStatus.textContent=message;
  }
  $('voice-wake-enable').onchange=async()=>{
    try{
      if(!$('voice-wake-enable').checked){await wakeStop();return;}
      if(window.conversationBusy||window.voiceBusy||busy||!connected)throw new Error('Terminez l’échange en cours et vérifiez la connexion avant d’activer le mot d’appel.');
      const state=await wakeRequest({action:'start'});wakeSession=state.session;wakeArmed=true;
      wakeStatus.textContent=state.phase==='permission'?'Autorisez le microphone pour activer le mot d’appel.':'Préparation du mot d’appel…';
    }catch(e){$('voice-wake-enable').checked=false;wakeStatus.textContent=e.message;}
  };
  const wakeStartConversation=button.onclick;
  button.onclick=async()=>{try{if(wakeArmed||wakeSession)await wakeStop();await wakeStartConversation();}catch(e){wakeStatus.textContent=e.message;}};
  const wakeClose=window.voiceFinishForClose;
  window.voiceFinishForClose=async()=>{if(wakeArmed||wakeSession)await wakeStop();await wakeClose?.();};
  document.addEventListener('visibilitychange',()=>{if(document.hidden&&(wakeArmed||wakeSession))wakeStop('Activation arrêtée lorsque Kiara passe en arrière-plan.').catch(e=>wakeStatus.textContent=e.message);});
  setInterval(async()=>{
    if(!wakeArmed||wakePolling)return;wakePolling=true;
    try{
      const state=await wakeRequest();
      if(state.phase==='detected'||state.turns?.length){await wakeStop('Kiara vous a entendu. Démarrage du vocal…');const claim=await api('/v1/workspace/action',{action:'voice_claim',request_key:crypto.randomUUID().replaceAll('-','')});if(!claim.accepted){wakeStatus.textContent=claim.message;return;}showView('voice');button.click();}
      else if(['error','stopped'].includes(state.phase)){await wakeStop(state.message||'Activation vocale arrêtée.');}
      else if(state.phase==='listening')wakeStatus.textContent='En attente de « Bonjour Kiara » · microphone actif sur cet appareil.';
    }catch(e){wakeArmed=false;$('voice-wake-enable').checked=false;wakeStatus.textContent=e.message;}
    finally{wakePolling=false;}
  },300);
  setInterval(refresh,200);refresh();
})();
