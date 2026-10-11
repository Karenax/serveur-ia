/* Voice administration: distinct CPU service, no changes to Qwen or EG2. */
(()=>{
  const card=document.createElement('section');card.className='topic-card';card.id='voice-service';
  const title=document.createElement('h3');title.textContent='Conversation vocale Windows';
  const description=document.createElement('p');description.textContent='Reconnaissance et microphone sur le client. Synthèse française Pocket TTS · Estelle sur le CPU du serveur. Un traitement vocal simultané, sans utilisation des P100.';
  const state=document.createElement('p');state.id='voice-service-state';state.setAttribute('aria-live','polite');
  const start=document.createElement('button');start.type='button';start.id='voice-service-start';start.className='button secondary';start.textContent='Activer la voix';
  const stop=document.createElement('button');stop.type='button';stop.id='voice-service-stop';stop.className='button quiet';stop.textContent='Désactiver la voix';
  card.append(title,description,state,start,stop);document.getElementById('exploitation').append(card);
  let pending=false;
  async function refresh(){if(pending)return;try{const response=await fetch('/api/voice');const value=await response.json();if(!response.ok)throw new Error('État vocal indisponible.');state.textContent=value.error||(!value.enabled?'Voix désactivée':value.phase==='loading'?'Chargement de la voix française…':value.ready?(value.busy?'Voix active · synthèse en cours':'Voix française prête · CPU'):'Voix arrêtée');start.disabled=value.phase==='loading'||value.ready;stop.disabled=!value.enabled;}catch(e){state.textContent=e.message;}}
  async function configure(enabled){pending=true;start.disabled=stop.disabled=true;try{const response=await fetch('/api/voice',{method:'POST',headers:{'Content-Type':'application/json','X-Launcher-Token':document.querySelector('meta[name="launcher-token"]').content},body:JSON.stringify({enabled})});const value=await response.json();if(!response.ok)throw new Error(value.error||'Commande vocale refusée.');}catch(e){state.textContent=e.message;}finally{pending=false;refresh();}}
  start.onclick=()=>configure(true);stop.onclick=()=>configure(false);setInterval(refresh,3000);refresh();
})();
