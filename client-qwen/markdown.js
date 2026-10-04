'use strict';
const fredMarkdown = markdownit({html:false, linkify:false, breaks:false, typographer:false});
// Only explicit web links are clickable. Images never trigger remote requests.
fredMarkdown.validateLink = url => /^https?:\/\//i.test(url);
fredMarkdown.renderer.rules.image = (tokens, index) => fredMarkdown.utils.escapeHtml('[Image : '+(tokens[index].content||'image')+']');
const fredLink = fredMarkdown.renderer.rules.link_open || ((tokens,index,options,env,self)=>self.renderToken(tokens,index,options));
fredMarkdown.renderer.rules.link_open = (tokens,index,options,env,self) => {
  tokens[index].attrSet('target','_blank');
  tokens[index].attrSet('rel','noopener noreferrer');
  return fredLink(tokens,index,options,env,self);
};
fredMarkdown.renderer.rules.table_open=()=>'<div class="markdown-table"><table>\n';
fredMarkdown.renderer.rules.table_close=()=>'</table></div>\n';
const markdownFrames=new WeakMap();
function queueMarkdown(element,text){
  let frame=markdownFrames.get(element);
  if(frame){frame.text=text;return;}
  frame={text};markdownFrames.set(element,frame);
  setTimeout(()=>{markdownFrames.delete(element);if(element.isConnected)renderMarkdown(element,frame.text);},100);
}
function renderMarkdown(element, text) {
  // HTML is disabled in the parser, code and raw tags are escaped, URLs are validated.
  element.innerHTML=fredMarkdown.render(text||'');
  element.classList.add('markdown');
  for (const pre of element.querySelectorAll('pre')) {
    const code=pre.querySelector('code'), toolbar=document.createElement('div');
    toolbar.className='code-toolbar';
    const language=document.createElement('span');
    language.textContent=[...code.classList].find(c=>c.startsWith('language-'))?.slice(9)||'Code';
    const copy=document.createElement('button');copy.type='button';copy.textContent='Copier';
    copy.setAttribute('aria-label','Copier le bloc de code');
    copy.onclick=async()=>{try{await navigator.clipboard.writeText(code.textContent);copy.textContent='Copié';setTimeout(()=>copy.textContent='Copier',1500);}catch{copy.textContent='Sélectionnez le code';}};
    toolbar.append(language,copy);pre.prepend(toolbar);
  }
}
