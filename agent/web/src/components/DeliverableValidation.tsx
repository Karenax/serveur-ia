import { useEffect, useState } from 'react';
import { deliverableApi, deliverableVersionLabel, documentLabels, type DeliverableDetail, type DocumentStatus } from '../lib/projectDeliverables';
import { useAlive } from './PlanningTasksPanel';

const transitions:Record<DocumentStatus,DocumentStatus[]>={draft:['to_verify','archived'],to_verify:['validated','to_revise','archived'],validated:['to_revise','archived'],to_revise:['to_verify','archived'],archived:['to_revise']};
const actions:Partial<Record<DocumentStatus,string>>={to_verify:'Soumettre à vérification',validated:'Valider cette version',to_revise:'Rouvrir pour révision',archived:'Archiver le document'};
function permitted(detail:DeliverableDetail,target:DocumentStatus) {
  return detail.can_edit&&!!detail.latest_version_id&&transitions[detail.document_status].includes(target)
    && (!(detail.document_status==='to_verify'&&['validated','to_revise'].includes(target))||detail.can_verify)
    && (!['validated','to_verify'].includes(target)||detail.active&&!!detail.verifier_id)
    && (target!=='validated'||!detail.validation_blockers.length);
}
export function DeliverableValidation({projectId,detail,onSaved,onBusy}:{projectId:string;detail:DeliverableDetail;onSaved:()=>void;onBusy:(busy:boolean)=>void}) {
  const [context,setContext]=useState(detail);const [target,setTarget]=useState<DocumentStatus|''>('');const [comment,setComment]=useState('');const [confirmed,setConfirmed]=useState(false);const [latest,setLatest]=useState<DeliverableDetail|null>(null);const [busy,setBusy]=useState(false);const [error,setError]=useState('');const alive=useAlive();
  useEffect(()=>{onBusy(busy);return()=>onBusy(false);},[busy,onBusy]);
  const dirty=!!target||!!comment||confirmed;const allowed=!!target&&permitted(context,target);
  async function save(){if(busy||latest||!allowed||!confirmed||!context.latest_version_id||target==='validated'&&!comment.trim())return;setBusy(true);setError('');
    try{await deliverableApi.transition(projectId,context.id,context.revision,target as DocumentStatus,context.latest_version_id,comment);if(alive.current)onSaved();}
    catch(e){if(alive.current)setError(e instanceof Error?e.message:String(e));}finally{if(alive.current)setBusy(false);}}
  async function compare(){setBusy(true);try{const value=await deliverableApi.detail(projectId,context.id);if(alive.current)setLatest(value);}catch(e){if(alive.current)setError(e instanceof Error?e.message:String(e));}finally{if(alive.current)setBusy(false);}}
  return <section aria-label="Validation documentaire"><p>Un document généré ou un travail terminé reste un brouillon jusqu’à la vérification humaine. Toute commande ci-dessous porte sur la dernière version publiée.</p>
    <p>Statut : <strong>{documentLabels[context.document_status]}</strong> · Version : <strong className="deliverable-version-id">{deliverableVersionLabel(context)}</strong></p>
    {context.latest_version_id&&<details><summary>Identifiant de la version visée</summary><small className="deliverable-version-id">{context.latest_version_id}</small></details>}
    {context.validation_blockers.length>0&&<section aria-label="Visas manquants"><h4>Visas requis avant validation</h4><ul>{context.validation_blockers.map(item=><li key={item.id}>{item.label} · {item.reason}</li>)}</ul><p>Complétez les points concernés dans « Checklist ».</p></section>}
    {!context.latest_version_id&&<p>Publiez un fichier dans « Versions » avant de soumettre ou d’archiver ce document.</p>}
    {context.can_edit&&!context.verifier_id&&<p>Désignez un vérificateur dans « Fiche » avant la soumission.</p>}
    {!context.can_edit?<p>Consultation en lecture seule.</p>:<form className="planning-editor" aria-label="Changer le statut documentaire" data-workspace-dirty={dirty?'true':undefined} onSubmit={e=>{e.preventDefault();void save();}}>
      {error&&<p role="alert" className="planning-error">{error} Votre commentaire et votre choix sont conservés.</p>}
      {latest&&<section className="planning-conflict" aria-label="Comparaison de la validation"><p>Révision {context.revision} → {latest.revision} · Statut {documentLabels[context.document_status]} → {documentLabels[latest.document_status]}</p><p>Version précédente : {context.latest_version_id||'Aucune'} · Version actuelle : {latest.latest_version_id||'Aucune'}</p><p>Visas manquants : {latest.validation_blockers.length}. Une nouvelle confirmation humaine est nécessaire.</p><button type="button" className="button secondary" disabled={busy} onClick={()=>{setContext(latest);setLatest(null);setConfirmed(false);setError('');}}>Préparer la commande sur la version actuelle</button></section>}
      <div className="planning-form-grid"><label>Action documentaire<select className="input" disabled={busy} value={target} onChange={e=>{setTarget(e.target.value as DocumentStatus|'');setConfirmed(false);}}><option value="">Choisir une action</option>{target&&!transitions[context.document_status].includes(target)&&<option value={target} disabled>{actions[target]} · action devenue indisponible</option>}{transitions[context.document_status].map(value=><option key={value} value={value} disabled={!permitted(context,value)}>{actions[value]}</option>)}</select></label>
        <label>Commentaire de validation<textarea aria-label="Commentaire de validation" className="input" maxLength={20000} required={target==='validated'} disabled={busy} value={comment} onChange={e=>setComment(e.target.value)}/><small>{target==='validated'?'Commentaire de visa humain obligatoire.':'Conservez la raison de cette décision dans l’historique.'}</small></label>
        <label className="identity-checkbox"><input type="checkbox" checked={confirmed} disabled={busy||!allowed||!!latest} onChange={e=>setConfirmed(e.target.checked)}/>Je confirme cette action pour la version affichée</label></div>
      {target==='to_revise'&&<p>La réouverture retire les visas obligatoires. Les points de préparation sont conservés.</p>}
      {context.document_status==='to_verify'&&!context.can_verify&&<p>La validation et le retour pour révision sont réservés au vérificateur désigné ou au propriétaire.</p>}
      <div className="planning-toolbar"><button type="submit" className="button primary" disabled={busy||!allowed||!confirmed||!!latest||target==='validated'&&!comment.trim()}>Appliquer l’action documentaire</button>{error&&<button type="button" className="button secondary" disabled={busy} onClick={()=>void compare()}>Comparer la version avant de reprendre</button>}<button type="button" className="button secondary" disabled={busy} onClick={()=>{if(!dirty||window.confirm('Abandonner la décision documentaire en cours ?')){setTarget('');setComment('');setConfirmed(false);setLatest(null);setError('');}}}>Annuler la décision</button></div>
    </form>}
  </section>;
}
