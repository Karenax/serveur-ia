/* Presentation layer: progressive disclosure around the existing, authenticated actions. */
'use strict';
function uiLoadedModel(name,code=''){
  const label=$('loaded-model');
  label.textContent=name?'Modèle chargé : '+name:['model_unloaded','no_models'].includes(code)?'Aucun modèle chargé':'Modèle : connexion requise';
  label.title=label.textContent;
}
const uiPaths={chat:'M3 4h18v12H8l-5 4V4',projects:'M3 7V5h6l2 2h10v13H3V7',tasks:'M9 3h6v3H9V3m-3 2H4v16h16V5h-2M8 11l2 2 5-5M8 17h8',settings:'M4 6h16M4 12h16M4 18h16M8 3v6m8 0v6m-6 0v6',new:'M15 4l5 5M4 20l4-1L21 6l-3-3L5 16l-1 4',sidebar:'M3 4h18v16H3V4m5 0v16',project:'M3 7V5h6l2 2h10v13H3V7',writing:'M4 20l4-1L21 6l-3-3L5 16l-1 4',code:'M8 6l-6 6 6 6m8-12 6 6-6 6m-3-14-2 16',analysis:'M4 20h16M7 16v-5m5 5V4m5 12V8',research:'M15 15l6 6M17 9a8 8 0 1 1-16 0 8 8 0 0 1 16 0',general:'M12 3v18M3 12h18M5.6 5.6l12.8 12.8m0-12.8L5.6 18.4'};
function uiIcon(name){const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('fill','none');svg.setAttribute('stroke','currentColor');svg.setAttribute('stroke-width','1.5');svg.setAttribute('stroke-linecap','round');svg.setAttribute('stroke-linejoin','round');svg.setAttribute('aria-hidden','true');svg.classList.add('icon');const path=document.createElementNS(svg.namespaceURI,'path');path.setAttribute('d',uiPaths[name]||uiPaths.general);svg.append(path);return svg;}
const uiNavTitles={chat:'Conversations',projects:'Projets',tasks:'Tâches',settings:'Réglages'};
function uiDecorateNavigation(){for(const b of document.querySelectorAll('.nav-button')){const name=b.dataset.viewButton;if(!uiNavTitles[name])continue;const notification=name==='tasks'&&(b.textContent.includes('résultats disponibles')||b.dataset.unread==='true');if(name==='tasks')b.dataset.unread=String(notification);b.replaceChildren(uiIcon(name),wsElement('span',uiNavTitles[name],'nav-text'));if(notification){b.append(wsElement('span',undefined,'nav-dot'));b.title='Tâches · nouveaux résultats';}else b.title=uiNavTitles[name];}}
$('new').prepend(uiIcon('new'));$('ui-sidebar-toggle').append(uiIcon('sidebar'));
document.querySelector('.sidebar-settings').append(document.querySelector('[data-view-button="settings"]'));
$('workspace-heading').after($('undo-delete'));
document.querySelector('[data-view="access"] .settings-card:last-child').append(document.querySelector('.sidebar-tools'));
wsSettingsNav.classList.add('settings-subnav');
function uiSyncSidebar(){const mobile=matchMedia('(max-width:850px)').matches;document.querySelector('.sidebar').inert=mobile&&!document.body.classList.contains('sidebar-open');$('ui-sidebar-toggle').setAttribute('aria-expanded',String(mobile?document.body.classList.contains('sidebar-open'):!document.body.classList.contains('sidebar-collapsed')));}
function uiToggleSidebar(){document.body.classList.toggle(matchMedia('(max-width:850px)').matches?'sidebar-open':'sidebar-collapsed');uiSyncSidebar();}
$('ui-sidebar-toggle').onclick=uiToggleSidebar;document.querySelector('.sidebar-backdrop').onclick=()=>{document.body.classList.remove('sidebar-open');uiSyncSidebar();};matchMedia('(max-width:850px)').addEventListener('change',uiSyncSidebar);uiSyncSidebar();
const uiThemeCard=wsElement('div',undefined,'settings-card');uiThemeCard.append(wsElement('h3','Apparence'));const uiThemeRow=wsElement('div',undefined,'theme-row');const uiThemeLabel=wsElement('label','Thème de l’interface');uiThemeLabel.htmlFor='ui-theme';const uiThemeSelect=wsElement('select');uiThemeSelect.id='ui-theme';uiThemeSelect.append(new Option('Clair','light'),new Option('Sombre','dark'),new Option('Comme Windows','system'));uiThemeRow.append(uiThemeLabel,uiThemeSelect);uiThemeCard.append(uiThemeRow);document.querySelector('[data-view="access"]').prepend(uiThemeCard);
let uiTheme='light';try{uiTheme=localStorage.getItem('fred-theme')||'light';}catch{}if(!['light','dark','system'].includes(uiTheme))uiTheme='light';
function uiSetTheme(value){uiTheme=value;uiThemeSelect.value=value;document.documentElement.dataset.theme=value==='system'?(matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light'):value;try{localStorage.setItem('fred-theme',value);}catch{}}
uiSetTheme(uiTheme);uiThemeSelect.onchange=()=>uiSetTheme(uiThemeSelect.value);matchMedia('(prefers-color-scheme:dark)').addEventListener('change',()=>{if(uiTheme==='system')uiSetTheme('system');});

const uiFonts={system:{label:'Moderne · Segoe UI',css:"'Segoe UI',system-ui,sans-serif"},humanist:{label:'Classique · Arial',css:'Arial,Helvetica,sans-serif'},serif:{label:'Lecture · Georgia',css:'Georgia,Cambria,serif'},mono:{label:'Technique · Consolas',css:"Consolas,'Cascadia Code',monospace"}};
const uiReadingSizes={compact:{label:'Compact · 14 px',css:'14px'},standard:{label:'Standard · 15 px',css:'15px'},large:{label:'Grand · 17 px',css:'17px'},extra:{label:'Très grand · 19 px',css:'19px'}};
function uiReadingSetting(id,label,options){const row=wsElement('div',undefined,'theme-row'),l=wsElement('label',label),select=wsElement('select');l.htmlFor=id;select.id=id;for(const [key,value] of Object.entries(options))select.append(new Option(value.label,key));row.append(l,select);uiThemeCard.append(row);return select;}
const uiFontSelect=uiReadingSetting('ui-font','Police des conversations',uiFonts),uiSizeSelect=uiReadingSetting('ui-text-size','Taille du texte',uiReadingSizes);
const uiFontPreview=wsElement('p','Une réponse claire, agréable à lire.','reading-preview');uiThemeCard.append(uiFontPreview,wsElement('small','Les changements s’appliquent immédiatement aux conversations et au correcteur.'));
const uiReadingStatus=wsElement('small');uiReadingStatus.id='ui-reading-status';uiReadingStatus.setAttribute('role','status');uiThemeCard.append(uiReadingStatus);
function uiSetReading(font,size){font=Object.hasOwn(uiFonts,font)?font:'system';size=Object.hasOwn(uiReadingSizes,size)?size:'standard';uiFontSelect.value=font;uiSizeSelect.value=size;document.documentElement.style.setProperty('--reading-font',uiFonts[font].css);document.documentElement.style.setProperty('--reading-size',uiReadingSizes[size].css);uiReadingStatus.textContent='Appliqué : '+uiFonts[font].label+' · '+uiReadingSizes[size].label;try{localStorage.setItem('fred-reading-font',font);localStorage.setItem('fred-reading-size',size);}catch{}}
let uiSavedFont='system',uiSavedSize='standard';try{uiSavedFont=localStorage.getItem('fred-reading-font')||uiSavedFont;uiSavedSize=localStorage.getItem('fred-reading-size')||uiSavedSize;}catch{}
uiSetReading(uiSavedFont,uiSavedSize);
for(const control of [uiFontSelect,uiSizeSelect]){
  control.addEventListener('input',()=>uiSetReading(uiFontSelect.value,uiSizeSelect.value));
  control.addEventListener('change',()=>{
    uiSetReading(uiFontSelect.value,uiSizeSelect.value);
    const font=uiFontSelect.value,size=uiSizeSelect.value;
    uiReadingStatus.textContent+=' · Enregistrement…';
    uiPersistPreferences().then(()=>{if(uiFontSelect.value===font&&uiSizeSelect.value===size)uiReadingStatus.textContent='Appliqué et enregistré : '+uiFonts[font].label+' · '+uiReadingSizes[size].label;}).catch(e=>{uiReadingStatus.textContent='Appliqué sur ce poste · enregistrement à réessayer.';error(e);});
  });
}

let uiPreferencesPending=0,uiPreferencesWrites=Promise.resolve(),uiPreferencesLoaded=false;
function uiPersistPreferences(){
  uiPreferencesLoaded=true;
  const values={theme:uiTheme,font:uiFontSelect.value,text_size:uiSizeSelect.value,thinking_effort:thinkingEffort(),thinking:thinkingEffort()!=='none',sidebar_collapsed:document.body.classList.contains('sidebar-collapsed'),corrector_text:$('corrector-text')?.value||''};
  uiPreferencesPending++;
  uiPreferencesWrites=uiPreferencesWrites.catch(()=>{}).then(()=>api('/client/preferences',values)).then(result=>{if(typeof correctorDirty!=='undefined'&&$('corrector-text')?.value===values.corrector_text)correctorDirty=false;return result;}).finally(()=>uiPreferencesPending--);
  return uiPreferencesWrites;
}
function uiApplyPreferences(values){
  if(uiPreferencesLoaded||uiPreferencesPending||!values)return;
  uiPreferencesLoaded=true;
  if(values.theme)uiSetTheme(values.theme);
  uiSetReading(values.font||uiFontSelect.value,values.text_size||uiSizeSelect.value);
  if(!busy){uiThinkingSet(values.thinking_effort||(values.thinking?'high':'none'));}
  if(typeof values.corrector_text==='string'&&$('corrector-text')&&!correctorDirty&&document.activeElement!==$('corrector-text'))$('corrector-text').value=values.corrector_text;
  if(typeof values.sidebar_collapsed==='boolean'){document.body.classList.toggle('sidebar-collapsed',values.sidebar_collapsed);uiSyncSidebar();}
}
uiThemeSelect.addEventListener('change',()=>uiPersistPreferences().catch(e=>error(e)));
$('ui-sidebar-toggle').addEventListener('click',()=>uiPersistPreferences().catch(e=>error(e)));

const uiSendRow=document.querySelector('.send-row');uiSendRow.prepend(pickers);
const uiDocumentControls=wsElement('div');uiDocumentControls.hidden=true;uiDocumentControls.append($('ws-chat-document').parentElement,$('ws-publish'),$('ws-panel'));document.querySelector('.composer').append(uiDocumentControls);
uiSendRow.insertBefore($('thinking'),uiSendRow.querySelector('.hint'));
const uiSourceButton=wsElement('button','Sources','context-details');uiSourceButton.type='button';uiSourceButton.hidden=true;pickers.append(uiSourceButton);const uiOriginalSources=workspaceShowSources;workspaceShowSources=function(sources){ws.lastSources=sources;uiSourceButton.hidden=!sources.length;uiSourceButton.textContent='Sources · '+sources.length;};uiSourceButton.onclick=()=>uiOriginalSources(ws.lastSources||[]);
let uiConversation=null;
const uiRender=render;render=function(){uiRender();document.querySelector('.chat-view').classList.toggle('is-empty',!messages.length);if(uiConversation!==currentId){uiSourceButton.hidden=true;$('ws-side').hidden=true;uiConversation=currentId;}uiDecorateNavigation();};
const uiDrawLibrary=drawLibrary;drawLibrary=function(){uiDrawLibrary();document.querySelector('.chat-view').classList.toggle('is-empty',!messages.length);};
const uiShowView=showView;showView=function(name){uiShowView(name);uiDecorateNavigation();document.body.classList.remove('sidebar-open');uiSyncSidebar();if(name==='api')uiRefreshIntegrations();};
$('prompt').addEventListener('input',()=>{const field=$('prompt');field.style.height='auto';field.style.height=Math.min(180,Math.max(74,field.scrollHeight))+'px';});
$('conversation-title').addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();$('rename-conversation').click();e.target.blur();}});$('conversation-title').addEventListener('change',()=>$('rename-conversation').click());
document.addEventListener('click',e=>{for(const menu of document.querySelectorAll('.menu[open]')){if(!menu.contains(e.target)||e.target.closest('.menu-body button'))menu.open=false;}});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){for(const d of document.querySelectorAll('.menu[open],.composer-options[open]'))d.open=false;document.body.classList.remove('sidebar-open');uiSyncSidebar();$('ws-side').hidden=true;}if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='b'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName)){e.preventDefault();uiToggleSidebar();}});

