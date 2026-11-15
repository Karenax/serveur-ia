import { useEffect, useState } from 'react';
import { deliverableApi, type DeliverableFocus, type GatePage } from '../lib/projectDeliverables';
import { Pagination } from './IdentityPickers';
import { message } from './PlanningTasksPanel';

export function MilestoneDeliverableGates({projectId,milestoneId,title,active=true,disabled=false,refreshKey=0,onStatus,onOpenDeliverable}:{projectId:string;milestoneId:string;title:string;active?:boolean;disabled?:boolean;refreshKey?:number;onStatus?:(page:GatePage|null)=>void;onOpenDeliverable?:(focus:Omit<DeliverableFocus,'requestId'>)=>void}) {
  const [page,setPage]=useState<GatePage|null>(null);const [includeReady,setIncludeReady]=useState(false);const [offset,setOffset]=useState(0);const [tick,setTick]=useState(0);const [error,setError]=useState('');const [loading,setLoading]=useState(false);
  useEffect(()=>{if(!active){onStatus?.(null);return;}const controller=new AbortController();setLoading(true);setPage(null);setError('');onStatus?.(null);
    deliverableApi.milestoneGates(projectId,milestoneId,{offset,limit:25,include_ready:includeReady,signal:controller.signal}).then(value=>{if(controller.signal.aborted)return;if(value.milestone_id!==milestoneId)throw new Error('Réponse de visas reçue pour un autre jalon.');setPage(value);onStatus?.(value);}).catch(e=>{if(!controller.signal.aborted){setError(message(e));onStatus?.(null);}}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return()=>controller.abort();
  },[projectId,milestoneId,active,includeReady,offset,tick,refreshKey,onStatus]);
  return <section className="planning-gates" aria-label={`Visas de livrables · ${title}`}><div className="planning-heading"><h4>Visas de livrables · {title}</h4><button type="button" className="button secondary sm" disabled={disabled||loading||!active} onClick={()=>setTick(value=>value+1)}>Recontrôler les visas</button></div>
    <p className="planning-note">La validation du jalon vérifie tous les visas obligatoires, leurs preuves humaines et les fichiers de la dernière version. La date réelle conserve son sens indépendant.</p>
    {loading&&<p role="status">Contrôle des visas et des fichiers…</p>}{error&&<p role="alert" className="planning-error">{error} La disponibilité du jalon n’a pas pu être vérifiée.</p>}
    {page&&<><p role="status" className={page.can_validate?'planning-notice':'planning-error'}>{page.checks_total===0?'Aucun visa de livrable requis pour ce jalon.':page.can_validate?`Les ${page.checks_total} visas requis sont obtenus.`:`${page.blocking_total} visa(s) bloquant(s) sur ${page.checks_total} contrôles requis.`} · Révision {page.revision}</p>
      <label className="identity-checkbox"><input type="checkbox" checked={includeReady} disabled={disabled||loading} onChange={e=>{setIncludeReady(e.target.checked);setOffset(0);}}/>Afficher aussi les visas obtenus</label><Pagination offset={page.offset} total={page.total} limit={page.limit} onChange={setOffset} disabled={disabled||loading}/>
      {!page.items.length&&<p>{page.total?'Aucun contrôle sur cette page.':'Aucun contrôle bloquant dans cette lecture.'}</p>}
      <ul className="deliverable-checks">{page.items.map(check=><li key={check.id}><strong>{check.label}</strong><span>{check.deliverable_title} · {check.ready?'Visa obtenu':check.reason||'Visa à vérifier'}</span><small>{check.version?`V${check.version.number} · ${check.version.reference||check.version.filename} · ${check.version.filename}`:'Aucune version publiée'}</small><small>Responsable : {check.responsible_name||'Non attribué'} · Vérificateur : {check.verifier_name||'Non attribué'}</small>
        {onOpenDeliverable&&<button type="button" className="button secondary sm" disabled={disabled||loading||!active} aria-label={`Ouvrir ${check.deliverable_title} · ${check.label}`} onClick={()=>onOpenDeliverable({deliverableId:check.deliverable_id,checkId:check.id,milestoneId,milestoneTitle:title,version:check.version})}>Ouvrir le livrable et son contrôle</button>}
      </li>)}</ul></>}
  </section>;
}
