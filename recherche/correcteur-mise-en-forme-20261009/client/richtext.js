'use strict';
// Rich formatting stays in the client. The model receives only identified text fragments.
const FredRichText=(()=>{
  const MAX_TEXT=100000,MAX_HTML=750000,MAX_FRAGMENTS=1500;
  const tags=new Set('p div span b strong i em u s strike sub sup br h1 h2 h3 h4 h5 h6 ul ol li blockquote pre a table thead tbody tfoot tr td th hr'.split(' '));
  const discard=new Set('script style link meta base img iframe object embed svg math video audio source input button textarea select canvas noscript'.split(' '));
  const properties=['font-family','font-size','font-weight','font-style','font-variant','color','background-color','text-decoration','text-decoration-color','text-align','line-height','white-space','vertical-align','margin-top','margin-bottom','margin-left','margin-right','padding-left','padding-right','padding-top','padding-bottom','border-top','border-bottom','border-left','border-right','border-collapse','list-style-type','text-indent'];
  function applyStyle(target,style){
    for(const property of properties){
      const value=style.getPropertyValue(property);
      if(value&&value.length<=250&&!/url\s*\(|expression\s*\(|var\s*\(|[\\<>]|@import/i.test(value))target.style.setProperty(property,value);
    }
  }
  function sanitize(html){
    if(typeof html!=='string'||html.length>MAX_HTML)throw new Error('La mise en forme est trop volumineuse (750 000 caractères maximum).');
    const template=document.createElement('template');template.innerHTML=html;
    const rules=[];
    // Word/Outlook often supply local class rules in addition to inline styles.
    for(const style of template.content.querySelectorAll('style')){
      if(style.textContent.length>100000)continue;
      try{
        const sheet=new CSSStyleSheet();sheet.replaceSync(style.textContent);
        for(const rule of sheet.cssRules){
          if(rule.selectorText&&rule.selectorText.length<200&&rules.length<500){
            // Only local simple selectors; no imported resources, pseudo-elements or layout rules.
            for(const selector of rule.selectorText.split(','))if(/^[\w.\-#\s>]+$/.test(selector.trim()))rules.push({selector:selector.trim(),style:rule.style});
          }
        }
      }catch{}
    }
    let count=0;
    function clean(node,depth=0){
      if(++count>20000||depth>100)throw new Error('Le document contient trop de fragments de mise en forme.');
      if(node.nodeType===Node.TEXT_NODE){
        const parent=node.parentElement?.localName;
        const structural=new Set('p div h1 h2 h3 h4 h5 h6 ul ol li blockquote pre table thead tbody tfoot tr'.split(' '));
        const siblings=[...node.parentNode.childNodes].some(n=>n.nodeType===Node.ELEMENT_NODE&&structural.has(n.localName));
        // Indentation between HTML blocks is source-code whitespace, not a blank paragraph.
        if(!node.nodeValue.trim()&&(['table','thead','tbody','tfoot','tr','ul','ol'].includes(parent)||((!parent||['div','blockquote','body'].includes(parent))&&siblings)))return document.createDocumentFragment();
        return document.createTextNode(node.nodeValue);
      }
      if(node.nodeType!==Node.ELEMENT_NODE)return document.createDocumentFragment();
      const tag=node.localName.toLowerCase();if(discard.has(tag))return document.createDocumentFragment();
      const result=tags.has(tag)||tag==='font'?document.createElement(tag==='font'?'span':tag):document.createDocumentFragment();
      if(result.nodeType===Node.ELEMENT_NODE){
        for(const rule of rules){try{if(node.matches(rule.selector))applyStyle(result,rule.style);}catch{}}
        if(tag==='font'){
          if(node.hasAttribute('face'))result.style.fontFamily=node.getAttribute('face');
          if(node.hasAttribute('color'))result.style.color=node.getAttribute('color');
          const size=Number(node.getAttribute('size'));if(size>=1&&size<=7)result.style.fontSize=[8,10,12,14,18,24,36][size-1]+'pt';
        }
        if(node.hasAttribute('align')&&/^(left|center|right|justify)$/.test(node.getAttribute('align')))result.style.textAlign=node.getAttribute('align');
        // Parse declarations through CSSOM: CSP can disable styles parsed by innerHTML.
        const declarations=document.createElement('span');declarations.style.cssText=node.getAttribute('style')||'';
        applyStyle(result,declarations.style);
        if(tag==='a'){
          const href=node.getAttribute('href')||'';
          try{const url=new URL(href);if(['http:','https:','mailto:'].includes(url.protocol)){result.href=url.href;result.rel='noopener noreferrer';result.target='_blank';}}catch{}
        }
        for(const name of ['colspan','rowspan','start','value']){
          const number=Number(node.getAttribute(name));
          if(node.hasAttribute(name)&&Number.isInteger(number)&&number>=1&&number<=100)result.setAttribute(name,String(number));
        }
      }
      for(const child of node.childNodes)result.append(clean(child,depth+1));
      return result;
    }
    const root=document.createElement('div');
    for(const child of template.content.childNodes)root.append(clean(child));
    if(root.textContent.length>MAX_TEXT)throw new Error('Le texte est limité à 100 000 caractères.');
    return root;
  }
  function plain(root){
    const blocks=new Set('p div h1 h2 h3 h4 h5 h6 ul ol li blockquote pre tr'.split(' '));
    function read(node){
      if(node.nodeType===Node.TEXT_NODE)return node.nodeValue;
      if(node.localName==='br')return '\n';
      const content=[...node.childNodes].map(read).join('');
      if(node.localName==='td'||node.localName==='th')return content+'\t';
      return content+(blocks.has(node.localName)?'\n':'');
    }
    return [...root.childNodes].map(read).join('').replace(/\t\n/g,'\n').replace(/\n$/,'');
  }
  function fromText(text){const root=document.createElement('div');root.textContent=text;return root;}
  function snapshot(html){
    const root=sanitize(html),fragments=[],nodes=[],blocks=new Map();
    const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);let node;
    while((node=walker.nextNode())){
      if(!node.nodeValue.trim())continue;
      const block=node.parentElement.closest('p,div,li,h1,h2,h3,h4,h5,h6,td,th,pre,blockquote')||root;
      if(!blocks.has(block))blocks.set(block,blocks.size);
      fragments.push({id:'f'+fragments.length,paragraph:blocks.get(block),text:node.nodeValue});nodes.push(node);
    }
    if(fragments.length>MAX_FRAGMENTS)throw new Error('Ce document contient trop de fragments distincts pour une correction fiable.');
    return {root,html:root.innerHTML,text:plain(root),fragments,nodes};
  }
  function parseResponse(text){
    let value=text.trim();const fence=/^```(?:json)?\s*\n([\s\S]*?)\n```$/.exec(value);if(fence)value=fence[1];
    try{return JSON.parse(value);}catch{throw new Error('Le résultat reçu ne permet pas de conserver la mise en forme. Votre original est conservé ; relancez la correction.');}
  }
  function apply(snapshot,response){
    if(!response||Object.keys(response).join(',')!=='fragments'||!Array.isArray(response.fragments)||response.fragments.length!==snapshot.fragments.length)throw new Error('Le modèle a modifié la structure du texte. Votre original est conservé.');
    const map=new Map();let length=0;
    for(const item of response.fragments){
      if(!item||Object.keys(item).sort().join(',')!=='id,text'||typeof item.id!=='string'||typeof item.text!=='string'||map.has(item.id)||!snapshot.fragments.some(f=>f.id===item.id))throw new Error('Des fragments du texte sont manquants ou invalides. Votre original est conservé.');
      if(!item.text.trim())throw new Error('Un passage du texte a été supprimé. Votre original est conservé.');
      const original=snapshot.fragments.find(f=>f.id===item.id).text;
      const corrected=original.match(/^\s*/)[0]+item.text.trim()+original.match(/\s*$/)[0];
      length+=corrected.length;map.set(item.id,corrected);
    }
    if(length>MAX_TEXT)throw new Error('Le résultat dépasse 100 000 caractères.');
    // Validate everything before touching even the isolated copy of the document.
    const result=sanitize(snapshot.html),walker=document.createTreeWalker(result,NodeFilter.SHOW_TEXT);let node,index=0;
    while((node=walker.nextNode()))if(node.nodeValue.trim())node.nodeValue=map.get(snapshot.fragments[index++].id);
    return {html:result.innerHTML,text:plain(result),root:result};
  }
  function display(element,html){const root=sanitize(html);element.replaceChildren(...root.childNodes);element.classList.remove('markdown');element.classList.add('corrector-rich');}
  function insert(editor,root){
    const token=crypto.randomUUID(),styles=new Map();let index=0;
    for(const element of root.querySelectorAll('*')){const key=token+'-'+index++;element.setAttribute('data-fred-paste',key);styles.set(key,element.style.cssText);}
    let inserted=false;try{inserted=document.execCommand('insertHTML',false,root.innerHTML);}catch{}
    if(inserted){
      // CSP rejects parsed inline styles. Reapply checked properties through the CSSOM.
      for(const element of editor.querySelectorAll('[data-fred-paste]')){const key=element.getAttribute('data-fred-paste');if(styles.has(key)){element.style.cssText=styles.get(key);element.removeAttribute('data-fred-paste');}}
      return;
    }
    for(const element of root.querySelectorAll('[data-fred-paste]'))element.removeAttribute('data-fred-paste');
    const selection=window.getSelection();let range=selection?.rangeCount?selection.getRangeAt(0):null;
    if(!range||!editor.contains(range.commonAncestorContainer)){range=document.createRange();range.selectNodeContents(editor);range.collapse(false);}
    range.deleteContents();const last=root.lastChild,fragment=document.createDocumentFragment();fragment.append(...root.childNodes);range.insertNode(fragment);
    if(last){range.setStartAfter(last);range.collapse(true);selection.removeAllRanges();selection.addRange(range);}
  }
  function selectionDocument(){
    const active=document.activeElement;if(active instanceof HTMLInputElement||active instanceof HTMLTextAreaElement)return null;
    const selection=window.getSelection();if(!selection?.rangeCount||selection.isCollapsed)return null;
    const range=selection.getRangeAt(0),element=range.commonAncestorContainer.nodeType===Node.ELEMENT_NODE?range.commonAncestorContainer:range.commonAncestorContainer.parentElement;
    const rich=element?.closest('.corrector-rich');if(!rich)return null;
    const fragment=range.cloneContents();
    const wrapper=document.createElement(fragment.querySelector('p,div,li,table,h1,h2,h3,h4,h5,h6')?'div':'span');
    const computed=getComputedStyle(element);
    for(const name of ['font-family','font-size','font-weight','font-style','color','background-color','text-decoration','vertical-align','white-space'])wrapper.style.setProperty(name,computed.getPropertyValue(name));
    const link=element.closest('a');if(link&&rich.contains(link)){const anchor=document.createElement('a');anchor.setAttribute('href',link.getAttribute('href')||'');anchor.append(fragment);wrapper.append(anchor);}else wrapper.append(fragment);
    const root=document.createElement('div');root.append(wrapper);return {html:root.innerHTML,text:selection.toString(),host:rich};
  }
  let copying=null,handled=false;
  function exportHTML(html,host){
    const root=sanitize(html),style=getComputedStyle(host);
    for(const name of ['font-family','font-size','color','line-height','white-space'])root.style.setProperty(name,style.getPropertyValue(name));
    return root.outerHTML;
  }
  document.addEventListener('copy',event=>{
    if(!copying&&typeof copyingText!=='undefined'&&copyingText!==null)return;
    const data=copying||selectionDocument();if(!data||!event.clipboardData)return;
    event.clipboardData.setData('text/plain',data.text);event.clipboardData.setData('text/html',exportHTML(data.html,data.host));event.preventDefault();handled=true;
  });
  async function copy(html,text,host){
    copying={html,text,host};handled=false;
    try{if(document.execCommand('copy')&&handled)return true;}catch{}finally{copying=null;}
    if(navigator.clipboard?.write&&typeof ClipboardItem!=='undefined'){
      try{await navigator.clipboard.write([new ClipboardItem({'text/html':new Blob([exportHTML(html,host)],{type:'text/html'}),'text/plain':new Blob([text],{type:'text/plain'})})]);return true;}catch{}
    }
    await copyText(text);return false;
  }
  return Object.freeze({sanitize,plain,fromText,snapshot,parseResponse,apply,display,insert,copy,selectionDocument,MAX_TEXT,MAX_HTML});
})();
