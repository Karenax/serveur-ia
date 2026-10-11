'use strict';
const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="launcher-token"]').content;
let settings = {}, liveState = {}, dirty = false, polling = false, actionBusy = false;
let remoteBusy = false;
let remoteDirty = false;
const definitions = {
  'compute-fields': [
    ['context','Contexte maximal','number','Tokens du prompt et de la réponse. Maximum du modèle : 262 144.',512,262144],
    ['workers','Travailleurs CPU','number','15 travailleurs + le thread principal = 16 cœurs. Au-delà de 15, le gain SMT reste à mesurer.',1,31],
    ['prefill','Bloc de traitement du prompt','select','Des blocs plus grands demandent davantage de VRAM.',[[256,'256 tokens · profil actuel'],[512,'512 tokens'],[1024,'1 024 tokens'],[2048,'2 048 tokens'],[4096,'4 096 tokens'],[8192,'8 192 tokens']]],
    ['vram_reserve','Réserve VRAM par GPU','number','En Mo. Préserve de la place pour les buffers ; réduit le nombre d’experts en VRAM.',512,8192],
  ],
  'history-fields': [
    ['history_enabled','Réutiliser l’historique','toggle','Évite de relire les parties identiques d’une conversation.'],
    ['history_slots','Points de sauvegarde','number','Environ 118 Mo de RAM par point ; six correspondent au réglage par défaut de Strata.',1,24],
    ['history_every','Sauvegarde tous les… tokens','number','16 384 par défaut. 0 désactive les points intermédiaires.',0,262144],
    ['mtp_enabled','Accélération MTP','toggle','Le modèle propose des tokens, puis vérifie leur validité.'],
    ['spec','Taille des fenêtres MTP','number','3 correspond à la configuration validée.',2,8],
    ['spec_min_p','Seuil des propositions MTP','number','Valeur entre 0 et 1. Réglage actuel : 0,5.',0,1,.05],
  ],
  'advanced-fields': [
    ['layer_split','Première couche du GPU 2','number','24 répartit les 48 couches en deux moitiés.',1,47],
    ['expert_cache','Cache d’experts GPU','text','auto adapte le cache à la VRAM disponible. Une valeur numérique fixe le cache du GPU principal.'],
    ['short_read','Lecture courte via la génération','number','0 utilise toujours le traitement par blocs. Sinon, seuil de nouveaux tokens.',0,256],
    ['min_free_ram_gib','Marge RAM pendant le chargement','number','Le lanceur arrête un nouveau chargement si la RAM disponible reste sous ce seuil pendant 8 secondes.',2,32,.5],
    ['gpus','GPU visibles, dans leur ordre','text','Deux indices ou UUID NVIDIA séparés par une virgule. Le profil par défaut utilise uniquement les deux P100.'],
  ],
  'network-fields': [
    ['host','Adresse d’écoute','text','127.0.0.1 : ce PC. 0.0.0.0 : toutes les interfaces IPv4.'],
    ['port','Port du serveur LLM','number','8080 par défaut. Le lanceur local utilise le port 8765.',1,65535],
    ['api_key','Clé API','password','Obligatoire pour une écoute réseau. Stockée dans les fichiers de configuration locaux.'],
    ['model_name','Nom du modèle dans l’API','text','À indiquer dans votre application cliente.'],
  ],
  'origin-fields': [
    ['cors_origins','Origines autorisées pour les clients web','textarea','Une origine par ligne, par exemple http://192.168.1.20:3000. Vide : aucun accès web entre origines.'],
    ['trusted_origins','Origines de confiance pour le chat','textarea','Pour le chat derrière un proxy : origines autorisées à utiliser les réglages et les outils Strata.'],
  ],
  'file-fields': [
    ['pack','Pack Strata','text','Par défaut : q4-local sur D:.'],
    ['native','Premier GGUF du modèle complet','text','Les autres shards restent dans le même dossier.'],
    ['tokenizer','Dossier du tokenizer','text','Doit contenir vocab.json.'],
    ['expert_profile','Profil des experts','text','Profil de fréquence utilisé pour remplir la VRAM.'],
    ['mtp_path','Pack MTP','text','Utilisé lorsque l’accélération MTP est activée.'],
    ['exe','Moteur Strata','text','Binaire CUDA adapté aux Tesla P100.'],
  ],
};
const flat = Object.values(definitions).flat();
function drawFields(){
  for(const [group, fields] of Object.entries(definitions)){
    for(const [name,label,type,help,min,max,step] of fields){
      const wrap=document.createElement('div');wrap.className='field'+(type==='toggle'?' toggle':'');
      const content=document.createElement('div');
      const lab=document.createElement('label');lab.htmlFor=name;lab.textContent=label;content.append(lab);
      const hint=document.createElement('small');hint.id=name+'-help';hint.textContent=help;
      let input;
      if(type==='toggle'){
        content.append(hint);wrap.append(content);
        const box=document.createElement('div');box.className='switch';
        input=document.createElement('input');input.type='checkbox';box.append(input,document.createElement('span'));wrap.append(box);
      }else{
        input=document.createElement(type==='select'?'select':type==='textarea'?'textarea':'input');
        if(type==='select')for(const [value,text]of min){const option=document.createElement('option');option.value=value;option.textContent=text;input.append(option);}
        else if(type!=='textarea'){input.type=type;if(type==='number'){input.min=min;input.max=max;input.step=step||1;}}
        content.append(input,hint);wrap.append(content);
      }
      input.id=name;input.setAttribute('aria-describedby',hint.id);input.autocomplete='off';
      input.addEventListener('input',()=>{dirty=true;$('save-state').textContent='Modifications à enregistrer';updatePreview();});
      $(group).append(wrap);
    }
  }
}
function applySettings(value){settings=value;for(const [name,,type]of flat){if(type==='toggle')$(name).checked=!!value[name];else $(name).value=value[name]??'';}dirty=false;updatePreview();$('save-state').textContent='Réglages enregistrés pour le prochain lancement';}
function form(){const data={...settings};for(const [name,,type]of flat)data[name]=type==='toggle'?$(name).checked:type==='number'?Number($(name).value):$(name).value;return data;}
function number(value){return Number(value).toLocaleString('fr-FR');}
function showDefaults(value){$('default-profile').textContent=`${value.workers+1} threads · ${number(value.context)} tokens\n${value.mtp_enabled?'MTP activé':'MTP désactivé'} · ${value.history_enabled?'historique réutilisé':'historique relu'}`;}
function updatePreview(){
  const s=form();$('context-value').replaceChildren(document.createTextNode(number(s.context)+' '));const unit=document.createElement('em');unit.textContent='tokens';$('context-value').append(unit);
  $('profile-detail').textContent=`${s.workers+1} threads de calcul · ${s.mtp_enabled?'MTP actif':'MTP désactivé'} · ${s.history_enabled?'historique réutilisé':'historique relu'}`;
  $('history_slots').disabled=!s.history_enabled;$('history_every').disabled=!s.history_enabled;$('spec').disabled=!s.mtp_enabled;$('spec_min_p').disabled=!s.mtp_enabled;
  const host=s.host==='0.0.0.0'?(liveState.lan_ips?.[0]||'ADRESSE_DU_PC'):s.host;
  $('api-address').value=`http://${host}:${s.port}/v1`;$('model-alias').textContent=liveState.health?.model||s.model_name;
  $('network-addresses').textContent=s.host==='0.0.0.0'?(liveState.lan_ips||[]).map(ip=>`http://${ip}:${s.port}/v1`).join('\n'):'Accès limité à ce PC.';
  if(liveState.running && liveState.active){
    const a=liveState.active;const pending=a.context!==s.context||a.workers!==s.workers||a.history!==(s.history_enabled?s.history_slots:0)||a.mtp!==s.mtp_enabled||a.host!==s.host||a.port!==s.port;
    $('notice').textContent=pending?'Des réglages diffèrent du serveur actif. Ils seront appliqués au prochain lancement.':'Le serveur fonctionne. Enregistrer un réglage ne le redémarre pas.';
    $('notice').classList.toggle('warning',pending);
  }
}
async function request(path,data){
  const options=data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-Launcher-Token':token},body:JSON.stringify(data)};
  const response=await fetch(path,options);const result=await response.json();if(!response.ok)throw new Error(result.error||'La commande a échoué.');return result;
}
let toastTimer;function toast(message,error=false){$('toast').textContent=message;$('toast').className='toast show'+(error?' error':'');clearTimeout(toastTimer);toastTimer=setTimeout(()=>{$('toast').className='toast';},error?10000:4500);}
async function action(work){if(actionBusy)return;actionBusy=true;updateButtons();try{await work();}catch(error){toast(error.message,true);}finally{actionBusy=false;await refresh();}}
function updateButtons(){$('start').disabled=actionBusy||!!liveState.running;$('stop').disabled=actionBusy||!liveState.running;for(const id of ['save','set-default'])$(id).disabled=actionBusy;}
function renderState(s){
  liveState=s;$('queue-status').textContent=`Demandes : ${s.queue?.active||0} active · ${s.queue?.waiting||0} en attente · ${s.queue?.completed||0} terminées · ${s.queue?.tokens_per_second??"—"} tokens/s`;$('ops-status').textContent=`Version ${s.operations?.version||'—'} · ${s.operations?.error||'Surveillance disponible'}`;const names={pret:'Prêt',chargement:'Chargement',validation_cuda:'Validation CUDA',arrete:'Arrêté',erreur:'Erreur'};const name=names[s.status]||s.status;
  $('server-state').textContent=name;$('status-badge').className='badge'+(s.status==='pret'?'':s.status==='erreur'?' error':s.running?' loading':' off');$('status-badge').querySelector('span').textContent=name;
  const duration=s.elapsed_seconds==null?'':`${Math.floor(s.elapsed_seconds/60)} min ${Math.floor(s.elapsed_seconds%60)} s`;
  $('server-description').textContent=s.error||(s.status==='pret'?(s.managed?'Modèle chargé et validation terminée.':'Serveur déjà actif, reconnu par le lanceur.'):s.running?`Le chargement peut être long depuis D:. ${duration}`:'Le modèle est déchargé. Vos réglages sont conservés.');
  $('ram-value').textContent=`${number(s.ram.available_gib)} Go`;$('ram-detail').textContent=`${number(s.ram.total_gib)} Go au total · ${s.ram.percent}% utilisés`;$('ram-meter').style.width=s.ram.percent+'%';$('ram-meter').style.background=s.ram.available_gib<6?'#f2a477':'var(--green)';
  const gpu=s.gpus.filter(g=>g.name.includes('P100'));$('gpu-value').textContent=gpu.length?`${number(gpu.reduce((n,g)=>n+g.used_mib,0)/1024).split(',')[0]} / ${Math.round(gpu.reduce((n,g)=>n+g.total_mib,0)/1024)} Go`:'—';
  $('gpu-lines').replaceChildren(...gpu.map((g,i)=>{const span=document.createElement('span');span.textContent=`P100 ${i+1} · ${g.utilization}% · ${g.temperature??'—'} °C · ${(g.used_mib/1024).toFixed(1)} Go`;return span;}));
  $('active-details').replaceChildren();if(s.running){for(const [label,value]of [['Contexte',number(s.active.context)+' tokens'],['Calcul CPU',`${s.active.workers+1} threads`],['MTP',s.active.mtp?'Activé':'Désactivé'],['Historique',s.active.history?`${s.active.history} sauvegardes`:'Désactivé'],['Écoute',`${s.active.host}:${s.active.port}`]]){const row=document.createElement('div');const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=label;dd.textContent=value;row.append(dt,dd);$('active-details').append(row);}}
  $('disk-stats').replaceChildren(...s.disks.map(d=>{const row=document.createElement('div');const title=document.createElement('span'),data=document.createElement('span');title.textContent=d.name;data.textContent=`↓ ${d.read_mib_s} · ↑ ${d.write_mib_s} Mo/s`;row.append(title,data);return row;}));
  $('open-chat').disabled=s.status!=='pret';const log=$('engine-log'),nearEnd=log.scrollTop+log.clientHeight>=log.scrollHeight-50;log.textContent=s.logs||'Aucun journal disponible.';if(nearEnd)log.scrollTop=log.scrollHeight;
  if(!s.running){$('notice').textContent=s.error||'Le serveur est arrêté. Le lancement utilisera les réglages affichés.';$('notice').classList.toggle('warning',!!s.error);}updatePreview();updateButtons();
}
async function refresh(){if(polling)return;polling=true;try{renderState(await request('/api/state'));}catch(error){$('status-badge').className='badge error';$('status-badge').querySelector('span').textContent='Lanceur indisponible';$('start').disabled=true;$('stop').disabled=true;}finally{polling=false;}}
async function copy(value){try{await navigator.clipboard.writeText(value);toast('Copié dans le presse-papiers.');}catch{toast('Copie indisponible : sélectionnez le texte manuellement.',true);}}
drawFields();
const topics={notifications:['MAINTENANCE','Notifications','Alertes du serveur, lecture et préférences.'],overview:['PILOTAGE','Vue d’ensemble','État du modèle, ressources et demandes en cours.'],launch:['PILOTAGE','Calcul & lancement','Réglez les performances du prochain chargement.'],files:['PILOTAGE','Modèle & fichiers','Choisissez les packs et les fichiers utilisés par le moteur.'],clients:['CLIENTS','Clients & accès','Distribuez les EXE personnels et gérez les autorisations.'],internet:['CLIENTS','Accès distant','Adresse publique, tunnel WireGuard et pare-feu.'],network:['CLIENTS','API & réseau local','Connexion des applications sur ce PC et sur le réseau local.'],updates:['CLIENTS','Mises à jour','Préparez la version signée distribuée aux clients.'],backup:['MAINTENANCE','Sauvegardes','Protégez et restaurez les réglages, accès et clés du serveur.'],exploitation:['MAINTENANCE','Démarrage & surveillance','Démarrage Windows, chargement automatique et reprise après une panne.'],logs:['MAINTENANCE','Journaux & diagnostic','Consultez le moteur ou exportez un diagnostic.']};
function openTopic(id){
  if(!topics[id])id='overview';
  document.querySelectorAll('.tab').forEach(t=>{const selected=t.dataset.tab===id;t.classList.toggle('active',selected);t.setAttribute('aria-selected',String(selected));t.tabIndex=selected?0:-1;});
  document.querySelectorAll('.panel').forEach(p=>{const selected=p.id===id;p.classList.toggle('active',selected);p.hidden=!selected;p.setAttribute('role','tabpanel');p.setAttribute('aria-labelledby','tab-'+p.id);});
  const [category,title,description]=topics[id];$('page-category').textContent=category;$('page-title').textContent=title;$('page-description').textContent=description;
  $('launch-actions').hidden=!['overview','launch','files','network'].includes(id);
  for(const name of ['save','set-default','save-state'])$(name).hidden=id==='overview';
  if(location.hash!=='#'+id)history.replaceState(null,'','#'+id);
}
document.querySelectorAll('.tab').forEach(tab=>{tab.onclick=()=>openTopic(tab.dataset.tab);tab.onkeydown=e=>{if(!['ArrowDown','ArrowUp','Home','End'].includes(e.key))return;e.preventDefault();const tabs=[...document.querySelectorAll('.tab')];let next=e.key==='Home'?0:e.key==='End'?tabs.length-1:(tabs.indexOf(tab)+(e.key==='ArrowDown'?1:-1)+tabs.length)%tabs.length;openTopic(tabs[next].dataset.tab);tabs[next].focus();};});
document.querySelectorAll('[data-open]').forEach(button=>button.onclick=()=>openTopic(button.dataset.open));
window.addEventListener('hashchange',()=>openTopic(location.hash.slice(1)));if(!['spaces','tools','tasks','knowledge','devices','notifications'].includes(location.hash.slice(1)))openTopic(location.hash.slice(1));
let clientsFingerprint='';
function element(tag,text,className){const node=document.createElement(tag);if(text)node.textContent=text;if(className)node.className=className;return node;}
function labelled(label,input,help){const field=element('div',null,'field'),lab=element('label',label);lab.htmlFor=input.id;field.append(lab,input);if(help)field.append(element('small',help));return field;}
function clientStorageInfo(storage){const box=element('div',null,'client-storage');if(!storage)return box;box.append(element('strong','Dossier des données sur le serveur'),element('code',storage.path,'client-storage-path'));const copy=element('button','Copier le chemin','button secondary');copy.type='button';copy.onclick=()=>action(async()=>{await navigator.clipboard.writeText(storage.path);toast('Chemin copié.');});box.append(copy);box.append(element('p',storage.error||(storage.status==='ready'?storage.conversations+' conversation(s) · dossier mis à jour le '+new Date(storage.updated*1000).toLocaleString():'Création du dossier en attente…'),'muted'));return box;}
function renderClients(value,force=false){
  const active=value.clients.filter(c=>!c.revoked);
  $('accounts-summary').textContent=active.length+' accès personnels · '+active.filter(c=>!c.suspended).length+' autorisés';
  $('account-alert').textContent='('+active.length+')';
  $('client-create-help').textContent=$('remote-create').disabled?'Enregistrer le réseau dans Accès distant avant de générer un nouvel EXE.':'Un EXE différent par personne ou PC utilisé simultanément. Téléchargez-le et transmettez-le uniquement à son destinataire. Aucun login requis.';
  const fingerprint=JSON.stringify(value.clients);if(!force&&fingerprint===clientsFingerprint)return;clientsFingerprint=fingerprint;
  $('remote-clients').replaceChildren(...value.clients.map(client=>{
    const card=element('article',null,'client-card'),header=element('div',null,'client-heading');
    const title=element('h3',client.name);
    const state=client.revoked?'Accès révoqué':client.suspended?'Accès suspendu':client.hermes_pending?'Création à reprendre':'Accès autorisé';
    header.append(title,element('span',state,'client-badge'+(client.suspended||client.revoked?' warning':'')));card.append(header);
    card.append(clientStorageInfo(client.storage));
    if(client.hermes){
      const ready=client.hermes.ready&&!client.hermes_pending;
      card.append(element('p',ready?'Assistant Hermes prêt · projets et conversations associés':client.hermes.error||'Assistant Hermes à préparer','muted'));
      if(!ready&&!client.revoked&&!client.suspended){const retry=element('button','Reprendre la création Hermes','button secondary');retry.onclick=()=>remoteAction('/api/remote/hermes-retry',{id:client.id});card.append(retry);}
    }
    const management=element('div',null,'key-row'),rename=element('button','Renommer','button secondary'),remove=element('button','Supprimer','button stop');
    const editor=element('form',null,'client-name-editor'),name=element('input');editor.hidden=true;name.id='name-'+client.id;name.value=client.name;name.maxLength=80;name.required=true;
    editor.append(labelled('Nom du client',name,'Ce nom sera repris dans le nom de l’EXE téléchargé.'));
    const editActions=element('div',null,'key-row'),saveName=element('button','Enregistrer le nom','button primary'),cancelName=element('button','Annuler','button secondary');saveName.type='submit';cancelName.type='button';cancelName.onclick=()=>{editor.hidden=true;};editActions.append(saveName,cancelName);editor.append(editActions);
    rename.onclick=()=>{editor.hidden=!editor.hidden;if(!editor.hidden){name.value=client.name;name.focus();name.select();}};
    editor.onsubmit=async event=>{event.preventDefault();if(editor.reportValidity())await remoteAction('/api/remote/rename',{id:client.id,name:name.value});};
    const deletion=element('div',null,'client-delete');deletion.hidden=true;
    deletion.append(element('p','Supprimer « '+client.name+' » désactivera son EXE et retirera ce client de la liste. Ses conversations et fichiers resteront sur le serveur.','muted'));
    const deleteActions=element('div',null,'key-row'),confirmDelete=element('button','Confirmer la suppression','button stop'),cancelDelete=element('button','Annuler','button secondary');confirmDelete.onclick=()=>remoteAction('/api/remote/delete',{id:client.id});cancelDelete.onclick=()=>{deletion.hidden=true;};deleteActions.append(confirmDelete,cancelDelete);deletion.append(deleteActions);
    remove.onclick=()=>{deletion.hidden=!deletion.hidden;editor.hidden=true;};management.append(rename,remove);card.append(management,editor,deletion);
    card.append(element('p',(client.address?'Adresse privée : '+client.address.replace('/32','')+' · ':'')+(client.expires_epoch?'Expire le '+new Date(client.expires_epoch*1000).toLocaleString():'Accès sans expiration'),'muted'));
    if(client.revoked){card.append(element('p','Cet accès ne peut plus se connecter. Ajoutez un nouveau client pour créer un nouvel accès.','muted'));return card;}
    if(client.hermes_pending)return card;
    const downloadRow=element('div',null,'client-download');const link=element('a','Télécharger l’EXE personnel','button primary');link.href='/api/remote/client/'+client.id;downloadRow.append(link,element('small','Connexion automatique avec cet EXE. Conservez-le comme une clé d’accès personnelle.'));card.append(downloadRow);
    const policy=element('details',null,'client-policy');policy.append(element('summary','Limites et suspension de l’accès'));
    const policyFields=element('div',null,'fields'),duration=element('input');duration.id='duration-'+client.id;duration.type='number';duration.min=0;duration.max=3650;duration.placeholder='Ne pas changer';
    policyFields.append(labelled('Nouvelle durée de validité (jours)',duration,'Laissez vide pour conserver la date actuelle. 0 = illimité.'));policy.append(policyFields);
    const buttons=element('div',null,'key-row'),save=element('button','Appliquer les limites','button secondary');save.onclick=()=>{if(!duration.checkValidity()){duration.reportValidity();return;}remoteAction('/api/remote/policy',{id:client.id,suspended:!!client.suspended,...(duration.value!==''?{days:Number(duration.value)}:{})});};
    const suspend=element('button',client.suspended?'Réactiver l’accès':'Suspendre l’accès','button secondary');suspend.onclick=()=>remoteAction('/api/remote/policy',{id:client.id,suspended:!client.suspended});
    buttons.append(save,suspend);policy.append(buttons);card.append(policy);
    const revokeDetails=element('details',null,'client-revoke');revokeDetails.append(element('summary','Révocation définitive'));
    revokeDetails.append(element('p','Révoquer cet accès invalide son EXE et son tunnel. Pour revenir, il faudra créer un nouvel accès.','muted'));
    const revoke=element('button','Révoquer cet accès','button stop');revoke.onclick=()=>remoteAction('/api/remote/revoke',{id:client.id});revokeDetails.append(revoke);card.append(revokeDetails);return card;
  }));
  if(!value.clients.length)$('remote-clients').append(element('div','Aucun client enregistré. Ajoutez votre premier client ci-dessus.','network-help'));
}
async function remoteRefresh(force=false){
  if(remoteBusy)return;
  try{
    const value=await request('/api/remote');
    $('remote-status').textContent=(value.enabled?'Accès clients activé. ':'Accès clients désactivé. ')+value.connection.message+(value.hermes?' · Hermes '+(value.hermes.available?'disponible':'indisponible'):'');
    $('remote-save').disabled=false;
    if(!remoteDirty){$('remote-host').value=value.connection.public_host;$('remote-port').value=value.connection.listen_port;}
    $('remote-url').value=value.connection.public_host?value.connection.public_host+':'+value.connection.listen_port+' / UDP':'';
    $('remote-copy-connection').disabled=remoteDirty||!value.connection.public_host;
    $('remote-route').textContent='Box : rediriger UDP '+value.connection.listen_port+' vers '+(liveState.lan_ips?.[0]||'l’adresse locale du PC serveur')+', port UDP '+value.connection.listen_port+'.';
    $('remote-firewall-state').textContent=value.connection.firewall?.message||'Autorisation Windows : utiliser « Autoriser dans Windows ».';
    $('remote-activate').disabled=remoteDirty||!value.connection.public_host||!value.connection.compiled||!value.gateway_available;
    $('remote-firewall').disabled=remoteDirty||!value.connection.public_host||!value.connection.compiled||(value.connection.firewall?.state==='ready'&&value.connection.firewall?.port===value.connection.listen_port);
    $('remote-disable').disabled=!value.enabled;
    $('remote-create').disabled=remoteDirty||!value.connection.public_host||!value.client_compiled;
    if(force||!document.activeElement?.closest('#remote-clients'))renderClients(value,force);
  }catch(error){$('remote-status').textContent=error.message;}
}
async function remoteAction(path,data={}){
  if(remoteBusy)return;remoteBusy=true;
  const buttons=[...document.querySelectorAll('#internet button,#clients button')].map(button=>[button,button.disabled]);buttons.forEach(([button])=>button.disabled=true);
  try{const result=await request(path,data);toast(result.message||'Commande terminée.');if(result.download){$('remote-client-name').value='';clientsFingerprint='';openTopic('clients');}return true;}
  catch(error){toast(error.message,true);return false;}
  finally{remoteBusy=false;buttons.forEach(([button,disabled])=>button.disabled=disabled);await remoteRefresh(true);}
}
for(const name of ['firewall','activate'])$('remote-'+name).onclick=()=>remoteAction('/api/remote/'+name);
$('remote-save').onclick=async()=>{if(await remoteAction('/api/remote/configure',{public_host:$('remote-host').value.trim(),listen_port:Number($('remote-port').value)})){remoteDirty=false;await remoteRefresh();}};
for(const id of ['remote-host','remote-port'])$(id).addEventListener('input',()=>{remoteDirty=true;$('remote-activate').disabled=true;$('remote-firewall').disabled=true;$('remote-create').disabled=true;});
$('remote-disable').onclick=()=>remoteAction('/api/remote/deactivate');
$('remote-create').onclick=()=>remoteAction('/api/remote/create-client',{name:$('remote-client-name').value});
remoteRefresh();setInterval(remoteRefresh,15000);
$('save').onclick=()=>action(async()=>{applySettings(await request('/api/save',form()));toast('Réglages enregistrés. Le serveur actif conserve sa configuration.');});
$('set-default').onclick=()=>action(async()=>{const value=await request('/api/set-default',form());applySettings(value);showDefaults(value);toast('Ces réglages sont votre nouveau profil par défaut.');});
$('restore-defaults').onclick=()=>action(async()=>{applySettings(await request('/api/defaults'));dirty=true;$('save-state').textContent='Valeurs par défaut restaurées · à enregistrer';toast('Valeurs par défaut restaurées dans le formulaire.');});
$('start').onclick=()=>action(async()=>{await request('/api/start',form());dirty=false;toast('Chargement démarré. Vous pouvez fermer cette page.');});
$('stop').onclick=()=>action(async()=>{await request('/api/stop',{});toast('Serveur arrêté. La RAM et la VRAM sont libérées.');});
$('open-chat').onclick=()=>{if(liveState.chat_url)window.open(liveState.chat_url,'_blank','noopener');};
$('local-only').onclick=()=>{$('host').value='127.0.0.1';dirty=true;$('save-state').textContent='Modifications à enregistrer';updatePreview();};
$('local-network').onclick=()=>{$('host').value='0.0.0.0';dirty=true;$('save-state').textContent='Modifications à enregistrer';updatePreview();};
$('generate-key').onclick=()=>action(async()=>{const result=await request('/api/key',{});$('api_key').value=result.api_key;dirty=true;$('save-state').textContent='Nouvelle clé · à enregistrer';toast('Clé générée ; enregistrez-la pour le prochain lancement.');});
$('show-key').onclick=()=>{const show=$('api_key').type==='password';$('api_key').type=show?'text':'password';$('show-key').textContent=show?'Masquer la clé':'Afficher la clé';};
$('copy-key').onclick=()=>{$('api_key').value?copy($('api_key').value):toast('Générez d’abord une clé API.',true);};
$('copy-api').onclick=()=>copy($('api-address').value);$('copy-log').onclick=()=>copy($('engine-log').textContent);
request('/api/settings').then(applySettings).then(refresh).catch(error=>toast(error.message,true));setInterval(refresh,5000);
request('/api/defaults').then(showDefaults).catch(error=>toast(error.message,true));

