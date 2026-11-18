import { useMemo, useState } from 'react';
import { priorityLabels, taskStatusLabels, workflowLabels, type PlanningDiff } from '../lib/projectPlanning';
import { Pagination } from './IdentityPickers';
import { SourceInspector } from './SourceInspector';

export const planningFieldLabels:Record<string,string>={title:'Intitulé',code:'Code',order:'Position',status:'État',workflow_status:'Workflow',comment:'Commentaire',active:'Actif',
  contractual_date:'Date contractuelle',forecast_date:'Date prévisionnelle',actual_date:'Date réelle',due_date:'Échéance',date_sources:'Sources des dates',
  parent_id:'Tâche parente',milestone_id:'Jalon de rattachement',responsible_id:'Responsable',priority:'Priorité',start_date:'Début',end_date:'Fin',planned_hours:'Charge (h)',
  planned_end_date:'Fin prévisionnelle du projet',budget_hours:'Budget d’heures du projet',design:'Bureau d’études',manufacturing:'Fabrication',template_id:'Modèle',template_key:'Clé du modèle',version_id:'Version de modèle',
  excluded_dates:'Dates exclues',inputs:'Paramètres d’application',label:'Nom de la référence',kind:'Type de référence',sha256:'Empreinte',baseline_id:'Référence figée',
  candidate_id:'Proposition',meeting_id:'Réunion',action_id:'Action de réunion',preview_sha256:'Empreinte de l’aperçu',quote:'Citation',source_id:'Source',artifact_id:'Texte source',path:'Chemin',field:'Champ',actor_id:'Opérateur'};
