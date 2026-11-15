/* Agent permissions are administered locally, per existing Kiara client. */
(() => {
  const open=document.getElementById('agent-access-open'), panel=document.getElementById('agent-access-panel');
  const node=(tag,text)=>{const item=document.createElement(tag);if(text)item.textContent=text;return item;};
  const option=(value,text)=>{const item=node('option',text);item.value=value;return item;};
  const field=(label,input)=>{const box=node('div');box.className='field';const title=node('label',label);title.htmlFor=input.id;box.append(title,input);return box;};
  let sequence=0;

  async function show(){
    const ticket=++sequence;
    panel.hidden=false;panel.replaceChildren();
    const status=node('p','Lecture des accès Agent…');status.setAttribute('role','status');panel.append(status);
    try{
      const service=await request('/api/agent-service');
      if(ticket!==sequence)return;
      if(!service.configured){status.textContent=service.configuration_error||'Le service Agent n’est pas encore configuré.';return;}
      const running=service.running;
      if(!running){
        const start=node('button','Démarrer Agent');start.type='button';start.className='button secondary';panel.append(start);
        start.onclick=async()=>{start.disabled=true;status.textContent='Démarrage d’Agent…';try{await request('/api/agent-service',{action:'start'});await show();}catch(error){status.textContent=error.message;start.disabled=false;}};
      }
      if(running){
        const enable=node('button','Activer les réunions');enable.type='button';enable.className='button secondary';
        const notice=node('p');notice.setAttribute('role','status');
        panel.append(enable,notice);
        enable.onclick=async()=>{
          enable.disabled=true;notice.textContent='Activation des réunions…';
          try{
            await request('/api/agent-service',{action:'enable-meetings'});
            notice.textContent='Les réunions sont activées dans Kiara.';
          }catch(error){
            notice.textContent=error.message;enable.disabled=false;
          }
        };
      }
      const [catalogue,remote]=await Promise.all([running?request('/api/agent-service/catalogue'):Promise.resolve({projects:[],sessions:[]}),request('/api/remote')]);
      if(ticket!==sequence)return;
      const unlinked=catalogue.projects.filter(project=>project.knowledge_linked===false);
      if(unlinked.length){
        const choice=node('select');choice.id='agent-knowledge-project';
        const link=node('button','Relier à la base de connaissances');link.type='button';link.className='button secondary';link.disabled=true;
        const notice=node('p');notice.setAttribute('role','status');
        choice.append(option('','Choisir un projet…'));
        for(const project of unlinked)choice.append(option(project.id,[project.code,project.title].filter(Boolean).join(' · ')));
        choice.onchange=()=>{link.disabled=!choice.value;};
        link.onclick=async()=>{
          const projectId=choice.value;
          if(!projectId)return;
          choice.disabled=true;link.disabled=true;notice.textContent='Liaison du projet…';
          try{
            await request('/api/agent-service',{action:'link-project-knowledge',project_id:projectId});
            const selected=[...choice.options].find(item=>item.value===projectId);
            if(selected)selected.remove();
            choice.value='';
            notice.textContent='Le projet est relié à la base de connaissances.';
          }catch(error){notice.textContent=error.message;}
          finally{choice.disabled=choice.options.length<2;link.disabled=!choice.value;}
        };
        panel.append(field('Projet sans base de connaissances',choice),link,notice);
      }
      const clients=remote.clients.filter(client=>!client.revoked&&!client.suspended);
      if(!clients.length){status.textContent='Aucun client actif. Ajoutez un client pour lui donner accès à Agent.';return;}
      const thunderbird=node('form'), device=node('select'), saveDevice=node('button','Enregistrer le poste'), deviceStatus=node('p');
      device.id='agent-thunderbird-device';device.append(option('','Aucun poste'));
      for(const value of clients)device.append(option(value.id,value.name));
      if(service.thunderbird_device && !clients.some(value=>value.id===service.thunderbird_device)){
        device.append(option(service.thunderbird_device,'Poste indisponible'));
      }
      device.value=service.thunderbird_device||'';
      saveDevice.type='submit';saveDevice.className='button secondary';
      deviceStatus.setAttribute('role','status');
      thunderbird.append(field('Poste Thunderbird',device),saveDevice,deviceStatus);
      thunderbird.onsubmit=async event=>{
        event.preventDefault();device.disabled=true;saveDevice.disabled=true;
        try{
          await request('/api/agent-service',{action:'thunderbird-device',owner:device.value||null});
          deviceStatus.textContent=device.value?'Poste Thunderbird enregistré.':'Liaison Thunderbird retirée.';
        }catch(error){deviceStatus.textContent=error.message;}
        finally{device.disabled=false;saveDevice.disabled=false;}
      };
      if('thunderbird_device' in service)panel.append(thunderbird);
      status.textContent=running?'Choisissez un client pour consulter ou modifier ses droits.':service.startup_error||'Agent est arrêté. Vous pouvez retirer un accès ou démarrer Agent pour modifier les droits.';
      const form=node('form'),client=node('select'),role=node('select'),all=node('input'),projects=node('fieldset'),session=node('select');
      let currentPolicy=null;
      client.id='agent-access-client';client.append(option('','Choisir un client…'));
      for(const value of clients)client.append(option(value.id,value.name));
      role.id='agent-access-role';role.append(option('none','Aucun accès'),option('reader','Lecture'),option('editor','Modification'),option('owner','Propriétaire'));
      if(!running)for(const item of role.options)if(item.value!=='none')item.disabled=true;
      all.id='agent-access-all';all.type='checkbox';
      const allLabel=node('label','Accès à tous les projets');allLabel.htmlFor=all.id;
      const allRow=node('div');allRow.className='agent-all-projects';allRow.append(all,allLabel);
      projects.className='agent-project-list';
      projects.append(node('legend','Projets autorisés'));
      const boxes=[];
      for(const [index,project] of catalogue.projects.entries()){
        const input=node('input'),label=node('label'),row=node('div');input.type='checkbox';input.id='agent-project-'+index;input.value=project.id;
        row.className='agent-project-option';label.htmlFor=input.id;label.textContent=[project.code,project.title].filter(Boolean).join(' · ');row.append(input,label);projects.append(row);boxes.push(input);
      }
      if(!boxes.length)projects.append(node('p','Aucun projet Agent disponible.'));
      session.id='agent-access-session';
      const populateSessions=actor=>{
        session.replaceChildren(option('','Aucune association'));
        for(const item of catalogue.sessions){
          const label=[item.title||'Séance sans titre',item.date||'',item.audio_chunks?`${item.audio_chunks} fragments audio`:''].filter(Boolean).join(' · ');
          session.append(option(item.operator_id,label));
        }
        if(actor&&![...session.options].some(item=>item.value===actor))session.append(option(actor,'Correspondance existante'));
        session.value=actor;
      };
      populateSessions('');
      const hint=node('p','Associer une séance donne aussi accès aux autres séances personnelles du même ancien utilisateur. Cet accès demande l’autorisation sur tous les projets.');hint.className='muted';
      if(catalogue.sessions_truncated)hint.textContent+=' Seules les 1 000 séances les plus récentes sont proposées.';
      const roleHint=node('p','L’administration d’Agent nécessite le rôle propriétaire et l’accès à tous les projets.');roleHint.className='muted';
      const details=node('div');details.hidden=true;details.append(field('Niveau d’accès',role),roleHint,allRow,projects,field('Séance personnelle à retrouver',session),hint);
      const save=node('button','Enregistrer les droits');save.className='button primary';save.type='submit';details.append(save);
      form.append(field('Client',client),details);panel.append(form);
      const refreshVisibility=()=>{const enabled=running&&role.value!=='none',hasSessions=session.options.length>1;roleHint.hidden=!enabled;allRow.hidden=!enabled;projects.hidden=!enabled||all.checked;session.parentElement.hidden=!enabled||!hasSessions;hint.hidden=!enabled||!hasSessions;};
      all.onchange=refreshVisibility;role.onchange=refreshVisibility;
      client.onchange=async()=>{
        const current=++sequence;
        details.hidden=true;if(!client.value)return;
        status.textContent='Lecture des droits…';
        try{
          const result=await request('/api/agent-service?owner='+encodeURIComponent(client.value));
          if(current!==sequence)return;
          const policy=result.operator;
          currentPolicy=policy;
          form.dataset.personId=policy?.person_id||'';
          role.value=policy?.role||'none';all.checked=!!policy&&policy.project_ids===null;
          for(const box of boxes)box.checked=Array.isArray(policy?.project_ids)&&policy.project_ids.includes(box.value);
          const actor=policy?.id&&policy.id!==client.value?policy.id:'';
          populateSessions(actor);details.hidden=false;refreshVisibility();
          status.textContent=policy?(running?'Droits actuels chargés.':'Agent est arrêté. Choisissez « Aucun accès » pour retirer ces droits.'):'Ce client n’a pas accès à Agent.';
        }catch(error){if(current===sequence)status.textContent=error.message;}
      };
      form.onsubmit=async event=>{
        event.preventDefault();if(!client.value)return;
        if(!running&&role.value!=='none'){status.textContent='Démarrez Agent pour modifier les droits ; vous pouvez les retirer dès maintenant.';return;}
        if(role.value!=='none'&&session.value&&!all.checked){status.textContent='Pour retrouver une séance personnelle, autorisez tous les projets.';return;}
        save.disabled=true;client.disabled=true;role.disabled=true;all.disabled=true;session.disabled=true;
        for(const box of boxes)box.disabled=true;
        try{
          const payload=role.value==='none'?{action:'revoke',owner:client.value,expected:currentPolicy}:{action:'access',owner:client.value,role:role.value,
            project_ids:all.checked?null:boxes.filter(box=>box.checked).map(box=>box.value),person_id:form.dataset.personId||null,
            agent_operator_id:session.value||null,expected:currentPolicy};
          await request('/api/agent-service',payload);
          currentPolicy=payload.action==='revoke'?null:{id:payload.agent_operator_id||payload.owner,role:payload.role,
            project_ids:payload.project_ids,person_id:payload.person_id};
          status.textContent=role.value==='none'?'Accès à Agent retiré.':'Droits Agent enregistrés.';
        }catch(error){status.textContent=error.message;}finally{save.disabled=false;client.disabled=false;role.disabled=false;all.disabled=false;session.disabled=false;for(const box of boxes)box.disabled=false;}
      };
    }catch(error){if(ticket===sequence)status.textContent=error.message;}
  }
  open.onclick=()=>{if(!panel.hidden){sequence++;panel.hidden=true;open.textContent='Configurer Agent';return;}open.textContent='Fermer';void show();};
})();
