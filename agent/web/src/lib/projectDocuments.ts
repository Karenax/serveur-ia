import { agentFetch } from './agentRoutes';
import { invalidateSession, request, token } from './http';
import { withActivity } from './asyncActivity';

export type DocumentId='offer_lt_simple'|'tdao'|'tdsp'|'manufacturing_specification'|'user_manual'|'ce_request'|
  'customer_satisfaction_product'|'customer_satisfaction_fixed_price';
export type DocumentTemplate={id:DocumentId;label:string;format:'DOCX'|'DOCM'|'XLSX'|'XLSM';fields:string[];
  cells:[string,string][];bookmarks:[string,string][];sheet_name:string|null;search_active?:boolean};
export type DocumentOrigin={kind:string;record_id:string|null;attribute:string|null};
export type DocumentValues={project_id:string;identity_revision:number;planning_revision:number;values:Record<string,string>;
  origins:Record<string,DocumentOrigin>;fields:Record<string,{label:string;edit_scope:string|null}>;missing_fields:string[];
  oversized_fields:string[];warnings:string[];overrides_scope:'one_document';read_only:true};
export type DocumentLink={id:string;code:string;label:string;path:string;order:number;missing?:boolean};
export type DocumentSearchItem={document_id:DocumentId;label:string;format:DocumentTemplate['format'];
  relative_paths:string[];filename_patterns:string[];excluded_tokens:string[];preferred_version:number|null;active:boolean;order:number};
export type DocumentPreferences={can_edit?:boolean;available:boolean;revision:number;version_id:string|null;items:DocumentSearchItem[]};
export type DocumentFormChoice={link_id:string|null;relative_path:string;overrides:Record<string,string>};
export type DocumentDraft=DocumentFormChoice&{available:boolean;revision:number;version_id:string|null;
  selected_link:DocumentLink|null;warnings:string[]};
export type DocumentJournal={id:string;revision:number;sha256:string;created_at:string;
  value:{actor_id:string;choice?:DocumentFormChoice;items?:DocumentSearchItem[];restored_from?:string|null};bindings?:Record<string,string|null>};
export type DocumentPage<T>={items:T[];total:number;offset:number;limit:number};
export type DocumentWorkspace=DocumentValues&{values_sha256:string;templates:DocumentTemplate[];
  links:{items:DocumentLink[];total:number;offset:number;limit:number};file_access:{status:'configured'|'disabled'|'invalid';detail:string};
  can_prepare_copy:boolean;publication:'explicit_separate_command';batch_available:boolean;search_preferences?:DocumentPreferences};
export type DocumentChoice={document_id:DocumentId;link_id:string;relative_path:string;overrides:Record<string,string>};
export type DocumentCandidate={relative_path:string;filename:string;size_bytes:number;modified_ns:number;
  matched_paths:string[];matched_patterns:string[];version:number|null;version_origin:'explicit'|'name_numbers'|'unknown';
  rank:number;direct_file_link:boolean;requires_preview:true};
export type DocumentDiscovery={project_id:string;link_id:string;document_id:DocumentId;rule_sha256:string;
  rule:{relative_paths:string[];filename_patterns:string[];excluded_tokens:string[];preferred_version:number|null};
  status:'completed'|'limited'|'cancelled';examined:{entries:number;files:number;directories:number};total:null;
  bounds:string[];skipped:Record<string,number>;candidates:DocumentCandidate[];ambiguous:boolean;
  recommended_path:string|null;elapsed_seconds:number;read_only:true;requires_manual_choice:true;
  preferences_revision?:number;preferences_version_id?:string|null};
export type DocumentFolderDiscovery=Pick<DocumentDiscovery,'project_id'|'link_id'|'status'|'bounds'|'examined'>&{
  items:(DocumentDiscovery&{existing_files:{filename:string;relative_path:string}[];missing_fields:string[]})[]};
export type DocumentTarget={kind:'cell'|'bookmark';target:string;field:string;present:boolean;available:boolean;
  existing_value:string;proposed_value:string;blockers:string[];replaces_placeholder?:boolean};
export type DocumentPreview={document_id:DocumentId;format:string;source_sha256:string;link_sha256:string;values_sha256:string;size_bytes:number;
  source:{project_id:string;link_id:string;relative_path:string;filename:string;sha256:string};field_values:DocumentValues;
  part:string;sheet:string|null;targets:DocumentTarget[];missing_fields:string[];missing_targets:string[];blockers:string[];
  can_prepare:boolean;can_prepare_copy:boolean;macro_parts:Record<string,string>;unmapped_fields:string[];
  output_filename:string|null;output_filename_error:string|null};