function uiProjectTab(name){for(const pane of document.querySelectorAll('[data-project-pane]'))pane.hidden=pane.dataset.projectPane!==name;for(const b of document.querySelectorAll('[data-project-tab]')){const selected=b.dataset.projectTab===name;b.classList.toggle('active',selected);b.setAttribute('aria-selected',String(selected));}}
document.querySelector('.project-tabs').after($('ws-project-status'));
for(const b of document.querySelectorAll('[data-project-tab]'))b.onclick=()=>uiProjectTab(b.dataset.projectTab);
$('ui-project-create').onclick=()=>{$('ws-create-project').hidden=!$('ws-create-project').hidden;if(!$('ws-create-project').hidden)$('ws-project-name').focus();};
const uiFillProject=wsFillProject;wsFillProject=function(){uiFillProject();const p=ws.data?.projects.find(p=>p.id===ws.project);$('ui-project-title').textContent=p?.title||'Votre projet';$('ui-document-empty').hidden=!!ws.document;for(const b of $('ws-documents').querySelectorAll('button'))b.classList.toggle('selected',b.textContent===ws.document?.title);};
const uiSelectProject=wsSelectProject;wsSelectProject=async function(id){await uiSelectProject(id);$('ws-create-project').hidden=true;uiProjectTab('documents');$('ui-document-empty').hidden=false;};
const uiOpenDocument=wsOpenDocument;wsOpenDocument=async function(id){await uiOpenDocument(id);$('ui-document-empty').hidden=true;uiProjectTab('documents');for(const b of $('ws-documents').querySelectorAll('button'))b.classList.toggle('selected',b.textContent===$('ws-document-title').value);};
$('ui-upload-label').onkeydown=e=>{if(['Enter',' '].includes(e.key)){e.preventDefault();$('ws-upload').click();}};

