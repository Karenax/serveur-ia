'use strict';

const $=id=>document.getElementById(id);
const config=JSON.parse($('settings-config').textContent);
const pane=document.querySelector('.settings-view');
const alert=$('device-error');
let visible=true, pending=0;
let refresh=()=>{};
const dirtyChecks=[];

function error(failure){
  alert.hidden=!failure;
  alert.textContent=failure?.message||failure||'';
}
function wsElement(tag,text,className){
  const element=document.createElement(tag);
  if(text!==undefined)element.textContent=text;
  if(className)element.className=className;
  return element;
}
async function api(path,body){
  const response=await fetch(path,{
    method:body===undefined?'GET':'POST',
    headers:{Authorization:'Bearer '+config.key,'Content-Type':'application/json'},
    body:body===undefined?undefined:JSON.stringify(body),
    signal:AbortSignal.timeout(path==='/client/integrations/apply'?90000:35000),
  });
  const value=await response.json();
  if(!response.ok)throw new Error(value.error?.message||value.detail||'Action refusée.');
  return value;
}
async function wsTry(task){
  pending++;
  error('');
  try{return await task();}catch(failure){error(failure);}
  finally{pending--;}
}
const dirty=()=>pending>0||dirtyChecks.some(check=>check());
window.addEventListener('beforeunload',event=>{
  if(dirty()){event.preventDefault();event.returnValue='';}
});
window.kiaraShowDeviceSetting=section=>section===config.section;
window.kiaraSetDeviceSettingActive=value=>{
  const reopen=value&&!visible;
  visible=value;
  if(!value&&config.section==='api-locale'&&$('local-api-key').type==='text')$('toggle-api-key').click();
  if(reopen)void refresh();
};
const systemTheme=matchMedia('(prefers-color-scheme: dark)');
function theme(){
  try{
    const saved=localStorage.getItem('fred-theme')||localStorage.getItem('agent-ui-theme');
    document.documentElement.dataset.theme=saved==='dark'||saved==='system'&&systemTheme.matches?'dark':'light';
  }catch{}
}
theme();
systemTheme.addEventListener('change',theme);
window.addEventListener('storage',theme);

function initializeVocal(){
  pane.insertAdjacentHTML('beforeend',voiceSettingsMarkup('Windows'));
  const settings=pane.querySelector('.voice-settings');
  settings.removeAttribute('aria-labelledby');
  settings.querySelector('#voice-settings-title').remove();
  settings.querySelector('.voice-diagnostics').open=true;
  let native={}, writes=Promise.resolve(), changed=false, edit=0;
  const voice=mountVoiceSettings(settings,{
    api,error,wsElement,runtime:()=>({native,active:['permission','loading','listening','stopping'].includes(native.phase)}),
    persist(values){
      changed=true;const revision=++edit;
      pending++;
      writes=writes.catch(()=>{}).then(()=>api('/client/preferences',values)).then(()=>{
        if(revision===edit)changed=false;
      }).finally(()=>pending--);
      return writes;
    },
  });
  dirtyChecks.push(()=>changed);
  const initialLoad=setupStateLoader(async state=>{
    if(state.voice_preferences_error)throw new Error(state.voice_preferences_error);
    voice.applyPreferences(state.voice_preferences);
    settings.inert=false;
    void voice.refreshMax();
  });
  settings.inert=true;
  const load=async()=>{
    await initialLoad();
    try{native=await api('/client/conversation');voice.drawQuality();}catch(failure){error(failure);}
  };
  return {refresh:load, interval:2500};
}

function initializeDictation(){
  const status=wsElement('p','Chargement…','muted');
  status.setAttribute('role','status');
  const phases=new Set(['installing','verifying','permission','loading','listening','finishing','cancelling']);
  let state={}, acting=false, loaded=false, revision=0;
  const locked=()=>!loaded||acting||phases.has(state.phase);
  const dictation=dictationSettings(status,action=>wsTry(async()=>{
    acting=true;revision++;
    dictation.render(state,true);
    try{update(await api('/client/voice',{action}));}
    finally{acting=false;dictation.render(state,locked());}
  }),locked,{embedded:true});
  pane.append(dictation.settings);
  dictation.render(state,true);
  function update(value){
    state=value;loaded=true;
    const amount=value.downloaded_bytes&&value.model_bytes?' · '+Math.floor(100*value.downloaded_bytes/value.model_bytes)+' %':'';
    status.textContent=(value.message||(value.installed?'Modèle installé.':'Modèle à installer.'))+amount;
    dictation.render(state,locked());
  }
  return {refresh:async()=>{
    if(acting)return;
    const requested=revision;
    try{const current=await api('/client/voice');if(requested===revision)update(current);}
    catch(failure){if(requested===revision)status.textContent=failure.message;}
  },interval:1500};
}