export class DocumentHttpError extends Error {constructor(public status:number,message:string){super(message);}}
const root=(id:string)=>`/api/v1/projects/${encodeURIComponent(id)}/documents`;
const maxBytes=50*1024*1024;
async function discover<T>(id:string,path:string,body:object,signal?:AbortSignal) {
  const controller=new AbortController(),cancel=()=>controller.abort();let expired=false;
  signal?.addEventListener('abort',cancel,{once:true});if(signal?.aborted)cancel();
  const timeout=window.setTimeout(()=>{expired=true;cancel();},30_000);
  try{
    if(controller.signal.aborted)throw new DOMException('Recherche annulée','AbortError');
    return await request<T>(root(id)+path,{method:'POST',signal:controller.signal,body:JSON.stringify(body)});
  }catch(error){if(expired)throw new Error('Recherche trop longue. Vérifiez la disponibilité du dossier puis réessayez.');throw error;}
  finally{window.clearTimeout(timeout);signal?.removeEventListener('abort',cancel);}
}
function searchPreferencesApi(path:string) {
  return {
    preferences:(signal?:AbortSignal)=>request<DocumentPreferences>(path,{signal}),
    savePreferences:(revision:number,items:DocumentSearchItem[],signal?:AbortSignal)=>request<DocumentPreferences>(path,
      {method:'PUT',body:JSON.stringify({expected_revision:revision,items}),signal}),
    preferencesHistory:(offset=0,signal?:AbortSignal)=>request<DocumentPage<DocumentJournal>>(`${path}/history?offset=${offset}&limit=20`,{signal}),
    restorePreferences:(revision:number,versionId:string,signal?:AbortSignal)=>request<DocumentPreferences>(path+'/restore',
      {method:'POST',body:JSON.stringify({expected_revision:revision,version_id:versionId}),signal}),
  };
}
export const sharedDocumentPreferences=searchPreferencesApi('/api/v1/document-settings');
export const documentApi={
  draft:(id:string,doc:DocumentId,signal?:AbortSignal)=>request<DocumentDraft>(`${root(id)}/forms/${doc}`,{signal}),
  saveDraft:(id:string,doc:DocumentId,revision:number,choice:DocumentFormChoice,signal?:AbortSignal)=>request<DocumentDraft>(`${root(id)}/forms/${doc}`,
    {method:'PUT',body:JSON.stringify({expected_revision:revision,...choice}),signal}),
  draftHistory:(id:string,doc:DocumentId,offset=0,signal?:AbortSignal)=>request<DocumentPage<DocumentJournal>>(`${root(id)}/forms/${doc}/history?offset=${offset}&limit=20`,{signal}),
  restoreDraft:(id:string,doc:DocumentId,revision:number,versionId:string,signal?:AbortSignal)=>request<DocumentDraft>(`${root(id)}/forms/${doc}/restore`,
    {method:'POST',body:JSON.stringify({expected_revision:revision,version_id:versionId}),signal}),
  ...searchPreferencesApi('/api/v1/document-settings/personal'),
  workspace:(id:string,offset=0,signal?:AbortSignal)=>request<DocumentWorkspace>(`${root(id)}?offset=${offset}&limit=100`,{signal}),
  preview:(id:string,choice:DocumentChoice,signal?:AbortSignal)=>request<DocumentPreview>(root(id)+'/preview',
    {method:'POST',body:JSON.stringify(choice),signal}),
  discover:(id:string,documentId:DocumentId,linkId:string,signal?:AbortSignal)=>
    discover<DocumentDiscovery>(id,'/discover',{document_id:documentId,link_id:linkId},signal),
  discoverFolder:(id:string,linkId:string,signal?:AbortSignal)=>
    discover<DocumentFolderDiscovery>(id,'/discover-folder',{link_id:linkId},signal),
  copy:async(id:string,choice:DocumentChoice,preview:DocumentPreview,signal?:AbortSignal)=>withActivity('Préparation et vérification du document…',async()=>{
    if(!preview.can_prepare||!preview.can_prepare_copy||!preview.output_filename)throw new Error('Aperçu complet et autorisation de préparation requis');
    if(preview.document_id!==choice.document_id||preview.source.project_id!==id||preview.source.link_id!==choice.link_id||
       preview.source.relative_path!==choice.relative_path)throw new Error('Aperçu différent du fichier sélectionné');
    const controller=new AbortController(),cancel=()=>controller.abort();
    signal?.addEventListener('abort',cancel,{once:true});if(signal?.aborted)cancel();
    const timeout=window.setTimeout(cancel,120_000);
    try{
      const csrf=await token();if(controller.signal.aborted)throw new DOMException('Préparation annulée','AbortError');
      const response=await agentFetch(root(id)+'/prepare-copy',{method:'POST',credentials:'same-origin',signal:controller.signal,
        headers:{'Content-Type':'application/json','X-Agent-Token':csrf},body:JSON.stringify({...choice,
          expected_source_sha256:preview.source_sha256,expected_link_sha256:preview.link_sha256,expected_values_sha256:preview.values_sha256,
          expected_identity_revision:preview.field_values.identity_revision,expected_planning_revision:preview.field_values.planning_revision})});
      if(!response.ok){if(response.status===403)invalidateSession();const data=await response.json();
        throw new DocumentHttpError(response.status,typeof data.detail==='string'?data.detail:'Préparation du document indisponible');}
      if(response.headers.get('x-agent-source-sha256')!==preview.source_sha256||
         response.headers.get('x-agent-link-sha256')!==preview.link_sha256||
         response.headers.get('x-agent-values-sha256')!==preview.values_sha256||response.headers.get('x-agent-network-published')!=='false')
        throw new Error('Copie reçue différente de l’aperçu approuvé');
      const expected=response.headers.get('etag')?.match(/^"([0-9a-f]{64})"$/)?.[1];
      if(!expected)throw new Error('Empreinte de la copie absente');
      const size=response.headers.get('content-length');
      if(size!==null&&(!/^\d+$/.test(size)||Number(size)>maxBytes))throw new Error('Copie trop volumineuse');
      const bytes=await response.arrayBuffer();
      if(!bytes.byteLength||bytes.byteLength>maxBytes)throw new Error('Taille de copie invalide');
      const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),v=>v.toString(16).padStart(2,'0')).join('');
      if(controller.signal.aborted)throw new DOMException('Préparation annulée','AbortError');
      if(digest!==expected)throw new Error('Empreinte de la copie incorrecte ; téléchargement interrompu');
      return {blob:new Blob([bytes],{type:'application/octet-stream'}),filename:preview.output_filename,sha256:digest};
    }finally{window.clearTimeout(timeout);signal?.removeEventListener('abort',cancel);}
  }),
};

