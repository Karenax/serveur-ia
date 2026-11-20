import { request } from './http';
import type { DocumentPage } from './projectDocuments';

export type PublicationChoice={link_id:string;relative_directory:string;replace_existing:boolean};
export type PublicationCommand=Omit<PublicationChoice,'replace_existing'>&{replace_existing?:boolean;command_id:string;expected_revision:number;expected_preview_sha256:string;reviewed:true;link_to_project?:boolean};
export type FileReceipt={identity:string;sha256:string;size_bytes:number};
export type PublicationPreview={project_id:string;job_id:string;job_revision:number;artifact_id:string;filename:string;
  destination:string;directory:string;directory_identity:string;preview_sha256:string;occupied:boolean;
  can_publish:boolean;blockers:string[];publication_command_available:boolean;existing_receipt:FileReceipt|null;
  link_id:string;relative_directory:string;replace_existing:boolean;version:number};
export type PublicationState='requested'|'prepared'|'backup_requested'|'backup_saved'|'succeeded'|'abandoned';
export type PublicationRecord={project_id:string;job_id:string;job_revision:number;artifact_id:string;command_id:string;
  command:PublicationCommand;state:PublicationState;network_published:boolean;execution_blocked:boolean;
  needs_inspection:boolean;can_resume:boolean;can_abandon:boolean;destination:string;candidate:string;
  receipt:FileReceipt|null;backup:string|null;backup_receipt:FileReceipt|null;requested_revision:number;updated_revision:number};
export type Publications=DocumentPage<PublicationRecord>&{project_id:string;job_id:string;job_revision:number;execution_blocked:boolean};
export type PublicationAbandon={expected_revision:number;retain_files:true;reviewed:true};
const root=(pid:string)=>`/api/v1/projects/${encodeURIComponent(pid)}/documents`;
async function bounded<T>(parent:AbortSignal|undefined,ms:number,run:(signal:AbortSignal)=>Promise<T>){
  const controller=new AbortController(),cancel=()=>controller.abort();
  parent?.addEventListener('abort',cancel,{once:true});if(parent?.aborted)cancel();
  const timer=window.setTimeout(cancel,ms);
  try{if(controller.signal.aborted)throw new DOMException('Opération annulée','AbortError');return await run(controller.signal);}
  finally{window.clearTimeout(timer);parent?.removeEventListener('abort',cancel);}
}
function scope<T extends {project_id:string;job_id:string;artifact_id:string}>(value:T,pid:string,jid:string,aid:string){
  if(value.project_id!==pid||value.job_id!==jid||value.artifact_id!==aid)throw new Error('Publication reçue hors de la copie sélectionnée');return value;
}
export const publicationApi={
  preview:async(pid:string,jid:string,aid:string,choice:PublicationChoice,signal?:AbortSignal)=>scope(await bounded(signal,120_000,s=>
    request<PublicationPreview>(`${root(pid)}/artifacts/${encodeURIComponent(aid)}/publication-preview`,{method:'POST',body:JSON.stringify(choice),signal:s})),pid,jid,aid),
  publish:async(pid:string,jid:string,aid:string,command:PublicationCommand,signal?:AbortSignal)=>{
    const value=scope(await bounded(signal,120_000,s=>request<PublicationRecord>(`${root(pid)}/artifacts/${encodeURIComponent(aid)}/publish`,
      {method:'POST',body:JSON.stringify(command),signal:s})),pid,jid,aid);
    if(value.command_id!==command.command_id)throw new Error('Reçu différent de la commande envoyée');return value;
  },
  list:async(pid:string,jid:string,aid:string,offset=0,signal?:AbortSignal,quiet=false)=>{
    const value=await bounded(signal,15_000,s=>request<Publications>(`${root(pid)}/jobs/${encodeURIComponent(jid)}/publications?artifact_id=${encodeURIComponent(aid)}&offset=${offset}&limit=20`,{signal:s,activity:quiet?false:undefined}));
    if(value.project_id!==pid||value.job_id!==jid)throw new Error('Historique reçu hors du lot sélectionné');
    value.items.forEach(row=>scope(row,pid,jid,aid));return value;
  },
  abandon:async(pid:string,jid:string,aid:string,cid:string,payload:PublicationAbandon,signal?:AbortSignal)=>{
    const value=scope(await bounded(signal,120_000,s=>request<PublicationRecord>(`${root(pid)}/jobs/${encodeURIComponent(jid)}/publications/${encodeURIComponent(cid)}/abandon`,
      {method:'POST',body:JSON.stringify(payload),signal:s})),pid,jid,aid);
    if(value.command_id!==cid)throw new Error('Clôture reçue pour une autre commande');return value;
  },
};
export const publicationStateLabel=(state:PublicationState)=>({requested:'À vérifier',prepared:'Copie préparée',backup_requested:'Sauvegarde demandée',
  backup_saved:'Original sauvegardé',succeeded:'Publication enregistrée',abandoned:'Commande clôturée'}[state]);
export const publicationBlockerLabel=(code:string)=>({read_only:'Consultation uniquement.',execution_blocked:'Historique suspendu après import ou restauration.',
  job_active:'Terminez ou interrompez le lot avant la publication.',destination_occupied:'Un fichier existe : choisissez explicitement son remplacement pour conserver une sauvegarde.',
  replacement_target_missing:'Aucun original à remplacer : désactivez ce choix.',replacement_not_supported:'Le remplacement nécessite un serveur Windows.',
  source_changed:'Le fichier existant a changé depuis la préparation. Refaites l’aperçu et préparez une nouvelle copie.'}[code]||code);
export const pendingKey=(pid:string,aid:string)=>'agent.publication.v2:'+JSON.stringify([pid,aid]);
export function readPending(pid:string,aid:string):PublicationCommand|null{
  const raw=localStorage.getItem(pendingKey(pid,aid));if(!raw)return null;
  const value=JSON.parse(raw) as PublicationCommand;
  const required=['command_id','expected_revision','expected_preview_sha256','link_id','relative_directory','reviewed'];
  const keys=value?Object.keys(value):[];
  if(!value||!required.every(key=>keys.includes(key))||keys.some(key=>!required.includes(key)&&key!=='replace_existing'&&key!=='link_to_project')||
    !Number.isSafeInteger(value.expected_revision)||value.expected_revision<1||
    typeof value.command_id!=='string'||typeof value.expected_preview_sha256!=='string'||
    !/^[a-zA-Z0-9_-]{1,36}$/.test(value.command_id)||!/^[a-f0-9]{64}$/.test(value.expected_preview_sha256)||
    typeof value.link_id!=='string'||!value.link_id||value.link_id.length>36||typeof value.relative_directory!=='string'||value.relative_directory.length>2048||
    'replace_existing' in value&&typeof value.replace_existing!=='boolean'||
    'link_to_project' in value&&typeof value.link_to_project!=='boolean'||value.reviewed!==true)throw new Error('Commande locale illisible : consultez les reçus avant de préparer une nouvelle publication.');
  return value;
}
