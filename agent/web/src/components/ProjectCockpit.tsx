import { useCallback, useEffect, useRef, useState } from 'react';
import { cockpitApi, type CockpitAlert, type CockpitDocument, type CockpitStructure } from '../lib/projectCockpit';
import { planningApi, taskStatusLabels, workflowLabels, type ItemDetail, type ItemPage, type PlanningMilestone, type PlanningTask } from '../lib/projectPlanning';
import { deliverableApi, documentLabels, deliverableVersionLabel, type DeliverableDetail, type DeliverableFocus } from '../lib/projectDeliverables';
import { useDebouncedValue } from '../hooks/useDebouncedValue';
import { TaskEditor, message } from './PlanningTasksPanel';
import { MilestoneEditor } from './PlanningMilestonesPanel';
import { Pagination } from './IdentityPickers';
import { ErrorState, LoadingState } from './Ui';
import './project-cockpit.css';
import { ProjectKnowledgePanel } from './ProjectKnowledgePanel';

type Props={projectId:string;active?:boolean;revision?:number;onSaved:()=>void;
  onOpenDeliverable:(focus:Omit<DeliverableFocus,'requestId'>)=>void;onOpenPlanning:()=>void;onOpenCdc:()=>void};
type Context={id:string;title:string}|null;
type Inspection={kind:'task';data:ItemDetail<PlanningTask>}|{kind:'milestone';data:ItemDetail<PlanningMilestone>;workflow:{code:string;title:string}[]}
  |{kind:'document';data:DeliverableDetail};
const dateLabel=(value?:string)=>value?value.split('-').reverse().join('/'):'À renseigner';
const alertLabels:Record<string,string>={overdue:'En retard',blocked:'Bloqué',document_review:'Document à revoir',date_proposal:'Date à vérifier',cdc_review:'CDC à confirmer',open_point:'Point ouvert'};

function useRead<T>(active:boolean,load:(signal:AbortSignal)=>Promise<T>) {
  const [loaded,setLoaded]=useState<{load:typeof load;data:T}|null>(null),[error,setError]=useState(''),[loading,setLoading]=useState(false),[tick,setTick]=useState(0);
  useEffect(()=>{if(!active)return;const controller=new AbortController();setLoading(true);setError('');setLoaded(null);
    void load(controller.signal).then(value=>{if(!controller.signal.aborted)setLoaded({load,data:value});}).catch(e=>{if(!controller.signal.aborted)setError(message(e));})
      .finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return()=>controller.abort();
  },[active,load,tick]);
  return {data:active&&loaded?.load===load?loaded.data:null,error,loading,retry:()=>setTick(value=>value+1)};
}

