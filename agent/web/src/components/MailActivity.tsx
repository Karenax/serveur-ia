import { useEffect, useRef, useState } from "react";
import { request } from "../lib/http";
import { api } from "../lib/api";
import "../progressive-options.css";

type Step = {state:string;detail:string;processed:number|null;total:number|null};
export type MailActivitySnapshot = {source:string;transfer:Step;analysis:Step;indexing:Step;
  events:{key:string;text:string;state:string}[];checked_at:string};
type Entry = {text:string;time:string};
const labels:Record<string,string> = {running:"En cours",queued:"En attente",offline:"Déconnecté",failed:"À reprendre",idle:"Au repos"};
export type MailActivityState = "checking" | "offline" | "running" | "failed" | "queued" | "idle" | "unavailable";

function isMailActivitySnapshot(value:unknown): value is MailActivitySnapshot {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const snapshot=value as Record<string,unknown>;
  const step=(item:unknown) => {
    if (!item || typeof item !== 'object' || Array.isArray(item)) return false;
    const row=item as Record<string,unknown>;
    const count=(number:unknown)=>number===null||(typeof number==='number'&&Number.isFinite(number));
    return typeof row.state==='string' && typeof row.detail==='string' && count(row.processed) && count(row.total);
  };
  return typeof snapshot.source==='string' && typeof snapshot.checked_at==='string'
    && step(snapshot.transfer) && step(snapshot.analysis) && step(snapshot.indexing)
    && Array.isArray(snapshot.events) && snapshot.events.every((event:unknown)=>{
      if(!event || typeof event!=='object' || Array.isArray(event))return false;
      const row=event as Record<string,unknown>;
      return typeof row.key==='string' && typeof row.state==='string' && typeof row.text==='string';
    });
}

