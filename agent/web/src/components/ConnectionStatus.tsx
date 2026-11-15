import {useEffect, useRef, useState} from "react";
import {MailActivity,type MailActivityState} from "./MailActivity";
import {request} from "../lib/http";
import {OfflineModeDialog,type OfflineStatus} from './OfflineModeDialog';
import "../progressive-options.css";

type Service = {state: "checking" | "ok" | "warning" | "error" | "disabled" | "unknown"; detail: string; model?: string; provider?: string; checked_at?: string};
type Connections = {services: Record<"llm" | "embedding" | "memory", Service>; refreshing: boolean;offline?:OfflineStatus};
const labels = {checking:"Vérification…",ok:"Accessible",warning:"À vérifier",error:"Indisponible",disabled:"Désactivé",unknown:"Non vérifié"};

export function ConnectionStatus({onOpenJobs}:{onOpenJobs?:()=>void}) {
  const popup=useRef<HTMLDetailsElement>(null);
  const [mailState,setMailState]=useState<MailActivityState>('checking');
  const [status,setStatus]=useState<Connections|null>(null);
  const [chooseOffline,setChooseOffline]=useState(false);
  useEffect(()=>{
    let stopped=false, pending=false, refreshAgain=false, failures=0, lastAttempt=-Infinity;
    const controller=new AbortController();
    const refresh=async(quiet=false,force=false)=>{
      if(document.hidden || stopped)return;
      if(pending){if(force)refreshAgain=true;return;}
      if(!force && Date.now()-lastAttempt<60000)return;
      lastAttempt=Date.now();
      pending=true;
      try {
        const value=await request<Connections>("/api/v1/connections/status",{signal:controller.signal,activity:quiet?false:undefined},20000);
        if(!value?.services?.llm || !value.services.embedding || !value.services.memory)throw new Error("Statut incomplet");
        if(!stopped && !refreshAgain){failures=0;setStatus(value);}
      } catch {
        if(!stopped && !refreshAgain){
          failures+=1;
          setStatus(previous=>previous && failures<3?previous:{refreshing:false,services:Object.fromEntries(["llm","embedding","memory"].map(key=>[key,{state:"unknown",detail:"État indisponible : le serveur Agent ne répond pas"}])) as Connections["services"]});
        }
      } finally {
        pending=false;
        if(refreshAgain && !stopped){refreshAgain=false;void refresh(true,true);}
      }
    };
    void refresh();
    const interval=window.setInterval(()=>void refresh(true),60000);
    const automaticRefresh=()=>void refresh(true),requestedRefresh=()=>void refresh(false,true);
    document.addEventListener("visibilitychange",automaticRefresh);
    window.addEventListener("agent:connections-refresh",requestedRefresh);
    return ()=>{stopped=true;controller.abort();window.clearInterval(interval);document.removeEventListener("visibilitychange",automaticRefresh);window.removeEventListener("agent:connections-refresh",requestedRefresh);};
  },[]);
  const services=Object.values(status?.services || {});
  const mailAvailable=!!onOpenJobs&&mailState!=='unavailable';
  const mailWarning=mailAvailable&&['failed','offline'].includes(mailState);
  const state=services.some(service=>service.state==='error')?'error':services.some(service=>service.state==='warning')||mailWarning?'warning':
    services.some(service=>service.state==='unknown')?'unknown':!status||services.some(service=>service.state==='checking')||(mailAvailable&&mailState==='checking')?'checking':
    services.some(service=>service.state==='disabled')?'disabled':'ok';
  const summary=state==='ok'&&mailAvailable&&mailState==='running'?'Traitement en cours':
    {ok:'Services accessibles',warning:mailState==='failed'?'Mails à reprendre':mailState==='offline'?'Mails déconnectés':'À vérifier',error:'Service indisponible',unknown:'État non vérifié',checking:'Vérification…',disabled:services.every(service=>service.state==='disabled')?'Services désactivés':'Service désactivé'}[state];
  const offline=status?.offline;
  return <><details ref={popup} className={`workspace-connections system-status ${state}`}>
    <summary><i aria-hidden="true"/><span>État du système</span><small>{summary}</small></summary>
    <div className="system-status-services" aria-label="Connexions des services">
    {offline?.decision==='wait'&&offline.outage_id&&<button type="button" onClick={()=>setChooseOffline(true)}>Choisir le mode hors ligne</button>}
    {offline?.using_fallback&&<p role="status">Mode hors ligne autorisé</p>}
    {([['llm','Assistant IA'],['embedding','Recherche dans les documents'],['memory','Informations indexées']] as const).map(([key,label])=>{
      const service=status?.services[key] || {state:"checking",detail:"Vérification en cours"};
      const state=key==='memory' && service.state==='warning' ? 'Dégradée' : labels[service.state];
      const detail=[service.detail,service.provider,service.model,service.checked_at?`Vérifié à ${new Date(service.checked_at).toLocaleTimeString('fr-FR')}`:''].filter(Boolean).join(' · ');
      return <div key={key} className={`workspace-connection ${service.state}`} role="status" aria-label={`${label} : ${state}`} title={detail}>
        <i aria-hidden="true"/><span><strong>{label}</strong><small>{state}</small><p>{detail}</p></span>
      </div>;
    })}
    {onOpenJobs&&<MailActivity onStateChange={setMailState} onOpen={()=>{if(popup.current)popup.current.open=false;onOpenJobs();}}/>}
    <p className="system-status-help">Ces états indiquent l’accès aux services. Une réponse ou une indexation réussie se vérifie dans le traitement concerné.</p>
    </div>
  </details>
  {offline?.outage_id&&(offline.approval_required||chooseOffline)&&<OfflineModeDialog key={offline.outage_id} status={offline}
    onChange={value=>{
      setStatus(previous=>previous?{...previous,offline:value}:previous);
      window.dispatchEvent(new Event('agent:connections-refresh'));
    }} onClose={()=>setChooseOffline(false)}/>}
  </>;
}
