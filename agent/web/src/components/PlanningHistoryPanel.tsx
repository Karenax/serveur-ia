import { useEffect, useRef, useState } from 'react';
import { planningApi, type PlanningChange } from '../lib/projectPlanning';
import type { Page } from '../lib/projectIdentity';
import { Pagination } from './IdentityPickers';
import { ErrorState, LoadingState } from './Ui';
import { focusPlanning, message, useAlive } from './PlanningTasksPanel';
import { historyChanges, PlanningChanges } from './PlanningChanges';
import '../project-planning.css';

const actionLabels:Record<string,string>={task_created:'Tâche créée',task_changed:'Tâche modifiée',milestone_created:'Jalon créé',milestone_changed:'Jalon modifié',
  candidate_accepted:'Date proposée validée',meeting_action_converted:'Action de réunion convertie',baseline_created:'Référence capturée',
  baseline_metadata_changed:'Métadonnées de référence modifiées',template_applied:'Modèle appliqué',project_changed:'Dates du projet modifiées'};
export function PlanningHistoryPanel(props:{projectId:string;active?:boolean}) {return <HistoryView key={props.projectId} {...props}/>;}
function HistoryView({projectId,active=true}:{projectId:string;active?:boolean}) {
  const [page,setPage]=useState<Page<PlanningChange>|null>(null);const [offset,setOffset]=useState(0);const [loading,setLoading]=useState(true);const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [tick,setTick]=useState(0);
  const [detail,setDetail]=useState<{row:PlanningChange;previous:Record<string,unknown>;value:Record<string,unknown>}|null>(null);const alive=useAlive();
  const detailFocus=useRef<HTMLElement>(null);useEffect(()=>{if(detail)focusPlanning(detailFocus.current);},[detail]);
  useEffect(()=>{if(!active)return;const controller=new AbortController();setLoading(true);setError('');planningApi.history(projectId,offset,controller.signal)
    .then(value=>{if(!controller.signal.aborted)setPage(value);}).catch(e=>{if(!controller.signal.aborted)setError(message(e));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return()=>controller.abort();},[projectId,active,offset,tick]);
  async function open(row:PlanningChange){if(busy)return;setBusy(true);setError('');try{const value=await planningApi.historyDetail(projectId,row.id);if(alive.current)setDetail({row,...value});}catch(e){if(alive.current)setError(message(e));}finally{if(alive.current)setBusy(false);}}
  return <section className="planning-panel" aria-label="Historique du planning"><header className="planning-heading"><div><h3>Historique du planning</h3><p>Journal immuable des modifications humaines, modèles, réunions et validations de dates.</p></div>
    <button type="button" className="button secondary sm" disabled={loading||busy} onClick={()=>setTick(value=>value+1)}>Recharger l’historique</button></header>
    {error&&<ErrorState message={error} retry={()=>setTick(value=>value+1)}/>}{loading&&<LoadingState label="Chargement de l’historique"/>}
    {detail&&<section ref={detailFocus} tabIndex={-1} className="card planning-comparison" aria-label={`Détail de la révision ${detail.row.revision}`}><div className="planning-heading"><div><h3>{actionLabels[detail.row.action]||detail.row.action}</h3>
      <p>Révision {detail.row.revision} · {new Date(detail.row.created_at).toLocaleString('fr-FR')} · opérateur {detail.row.actor_id}</p></div><button type="button" className="button secondary sm" onClick={()=>setDetail(null)}>Fermer le détail historique</button></div>
      <PlanningChanges key={detail.row.id} changes={historyChanges(detail.previous,detail.value)}/></section>}
    {page&&<><Pagination offset={page.offset} total={page.total} limit={page.limit} onChange={setOffset} disabled={loading||busy}/>
      {!page.total&&!loading&&<p>Aucune modification de planning enregistrée. Les anciennes dates conservent leur historique dans Jalons.</p>}
      <div className="planning-table-scroll"><table className="data-table planning-history-table"><thead><tr><th>Révision</th><th>Modification</th><th>Date / opérateur</th><th>Action</th></tr></thead><tbody>{page.items.map(row=><tr key={row.id}><td>{row.revision}</td><td>{actionLabels[row.action]||row.action}</td><td>{new Date(row.created_at).toLocaleString('fr-FR')}<small>{row.actor_id}</small></td>
        <td><button type="button" className="button secondary sm" aria-label={`Consulter la révision ${row.revision}`} disabled={loading||busy} onClick={()=>void open(row)}>Voir avant / après</button></td></tr>)}</tbody></table></div></>}
  </section>;
}