function initializeConnection(){
  let endpointDirty=false,busy=false;
  let readRevision=0;
  const form=$('endpoint-form');
  const endpoint=$('endpoint'), buttons=[form.querySelector('[type="submit"]'),$('reconnect')];
  const status=wsElement('p');
  status.setAttribute('role','status');
  form.querySelector('.actions').after(status);
  const result=$('connection-diagnostic');
  function copyText(value){return navigator.clipboard.writeText(value);}
  /* kiara-device:connection */
  async function read(){
    const revision=++readRevision;
    const state=await api('/client/device-state');
    if(revision!==readRevision)return;
    if(!endpointDirty&&document.activeElement!==endpoint)endpoint.value=state.endpoint||'';
    uiConnectionSettings(state);
    const c=state.connection;
    result.textContent=c.connected?'Serveur Kiara accessible.':c.error||
      (c.connection_required?'Choisissez le mode de connexion.':'Vérification de la connexion en cours…');
    result.textContent+=c.endpoint?'\nAdresse utilisée · '+c.endpoint+(c.automatic?' · automatique':''):'';
  }
  async function action(values){
    if(busy)return;
    readRevision++;
    busy=true;buttons.forEach(button=>button.disabled=true);
    try{
      if(values!==undefined){
        await api('/client/endpoint',values);
        endpointDirty=false;status.textContent='Connexion enregistrée.';
      }
      await api('/client/device-reconnect',{});
      if(values===undefined)status.textContent='Nouvelle vérification lancée.';
      await read();
    }finally{
      busy=false;buttons.forEach(button=>button.disabled=false);
      $('connection-mode').disabled=false;$('automatic').disabled=$('connection-mode').value==='https';
      for(const id of ['connection-copy','connection-paste','connection-use-parameters'])$(id).disabled=false;
    }
  }
  endpoint.oninput=()=>{endpointDirty=true;};
  $('endpoint-form').onsubmit=event=>{event.preventDefault();void wsTry(()=>action({endpoint:endpoint.value}));};
  $('automatic').onclick=()=>wsTry(()=>action({}));
  $('reconnect').onclick=()=>wsTry(()=>action());
  dirtyChecks.push(()=>endpointDirty);
  return {refresh:()=>busy?undefined:read().catch(error),interval:2500};
}

function initializeUpdates(){
  const check=$('update-check'),apply=$('update-apply'),status=$('update-status');
  $('update-kiara4').hidden=true;
  $('update-rollback').hidden=true;
  let acting=false, state={};
  const render=value=>{
    state=value;
    check.disabled=acting||!!value.busy;
    apply.disabled=acting||!!value.busy||!value.available;
    status.textContent=value.message||'Vérifiez si une nouvelle version est disponible.';
  };
  async function run(install){
    if(acting||state.busy||install&&!state.available)return;
    acting=true;render(state);
    try{
      if(install)await api('/client/history/flush',{});
      render(await api('/client/update/'+(install?'apply':'check'),{}));
    }finally{acting=false;render(state);}
  }
  check.onclick=()=>wsTry(()=>run(false));
  apply.onclick=()=>wsTry(()=>run(true));
  return {refresh:async()=>{
    if(acting)return;
    try{const current=await api('/client/device-state');if(!acting)render(current.update);}
    catch(failure){error(failure);}
  },interval:1200};
}

function initializeApi(){
  let connected=false;
  const key=$('local-api-key');
  const model=wsElement('select');model.id='device-integration-model';
  const label=wsElement('label','Modèle à ajouter');label.htmlFor=model.id;
  $('integration-opencode').closest('.settings-card').querySelector('p').after(label,model,$('integration-model'));
  const conversationModel=()=>model.value;
  const conversationModelAvailable=()=>!!model.value;
  const conversationModelLabel=()=>model.value;
  /* kiara-device:api */
  $('toggle-api-key').onclick=()=>{
    key.type=key.type==='password'?'text':'password';
    $('toggle-api-key').textContent=key.type==='password'?'Afficher la clé':'Masquer la clé';
  };
  model.onchange=uiIntegrationButtons;
  dirtyChecks.push(()=>uiIntegrationPending);
  const load=setupStateLoader(async state=>{
    $('local-api').textContent=state.local_api;
    key.value=state.key||'';
    connected=state.connection.connected;
    const models=state.connection.models||[];
    if(JSON.stringify(models)!==model.dataset.models){
      const selected=model.value||state.connection.model;
      model.replaceChildren(...models.map(id=>new Option(id,id)));
      if(models.includes(selected))model.value=selected;
      model.dataset.models=JSON.stringify(models);
    }
    model.disabled=!connected||!models.length;
    uiIntegrationButtons();
  },{repeat:true});
  void uiRefreshIntegrations();
  return {refresh:load,interval:4000};
}

function setupStateLoader(apply,{repeat=false}={}){
  let ready=false,loading=false;
  const retry=wsElement('button','Réessayer','secondary');
  retry.hidden=true;retry.type='button';alert.after(retry);
  async function load(){
    if(loading||ready&&!repeat)return;
    loading=true;
    try{
      const section=['api','vocal'].includes(config.section)?'?section='+config.section:'';
      await apply(await api('/client/device-state'+section));
      ready=true;retry.hidden=true;
    }
    catch(failure){error(failure);retry.hidden=false;}
    finally{loading=false;}
  }
  retry.onclick=()=>{error('');void load();};
  return load;
}

const panel={
  vocal:initializeVocal,dictee:initializeDictation,connexion:initializeConnection,
  'mises-a-jour':initializeUpdates,'api-locale':initializeApi,
}[config.section]();
let refreshing=false;
refresh=async()=>{
  if(refreshing)return;
  refreshing=true;
  try{await panel.refresh();}
  finally{refreshing=false;}
};
void refresh();
setInterval(()=>{if(visible&&!document.hidden)void refresh();},panel.interval);
