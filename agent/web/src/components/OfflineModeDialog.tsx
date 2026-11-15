import {useEffect,useRef,useState} from 'react';
import {createPortal} from 'react-dom';
import {request} from '../lib/http';

export type OfflineStatus={outage_id:string|null;remaining_seconds:number;approval_required:boolean;decision:'offline'|'wait'|null;using_fallback:boolean};

export function OfflineModeDialog({status,onChange,onClose}:{status:OfflineStatus;onChange:(value:OfflineStatus)=>void;onClose:()=>void}) {
  const dialog=useRef<HTMLDialogElement>(null);
  const [busy,setBusy]=useState(false),[error,setError]=useState('');
  const pending=useRef(false);
  useEffect(()=>{
    const previous=document.activeElement instanceof HTMLElement?document.activeElement:null;
    const element=dialog.current;
    element?.showModal?.();
    return()=>{element?.close?.();if(previous?.isConnected)previous.focus();};
  },[]);
  const decide=async(decision:'offline'|'wait')=>{
    if(pending.current)return;
    pending.current=true;setBusy(true);setError('');
    try {
      const value=await request<OfflineStatus>('/v1/settings/ai/offline-decision',{method:'POST',activity:false,body:JSON.stringify({outage_id:status.outage_id,decision})},20000);
      onChange(value);onClose();
    } catch {setError('Choix non enregistré. Réessayez ou vérifiez la connexion.');window.dispatchEvent(new Event('agent:connections-refresh'));}
    finally {pending.current=false;setBusy(false);}
  };
  return createPortal(<dialog ref={dialog} className="workspace-command" aria-labelledby="offline-mode-title" aria-describedby="offline-mode-description"
    onKeyDown={event=>{
      if(event.key!=='Tab')return;
      const buttons=Array.from(dialog.current?.querySelectorAll<HTMLButtonElement>('button:not([disabled])')||[]);
      if(!buttons.length){event.preventDefault();return;}
      const first=buttons[0],last=buttons[buttons.length-1];
      if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
      if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
    }}
    onCancel={event=>{event.preventDefault();void decide('wait');}}>
    <div className="workspace-section-heading"><h2 id="offline-mode-title">Serveur IA sans réponse</h2></div>
    <p id="offline-mode-description">Le serveur ne répond plus depuis au moins deux minutes. Passer hors ligne autorise le chargement du modèle local pour vos prochaines demandes.</p>
    {error&&<p role="alert">{error}</p>}
    <div className="workspace-offline-actions">
      <button type="button" className="button secondary" autoFocus disabled={busy} onClick={()=>void decide('wait')}>Attendre la connexion</button>
      <button type="button" className="button primary" disabled={busy} onClick={()=>void decide('offline')}>Passer hors ligne</button>
    </div>
  </dialog>,document.querySelector('.workspace-shell')||document.body);
}