export const baselineKindLabels={initial:'Initiale',contractual:'Contractuelle',review:'Revue',amendment:'Avenant'};
export type VisibleChange={kind:'tasks'|'milestones'|'project'|'metadata';id:string;title?:string;field:string|null;severity:'high'|'normal';before:unknown;after:unknown};
const same=(a:unknown,b:unknown)=>JSON.stringify(a)===JSON.stringify(b);
function rows(value:Record<string,unknown>,kind:'tasks'|'milestones'):Record<string,unknown>[] {
  const list=Array.isArray(value[kind])?value[kind] as Record<string,unknown>[]:[];
  const single=value[kind==='tasks'?'task':'milestone'];
  return single&&typeof single==='object'&&!Array.isArray(single)?[...list,single as Record<string,unknown>]:list;
}
export function historyChanges(previous:Record<string,unknown>,value:Record<string,unknown>):VisibleChange[] {
  const result:VisibleChange[]=[];
  for(const kind of ['tasks','milestones'] as const) {
    const before=new Map(rows(previous,kind).map(row=>[String(row.id),row]));const after=new Map(rows(value,kind).map(row=>[String(row.id),row]));
    for(const id of new Set([...before.keys(),...after.keys()])) {
      const left=before.get(id),right=after.get(id);const title=String(right?.title||left?.title||id);
      if(!left||!right){result.push({kind,id,title,field:null,severity:'high',before:left||null,after:right||null});continue;}
      for(const field of new Set([...Object.keys(left),...Object.keys(right)])) if(field!=='id'&&!same(left[field],right[field]))
        result.push({kind,id,title,field,severity:['actual_date','contractual_date','parent_id','milestone_id'].includes(field)?'high':'normal',before:left[field]??null,after:right[field]??null});
    }
  }
  const left=previous.project as Record<string,unknown>|undefined,right=value.project as Record<string,unknown>|undefined;
  if(left||right)for(const field of new Set([...Object.keys(left||{}),...Object.keys(right||{})]))if(!same(left?.[field],right?.[field]))
    result.push({kind:'project',id:'project',title:'Projet',field,severity:'high',before:left?.[field]??null,after:right?.[field]??null});
  const collections=new Set(['tasks','milestones','task','milestone','project']);
  for(const field of new Set([...Object.keys(previous),...Object.keys(value)])) if(!collections.has(field)&&!same(previous[field],value[field]))
    result.push({kind:'metadata',id:field,title:'Planning / référence',field,severity:'normal',before:previous[field]??null,after:value[field]??null});
  return result;
}
export function PlanningValue({value,field,onSource}:{value:unknown;field?:string|null;onSource?:(id:string)=>void}) {
  if(value===null||value===undefined||value==='')return <span className="muted">Non renseigné</span>;
  if(typeof value==='boolean')return <span>{value?'Oui':'Non'}</span>;
  if(typeof value==='number')return <span>{value.toLocaleString('fr-FR')}{field==='planned_hours'||field==='budget_hours'?' h':''}</span>;
  if(typeof value==='string') {
    const label=field==='status'?taskStatusLabels[value as keyof typeof taskStatusLabels]:field==='workflow_status'?workflowLabels[value as keyof typeof workflowLabels]:field==='priority'?priorityLabels[value as keyof typeof priorityLabels]:undefined;
    return <span>{label||(/^\d{4}-\d\d-\d\d$/.test(value)?value.split('-').reverse().join('/'):value)}</span>;
  }
  if(Array.isArray(value))return <details className="planning-value-details"><summary>{value.length} élément(s)</summary><pre>{JSON.stringify(value,null,2)}</pre></details>;
  const object=value as Record<string,unknown>;
  return <details className="planning-value-details"><summary>{typeof object.title==='string'?object.title:typeof object.label==='string'?object.label:'Voir les champs et sources'}</summary>
    {typeof object.source_id==='string'&&onSource&&<button type="button" className="button secondary sm" onClick={()=>onSource(object.source_id as string)}>Consulter la source citée</button>}
    <dl>{Object.entries(object).map(([key,item])=><div key={key}><dt>{key==='label'&&object.kind?'Libellé':key==='kind'?'Type':planningFieldLabels[key]||key}</dt><dd><PlanningValue value={item} field={key} onSource={onSource}/></dd></div>)}</dl></details>;
}
export function PlanningChanges({changes,plannedHoursDelta,projectBudgetHoursDelta,projectUnavailable}:{changes:VisibleChange[];plannedHoursDelta?:number;projectBudgetHoursDelta?:number|null;projectUnavailable?:boolean}) {
  const [kind,setKind]=useState('all');const [severity,setSeverity]=useState('all');const [search,setSearch]=useState('');const [offset,setOffset]=useState(0);
  const [sourceId,setSourceId]=useState<string|null>(null);
  const filtered=useMemo(()=>changes.filter(row=>(kind==='all'||row.kind===kind)&&(severity==='all'||row.severity===severity)&&
    `${row.title||''} ${planningFieldLabels[row.field||'']||row.field||''}`.toLocaleLowerCase('fr').includes(search.toLocaleLowerCase('fr'))),[changes,kind,severity,search]);
  const safeOffset=offset>=filtered.length?0:offset;const page=filtered.slice(safeOffset,safeOffset+25);
  const counts={added:changes.filter(row=>!row.field&&row.before==null).length,removed:changes.filter(row=>!row.field&&row.after==null).length,high:changes.filter(row=>row.severity==='high').length};
  return <section className="planning-changes" aria-label="Écarts détaillés">
    <div className="planning-diff-counts"><span>{changes.length} écart(s)</span><span>{counts.added} ajout(s)</span><span>{counts.removed} retrait(s)</span><span>{counts.high} majeur(s)</span>
      {plannedHoursDelta!==undefined&&<strong>Variation de charge : {plannedHoursDelta>0?'+':''}{plannedHoursDelta.toLocaleString('fr-FR')} h</strong>}
      {projectBudgetHoursDelta!=null&&<strong>Variation du budget d’heures : {projectBudgetHoursDelta>0?'+':''}{projectBudgetHoursDelta.toLocaleString('fr-FR')} h</strong>}</div>
    {projectUnavailable&&<p className="planning-note">Ancienne référence : les dates et le budget d’heures du projet n’ont pas été capturés et ne sont pas comparables. Aucun engagement passé n’est reconstitué.</p>}
    <div className="planning-toolbar"><label>Rechercher un écart<input className="input" type="search" value={search} onChange={e=>{setSearch(e.target.value);setOffset(0);}}/></label>
      <label>Type d’élément<select className="input" value={kind} onChange={e=>{setKind(e.target.value);setOffset(0);}}><option value="all">Tous</option><option value="project">Projet</option><option value="milestones">Jalons</option><option value="tasks">Tâches</option><option value="metadata">Planning / référence</option></select></label>
      <label>Sévérité<select className="input" value={severity} onChange={e=>{setSeverity(e.target.value);setOffset(0);}}><option value="all">Toutes</option><option value="high">Majeure</option><option value="normal">Normale</option></select></label></div>
    <Pagination offset={safeOffset} total={filtered.length} limit={25} onChange={setOffset}/>
    {!filtered.length?<p>{changes.length?'Aucun écart ne correspond aux filtres.':'Aucun écart sur les jalons et tâches comparés.'}</p>:<div className="planning-table-scroll"><table className="data-table planning-diff-table"><thead><tr><th>Élément</th><th>Champ / opération</th><th>Sévérité</th><th>Avant</th><th>Après</th></tr></thead><tbody>
      {page.map((row,index)=><tr key={`${row.kind}-${row.id}-${row.field}-${index}`}><td><strong>{row.title||row.id}</strong><small>{row.kind==='tasks'?'Tâche':row.kind==='milestones'?'Jalon':row.kind==='project'?'Projet':'Planning / référence'}</small></td>
        <td>{row.field?planningFieldLabels[row.field]||row.field:row.before==null?'Ajout':'Retrait'}</td><td><span className={`badge ${row.severity==='high'?'danger':'neutral'}`}>{row.severity==='high'?'Majeure':'Normale'}</span></td>
        <td><PlanningValue value={row.before} field={row.field} onSource={setSourceId}/></td><td><PlanningValue value={row.after} field={row.field} onSource={setSourceId}/></td></tr>)}</tbody></table></div>}
    {sourceId&&<SourceInspector sourceId={sourceId} onClose={()=>setSourceId(null)}/>}
  </section>;
}
export function DiffDetails({diff}:{diff:PlanningDiff}) {return <PlanningChanges changes={diff.changes} plannedHoursDelta={diff.planned_hours_delta} projectBudgetHoursDelta={diff.project_budget_hours_delta} projectUnavailable={diff.baseline_revision!==undefined&&diff.project_comparison_available===false}/>;}