request('/api/operations').then(o=>{for(const k of ['startup','autoload','restart'])$('ops-'+k).checked=o[k];});
$('ops-save').onclick=()=>action(async()=>{await request('/api/operations',{autoload:$('ops-autoload').checked,restart:$('ops-restart').checked});await request('/api/startup',{enabled:$('ops-startup').checked});toast('Options d’exploitation enregistrées.');});
$('performance-profile').onchange=()=>{const profiles={fast:{context:8192,history_slots:2},long:{context:262144,history_slots:6},shared:{context:32768,history_slots:6}};const p=profiles[$('performance-profile').value];if(p){applySettings({...form(),...p,history_enabled:true});dirty=true;$('save-state').textContent='Profil à enregistrer pour le prochain lancement';}};
$('ops-backup').onclick=()=>action(async()=>{const r=await request('/api/backup',{password:$('backup-password').value});$('backup-password').value='';$('backup-result').textContent=r.file;toast(r.message);});
$('ops-restore').onclick=()=>action(async()=>{const r=await request('/api/restore',{file:$('backup-file').value,password:$('backup-password').value});$('backup-password').value='';applySettings(await request('/api/settings'));$('backup-result').textContent=r.message;toast(r.message);});
$('ops-diagnostic').onclick=()=>action(async()=>{const d=await request('/api/diagnostic');const url=URL.createObjectURL(new Blob([JSON.stringify(d,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='diagnostic-qwen.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});

request('/api/releases').then(r=>{document.getElementById('release-status').textContent='Serveur '+r.server_version+' · client '+(r.release.version||'à compiler')+' · '+(r.verified?'empreinte vérifiée':'binaire non vérifié');});
$('release-prepare').onclick=()=>action(async()=>{toast((await request('/api/releases/prepare',{})).message);});
$('release-rollback').onclick=()=>action(async()=>{toast((await request('/api/releases/rollback',{})).message);});
$('remote-copy-connection').onclick=()=>action(async()=>{
  if(remoteDirty)throw new Error('Enregistrez les paramètres d’accès distant avant de les copier.');
  const endpoint=$('remote-url').value.replace(/\s*\/\s*UDP\s*$/i,'').trim();
  if(!endpoint)throw new Error('Enregistrez une adresse publique et un port UDP.');
  const settings=JSON.stringify({format:'acces-serveur-fred-connection',version:1,protocol:'UDP',endpoint},null,2);
  try{await navigator.clipboard.writeText(settings);$('remote-copy-status').textContent='Paramètres copiés. Dans le client : Réglages → Connexion → Coller les paramètres.';}
  catch{$('remote-url').focus();$('remote-url').select();$('remote-copy-status').textContent='Adresse sélectionnée. Copiez avec Ctrl+C et collez-la dans le client distant.';}
});