let uiJobFilter='all';function uiFilterJobs(){let visible=0;[...$('ws-jobs').children].forEach((card,i)=>{const j=ws.data.jobs[i];const groups={all:true,active:['queued','running'].includes(j.state),completed:j.state==='completed',attention:['failed','paused','cancelled'].includes(j.state)};card.hidden=!groups[uiJobFilter];if(!card.hidden)visible++;});$('ui-jobs-empty').hidden=visible>0;for(const b of document.querySelectorAll('[data-job-filter]'))b.classList.toggle('active',b.dataset.jobFilter===uiJobFilter);}
for(const b of document.querySelectorAll('[data-job-filter]'))b.onclick=()=>{uiJobFilter=b.dataset.jobFilter;uiFilterJobs();};
const uiDrawJobs=wsDrawJobs;wsDrawJobs=function(){uiDrawJobs();uiFilterJobs();};
const uiOpenJob=wsOpenJob;wsOpenJob=async function(id){await uiOpenJob(id);document.querySelector('[data-view-button="tasks"]').dataset.unread='false';uiDecorateNavigation();};
$('ws-task-kind').addEventListener('change',()=>{$('ui-task-web').hidden=$('ws-task-kind').value!=='web';});
const uiRefresh=wsRefresh;wsRefresh=async function(){await uiRefresh();uiDecorateNavigation();};
uiDecorateNavigation();render();uiProjectTab('documents');

