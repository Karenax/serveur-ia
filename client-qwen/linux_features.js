/* Linux capabilities: keep unsupported Windows installers out of this build. */
(()=>{
  // Desktop portals may return the whole screen even when interaction was requested.
  // Crop locally and explicitly before the existing voice attachment preview.
  window.kiaraSelectLinuxCapture=async function(url){
    const image=new Image();
    await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=()=>reject(new Error('La capture ne peut pas être affichée.'));image.src=url;});
    return new Promise((resolve,reject)=>{
      const dialog=document.createElement('dialog');dialog.className='fred-source-dialog';dialog.setAttribute('aria-labelledby','linux-capture-title');
      dialog.style.maxWidth='960px';
      const heading=document.createElement('h2');heading.id='linux-capture-title';heading.textContent='Choisir la zone à joindre';
      const help=document.createElement('p');help.textContent='Le bureau peut capturer tout l’écran et en conserver une copie locale. Tracez une zone ou indiquez ses coordonnées, puis vérifiez l’aperçu avant votre question.';
      const canvas=document.createElement('canvas');canvas.width=image.naturalWidth;canvas.height=image.naturalHeight;
      canvas.style.maxWidth='100%';canvas.style.maxHeight='45vh';canvas.style.display='block';canvas.style.margin='auto';canvas.style.cursor='crosshair';canvas.style.touchAction='none';
      canvas.setAttribute('aria-label','Aperçu de la capture : tracez une zone avec la souris ou utilisez les coordonnées ci-dessous.');
      const fields=document.createElement('div');fields.style.display='flex';fields.style.flexWrap='wrap';fields.style.gap='12px';fields.style.marginTop='12px';
      const inputs={};
      for(const [key,label,value] of [['left','Gauche',0],['top','Haut',0],['width','Largeur',canvas.width],['height','Hauteur',canvas.height]]){
        const wrapper=document.createElement('label');wrapper.textContent=label+' ';
        const input=document.createElement('input');input.type='number';input.min='0';input.step='1';input.value=String(value);input.style.width='84px';
        inputs[key]=input;wrapper.append(input);fields.append(wrapper);
      }
      const status=document.createElement('p');status.setAttribute('role','status');status.setAttribute('aria-live','polite');
      const actions=document.createElement('div');actions.style.display='flex';actions.style.gap='10px';actions.style.flexWrap='wrap';
      const cancel=document.createElement('button');cancel.type='button';cancel.className='secondary';cancel.textContent='Annuler';
      const confirm=document.createElement('button');confirm.type='button';confirm.textContent='Utiliser cette zone';actions.append(cancel,confirm);
      dialog.append(heading,help,canvas,fields,status,actions);document.body.append(dialog);
      let finished=false,start=null;
      const finish=value=>{if(finished)return;finished=true;dialog.close();dialog.remove();image.src='';resolve(value);};
      const rectangle=()=>{
        const box=Object.fromEntries(Object.entries(inputs).map(([key,input])=>[key,Number(input.value)]));
        if(Object.values(box).some(value=>!Number.isSafeInteger(value))||box.left<0||box.top<0||box.width<8||box.height<8||box.left+box.width>canvas.width||box.top+box.height>canvas.height)return null;
        return box;
      };
      const draw=()=>{const context=canvas.getContext('2d');context.drawImage(image,0,0);const box=rectangle();if(box){context.strokeStyle='#00d4ff';context.lineWidth=Math.max(2,Math.ceil(Math.max(canvas.width,canvas.height)/500));context.strokeRect(box.left,box.top,box.width,box.height);}};
      const point=event=>{const rect=canvas.getBoundingClientRect();return {x:Math.max(0,Math.min(canvas.width,Math.round((event.clientX-rect.left)*canvas.width/rect.width))),y:Math.max(0,Math.min(canvas.height,Math.round((event.clientY-rect.top)*canvas.height/rect.height)))};};
      const select=end=>{const left=Math.min(start.x,end.x),top=Math.min(start.y,end.y);inputs.left.value=String(left);inputs.top.value=String(top);inputs.width.value=String(Math.abs(end.x-start.x));inputs.height.value=String(Math.abs(end.y-start.y));draw();};
      canvas.addEventListener('pointerdown',event=>{if(event.button!==0)return;event.preventDefault();start=point(event);canvas.setPointerCapture(event.pointerId);});
      canvas.addEventListener('pointermove',event=>{if(start)select(point(event));});
      canvas.addEventListener('pointerup',event=>{if(!start)return;select(point(event));start=null;status.textContent=rectangle()?'Zone sélectionnée.':'Choisissez une zone d’au moins 8 pixels de côté.';});
      canvas.addEventListener('pointercancel',()=>{start=null;});
      for(const input of Object.values(inputs))input.addEventListener('input',draw);
      cancel.addEventListener('click',()=>finish(null));dialog.addEventListener('cancel',event=>{event.preventDefault();finish(null);});
      confirm.addEventListener('click',()=>{
        const box=rectangle();if(!box){status.textContent='Choisissez une zone valide d’au moins 8 pixels de côté.';return;}
        try{const cropped=document.createElement('canvas');cropped.width=box.width;cropped.height=box.height;cropped.getContext('2d').drawImage(image,box.left,box.top,box.width,box.height,0,0,box.width,box.height);
          const selected=cropped.toDataURL('image/jpeg',.82);if(selected.length>2700000)throw new Error('Choisissez une zone plus petite.');finish(selected);
        }catch(error){status.textContent=error.message||'La sélection ne peut pas être préparée.';}
      });
      try{draw();dialog.showModal();}catch(error){dialog.remove();image.src='';reject(error);}
    });
  };
  const updates=document.querySelector('[data-view="updates"]');
  if(updates){
    const title=document.createElement('h2');title.textContent='Mises à jour';
    const message=document.createElement('p');
    message.textContent='Pour mettre Kiara à jour, fermez l’application et installez le nouveau paquet Linux fourni par votre administrateur. Vos conversations sont conservées.';
    // Keep state targets used by the shared polling code, without actionable EXE controls.
    for(const id of ['update-status','update-check','update-apply']){
      const element=document.getElementById(id);if(element)element.hidden=true;
    }
    updates.querySelectorAll('h2,p,small,h3').forEach(element=>{element.hidden=true;});
    updates.prepend(title,message);
  }
  const execution=document.getElementById('voice-execution');
  if(execution){
    execution.value='server';
    for(const option of execution.options)option.disabled=option.value!=='server';
  }
  const testMax=document.getElementById('voice-test-max');
  if(testMax)testMax.textContent='Tester le serveur';
  const theme=document.querySelector('#ui-theme option[value="system"]');
  if(theme)theme.textContent='Comme le système';
  const font=document.querySelector('#ui-font option[value="system"]');
  if(font){font.textContent='Moderne · Système';if(typeof uiFonts!=='undefined'&&uiFonts.system)uiFonts.system.label='Moderne · Système';}
  const access=[...document.querySelectorAll('[data-view="access"] .settings-card small')].find(node=>node.textContent.includes('EXE'));
  if(access)access.textContent='Votre accès est personnel. Le serveur peut le suspendre, limiter sa validité ou le révoquer. Ne partagez pas le fichier fourni par votre administrateur.';
  const connection=document.getElementById('connection-diagnostic')?.closest('.settings-card')?.querySelector('small');
  if(connection)connection.textContent='Utilisez un accès distinct pour chaque appareil connecté en même temps. Deux appareils partageant le même accès peuvent interrompre leurs connexions.';
  const automaticHint=document.getElementById('endpoint')?.nextElementSibling;
  if(automaticHint?.tagName==='SMALL')automaticHint.textContent='En mode WireGuard, Automatique utilise l’adresse prévue dans votre accès personnel.';
  const previousClientState=clientState;
  clientState=async function(){await previousClientState();document.getElementById('account-status').textContent='Accès personnel · Linux';};
  document.getElementById('account-status').textContent='Accès personnel · Linux';
})();
