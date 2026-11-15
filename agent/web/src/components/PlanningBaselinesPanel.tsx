import { useEffect, useRef, useState } from 'react';
import { planningApi, type Baseline, type BaselineDetail, type BaselineKind, type BaselineMetadata, type PlanningDiff, type PlanningInfo } from '../lib/projectPlanning';
import type { Page } from '../lib/projectIdentity';
import { Pagination } from './IdentityPickers';
import { ErrorState, LoadingState } from './Ui';
import { changedFields, focusPlanning, message, useAlive, useEditorFocus } from './PlanningTasksPanel';
import { baselineKindLabels, DiffDetails, PlanningValue } from './PlanningChanges';
import '../project-planning.css';

export function PlanningBaselinesPanel(props:{projectId:string;active?:boolean;onSaved:()=>void}) {return <BaselinesView key={props.projectId} {...props}/>;}
function BaselinesView({projectId,active=true,onSaved}:{projectId:string;active?:boolean;onSaved:()=>void}) {
  const [page,setPage]=useState<Page<Baseline>|null>(null);const [info,setInfo]=useState<PlanningInfo|null>(null);const [offset,setOffset]=useState(0);const [archived,setArchived]=useState(false);
  const [loading,setLoading]=useState(true);const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [tick,setTick]=useState(0);const [notice,setNotice]=useState('');
  const [capture,setCapture]=useState<PlanningInfo|null>(null);const [editor,setEditor]=useState<BaselineDetail|null>(null);
  const [compare,setCompare]=useState<{baseline:Baseline;diff:PlanningDiff}|null>(null);const alive=useAlive();const generation=useRef(0);
  const compareFocus=useRef<HTMLElement>(null);useEffect(()=>{if(compare)focusPlanning(compareFocus.current);},[compare]);
  useEffect(()=>{if(!active)return;const controller=new AbortController();setLoading(true);setError('');setCompare(null);
    Promise.all([planningApi.info(projectId,controller.signal),planningApi.baselines(projectId,offset,controller.signal,archived)])
      .then(([state,values])=>{if(!controller.signal.aborted){setInfo(state);setPage(values);}})
      .catch(e=>{if(!controller.signal.aborted)setError(message(e));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return()=>controller.abort();},[projectId,active,offset,archived,tick]);
  const refreshed=()=>{if(alive.current){setTick(value=>value+1);onSaved();}};
  async function run(action:()=>Promise<void>) {if(busy)return;const request=++generation.current;setBusy(true);setError('');try {await action();}
    catch(e){if(alive.current&&request===generation.current)setError(message(e));}finally{if(alive.current&&request===generation.current)setBusy(false);}}
  return <section className="planning-panel" aria-label="Références figées du planning">
    <header className="planning-heading"><div><h3>Planning de référence et écarts</h3><p>Conserver les dates et le budget d’heures du projet avec ses jalons et tâches, puis suivre leurs écarts.</p></div>
      {info?.can_edit&&<button type="button" className="button primary" disabled={loading||busy||!!capture||!!editor} onClick={()=>{setCapture(info);setNotice('');}}>Enregistrer le planning de référence</button>}</header>
    <div className="planning-toolbar"><label className="identity-checkbox"><input type="checkbox" checked={archived} onChange={e=>{setArchived(e.target.checked);setOffset(0);}}/>Inclure les références archivées</label>
      <button type="button" className="button secondary sm" disabled={loading||busy} onClick={refreshed}>Recharger les références</button></div>
    {notice&&<p role="status" className="planning-notice">{notice}</p>}{error&&<ErrorState message={error} retry={refreshed}/>}{loading&&<LoadingState label="Chargement des références"/>}
    {capture&&<BaselineCapture projectId={projectId} initial={capture} onCancel={()=>setCapture(null)} onSaved={()=>{setCapture(null);setNotice('Référence capturée : son instantané restera inchangé.');refreshed();}}/>}
    {editor&&<BaselineEditor key={editor.baseline.id} projectId={projectId} initial={editor} onCancel={()=>setEditor(null)} onSaved={()=>{setEditor(null);setNotice('Nom et commentaire enregistrés ; l’instantané reste inchangé.');refreshed();}}/>}
    {compare&&<section ref={compareFocus} tabIndex={-1} className="card planning-comparison" aria-label={`Comparaison · ${compare.baseline.label}`}><div className="planning-heading"><div><h3>{compare.baseline.label} · écarts</h3>
      <p>Référence : révision {compare.baseline.revision} · état comparé : révision {compare.diff.revision??'non précisée'}</p></div><button type="button" className="button secondary sm" onClick={()=>setCompare(null)}>Fermer la comparaison</button></div>
      <p className="planning-note">Cette comparaison porte sur les jalons, tâches, dates, charges et sources capturés. La référence n’est jamais remplacée par l’état actuel.</p><DiffDetails key={`${compare.baseline.id}-${compare.diff.revision}`} diff={compare.diff}/></section>}
    {page&&<><Pagination offset={page.offset} total={page.total} limit={page.limit} onChange={setOffset} disabled={loading||busy}/>
      {!page.total&&!loading&&<p>Aucune référence dans cette vue. Enregistrer le planning de référence initiale avant de suivre les évolutions du planning.</p>}
      <div className="planning-table-scroll"><table className="data-table planning-baseline-table"><thead><tr><th>Référence</th><th>Type / révision capturée</th><th>Création / opérateur</th><th>Actions</th></tr></thead><tbody>{page.items.map(row=><tr key={row.id} className={!row.active?'planning-archived':undefined}>
        <td><strong>{row.label}</strong>{row.comment&&<p>{row.comment}</p>}{!row.active&&<span className="badge neutral">Archivée</span>}<details><summary>Intégrité de l’instantané</summary><small>Nom à la capture : {row.capture_label}</small><code>{row.sha256}</code></details></td>
        <td>{baselineKindLabels[row.kind]}<small>Révision {row.revision}</small></td><td>{new Date(row.created_at).toLocaleString('fr-FR')}<small>{row.actor_id}</small></td>
        <td><div className="planning-row-actions"><button type="button" className="button secondary sm" aria-label={`Comparer · ${row.label}`} disabled={loading||busy} onClick={()=>void run(async()=>{const diff=await planningApi.compare(projectId,row.id);if(alive.current)setCompare({baseline:row,diff});})}>Comparer à l’état actuel</button>
          <button type="button" className="button secondary sm" aria-label={`${info?.can_edit?'Modifier':'Consulter'} la référence · ${row.label}`} disabled={loading||busy||!!editor||!!capture} onClick={()=>void run(async()=>{const value=await planningApi.baseline(projectId,row.id);if(alive.current)setEditor(value);})}>{info?.can_edit?'Modifier le nom et le commentaire':'Consulter le nom et le commentaire'}</button></div></td></tr>)}</tbody></table></div></>}
  </section>;
}
function BaselineCapture({projectId,initial,onCancel,onSaved}:{projectId:string;initial:PlanningInfo;onCancel:()=>void;onSaved:()=>void}) {
  const [state,setState]=useState(initial);const [label,setLabel]=useState('');const [kind,setKind]=useState<BaselineKind>('initial');const [error,setError]=useState('');const [busy,setBusy]=useState(false);
  const [latest,setLatest]=useState<PlanningInfo|null>(null);const alive=useAlive();const focus=useEditorFocus();
  async function save() {if(busy||latest||!state.can_edit)return;setBusy(true);setError('');try{await planningApi.createBaseline(projectId,state.revision,kind,label.trim());if(alive.current)onSaved();}catch(e){if(alive.current)setError(message(e));}finally{if(alive.current)setBusy(false);}}
  async function reload() {setBusy(true);try{const value=await planningApi.info(projectId);if(alive.current)setLatest(value);}catch(e){if(alive.current)setError(message(e));}finally{if(alive.current)setBusy(false);}}
  return <form ref={focus} tabIndex={-1} className="card planning-editor" aria-label="Enregistrer le planning de référence" data-workspace-dirty={label.trim()?'true':undefined} onSubmit={e=>{e.preventDefault();void save();}}>
    <div className="planning-heading"><h3>Enregistrer le planning de référence</h3><span>Révision {state.revision}</span></div><p className="planning-note">La capture comprend les dates de début et de fin prévisionnelle et le budget d’heures enregistré du projet, ainsi que tous ses jalons et tâches, y compris archivés, avec leurs dates, sources et relations. Aucun filtre de liste ne limite l’instantané. Le budget d’heures reste distinct de la charge cumulée des tâches.</p>
    {error&&<p role="alert" className="planning-error">{error} Le nom et le type saisis sont conservés.</p>}
    {latest&&<section className="planning-conflict" aria-label="Révision de la capture"><p>Le planning est maintenant à la révision {latest.revision}. Préparer la capture de cet état à la place de la révision {state.revision}.</p><button type="button" className="button secondary" disabled={busy||!latest.can_edit} onClick={()=>{setState(latest);setLatest(null);setError('');}}>Préparer la capture sur cette révision</button></section>}
    <div className="planning-form-grid"><label>Nom de la référence<input className="input" required maxLength={255} disabled={busy||!state.can_edit} value={label} onChange={e=>setLabel(e.target.value)}/></label>
      <label>Type de référence<select className="input" value={kind} disabled={busy||!state.can_edit} onChange={e=>setKind(e.target.value as BaselineKind)}>{Object.entries(baselineKindLabels).map(([value,title])=><option key={value} value={value}>{title}</option>)}</select></label></div>
    <div className="planning-actions"><button type="submit" className="button primary" disabled={busy||!label.trim()||!!latest||!state.can_edit}>Capturer l’état du planning</button>
      {error&&<button type="button" className="button secondary" disabled={busy} onClick={()=>void reload()}>Relire la révision sans perdre la saisie</button>}
      <button type="button" className="button secondary" disabled={busy} onClick={onCancel}>Annuler la capture</button></div>
  </form>;
}
const metadata=(row:Baseline):BaselineMetadata=>({label:row.label,comment:row.comment,active:row.active});
function BaselineEditor({projectId,initial,onCancel,onSaved}:{projectId:string;initial:BaselineDetail;onCancel:()=>void;onSaved:()=>void}) {
  const [base,setBase]=useState(initial);const [draft,setDraft]=useState(()=>metadata(initial.baseline));const [latest,setLatest]=useState<BaselineDetail|null>(null);const [error,setError]=useState('');const [busy,setBusy]=useState(false);
  const patches=changedFields(metadata(base.baseline),draft);const alive=useAlive();const focus=useEditorFocus();const disabled=busy||!base.can_edit;
  async function save(){if(disabled||latest)return;setBusy(true);setError('');try{await planningApi.patchBaseline(projectId,base.baseline.id,base.revision,patches);if(alive.current)onSaved();}catch(e){if(alive.current)setError(message(e));}finally{if(alive.current)setBusy(false);}}
  async function reload(){setBusy(true);try{const result=await planningApi.baseline(projectId,base.baseline.id);if(alive.current)setLatest(result);}catch(e){if(alive.current)setError(message(e));}finally{if(alive.current)setBusy(false);}}
  return <form ref={focus} tabIndex={-1} className="card planning-editor" aria-label="Informations du planning de référence" data-workspace-dirty={base.can_edit&&Object.keys(patches).length?'true':undefined} onSubmit={e=>{e.preventDefault();void save();}}>
    <div className="planning-heading"><h3>{base.can_edit?'Modifier':'Consulter'} le nom et le commentaire</h3><span>Révision {base.revision}</span></div><p className="planning-note">Nom, commentaire et archivage sont journalisés. Les dates, tâches, sources, empreinte et opérateur de l’instantané d’origine restent protégés.</p>
    {error&&<p role="alert" className="planning-error">{error} Votre brouillon est conservé.</p>}
    {latest&&<section className="planning-conflict" aria-label="Comparaison du nom et du commentaire"><h4>État actuel : révision {latest.revision}</h4><table className="data-table"><thead><tr><th>Champ</th><th>Au début</th><th>Actuellement</th><th>Votre saisie</th></tr></thead><tbody>{Object.entries(patches).map(([key,value])=><tr key={key}><td>{key==='label'?'Nom':key==='comment'?'Commentaire':'Actif'}</td><td><PlanningValue value={metadata(base.baseline)[key as keyof BaselineMetadata]}/></td><td><PlanningValue value={metadata(latest.baseline)[key as keyof BaselineMetadata]}/></td><td><PlanningValue value={value}/></td></tr>)}</tbody></table>
      <button type="button" className="button secondary" disabled={busy} onClick={()=>{setDraft({...metadata(latest.baseline),...patches});setBase(latest);setLatest(null);setError('');}}>Préparer le nom et le commentaire sur cette révision</button></section>}
    <label>Nom de la référence<input className="input" required maxLength={255} disabled={disabled} value={draft.label} onChange={e=>{setDraft({...draft,label:e.target.value});setLatest(null);}}/></label>
    <label>Commentaire de la référence<textarea className="input" rows={3} maxLength={20000} disabled={disabled} value={draft.comment} onChange={e=>{setDraft({...draft,comment:e.target.value});setLatest(null);}}/></label>
    <label className="identity-checkbox"><input type="checkbox" checked={draft.active} disabled={disabled} onChange={e=>{setDraft({...draft,active:e.target.checked});setLatest(null);}}/>Référence active dans les listes</label>
    <div className="planning-actions">{base.can_edit&&<button type="submit" className="button primary" disabled={busy||!!latest||!draft.label.trim()||!Object.keys(patches).length}>Enregistrer le nom et le commentaire</button>}
      {error&&<button type="button" className="button secondary" disabled={busy} onClick={()=>void reload()}>Relire et comparer le nom et le commentaire</button>}
      <button type="button" className="button secondary" disabled={busy} onClick={onCancel}>{base.can_edit?'Annuler le brouillon de référence':'Fermer la référence'}</button></div>
  </form>;
}
