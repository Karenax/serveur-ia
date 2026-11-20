import { agentFetch } from './agentRoutes';
import { invalidateSession, request } from './http';
import { withActivity } from './asyncActivity';
import type { DocumentChoice, DocumentPage } from './projectDocuments';
import type { PublicationChoice } from './projectDocumentPublications';

export type BatchItem=DocumentChoice&{expected_source_sha256:string;expected_link_sha256:string;expected_values_sha256:string;
  expected_identity_revision:number;expected_planning_revision:number;expected_draft_revision:number};
export type BatchCommand={command_id:string;items:BatchItem[]};
export type JobStatus='queued'|'running'|'completed'|'failed'|'cancelled'|'interrupted';
export type FileStatus='queued'|'running'|'succeeded'|'failed'|'cancelled'|'interrupted';
export type DocumentWorker={state:string;enabled:boolean;running:boolean;can_submit:boolean;error:string};
export type DocumentJobSummary={id:string;project_id:string;status:JobStatus;revision:number;total:number;processed:number;
  progress:number;cancel_requested:boolean;execution_blocked:boolean;can_cancel:boolean;can_retry:boolean;created_at:string;updated_at:string};
export type DocumentJob=DocumentJobSummary&{actor_id:string;items:{id:string;document_id:BatchItem['document_id'];position:number;
  status:FileStatus;last_attempt_id:string|null;artifact_id:string|null;error:string;
  publication_suggestion?:PublicationChoice|null}[]};
export type DocumentJobs=DocumentPage<DocumentJobSummary>&{available:boolean;worker:DocumentWorker};
export type DocumentEvent={id:string;revision:number;kind:string;actor_id:string;detail:Record<string,unknown>;created_at:string};
export type DocumentAttempt={id:string;item_id:string;number:number;actor_id:string;created_at:string;finished_at:string|null;
  outcome:'running'|'succeeded'|'failed'|'interrupted';artifact_id:string|null;error:string};
const root=(id:string)=>`/api/v1/projects/${encodeURIComponent(id)}/documents`;
const maxBytes=50*1024*1024;

