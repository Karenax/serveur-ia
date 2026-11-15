import { useCallback, useEffect, useRef, useState } from 'react';
import { planningApi, priorityLabels, taskStatusLabels, type ItemDetail, type ItemPage, type PlanningInfo, type PlanningTask, type TaskInput, type TaskStatus, type Priority } from '../lib/projectPlanning';
import { Pagination, PersonPicker, Picker } from './IdentityPickers';
import { ErrorState, LoadingState } from './Ui';
import '../project-planning.css';

export const message=(error:unknown)=>error instanceof Error?error.message:String(error);
export function useAlive() {const alive=useRef(true);useEffect(()=>{alive.current=true;return()=>{alive.current=false;};},[]);return alive;}
export function focusPlanning(element:HTMLElement|null) {element?.focus({preventScroll:true});element?.scrollIntoView?.({block:'start'});}
export function useEditorFocus() {const ref=useRef<HTMLFormElement>(null);useEffect(()=>{focusPlanning(ref.current);},[]);return ref;}
export function changedFields<T extends object>(before:T,after:T):Partial<T> {
  return Object.fromEntries(Object.entries(after).filter(([key,value])=>JSON.stringify(value)!==JSON.stringify(before[key as keyof T]))) as Partial<T>;
}
export function PlanningTasksPanel(props:{projectId:string;active?:boolean;onSaved:()=>void}) {
  return <TasksView key={props.projectId} {...props}/>;
}
function TasksView({projectId,active=true,onSaved}:{projectId:string;active?:boolean;onSaved:()=>void}) {
  const [search,setSearch]=useState('');const [offset,setOffset]=useState(0);const [archived,setArchived]=useState(false);
  const [page,setPage]=useState<ItemPage<PlanningTask>|null>(null);const [info,setInfo]=useState<PlanningInfo|null>(null);
  const [loading,setLoading]=useState(true);const [error,setError]=useState('');const [tick,setTick]=useState(0);
  const [editor,setEditor]=useState<ItemDetail<PlanningTask>|null>(null);const [opening,setOpening]=useState(false);const [notice,setNotice]=useState('');
  const alive=useAlive();const openGeneration=useRef(0);
  useEffect(()=>{if(!active)return;const controller=new AbortController();setLoading(true);setError('');
    const timer=window.setTimeout(()=>{Promise.all([planningApi.info(projectId,controller.signal),planningApi.tasks(projectId,{search,offset,include_inactive:archived,signal:controller.signal})])
      .then(([state,values])=>{if(!controller.signal.aborted){setInfo(state);setPage(values);}})
      .catch(e=>{if(!controller.signal.aborted)setError(message(e));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});},150);
    return()=>{controller.abort();window.clearTimeout(timer);};},[projectId,active,search,offset,archived,tick]);
  async function edit(row:PlanningTask) {if(opening)return;const generation=++openGeneration.current;setOpening(true);setError('');setNotice('');
    try {const value=await planningApi.task(projectId,row.id);if(alive.current&&generation===openGeneration.current)setEditor(value);}
    catch(e){if(alive.current&&generation===openGeneration.current)setError(message(e));}
    finally{if(alive.current&&generation===openGeneration.current)setOpening(false);}}
  const saved=()=>{if(!alive.current)return;setEditor(null);setNotice('Tâche enregistrée.');setTick(value=>value+1);onSaved();};
  return <section className="planning-panel" aria-label="Tâches et charges du projet">
    <header className="planning-heading"><div><h3>Tâches et charges</h3></div>
      {info?.can_edit&&<button type="button" className="button primary" disabled={loading||opening||!!editor} onClick={()=>{setNotice('');setEditor({item:emptyTask(),revision:page?.revision??info.revision,can_edit:true,children_total:0});}}>Nouvelle tâche</button>}</header>
    <div className="planning-toolbar"><label>Rechercher une tâche<input className="input" type="search" value={search} maxLength={200} onChange={e=>{setSearch(e.target.value);setOffset(0);}}/></label>
      <label className="identity-checkbox"><input type="checkbox" checked={archived} onChange={e=>{setArchived(e.target.checked);setOffset(0);}}/>Inclure les tâches archivées</label>
      <button type="button" className="button secondary sm" disabled={loading} onClick={()=>setTick(value=>value+1)}>Recharger la liste</button></div>
    {notice&&<p role="status" className="planning-notice">{notice}</p>}{error&&<ErrorState message={error} retry={()=>setTick(value=>value+1)}/>}
    {loading&&<LoadingState label="Chargement des tâches"/>}{opening&&<p role="status">Chargement de la tâche…</p>}
    {editor&&<TaskEditor key={editor.item.id||'new'} projectId={projectId} initial={editor} onCancel={()=>setEditor(null)} onSaved={saved}/>}
    {page&&<><Pagination offset={page.offset} total={page.total} limit={page.limit} onChange={setOffset} disabled={loading}/>
      {!page.items.length&&!loading&&<p>Aucune tâche ne correspond à ces filtres.</p>}
      <div className="planning-table-scroll"><table className="data-table planning-task-table"><thead><tr><th>Tâche / parent</th><th>État</th><th>Responsable / jalon</th><th>Dates</th><th>Charge</th><th>Priorité / métier</th><th>Action</th></tr></thead>
        <tbody>{page.items.map(row=><tr key={row.id} className={!row.active?'planning-archived':undefined}><td><strong>{row.title}</strong>{row.parent_id&&<small>↳ {row.parent_title||'Parent attribué'}</small>}{!row.active&&<span className="badge neutral">Archivée</span>}</td>
          <td><span className={`badge ${row.status==='blocked'?'danger':row.status==='done'?'ok':'neutral'}`}>{taskStatusLabels[row.status]}</span></td>
          <td>{row.responsible_name||'Non affectée'}<small>{row.milestone_title||'Sans jalon'}</small></td><td>{row.start_date||'Début à préciser'}<small>→ {row.end_date||'Fin à préciser'}</small></td>
          <td className="numeric">{row.planned_hours.toLocaleString('fr-FR')} h</td><td>{priorityLabels[row.priority]}<small>{[row.design?'BE':'',row.manufacturing?'Fabrication':''].filter(Boolean).join(' · ')||'Métier à préciser'}</small></td>
          <td><button type="button" className="button secondary sm" aria-label={`${info?.can_edit?'Modifier':'Consulter'} · ${row.title}`} disabled={loading||opening||!!editor} onClick={()=>void edit(row)}>{info?.can_edit?'Modifier':'Consulter'}</button></td></tr>)}</tbody></table></div></>}
  </section>;
}
function emptyTask():PlanningTask {return {id:'',title:'',status:'todo',due_date:'',parent_id:null,milestone_id:null,responsible_id:null,template_id:null,template_key:null,priority:'normal',start_date:'',end_date:'',planned_hours:0,design:false,manufacturing:false,comment:'',active:true};}
function taskInput(row:PlanningTask):TaskInput&{title:string} {return {title:row.title,status:row.status,parent_task_id:row.parent_id,milestone_id:row.milestone_id,responsible_id:row.responsible_id,priority:row.priority,start_date:row.start_date,end_date:row.end_date,planned_hours:row.planned_hours,design:row.design,manufacturing:row.manufacturing,comment:row.comment,active:row.active};}
export function PlanningRelationPicker({projectId,kind,label,value,current,onChange,onPick,disabled,excludeId,allowedIds}:{projectId:string;kind:'tasks'|'milestones';label:string;value:string|null;current?:{id:string;title:string}|null;onChange:(id:string|null)=>void;onPick?:(row:PlanningTask|import('../lib/projectPlanning').PlanningMilestone|null)=>void;disabled?:boolean;excludeId?:string;allowedIds?:string[]}) {
  const load=useCallback(async(search:string,offset:number,signal:AbortSignal)=>kind==='tasks'?planningApi.tasks(projectId,{search,offset,limit:50,signal}):planningApi.milestones(projectId,{search,offset,limit:50,signal}),[projectId,kind]);
  return <Picker<{id:string;title:string;active:boolean}> label={label} value={value} current={current?{...current,active:true}:null} onChange={onChange} onPick={row=>onPick?.(row as PlanningTask|import('../lib/projectPlanning').PlanningMilestone|null)} load={load} display={row=>row.title} disabled={disabled} optionDisabled={row=>row.id===excludeId||!!allowedIds&&!allowedIds.includes(row.id)}/>;
}
export function TaskEditor({projectId,initial,onCancel,onSaved}:{projectId:string;initial:ItemDetail<PlanningTask>;onCancel:()=>void;onSaved:()=>void}) {
  const [base,setBase]=useState(initial);const [draft,setDraft]=useState(()=>taskInput(initial.item));const [busy,setBusy]=useState(false);const [error,setError]=useState('');
  const [latest,setLatest]=useState<ItemDetail<PlanningTask>|null>(null);const alive=useAlive();
  const creating=!base.item.id;const patches=changedFields(taskInput(base.item),draft);const group=!!base.children_total;const readOnly=!base.can_edit;
  const change=(key:keyof TaskInput,value:unknown)=>{setDraft(previous=>({...previous,[key]:value}));setLatest(null);};
  async function save() {if(busy||readOnly||latest)return;
    if(draft.status==='assigned'&&!draft.responsible_id){setError('Choisir un responsable pour une tâche affectée.');return;}
    setBusy(true);setError('');try {if(creating)await planningApi.createTask(projectId,base.revision,draft);else await planningApi.patchTask(projectId,base.item.id,base.revision,patches);
      if(alive.current)onSaved();}catch(e){if(alive.current)setError(message(e));}finally{if(alive.current)setBusy(false);}}
  async function loadLatest() {if(busy)return;setBusy(true);try {const result=creating?await planningApi.info(projectId).then(state=>({...base,revision:state.revision,can_edit:state.can_edit})):await planningApi.task(projectId,base.item.id);if(alive.current)setLatest(result);}
    catch(e){if(alive.current)setError(message(e));}finally{if(alive.current)setBusy(false);}}
  const disabled=busy||readOnly;const editorFocus=useEditorFocus();
  return <form ref={editorFocus} tabIndex={-1} className="card planning-editor" aria-label={creating?'Nouvelle tâche':'Édition de la tâche'} data-workspace-dirty={!readOnly&&Object.keys(patches).length?'true':undefined} onSubmit={e=>{e.preventDefault();void save();}}>
    <div className="planning-heading"><h3>{creating?'Nouvelle tâche':readOnly?'Consulter la tâche':'Modifier la tâche'}</h3><span>Révision {base.revision}</span></div>
    {error&&<p role="alert" className="planning-error">{error} Votre saisie est conservée.</p>}
    {latest&&<section className="planning-conflict" aria-label="Comparaison avec la dernière révision"><h4>Version actuelle : révision {latest.revision}</h4><p>{creating?'Le projet a changé pendant la création. Votre nouvelle tâche reste un brouillon ; préparer son enregistrement sur la révision actuelle.':'Comparer vos champs modifiés avant de préparer une nouvelle sauvegarde.'}</p>
      <table className="data-table"><thead><tr><th>Champ</th><th>Au début</th><th>Actuellement</th><th>Votre saisie</th></tr></thead><tbody>{Object.entries(patches).map(([key,value])=><tr key={key}><td>{taskFieldLabels[key]||key}</td><td>{String(taskInput(base.item)[key as keyof TaskInput]??'—')}</td><td>{String(taskInput(latest.item)[key as keyof TaskInput]??'—')}</td><td>{String(value??'—')}</td></tr>)}</tbody></table>
      <button className="button secondary" type="button" disabled={busy} onClick={()=>{setDraft({...taskInput(latest.item),...patches});setBase(latest);setLatest(null);setError('');}}>Préparer mon brouillon sur cette révision</button></section>}
    <div className="planning-form-grid"><label>Intitulé de la tâche<input className="input" value={draft.title} required maxLength={255} disabled={disabled} onChange={e=>change('title',e.target.value)}/></label>
      <label>État de la tâche<select className="input" value={draft.status} disabled={disabled} onChange={e=>change('status',e.target.value as TaskStatus)}>{Object.entries(taskStatusLabels).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
      <PlanningRelationPicker projectId={projectId} kind="tasks" label="Tâche parente" value={draft.parent_task_id||null} current={base.parent} excludeId={base.item.id} onChange={value=>change('parent_task_id',value)} disabled={disabled}/>
      <PlanningRelationPicker projectId={projectId} kind="milestones" label="Jalon de rattachement" value={draft.milestone_id||null} current={base.milestone} onChange={value=>change('milestone_id',value)} disabled={disabled}/>
      <PersonPicker label="Responsable de la tâche" value={draft.responsible_id||null} current={base.responsible} onChange={value=>change('responsible_id',value)} disabled={disabled}/>
      <label>Priorité<select className="input" value={draft.priority} disabled={disabled} onChange={e=>change('priority',e.target.value as Priority)}>{Object.entries(priorityLabels).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
      <label>Début de la tâche<input className="input" type="date" value={draft.start_date} disabled={disabled||group} onChange={e=>change('start_date',e.target.value)}/></label>
      <label>Fin de la tâche<input className="input" type="date" value={draft.end_date} min={draft.start_date||undefined} disabled={disabled||group} onChange={e=>change('end_date',e.target.value)}/></label>
      <label>Charge prévue (h)<input className="input" type="number" min={0} max={1000000} step="any" value={draft.planned_hours} disabled={disabled||group} onChange={e=>change('planned_hours',Number(e.target.value))}/></label>
    </div>
    {group&&<p className="planning-note">Ce groupe contient {base.children_total} tâche(s). Ses dates et sa charge sont calculées à partir des enfants actifs.</p>}
    {base.item.template_key&&<details><summary>Origine de la tâche</summary><p className="planning-note">Tâche issue d’un modèle · référence « {base.item.template_key} ».</p></details>}
    <div className="planning-checks"><label><input type="checkbox" checked={draft.design} disabled={disabled} onChange={e=>change('design',e.target.checked)}/>Bureau d’études</label>
      <label><input type="checkbox" checked={draft.manufacturing} disabled={disabled} onChange={e=>change('manufacturing',e.target.checked)}/>Fabrication</label>
      <label><input type="checkbox" checked={draft.active} disabled={disabled} onChange={e=>change('active',e.target.checked)}/>Tâche active</label></div>
    <p className="planning-note">Archiver conserve la tâche et son historique. Un groupe ayant des enfants actifs ne peut pas être archivé.</p>
    <label>Commentaire de la tâche<textarea className="input" rows={3} value={draft.comment} maxLength={20000} disabled={disabled} onChange={e=>change('comment',e.target.value)}/></label>
    <div className="planning-actions">{!readOnly&&<button className="button primary" type="submit" disabled={busy||!!latest||!draft.title.trim()||!creating&&!Object.keys(patches).length}>{busy?'Enregistrement…':'Enregistrer la tâche'}</button>}
      {error&&<button className="button secondary" type="button" disabled={busy} onClick={()=>void loadLatest()}>Recharger et comparer sans perdre ma saisie</button>}
      <button className="button secondary" type="button" disabled={busy} onClick={onCancel}>{readOnly?'Fermer la tâche':'Annuler le brouillon'}</button></div>
  </form>;
}
const taskFieldLabels:Record<string,string>={title:'Intitulé',status:'État',priority:'Priorité',parent_task_id:'Parent',milestone_id:'Jalon',responsible_id:'Responsable',start_date:'Début',end_date:'Fin',planned_hours:'Heures',design:'BE',manufacturing:'Fabrication',comment:'Commentaire',active:'Activation'};
