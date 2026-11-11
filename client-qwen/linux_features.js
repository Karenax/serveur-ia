/* Linux capabilities: keep unsupported Windows installers out of this build. */
(()=>{
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
  const capture=document.getElementById('voice-image-capture');
  if(capture)capture.hidden=true;
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
