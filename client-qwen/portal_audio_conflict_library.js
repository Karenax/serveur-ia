/* Experimental read-only access to audio copies retained during recovery. */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else api.install(root).catch(() => {});
})(globalThis, function () {
  'use strict';
  function node(document, tag, text, className) {
    const result = document.createElement(tag);
    if (text !== undefined) result.textContent = text;
    if (className) result.className = className;
    return result;
  }
  function label(item, index) {
    const meta = item.incoming.meta;
    const track = ['mic','microphone'].includes(meta.track) ? 'microphone' : meta.track === 'system' ? 'audio système' : 'audio';
    const date = new Date(meta.created_at);
    const when = Number.isNaN(date.getTime()) ? '' : ` — ${new Intl.DateTimeFormat('fr-FR',
      {dateStyle:'short',timeStyle:'short'}).format(date)}`;
    return `Fragment ${index + 1} — ${track}${when}`;
  }
  function extension(mime) {
    const type = mime.toLowerCase().split(';', 1)[0].trim();
    return ({'audio/wav':'wav','audio/wave':'wav','audio/x-wav':'wav','audio/webm':'webm',
      'audio/ogg':'ogg','audio/mpeg':'mp3','audio/mp4':'m4a','audio/flac':'flac'})[type] || 'bin';
  }

  async function install(root) {
    const {document,indexedDB,kiaraPortalAudioConflictArchive:archive} = root;
    if (!document || !indexedDB || !archive || !root.URL || typeof root.URL.createObjectURL !== 'function'
        || typeof root.URL.revokeObjectURL !== 'function' || typeof root.Blob !== 'function')
      throw new Error('Copies audio indisponibles.');
    const host = document.querySelector('.chat-view');
    if (!host) return false;
    let count = 0, unavailable = false;
    try {
      const initial = await archive.open(indexedDB,{allowMissing:true});
      if (initial) {
        try {
          const keys = await initial.keys();
          if (!Array.isArray(keys) || keys.length > 3000) throw new Error();
          count = keys.length;
        } finally {initial.close();}
      }
    }
    catch {unavailable = true;}
    if (!count && !unavailable) return false;

    const banner = node(document,'div',undefined,'kiara-conflict-banner');
    const bannerText = node(document,'span',unavailable ? 'Les copies audio ne peuvent pas être vérifiées.' : 'Des fragments audio ont été conservés.');
    bannerText.setAttribute('role','status');banner.append(bannerText);
    const trigger = node(document,'button','Consulter les audios','secondary');trigger.type='button';banner.append(trigger);host.prepend(banner);
    const dialog = node(document,'dialog',undefined,'kiara-conflict-dialog');
    dialog.setAttribute('aria-labelledby','kiara-audio-library-title');
    const header = node(document,'div',undefined,'kiara-conflict-heading');
    const title = node(document,'h2','Fragments audio conservés');title.id='kiara-audio-library-title';
    const close = node(document,'button','Fermer','secondary');close.type='button';header.append(title,close);
    const info = node(document,'p','Ces copies datent de la récupération. Vous pouvez les écouter ou les télécharger ; elles ne modifient pas votre travail en cours.');
    const status = node(document,'p','','kiara-conflict-status');status.setAttribute('role','status');
    const content = node(document,'div',undefined,'kiara-conflict-content');
    dialog.append(header,info,status,content);document.body.append(dialog);
    let generation=0,selection=0,objectUrls=[];
    const release=()=>{for(const url of objectUrls.splice(0))root.URL.revokeObjectURL(url);};
    close.addEventListener('click',()=>dialog.close());
    dialog.addEventListener('close',()=>{generation++;selection++;release();content.replaceChildren();status.textContent='';trigger.focus();});

    trigger.addEventListener('click',async()=>{
      if(dialog.open)return;
      const run=++generation;content.replaceChildren();status.textContent='Chargement des copies…';
      try {dialog.showModal();} catch {bannerText.textContent='Impossible d’ouvrir les copies audio.';return;}
      close.focus();
      try {
        const store=await archive.open(indexedDB);
        let copies;
        try {copies=await archive.list(store);} finally {store.close();}
        if(run!==generation || !dialog.open)return;
        bannerText.textContent='Des fragments audio ont été conservés.';
        if(!copies.length){status.textContent='Aucune copie audio conservée sur cet appareil.';return;}
        const field=node(document,'label','Fragment à consulter','kiara-conflict-label');
        const select=document.createElement('select');select.setAttribute('aria-label','Fragment à consulter');
        copies.forEach((item,index)=>{const option=document.createElement('option');option.value=String(index);
          option.textContent=label(item,index);select.append(option);});
        field.append(select);
        const versions=node(document,'div',undefined,'kiara-conflict-versions');content.append(field,versions);
        const render=async()=>{
          const chosen=++selection;release();versions.replaceChildren();status.textContent='Vérification du fragment…';
          let pending=[];
          try {
            const item=copies[Number(select.value)];if(!item)throw new Error();
            const db=await archive.open(indexedDB);let copy;
            try {copy=await archive.read(db,item.id);} finally {db.close();}
            if(run!==generation || chosen!==selection || !dialog.open)return;
            const sections=[];
            for(const [heading,value,name] of [['Version présente à la récupération',copy.current,'version-presente'],
                                                ['Autre version conservée',copy.incoming,'autre-version']]) {
              const section=node(document,'section',undefined,'kiara-conflict-version');section.append(node(document,'h3',heading));
              const mime=/^audio\/[a-z0-9.+-]+(?:\s*;[^\r\n]*)?$/i.test(value.mime) ? value.mime : 'application/octet-stream';
              const url=root.URL.createObjectURL(new root.Blob([value.bytes],{type:mime}));pending.push(url);
              const player=document.createElement('audio');player.controls=true;player.preload='none';
              player.setAttribute('aria-label',heading);player.src=url;section.append(player);
              const download=node(document,'a','Télécharger ce fragment','kiara-audio-download');
              download.href=url;download.download=`${name}.${extension(mime)}`;section.append(download);sections.push(section);
            }
            objectUrls=pending;pending=[];versions.replaceChildren(...sections);status.textContent='';
          } catch {
            for(const url of pending)root.URL.revokeObjectURL(url);
            if(run!==generation || chosen!==selection || !dialog.open)return;
            versions.replaceChildren();status.textContent='Impossible de lire cette copie. Elle reste conservée sur cet appareil.';
          }
        };
        select.addEventListener('change',()=>{void render();});await render();
      } catch {
        if(run!==generation || !dialog.open)return;
        content.replaceChildren();status.textContent='Impossible de lire les copies audio. Elles restent conservées sur cet appareil.';
      }
    });
    return true;
  }
  return {install};
});