export function ProjectCockpit(props:Props) {return <Cockpit key={props.projectId} {...props}/>;}
function Cockpit({projectId,active=true,revision,onSaved,onOpenDeliverable,onOpenPlanning,onOpenCdc}:Props) {
  const [search,setSearch]=useState(''),[past,setPast]=useState(false),[offset,setOffset]=useState(0),[layer,setLayer]=useState<'all'|'tasks'|'documents'>('all');
  const [compact,setCompact]=useState(true);
  const [context,setContext]=useState<Context>(null),[tick,setTick]=useState(0),[inspection,setInspection]=useState<Inspection|null>(null);
  const [target,setTarget]=useState<{kind:'task'|'milestone'|'document'|'create';id:string;title:string}|null>(null);
  const root=useRef<HTMLElement>(null),inspector=useRef<HTMLElement>(null),filtered=useDebouncedValue(search);
  useEffect(()=>setOffset(0),[filtered,past]);
  const load=useCallback((signal:AbortSignal)=>cockpitApi.structure(projectId,{search:filtered,show_past:past,offset,limit:25,signal}),[projectId,filtered,past,offset,tick,revision]);
  const graph=useRead(active,load);
  const loadInspector=useCallback(async(signal:AbortSignal):Promise<Inspection>=>{
    if(!target)throw new Error('Choisir un élément à consulter.');
    if(target.kind==='document')return {kind:'document',data:await deliverableApi.detail(projectId,target.id,signal)};
    if(target.kind==='task')return {kind:'task',data:await planningApi.task(projectId,target.id,signal)};
    const info=await planningApi.info(projectId,signal);
    if(target.kind==='milestone'){
      const data=await planningApi.milestone(projectId,target.id,signal);
      if(data.revision!==info.revision)throw new Error('Le projet a changé. Relancer le chargement de cet élément.');
      return {kind:'milestone',data,workflow:info.workflow};
    }
    const item:PlanningTask={id:'',title:'',status:'todo',due_date:'',parent_id:null,milestone_id:context&&context.id!=='unassigned'?context.id:null,
      responsible_id:null,template_id:null,template_key:null,priority:'normal',start_date:'',end_date:'',planned_hours:0,design:false,manufacturing:false,comment:'',active:true};
    return {kind:'task',data:{item,revision:info.revision,can_edit:info.can_edit,milestone:item.milestone_id?context:null}};
  },[projectId,target,context]);
  const detail=useRead(active&&!!target&&!inspection,loadInspector);
  useEffect(()=>{if(target&&detail.data&&!inspection)setInspection(detail.data);},[target,detail.data,inspection]);
  useEffect(()=>{if(inspection?.kind==='document')inspector.current?.focus({preventScroll:true});},[inspection]);
  const locked=!!target;
  function select(kind:'task'|'milestone'|'document'|'create',id:string,title:string) {if(locked)return;setTarget({kind,id,title});}
  function close() {setTarget(null);setInspection(null);requestAnimationFrame(()=>root.current?.focus({preventScroll:true}));}
  function saved() {close();setTick(value=>value+1);onSaved();}
  function refresh() {setTick(value=>value+1);}
  const openDocument=(id:string,title:string)=>{const focus={deliverableId:id,checkId:'',milestoneId:context&&context.id!=='unassigned'?context.id:'',milestoneTitle:context?.title||title,version:null,origin:'cockpit' as const};close();onOpenDeliverable(focus);};
  const inspectAlert=(row:CockpitAlert)=>{if(['task','milestone','deliverable'].includes(row.entity_kind))select(row.entity_kind==='deliverable'?'document':row.entity_kind as 'task'|'milestone',row.id,row.title);
    else if(row.entity_kind==='candidate')onOpenPlanning();else onOpenCdc();};
  return <section ref={root} tabIndex={-1} className={`project-cockpit${compact?' compact':''}`} aria-label="Vue d’ensemble du projet">
    <div className="cockpit-heading"><h3>Vue d’ensemble</h3></div>
    {graph.error&&<ErrorState message={graph.error} retry={graph.retry}/>}
    {graph.loading&&<LoadingState label="Chargement des jalons et compteurs"/>}
    {graph.data&&<CockpitSummary data={graph.data}/>}
    <CockpitAlerts projectId={projectId} active={active} tick={tick} revision={revision} graphRevision={graph.data?.revision} locked={locked} onSelect={inspectAlert} onRefresh={refresh}/>
    <ProjectKnowledgePanel key={projectId} projectId={projectId} active={active}/>
    <div className="cockpit-controls"><label>Rechercher dans le projet<input className="input" value={search} maxLength={200} placeholder="Échéance, tâche, document…" onChange={e=>setSearch(e.target.value)}/></label>
    <details className="cockpit-display-options"><summary>Options d’affichage</summary><div className="cockpit-controls">
      <label>Afficher<select className="input" value={layer} onChange={e=>setLayer(e.target.value as typeof layer)}><option value="all">Tâches et livrables</option><option value="tasks">Tâches</option><option value="documents">Livrables</option></select></label>
      <label className="identity-checkbox"><input type="checkbox" checked={past} onChange={e=>setPast(e.target.checked)}/>Inclure les jalons passés</label>
      <label className="identity-checkbox"><input type="checkbox" checked={compact} onChange={e=>setCompact(e.target.checked)}/>Vue compacte</label>
      <button type="button" className="button secondary sm" disabled={!active} onClick={refresh}>Actualiser la vue</button>
      <button type="button" className="button secondary sm" disabled={locked} onClick={()=>{setSearch('');setPast(false);setCompact(true);setLayer('all');setContext(null);setOffset(0);root.current?.focus({preventScroll:true});}}>Réinitialiser l’affichage</button>
    </div></details></div>
    {locked&&<p className="planning-note" role="status">Terminer ou annuler la consultation en cours pour sélectionner un autre élément. Votre saisie reste conservée pendant l’actualisation.</p>}
    <div className={`cockpit-layout${locked?' with-inspector':''}`}><div className="cockpit-main">
      {graph.data&&<section aria-label="Parcours des jalons"><div className="cockpit-contexts"><button type="button" className={`button ${!context?'primary':'secondary'} sm`} aria-pressed={!context} disabled={locked} onClick={()=>setContext(null)}>Tout le projet</button>
        <button type="button" className={`button ${context?.id==='unassigned'?'primary':'secondary'} sm`} aria-pressed={context?.id==='unassigned'} disabled={locked} onClick={()=>setContext({id:'unassigned',title:'Sans jalon'})}>Sans jalon · {graph.data.unassigned_tasks} tâches · {graph.data.unassigned_deliverables} livrables</button></div>
        {!graph.data.items.length&&<p className="cockpit-empty">{filtered?'Aucun jalon lié à cette recherche. Les éléments sans jalon restent accessibles ci-dessous.':'Aucun jalon à afficher. Créez ou activez vos jalons dans Planification.'}</p>}
        <ol className="cockpit-spine">{graph.data.items.map(row=><li key={row.id} className={`cockpit-phase ${row.workflow_status}${context?.id===row.id?' selected':''}`}>
          <div className="cockpit-phase-heading"><button type="button" className="cockpit-node" aria-label={`Sélectionner le jalon ${row.title}`} aria-pressed={context?.id===row.id} disabled={locked} onClick={()=>setContext({id:row.id,title:row.title})}>
            <small>{row.code||`Jalon ${row.order+1}`}{graph.data?.current_milestone?.id===row.id?' · En cours':''}</small><strong>{row.title}</strong><span>{workflowLabels[row.workflow_status]}</span></button>
            <button type="button" className="button secondary sm" disabled={locked} onClick={()=>select('milestone',row.id,row.title)}>Dates et détail<span className="sr-only"> · {row.title}</span></button></div>
          <dl className="cockpit-dates"><div><dt>Contractuel</dt><dd>{dateLabel(row.contractual_date)}</dd></div><div><dt>Prévisionnel</dt><dd>{dateLabel(row.forecast_date)}</dd></div><div><dt>Réel</dt><dd>{dateLabel(row.actual_date)}</dd></div></dl>
          <p>{row.task_count} tâches · {row.deliverable_count} livrables{row.past?' · Jalon passé':''}</p></li>)}</ol>
        <Pagination offset={offset} total={graph.data.total} limit={25} onChange={setOffset}/></section>}
      <section className="cockpit-relationships" aria-label="Éléments liés"><div className="cockpit-heading"><h4>{context?.title||'Éléments de tout le projet'}</h4>
        {graph.data?.can_edit&&<button type="button" className="button primary sm" disabled={locked||graph.loading} onClick={()=>select('create','',context?.title||'Tout le projet')}>Créer une tâche{context&&context.id!=='unassigned'?' sur ce jalon':''}</button>}</div>
        <div className="cockpit-layers">{layer!=='documents'&&<RelatedTasks key={`t-${context?.id||'all'}-${filtered}`} projectId={projectId} active={active} context={context} search={filtered} tick={tick} revision={revision} graphRevision={graph.data?.revision} locked={locked} onSelect={select} onRefresh={refresh}/>}
          {layer!=='tasks'&&<RelatedDocuments key={`d-${context?.id||'all'}-${filtered}`} projectId={projectId} active={active} context={context} search={filtered} tick={tick} revision={revision} graphRevision={graph.data?.revision} locked={locked} onSelect={select} onRefresh={refresh}/>}</div></section>
    </div>
    {target&&<aside ref={inspector} className="cockpit-inspector" tabIndex={-1} aria-label={`Détail · ${target.title||'Nouvelle tâche'}`}>
      {detail.loading&&<LoadingState label="Chargement du détail"/>}{detail.error&&<><ErrorState message={detail.error} retry={detail.retry}/><button type="button" className="button secondary" onClick={close}>Fermer le détail</button></>}
      {inspection?.kind==='task'&&<TaskEditor initial={inspection.data} projectId={projectId} onSaved={saved} onCancel={close}/>}
      {inspection?.kind==='milestone'&&<MilestoneEditor initial={inspection.data} workflow={inspection.workflow} projectId={projectId} active={active} onSaved={saved} onCancel={close} onOpenDeliverable={onOpenDeliverable}/>}
      {inspection?.kind==='document'&&<div className="card"><h4>{inspection.data.title}</h4><p>{documentLabels[inspection.data.document_status]}</p><p>{deliverableVersionLabel(inspection.data)}</p><p>{inspection.data.comment||'Aucun commentaire.'}</p>
        <p>{inspection.data.checklist.filter(row=>row.active&&row.completed).length} contrôles réalisés / {inspection.data.checklist.filter(row=>row.active).length} contrôles actifs</p>
        <button type="button" className="button primary" onClick={()=>openDocument(inspection.data.id,inspection.data.title)}>Ouvrir le livrable et ses preuves</button><button type="button" className="button secondary" onClick={close}>Fermer le livrable</button></div>}
    </aside>}</div>
  </section>;
}

