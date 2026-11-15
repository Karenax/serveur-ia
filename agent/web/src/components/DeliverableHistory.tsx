import { useEffect, useRef, useState } from 'react';
import { deliverableApi, deliverableDate, type DeliverableEvent, type EventDetail, type RevisionPage } from '../lib/projectDeliverables';
import { Pagination } from './IdentityPickers';
import { LoadingState, ErrorState } from './Ui';
import { deliverableActionLabels, EvidenceComparison } from './DeliverableEvidence';
import { focusPlanning } from './PlanningTasksPanel';

export function DeliverableHistory({projectId,deliverableId,active=true}:{projectId:string;deliverableId:string;active?:boolean}) {
  const [page,setPage]=useState<RevisionPage<DeliverableEvent>|null>(null);const [offset,setOffset]=useState(0);const [tick,setTick]=useState(0);const [loading,setLoading]=useState(false);const [error,setError]=useState('');
  const [eventId,setEventId]=useState<string|null>(null);const [detail,setDetail]=useState<EventDetail|null>(null);const [opening,setOpening]=useState(false);const focus=useRef<HTMLElement>(null);
  useEffect(()=>{if(detail)focusPlanning(focus.current);},[detail]);
  useEffect(()=>{if(!active)return;const controller=new AbortController();setLoading(true);setError('');setPage(null);
    deliverableApi.history(projectId,deliverableId,{offset,limit:25,signal:controller.signal}).then(value=>{if(!controller.signal.aborted)setPage(value);}).catch(e=>{if(!controller.signal.aborted)setError(String(e.message||e));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});return()=>controller.abort();
  },[projectId,deliverableId,active,offset,tick]);
  useEffect(()=>{if(!active||!eventId)return;const controller=new AbortController();setOpening(true);setError('');setDetail(null);
    deliverableApi.event(projectId,deliverableId,eventId,controller.signal).then(value=>{if(!controller.signal.aborted)setDetail(value);}).catch(e=>{if(!controller.signal.aborted)setError(String(e.message||e));}).finally(()=>{if(!controller.signal.aborted)setOpening(false);});return()=>controller.abort();
  },[projectId,deliverableId,active,eventId,tick]);
  return <section aria-label="Historique du livrable"><header className="planning-heading"><div><h4>Historique du livrable</h4><p>Journal immuable des versions, preuves, visas et modifications humaines.</p></div><button type="button" className="button secondary sm" disabled={loading||opening||!active} onClick={()=>setTick(value=>value+1)}>Recharger le journal du livrable</button></header>
    {error&&<ErrorState message={error} retry={()=>setTick(value=>value+1)}/>} {loading&&<LoadingState label="Chargement du journal"/>} {opening&&<LoadingState label="Chargement de la modification"/>}
    {detail&&<section ref={focus} tabIndex={-1} className="planning-editor" aria-label={`Modification · révision ${detail.revision}`}><header className="planning-heading"><div><h4>{deliverableActionLabels[detail.action]||'Modification enregistrée'}</h4><p>Révision {detail.revision} · {deliverableDate(detail.created_at)} · opérateur {detail.actor_id}</p></div><button type="button" className="button secondary sm" onClick={()=>{setEventId(null);setDetail(null);}}>Fermer la modification</button></header><EvidenceComparison previous={detail.previous} value={detail.value}/></section>}
    {page&&<><Pagination offset={page.offset} limit={page.limit} total={page.total} onChange={value=>{setEventId(null);setDetail(null);setOffset(value);}} disabled={loading||opening||!active}/>{!page.total&&<p>Aucune modification enregistrée pour ce livrable.</p>}
      <div className="planning-table-scroll"><table className="data-table deliverable-history-table"><thead><tr><th>Révision</th><th>Modification</th><th>Date / opérateur</th><th>Consulter</th></tr></thead><tbody>{page.items.map(row=><tr key={row.id}><td>{row.revision}</td><td>{deliverableActionLabels[row.action]||'Modification enregistrée'}</td><td>{deliverableDate(row.created_at)}<small>{row.actor_id}</small></td><td><button type="button" className="button secondary sm" aria-label={`Consulter la modification ${row.revision}`} disabled={loading||opening||!active} onClick={()=>setEventId(row.id)}>Avant / après</button></td></tr>)}</tbody></table></div></>}
  </section>;
}
