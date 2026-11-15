import {useEffect, useState} from 'react';
import {request} from '../lib/http';
import "../progressive-options.css";

type Recovery = {running:boolean; total:number; processed:number; indexed:number; failed:number; remaining_failed:number; error:string|null};
const endpoint='/v1/settings/memory/recovery';
export function MemoryRecovery() {
  const [state,setState]=useState<Recovery|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  useEffect(()=>{
    let alive=true,pending=false;
    const controller=new AbortController();
    const read=async(quiet=false)=>{
      if(pending||document.hidden)return;
      pending=true;
      try{const value=await request<Recovery>(endpoint,{signal:controller.signal,activity:quiet?false:undefined},10000);if(alive){setState(value);setError('');}}
      catch(e){if(alive)setError(String(e instanceof Error?e.message:e));}
      finally{pending=false;}
    };
    void read();const timer=window.setInterval(()=>void read(true),3000);
    return()=>{alive=false;controller.abort();window.clearInterval(timer);};
  },[]);
  const retry=async()=>{
    setBusy(true);setError('');
    try{setState(await request<Recovery>(endpoint,{method:'POST'},10000));}
    catch(e){setError(String(e instanceof Error?e.message:e));}
    finally{setBusy(false);}
  };
  const retryButton=<button type="button" className="button primary" disabled={busy||!state||state.running||!state.remaining_failed} onClick={()=>void retry()}>{state?.running?'Reprise en cours…':busy?'Démarrage…':'Reprendre les indexations en échec'}</button>;
  return <section className="memory-recovery" aria-label="Reprise des indexations mémoire">
    <div className="memory-recovery-summary"><strong>Informations indexées</strong><span role="status">{state?state.remaining_failed?`${state.remaining_failed} indexation(s) en échec`:"Aucune indexation en échec":'Lecture de l’état…'}</span></div>
    {(state?.remaining_failed || state?.running || busy)?<div className="settings-main-actions">{retryButton}</div>:null}
    {!!state?.total&&<div role="status"><p>{state.processed} / {state.total} traitées · {state.indexed} réussies · {state.failed} en échec{!state.running?' · Reprise terminée':''}</p>
      {state.running&&<progress aria-label="Avancement de la reprise mémoire" value={state.processed} max={state.total} style={{width:'100%'}}/>}</div>}
    {(error||state?.error)&&<p role="alert">{error||state?.error}</p>}
    <details className="progressive-options"><summary>Options de reprise</summary>
      <p>La reprise remet dans la file les indexations en échec. Les sources et les validations sont conservées.</p>
      {!state?.remaining_failed&&!state?.running&&!busy&&retryButton}
    </details>
  </section>;
}
