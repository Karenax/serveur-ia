async function clientState(){
  try{
    const state=await api('/client/state');
    $('local-api').textContent=state.local_api||'';
    $('local-api-key').value=state.key||'';
    if(typeof androidUpdateState==='function')androidUpdateState(state.update);
    const profileRequired=state.profile_required===true;
    loggedIn=!profileRequired;
    if(typeof uiApplyPreferences==='function')uiApplyPreferences(state.preferences);
    if(state.history&&historyReady&&!historySaving&&!historySyncPending){
      $('history-status').textContent=state.history.message||'Historique enregistré sur cet appareil.';
      if(state.history.needs_merge)serverHistoryReady=false;
    }
    $('account-status').textContent=profileRequired?'Profil à importer':'Accès personnel · Android';
    $('client-version').textContent='Kiara Android '+(state.version||config.version);
    $('android-profile-name').textContent=profileRequired?'Profil à importer':state.profile?.name||state.username||'Accès personnel actif';
    if(profileRequired){
      connected=false;buttons();
      $('connection').textContent='Importer un profil';
      $('connection').classList.remove('online');
      if($('connection-choice').open)$('connection-choice').close();
      if(!$('android-onboarding').open)$('android-onboarding').showModal();
      return;
    }
    if($('android-onboarding').open)$('android-onboarding').close();
    const c=state.connection||{};
    if(c.connection_required){
      connected=false;buttons();
      if(!$('connection-choice').open)$('connection-choice').showModal();
    }
    if(!endpointDirty)$('endpoint').value=state.endpoint||c.endpoint||'';
    if(typeof uiConnectionSettings==='function')uiConnectionSettings(state);
    if(typeof uiConnectionStatus==='function')uiConnectionStatus(c);
    if(!c.connected&&Number(c.checked_at)*1000>lastConnectionUpdate)connectionFailure({code:c.code,message:c.error});
    $('connection-diagnostic').textContent=(c.connected?'Serveur IA accessible.':c.error||(c.connection_required?'Choisissez votre mode de connexion.':'Connexion en cours…'))+'\nMode : '+(c.transport==='wireguard'?'WireGuard':'HTTPS')+'\nAdresse : '+(c.endpoint||state.endpoint||'À configurer');
  }catch(e){error(e);}
}
