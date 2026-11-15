import { useEffect, useState } from 'react';
import { deliverableApi, deliverableDate, deliverableVersionLabel, documentLabels, type CheckItem, type DeliverableDetail, type RevisionPage } from '../lib/projectDeliverables';
import { useDebouncedValue } from '../hooks/useDebouncedValue';
import { Pagination } from './IdentityPickers';
import { PlanningRelationPicker, useAlive } from './PlanningTasksPanel';
import { ErrorState, LoadingState } from './Ui';

const message=(error:unknown)=>error instanceof Error?error.message:String(error);
type CheckFields=Pick<CheckItem,'label'|'active'|'completed'|'proof'|'comment'>;
const fields=(item:CheckItem):CheckFields=>({label:item.label,active:item.active,completed:item.completed,proof:item.proof,comment:item.comment});
const editingFields=(item:CheckItem,detail:DeliverableDetail):CheckFields=>({...fields(item),completed:item.completed&&(!item.is_gate||!!detail.latest_version_id&&item.completed_version_id===detail.latest_version_id)});
function edits(base:CheckFields,draft:CheckFields):Partial<CheckFields> {
  const result=Object.fromEntries(Object.entries(draft).filter(([key,value])=>value!==base[key as keyof CheckFields])) as Partial<CheckFields>;
  // A changed label/proof invalidates an existing visa on the server. A human
  // must explicitly tick completion again before it can be sent as true.
  if(draft.completed&&('label' in result||'proof' in result))result.completed=true;
  return result;
}
const frozen=(detail:DeliverableDetail)=>['validated','archived'].includes(detail.document_status);
export function DeliverableChecklist({projectId,detail,active=true,onSaved,onBusy,focusedCheckId}:{projectId:string;detail:DeliverableDetail;active?:boolean;onSaved:()=>void;onBusy:(busy:boolean)=>void;focusedCheckId?:string}) {
  const focused=detail.checklist.find(row=>row.id===focusedCheckId);
  const [search,setSearch]=useState(()=>focused?.code||'');const term=useDebouncedValue(search);const [inactive,setInactive]=useState(()=>!!focused&&!focused.active);const [offset,setOffset]=useState(0);const [tick,setTick]=useState(0);
  const [page,setPage]=useState<RevisionPage<CheckItem>|null>(null);const [loading,setLoading]=useState(false);const [error,setError]=useState('');const [selected,setSelected]=useState<CheckItem|null>(null);const [creating,setCreating]=useState(false);
  const editing=!!selected||creating;const disabled=editing||loading||!active;
  useEffect(()=>{if(!active)return;const controller=new AbortController();setLoading(true);setError('');setPage(null);
    deliverableApi.checklist(projectId,detail.id,{search:term,include_inactive:inactive,offset,limit:25,signal:controller.signal})
      .then(value=>{if(!controller.signal.aborted)setPage(value);}).catch(e=>{if(!controller.signal.aborted)setError(message(e));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});return()=>controller.abort();
  },[projectId,detail.id,detail.revision,active,term,inactive,offset,tick]);
  function saved(){setSelected(null);setCreating(false);onSaved();}
  const stale=!!page&&page.revision!==detail.revision;
  return <section aria-label="Checklist du livrable"><p>Les points de préparation et les visas sont distincts. Les visas confirment une preuve humaine pour la dernière version publiée ; ils ne valident pas automatiquement le document.</p>
    {frozen(detail)&&<p role="status">Checklist verrouillée. Rouvrir le document dans « Validation » pour la modifier.</p>}
    <div className="planning-toolbar"><label>Rechercher un point<input className="input" type="search" maxLength={200} value={search} disabled={disabled} onChange={e=>{setSearch(e.target.value);setOffset(0);}}/></label>
      <label className="identity-checkbox"><input type="checkbox" checked={inactive} disabled={disabled} onChange={e=>{setInactive(e.target.checked);setOffset(0);}}/>Inclure les points inactifs</label>
      {detail.can_edit&&!frozen(detail)&&<button type="button" className="button primary" disabled={disabled||!page||stale} onClick={()=>setCreating(true)}>Ajouter un point</button>}</div>
    {error&&<ErrorState message={error} retry={()=>setTick(value=>value+1)}/>} {loading&&<LoadingState label="Chargement de la checklist"/>}
    {stale&&<p role="alert">La révision a changé. <button type="button" className="button secondary" disabled={editing} onClick={onSaved}>Recharger la fiche avant de modifier</button></p>}
    {creating&&<CheckCreate projectId={projectId} detail={detail} onSaved={saved} onBusy={onBusy} onCancel={()=>setCreating(false)}/>}
    {selected&&<CheckEditor key={selected.id} projectId={projectId} detail={detail} initial={selected} onSaved={saved} onBusy={onBusy} onCancel={()=>setSelected(null)}/>}
    {page&&<><Pagination offset={page.offset} limit={page.limit} total={page.total} onChange={setOffset} disabled={disabled}/>
      {!page.items.length&&<p>Aucun point ne correspond à ces filtres.</p>}
      <ul className="deliverable-checks">{page.items.map(check=>{const exact=check.completed&&check.completed_version_id===detail.latest_version_id&&!!detail.latest_version_id;
        const editable=detail.can_edit&&!frozen(detail)&&(!check.is_gate||detail.can_verify);
        return <li key={check.id} aria-current={check.id===focusedCheckId?'true':undefined}><strong>{check.label}</strong>{check.id===focusedCheckId&&<small>Contrôle ouvert depuis le jalon</small>}<span>{check.is_gate?'Visa requis':'Préparation'} · {check.is_gate?(exact?'Visé pour cette version':'Visa à effectuer'):check.completed?'Effectué':'À effectuer'}{!check.active?' · Inactif':''}{check.transverse?' · Transverse':''}{!check.contributes?' · Hors progression':''}</span>
          {check.milestone_id&&<small>Jalon associé : {check.milestone_id}</small>}{check.proof&&<p>Preuve : {check.proof}</p>}{check.comment&&<p>Commentaire : {check.comment}</p>}
          {check.completed_by&&<small>Confirmé par {check.completed_by}{check.completed_at?` · ${deliverableDate(check.completed_at)}`:''}</small>}
          {editable&&<button type="button" className="button secondary sm" disabled={disabled||stale} onClick={()=>setSelected(check)}>Modifier · {check.label}</button>}
          {check.is_gate&&!detail.can_verify&&detail.can_edit&&<small>Visa réservé au vérificateur désigné ou au propriétaire.</small>}</li>;})}</ul></>}
  </section>;
}

