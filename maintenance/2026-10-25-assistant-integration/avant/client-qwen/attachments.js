'use strict';
let chatAttachments=[],attachmentLoading=false,chatCapabilities={images:false,files:[]};
const attachmentRow=document.createElement('div');attachmentRow.id='chat-attachments';attachmentRow.className='chat-attachments';
const attachmentTools=document.createElement('div');attachmentTools.className='attachment-tools';
attachmentTools.innerHTML='<button id="attach-file" type="button" aria-label="Joindre un document">+</button><span id="attachment-help" class="sr-only" role="status"></span><input id="chat-file-input" type="file" multiple hidden>';
document.querySelector('.send-row').prepend(attachmentTools);
document.querySelector('.input-box').before(attachmentRow);
function attachmentValid(m){
  if(m.attachments===undefined)return true;
  return m.role==='user'&&Array.isArray(m.attachments)&&m.attachments.length<=4&&m.attachments.every(a=>a&&typeof a.name==='string'&&a.name.length>0&&a.name.length<=180&&(a.kind==='file'?typeof a.text==='string'&&a.text.length>0&&a.text.length<=50000:a.kind==='image'&&typeof a.url==='string'&&a.url.length<=2800000&&/^data:image\/(png|jpeg|webp);base64,[A-Za-z0-9+/]+=*$/.test(a.url)));
}
function chatRequestContent(m){
  const files=(m.attachments||[]).filter(a=>a.kind==='file');
  const text=m.content+files.map(a=>'\n\n--- Fichier joint : '+a.name+' ---\n'+a.text+'\n--- Fin du fichier ---').join('');
  const images=(m.attachments||[]).filter(a=>a.kind==='image');
  return images.length?[{type:'text',text:text||'Analyse les images jointes.'},...images.map(a=>({type:'image_url',image_url:{url:a.url}}))]:text;
}
function attachmentDraw(container,items){
  const group=document.createElement('div');group.className='chat-attachments';
  for(const item of items){const chip=document.createElement('div');chip.className='attachment-chip';
    if(item.kind==='image'&&attachmentValid({role:'user',attachments:[item]})){const img=document.createElement('img');img.src=item.url;img.alt=item.name;chip.append(img);}
    const label=document.createElement('span');label.textContent=item.name;chip.append(label);group.append(chip);
  }container.append(group);return group;
}
function attachmentRender(){
  attachmentRow.replaceChildren();const group=attachmentDraw(attachmentRow,chatAttachments);
  [...group.children].forEach((chip,index)=>{const b=document.createElement('button');b.type='button';b.textContent='×';b.setAttribute('aria-label','Retirer '+chatAttachments[index].name);b.disabled=attachmentLoading||busy;b.onclick=()=>{chatAttachments.splice(index,1);attachmentRender();};chip.append(b);});attachmentButtons();
}
function attachmentCapabilities(value){chatCapabilities={images:value.images===true,files:Array.isArray(value.files)?value.files.filter(x=>['txt','md','pdf','docx'].includes(x)):[]};$('chat-file-input').accept=[...chatCapabilities.files.map(x=>'.'+x),...(chatCapabilities.images?['image/png','image/jpeg','image/webp']:[])].join(',');attachmentButtons();}
function attachmentButtons(){
  const locked=busy||attachmentLoading||conversationLocked()||!connected||!conversationModelAvailable();
  $('attach-file').disabled=locked||(!chatCapabilities.files.length&&!chatCapabilities.images);
  $('attach-file').setAttribute('aria-label',chatCapabilities.images?'Joindre un document ou une image':'Joindre un document');
  $('attach-file').title='Joindre un document'+(chatCapabilities.images?' ou une image':'')+' · '+chatCapabilities.files.join(', ').toUpperCase()+' · 2 Mo par fichier';
  $('attachment-help').textContent=attachmentLoading?'Lecture du fichier…':!connected?'Connectez-vous pour joindre des fichiers.':chatCapabilities.images?'Fichiers et images · 2 Mo chacun · 4 pièces maximum':'TXT, Markdown, PDF texte, Word · 2 Mo · Images indisponibles sur ce modèle';
  if(attachmentLoading)$('send').disabled=true;
}
function readAttachment(file){return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(new Error('Lecture du fichier impossible.'));reader.readAsDataURL(file);});}
async function attachmentSelect(input){
  if(attachmentLoading||busy)return;
  const files=[...input.files];input.value='';if(!files.length)return;
  attachmentLoading=true;window.chatAttachmentLoading=true;buttons();drawLibrary();attachmentButtons();
  try{
    if(chatAttachments.length+files.length>4)throw new Error('Maximum quatre pièces jointes par message.');
    const incoming=[];
    for(const file of files){
      const images=file.type.startsWith('image/')||/\.(png|jpe?g|webp)$/i.test(file.name);
      if(!file.size||file.size>2*1024*1024)throw new Error(file.name+' : fichier vide ou supérieur à 2 Mo.');
      if(file.name.length>180)throw new Error('Nom de fichier trop long.');
      if(images&&!chatCapabilities.images)throw new Error('Le modèle chargé ne prend pas en charge les images.');
      if(images&&!['image/png','image/jpeg','image/webp'].includes(file.type))throw new Error('Image PNG, JPEG ou WebP attendue.');
      if(!images&&!chatCapabilities.files.includes(file.name.split('.').pop().toLowerCase()))throw new Error('Formats acceptés : '+chatCapabilities.files.join(', '));
      const data=await readAttachment(file);
      if(images)incoming.push({kind:'image',name:file.name,url:data});
      else{const result=await api('/v1/workspace/action',{action:'attachment_extract',title:file.name,data:data.split(',')[1]});incoming.push({kind:'file',name:file.name,text:result.text});}
    }
    if(new TextEncoder().encode(JSON.stringify([...chatAttachments,...incoming])).length>6*1024*1024)throw new Error('Pièces jointes trop volumineuses : maximum 6 Mo encodés par message.');
    chatAttachments.push(...incoming);error('');
  }catch(e){error(e);}finally{attachmentLoading=false;window.chatAttachmentLoading=false;attachmentRender();buttons();drawLibrary();}
}
$('attach-file').onclick=()=>$('chat-file-input').click();
$('chat-file-input').onchange=()=>attachmentSelect($('chat-file-input'));
$('connection-choice').addEventListener('cancel',event=>event.preventDefault());
async function chooseConnection(endpoint){
  $('choose-https').disabled=$('choose-wireguard').disabled=true;
  try{await api('/client/endpoint',{endpoint});$('connection-choice').close();endpointDirty=false;await clientState();await models();}
  catch(e){$('connection-choice-error').textContent=e.message;}
  finally{$('choose-https').disabled=$('choose-wireguard').disabled=false;}
}
$('choose-https').onclick=()=>chooseConnection('https://ia.karenax.net');$('choose-wireguard').onclick=()=>chooseConnection(null);
attachmentRender();
