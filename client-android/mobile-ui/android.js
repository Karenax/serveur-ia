/* The native bridge owns credentials, profile import, transports and file export. */
'use strict';
document.body.classList.add('android-client');
const androidBridge=window.AndroidClient;
$('android-copy-api').onclick=()=>androidBridge.copyText($('local-api').textContent);
$('android-copy-api-key').onclick=()=>androidBridge.copyText($('local-api-key').value);
$('toggle-api-key').onclick=()=>{const input=$('local-api-key');input.type=input.type==='password'?'text':'password';$('toggle-api-key').textContent=input.type==='password'?'Afficher la clé':'Masquer la clé';};
function androidRequireBridge(){if(!androidBridge)throw new Error('Cette fonction est disponible dans l’application Fred Android.');return androidBridge;}
function androidNativeResult(value){
  if(typeof value==='string'&&value.trim().startsWith('{'))value=JSON.parse(value);
  if(value?.error)throw new Error(typeof value.error==='string'?value.error:value.error.message||'Action refusée.');
  if(value?.ok===false)throw new Error(value.message||'Action refusée.');
  return value;
}
function androidImportProfile(){
  try{$('android-profile-message').textContent='';androidRequireBridge().importProfile();}
  catch(e){$('android-profile-message').textContent=e.message;}
}
$('android-import-profile').onclick=androidImportProfile;
$('android-onboarding').addEventListener('cancel',event=>event.preventDefault());
$('android-manage-profile').onclick=()=>wsTry(()=>androidRequireBridge().openSettings());
$('android-network-settings').onclick=()=>wsTry(()=>androidRequireBridge().openSettings());
window.androidProfileImported=()=>location.reload();
window.androidProfileError=message=>{$('android-profile-message').textContent=String(message||'Import du profil impossible.');};
window.androidConnectionChanged=async()=>{endpointDirty=false;await clientState();if(!$('connection-choice').open)await models();};

// Native downloads keep credentials and APK bytes out of the WebView.
let androidUpdateInstalling=false;
function androidUpdateState(update){
  const pane=document.querySelector('[data-view="access"]');if(!pane)return;
  if(!$('android-update-status')){
    const card=wsElement('div',undefined,'settings-card');
    card.append(wsElement('h3','Mises à jour Android'));
    const status=wsElement('p');status.id='android-update-status';status.setAttribute('role','status');
    const check=wsElement('button','Rechercher une mise à jour','secondary');check.type='button';check.id='android-update-check';
    check.onclick=()=>wsTry(async()=>androidUpdateState(await api('/client/update/check',{})));
    card.append(status,check,wsElement('p','Fred recherche et télécharge les nouvelles versions pendant son utilisation. Android vous demandera de confirmer l’installation.'));
    pane.append(card);
    const banner=wsElement('div',undefined,'settings-card');banner.id='android-update-banner';banner.hidden=true;
    const label=wsElement('span');label.id='android-update-label';
    const install=wsElement('button','Installer la mise à jour','secondary');install.type='button';install.id='android-update-install';
    install.onclick=()=>wsTry(async()=>{
      if(androidUpdateInstalling||conversationLocked())return;
      androidUpdateInstalling=true;install.disabled=true;
      try{
        if(!await window.androidFlush())throw new Error('Enregistrement non confirmé. Réessayez avant d’installer la mise à jour.');
        androidRequireBridge().installUpdate();
      }finally{androidUpdateInstalling=false;install.disabled=conversationLocked();}
    });
    banner.append(label,document.createTextNode(' '),install);
    document.querySelector('.workspace-top').after(banner);
  }
  const value=update||{},phase=value.phase||'idle';
  $('android-update-status').textContent=value.message||'Les mises à jour sont recherchées automatiquement.';
  if(phase==='downloading'&&value.bytes>0)$('android-update-status').textContent+=' '+Math.min(100,Math.round(value.received/value.bytes*100))+' %';
  $('android-update-check').disabled=!loggedIn||['checking','downloading'].includes(phase);
  $('android-update-banner').hidden=!value.available;
  $('android-update-label').textContent=value.available?'Fred Android '+value.version+' est prêt à installer.':'';
  $('android-update-install').disabled=androidUpdateInstalling||conversationLocked()||['checking','downloading'].includes(phase);
}
androidUpdateState();

