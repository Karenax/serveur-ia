/* Dictation only. Sending text remains the composer's explicit action. */
(()=>{
  const prompt=document.getElementById('prompt'),row=document.querySelector('.send-row');
  if(!prompt||!row)return;
  const button=document.createElement('button');button.id='voice-start';button.type='button';button.className='secondary voice-button';button.textContent='Dicter';button.title='Dictée locale en français';
  const cancel=document.createElement('button');cancel.id='voice-cancel';cancel.type='button';cancel.className='secondary voice-button';cancel.textContent='Annuler';cancel.hidden=true;
  const status=document.createElement('span');status.id='voice-status';status.className='voice-status';status.setAttribute('role','status');status.setAttribute('aria-live','polite');
  row.insertBefore(button,document.getElementById('send'));row.insertBefore(cancel,button.nextSibling);document.getElementById('composer').append(status);
  const phases=new Set(['installing','verifying','permission','loading','listening','finishing','cancelling']);
  let state={phase:'idle',installed:false},session='',draft='',dictating=false,polling=false,acting=false,closed=false;
  window.voiceBusy=false;
  async function transport(action){
    if(window.AndroidClient?.voiceStatus){const result=JSON.parse(action?AndroidClient.voiceAction(JSON.stringify(action)):AndroidClient.voiceStatus());if(result.error)throw new Error(result.error);return result;}
    return api('/client/voice',action);
  }
  function unlock(){window.voiceBusy=false;dictating=false;if(typeof buttons==='function')buttons();if(typeof drawLibrary==='function')drawLibrary();}
  function render(value){
    if(session&&value.session&&value.session!==session)return;
    state=value;const active=phases.has(value.phase),installing=['installing','verifying'].includes(value.phase);
    const model=value.model||'Modèle français',size=value.model_bytes?'environ '+Math.ceil(value.model_bytes/1000000)+' Mo':'taille indiquée à l’installation';
    description.textContent=model+' · français · '+size+'. Microphone fermé à la fin de la dictée. Aucun envoi automatique. Chaque dictée dure au maximum deux minutes.';
    if(dictating){
      if(value.phase==='cancelled'){prompt.value=draft;unlock();}
      else {if(typeof value.text==='string')prompt.value=draft+(draft&&value.text?'\n':'')+value.text;if(!active)unlock();}
      prompt.dispatchEvent(new Event('input',{bubbles:true}));
    }
    const amount=value.downloaded_bytes&&value.model_bytes?' '+Math.floor(100*value.downloaded_bytes/value.model_bytes)+' %':'';
    status.textContent=(value.message||'Dictée locale · français')+amount+(value.phase==='listening'?' · '+(value.seconds||0)+' s · texte provisoire':'');
    button.textContent=value.phase==='listening'?'Terminer la dictée':installing?'Installation…':['loading','permission'].includes(value.phase)?'Chargement…':value.phase==='finishing'?'Finalisation…':value.installed?'Dicter':'Installer la dictée';
    button.setAttribute('aria-label',button.textContent);button.setAttribute('aria-pressed',String(value.phase==='listening'));
    const locked=typeof conversationLocked==='function'&&conversationLocked();
    button.disabled=acting||(active&&value.phase!=='listening')||(!active&&locked);
    cancel.hidden=!active;cancel.disabled=acting||value.phase==='cancelling';
  }
  async function refresh(){if(polling||acting||closed)return;polling=true;try{render(await transport());}catch(e){status.textContent=e.message;/* Keep the composer locked until the native session's end is confirmed. */}finally{polling=false;}}
  async function act(action){if(acting)return;acting=true;button.disabled=cancel.disabled=true;try{const value=await transport({action,...(['stop','cancel'].includes(action)?{session}: {})});if(action==='start'||action==='install')session=value.session||'';render(value);}catch(e){status.textContent=e.message;if(action==='start')unlock();}finally{acting=false;render(state);}}
  button.onclick=async()=>{
    if(state.phase==='listening'){await act('stop');return;}
    if(phases.has(state.phase)||acting||(typeof conversationLocked==='function'&&conversationLocked()))return;
    if(!state.installed){if(!confirm('Installer la reconnaissance française sur cet appareil ? '+Math.ceil((state.model_bytes||487601967)/1000000)+' Mo à télécharger. La reconnaissance fonctionne ensuite sans Internet ; aucun audio n’est envoyé au serveur.'))return;await act('install');return;}
    draft=prompt.value;dictating=true;window.voiceBusy=true;if(typeof buttons==='function')buttons();if(typeof drawLibrary==='function')drawLibrary();await act('start');
  };
  cancel.onclick=()=>act('cancel');
  const settings=document.createElement('details');settings.className='composer-options';
  const label=document.createElement('summary');label.textContent='Dictée';
  const description=document.createElement('p');description.textContent='Reconnaissance locale en français. Microphone fermé à la fin de la dictée. Aucun envoi automatique.';
  const reinstall=document.createElement('button');reinstall.type='button';reinstall.className='secondary';reinstall.textContent='Installer / réparer';
  const remove=document.createElement('button');remove.type='button';remove.className='secondary';remove.textContent='Désinstaller le modèle';
  reinstall.onclick=()=>{if(phases.has(state.phase)||acting)return;if(confirm('Télécharger et vérifier le modèle vocal local ?'))act('install');};
  remove.onclick=()=>{if(phases.has(state.phase)||acting)return;if(confirm('Supprimer le modèle vocal de cet appareil ?'+(!window.AndroidClient?' Il sert à la dictée et à la conversation.':'')))act('remove');};
  settings.append(label,description,reinstall,remove);document.querySelector('.composer-bottom').append(settings);
  window.voiceFinishForClose=async()=>{if(!dictating)return;if(['listening','loading','permission'].includes(state.phase))await act('stop');const deadline=Date.now()+120000;while(phases.has(state.phase)){if(Date.now()>deadline)throw new Error('La dictée se termine encore. Réessayez de fermer après la finalisation.');await new Promise(r=>setTimeout(r,250));await refresh();}};
  document.addEventListener('visibilitychange',()=>{if(document.hidden&&dictating&&state.phase==='listening')act('stop');else if(!document.hidden)refresh();});
  window.addEventListener('pagehide',()=>{closed=true;if(phases.has(state.phase)&&session){if(window.AndroidClient?.voiceAction)AndroidClient.voiceAction(JSON.stringify({action:'cancel',session}));else fetch('/client/voice',{method:'POST',headers:{Authorization:'Bearer '+config.key,'Content-Type':'application/json'},body:JSON.stringify({action:'cancel',session}),keepalive:true}).catch(()=>{});}});
  setInterval(()=>{if(!document.hidden||dictating)refresh();else render(state);},400);
  (async()=>{if(typeof clientReady!=='undefined')await clientReady;await refresh();})();
})();