export function MailActivity({onOpen,onStateChange}:{onOpen:()=>void;onStateChange?:(state:MailActivityState)=>void}) {
  const [value,setValue]=useState<MailActivitySnapshot|null>(null);
  const [error,setError]=useState(false);
  const [restricted,setRestricted]=useState(false);
  const [log,setLog]=useState<Entry[]>([]);
  const previous=useRef(new Map<string,string>());
  const disconnected=useRef(false);
  useEffect(()=>{
    let live=true,failures=0,lastAttempt=-Infinity,visible=!document.hidden;
    let timer:number|undefined,controller:AbortController|null=null;
    const schedule=(delay=30000)=>{if(live&&!document.hidden&&timer===undefined)timer=window.setTimeout(()=>{timer=undefined;void load(true);},delay);};
    const load=async(quiet=false,force=false)=>{
      if(!live||document.hidden||controller)return;
      if(force&&timer!==undefined){window.clearTimeout(timer);timer=undefined;}
      if(!force&&Date.now()-lastAttempt<30000){schedule(30000-(Date.now()-lastAttempt));return;}
      lastAttempt=Date.now();
      const current=new AbortController();controller=current;
      try {
        const session=await api.session(current.signal,20000);
        if(!live||current.signal.aborted)return;
        const limited=Array.isArray(session.operator.project_ids);
        setRestricted(limited);
        if(limited)return;
        const result=await request<unknown>("/api/v1/workspace/mail-activity",{signal:current.signal,activity:quiet?false:undefined},20000);
        if(!live||current.signal.aborted)return;
        if(!isMailActivitySnapshot(result))throw new Error('État des mails incomplet');
        failures=0;setValue(result);setError(false);
        const changed=result.events.filter(event=>previous.current.get(event.key)!==`${event.state}:${event.text}`);
        previous.current=new Map(result.events.map(event=>[event.key,`${event.state}:${event.text}`]));
        const updates=changed.map(event=>({text:event.text,time:result.checked_at}));
        if(disconnected.current)updates.unshift({text:"Connexion au serveur rétablie",time:result.checked_at});
        disconnected.current=false;
        if(updates.length)setLog(old=>[...updates,...old].slice(0,4));
      }catch{if(live&&!current.signal.aborted){
        failures+=1;
        if(failures<3)return;
        setError(true);
        if(!disconnected.current)setLog(old=>[{text:"Serveur indisponible · nouvelle tentative",time:new Date().toISOString()},...old].slice(0,4));
        disconnected.current=true;
      }}finally{if(controller===current){controller=null;schedule();}}
    };
    const stop=()=>{if(timer!==undefined)window.clearTimeout(timer);timer=undefined;controller?.abort();controller=null;};
    const visibility=()=>{const next=!document.hidden;if(next===visible)return;visible=next;if(!next)stop();else void load(true,true);};
    const resume=()=>void load(true);
    if(visible)void load();window.addEventListener("focus",resume);document.addEventListener("visibilitychange",visibility);
    return()=>{live=false;stop();window.removeEventListener("focus",resume);document.removeEventListener("visibilitychange",visibility);};
  },[]);
  const steps=value?[value.transfer,value.analysis,value.indexing]:[];
  const busy=!error&&steps.some(step=>step.state==="running");
  const state=error?"offline":busy?"running":steps.some(step=>step.state==="failed")?"failed":steps.some(step=>step.state==="queued")?"queued":value?.transfer.state==="offline"?"offline":"idle";
  const reportedState=restricted?'unavailable':error?'offline':steps.some(step=>step.state==='failed')?'failed':value?state:'checking';
  useEffect(()=>{onStateChange?.(reportedState);},[reportedState,onStateChange]);
  const current=busy?steps.find(step=>step.state==="running"):null;
  const failed=steps.filter(step=>step.state==="failed");
  if(restricted)return null;
  return <section className={`workspace-mail-activity ${busy?"is-active":""}`} aria-label="Activité des mails">
    <details className="mail-activity-details">
      <summary><strong><span className={`mail-activity-dot ${state}`} aria-hidden="true"/>Mails</strong><span role="status">{value||error?labels[state]:"Connexion…"}</span><span className="mail-activity-expand">Détails</span></summary>
    {!error&&value?<>
      {([["Synchronisation",value.transfer],["Analyse des mails",value.analysis],["Ajout à la recherche",value.indexing]] as [string,Step][]).map(([label,step])=>{
        const known=step.total!==null&&step.total>0&&step.processed!==null;
        return <div className="mail-activity-step" key={label}>
          <div><span>{label}</span><small>{labels[step.state]||step.state}</small></div>
          {known?<progress aria-label={label} max={step.total!} value={Math.min(step.total!,step.processed!)}/>:
            <div className={`mail-activity-track ${step.state==="running"?"indeterminate":""}`} role={step.state==="running"?"progressbar":undefined} aria-label={label}><i/></div>}
          <p title={step.detail}>{step.detail}</p>
        </div>;
      })}
    </>:<p>{error?"Nouvelle tentative de connexion en cours…":"Lecture de l’état du serveur…"}</p>}
    <ol className="mail-activity-log" aria-label="Dernières activités des mails">{log.map((entry,i)=><li key={`${entry.time}:${i}`}><time dateTime={entry.time}>{new Date(entry.time).toLocaleTimeString("fr-FR",{hour:"2-digit",minute:"2-digit"})}</time><span title={entry.text}>{entry.text}</span></li>)}</ol>
    <button type="button" onClick={onOpen}>Voir les traitements →</button>
    </details>
    {error&&<p role="alert">État indisponible · reconnexion…</p>}
    {!error&&failed.map((step,index)=><p role="alert" key={index}>{step.detail}</p>)}
    {current&&<div className="mail-activity-live" role="status"><p>{current.detail}</p>
      {current.total!==null&&current.total>0&&current.processed!==null?<progress aria-label="Traitement des mails en cours" value={Math.min(current.total,current.processed)} max={current.total}/>:
      <div className="mail-activity-track indeterminate" role="progressbar" aria-label="Traitement des mails en cours"><i/></div>}
    </div>}
  </section>;
}