function CockpitSummary({data}:{data:CockpitStructure}) {return <div className="cockpit-summary" aria-label="Indicateurs du projet">
  <div><small>Avancement</small><strong>{data.tasks.total?`${data.progress} %`:"Aucun planning"}</strong>{data.tasks.total>0&&<progress max={100} value={data.progress} aria-label="Avancement des tâches"/>}<span>{data.tasks.done} / {data.tasks.total} tâches terminées</span></div>
  <div><small>Charge prévue</small><strong>{data.hours.initial_hours?`${data.hours.initial_hours} h`:"Non renseignée"}</strong><span>{data.hours.consumed_hours} h consommées</span></div>
  <div><small>Reste à faire</small><strong>{data.hours.initial_hours||data.hours.consumed_hours||data.hours.remaining_mode==='reestimated'?`${data.hours.raf} h`:"À estimer"}</strong><span>{data.hours.remaining_mode==='reestimated'?'Réestimé':'Solde de charge'}{data.hours.overrun_hours>0?` · ${data.hours.overrun_hours} h dépassées`:''}</span></div>
  <div><small>À suivre</small><strong>{data.tasks.overdue} en retard</strong><span>{data.tasks.blocked} tâches bloquées · {data.deliverables_total} livrables</span></div>
</div>;}
type LayerProps={projectId:string;active:boolean;context:Context;search:string;tick:number;revision?:number;graphRevision?:number;locked:boolean;onSelect:(kind:'task'|'document',id:string,title:string)=>void;onRefresh:()=>void};
const contextOptions=(context:Context)=>({milestone_id:context&&context.id!=='unassigned'?context.id:null,unassigned:context?.id==='unassigned'});
function RevisionState({page,revision,onRefresh}:{page:{revision:number}|null;revision?:number;onRefresh:()=>void}) {return page&&revision!==undefined&&page.revision!==revision?<ErrorState message="Le projet a changé entre le chargement des jalons et de cette liste." retry={onRefresh}/>:null;}
function RelatedTasks(props:LayerProps) {
  const [offset,setOffset]=useState(0);
  const load=useCallback((signal:AbortSignal)=>cockpitApi.tasks(props.projectId,{...contextOptions(props.context),search:props.search,offset,limit:20,signal}),[props.projectId,props.context,props.search,offset,props.tick,props.revision]);
  const state=useRead(props.active,load),page=state.data,stale=page&&props.graphRevision!==undefined&&page.revision!==props.graphRevision;
  return <section className="cockpit-layer" aria-label="Tâches liées"><h5>Tâches{page&&!stale?` · ${page.total}`:''}</h5>{state.loading&&<LoadingState label="Chargement des tâches"/>}{state.error&&<ErrorState message={state.error} retry={state.retry}/>}
    <RevisionState page={page} revision={props.graphRevision} onRefresh={props.onRefresh}/>
    {page&&!stale&&<>{!page.items.length&&<p>Aucune tâche dans cette sélection.</p>}<ul className="cockpit-item-list">{page.items.map(row=><li key={row.id}><button type="button" aria-label={`Consulter la tâche ${row.title}`} disabled={props.locked} onClick={()=>props.onSelect('task',row.id,row.title)}><strong>{row.title}</strong><span>{taskStatusLabels[row.status]} · {row.planned_hours} h{row.end_date?` · ${dateLabel(row.end_date)}`:''}</span>{row.parent_title&&<small>Groupe : {row.parent_title}</small>}</button></li>)}</ul>
      <Pagination offset={offset} total={page.total} limit={20} onChange={setOffset}/></>}
  </section>;
}
function RelatedDocuments(props:LayerProps) {
  const [offset,setOffset]=useState(0);
  const load=useCallback((signal:AbortSignal)=>cockpitApi.documents(props.projectId,{...contextOptions(props.context),search:props.search,offset,limit:20,signal}),[props.projectId,props.context,props.search,offset,props.tick,props.revision]);
  const state=useRead<ItemPage<CockpitDocument>>(props.active,load),page=state.data,stale=page&&props.graphRevision!==undefined&&page.revision!==props.graphRevision;
  return <section className="cockpit-layer" aria-label="Livrables liés"><h5>Livrables{page&&!stale?` · ${page.total}`:''}</h5>{state.loading&&<LoadingState label="Chargement des livrables"/>}{state.error&&<ErrorState message={state.error} retry={state.retry}/>}
    <RevisionState page={page} revision={props.graphRevision} onRefresh={props.onRefresh}/>
    {page&&!stale&&<>{!page.items.length&&<p>Aucun livrable dans cette sélection.</p>}<ul className="cockpit-item-list">{page.items.map(row=><li key={row.id}><button type="button" aria-label={`Consulter le livrable ${row.title}`} disabled={props.locked} onClick={()=>props.onSelect('document',row.id,row.title)}><strong>{row.title}</strong><span>{documentLabels[row.document_status]} · {row.milestone_ids.length} jalon(s) lié(s)</span></button></li>)}</ul>
      <Pagination offset={offset} total={page.total} limit={20} onChange={setOffset}/></>}
  </section>;
}
function CockpitAlerts({projectId,active,tick,revision,graphRevision,locked,onSelect,onRefresh}:{projectId:string;active:boolean;tick:number;revision?:number;graphRevision?:number;locked:boolean;onSelect:(row:CockpitAlert)=>void;onRefresh:()=>void}) {
  const [offset,setOffset]=useState(0);
  const load=useCallback((signal:AbortSignal)=>cockpitApi.alerts(projectId,{offset,limit:10,signal}),[projectId,offset,tick,revision]);
  const state=useRead(active,load),page=state.data,stale=page&&graphRevision!==undefined&&page.revision!==graphRevision;
  return <section className="cockpit-alerts" aria-label="Points à traiter"><h4>Points à traiter{page&&!stale?` · ${page.total}`:''}</h4>{state.loading&&<LoadingState label="Chargement des alertes"/>}{state.error&&<ErrorState message={state.error} retry={state.retry}/>}
    <RevisionState page={page} revision={graphRevision} onRefresh={onRefresh}/>{page&&!stale&&<>{!page.items.length&&<p>Aucune alerte dans les données actuellement enregistrées.</p>}<ul className="cockpit-item-list">{page.items.map(row=><li key={`${row.kind}-${row.id}`}><button type="button" aria-label={`${alertLabels[row.kind]||row.kind} · ${row.title}`} disabled={locked} onClick={()=>onSelect(row)}><span className={`badge ${row.severity==='high'?'danger':'neutral'}`}>{alertLabels[row.kind]||row.kind}</span><strong>{row.title}</strong>{row.due_date&&<span>{dateLabel(row.due_date)}</span>}</button></li>)}</ul>
      <Pagination offset={offset} total={page.total} limit={10} onChange={setOffset}/></>}
  </section>;
}
