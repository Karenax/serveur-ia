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
export function MailActivity({onOpen,onStateChange}:{onOpen:()=>void;onStateChange?:(state:MailActivityState)=>void}) {
  const [value,setValue]=useState<MailActivitySnapshot|null>(null);
  const [error,setError]=useState(false);
  const [restricted,setRestricted]=useState(false);
  const [log,setLog]=useState<Entry[]>([]);
  const previous=useRef(new Map<string,string>());
  const disconnected=useRef(false);
  useEffect(()=>{
    let live=true,loading=false,failures=0,lastAttempt=-Infinity;
    const controller=new AbortController();
    const load=async(quiet=false)=>{
      if(loading||document.hidden||!live||Date.now()-lastAttempt<30000)return;
      lastAttempt=Date.now();
      loading=true;
      try {
        const session=await api.session();
        if(!live)return;
        const limited=Array.isArray(session.operator.project_ids);
        setRestricted(limited);
        if(limited)return;
        const result=await request<MailActivitySnapshot>("/api/v1/workspace/mail-activity",{signal:controller.signal,activity:quiet?false:undefined},20000);
        if(!live)return;
        failures=0;setValue(result);setError(false);
        const changed=result.events.filter(event=>previous.current.get(event.key)!==`${event.state}:${event.text}`);
        previous.current=new Map(result.events.map(event=>[event.key,`${event.state}:${event.text}`]));
        const updates=changed.map(event=>({text:event.text,time:result.checked_at}));
        if(disconnected.current)updates.unshift({text:"Connexion au serveur rétablie",time:result.checked_at});
        disconnected.current=false;
        if(updates.length)setLog(old=>[...updates,...old].slice(0,4));
      }catch{if(live){
        failures+=1;
        if(failures<3)return;
        setError(true);
        if(!disconnected.current)setLog(old=>[{text:"Serveur indisponible · nouvelle tentative",time:new Date().toISOString()},...old].slice(0,4));
        disconnected.current=true;
      }}finally{loading=false;}
    };
    void load();const timer=window.setInterval(()=>void load(true),30000);
    const resume=()=>void load(true);window.addEventListener("focus",resume);document.addEventListener("visibilitychange",resume);
    return()=>{live=false;controller.abort();window.clearInterval(timer);window.removeEventListener("focus",resume);document.removeEventListener("visibilitychange",resume);};
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