async function bounded<T>(signal:AbortSignal|undefined, milliseconds:number, action:(signal:AbortSignal)=>Promise<T>) {
  const controller=new AbortController(),cancel=()=>controller.abort();
  signal?.addEventListener('abort',cancel,{once:true});if(signal?.aborted)cancel();
  const timer=window.setTimeout(cancel,milliseconds);
  try {if(controller.signal.aborted)throw new DOMException('Opération annulée','AbortError');return await action(controller.signal);}
  finally {window.clearTimeout(timer);signal?.removeEventListener('abort',cancel);}
}
async function jobRequest(projectId:string,url:string,init:RequestInit & {activity?:string|false},signal?:AbortSignal) {
  const value=await bounded(signal,120_000,s=>request<DocumentJob>(url,{...init,signal:s}));
  if(value.project_id!==projectId)throw new Error('Lot reçu hors du projet sélectionné');
  return value;
}
export const documentJobApi={
  list:async(id:string,offset=0,signal?:AbortSignal,quiet=false)=>{
    const value=await bounded(signal,15_000,s=>request<DocumentJobs>(`${root(id)}/jobs?offset=${offset}&limit=20`,{signal:s,activity:quiet?false:undefined}));
    if(value.items.some(row=>row.project_id!==id))throw new Error('Liste reçue hors du projet sélectionné');return value;
  },
  detail:(id:string,jobId:string,signal?:AbortSignal,quiet=false)=>jobRequest(id,`${root(id)}/jobs/${encodeURIComponent(jobId)}`,quiet?{activity:false}:{},signal),
  submit:(id:string,command:BatchCommand,signal?:AbortSignal)=>jobRequest(id,`${root(id)}/jobs`,{method:'POST',body:JSON.stringify(command)},signal),
  cancel:(id:string,job:DocumentJob,signal?:AbortSignal)=>jobRequest(id,`${root(id)}/jobs/${encodeURIComponent(job.id)}/cancel`,
    {method:'POST',body:JSON.stringify({expected_revision:job.revision})},signal),
  retry:(id:string,job:DocumentJob,signal?:AbortSignal)=>jobRequest(id,`${root(id)}/jobs/${encodeURIComponent(job.id)}/retry`,
    {method:'POST',body:JSON.stringify({expected_revision:job.revision})},signal),
  events:(id:string,jobId:string,offset=0,signal?:AbortSignal)=>bounded(signal,15_000,s=>request<DocumentPage<DocumentEvent>>(
    `${root(id)}/jobs/${encodeURIComponent(jobId)}/events?offset=${offset}&limit=20`,{signal:s})),
  attempts:(id:string,jobId:string,offset=0,signal?:AbortSignal)=>bounded(signal,15_000,s=>request<DocumentPage<DocumentAttempt>>(
    `${root(id)}/jobs/${encodeURIComponent(jobId)}/attempts?offset=${offset}&limit=20`,{signal:s})),
  download:(id:string,artifactId:string,signal?:AbortSignal)=>withActivity('Téléchargement et vérification du document…',()=>bounded(signal,120_000,async s=>{
    const response=await agentFetch(`${root(id)}/artifacts/${encodeURIComponent(artifactId)}`,{credentials:'same-origin',signal:s});
    if(!response.ok){if(response.status===403)invalidateSession();const value=await response.json();
      throw new Error(typeof value.detail==='string'?value.detail:'Téléchargement documentaire indisponible');}
    const expected=response.headers.get('etag')?.match(/^"([0-9a-f]{64})"$/)?.[1];
    if(!expected||response.headers.get('x-agent-network-published')!=='false')throw new Error('Reçu de copie documentaire invalide');
    const encoded=response.headers.get('content-disposition')?.match(/^attachment;\s*filename\*=UTF-8''(.+)$/i)?.[1];
    let filename='';try{filename=decodeURIComponent(encoded||'');}catch{throw new Error('Nom de copie documentaire invalide');}
    if(!filename||filename.length>255||/[\\/:\x00-\x1f]/.test(filename)||filename==='.'||filename==='..')throw new Error('Nom de copie documentaire invalide');
    const length=response.headers.get('content-length');
    if(length!==null&&(!/^\d+$/.test(length)||Number(length)>maxBytes))throw new Error('Copie trop volumineuse');
    const bytes=await response.arrayBuffer();
    if(s.aborted)throw new DOMException('Téléchargement annulé','AbortError');
    if(!bytes.byteLength||bytes.byteLength>maxBytes)throw new Error('Taille de copie invalide');
    const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),v=>v.toString(16).padStart(2,'0')).join('');
    if(s.aborted)throw new DOMException('Téléchargement annulé','AbortError');
    if(digest!==expected)throw new Error('Empreinte de copie incorrecte ; téléchargement interrompu');
    return {url:`${root(id)}/artifacts/${encodeURIComponent(artifactId)}`,filename,sha256:digest};
  })),
};
export const documentJobLabel=(status:JobStatus|FileStatus)=>({queued:'En attente',running:'En cours',completed:'Terminé',
  succeeded:'Copie prête',failed:'Échec',cancelled:'Arrêté',interrupted:'Interrompu'}[status]);
export const documentEventLabel=(kind:string)=>({submitted:'Lot soumis',cancel_requested:'Arrêt demandé',retry_requested:'Reprise demandée',
  item_started:'Fichier commencé',item_succeeded:'Copie validée',item_failed:'Préparation échouée',item_interrupted:'Tentative interrompue',
  worker_interrupted:'Worker interrompu',store_restored:'Sauvegarde restaurée',archive_imported:'Archive importée',
  publication_requested:'Publication demandée',publication_prepared:'Copie prête à publier',publication_backup_requested:'Sauvegarde de l’original demandée',
  publication_backup_saved:'Original sauvegardé',publication_succeeded:'Publication enregistrée',publication_abandoned:'Intention de publication clôturée'}[kind]||kind);