let uiLastConnection={},uiIntegrations=null,uiIntegrationsLoading=false,uiIntegrationPending=false;
function uiIntegrationButtons(){
  const model=uiLastConnection.connected?(uiLastConnection.model||config.model):'';
  $('integration-model').textContent=model?'Modèle à ajouter : '+model:'Connectez le client au serveur et chargez un modèle pour l’ajouter.';
  for(const name of ['opencode','hermes']){
    const app=uiIntegrations?.[name],button=$('integration-'+name);
    button.disabled=uiIntegrationPending||uiIntegrationsLoading||!app?.installed||!model;
    $('integration-'+name+'-state').textContent=uiIntegrationsLoading?'Détection en cours…':app?(app.installed?'Détecté sur ce PC':'Non détecté sur ce PC'):'Détection indisponible';
  }
}
async function uiRefreshIntegrations(){
  if(uiIntegrationsLoading||uiIntegrationPending)return;
  uiIntegrationsLoading=true;uiIntegrationButtons();
  try{uiIntegrations=(await api('/client/integrations')).apps;}
  catch(e){uiIntegrations=null;$('integration-result').textContent=e.message;}
  finally{uiIntegrationsLoading=false;uiIntegrationButtons();}
}
for(const name of ['opencode','hermes'])$('integration-'+name).onclick=async()=>{
  if(uiIntegrationPending)return;
  uiIntegrationPending=true;uiIntegrationButtons();$('integration-backup').hidden=true;$('integration-result').textContent='Ajout du modèle en cours…';
  try{
    const result=await api('/client/integrations/apply',{app:name,model:uiLastConnection.model||config.model});
    $('integration-result').textContent=result.message;
    if(result.backup){$('integration-backup-path').textContent=result.backup;$('integration-backup').hidden=false;}
  }catch(e){$('integration-result').textContent=e.message;}
  finally{uiIntegrationPending=false;uiIntegrationButtons();}
};
const uiConnectionPhases={requesting:'Envoi de la demande',queued:'En attente du moteur',waiting_model:'Calcul en cours',thinking:'Réflexion en cours',answering:'Rédaction de la réponse',complete:'Réponse terminée',interrupted:'Réponse interrompue'};
const uiConnectionEvents={endpoint_selected:'Adresse sélectionnée',wireguard_started:'Nouveau tunnel WireGuard',connection_probe:'Vérification de connexion',connection_failed:'Échec de connexion',server_response:'Réponse du serveur',generation_complete:'Génération terminée',generation_interrupted:'Flux interrompu'};
function uiConnectionStatus(state=uiLastConnection){
  uiLastConnection=state;const phase=busy?(replyProgress.phase||state.stream?.phase||'requesting'):null;
  uiIntegrationButtons();
  uiLoadedModel(state.connected?(state.model||config.model):'',state.code);
  const https=state.transport==='https';
  let label=phase?uiConnectionPhases[phase]:state.checking?(https?'Vérification HTTPS':'Vérification WireGuard'):connected?'Connecté au serveur IA':'Connexion indisponible';
  const elapsed=busy?Math.max(0,Math.round((Date.now()-(replyProgress.started||Date.now()))/1000)):0;
  const silence=busy?Math.max(0,Math.round((Date.now()-(replyProgress.lastEvent||Date.now()))/1000)):0;
  if(busy)label+=' · '+elapsed+' s';if(busy&&silence>=45)label='Flux silencieux · '+silence+' s';
  $('connection').textContent='● '+label+' ⌄';$('connection').classList.toggle('online',connected&&!state.checking&&silence<45);
  $('connection-summary').textContent=busy&&silence>=45?'Aucun nouveau texte reçu. Le moteur peut encore calculer ; les compteurs ci-dessous permettent de vérifier le tunnel.':state.checking?'Le client vérifie le serveur et essaie les adresses disponibles.':state.error||label;
  const lines=['Adresse active : '+(state.endpoint||'en cours'), 'Mode : '+(state.automatic?'automatique':'adresse manuelle'), 'Handshakes : '+(state.handshake?'un échange authentifié a été reçu':'aucun reçu'), 'Dernier handshake : '+(state.last_handshake_time_sec?new Date(state.last_handshake_time_sec*1000).toLocaleString():'aucun'), 'Reçu / envoyé : '+(state.rx_bytes||0)+' / '+(state.tx_bytes||0)+' octets', 'Dernière réponse HTTP : '+(state.last_contact?new Date(state.last_contact*1000).toLocaleTimeString():'aucune'), 'Tunnels démarrés : '+(state.bridge_starts||0)+' · vérifications : '+(state.attempts||0), 'État : '+(state.code||'connexion')];
  if(state.stream?.started)lines.push('Dernière génération : '+(uiConnectionPhases[state.stream.phase]||state.stream.phase),'Réflexion / réponse : '+(state.stream.reasoning_chars||0)+' / '+(state.stream.answer_chars||0)+' caractères reçus');
  lines.push('','Événements récents :');for(const e of (state.events||[]).slice(-6))lines.push(new Date(e.time*1000).toLocaleTimeString()+' · '+(uiConnectionEvents[e.event]||e.event)+(e.route?' · '+e.route:'')+(e.code?' · '+e.code:'')+(e.status?' · HTTP '+e.status:''));
  if(https){lines.splice(2,3);lines[1]='Mode : HTTPS Cloudflare';const i=lines.findIndex(line=>line.startsWith('Tunnels démarrés'));lines[i]='Vérifications HTTPS : '+(state.attempts||0);}
  $('connection-panel-text').textContent=lines.join('\n');$('connection-retry').disabled=busy||!!modelsPending;
  if(busy)$('queue-state').textContent=label;
}
$('connection').onclick=()=>{const panel=$('connection-panel');panel.hidden=!panel.hidden;$('connection').setAttribute('aria-expanded',String(!panel.hidden));uiConnectionStatus();};
$('connection-close').onclick=()=>{$('connection-panel').hidden=true;$('connection').setAttribute('aria-expanded','false');};
$('connection-retry').onclick=()=>{$('reconnect').click();};
let uiWireGuardEndpoint='';
function uiSetConnectionMode(https){
  $('connection-mode').value=https?'https':'wireguard';
  $('endpoint').readOnly=https;
  $('automatic').disabled=busy||https;
}
$('connection-mode').onchange=()=>{
  if(busy)return;
  const https=$('connection-mode').value==='https';
  $('endpoint').value=https?'https://ia.karenax.net':uiWireGuardEndpoint;
  endpointDirty=true;uiSetConnectionMode(https);
  $('connection-transfer-status').textContent='Cliquez Appliquer la connexion pour utiliser ce mode.';
};
function uiConnectionSettings(state){
  uiWireGuardEndpoint=state.internet_endpoint||uiWireGuardEndpoint;
  if(!endpointDirty)uiSetConnectionMode(state.connection?.transport==='https');
  $('connection-mode').disabled=busy;
  for(const id of ['connection-copy','connection-paste','connection-use-parameters'])$(id).disabled=busy;
}
function uiReadConnectionParameters(text){
  if(typeof text!=='string'||text.length>2048)throw new Error('Paramètres de connexion limités à 2 048 caractères.');
  let value=text.trim();
  if(value.startsWith('{')){
    let settings;try{settings=JSON.parse(value);}catch{throw new Error('Paramètres de connexion JSON illisibles.');}
    if(!settings||Object.keys(settings).sort().join(',')!=='endpoint,format,protocol,version'||settings.format!=='acces-serveur-fred-connection'||settings.version!==1||!['UDP','HTTPS'].includes(settings.protocol)||typeof settings.endpoint!=='string')throw new Error('Paramètres de connexion incompatibles.');
    value=settings.endpoint.trim();
    if((/^https:\/\//i.test(value)?'HTTPS':'UDP')!==settings.protocol)throw new Error('Le protocole ne correspond pas à l’adresse.');
  }else value=value.replace(/\s*\/\s*UDP\s*$/i,'').trim();
  if(!value||value.length>300)throw new Error('Adresse attendue : IP-ou-DNS:port.');
  if(/^https:\/\//i.test(value)){
    if(value.toLowerCase().replace(/\/+$/,'')!=='https://ia.karenax.net')throw new Error('L’accès HTTPS autorisé est https://ia.karenax.net.');
    return 'https://ia.karenax.net';
  }
  return value;
}
function uiUseConnectionParameters(text){
  if(busy)throw new Error('Attendez la fin de la réponse avant de changer la connexion.');
  $('endpoint').value=uiReadConnectionParameters(text);endpointDirty=true;
  uiSetConnectionMode($('endpoint').value==='https://ia.karenax.net');
  $('connection-transfer-status').textContent='Adresse prête. Cliquez Appliquer l’adresse pour vous connecter.';
}
$('connection-copy').onclick=()=>wsTry(async()=>{
  const state=await api('/client/state');uiConnectionSettings(state);
  const endpoint=uiReadConnectionParameters(endpointDirty?$('endpoint').value:state.connection?.automatic?state.internet_endpoint:state.endpoint);
  const text=JSON.stringify({format:'acces-serveur-fred-connection',version:1,protocol:endpoint.startsWith('https://')?'HTTPS':'UDP',endpoint},null,2);
  $('connection-parameters').value=text;
  try{await copyText(text);$('connection-transfer-status').textContent='Paramètres copiés. Collez-les dans le client distant.';}
  catch{$('connection-parameters').focus();$('connection-parameters').select();$('connection-transfer-status').textContent='Paramètres sélectionnés. Appuyez sur Ctrl+C pour les copier.';}
});
$('connection-paste').onclick=()=>wsTry(async()=>{
  try{const text=await navigator.clipboard.readText();$('connection-parameters').value=text;uiUseConnectionParameters(text);}
  catch(e){if(e.name!=='NotAllowedError')throw e;$('connection-parameters').focus();$('connection-transfer-status').textContent='Collez avec Ctrl+V dans la zone ci-dessus, puis cliquez Utiliser ces paramètres.';}
});
$('connection-use-parameters').onclick=()=>wsTry(()=>uiUseConnectionParameters($('connection-parameters').value));
$('endpoint').addEventListener('paste',e=>{const text=e.clipboardData?.getData('text/plain');if(!text)return;try{const endpoint=uiReadConnectionParameters(text);e.preventDefault();uiUseConnectionParameters(endpoint);}catch(err){e.preventDefault();error(err);}});
setInterval(()=>{if(busy)uiConnectionStatus();},1000);

// Follow streamed output only while the reader remains at the bottom.
const chatScrollPane=$('messages'),chatLatestButton=wsElement('button','↓ Revenir à la réponse','chat-latest');
chatLatestButton.type='button';chatLatestButton.hidden=true;
chatLatestButton.setAttribute('aria-label','Revenir à la réponse en cours');
document.querySelector('.chat-view').append(chatLatestButton);
chatScrollPane.tabIndex=0;
let chatFollowing=true,chatReadingTop=chatScrollPane.scrollTop,chatScrollFrame=0,chatScrollConversation=currentId;
function chatScrollChanged(){
 if(chatScrollFrame)return;
 chatScrollFrame=requestAnimationFrame(()=>{
  chatScrollFrame=0;
  if(chatFollowing)chatScrollPane.scrollTop=chatScrollPane.scrollHeight;
  else chatScrollPane.scrollTop=chatReadingTop;
  chatReadingTop=chatScrollPane.scrollTop;
  chatLatestButton.hidden=chatFollowing||chatScrollPane.scrollHeight-chatScrollPane.scrollTop-chatScrollPane.clientHeight<=2;
  chatLatestButton.style.bottom=(document.querySelector('.composer').offsetHeight+12)+'px';
 });
}
function chatScrollLatest(){chatFollowing=true;chatScrollChanged();}
function chatPauseFollowing(){chatFollowing=false;chatReadingTop=chatScrollPane.scrollTop;chatScrollChanged();}
chatLatestButton.onclick=chatScrollLatest;
chatScrollPane.addEventListener('scroll',()=>{
 chatReadingTop=chatScrollPane.scrollTop;
 chatFollowing=chatScrollPane.scrollHeight-chatReadingTop-chatScrollPane.clientHeight<=2;
 chatLatestButton.hidden=chatFollowing;
},{passive:true});
chatScrollPane.addEventListener('wheel',event=>{if(event.deltaY<0)chatPauseFollowing();},{passive:true});
chatScrollPane.addEventListener('keydown',event=>{if(['ArrowUp','PageUp','Home'].includes(event.key)||(event.key===' '&&event.shiftKey))chatPauseFollowing();});
let chatTouchY=null;
chatScrollPane.addEventListener('touchstart',event=>{chatTouchY=event.touches[0]?.clientY??null;},{passive:true});
chatScrollPane.addEventListener('touchmove',event=>{const y=event.touches[0]?.clientY;if(chatTouchY!==null&&y>chatTouchY)chatPauseFollowing();chatTouchY=y??null;},{passive:true});
chatScrollPane.addEventListener('pointerdown',event=>{const box=chatScrollPane.getBoundingClientRect();if(event.clientX>=box.left+chatScrollPane.clientWidth)chatPauseFollowing();});
new MutationObserver(chatScrollChanged).observe(chatScrollPane,{childList:true,subtree:true,characterData:true,attributes:true});
const chatScrollResize=new ResizeObserver(chatScrollChanged);chatScrollResize.observe(chatScrollPane);chatScrollResize.observe(document.querySelector('.composer'));
chatScrollPane.addEventListener('load',chatScrollChanged,true);
const chatScrollRender=render;render=function(){
 const sameConversation=chatScrollConversation===currentId,top=chatScrollPane.scrollTop,following=chatFollowing;
 chatScrollRender();chatScrollConversation=currentId;
 chatFollowing=sameConversation?following:true;chatReadingTop=sameConversation?top:0;
 if(sameConversation&&!following)chatScrollPane.scrollTop=top;
 chatScrollChanged();
};
chatScrollChanged();