function CheckEditor({projectId,detail,initial,onSaved,onBusy,onCancel}:{projectId:string;detail:DeliverableDetail;initial:CheckItem;onSaved:()=>void;onBusy:(busy:boolean)=>void;onCancel:()=>void}) {
  const [base,setBase]=useState(initial);const [context,setContext]=useState(detail);const [draft,setDraft]=useState(editingFields(initial,detail));const [latest,setLatest]=useState<DeliverableDetail|null>(null);const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [notice,setNotice]=useState('');const alive=useAlive();
  const changes=edits(editingFields(base,context),draft);const dirty=Object.keys(changes).length>0;const allowed=context.can_edit&&!frozen(context)&&(!base.is_gate||context.can_verify);
  const invalidVisa=base.is_gate&&draft.completed&&(!context.latest_version_id||!draft.proof.trim());
  useEffect(()=>{onBusy(busy);return()=>onBusy(false);},[busy,onBusy]);
  async function save(){if(busy||!allowed||latest||invalidVisa||!dirty)return;setBusy(true);setError('');try{await deliverableApi.patchCheck(projectId,context.id,base.id,context.revision,changes);if(alive.current)onSaved();}catch(e){if(alive.current)setError(message(e));}finally{if(alive.current)setBusy(false);}}
  async function compare(){setBusy(true);try{const value=await deliverableApi.detail(projectId,detail.id);if(alive.current)setLatest(value);}catch(e){if(alive.current)setError(message(e));}finally{if(alive.current)setBusy(false);}}
  function prepare(){const check=latest?.checklist.find(row=>row.id===base.id);if(!latest||!check)return;
    setDraft({...fields(check),...changes,...(check.is_gate?{completed:false}:{})});setBase(check);setContext(latest);setLatest(null);setError('');setNotice(check.is_gate?'Votre preuve est conservée. Confirmez à nouveau le visa pour la version actuelle.':'Brouillon préparé ; vérifiez les valeurs avant de l’enregistrer.');}
  function cancel(){if(!dirty||window.confirm('Abandonner les modifications de ce point ?'))onCancel();}
  return <form className="planning-editor" aria-label={`Modifier le point · ${base.label}`} data-workspace-dirty={dirty?'true':undefined} onSubmit={e=>{e.preventDefault();void save();}}>
    <h4>{base.is_gate?'Visa humain':'Point de préparation'} · {base.label}</h4>
    {base.is_gate&&<p>Version visée : {deliverableVersionLabel(context)}. Modifier la preuve ou l’intitulé retire le visa précédent ; une nouvelle confirmation est nécessaire.</p>}
    {!allowed&&<p role="alert">Ce point est désormais verrouillé ou votre autorisation a changé. Votre saisie reste affichée.</p>}
    {error&&<p role="alert" className="planning-error">{error} Votre saisie est conservée.</p>}{notice&&<p role="status">{notice}</p>}
    {latest&&<section className="planning-conflict" aria-label="Comparaison du point"><h4>Révision actuelle : {latest.revision}</h4><p>Version actuelle : {latest.latest_version_id||'Aucune'} · Document : {documentLabels[latest.document_status]}</p>
      {latest.checklist.some(row=>row.id===base.id)?<><table className="data-table"><thead><tr><th>Champ</th><th>Au début</th><th>Actuellement</th><th>Votre saisie</th></tr></thead><tbody>{Object.keys(changes).map(key=><tr key={key}><td>{({label:'Intitulé',active:'Actif',completed:'Effectué',proof:'Preuve',comment:'Commentaire'} as Record<string,string>)[key]}</td><td>{String(fields(base)[key as keyof CheckFields])}</td><td>{String(fields(latest.checklist.find(row=>row.id===base.id)!)[key as keyof CheckFields])}</td><td>{String(draft[key as keyof CheckFields])}</td></tr>)}</tbody></table><button type="button" className="button secondary" disabled={busy} onClick={prepare}>Préparer ce point sur la révision actuelle</button></>:<p>Ce point n’est plus disponible. Conservez votre saisie avant de fermer.</p>}</section>}
    <div className="planning-form-grid"><label>Intitulé du point<input className="input" required maxLength={500} value={draft.label} disabled={busy||!allowed} onChange={e=>setDraft(old=>({...old,label:e.target.value,completed:false}))}/></label>
      <label>Preuve du point<textarea className="input" maxLength={20000} value={draft.proof} disabled={busy||!allowed} onChange={e=>setDraft(old=>({...old,proof:e.target.value,...(base.is_gate?{completed:false}:{})}))}/></label>
      <label>Commentaire du point<textarea className="input" maxLength={20000} value={draft.comment} disabled={busy||!allowed} onChange={e=>setDraft(old=>({...old,comment:e.target.value}))}/></label>
      <label className="identity-checkbox"><input type="checkbox" checked={draft.active} disabled={busy||!allowed||base.is_gate} onChange={e=>setDraft(old=>({...old,active:e.target.checked,...(!e.target.checked?{completed:false}:{})}))}/>Point actif{base.is_gate?' · visa obligatoire':''}</label>
      <label className="identity-checkbox"><input type="checkbox" checked={draft.completed} disabled={busy||!allowed||!draft.active||(base.is_gate&&(!context.latest_version_id||!draft.proof.trim()))} onChange={e=>setDraft(old=>({...old,completed:e.target.checked}))}/>{base.is_gate?'Je confirme ce visa humain pour la version affichée':'Préparation effectuée'}</label></div>
    <div className="planning-toolbar"><button type="submit" className="button primary" disabled={busy||!allowed||!!latest||!dirty||!draft.label.trim()||invalidVisa}>Enregistrer le point</button>{error&&<button type="button" className="button secondary" disabled={busy} onClick={()=>void compare()}>Comparer le point actuel</button>}<button type="button" className="button secondary" disabled={busy} onClick={cancel}>Annuler le point</button></div>
  </form>;
}