// The server inbox survives a closed app. System alerts are optional and only
// delivered while this client is active; no external push account is involved.
let androidLastInbox=null,androidOpeningNotification=false,androidLastNotificationOpen=0;
function androidNotificationControls(){
  const pane=document.querySelector('[data-view="notifications"]');if(!pane)return;
  let box=$('android-notification-settings');
  if(!box){box=wsElement('div',undefined,'android-notification-settings');box.id='android-notification-settings';
    const button=wsElement('button','Activer les alertes Android');button.id='android-notification-enable';button.type='button';
    const message=wsElement('p','');message.id='android-notification-status';
    button.onclick=()=>wsTry(()=>{const state=androidNativeResult(androidRequireBridge().notificationStatus());androidRequireBridge().setNotificationsEnabled(!state.enabled);});
    box.append(button,message);pane.append(box);
  }
  try{const state=androidNativeResult(androidRequireBridge().notificationStatus());
    $('android-notification-enable').textContent=state.enabled?'Désactiver les alertes Android':'Activer les alertes Android';
    $('android-notification-enable').disabled=!loggedIn;
    $('android-notification-status').textContent=state.enabled&&state.permitted?(state.discreet?'Alertes silencieuses actives pendant l’utilisation de Fred.':'Alertes avec le son Android pendant l’utilisation de Fred, selon vos réglages système.')+' Aucun texte privé sur l’écran verrouillé.':state.enabled?'Android bloque les alertes. La boîte de notifications reste disponible ; vérifiez les autorisations système.':'La boîte reste disponible dans Fred. Activez les alertes pour demander l’autorisation Android. L’application arrêtée reçoit ses notifications à la prochaine ouverture.';
    if(state.storage_available===false){$('android-notification-enable').disabled=true;$('android-notification-status').textContent='Le stockage local des alertes est illisible ; la boîte serveur reste disponible et votre fichier est conservé.';}
  }catch(e){$('android-notification-status').textContent='La boîte de notifications reste disponible dans Fred.';}
}
window.androidInboxChanged=payload=>{
  androidLastInbox=payload;
  try{androidRequireBridge().notificationInbox(JSON.stringify(payload||{}));}catch{}
  androidNotificationControls();
};
window.androidNotificationPermissionChanged=()=>{androidNotificationControls();if(androidLastInbox)window.androidInboxChanged(androidLastInbox);};
window.androidNotificationOpened=id=>{
  if(androidOpeningNotification||!connected||Date.now()-androidLastNotificationOpen<15000||typeof window.fredOpenNotificationById!=='function')return false;
  androidOpeningNotification=true;
  androidLastNotificationOpen=Date.now();
  Promise.resolve(window.fredOpenNotificationById(String(id))).then(()=>androidRequireBridge().notificationOpened(String(id))).catch(e=>{if([401,403,404,410].includes(e.status))androidRequireBridge().notificationOpened(String(id));error(e);}).finally(()=>androidOpeningNotification=false);
  return false;
};
androidNotificationControls();
setInterval(()=>{if(!document.hidden){androidNotificationControls();androidBridge?.notificationReady();}},3000);

// Connection selection must stay explicit after importing a profile.
let androidChoosingConnection=false;
chooseConnection=async function(mode){
  if(androidChoosingConnection||busy)return;
  androidChoosingConnection=true;
  $('choose-https').disabled=$('choose-wireguard').disabled=true;
  $('connection-choice-error').textContent='';
  try{
    androidNativeResult(androidRequireBridge().setConnectionMode(mode));
    endpointDirty=false;
    $('connection-transfer-status').textContent='Connexion '+(mode==='wireguard'?'WireGuard':'HTTPS')+' sélectionnée.';
    const state=await api('/client/state');
    if(state.connection?.connection_required)throw new Error('Le mode de connexion n’a pas été enregistré. Réessayez.');
    $('connection-choice').close();
    await clientState();await models();
  }catch(e){$('connection-choice-error').textContent=e.message;$('connection-transfer-status').textContent=e.message;}
  finally{androidChoosingConnection=false;$('choose-https').disabled=$('choose-wireguard').disabled=false;}
};
$('choose-https').onclick=()=>chooseConnection('https');
$('choose-wireguard').onclick=()=>chooseConnection('wireguard');
$('connection-mode').onchange=()=>{endpointDirty=true;$('connection-transfer-status').textContent='Touchez Appliquer la connexion pour utiliser ce mode.';};
$('endpoint-form').onsubmit=event=>{event.preventDefault();if(!loggedIn)return androidImportProfile();chooseConnection($('connection-mode').value);};
uiConnectionSettings=function(state){
  if(!endpointDirty)$('connection-mode').value=state.connection?.transport==='wireguard'?'wireguard':'https';
  $('connection-mode').disabled=busy||androidChoosingConnection;
  $('endpoint-form').querySelector('[type="submit"]').disabled=busy||androidChoosingConnection;
  $('android-network-settings').disabled=busy;
};

