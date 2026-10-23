/* Qwen's immediate LAN access is independent of next-launch model settings. */
(()=>{'use strict';
  let current=null,posting=false,reading=false;
  const button=$('qwen-lan-toggle'),card=$('qwen-lan-card');
  function render(value){
    current=value;
    const busy=posting||value.pending;
    card.setAttribute('aria-busy',String(busy));
    $('qwen-lan-status').textContent=value.message;
    $('qwen-lan-error').textContent=value.error||'';
    $('qwen-lan-error').hidden=!value.error;
    $('qwen-lan-url').value=value.base_url;
    $('qwen-lan-model').value=value.model;
    $('qwen-lan-subnet').value=value.subnet;
    button.textContent=busy?'Modification en cours…':value.can_disable?'Couper l’accès local':'Activer l’accès local';
    button.className='button '+(value.can_disable?'stop':'primary');
    button.disabled=busy||['unknown','conflict'].includes(value.state);
    $('qwen-lan-copy').disabled=false;
    $('qwen-lan-copy-url').disabled=false;
  }
  async function refresh(){
    if(reading)return;reading=true;
    try{render(await request('/api/local-network'));}
    catch(error){
      current=null;button.disabled=true;button.textContent='Accès local indisponible';
      $('qwen-lan-status').textContent='Impossible de lire l’accès local. Nouvelle tentative automatique.';
      $('qwen-lan-error').textContent=error.message;$('qwen-lan-error').hidden=false;
      card.setAttribute('aria-busy','false');
    }finally{reading=false;}
  }
  button.onclick=async()=>{
    if(posting||!current||current.pending)return;
    const enabled=!current.can_disable;
    posting=true;render(current);
    try{const result=await request('/api/local-network',{enabled});toast(result.message);}
    catch(error){toast(error.message,true);}
    finally{posting=false;await refresh();}
  };
  async function copySettings(text){
    try{
      await navigator.clipboard.writeText(text);
      $('qwen-lan-copy-status').textContent='Copié.';
    }catch{
      $('qwen-lan-copy-status').textContent='Copie impossible. Sélectionnez l’adresse ou le modèle pour les copier.';
    }
  }
  $('qwen-lan-copy-url').onclick=()=>current&&copySettings(current.base_url);
  $('qwen-lan-copy').onclick=()=>current&&copySettings(`API compatible OpenAI\nAdresse de base : ${current.base_url}\nModèle : ${current.model}\nClé API : aucune (local si obligatoire)\nRéseau autorisé : ${current.subnet}`);
  refresh();setInterval(refresh,3000);
})();
