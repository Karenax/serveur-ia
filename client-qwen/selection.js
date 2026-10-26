'use strict';
// The same selection commands work in WebView2 and in the browser preview.
let selectionText='',selectionTarget=null;
const selectionCopy=wsElement('button',undefined,'secondary selection-copy-control');selectionCopy.id='copy-selection';selectionCopy.type='button';selectionCopy.disabled=true;selectionCopy.setAttribute('aria-label','Copier la sélection');selectionCopy.title='Copier la sélection · Ctrl+C';
selectionCopy.append(wsElement('span','⧉'),wsElement('span','Copier la sélection','selection-copy-label'));
document.querySelector('.workspace-top').insertBefore(selectionCopy,$('connection'));
const selectionStatus=wsElement('div',undefined,'selection-status');selectionStatus.id='selection-status';selectionStatus.setAttribute('role','status');document.body.append(selectionStatus);
const selectionMenu=wsElement('div',undefined,'selection-menu');selectionMenu.hidden=true;selectionMenu.setAttribute('role','menu');selectionMenu.setAttribute('aria-label','Copie de texte');
const selectionMenuCopy=wsElement('button','Copier la sélection','secondary'),selectionMenuAll=wsElement('button','Tout sélectionner dans cette zone','secondary');
for(const button of [selectionMenuCopy,selectionMenuAll]){button.type='button';button.setAttribute('role','menuitem');}
selectionMenu.append(selectionMenuCopy,selectionMenuAll);document.body.append(selectionMenu);
function selectionField(el){return el instanceof HTMLTextAreaElement||(el instanceof HTMLInputElement&&['text','search','url','tel'].includes(el.type));}
function selectionRead(){
  const el=document.activeElement;
  if(selectionField(el)&&typeof el.selectionStart==='number')return el.value.slice(el.selectionStart,el.selectionEnd);
  if(el instanceof HTMLInputElement)return '';
  const selection=window.getSelection();if(!selection?.rangeCount)return '';
  const node=selection.getRangeAt(0).commonAncestorContainer,element=node.nodeType===Node.ELEMENT_NODE?node:node.parentElement;
  if(element?.closest('[hidden]'))return '';
  return selection.toString();
}
function selectionUpdate(){if(document.activeElement===selectionCopy||(!selectionMenu.hidden&&selectionMenu.contains(document.activeElement)))return;selectionText=selectionRead();selectionCopy.disabled=!selectionText;}
function selectionClose(){selectionMenu.hidden=true;}
let selectionStatusTimer;
let copyingText=null;
document.addEventListener('copy',event=>{if(copyingText!==null&&event.clipboardData){event.clipboardData.setData('text/plain',copyingText);event.preventDefault();}});
async function copyText(text){
  copyingText=String(text);let copied=false;
  try{copied=document.execCommand('copy');}catch{}finally{copyingText=null;}
  if(!copied)await navigator.clipboard.writeText(String(text));
}
async function selectionWrite(text){
  if(!text)return;
  try{await copyText(text);selectionStatus.textContent='Sélection copiée.';}
  catch(e){selectionStatus.textContent=e.message||'Copie impossible. Réessayez avec Ctrl+C.';}
  clearTimeout(selectionStatusTimer);selectionStatusTimer=setTimeout(()=>selectionStatus.textContent='',2500);selectionClose();
}
selectionCopy.onmousedown=e=>e.preventDefault();selectionMenuCopy.onmousedown=e=>e.preventDefault();
selectionCopy.onclick=()=>selectionWrite(selectionText);selectionMenuCopy.onclick=()=>selectionWrite(selectionText);
selectionMenuAll.onclick=()=>{
  selectionClose();if(!selectionTarget?.isConnected)return;
  if(selectionField(selectionTarget)){selectionTarget.focus({preventScroll:true});selectionTarget.select();}
  else{document.activeElement?.blur();const range=document.createRange();range.selectNodeContents(selectionTarget);const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);}
  selectionUpdate();
};
for(const event of ['selectionchange','select','keyup','mouseup','focusin'])document.addEventListener(event,selectionUpdate);
/* kiara-slot:native-android-selection-handles-33 */document.addEventListener('contextmenu',event=>{
  selectionUpdate();/* /kiara-slot:native-android-selection-handles-33 */const target=event.target.closest('textarea,input,.content,.reasoning,.ws-result,.readonly-address,pre,code,p,h1,h2,h3,label,small');
  if(!selectionText&&!target)return;if(target instanceof HTMLInputElement&&!selectionField(target))return;
  event.preventDefault();event.stopImmediatePropagation();selectionTarget=target;selectionMenuCopy.disabled=!selectionText;selectionMenuAll.disabled=!target;
  selectionMenu.hidden=false;const rect=selectionMenu.getBoundingClientRect();selectionMenu.style.left=Math.max(8,Math.min(event.clientX,innerWidth-rect.width-8))+'px';selectionMenu.style.top=Math.max(8,Math.min(event.clientY,innerHeight-rect.height-8))+'px';
},true);
document.addEventListener('mousedown',e=>{if(!selectionMenu.contains(e.target))selectionClose();});
document.addEventListener('keydown',e=>{if(e.key==='Escape')selectionClose();if((e.ctrlKey||e.metaKey)&&!e.altKey&&!e.shiftKey&&e.key.toLowerCase()==='c'){const text=selectionRead();if(text){e.preventDefault();selectionWrite(text);}}});
document.addEventListener('scroll',selectionClose,true);window.addEventListener('resize',selectionClose);
const selectionOriginalShowView=showView;showView=function(name){selectionClose();selectionText='';selectionCopy.disabled=true;selectionOriginalShowView(name);};