// All download sources use the Android document chooser, including binary originals.
async function androidSaveFile(filename,data,mime='text/plain;charset=utf-8'){
  const blob=data instanceof Blob?data:new Blob([data],{type:mime});
  if(blob.size>16*1024*1024)throw new Error('Export limité à 16 Mo par fichier.');
  const base64=await new Promise((resolve,reject)=>{
    const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);
    reader.onerror=()=>reject(new Error('Préparation de l’export impossible.'));reader.readAsDataURL(blob);
  });
  androidNativeResult(androidRequireBridge().exportFile(String(filename),mime,String(base64)));
}
wsDownload=function(filename,data,mime){return wsTry(()=>androidSaveFile(filename,data,mime||'text/markdown;charset=utf-8'));};
$('export-conversations').onclick=()=>wsTry(async()=>{
  save();await androidSaveFile('conversations-fred.json',JSON.stringify({version:1,conversations:library},null,2),'application/json');
});
const androidOriginalCopyText=copyText;
copyText=async function(text){
  if(androidBridge){androidNativeResult(androidBridge.copyText(String(text)));return;}
  return androidOriginalCopyText(text);
};
window.androidExportResult=(success,message)=>{
  selectionStatus.textContent=message||(success?'Fichier enregistré.':'Export annulé.');
  clearTimeout(selectionStatusTimer);selectionStatusTimer=setTimeout(()=>selectionStatus.textContent='',3000);
};
document.addEventListener('click',event=>{
  const anchor=event.target.closest('a[href]');if(!anchor||anchor.hasAttribute('download'))return;
  let url;try{url=new URL(anchor.href);}catch{return;}
  if(!['https:','http:'].includes(url.protocol)||url.origin===location.origin)return;
  event.preventDefault();wsTry(()=>androidRequireBridge().openUrl(url.href));
},true);

// Make conversation actions available by tapping instead of relying on desktop drag/drop.
wsPrepareConversationDrag=function(button){button.draggable=false;button.title='Ouvrir la conversation';button.ondragstart=null;button.ondragend=null;};
function androidConversationActions(){
  for(const button of document.querySelectorAll('.history-navigation [data-conversation-id]')){
    if(button.parentElement.classList.contains('android-conversation-row'))continue;
    const row=wsElement('div',undefined,'android-conversation-row');button.before(row);row.append(button);
    const actions=wsElement('button','···','android-conversation-actions');actions.type='button';
    actions.setAttribute('aria-label','Actions de la conversation '+button.textContent.trim());
    actions.disabled=conversationLocked();
    actions.onclick=()=>wsTry(()=>wsOpenConversationMenu(button.dataset.conversationId,actions));
    row.append(actions);
  }
}
const androidOriginalDrawLibrary=drawLibrary;drawLibrary=function(){androidOriginalDrawLibrary();androidConversationActions();};
const androidOriginalDrawSidebarProjects=wsDrawSidebarProjects;
wsDrawSidebarProjects=function(){androidOriginalDrawSidebarProjects();androidConversationActions();};
drawLibrary();

// Android resizes the WebView for the IME; visualViewport also handles tablet floating keyboards.
let androidFullHeight=window.innerHeight;
function androidViewportChanged(){
  const viewport=window.visualViewport;
  const height=Math.round(Math.min(window.innerHeight,viewport?.height||window.innerHeight));
  const editing=['INPUT','TEXTAREA'].includes(document.activeElement?.tagName);
  if(!editing)androidFullHeight=window.innerHeight;
  const keyboard=editing&&androidFullHeight-height>120;
  document.documentElement.style.setProperty('--android-height',height+'px');
  document.body.classList.toggle('android-keyboard',keyboard);
  if(typeof chatScrollChanged==='function')chatScrollChanged();
}
window.addEventListener('resize',androidViewportChanged);
window.visualViewport?.addEventListener('resize',androidViewportChanged);
document.addEventListener('focusin',androidViewportChanged);
document.addEventListener('focusout',()=>requestAnimationFrame(androidViewportChanged));
androidViewportChanged();

window.androidBack=()=>{
  if($('android-onboarding').open||$('connection-choice').open)return false;
  if($('fred-source-dialog')?.open){$('fred-source-dialog').close();return true;}
  if(!wsConversationMenu.hidden){wsCloseConversationMenu();return true;}
  if(!selectionMenu.hidden){selectionClose();return true;}
  if(document.body.classList.contains('sidebar-open')){document.body.classList.remove('sidebar-open');uiSyncSidebar();return true;}
  if(!$('connection-panel').hidden){$('connection-close').click();return true;}
  if(!$('ws-side').hidden){$('ws-side').hidden=true;return true;}
  const menu=document.querySelector('.menu[open],.composer-options[open]');if(menu){menu.open=false;return true;}
  const current=document.querySelector('.workspace>[data-view]:not([hidden])');
  if(current&&current.dataset.view!=='chat'){showView('chat');return true;}
  return false;
};
window.androidFlush=async()=>{
  try{if(historyBlocked)throw new Error('Enregistrement bloqué : exporter votre travail puis recharger le client.');await uiPersistPreferences();if(historyReady)await flushHistory();return true;}
  catch(e){error(e);return false;}
};
document.addEventListener('visibilitychange',()=>{
  if(document.hidden){window.androidFlush();}
  else{clientState().then(()=>models());}
});
