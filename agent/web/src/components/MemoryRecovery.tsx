import {useEffect, useRef, useState} from 'react';
import {request} from '../lib/http';
import "../progressive-options.css";

type Recovery = {running:boolean; total:number; processed:number; indexed:number; failed:number; remaining_failed:number; error:string|null};
const endpoint='/v1/settings/memory/recovery';
export function MemoryRecovery({active=true}:{active?:boolean} = {}) {
  const [state,setState]=useState<Recovery|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const generation=useRef(0),operation=useRef(false),mounted=useRef(false);
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;};},[]);
  useEffect(()=>{
    if(!active)return;
    let alive=true,controller:AbortController|null=null,timer:number|undefined;
    const stop=()=>{generation.current++;controller?.abort();controller=null;if(timer!==undefined){window.clearInterval(timer);timer=undefined;}};
    const read=async(quiet=false)=>{
      if(!alive||operation.current||document.hidden||controller)return;
      const current=new AbortController();controller=current;const ticket=++generation.current;
      try{const value=await request<Recovery>(endpoint,{signal:current.signal,activity:quiet?false:undefined},10000);
        if(alive&&!current.signal.aborted&&ticket===generation.current){setState(value);setError('');}}
      catch(e){if(alive&&!current.signal.aborted&&ticket===generation.current)setError(String(e instanceof Error?e.message:e));}
      finally{if(controller===current)controller=null;}
    };
    const start=(quiet=false)=>{if(!alive||document.hidden||timer!==undefined)return;void read(quiet);timer=window.setInterval(()=>void read(true),3000);};
    const visibility=()=>{if(document.hidden)stop();else start(true);};
    document.addEventListener('visibilitychange',visibility);start();
    return()=>{alive=false;document.removeEventListener('visibilitychange',visibility);stop();};
  },[active]);
  const retry=async()=>{
    if(operation.current)return;
    operation.current=true;generation.current++;setBusy(true);setError('');
    try{const value=await request<Recovery>(endpoint,{method:'POST'},10000);if(mounted.current)setState(value);}
    catch(e){if(mounted.current)setError(String(e instanceof Error?e.message:e));}
    finally{operation.current=false;if(mounted.current)setBusy(false);}
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
