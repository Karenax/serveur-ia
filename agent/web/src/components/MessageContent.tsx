import {useEffect,useMemo,useRef,useState} from 'react';
import './message-content.css';
type Options={inlineImages?:Record<string,string>;showRemote?:boolean};
const hasHtml=(text:string)=>/<(?:!doctype|html|head|body|div|p|br|table|tbody|tr|td|span|a|h[1-6]|ul|ol|li|img|font)\b[^>]*>/i.test(text);
export function messageDocument(text:string,{inlineImages={},showRemote=false}:Options={}):string|null{
  if(!hasHtml(text))return null;
  const parsed=new DOMParser().parseFromString(text,'text/html');
  parsed.querySelectorAll('script,iframe,object,embed,form,input,button,link,meta,base,svg,math,video,audio,source').forEach(node=>node.remove());
  const styles=Array.from(parsed.querySelectorAll('style')).map(node=>node.textContent||'').join('\n');
  parsed.querySelectorAll('style').forEach(node=>node.remove());
  const allowed=new Set('div p br table tbody thead tfoot tr td th col colgroup caption span a h1 h2 h3 h4 h5 h6 ul ol li dl dt dd strong b em i u s strike sub sup blockquote hr pre code img font center address section article header footer'.split(' '));
  const attrs=new Set('style class id title lang dir align valign width height bgcolor color face size border cellpadding cellspacing colspan rowspan nowrap alt href src'.split(' '));
  const clean=(node:Element)=>{for(const attr of Array.from(node.attributes))if(!attrs.has(attr.name))node.removeAttribute(attr.name);};
  clean(parsed.body);
  for(const node of Array.from(parsed.body.querySelectorAll('*')).reverse()){
    if(!allowed.has(node.localName)){node.replaceWith(...Array.from(node.childNodes));continue;}
    clean(node);
    if(node.localName==='img'){
      const src=node.getAttribute('src')||'';
      const embedded=/^cid:/i.test(src)?inlineImages[src.slice(4).replace(/^<|>$/g,'')]:undefined;
      node.removeAttribute('src');
      if(embedded&&/^data:image\/(png|jpeg|gif|webp);base64,/i.test(embedded))node.setAttribute('src',embedded);
      else if(/^data:image\/(png|jpeg|gif|webp);base64,/i.test(src))node.setAttribute('src',src);
      else if(showRemote&&/^https?:\/\//i.test(src))node.setAttribute('src',src);
      else {
        const placeholder=parsed.createElement('span');
        placeholder.className='agent-blocked-image';
        placeholder.textContent=/^https?:/i.test(src)?'Image distante masquée':'Image indisponible';
        placeholder.setAttribute('role','img');
        placeholder.setAttribute('aria-label',placeholder.textContent);
        node.replaceWith(placeholder);
      }
    }else node.removeAttribute('src');
    if(node.localName==='a'){
      if(!/^(https?:|mailto:|tel:)/i.test(node.getAttribute('href')||''))node.removeAttribute('href');
      node.setAttribute('target','_blank');node.setAttribute('rel','noopener noreferrer');
    }else node.removeAttribute('href');
  }
  const bodyAttrs=Array.from(parsed.body.attributes).map(attr=>` ${attr.name}="${attr.value.replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;')}"`).join('');
  // Original CSS is isolated in the frame; CSP also blocks URLs hidden in CSS.
  const imagePolicy=showRemote?'data: https: http:':'data:';
  const safeStyles=styles.replace(/<\/style/gi,'<\\/style');
  return `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'none'; style-src 'unsafe-inline'; img-src ${imagePolicy}; font-src data:; base-uri 'none'; form-action 'none'"><style>html{color-scheme:light}body{margin:8px;background:#fff;color:#111;font:16px/normal Arial,sans-serif;overflow-wrap:break-word}img{max-width:100%}.agent-blocked-image{display:inline-block;padding:8px 12px;margin:4px;border:1px solid #c9d2d9;background:#f4f6f8;color:#465562;font:13px/1.4 Arial,sans-serif;max-width:100%;box-sizing:border-box}pre{white-space:pre-wrap}table{max-width:100%}</style><style>${safeStyles}</style></head><body${bodyAttrs}>${parsed.body.innerHTML}</body></html>`;
}
export function MessageContent({text,inlineImages={}}:{text:string;inlineImages?:Record<string,string>}){
  const [remoteFor,setRemoteFor]=useState<string|null>(null);
  const showRemote=remoteFor===text;
  const frame=useRef<HTMLIFrameElement>(null);
  const content=useMemo(()=>messageDocument(text,{inlineImages,showRemote}),[text,inlineImages,showRemote]);
  useEffect(()=>{
    const iframe=frame.current;if(!iframe||!content)return;
    let observer:ResizeObserver|undefined;
    const resize=()=>{const body=iframe.contentDocument?.body;if(body)iframe.style.height=`${Math.max(180,Math.ceil(body.getBoundingClientRect().height+24))}px`;};
    const loaded=()=>{observer?.disconnect();resize();const body=iframe.contentDocument?.body;if(body&&typeof ResizeObserver!=='undefined'){observer=new ResizeObserver(resize);observer.observe(body);}};
    iframe.addEventListener('load',loaded);return()=>{iframe.removeEventListener('load',loaded);observer?.disconnect();};
  },[content]);
  if(content)return <div className="message-content-original">{/(?:src\s*=\s*["']?https?:|url\s*\()/i.test(text)&&!showRemote&&<button type="button" className="message-content-images" onClick={()=>setRemoteFor(text)}>Afficher les images distantes</button>}<iframe ref={frame} className="message-content-frame" title="Contenu du message" sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox" referrerPolicy="no-referrer" srcDoc={content}/></div>;
  const lines=text.replace(/\r\n/g,'\n').split('\n'),quoted=lines.findIndex(line=>/^\s*>/.test(line));
  return <div className="message-content-text"><div>{quoted>0?lines.slice(0,quoted).join('\n').trim():text}</div>{quoted>0&&<details><summary>Afficher l’historique des échanges</summary><div>{lines.slice(quoted).join('\n')}</div></details>}</div>;
}
