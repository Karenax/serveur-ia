import { documentLabels, workLabels } from '../lib/projectDeliverables';

export const deliverableActionLabels:Record<string,string>={deliverable_created:'Livrable créé',deliverable_metadata_changed:'Fiche du livrable modifiée',deliverable_legacy_changed:'Suivi du travail modifié',deliverable_check_created:'Point ajouté',deliverable_check_changed:'Point de checklist modifié',deliverable_version_published:'Version publiée',deliverable_version_metadata_changed:'Métadonnées de version modifiées',deliverable_status_changed:'Statut documentaire modifié',deliverable_selection_changed:'Sélection des livrables modifiée',deliverable_adopted:'Livrable rattaché à un type'};
const fieldLabels:Record<string,string>={id:'Identifiant',deliverable_id:'Livrable',project_id:'Projet',version_id:'Version',number:'Numéro de version',filename:'Fichier',size_bytes:'Taille en octets',sha256:'SHA-256 du fichier',manifest_sha256:'SHA-256 du manifeste',document_status:'Statut documentaire',legacy_status:'Statut du travail',title:'Intitulé',label:'Intitulé',code:'Code',proof:'Preuve',comment:'Commentaire',reference:'Référence',active:'Actif',completed:'Effectué',completed_at:'Date de confirmation',completed_by:'Opérateur de confirmation',completed_version_id:'Version confirmée',responsible_id:'Responsable',verifier_id:'Vérificateur',is_gate:'Visa obligatoire',transverse:'Progression transverse',contributes:'Contribue à la progression',milestone_id:'Jalon',milestone_ids:'Jalons associés',scope_key:'Portée',position:'Position',type_version_id:'Version du type',source_delivery_id:'Livraison CDC source',generated:'Document généré',actor_id:'Opérateur',checklist:'Checklist capturée',format:'Format du manifeste',version:'Version du format',publication:'Publication d’origine'};
export const evidenceLabel=(key:string)=>fieldLabels[key]||key.replace(/_/g,' ');
export function EvidenceValue({value,field}:{value:unknown;field?:string}) {
  if(value===undefined)return <span>Non enregistré</span>;
  if(value===null||value==='')return <span>—</span>;
  if(typeof value==='boolean')return <span>{value?'Oui':'Non'}</span>;
  if(Array.isArray(value))return value.length?<details><summary>{value.length} élément(s)</summary><ol>{value.map((item,index)=><li key={index}><EvidenceValue value={item}/></li>)}</ol></details>:<span>Aucun élément</span>;
  if(typeof value==='object')return <dl className="deliverable-evidence">{Object.entries(value).map(([key,item])=><div key={key}><dt>{evidenceLabel(key)}</dt><dd><EvidenceValue value={item} field={key}/></dd></div>)}</dl>;
  const displayed=field==='document_status'?documentLabels[String(value) as keyof typeof documentLabels]||value:field==='legacy_status'?workLabels[String(value)]||value:value;
  return <span className="deliverable-evidence-text">{String(displayed)}</span>;
}
export function EvidenceComparison({previous,value}:{previous:Record<string,unknown>;value:Record<string,unknown>}) {
  const keys=Array.from(new Set([...Object.keys(previous),...Object.keys(value)]));
  return <div className="planning-table-scroll"><table className="data-table deliverable-evidence-table"><thead><tr><th>Information</th><th>Avant</th><th>Après</th></tr></thead><tbody>{keys.map(key=><tr key={key}><th scope="row">{evidenceLabel(key)}</th><td><EvidenceValue field={key} value={previous[key]}/></td><td><EvidenceValue field={key} value={value[key]}/></td></tr>)}</tbody></table>{!keys.length&&<p>Aucun champ détaillé enregistré pour cette modification.</p>}</div>;
}
