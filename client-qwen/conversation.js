/* Windows only: explicit conversation session, local microphone, server speech. */
(()=>{
  if(window.AndroidClient)return;
  const row=document.querySelector('.send-row'),prompt=$('prompt');if(!row||!prompt)return;
  const button=document.createElement('button');button.id='conversation-start';button.type='button';button.className='secondary voice-button';button.textContent='Conversation';
  const muteButton=document.createElement('button');muteButton.id='conversation-mute';muteButton.type='button';muteButton.className='secondary voice-button';muteButton.textContent='Muet';muteButton.hidden=true;muteButton.setAttribute('aria-pressed','false');
  const status=document.createElement('span');status.id='conversation-status';status.className='voice-status';status.setAttribute('role','status');status.setAttribute('aria-live','polite');
  row.insertBefore(button,$('send'));row.insertBefore(muteButton,button);$('composer').append(status);
  let native={phase:'idle',installed:false},session='',active=false,acting=false,polling=false,seenSpeech=0,seenTurn=0;
  let context=null,sources=new Set(),nextAudio=0,epoch=0,speechQueue=[],speechBuffer='',speechRunning=false,currentSpeech='',speechAbort=null;
  let answerRef=null,heard='',interrupted=false,llmDone=false,pendingTurns=[],voiceRequestId='';
  let readingText='',playbackReferences=[];
  let muting=false;
  window.conversationBusy=false;
  window.conversationConnectionFailure=value=>{
    if(active&&['access_denied','access_revoked','access_suspended','access_expired','remote_disabled'].includes(value?.code))stop(value.message||'Conversation arrêtée : accès indisponible.').catch(error);
  };
  function needsRepair(){return native.phase==='error'&&native.message?.includes('corrompu');}
  function localModel(){return modelSource!=='hermes'||conversationModel()==='fred-qwen'||conversationModelEntry()?.provider==='Qwen local';}
  function refreshButtons(){buttons();drawLibrary();const closing=!active&&window.conversationBusy;if(active||closing)$('voice-start').disabled=true;button.textContent=active?'Raccrocher':closing?'Réessayer le raccrochage':native.phase==='installing'?'Arrêter l’installation':needsRepair()?'Réparer la conversation':native.installed?'Conversation':'Installer la conversation';button.disabled=acting||(!active&&!closing&&(conversationLocked()||!conversationModelAvailable()));button.title='Conversation orale directe avec Qwen local';button.setAttribute('aria-pressed',String(active));muteButton.hidden=!active;muteButton.disabled=acting||muting||native.mute_pending;muteButton.setAttribute('aria-pressed',String(!!native.muted));muteButton.title=native.muted?'Réactiver le microphone':'Couper le microphone';}
  async function command(action,extra={}){return api('/client/conversation',{action,...(['stop','ack','mute'].includes(action)?{session}:{}),...extra});}
  muteButton.onclick=async()=>{
    if(!active||acting||muting)return;
    const desired=!native.muted,owner=session;muting=true;refreshButtons();
    status.textContent=desired?'Coupure du microphone…':'Réactivation du microphone…';
    try{
      native=await command('mute',{muted:desired});const deadline=Date.now()+5000;
      while(active&&session===owner&&(native.mute_pending||native.muted!==desired||desired&&!native.microphone_closed)&&Date.now()<deadline){await new Promise(r=>setTimeout(r,50));native=await api('/client/conversation');}
      if(!active||session!==owner)return;
      if(native.mute_pending||native.muted!==desired||desired&&!native.microphone_closed)throw new Error('L’état du microphone n’est pas confirmé. Réessayez.');
      status.textContent=desired?'Microphone coupé · vous entendez Fred':'Microphone actif · je vous écoute';
    }catch(e){error(e);}finally{muting=false;refreshButtons();}
  };
  function stopAudio(){
    epoch++;speechQueue=[];speechBuffer='';speechAbort?.abort();
    for(const source of sources){try{source.stop();}catch{}}sources.clear();nextAudio=context?.currentTime||0;
    if(currentSpeech)api('/v1/voice/cancel',{request_id:currentSpeech}).catch(()=>{});
  }
  function interrupt(reported=true){
    const outstanding=busy||speechRunning||sources.size||speechQueue.length||speechBuffer.trim();
    if(outstanding&&reported){interrupted=true;if(llmDone&&answerRef){answerRef.content=heard||'[Réponse interrompue avant la fin de sa première phrase.]';answerRef.interrupted=true;save();render();}}
    stopAudio();if(busy)$('cancel').click();status.textContent='Je vous écoute · réponse interrompue';
  }
  async function stop(message='Conversation terminée.'){ 
    if(!active&&!window.conversationBusy&&native.phase!=='installing')return;
    active=false;acting=true;interrupt(false);pendingTurns=[];status.textContent=message;
    try{
      await command('stop');const deadline=Date.now()+7000;
      do{native=await api('/client/conversation');if(!['loading','listening','stopping','installing'].includes(native.phase))break;await new Promise(r=>setTimeout(r,100));}while(Date.now()<deadline);
      if(['loading','listening','stopping','installing'].includes(native.phase))throw new Error('Le microphone se ferme encore. Réessayez dans un instant.');
      window.conversationBusy=false;await context?.close();context=null;nextAudio=0;
    }finally{acting=false;refreshButtons();status.textContent=message;}
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
  function enqueue(text){text=plain(text);if(!text)return;if(speechQueue.length>=24){stop('Réponse trop longue pour la lecture vocale. Le texte reste disponible.').catch(error);return;}speechQueue.push(text.slice(0,600));pump();}
  function splitSpeech(final=false){
    while(speechBuffer){
      const fences=speechBuffer.match(/```/g)||[];if(fences.length%2&&!final)return;
      let length=0;const match=[...speechBuffer.matchAll(/[.!?;:\n](?:\s|$)/g)].find(value=>value.index>=2);
      if(match&&match.index<600)length=match.index+1;
      else if(speechBuffer.length>300)length=speechBuffer.lastIndexOf(' ',280)>40?speechBuffer.lastIndexOf(' ',280):280;
      else if(final)length=speechBuffer.length;else return;
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
    const source=context.createBufferSource();source.buffer=buffer;source.connect(context.destination);sources.add(source);
    source.onended=()=>sources.delete(source);const start=Math.max(context.currentTime+.03,nextAudio);nextAudio=start+buffer.duration;source.start(start);
    if(readingText){const previous=playbackReferences.at(-1),until=Date.now()+Math.max(0,nextAudio-context.currentTime)*1000+3000;if(previous?.text===readingText)previous.until=until;else playbackReferences.push({text:readingText,until});playbackReferences=playbackReferences.slice(-8);}
    status.textContent=native.muted?'Fred répond · microphone coupé':'Fred répond · vous pouvez l’interrompre';
  }
  async function speak(text,token){
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
        if(pending.length>100000)throw new Error('Trame vocale trop volumineuse.');
        const frames=pending.split(/\r?\n\r?\n/);pending=frames.pop();
        for(const event of frames){const line=event.split(/\r?\n/).find(l=>l.startsWith('data: '));if(!line)continue;const frame=JSON.parse(line.slice(6));if(frame.id!==id)throw new Error('Session audio invalide.');if(frame.error)throw new Error(frame.error);if(frame.pcm)await pcm(frame,token);if(frame.done){done=true;if(frame.cancelled&&epoch===token)throw new Error('Synthèse interrompue sur le serveur.');}}
        if(value.done)break;
      }
      if(active&&epoch===token&&!done)throw new Error('Connexion audio interrompue.');
      while(active&&epoch===token&&context.currentTime<nextAudio)await new Promise(r=>setTimeout(r,30));
      if(active&&epoch===token)heard+=(heard?' ':'')+text;
    }finally{reader.cancel().catch(()=>{});if(currentSpeech===id)currentSpeech='';}
  }
  async function pump(){
    if(speechRunning)return;speechRunning=true;
    try{while(active&&speechQueue.length){const token=epoch,text=speechQueue.shift();try{await speak(text,token);}catch(e){if(e.name==='AbortError'||token!==epoch)continue;stopAudio();error(e);status.textContent='Lecture interrompue · le texte reste disponible';break;}}}
    finally{speechRunning=false;if(active&&llmDone&&!sources.size)status.textContent=native.muted?'Microphone coupé · vous entendez Fred':'Je vous écoute · microphone actif';}
  }
  window.conversationOnReplyStart=answer=>{if(!active)return;answerRef=answer;voiceRequestId=answer.turn_id;heard='';interrupted=false;llmDone=false;speechBuffer='';status.textContent='Qwen prépare la réponse · vous pouvez l’interrompre';};
  window.conversationDelta=text=>{if(active&&!interrupted){speechBuffer+=text;splitSpeech();}};
  window.conversationOnReplyEnd=answer=>{
    if(answer!==answerRef)return;
    voiceRequestId='';
    llmDone=true;
    if(interrupted){answer.content=heard||'[Réponse interrompue avant la fin de sa première phrase.]';answer.interrupted=true;}
    else if(active)splitSpeech(true);
  };
  async function submitTurn(turn){
    if(!active)return;
    if(busy||historySyncPending||historySaving||agentRecoveryPending||conversationActionPending||!conversationModelAvailable()){pendingTurns.unshift(turn);return;}
    prompt.value=turn.text;window.conversationSubmitting=true;
    try{$('composer').requestSubmit();}finally{window.conversationSubmitting=false;}
  }
  async function refresh(){
    if(polling||acting||muting)return;polling=true;
    try{
      native=await api('/client/conversation');
      if(!active&&native.phase==='installing')status.textContent='Installation des modèles · '+Math.floor(100*(native.downloaded_bytes||0)/native.model_bytes)+' %';
      else if(!active&&native.message)status.textContent=native.message;
      if(active){
        // A normal history sync follows every answer. It pauses new sends,
        // while the microphone and the completed answer's audio stay active.
        if(historyBlocked||conversationActionPending){await stop('Conversation arrêtée : vérifiez la synchronisation.');return;}
        if(!connected)status.textContent='Connexion interrompue · reconnexion en cours…';
        if(connected&&!conversationModelAvailable()&&!busy&&!speechRunning&&!sources.size){await stop('Conversation arrêtée : choisissez un modèle disponible.');return;}
        if(native.session!==session||['stopped','error'].includes(native.phase)){await stop(native.message||'Conversation arrêtée.');return;}
        if(native.muted)status.textContent=busy||speechRunning||sources.size?'Fred répond · microphone coupé':'Microphone coupé · vous entendez Fred';
        else if(connected&&native.phase==='listening'&&!busy&&!speechRunning&&!native.partial&&!pendingTurns.length)status.textContent='Je vous écoute · Qwen local · microphone actif';
        const partialSpeech=native.partial_speech_id??native.speech_id;
        if(!native.muted&&!native.mute_pending&&!muting&&partialSpeech>seenSpeech&&confirmedSpeech(native.partial||'')&&!echo(native.partial)){
          seenSpeech=partialSpeech;if(busy||speechRunning||sources.size)interrupt();
        }
        if(!native.muted&&!native.mute_pending&&native.partial&&!busy&&!speechRunning)status.textContent='Vous : '+native.partial;
        for(const turn of native.turns||[]){
          if(native.muted||native.mute_pending||muting)break;
          if(turn.id<=seenTurn)continue;
          // Acknowledge before advancing the local cursor: a failed ACK is
          // retried and cannot discard a phrase which was never submitted.
          await command('ack',{turn:turn.id});seenTurn=turn.id;
          seenSpeech=Math.max(seenSpeech,turn.speech_id??native.speech_id??0);
          if(echo(turn.text))continue;
          if(busy||speechRunning||sources.size)interrupt();pendingTurns.push(turn);
        }
        if(connected&&!native.muted&&!native.mute_pending&&!busy&&!historySyncPending&&!historySaving&&!agentRecoveryPending&&conversationModelAvailable()&&pendingTurns.length)await submitTurn(pendingTurns.shift());
      }
      refreshButtons();
    }catch(e){if(active)await stop(e.message).catch(()=>{});else status.textContent=e.message;}
    finally{polling=false;}
  }
  button.onclick=async()=>{
    if(acting)return;if(active||window.conversationBusy||native.phase==='installing'){await stop().catch(error);return;}
    if(conversationLocked()||!connected||!conversationModelAvailable())return;
    if(!localModel()){status.textContent='Choisissez Qwen local pour la conversation orale.';return;}
    if(prompt.value.trim()||chatAttachments.length){status.textContent='Envoyez ou conservez votre brouillon avant de démarrer une conversation vocale.';return;}
    acting=true;
    try{
      if(!native.installed||needsRepair()){native=await command('install');session=native.session;status.textContent='Installation des modèles de conversation…';return;}
      context=new AudioContext({sampleRate:24000});nextAudio=0;await context.resume();
      const server=await api('/v1/voice/status');if(!server.ready)throw new Error(server.error||'Activez la voix dans la console serveur et attendez son chargement.');
      native=await command('start');session=native.session;active=true;window.conversationBusy=true;
      seenSpeech=seenTurn=0;pendingTurns=[];playbackReferences=[];status.textContent='Conversation locale · Qwen direct · chargement du microphone';
    }catch(e){status.textContent=e.message;if(context){await context.close();context=null;}}
    finally{acting=false;refreshButtons();}
  };
  const closeDictation=window.voiceFinishForClose;
  const cancelBody=window.generationCancelBody;
  window.generationCancelBody=()=>active||busy&&requestId===voiceRequestId?{voice_conversation:true}:cancelBody?.()||{};
  window.conversationRequest=()=>active?{voice_conversation:true,reasoning_effort:'none'}:{};
  window.voiceFinishForClose=async()=>{await stop();await closeDictation?.();};
  document.addEventListener('visibilitychange',()=>{if(document.hidden&&active)stop('Conversation arrêtée au passage en arrière-plan.').catch(error);});
  window.addEventListener('pagehide',()=>{stopAudio();if(active&&session)fetch('/client/conversation',{method:'POST',headers:{Authorization:'Bearer '+config.key,'Content-Type':'application/json'},body:JSON.stringify({action:'stop',session}),keepalive:true}).catch(()=>{});});
  setInterval(refresh,200);refresh();
})();
