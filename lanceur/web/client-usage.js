/* Aggregate presence in the local administration console. */
'use strict';
(()=>{
  const panel=document.getElementById('client-usage');if(!panel)return;
  const get=id=>document.getElementById('usage-'+id);
  let sequence=0,lastValue=null,renderedPeriod=null;
  const integer=value=>Math.max(0,Math.trunc(Number(value)||0)).toLocaleString('fr-FR');
  const duration=value=>{
    const minutes=Math.floor(Math.max(0,Number(value)||0)/60);
    if(!minutes)return value>0?'Moins d’une min':'0 min';
    return minutes<60?minutes+' min':Math.floor(minutes/60)+' h '+String(minutes%60).padStart(2,'0')+' min';
  };
  const cell=(row,value)=>{const td=document.createElement('td');td.textContent=value;row.append(td);return td;};
  const date=value=>new Date(value+'T12:00:00').toLocaleDateString('fr-FR',{day:'numeric',month:'short'});
  function render(value){
    if(!value.available){lastValue=null;renderedPeriod=null;get('body').hidden=true;get('status').textContent=value.error||'Historique indisponible.';return;}
    get('body').hidden=false;
    lastValue=value;renderedPeriod=value.period;
    get('sessions').textContent=integer(value.sessions);
    get('duration').textContent=duration(value.seconds);
    get('clients').textContent=integer(value.active_clients);
    get('presence').textContent=integer(value.online)+' client'+(value.online===1?'':'s')+' avec un contact depuis moins de 2 min';
    get('status').textContent=value.warning||'';
    const weekly=value.period==='week',field=get('metric').value==='seconds'?'seconds':'sessions';
    const maximum=Math.max(1,...value.buckets.map(item=>item[field]));
    get('chart-title').textContent=(field==='seconds'?'Temps connecté estimé':'Connexions')+' par '+(weekly?'semaine':'jour');
    get('scale').textContent=field==='sessions'?integer(maximum):maximum>=3600?(maximum/3600).toLocaleString('fr-FR',{maximumFractionDigits:1})+' h':Math.max(1,Math.round(maximum/60))+' min';
    get('from').textContent=date(value.start);get('to').textContent=date(value.end);
    const bars=document.createDocumentFragment(),data=document.createDocumentFragment();
    for(const item of value.buckets){
      const description=(weekly?'Semaine du ':'')+date(item.date)+' : '+integer(item.sessions)+' connexion'+(item.sessions===1?'':'s')+', '+duration(item.seconds)+', '+integer(item.clients)+' client'+(item.clients===1?'':'s');
      const bar=document.createElement('div');bar.className='usage-bar'+(item[field]?'':' is-zero');bar.title=description;
      const amount=document.createElement('span');amount.textContent=field==='sessions'&&item.sessions?integer(item.sessions):'';
      const fill=document.createElement('i');fill.style.height=(100*item[field]/maximum)+'%';
      bar.append(amount,fill);bars.append(bar);
      const row=document.createElement('tr');cell(row,(weekly?'Semaine du ':'')+date(item.date));cell(row,integer(item.sessions));cell(row,duration(item.seconds));cell(row,integer(item.clients));data.append(row);
    }
    get('bars').style.setProperty('--usage-columns',value.buckets.length);
    get('bars').replaceChildren(bars);get('data').replaceChildren(data);
    get('empty').hidden=value.sessions>0||value.seconds>0;
    const rows=document.createDocumentFragment();
    for(const client of value.clients){
      const row=document.createElement('tr'),name=cell(row,client.name);
      const presence=document.createElement('small');presence.textContent=client.deleted?'Accès supprimé':client.online?'Contact récent':'Sans contact récent';presence.className=client.online?'usage-present':'muted';name.append(presence);
      const options={day:'numeric',month:'short',hour:'2-digit',minute:'2-digit',...(value.timezone==='Europe/Paris'?{timeZone:'Europe/Paris'}:{})};
      cell(row,client.last_epoch?new Date(client.last_epoch*1000).toLocaleString('fr-FR',options):'Aucun contact enregistré');
      cell(row,integer(client.sessions));cell(row,duration(client.seconds));rows.append(row);
    }
    get('client-rows').replaceChildren(rows);get('no-clients').hidden=value.clients.length>0;get('client-table').hidden=!value.clients.length;
    const since=new Date(value.started_epoch*1000).toLocaleDateString('fr-FR',value.timezone==='Europe/Paris'?{timeZone:'Europe/Paris'}:{});
    get('since').textContent='Suivi depuis le '+since+' · Historique conservé '+value.retention_days+' jours · '+value.timezone;
  }
  async function refresh(){
    const current=++sequence;get('refresh').disabled=true;panel.setAttribute('aria-busy','true');
    try{
      const response=await fetch('/api/clients/activity?period='+get('period').value,{headers:{'X-Launcher-Token':token},signal:AbortSignal.timeout(10000)});
      if(response.status===404)throw new Error('Redémarrez la console serveur pour activer le suivi des clients.');
      const value=await response.json();if(!response.ok)throw new Error(value.error||'Lecture de l’activité impossible.');
      if(current===sequence)render(value);
    }catch(error){if(current===sequence){if(get('period').value!==renderedPeriod)get('body').hidden=true;get('status').textContent=(error.name==='TimeoutError'?'Le serveur ne répond pas.':error.message)+' Réessayez l’actualisation.';}}
    finally{if(current===sequence){get('refresh').disabled=false;panel.setAttribute('aria-busy','false');}}
  }
  get('refresh').addEventListener('click',refresh);get('period').addEventListener('change',refresh);
  get('metric').addEventListener('change',()=>{if(lastValue?.period===get('period').value)render(lastValue);});
  document.querySelector('[data-tab="clients"]')?.addEventListener('click',refresh);
  setInterval(()=>{if(!document.hidden&&!document.getElementById('clients').hidden)refresh();},15000);
  refresh();
})();
