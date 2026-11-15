import { useEffect, useState } from 'react';
import { planningApi, workflowLabels, type ItemDetail, type ItemPage, type MilestoneInput, type PlanningInfo, type PlanningMilestone, type WorkflowStatus } from '../lib/projectPlanning';
import { milestoneApi, type DateField, type MilestoneChange, type MilestoneEvidence } from '../lib/milestones';
import { api } from '../lib/api';
import { Pagination } from './IdentityPickers';
import { ErrorState, LoadingState } from './Ui';
import { MilestonesPanel } from './MilestonesPanel';
import { SourceInspector } from './WorkspaceViews';
import { changedFields, message, PlanningRelationPicker, useAlive, useEditorFocus } from './PlanningTasksPanel';
import '../project-planning.css';
import { MilestoneDeliverableGates } from './MilestoneDeliverableGates';
import type { DeliverableFocus, GatePage } from '../lib/projectDeliverables';

const dateFields:DateField[]=['contractual_date','forecast_date','actual_date'];
const dateLabels:Record<DateField,string>={contractual_date:'Contractuelle',forecast_date:'Prévisionnelle',actual_date:'Réelle'};
const formatDate=(value?:string)=>value?value.split('-').reverse().join('/'):'À préciser';
type MilestonesProps={projectId:string;active?:boolean;onSaved:()=>void;onOpenDeliverable?:(focus:Omit<DeliverableFocus,'requestId'>)=>void};
export function PlanningMilestonesPanel(props:MilestonesProps) {return <MilestonesView key={props.projectId} {...props}/>;}
function MilestonesView({projectId,active=true,onSaved,onOpenDeliverable}:MilestonesProps) {
  const [search,setSearch]=useState('');const [offset,setOffset]=useState(0);const [archived,setArchived]=useState(false);
  const [page,setPage]=useState<ItemPage<PlanningMilestone>|null>(null);const [info,setInfo]=useState<PlanningInfo|null>(null);const [loading,setLoading]=useState(true);
  const [error,setError]=useState('');const [tick,setTick]=useState(0);const [busy,setBusy]=useState(false);const [title,setTitle]=useState('');
  const [editor,setEditor]=useState<ItemDetail<PlanningMilestone>|null>(null);const [notice,setNotice]=useState('');const [source,setSource]=useState<MilestoneEvidence|null>(null);
  const [history,setHistory]=useState<{title:string;rows:MilestoneChange[]}|null>(null);const [selected,setSelected]=useState<Record<string,PlanningMilestone>>({});
  const alive=useAlive();
  const [gates,setGates]=useState<PlanningMilestone|null>(null);
  useEffect(()=>{if(!active)return;const controller=new AbortController();setLoading(true);setError('');
    const timer=window.setTimeout(()=>{Promise.all([planningApi.info(projectId,controller.signal),planningApi.milestones(projectId,{search,offset,include_inactive:archived,signal:controller.signal})])
      .then(([state,values])=>{if(!controller.signal.aborted){setInfo(state);setPage(values);}})
      .catch(e=>{if(!controller.signal.aborted)setError(message(e));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});},150);
    return()=>{controller.abort();window.clearTimeout(timer);};},[projectId,active,search,offset,archived,tick]);
  const refreshed=()=>{if(!alive.current)return;setTick(value=>value+1);onSaved();};
  async function run(action:()=>Promise<void>) {if(busy)return;setBusy(true);setError('');try {await action();}catch(e){if(alive.current)setError(message(e));}finally{if(alive.current)setBusy(false);}}
  const rows=Array.from(new Map([...Object.values(selected),...(page?.items||[])].map(row=>[row.id,row])).values());
  return <section className="planning-panel" aria-label="Échéances du projet">
    <header className="planning-heading"><div><h3>Échéances du projet</h3></div></header>
    <div className="planning-toolbar"><label>Rechercher un jalon<input className="input" type="search" value={search} maxLength={200} onChange={e=>{setSearch(e.target.value);setOffset(0);}}/></label>
      <label className="identity-checkbox"><input type="checkbox" checked={archived} onChange={e=>{setArchived(e.target.checked);setOffset(0);}}/>Inclure les jalons archivés</label>
      <button type="button" className="button secondary sm" disabled={loading} onClick={refreshed}>Recharger la liste</button></div>
    {notice&&<p role="status" className="planning-notice">{notice}</p>}{error&&<ErrorState message={error} retry={refreshed}/>}{loading&&<LoadingState label="Chargement des jalons"/>}
    {info?.can_edit&&<form className="inline-form" data-workspace-dirty={title.trim()?'true':undefined} onSubmit={e=>{e.preventDefault();if(!title.trim()||loading)return;void run(async()=>{await planningApi.createMilestone(projectId,page?.revision??info.revision,title.trim());if(alive.current){setTitle('');setNotice('Jalon créé ; ses dates restent à renseigner.');refreshed();}});}}>
      <label>Nouveau jalon spécifique<input className="input" value={title} maxLength={255} required disabled={busy} onChange={e=>setTitle(e.target.value)}/></label><button className="button secondary" type="submit" disabled={busy||loading||!title.trim()}>Créer le jalon</button></form>}
    {editor&&<MilestoneEditor key={editor.item.id} projectId={projectId} initial={editor} active={active} onOpenDeliverable={onOpenDeliverable} workflow={info?.workflow||[]} onCancel={()=>setEditor(null)} onSaved={()=>{if(alive.current){setEditor(null);setNotice('Jalon enregistré ; la date réelle reste indépendante du workflow.');refreshed();}}}/>}
    {gates&&!editor&&<section className="card" aria-label={`Contrôles du jalon · ${gates.title}`}><button type="button" className="button secondary sm" onClick={()=>setGates(null)}>Fermer les contrôles du jalon</button><MilestoneDeliverableGates projectId={projectId} milestoneId={gates.id} title={gates.title} active={active} refreshKey={tick} onOpenDeliverable={onOpenDeliverable}/></section>}
    {page&&<><Pagination offset={page.offset} total={page.total} limit={page.limit} onChange={setOffset} disabled={loading}/>
      {!page.items.length&&!loading&&<p>Aucun jalon ne correspond à ces filtres.</p>}
      <div className="planning-table-scroll"><table className="data-table planning-milestone-table"><caption>Écart : réalisation ou prévision moins engagement contractuel. Un écart positif indique un retard.</caption>
        <thead><tr><th>Jalon / ordre</th>{dateFields.map(field=><th key={field}>{dateLabels[field]}</th>)}<th>Écart</th><th>Étape</th><th>Actions</th></tr></thead><tbody>{page.items.map(row=><tr key={row.id} className={!row.active?'planning-archived':undefined}>
          <td><strong>{row.title}</strong><small>{row.code||'Sans code'} · position {row.order}</small>{!row.active&&<span className="badge neutral">Archivé</span>}</td>
          {dateFields.map(field=><td key={field}>{formatDate(row[field])}{row.date_sources?.[field]&&<details className="milestone-proof"><summary>Source de la date</summary><span>{row.date_sources[field]?.label||'Preuve conservée'}</span>
            {row.date_sources[field]?.quote&&<blockquote>{row.date_sources[field]?.quote}</blockquote>}
            {(row.date_sources[field]?.source_id||row.date_sources[field]?.path)&&<button type="button" className="button secondary sm" onClick={()=>{const proof=row.date_sources![field]!;if(proof.source_id)setSource(proof);else if(proof.path)void run(async()=>{await api.openPath(proof.path!,projectId);});}}>Consulter la source</button>}</details>}</td>)}
          <td><span className={(row.variance_days??0)>0?'milestone-delay':''}>{row.variance_days==null?'—':`${row.variance_days>0?'+':''}${row.variance_days} j`}</span></td>
          <td><span className={`badge ${row.workflow_status==='blocked'?'danger':row.workflow_status==='validated'?'ok':'neutral'}`}>{workflowLabels[row.workflow_status]}</span>{row.actual_date&&<small>Réalisation datée</small>}{row.comment&&<details><summary>Commentaire</summary><p>{row.comment}</p></details>}</td>
          <td><div className="planning-row-actions"><button type="button" className="button secondary sm" aria-label={`${info?.can_edit?'Modifier':'Consulter'} · ${row.title}`} disabled={loading||busy||!!editor} onClick={()=>void run(async()=>{const value=await planningApi.milestone(projectId,row.id);if(alive.current){setEditor(value);setNotice('');}})}>{info?.can_edit?'Modifier':'Consulter'}<span className="sr-only"> · {row.title}</span></button>
            <details className="milestone-row-options" onClick={event=>{if((event.target as HTMLElement).closest('button'))event.currentTarget.open=false;}}><summary aria-label={`Options du jalon ${row.title}`}>Options</summary><div className="milestone-row-menu"><button type="button" className="button secondary sm" aria-label={`Historique des dates · ${row.title}`} disabled={busy} onClick={()=>void run(async()=>{const values=await milestoneApi.history(projectId,row.id);if(alive.current)setHistory({title:row.title,rows:values});})}>Historique des dates</button><button type="button" className="button secondary sm" aria-label={`Visas de livrables · ${row.title}`} disabled={busy||loading||!!editor||!active} onClick={()=>setGates(row)}>Visas de livrables</button></div></details></div></td></tr>)}</tbody></table></div></>}
    {history&&<section className="card" aria-label={`Historique des dates · ${history.title}`}><div className="planning-heading"><h4>Historique des dates · {history.title}</h4><button type="button" className="button secondary sm" onClick={()=>setHistory(null)}>Fermer l’historique des dates</button></div>
      {!history.rows.length&&<p>Aucune modification de date enregistrée.</p>}{history.rows.map(row=><article className="planning-date-change" key={row.id}><strong>{dateLabels[row.field as DateField]||'Nom'} : {row.previous||'Non renseigné'} → {row.value||'Non renseigné'}</strong><small>{new Date(row.created_at).toLocaleString('fr-FR')} · {row.evidence.label}</small>{row.evidence.quote&&<blockquote>{row.evidence.quote}</blockquote>}</article>)}</section>}
    <MilestonesPanel projectId={projectId} rows={rows} refresh={refreshed} active={active} reviewOnly canEdit={!!info?.can_edit&&!loading} expectedRevision={page?.revision}
      renderTarget={(candidate,value,onChange)=><div className="planning-candidate-target"><PlanningRelationPicker projectId={projectId} kind="milestones" label={`Jalon cible · ${candidate.title}`} value={value||null}
        current={value?rows.find(row=>row.id===value)||{id:value,title:candidate.title}:null} disabled={!info?.can_edit||loading}
        onPick={row=>{if(row)setSelected(previous=>({...previous,[row.id]:row as PlanningMilestone}));}} onChange={id=>onChange(id||'')}/>{!value&&<small>La validation créera « {candidate.title} ».</small>}</div>}/>
    {source?.source_id&&<SourceInspector sourceId={source.source_id} evidence={[{source_id:source.source_id,title:source.label,excerpt:source.quote||''}]} onClose={()=>setSource(null)}/>}
  </section>;
}
function milestoneInput(row:PlanningMilestone):MilestoneInput {return {title:row.title,code:row.code,position:row.order,workflow_status:row.workflow_status,comment:row.comment,active:row.active,contractual_date:row.contractual_date||'',forecast_date:row.forecast_date||'',actual_date:row.actual_date||''};}
export function MilestoneEditor({projectId,initial,workflow,onCancel,onSaved,active,onOpenDeliverable}:{projectId:string;initial:ItemDetail<PlanningMilestone>;workflow:{code:string;title:string}[];onCancel:()=>void;onSaved:()=>void;active:boolean;onOpenDeliverable?:MilestonesProps['onOpenDeliverable']}) {
  const [base,setBase]=useState(initial);const [draft,setDraft]=useState(()=>milestoneInput(initial.item));const [busy,setBusy]=useState(false);const [error,setError]=useState('');
  const [latest,setLatest]=useState<ItemDetail<PlanningMilestone>|null>(null);const alive=useAlive();const patches=changedFields(milestoneInput(base.item),draft);const readOnly=!base.can_edit;
  const [gatePage,setGatePage]=useState<GatePage|null>(null);const [gateTick,setGateTick]=useState(0);
  const needsGates=patches.workflow_status==='validated';const staleGates=!!gatePage&&gatePage.revision!==base.revision;
  const gateBlocked=needsGates&&(!gatePage||!gatePage.can_validate||staleGates);
  const change=(key:keyof MilestoneInput,value:unknown)=>{setDraft(previous=>({...previous,[key]:value}));setLatest(null);};
  async function save() {if(busy||readOnly||latest||gateBlocked||!active)return;setBusy(true);setError('');try {await planningApi.patchMilestone(projectId,base.item.id,base.revision,patches);if(alive.current)onSaved();}
    catch(e){if(alive.current){setError(message(e));setGateTick(value=>value+1);}}finally{if(alive.current)setBusy(false);}}
  async function loadLatest() {if(busy)return;setBusy(true);try {const value=await planningApi.milestone(projectId,base.item.id);if(alive.current)setLatest(value);}catch(e){if(alive.current)setError(message(e));}finally{if(alive.current)setBusy(false);}}
  const disabled=busy||readOnly;const editorFocus=useEditorFocus();
  return <form ref={editorFocus} tabIndex={-1} className="card planning-editor" aria-label="Édition du jalon" data-workspace-dirty={!readOnly&&Object.keys(patches).length?'true':undefined} onSubmit={e=>{e.preventDefault();void save();}}>
    <div className="planning-heading"><h3>{readOnly?'Consulter le jalon':'Modifier le jalon'}</h3><span>Révision {base.revision}</span></div>
    {error&&<p role="alert" className="planning-error">{error} Votre saisie est conservée.</p>}
    {latest&&<section className="planning-conflict" aria-label="Comparaison du jalon avec la dernière révision"><h4>Version actuelle : révision {latest.revision}</h4><table className="data-table"><thead><tr><th>Champ</th><th>Au début</th><th>Actuellement</th><th>Votre saisie</th></tr></thead><tbody>{Object.entries(patches).map(([key,value])=><tr key={key}><td>{milestoneFieldLabels[key]||key}</td><td>{String(milestoneInput(base.item)[key as keyof MilestoneInput]??'—')}</td><td>{String(milestoneInput(latest.item)[key as keyof MilestoneInput]??'—')}</td><td>{String(value??'—')}</td></tr>)}</tbody></table>
      <button type="button" className="button secondary" disabled={busy} onClick={()=>{setDraft({...milestoneInput(latest.item),...patches});setBase(latest);setLatest(null);setError('');}}>Préparer mon brouillon sur cette révision</button></section>}
    <div className="planning-form-grid"><label>Intitulé du jalon<input className="input" required maxLength={255} disabled={disabled} value={draft.title} onChange={e=>change('title',e.target.value)}/></label>
      <label>Code du jalon<input className="input" list={`workflow-${base.item.id}`} pattern="[a-z][a-z0-9_-]{0,63}" maxLength={64} disabled={disabled} value={draft.code||''} onChange={e=>change('code',e.target.value||null)}/><datalist id={`workflow-${base.item.id}`}>{workflow.map(row=><option key={row.code} value={row.code}>{row.title}</option>)}</datalist></label>
      <label>Ordre des étapes<input className="input" type="number" min={0} max={100000} step={1} disabled={disabled} value={draft.position??''} onChange={e=>change('position',e.target.value?Number(e.target.value):null)}/></label>
      <label>État du jalon<select className="input" value={draft.workflow_status} disabled={disabled} onChange={e=>change('workflow_status',e.target.value as WorkflowStatus)}>{Object.entries(workflowLabels).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
      {dateFields.map(field=><label key={field}>Date {dateLabels[field].toLowerCase()}<input className="input" type="date" value={draft[field]||''} disabled={disabled} onChange={e=>change(field,e.target.value)}/></label>)}
    </div>
    <p className="planning-note">Valider un jalon codé ouvre le suivant en attente, sans franchir un jalon bloqué. Ce changement ne renseigne pas la date réelle. Les jalons sans code restent indépendants.</p>
    <label>Commentaire du jalon<textarea className="input" rows={3} maxLength={20000} disabled={disabled} value={draft.comment} onChange={e=>change('comment',e.target.value)}/></label>
    <label className="identity-checkbox"><input type="checkbox" checked={draft.active} disabled={disabled} onChange={e=>change('active',e.target.checked)}/>Afficher ce jalon dans le planning</label>
    <p className="planning-note">Archiver conserve le jalon, ses dates et toutes ses preuves.</p>
    <MilestoneDeliverableGates projectId={projectId} milestoneId={base.item.id} title={base.item.title} active={active} disabled={busy} refreshKey={gateTick} onStatus={setGatePage} onOpenDeliverable={onOpenDeliverable}/>
    {needsGates&&gateBlocked&&<p role="alert">{!gatePage?'Attendre ou relancer la vérification des visas avant validation.':staleGates?'La révision du projet a changé. Comparer et préparer le brouillon avant validation.':'Les visas affichés doivent être obtenus avant de valider le jalon.'} Votre saisie des dates est conservée.</p>}
    <div className="planning-actions">{!readOnly&&<button className="button primary" type="submit" disabled={busy||!!latest||!active||gateBlocked||!draft.title?.trim()||!Object.keys(patches).length}>{busy?'Enregistrement…':'Enregistrer le jalon'}</button>}
      {(error||staleGates)&&<button type="button" className="button secondary" disabled={busy} onClick={()=>void loadLatest()}>Recharger et comparer sans perdre ma saisie</button>}
      <button type="button" className="button secondary" disabled={busy} onClick={onCancel}>{readOnly?'Fermer le jalon':'Annuler le brouillon'}</button></div>
  </form>;
}
const milestoneFieldLabels:Record<string,string>={title:'Intitulé',code:'Code',position:'Ordre',workflow_status:'État du jalon',comment:'Commentaire',active:'Affiché dans le planning',contractual_date:'Date contractuelle',forecast_date:'Date prévisionnelle',actual_date:'Date réelle'};
