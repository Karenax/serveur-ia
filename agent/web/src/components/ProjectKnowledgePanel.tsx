import { useEffect, useState } from 'react';
import { projectKnowledgeApi, type KnowledgeAnalysis, type Proof } from '../lib/projectKnowledge';
import { Pagination } from './IdentityPickers';
import './project-knowledge.css';

const states:Record<string,string>={satisfied:'Justifiée, à confirmer',partial:'Partiellement justifiée',not_satisfied:'Écart documenté',unclear:'À vérifier',unknown:'Sans justificatif'};
const jobs:Record<string,string>={queued:'En attente du premier passage',waiting_idle:'En attente de disponibilité du modèle',waiting_model:'Modèle indisponible ou désactivé',running:'Analyse en cours',failed:'Analyse interrompue, reprise automatique prévue',completed:'Analyse terminée'};
const dateLabel=(value?:string|null)=>value?new Date(value).toLocaleString('fr-FR'):'Après disponibilité du modèle';
function Evidence({proof}:{proof:Proof}) {return <details><summary>Voir le justificatif</summary><blockquote>{proof.quote}</blockquote><small>{proof.sources.length?`Sources : ${proof.sources.join(', ')}`:'Validation manuelle'} · Référence : {proof.knowledge_id}</small></details>;}
export function ProjectKnowledgePanel({projectId,active=true}:{projectId:string;active?:boolean}) {
  const [data,setData]=useState<KnowledgeAnalysis|null>(null),[error,setError]=useState(''),[offset,setOffset]=useState(0),[tick,setTick]=useState(0);
  useEffect(()=>{if(!active)return;const controller=new AbortController();let timer:ReturnType<typeof setTimeout>;
    const load=async(quiet=false)=>{try {const result=await (quiet?projectKnowledgeApi.read(projectId,offset,controller.signal,true):projectKnowledgeApi.read(projectId,offset,controller.signal));if(controller.signal.aborted)return;setData(result);setError('');}
      catch(e){if(!controller.signal.aborted)setError(e instanceof Error?e.message:'Analyse indisponible');}
      finally {if(!controller.signal.aborted)timer=setTimeout(()=>void load(true),15000);}};
    void load();return()=>{controller.abort();clearTimeout(timer);};
  },[projectId,active,offset,tick]);
  useEffect(()=>{setData(null);setOffset(0);setError('');},[projectId]);
  return <section className="project-knowledge" aria-label="Informations à vérifier">
    {error&&<p role="alert">{error}</p>}
    {data?.error&&<p role="alert">{data.error} · Reprise : {dateLabel(data.retry_after)}</p>}
    <details className="knowledge-disclosure"><summary><strong>Informations à vérifier</strong><span>{!data?'Chargement…':!data.enabled?'Analyse désactivée':data.report.completed_at?`${data.total} exigences examinées${data.stale?' · Bilan à actualiser':''}`:jobs[data.status]||data.status}</span></summary>
    <div className="knowledge-disclosure-content"><div className="cockpit-heading"><h4>Propositions de l’IA</h4>
      <button className="button secondary sm" type="button" disabled={!active} onClick={()=>setTick(value=>value+1)}>Actualiser l’analyse</button></div>
    {data&&<><p role="status">{!data.enabled?'Analyse automatique désactivée':jobs[data.status]||data.status}{data.total_batches?` · ${data.cursor}/${data.total_batches} lots traités`:''}</p>
      {data.report.completed_at&&<><p>Dernier bilan : {dateLabel(data.report.completed_at)} · {data.report.knowledge_count} informations examinées</p>
        {data.stale&&<p className="planning-note">Les informations ou le CDC ont changé depuis ce bilan. Une nouvelle analyse est nécessaire.</p>}
        <p>Ces évaluations IA sont à confirmer. Les validations et dates saisies restent conservées.</p>
        <div className="knowledge-counts">{Object.entries(data.report.counts||{}).map(([state,count])=><span key={state}>{states[state]} : {count}</span>)}</div>
        <details><summary>Dates proposées et points importants</summary>{(data.report.dates||[]).map((row,index)=><article key={`d-${index}`}><strong>{row.title} · {{contractual_date:'Contractuelle',forecast_date:'Prévisionnelle',actual_date:'Réelle'}[row.date_type]||row.date_type} · {row.date}</strong><Evidence proof={row}/></article>)}
          {(data.report.highlights||[]).map((row,index)=><article key={`h-${index}`}><p>{row.reason}</p><Evidence proof={row}/></article>)}
          {!data.report.dates?.length&&!data.report.highlights?.length&&<p>Aucune date ni point important étayé identifié.</p>}
          {((data.report.dates_total||0)>50||(data.report.highlights_total||0)>50)&&<p>Affichage limité aux 50 premiers éléments de chaque catégorie ; le bilan conserve {data.report.dates_total} dates et {data.report.highlights_total} points.</p>}</details>
        {!!data.items.length&&<div className="knowledge-table"><table><thead><tr><th>Fonction / contrainte / exigence</th><th>Évaluation proposée</th><th>Justification</th></tr></thead><tbody>{data.items.map(row=><tr key={row.id}><td>{row.human_id&&<small>{row.human_id} · </small>}{row.title}</td><td>{states[row.state]||row.state}</td><td><p>{row.reason}</p>{row.proofs.map((proof,index)=><Evidence key={index} proof={proof}/>)}</td></tr>)}</tbody></table></div>}
        {!data.total&&<p>Aucune fonction, contrainte ou exigence CDC à évaluer sur ce projet.</p>}
        <Pagination offset={offset} total={data.total} limit={20} onChange={setOffset}/></>}
      <details><summary>Fonctionnement de l’analyse</summary><p>Passage automatique toutes les {data.interval_hours} h, projet par projet, lorsque le modèle est libre dans Agent. Prochain passage : {dateLabel(data.next_due)}.</p></details>
    </>}</div></details>
  </section>;
}
