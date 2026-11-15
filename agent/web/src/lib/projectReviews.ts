import { agentFetch } from './agentRoutes';
import { request } from './http';
import { withActivity } from './asyncActivity';
import type { Page } from './projectIdentity';

export const reviewSections = [
  {code:'vigilance_points',label:'Points de vigilance',required:true},
  {code:'expected_functions',label:'Fonctions attendues',required:true},
  {code:'initial_constraints',label:'Contraintes initiales',required:true},
  {code:'decisions',label:'Décisions',required:false},
  {code:'actions',label:'Actions',required:false},
] as const;
export type ReviewSection = typeof reviewSections[number]['code'];
export type ReviewParticipant = {person_id:string|null;name:string;function:string;signature_required:boolean};
export type ReviewItem = {id:string;section_code:ReviewSection;text:string;reviewed:boolean;evidence_ids:string[];owner:string;due_date:string};
export type ReviewContent = {meeting_date:string;location:string;notes:string;milestone_id:string|null;
  participants:ReviewParticipant[];items:ReviewItem[];deliverable_ids:string[]};
export type ReviewEvidence = {recording_id:string;brain_project_id:string;erp_project_id:string;source_id:string;
  revision:number;summary_model:string;summary_sha256:string;segment_id:string;quote:string;text:string;speaker:string;start:number;end:number};
export type ReviewRow = {id:string;number:number;status:'draft'|'published';review_revision:number;meeting_date:string;participants:number;updated_at:string};
export type ReviewDetail = Omit<ReviewRow,'meeting_date'|'participants'> & {project_id:string;type_code:'rlp';previous_review_id:string|null;
  revision:number;can_edit:boolean;can_create_revision:boolean;content:ReviewContent;provenance:Record<string,ReviewEvidence>;
  created_at:string;publication:null|{id:string;sha256:string;pdf_sha256:string;created_at:string};publication_blockers:string[]};
export type ReviewPage = Page<ReviewRow> & {revision:number;can_edit:boolean};
export type ReviewEvent = {id:string;action:string;actor_id:string;planning_revision:number;created_at:string};
export type ReviewBindings = {erp:Record<string,string>;brain:Record<string,string>};
export type ReviewEventDetail = ReviewEvent & {previous:Record<string,unknown>;value:Record<string,unknown>;bindings?:Partial<ReviewBindings>};
export type RecordingChoice = {id:string;title:string;date:string;revision:number;summary_model:string};
export type ReviewPublication = {id:string;sha256:string;pdf_sha256:string;bindings?:Partial<ReviewBindings>;snapshot:{project:{id:string;code:string;title:string};
  team:{person_id:string;role:string;name:string}[];deliverables:{id:string;title:string}[];
  review:{content:ReviewContent;provenance:Record<string,ReviewEvidence>};published_by:string;published_at:string}};
