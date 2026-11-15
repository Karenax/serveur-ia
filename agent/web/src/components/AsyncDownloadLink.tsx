import { agentPath } from '../lib/agentRoutes';
import {useEffect,useRef,useState,type AnchorHTMLAttributes,type MouseEvent} from 'react';
import {beginActivity} from '../lib/asyncActivity';
import '../async-download.css';

type Prepared={href:string;url:string;filename:string};
type DownloadTask={href:string;controller:AbortController;finish:()=>void;timer?:number;cancelled:boolean};
type Props=Omit<AnchorHTMLAttributes<HTMLAnchorElement>,'href'|'download'>&{
  href:string;download?:boolean|string;filename?:string;activityLabel?:string;
};
const simpleName=(value:string)=>{
  const name=value.split(/[\\/]/).pop()?.replace(/[\x00-\x1f\x7f<>:"|?*]/g,'_').trim();
  return name&&name!=='.'&&name!=='..'?name:'fichier-agent';
};
export function downloadFilename(disposition:string|null,fallback:string):string{
  const extended=disposition?.match(/(?:^|;)\s*filename\*\s*=\s*UTF-8'[^']*'([^;]+)/i)?.[1];
  if(extended){try{return simpleName(decodeURIComponent(extended.trim().replace(/^"|"$/g,'')));}catch{/* Try the ordinary name or fallback. */}}
  const ordinary=disposition?.match(/(?:^|;)\s*filename\s*=\s*(?:"((?:[^"\\]|\\.)*)"|([^;]+))/i);
  return simpleName(ordinary?(ordinary[1]??ordinary[2]).replace(/\\(.)/g,'$1'):fallback);
}
function cancelTask(task:DownloadTask){task.cancelled=true;task.controller.abort();window.clearTimeout(task.timer);task.finish();}

/** Download only explicit internal file links. Viewing links keep their native behavior. */
export function AsyncDownloadLink({href,download,filename,activityLabel='Préparation du fichier à télécharger…',onClick,children,...attributes}:Props){
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[prepared,setPrepared]=useState<Prepared|null>(null);
  const action=useRef<DownloadTask|null>(null),objectUrl=useRef<string|null>(null),currentHref=useRef(href);
  currentHref.current=href;
  useEffect(()=>{
    setBusy(false);setError('');setPrepared(null);
    return()=>{
      if(action.current){cancelTask(action.current);action.current=null;}
      if(objectUrl.current){URL.revokeObjectURL(objectUrl.current);objectUrl.current=null;}
    };
  },[href]);

  async function prepare(url:URL){
    if(action.current)return;
    const task:DownloadTask={href,controller:new AbortController(),finish:beginActivity(activityLabel),cancelled:false};
    action.current=task;setBusy(true);setError('');
    const owns=()=>action.current===task&&!task.cancelled&&currentHref.current===task.href;
    task.timer=window.setTimeout(()=>{
      if(!owns())return;cancelTask(task);action.current=null;setBusy(false);setError('La préparation du fichier a expiré. Réessayez le téléchargement.');
    },360_000);
    try{
      const response=await fetch(url.href,{method:'GET',credentials:'same-origin',signal:task.controller.signal});
      if(!owns())return;
      if(!response.ok){
        let detail:unknown;try{detail=(await response.json()).detail;}catch{/* Preserve the HTTP error if its body is not JSON. */}
        throw new Error(typeof detail==='string'?detail:detail&&typeof detail==='object'&&'message' in detail?String(detail.message):`Fichier indisponible (${response.status}).`);
      }
      const blob=await response.blob();if(!owns())return;
      const fallback=filename||(typeof download==='string'&&download)||url.pathname.split('/').pop()||'fichier-agent';
      const name=downloadFilename(response.headers.get('content-disposition'),fallback);
      const ready=URL.createObjectURL(blob);
      if(objectUrl.current)URL.revokeObjectURL(objectUrl.current);objectUrl.current=ready;
      setPrepared({href,url:ready,filename:name});
      const anchor=document.createElement('a');anchor.href=ready;anchor.download=name;document.body.append(anchor);
      try{anchor.click();}catch{/* The received bytes remain available through the manual link. */}finally{anchor.remove();}
    }catch(failure){if(owns())setError(failure instanceof Error?failure.message:'Préparation du fichier indisponible.');}
    finally{window.clearTimeout(task.timer);task.finish();if(action.current===task){action.current=null;setBusy(false);}}
  }
  function activate(event:MouseEvent<HTMLAnchorElement>){
    onClick?.(event);if(event.defaultPrevented)return;
    if(action.current){event.preventDefault();return;}
    if(event.button!==0||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;
    let url:URL;try{url=new URL(agentPath(href),window.location.href);}catch{return;}
    if(url.origin!==window.location.origin||!['http:','https:'].includes(url.protocol))return;
    event.preventDefault();void prepare(url);
  }
  const visible=prepared?.href===href?prepared:null;
  return <span className="async-download-link">
    <a {...attributes} href={agentPath(href)} download={download} onClick={activate} aria-busy={busy||undefined} aria-disabled={busy||undefined}>{children}</a>
    {busy&&<small role="status" className="async-download-status">Préparation du fichier…</small>}
    {error&&<small role="alert" className="async-download-error">{error}</small>}
    {visible&&<small className="async-download-ready"><a href={visible.url} download={visible.filename}>Enregistrer le fichier préparé</a><span> · Octets reçus, prêt à enregistrer.</span></small>}
  </span>;
}