function CheckCreate({projectId,detail,onSaved,onBusy,onCancel}:{projectId:string;detail:DeliverableDetail;onSaved:()=>void;onBusy:(busy:boolean)=>void;onCancel:()=>void}) {
  const [draft,setDraft]=useState({code:'',label:'',is_gate:false,transverse:false,contributes:true,milestone_id:null as string|null});const [context,setContext]=useState(detail);const [latest,setLatest]=useState<DeliverableDetail|null>(null);const [busy,setBusy]=useState(false);const [error,setError]=useState('');const alive=useAlive();
  const dirty=!!draft.code||!!draft.label||draft.is_gate||draft.transverse||!draft.contributes||!!draft.milestone_id;const allowed=context.can_edit&&!frozen(context);
  useEffect(()=>{onBusy(busy);return()=>onBusy(false);},[busy,onBusy]);
  async function save(){if(busy||!allowed||latest)return;setBusy(true);setError('');try{await deliverableApi.createCheck(projectId,context.id,context.revision,draft);if(alive.current)onSaved();}catch(e){if(alive.current)setError(message(e));}finally{if(alive.current)setBusy(false);}}
  async function compare(){setBusy(true);try{const value=await deliverableApi.detail(projectId,detail.id);if(alive.current)setLatest(value);}catch(e){if(alive.current)setError(message(e));}finally{if(alive.current)setBusy(false);}}
  return <form className="planning-editor" aria-label="Nouveau point de checklist" data-workspace-dirty={dirty?'true':undefined} onSubmit={e=>{e.preventDefault();void save();}}><h4>Nouveau point</h4>
    {error&&<p role="alert">{error} Votre saisie est conservée.</p>}{!allowed&&<p role="alert">La checklist est verrouillée ou votre autorisation a changé.</p>}
    {latest&&<section className="planning-conflict" aria-label="Comparaison avant ajout du point"><p>Révision actuelle : {latest.revision}. Vérifiez le statut et les jalons associés avant de reprendre.</p><button type="button" className="button secondary" disabled={busy} onClick={()=>{setContext(latest);setLatest(null);setError('');}}>Préparer l’ajout sur cette révision</button></section>}
    <div className="planning-form-grid"><label>Code du point<input aria-label="Code du point" className="input" required pattern="[a-z][a-z0-9_-]{0,63}" maxLength={64} value={draft.code} disabled={busy||!allowed} onChange={e=>setDraft(old=>({...old,code:e.target.value}))}/><small>Code stable : lettres minuscules, chiffres, tiret ou soulignement.</small></label>
      <label>Intitulé du nouveau point<input className="input" required maxLength={500} value={draft.label} disabled={busy||!allowed} onChange={e=>setDraft(old=>({...old,label:e.target.value}))}/></label>
      <div><PlanningRelationPicker projectId={projectId} kind="milestones" label="Jalon du point" value={draft.milestone_id} allowedIds={context.milestone_ids} disabled={busy||!allowed} onChange={value=>setDraft(old=>({...old,milestone_id:value}))}/><small>Choisissez un jalon déjà rattaché au livrable. Sans sélection, le point s’applique à tous ses jalons.</small>{draft.milestone_id&&!context.milestone_ids.includes(draft.milestone_id)&&<p role="alert">Le jalon choisi a été détaché. Choisissez une nouvelle portée avant de créer ce point.</p>}</div>
      <label className="identity-checkbox"><input type="checkbox" checked={draft.is_gate} disabled={busy||!allowed} onChange={e=>setDraft(old=>({...old,is_gate:e.target.checked}))}/>Visa humain obligatoire</label>
      <label className="identity-checkbox"><input type="checkbox" checked={draft.transverse} disabled={busy||!allowed} onChange={e=>setDraft(old=>({...old,transverse:e.target.checked}))}/>Progression transverse</label>
      <label className="identity-checkbox"><input type="checkbox" checked={draft.contributes} disabled={busy||!allowed} onChange={e=>setDraft(old=>({...old,contributes:e.target.checked}))}/>Contribue à la progression</label></div>
    {draft.is_gate&&<p>Le nouveau visa sera à effectuer. Sa création n’accorde aucune validation.</p>}
    <div className="planning-toolbar"><button type="submit" className="button primary" disabled={busy||!allowed||!!latest||!draft.label.trim()||!(/^[a-z][a-z0-9_-]{0,63}$/).test(draft.code)||!!draft.milestone_id&&!context.milestone_ids.includes(draft.milestone_id)}>Créer le point</button>{error&&<button type="button" className="button secondary" disabled={busy} onClick={()=>void compare()}>Comparer avant d’ajouter</button>}<button type="button" className="button secondary" disabled={busy} onClick={()=>{if(!dirty||window.confirm('Abandonner la saisie du nouveau point ?'))onCancel();}}>Annuler le nouveau point</button></div>
  </form>;
}
