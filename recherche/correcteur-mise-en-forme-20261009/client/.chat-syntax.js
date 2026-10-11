
    'use strict';
    const config={}, $=id=>document.getElementById(id);
    const storage='qwen-chat-'+config.storage;
    let messages=[],busy=false,connected=false,controller=null,requestId=null,loggedIn=false;
    try{const saved=JSON.parse(localStorage.getItem(storage)||'[]');if(Array.isArray(saved)&&saved.every(m=>m&&['user','assistant'].includes(m.role)&&typeof m.content==='string'&&(!m.reasoning_content||typeof m.reasoning_content==='string')))messages=saved;}catch{}
    function error(text){$('error').hidden=!text;$('error').textContent=text||'';}
    let saveTimer=null,historyWrites=Promise.resolve();
    function save(){
      const c=library.find(c=>c.id===currentId);if(c)c.messages=messages;
      clearTimeout(saveTimer);saveTimer=setTimeout(flushHistory,400);
    }
    function flushHistory(){
      clearTimeout(saveTimer);
      const body=JSON.stringify({history:{conversations:library,currentId}});
      historyWrites=historyWrites.catch(()=>{}).then(()=>api('/client/history',JSON.parse(body))).catch(e=>error('Historique non enregistré : '+e.message));
      return historyWrites;
    }
    const libraryKey=storage+'-library';let library=[],currentId=null;
    function validMessages(value){return Array.isArray(value)&&value.length<=1000&&value.every(m=>m&&['user','assistant'].includes(m.role)&&typeof m.content==='string'&&(!m.reasoning_content||typeof m.reasoning_content==='string'));}
    try{const saved=JSON.parse(localStorage.getItem(libraryKey)||'[]');if(Array.isArray(saved)&&saved.every(c=>typeof c.id==='string'&&typeof c.title==='string'&&validMessages(c.messages)))library=saved;}catch{}
    if(!library.length)library=[{id:crypto.randomUUID(),title:'Conversation',messages}];
    currentId=library[0].id;messages=library[0].messages;
    function drawLibrary(){const query=$('search-conversations').value.toLowerCase();$('conversation-title').value=library.find(c=>c.id===currentId)?.title||'';$('conversations').replaceChildren(...library.filter(c=>c.title.toLowerCase().includes(query)||c.messages.some(m=>m.content.toLowerCase().includes(query))).map(c=>{const o=document.createElement('option');o.value=c.id;o.textContent=c.title;o.selected=c.id===currentId;return o;}));}
    $('search-conversations').oninput=drawLibrary;
    $('conversations').onchange=()=>{if(busy)return;const selected=$('conversations').value;save();currentId=selected;messages=library.find(c=>c.id===currentId).messages;render();drawLibrary();error('');};
    $('rename-conversation').onclick=()=>{if(busy)return;const c=library.find(c=>c.id===currentId),title=$('conversation-title').value;if(title.trim()){c.title=title.trim().slice(0,120);save();drawLibrary();}};
    $('export-conversations').onclick=()=>{save();const url=URL.createObjectURL(new Blob([JSON.stringify({version:1,conversations:library},null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='conversations-qwen.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
    $('import-conversations').onclick=()=>{if(!busy)$('import-file').click();};
    $('import-file').onchange=async()=>{try{const f=$('import-file').files[0];if(!f)return;if(f.size>10*1024*1024)throw new Error('Import limité à 10 Mo.');const d=JSON.parse(await f.text());if(d.version!==1||!Array.isArray(d.conversations)||d.conversations.length>200||!d.conversations.every(c=>typeof c.title==='string'&&validMessages(c.messages)))throw new Error('Fichier de conversations invalide.');for(const c of d.conversations)library.push({id:crypto.randomUUID(),title:c.title.slice(0,120),messages:c.messages});save();drawLibrary();}catch(e){error(e.message);}finally{$('import-file').value='';}};
    $('retry').onclick=()=>{if(busy)return;let i=messages.length-1;if(messages[i]?.role==='assistant')i--;if(messages[i]?.role!=='user')return;const text=messages[i].content;messages=messages.slice(0,i);save();render();$('prompt').value=text;$('composer').requestSubmit();};
    drawLibrary();
    function draw(message){
      const article=document.createElement('article');article.className='message '+message.role;
      const label=document.createElement('div');label.className='label';label.textContent=message.role==='user'?'Vous':'Assistant';
      const content=document.createElement('div');content.className='content';content.textContent=message.content;
      const details=document.createElement('details');details.hidden=!message.reasoning_content;
      const summary=document.createElement('summary');summary.textContent='Réflexion';
      const reasoning=document.createElement('div');reasoning.className='reasoning';reasoning.textContent=message.reasoning_content||'';
      details.append(summary,reasoning);article.append(label,details,content);$('messages').append(article);
      return {article,content,details,reasoning};
    }
    function render(){$('messages').querySelectorAll('.message').forEach(m=>m.remove());$('empty').hidden=messages.length>0;messages.forEach(draw);}
    function buttons(){for(const id of ['conversations','rename-conversation','import-conversations','retry'])$(id).disabled=busy;$('send').disabled=busy||!connected;$('send').hidden=busy;$('cancel').hidden=!busy;$('new').disabled=busy;$('thinking').disabled=busy;$('maximum').disabled=busy;$('prompt').disabled=busy;}
    async function models(){
      if(!loggedIn){connected=false;buttons();return;}
      try{const r=await fetch('/v1/models',{headers:{Authorization:'Bearer '+config.key}});if(!r.ok){const d=await r.json();if(d.error?.code==='login_required'){loggedIn=false;$('login-form').hidden=false;$('logout').hidden=true;$('account-status').textContent=d.error.message;}throw new Error(d.error?.message||'Serveur indisponible');}const d=await r.json();const ids=Array.isArray(d.data)?d.data.filter(m=>m&&typeof m.id==='string'&&m.id.trim()).map(m=>m.id):[];if(!ids.length)throw new Error();if(!ids.includes(config.model))config.model=ids[0];connected=true;let serverVersion='';try{const sr=await fetch('/v1/status',{headers:{Authorization:'Bearer '+config.key}});if(sr.ok){const state=await sr.json();serverVersion=state.version||'';if(state.protocol>3)throw new Error('Mettre à jour Qwen Client pour ce serveur.');}}catch(e){if(e.message.includes('Mettre à jour'))throw e;}$('model').textContent=config.model+(serverVersion?' · serveur '+serverVersion+' · client 3.0.0':'');$('connection').textContent='● Connecté au serveur IA';$('connection').classList.add('online');}
      catch(e){connected=false;config.model='';$('model').textContent='Aucun modèle accessible';$('connection').textContent=e.message||'● Serveur indisponible';$('connection').classList.remove('online');}buttons();
    }
    function delta(event,answer,view){
      const queued=event.split(/\r?\n/).find(line=>line.startsWith(': qwen-queue '));if(queued){const q=JSON.parse(queued.slice(13));$('queue-state').textContent=q.position?`En attente · position ${q.position}`:'Génération en cours';return;}
      const data=event.split(/\r?\n/).filter(line=>line.startsWith('data:')).map(line=>line.slice(5).trimStart()).join('\n');
      if(!data||data==='[DONE]')return;
      const value=JSON.parse(data);if(value.queue){$('queue-state').textContent=value.queue.position?`En attente · position ${value.queue.position}`:'Génération en cours';return;}if(value.error)throw new Error(value.error.message||'La génération a échoué.');
      const d=value.choices?.[0]?.delta||{};
      if(typeof d.content==='string')answer.content+=d.content;
      const reason=d.reasoning_content??d.reasoning;if(typeof reason==='string')answer.reasoning_content+=reason;
      save();view.content.textContent=answer.content;view.reasoning.textContent=answer.reasoning_content;view.details.hidden=!answer.reasoning_content;
      if(window.innerHeight+window.scrollY>=document.body.scrollHeight-300)window.scrollTo(0,document.body.scrollHeight);
    }
    $('composer').addEventListener('submit',async event=>{
      event.preventDefault();const text=$('prompt').value.trim();if(!text||busy||!connected)return;
      error('');messages.push({role:'user',content:text});$('prompt').value='';render();save();
      const history=messages.map(m=>({role:m.role,content:m.content,...(m.reasoning_content?{reasoning_content:m.reasoning_content}:{})}));
      const answer={role:'assistant',content:'',reasoning_content:''};messages.push(answer);const view=draw(answer);window.scrollTo(0,document.body.scrollHeight);
      busy=true;controller=new AbortController();requestId=crypto.randomUUID().replaceAll('-','');buttons();
      try{
        const response=await fetch('/v1/chat/completions',{method:'POST',headers:{Authorization:'Bearer '+config.key,'Content-Type':'application/json','X-Qwen-Request':requestId},signal:controller.signal,body:JSON.stringify({model:config.model,messages:history,stream:true,max_tokens:Number($('maximum').value),chat_template_kwargs:{enable_thinking:$('thinking').checked}})});
        if(!response.ok){let detail;try{detail=await response.json();}catch{}throw new Error(detail?.error?.message||'Le serveur a refusé la requête ('+response.status+').');}
        if(!response.headers.get('content-type')?.includes('text/event-stream')){
          const value=await response.json(),m=value.choices?.[0]?.message;if(value.error||!m)throw new Error(value.error?.message||'Réponse du serveur invalide.');answer.content=m.content||'';answer.reasoning_content=m.reasoning_content||'';view.content.textContent=answer.content;view.reasoning.textContent=answer.reasoning_content;view.details.hidden=!answer.reasoning_content;
        }else{
          const reader=response.body.getReader(),decoder=new TextDecoder();let pending='';
          while(true){const {value,done}=await reader.read();pending+=done?decoder.decode():decoder.decode(value,{stream:true});const frames=pending.split(/\r?\n\r?\n/);pending=frames.pop();for(const frame of frames)delta(frame,answer,view);if(done){if(pending.trim())delta(pending,answer,view);break;}}
        }
      }catch(e){error(e.name==='AbortError'?'Réponse interrompue.':e.message);}
      finally{$('queue-state').textContent='';if(!answer.content&&!answer.reasoning_content){messages.pop();view.article.remove();}busy=false;controller=null;save();buttons();$('prompt').focus();models();}
    });
    $('prompt').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();$('composer').requestSubmit();}});
    $('cancel').onclick=()=>{const oldController=controller,oldId=requestId;oldController?.abort();if(oldId)fetch('/v1/cancel',{method:'POST',headers:{Authorization:'Bearer '+config.key,'Content-Type':'application/json','X-Qwen-Request':oldId},body:'{}',signal:AbortSignal.timeout(5000)}).catch(()=>{});};
    $('new').onclick=()=>{if(busy)return;save();currentId=crypto.randomUUID();messages=[];library.unshift({id:currentId,title:'Conversation '+new Date().toLocaleString(),messages});save();drawLibrary();render();error('');$('prompt').focus();};
    async function api(path,body){const r=await fetch(path,{method:body?'POST':'GET',headers:{Authorization:'Bearer '+config.key,'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(20000)});const value=await r.json();if(!r.ok)throw new Error(value.error?.message||'Action refusée');return value;}
    async function clientState(){try{const state=await api('/client/state');loggedIn=state.logged_in;$('login-form').hidden=loggedIn;$('logout').hidden=!loggedIn;$('account-status').textContent=loggedIn?'Connecté : '+state.username:'Connexion au compte requise.';$('update-status').textContent=state.update.message||'';$('update-apply').disabled=busy||!loggedIn||state.update.busy||!state.update.available;$('update-check').disabled=busy||!loggedIn||state.update.busy;$('local-api').textContent=state.local_api;$('local-api-key').value=state.key;if(document.activeElement!==$('endpoint'))$('endpoint').value=state.endpoint;if(!loggedIn){connected=false;buttons();}}catch(e){error(e.message);}}
    $('login-form').onsubmit=async event=>{event.preventDefault();const password=$('password').value;$('password').value='';try{error('');await api('/client/login',{username:$('username').value,password});await clientState();await models();$('client-settings').open=false;}catch(e){error(e.message);}};
    $('logout').onclick=async()=>{try{controller?.abort();await api('/client/logout',{});await clientState();$('client-settings').open=true;}catch(e){error(e.message);}};
    $('endpoint-form').onsubmit=async event=>{event.preventDefault();try{await api('/client/endpoint',{endpoint:$('endpoint').value});await clientState();models();}catch(e){error(e.message);}};
    $('automatic').onclick=async()=>{try{await api('/client/endpoint',{});await clientState();models();}catch(e){error(e.message);}};
    $('update-check').onclick=async()=>{try{await api('/client/update/check',{});clientState();}catch(e){error(e.message);}};
    $('update-apply').onclick=async()=>{if(busy)return;try{await flushHistory();await api('/client/update/apply',{});clientState();}catch(e){error(e.message);}};
    async function bootstrap(){try{const saved=(await api('/client/history')).history;if(saved&&Array.isArray(saved.conversations)&&saved.conversations.length&&saved.conversations.every(c=>typeof c.id==='string'&&typeof c.title==='string'&&validMessages(c.messages))){library=saved.conversations;currentId=library.some(c=>c.id===saved.currentId)?saved.currentId:library[0].id;messages=library.find(c=>c.id===currentId).messages;}else save();}catch(e){error(e.message);}render();drawLibrary();await clientState();models();}
    bootstrap();setInterval(models,15000);setInterval(clientState,2000);window.addEventListener('pagehide',()=>{const c=library.find(c=>c.id===currentId);if(c)c.messages=messages;fetch('/client/history',{method:'POST',headers:{Authorization:'Bearer '+config.key,'Content-Type':'application/json'},body:JSON.stringify({history:{conversations:library,currentId}}),keepalive:true}).catch(()=>{});});
  