// Only resolve a declared relationship at use time. Frozen payload/text and
// local point, segment or evidence IDs never pass through this function.
export function reviewRelation(id:string,space:keyof ReviewBindings,bindings?:Partial<ReviewBindings>) {
  const map=bindings?.[space];
  return map&&Object.prototype.hasOwnProperty.call(map,id)&&typeof map[id]==='string'?map[id]:id;
}
const root=(id:string)=>`/api/v1/projects/${encodeURIComponent(id)}/reviews`;
const owner=(id:string,reviewId:string)=>`${root(id)}/${encodeURIComponent(reviewId)}`;
const stamp=(row:ReviewDetail)=>({expected_revision:row.revision,expected_review_revision:row.review_revision});
const command=<T,>(url:string,method:string,body:unknown)=>request<T>(url,{method,body:JSON.stringify(body)});
export const reviewApi={
  list:(id:string,offset=0,signal?:AbortSignal)=>request<ReviewPage>(`${root(id)}?offset=${offset}&limit=25`,{signal}),
  read:(id:string,reviewId:string,signal?:AbortSignal)=>request<ReviewDetail>(owner(id,reviewId),{signal}),
  create:(id:string,revision:number)=>command<ReviewDetail>(root(id),'POST',{expected_revision:revision}),
  save:(id:string,row:ReviewDetail,content:ReviewContent)=>command<ReviewDetail>(owner(id,row.id),'PUT',{...stamp(row),content}),
  newRevision:(id:string,row:ReviewDetail)=>command<ReviewDetail>(`${owner(id,row.id)}/revision`,'POST',stamp(row)),
  publish:(id:string,row:ReviewDetail)=>command<ReviewDetail>(`${owner(id,row.id)}/publish`,'POST',{...stamp(row),confirmed:true}),
  recordings:(id:string,offset=0,signal?:AbortSignal)=>request<Page<RecordingChoice>>(`${root(id)}/recording-choices?offset=${offset}&limit=25`,{signal}),
  importRecording:(id:string,row:ReviewDetail,source:RecordingChoice)=>command<ReviewDetail>(`${owner(id,row.id)}/recordings`,'POST',
    {...stamp(row),recording_id:source.id,expected_recording_revision:source.revision}),
  publication:(id:string,reviewId:string,signal?:AbortSignal)=>request<ReviewPublication>(`${owner(id,reviewId)}/publication`,{signal}),
  history:(id:string,reviewId:string,offset=0,signal?:AbortSignal)=>request<Page<ReviewEvent>>(`${owner(id,reviewId)}/history?offset=${offset}&limit=25`,{signal}),
  event:(id:string,reviewId:string,eventId:string,signal?:AbortSignal)=>request<ReviewEventDetail>(`${owner(id,reviewId)}/history/${encodeURIComponent(eventId)}`,{signal}),
  pdf:async(id:string,row:ReviewDetail,signal?:AbortSignal)=>withActivity('Téléchargement et vérification de la revue…',async()=>{
    if(!row.publication)throw new Error('Révision non publiée');
    const response=await agentFetch(`${owner(id,row.id)}/pdf`,{credentials:'same-origin',signal});
    if(!response.ok) {const value=await response.json();throw new Error(value.detail||'PDF indisponible');}
    const bytes=await response.arrayBuffer();
    if(signal?.aborted)throw new DOMException('Lecture annulée','AbortError');
    const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),v=>v.toString(16).padStart(2,'0')).join('');
    if(digest!==row.publication.pdf_sha256)throw new Error('Empreinte du PDF différente de la publication ; téléchargement interrompu');
    return new Blob([bytes],{type:'application/pdf'});
  }),
};

export const sameReviewValue=(a:unknown,b:unknown)=>JSON.stringify(a)===JSON.stringify(b);
export type ReviewConflict={key:string;label:string;base:unknown;mine:unknown;current:unknown};
const labels:Record<keyof ReviewContent,string>={meeting_date:'Date de revue',location:'Lieu',notes:'Notes',milestone_id:'Jalon',participants:'Participants',items:'Points de revue',deliverable_ids:'Livrables'};
// Merge only explicitly changed fields and stable item IDs. Conflicting changes
// remain explicit human choices; the latest server provenance is never edited.
export function mergeReviewContent(base:ReviewContent,mine:ReviewContent,current:ReviewContent,choices:Record<string,'mine'|'current'>={}) {
  const conflicts:ReviewConflict[]=[];
  function resolve(key:string,label:string,old:unknown,local:unknown,remote:unknown) {
    if(sameReviewValue(local,old)||sameReviewValue(local,remote))return remote;
    if(sameReviewValue(remote,old))return local;
    conflicts.push({key,label,base:old,mine:local,current:remote});
    return choices[key]==='mine'?local:remote;
  }
  const content=structuredClone(current);
  for(const key of ['meeting_date','location','notes','milestone_id','participants','deliverable_ids'] as const)
    Object.assign(content,{[key]:resolve(key,labels[key],base[key],mine[key],current[key])});
  const maps=[base,mine,current].map(value=>new Map(value.items.map(item=>[item.id,item])));
  const ids=[...new Set([...current.items,...mine.items,...base.items].map(item=>item.id))];
  content.items=ids.flatMap(id=>{
    const value=resolve(`item:${id}`,`Point · ${(maps[1].get(id)||maps[2].get(id)||maps[0].get(id))?.text||id}`,maps[0].get(id),maps[1].get(id),maps[2].get(id)) as ReviewItem|undefined;
    return value?[structuredClone(value)]:[];
  });
  return {content,conflicts,unresolved:conflicts.filter(conflict=>!choices[conflict.key])};
}