export const originLabel=(origin?:DocumentOrigin)=>({project:'Projet',project_profile:'Fiche projet',client:'Référentiel client',person:'Équipe projet',
  server_date:'Date du jour',document_override:'Correction de cette copie',missing:'À renseigner'}[origin?.kind||'missing']||'Donnée projet');
export const warningLabel=(code:string)=>({client_archived:'Le client sélectionné est archivé.',client_reference_missing:'La référence client est introuvable.',
  responsible_archived:'Le responsable sélectionné est archivé.',responsible_reference_missing:'Le responsable du projet est introuvable.',
  agency_contact_details_not_configured:'Les coordonnées d’agence sont à renseigner pour cette copie.'}[code]||code);
export const blockerLabel=(code:string)=>({formula:'Une formule occupe cette cellule.',merged_non_anchor:'La cellule fait partie d’une fusion.',
  sheet_protected:'La feuille est protégée.',bookmark_missing:'Signet absent.',bookmark_ambiguous:'Signet présent plusieurs fois.',
  bookmark_overlap:'Signets imbriqués ou superposés.',bookmark_field:'Signet contenant un champ Word.',bookmark_structure:'Structure du signet incompatible.',
  document_protected:'Le document Word est protégé.',signed_package:'Le fichier comporte une signature Office.',output_filename_invalid:'Le nom de sortie est invalide.'}
  [code]|| (code.startsWith('target_unavailable:')?'Aucune cible disponible pour ce champ.':code));
export const discoveryBoundLabel=(code:string)=>({entries:'nombre d’entrées',directories:'nombre de dossiers',depth:'profondeur',
  candidates:'nombre de candidats',time:'durée'}[code]||code);
