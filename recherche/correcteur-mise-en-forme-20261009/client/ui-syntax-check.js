
    'use strict';
    const config={}, $=id=>document.getElementById(id);
    const storage='qwen-chat-'+config.storage;
    let messages=[],busy=false,connected=false,controller=null,requestId=null,loggedIn=false;
    try{const saved=JSON.parse(localStorage.getItem(storage)||'[]');if(Array.isArray(saved)&&saved.every(m=>m&&['user','assistant'].includes(m.role)&&typeof m.content==='string'&&(!m.reasoning_content||typeof m.reasoning_content==='string')))messages=saved;}catch{}
    function error(text){$('error').hidden=!text;$('error').textContent=text||'';}
    let saveTimer=null,historyWrites=Promise.resolve(),historyRevision="",historyReady=false,historyBlocked=false,endpointDirty=false,deletedConversation=null;
    function save(){
      const c=library.find(c=>c.id===currentId);if(c)c.messages=messages;
      if(!historyReady||historyBlocked)return;clearTimeout(saveTimer);saveTimer=setTimeout(()=>flushHistory().catch(()=>{}),400);
    }
    function flushHistory(){
      clearTimeout(saveTimer);
      if(!historyReady||historyBlocked)return Promise.reject(new Error('Enregistrement bloqué : exporter votre travail puis recharger le client.'));
      const history=JSON.parse(JSON.stringify({conversations:library,currentId}));
      $('history-status').textContent='Enregistrement…';
      historyWrites=historyWrites.catch(()=>{}).then(()=>api('/client/history',{history,revision:historyRevision})).then(result=>{
        historyRevision=result.revision;localStorage.removeItem(storage);localStorage.removeItem(libraryKey);
        $('history-status').textContent='Historique enregistré et chiffré sur ce PC';
      }).catch(e=>{if(e.status===409)historyBlocked=true;$('history-status').textContent='Historique non enregistré : '+e.message;throw e;});
      return historyWrites;
    }
    const libraryKey=storage+'-library';let library=[],currentId=null;
    function validMessages(value){return Array.isArray(value)&&value.length<=1000&&value.every(m=>m&&['user','assistant'].includes(m.role)&&typeof m.content==='string'&&(!m.reasoning_content||typeof m.reasoning_content==='string'));}
    try{const saved=JSON.parse(localStorage.getItem(libraryKey)||'[]');if(Array.isArray(saved)&&saved.every(c=>typeof c.id==='string'&&typeof c.title==='string'&&validMessages(c.messages)))library=saved;}catch{}
    if(!library.length)library=[{id:crypto.randomUUID(),title:'Conversation',messages}];
    currentId=library[0].id;messages=library[0].messages;
    function drawLibrary(){
      const query=$('search-conversations').value.toLowerCase(),current=library.find(c=>c.id===currentId);$('conversation-title').value=current?.title||'Nouvelle conversation';
      const items=library.filter(c=>c.title.toLowerCase().includes(query)||c.messages.some(m=>m.content.toLowerCase().includes(query)));
      $('conversations').replaceChildren(...items.map(c=>{const o=document.createElement('option');o.value=c.id;o.textContent=c.title;o.selected=c.id===currentId;return o;}));
      $('conversation-list').replaceChildren(...items.map(c=>{const b=document.createElement('button');b.className='conversation-item'+(c.id===currentId?' selected':'');b.type='button';b.disabled=busy;b.setAttribute('aria-current',c.id===currentId?'true':'false');const title=document.createElement('span');title.textContent=c.title;const detail=document.createElement('small');detail.textContent=c.messages.length+' messages';b.append(title,detail);b.onclick=()=>{if(busy)return;save();currentId=c.id;messages=c.messages;render();drawLibrary();showView('chat');error('');};return b;}));
      if(!items.length){const empty=document.createElement('p');empty.className='muted';empty.textContent='Aucune conversation trouvée.';$('conversation-list').append(empty);}
    }
    $('search-conversations').oninput=drawLibrary;
    $('conversations').onchange=()=>{if(busy)return;const selected=$('conversations').value;save();currentId=selected;messages=library.find(c=>c.id===currentId).messages;render();drawLibrary();error('');};
    $('rename-conversation').onclick=()=>{if(busy)return;const c=library.find(c=>c.id===currentId),title=$('conversation-title').value;if(title.trim()){c.title=title.trim().slice(0,120);save();drawLibrary();}};
    $('export-conversations').onclick=()=>{save();const url=URL.createObjectURL(new Blob([JSON.stringify({version:1,conversations:library},null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='conversations-fred.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
    $('import-conversations').onclick=()=>{if(!busy)$('import-file').click();};
    $('import-file').onchange=async()=>{try{const f=$('import-file').files[0];if(!f)return;if(f.size>10*1024*1024)throw new Error('Import limité à 10 Mo.');const d=JSON.parse(await f.text());if(d.version!==1||!Array.isArray(d.conversations)||d.conversations.length>200||!d.conversations.every(c=>typeof c.title==='string'&&validMessages(c.messages)))throw new Error('Fichier de conversations invalide.');if(d.conversations.some(c=>!c.title.trim()||c.title.length>120))throw new Error('Titres importés invalides.');if(library.length+d.conversations.length>200)throw new Error('Import impossible : maximum 200 conversations au total.');const incoming=d.conversations.map(c=>({id:crypto.randomUUID(),title:c.title.trim(),messages:c.messages}));const candidate=[...library,...incoming];if(new TextEncoder().encode(JSON.stringify({conversations:candidate,currentId})).length>9*1024*1024)throw new Error('Historique total limité à 9 Mo. Exportez puis supprimez des conversations.');library=candidate;save();await flushHistory();drawLibrary();}catch(e){error(e.message);}finally{$('import-file').value='';}};
    $('delete-conversation').onclick=()=>{if(busy)return;deletedConversation=library.find(c=>c.id===currentId);library=library.filter(c=>c.id!==currentId);if(!library.length)library=[{id:crypto.randomUUID(),title:'Nouvelle conversation',messages:[]}];currentId=library[0].id;messages=library[0].messages;$('undo-delete').hidden=false;save();render();drawLibrary();};
    $('undo-delete').onclick=()=>{if(busy||!deletedConversation)return;if(library.length>=200){error('Maximum 200 conversations.');return;}library.unshift(deletedConversation);currentId=deletedConversation.id;messages=deletedConversation.messages;deletedConversation=null;$('undo-delete').hidden=true;save();render();drawLibrary();};
    $('history-recover').onclick=async()=>{if(!confirm('Conserver une copie chiffrée du fichier illisible et enregistrer les conversations actuellement affichées ?'))return;try{const result=await api('/client/history/recover',{history:{conversations:library,currentId}});historyRevision=result.revision;historyReady=true;historyBlocked=false;$('history-recover').hidden=true;$('history-status').textContent='Historique récupéré. Original conservé : '+result.backup;error('');}catch(e){error(e.message);}};
    $('retry').onclick=()=>{if(busy)return;let i=messages.length-1;if(messages[i]?.role==='assistant')i--;if(messages[i]?.role!=='user')return;const text=messages[i].content;messages=messages.slice(0,i);save();render();$('prompt').value=text;$('composer').requestSubmit();};
    drawLibrary();
    function draw(message){
      const article=document.createElement('article');article.className='message '+message.role;
      const label=document.createElement('div');label.className='label';label.textContent=message.role==='user'?'Vous':('Assistant'+(message.interrupted?' · réponse interrompue':''));
      const content=document.createElement('div');content.className='content';content.textContent=message.content;
      const details=document.createElement('details');details.hidden=!message.reasoning_content;
      const summary=document.createElement('summary');summary.textContent='Réflexion';
      const reasoning=document.createElement('div');reasoning.className='reasoning';reasoning.textContent=message.reasoning_content||'';
      details.append(summary,reasoning);const copy=document.createElement('button');copy.type='button';copy.className='secondary message-copy';copy.textContent='Copier';copy.setAttribute('aria-label',message.role==='user'?'Copier votre message':'Copier la réponse');copy.onclick=async()=>{try{await navigator.clipboard.writeText(message.content);copy.textContent='Copié';setTimeout(()=>copy.textContent='Copier',1500);}catch{error('Copie impossible. Sélectionnez le texte pour le copier.');}};article.append(copy,label,details,content);$('messages').append(article);
      return {article,content,details,reasoning};
    }
    function render(){$('messages').querySelectorAll('.message').forEach(m=>m.remove());$('empty').hidden=messages.length>0;messages.forEach(draw);}
    function buttons(){for(const id of ['conversations','rename-conversation','delete-conversation','undo-delete','import-conversations','retry'])$(id).disabled=busy;$('send').disabled=busy||!connected;$('send').hidden=busy;$('cancel').hidden=!busy;$('new').disabled=busy||!historyReady&&!historyBlocked;$('thinking').disabled=busy;$('maximum').disabled=busy;$('prompt').disabled=busy;}
    async function models(){
      if(busy)return;if(!loggedIn){connected=false;buttons();return;}
      try{const r=await fetch('/v1/models',{headers:{Authorization:'Bearer '+config.key}});if(!r.ok){const d=await r.json();if(d.error?.code==='login_required'){loggedIn=false;$('account-status').textContent=d.error.message;}throw new Error(d.error?.message||'Serveur indisponible');}const d=await r.json();const ids=Array.isArray(d.data)?d.data.filter(m=>m&&typeof m.id==='string'&&m.id.trim()).map(m=>m.id):[];if(!ids.length)throw new Error();if(!ids.includes(config.model))config.model=ids[0];connected=true;let serverVersion='';try{const sr=await fetch('/v1/status',{headers:{Authorization:'Bearer '+config.key}});if(sr.ok){const state=await sr.json();serverVersion=state.version||'';if(state.protocol>3)throw new Error('Mettre à jour Accès serveur Fred pour ce serveur.');}}catch(e){if(e.message.includes('Mettre à jour'))throw e;}$('model').textContent=config.model+(serverVersion?' · serveur '+serverVersion+' · client '+config.version:'');$('connection').textContent='● Connecté au serveur IA';$('connection').classList.add('online');}
      catch(e){connected=false;config.model='';$('model').textContent='Aucun modèle accessible';$('connection').textContent=e.message||'● Serveur indisponible';$('connection').classList.remove('online');}buttons();
    }
    function delta(event,answer,view){
      const queued=event.split(/\r?\n/).find(line=>line.startsWith(': qwen-queue '));if(queued){const q=JSON.parse(queued.slice(13));$('queue-state').textContent=q.position?`En attente · position ${q.position}`:'Génération en cours';return;}
      const data=event.split(/\r?\n/).filter(line=>line.startsWith('data:')).map(line=>line.slice(5).trimStart()).join('\n');
      if(data==='[DONE]')return true;if(!data)return false;
      const value=JSON.parse(data);if(value.queue){$('queue-state').textContent=value.queue.position?`En attente · position ${value.queue.position}`:'Génération en cours';return;}if(value.error)throw new Error(value.error.message||'La génération a échoué.');
      const d=value.choices?.[0]?.delta||{};
      if(typeof d.content==='string')answer.content+=d.content;
      const reason=d.reasoning_content??d.reasoning;if(typeof reason==='string')answer.reasoning_content+=reason;
      save();view.content.textContent=answer.content;view.reasoning.textContent=answer.reasoning_content;view.details.hidden=!answer.reasoning_content;
      const pane=$('messages');if(pane.scrollHeight-pane.scrollTop-pane.clientHeight<300)pane.scrollTop=pane.scrollHeight;
    }
    $('composer').addEventListener('submit',async event=>{
      event.preventDefault();const text=$('prompt').value.trim();if(!text||busy||!connected)return;
      error('');const current=library.find(c=>c.id===currentId);if(!messages.length&&/^Conversation|^Nouvelle conversation/.test(current?.title||'')){current.title=text.slice(0,70);drawLibrary();}messages.push({role:'user',content:text});$('prompt').value='';render();save();
      const history=messages.map(m=>({role:m.role,content:m.content,...(m.reasoning_content?{reasoning_content:m.reasoning_content}:{})}));
      const answer={role:'assistant',content:'',reasoning_content:''};messages.push(answer);const view=draw(answer);$('messages').scrollTop=$('messages').scrollHeight;
      busy=true;drawLibrary();controller=new AbortController();requestId=crypto.randomUUID().replaceAll('-','');buttons();
      try{
        const response=await fetch('/v1/chat/completions',{method:'POST',headers:{Authorization:'Bearer '+config.key,'Content-Type':'application/json','X-Qwen-Request':requestId},signal:controller.signal,body:JSON.stringify({model:config.model,messages:history,stream:true,max_tokens:Number($('maximum').value),chat_template_kwargs:{enable_thinking:$('thinking').checked}})});
        if(!response.ok){let detail;try{detail=await response.json();}catch{}throw new Error(detail?.error?.message||'Le serveur a refusé la requête ('+response.status+').');}
        if(!response.headers.get('content-type')?.includes('text/event-stream')){
          const value=await response.json(),m=value.choices?.[0]?.message;if(value.error||!m)throw new Error(value.error?.message||'Réponse du serveur invalide.');answer.content=m.content||'';answer.reasoning_content=m.reasoning_content||'';view.content.textContent=answer.content;view.reasoning.textContent=answer.reasoning_content;view.details.hidden=!answer.reasoning_content;
        }else{
          const reader=response.body.getReader(),decoder=new TextDecoder();let pending='',completed=false;
          while(true){const {value,done}=await reader.read();pending+=done?decoder.decode():decoder.decode(value,{stream:true});const frames=pending.split(/\r?\n\r?\n/);pending=frames.pop();for(const frame of frames)completed=delta(frame,answer,view)||completed;if(done){if(pending.trim())completed=delta(pending,answer,view)||completed;if(!completed)throw new Error("Connexion interrompue : cette réponse est incomplète.");break;}}
        }
      }catch(e){answer.interrupted=true;error(e.name==='AbortError'?'Réponse interrompue.':e.message);}
      finally{$('queue-state').textContent='';if(!answer.content&&!answer.reasoning_content){messages.pop();view.article.remove();}busy=false;controller=null;save();render();drawLibrary();buttons();$('prompt').focus();models();}
    });
    $('prompt').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();$('composer').requestSubmit();}});
    $('cancel').onclick=()=>{const oldController=controller,oldId=requestId;oldController?.abort();if(oldId)fetch('/v1/cancel',{method:'POST',headers:{Authorization:'Bearer '+config.key,'Content-Type':'application/json','X-Qwen-Request':oldId},body:'{}',signal:AbortSignal.timeout(5000)}).catch(()=>{});};
    $('new').onclick=()=>{if(busy)return;if(library.length>=200){error('Limite de 200 conversations atteinte. Exportez votre historique.');return;}save();currentId=crypto.randomUUID();messages=[];library.unshift({id:currentId,title:'Nouvelle conversation',messages});save();drawLibrary();render();showView('chat');error('');$('prompt').focus();};
    async function api(path,body){const r=await fetch(path,{method:body?'POST':'GET',headers:{Authorization:'Bearer '+config.key,'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(20000)});const value=await r.json();if(!r.ok){const e=new Error(value.error?.message||'Action refusée');e.status=r.status;e.code=value.error?.code;throw e;}return value;}
    async function clientState(){try{const state=await api('/client/state');loggedIn=true;$('account-status').textContent='EXE personnel · connexion automatique';$('update-status').textContent=state.update.message||'';$('client-version').textContent='Accès serveur Fred '+state.version;$('update-apply').disabled=busy||state.update.busy||!state.update.available;$('update-check').disabled=busy||state.update.busy;$('local-api').textContent=state.local_api;$('local-api-key').value=state.key;if(!endpointDirty&&document.activeElement!==$('endpoint'))$('endpoint').value=state.endpoint;}catch(e){error(e.message);}}
    $('endpoint').oninput=()=>{endpointDirty=true;};
    $('endpoint-form').onsubmit=async event=>{event.preventDefault();try{await api('/client/endpoint',{endpoint:$('endpoint').value});endpointDirty=false;await clientState();models();}catch(e){error(e.message);}};
    $('automatic').onclick=async()=>{try{await api('/client/endpoint',{});endpointDirty=false;await clientState();models();}catch(e){error(e.message);}};
    $('update-check').onclick=async()=>{try{await api('/client/update/check',{});clientState();}catch(e){error(e.message);}};
    $('update-apply').onclick=async()=>{if(busy)return;try{await flushHistory();await api('/client/update/apply',{});clientState();}catch(e){error(e.message);}};
    async function bootstrap(){try{const result=await api('/client/history'),saved=result.history;historyRevision=result.revision;historyReady=true;if(saved){library=saved.conversations;currentId=saved.currentId;messages=library.find(c=>c.id===currentId).messages;}else save();}catch(e){historyBlocked=true;$('history-status').textContent=e.message;$('history-recover').hidden=e.code!=='history_unreadable';error(e.message);}render();drawLibrary();await clientState();models();}
    function showView(name){for(const pane of document.querySelectorAll('[data-view]'))pane.hidden=pane.dataset.view!==name;for(const button of document.querySelectorAll('[data-view-button]')){const active=button.dataset.viewButton===name;button.classList.toggle('active',active);button.setAttribute('aria-selected',String(active));}$('workspace-heading').textContent=({chat:'Conversations',access:'Mon accès',connection:'Connexion au serveur',updates:'Mises à jour',api:'API locale'})[name]||'Conversations';}
    document.querySelectorAll('[data-view-button]').forEach(button=>button.onclick=()=>showView(button.dataset.viewButton));
    document.querySelectorAll('[data-prompt]').forEach(button=>button.onclick=()=>{$('prompt').value=button.dataset.prompt;$('prompt').focus();});
    $('toggle-api-key').onclick=()=>{const field=$('local-api-key');field.type=field.type==='password'?'text':'password';$('toggle-api-key').textContent=field.type==='password'?'Afficher la clé':'Masquer la clé';};
    showView('chat');bootstrap();setInterval(models,15000);setInterval(clientState,2000);setInterval(()=>{if(loggedIn&&!busy)api('/client/update/check',{}).catch(()=>{});},600000);window.addEventListener('pagehide',()=>{if(!historyReady||historyBlocked)return;const c=library.find(c=>c.id===currentId);if(c)c.messages=messages;fetch('/client/history',{method:'POST',headers:{Authorization:'Bearer '+config.key,'Content-Type':'application/json'},body:JSON.stringify({history:{conversations:library,currentId},revision:historyRevision}),keepalive:true}).catch(()=>{});});
  