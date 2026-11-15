import { agentFetch } from './agentRoutes';
import { request } from './http';
import { withActivity } from './asyncActivity';
import type { Page } from './projectIdentity';
import type { ProjectReference } from './projectIdentity';
import type { Delivery, NetworkLink } from './api';

export type DocumentStatus='draft'|'to_verify'|'validated'|'to_revise'|'archived';
export type Category='studies'|'fabrication'|'project_end'|'custom';
export const documentLabels:Record<DocumentStatus,string>={draft:'Brouillon',to_verify:'À vérifier',validated:'Validé',to_revise:'À réviser',archived:'Archivé'};
export const categoryLabels:Record<Category,string>={studies:'Études',fabrication:'Fabrication',project_end:'Fin de projet',custom:'Personnalisé'};
export const workLabels:Record<string,string>={todo:'À faire',in_progress:'En cours',done:'Terminé',cancelled:'Annulé'};
// SQLite checklist evidence uses naive UTC ISO dates; other L3 reads carry an
// explicit UTC offset. Interpret both correctly without changing stored proof.
export function deliverableDate(value:string) {const date=new Date(/[zZ]$|[+-]\d{2}:?\d{2}$/.test(value)?value:value+'Z');return Number.isNaN(date.getTime())?value:date.toLocaleString('fr-FR');}
export type Progress={completed:number;total:number;percentage:number;state:string};
export type FileVersion={id:string;number:number;filename:string;size_bytes:number;sha256:string;manifest_sha256:string;
  generated:boolean;source_delivery_id:string|null;actor_id:string;created_at:string;reference:string|null;comment:string|null};
export type VersionDetail=FileVersion&{revision:number;manifest:Record<string,unknown>;published_manifest:Record<string,unknown>};
export type DeliverableRow={id:string;project_id:string;title:string;legacy_status:string;active:boolean;document_status:DocumentStatus;
  responsible_id:string|null;verifier_id:string|null;type_version_id:string|null;category:Category;type:{id:string;code:string;label:string}|null;
  progress:Progress;transverse_progress:Progress;latest_version:FileVersion|null;milestone_ids:string[]};
export type CheckItem={id:string;code:string;scope_key:string;milestone_id:string|null;label:string;position:number;is_gate:boolean;
  transverse:boolean;contributes:boolean;active:boolean;completed:boolean;completed_version_id:string|null;completed_by:string|null;
  completed_at:string|null;comment:string;proof:string};
export type DeliverableDetail=Omit<DeliverableRow,'category'|'type'|'latest_version'> & {revision:number;comment:string;latest_version_id:string|null;
  latest_version?:FileVersion|null;can_edit:boolean;can_verify:boolean;checklist:CheckItem[];validation_blockers:{id:string;label:string;reason:string}[]};
export function deliverableVersionLabel(detail:DeliverableDetail) {return detail.latest_version?`V${detail.latest_version.number} · ${detail.latest_version.reference||detail.latest_version.filename} · ${detail.latest_version.filename}`:detail.latest_version_id?'Version publiée':'Aucune version publiée';}
export type DeliverableFields={title:string;responsible_id:string|null;verifier_id:string|null;comment:string;active:boolean};
export type DeliverableInput={title:string;responsible_id?:string|null;verifier_id?:string|null;type_version_id?:string|null;milestone_ids?:string[];milestone_mapping?:Record<string,string>};
export type RevisionPage<T>=Page<T>&{revision:number};
export type DeliverablePage=RevisionPage<DeliverableRow>&{can_edit:boolean};
export type DeliverableEvent={id:string;revision:number;action:string;actor_id:string;created_at:string};
export type EventDetail=DeliverableEvent&{previous:Record<string,unknown>;value:Record<string,unknown>};
export type CheckDefinition={code:string;label:string;milestone_code:string;is_gate:boolean;transverse:boolean;contributes:boolean;active:boolean;typology_codes:string[]};
export type TypeDefinition={category:Exclude<Category,'custom'>;design:boolean;position:number;checklist:CheckDefinition[]};
export type TypeHead={id:string;code:string;label:string;active:boolean;revision:number};
export type TypeVersion={id:string;number:number;sha256:string;created_at?:string};
export type TypeVersionDetail=TypeVersion&{type_id:string;definition:TypeDefinition;published_definition:Record<string,unknown>};
export type CatalogueRow=TypeHead&{latest_version:(TypeVersion&{position:number})|null};
export type CataloguePage=Page<CatalogueRow>&{can_manage:boolean};
export type ConditionTypology=ProjectReference&{condition_code:string};
export type StandardCatalogue={format:string;version:number;source:Record<string,unknown>;types:{code:string;label:string;order:number;definition:TypeDefinition}[]};
export type TypologyComposition={typology_id:string;code:string;revision:number;type_ids:string[];active:boolean};
export type GateCheck={id:string;label:string;deliverable_id:string;deliverable_title:string;version_id:string|null;ready:boolean;reason:string|null;
  version:{id:string;number:number;filename:string;reference:string}|null;responsible_id:string|null;responsible_name:string|null;verifier_id:string|null;verifier_name:string|null};
export type GatePage=Page<GateCheck>&{milestone_id:string;revision:number;can_validate:boolean;checks_total:number;blocking_total:number};
export type DeliverableFocus={requestId:number;deliverableId:string;checkId:string;milestoneId:string;milestoneTitle:string;version:GateCheck['version'];origin?:'cockpit'|'gate'|'review'};
export type SelectionInputs={expected_revision:number;type_version_ids:string[];typology_id:string|null;milestone_mapping:Record<string,string>;excluded_milestone_codes:string[];existing_mapping:Record<string,string>;deactivate_missing:boolean;responsible_id:string|null;verifier_id:string|null};
export type SelectionOperation={operation:'create'|'adopt'|'reactivate'|'keep'|'deactivate';type_id:string;version_id:string;deliverable_id:string|null;label:string};
export type SelectionIssue={message:string;type_id?:string;deliverable_id?:string;code?:string;candidate_ids?:string[];retained_version_id?:string};
export type SelectionPreview={project_id:string;revision:number;can_edit:boolean;operations:SelectionOperation[];blockers:SelectionIssue[];warnings:SelectionIssue[];sha256:string;changes:number};
export type ListOptions={search?:string;include_inactive?:boolean;status?:DocumentStatus|'';category?:Category|'';
  responsible_id?:string|null;verifier_id?:string|null;milestone_id?:string|null;offset?:number;limit?:number;signal?:AbortSignal};
const part=encodeURIComponent;
const root=(projectId:string)=>`/api/v1/projects/${part(projectId)}/deliverable-plan`;
const owner=(projectId:string,id:string)=>`${root(projectId)}/${part(id)}`;
function query(options:Record<string,unknown>) {const params=new URLSearchParams();for(const [key,value] of Object.entries(options))
  if(key!=='signal'&&value!==null&&value!==undefined&&value!=='')params.set(key,String(value));return params.size?`?${params}`:'';}
const json=(method:string,body:unknown):RequestInit=>({method,body:JSON.stringify(body)});
export const deliverableApi={
  milestoneGates:(projectId:string,milestoneId:string,options:{include_ready?:boolean;offset?:number;limit?:number;signal?:AbortSignal}={})=>request<GatePage>(root(projectId)+`/milestones/${part(milestoneId)}/gates/page`+query(options),{signal:options.signal}),
  types:(options:{search?:string;offset?:number;limit?:number;typology_id?:string|null;include_inactive?:boolean;signal?:AbortSignal}={})=>request<CataloguePage>('/api/v1/deliverable-types'+query(options),{signal:options.signal}),
  typeVersions:(typeId:string,options:{offset?:number;limit?:number;signal?:AbortSignal}={})=>request<Page<TypeVersion>>(`/api/v1/deliverable-types/${part(typeId)}/versions`+query(options),{signal:options.signal}),
  typeVersion:(typeId:string,versionId:string,signal?:AbortSignal)=>request<TypeVersionDetail>(`/api/v1/deliverable-types/${part(typeId)}/versions/${part(versionId)}`,{signal}),
  typeHead:(typeId:string,signal?:AbortSignal)=>request<TypeHead>(`/api/v1/deliverable-types/${part(typeId)}`,{signal}),
  standardTypes:(signal?:AbortSignal)=>request<StandardCatalogue>('/api/v1/deliverable-types/standard-definition',{signal}),
  conditionTypologies:(options:{search?:string;offset?:number;limit?:number;include_inactive?:boolean;signal?:AbortSignal}={})=>request<Page<ConditionTypology>>('/api/v1/deliverable-types/condition-typologies'+query(options),{signal:options.signal}),
  createType:(fields:{code:string;label:string;definition:TypeDefinition})=>request<{id:string;version_id:string;revision:number;sha256:string}>('/api/v1/deliverable-types',json('POST',fields)),
  publishType:(typeId:string,revision:number,definition:TypeDefinition)=>request<{id:string;version_id:string;revision:number;sha256:string}>(`/api/v1/deliverable-types/${part(typeId)}/versions`,json('POST',{expected_revision:revision,definition})),
  patchType:(typeId:string,revision:number,fields:{label?:string;active?:boolean})=>request<TypeHead>(`/api/v1/deliverable-types/${part(typeId)}`,json('PATCH',{...fields,expected_revision:revision})),
  composition:(typologyId:string,signal?:AbortSignal)=>request<TypologyComposition>(`/api/v1/project-references/${part(typologyId)}/deliverable-types`,{signal}),
  patchComposition:(typologyId:string,revision:number,typeIds:string[])=>request<TypologyComposition>(`/api/v1/project-references/${part(typologyId)}/deliverable-types`,json('PATCH',{expected_revision:revision,type_ids:typeIds})),
  previewSelection:(pid:string,inputs:SelectionInputs,signal?:AbortSignal)=>request<SelectionPreview>(root(pid)+'/selection/preview',{...json('POST',inputs),signal}),
  applySelection:(pid:string,inputs:SelectionInputs,sha256:string)=>request<{revision:number;changed:SelectionOperation[];warnings:SelectionIssue[]}>(root(pid)+'/selection/apply',json('POST',{...inputs,expected_preview_sha256:sha256})),
  list:(pid:string,options:ListOptions={})=>request<DeliverablePage>(root(pid)+query(options),{signal:options.signal}),
  detail:async(pid:string,id:string,signal?:AbortSignal)=>{
    const detail=await request<DeliverableDetail>(owner(pid,id),{signal});
    if(!detail.latest_version_id)return {...detail,latest_version:null};
    try {const version=await request<FileVersion>(owner(pid,id)+`/versions/${part(detail.latest_version_id)}`,{signal},15000);
      // Descriptive metadata never replaces the captured command revision/ID.
      return {...detail,latest_version:version};
    }catch(error){if(signal?.aborted)throw error;return detail;}
  },
  create:(pid:string,revision:number,fields:DeliverableInput)=>request<{id:string;revision:number}>(root(pid),json('POST',{...fields,expected_revision:revision})),
  patch:(pid:string,id:string,revision:number,fields:Partial<DeliverableFields>)=>request<{revision:number}>(owner(pid,id),json('PATCH',{...fields,expected_revision:revision})),
  workStatus:(pid:string,id:string,revision:number,status:string)=>request<{revision:number}>(`/api/v1/projects/${part(pid)}/deliverables/${part(id)}`,json('PATCH',{status,expected_revision:revision})),
  checklist:(pid:string,id:string,options:ListOptions={})=>request<RevisionPage<CheckItem>>(owner(pid,id)+'/checklist'+query(options),{signal:options.signal}),
  patchCheck:(pid:string,id:string,checkId:string,revision:number,fields:Partial<Pick<CheckItem,'label'|'completed'|'active'|'comment'|'proof'>>)=>request<{revision:number}>(owner(pid,id)+`/checklist/${part(checkId)}`,json('PATCH',{...fields,expected_revision:revision})),
  createCheck:(pid:string,id:string,revision:number,fields:Pick<CheckItem,'code'|'label'|'is_gate'|'transverse'|'contributes'|'milestone_id'>)=>request<{revision:number}>(owner(pid,id)+'/checklist',json('POST',{...fields,expected_revision:revision})),
  versions:(pid:string,id:string,options:{offset?:number;limit?:number;signal?:AbortSignal}={})=>request<RevisionPage<FileVersion>>(owner(pid,id)+'/versions'+query(options),{signal:options.signal}),
  version:(pid:string,id:string,versionId:string,signal?:AbortSignal)=>request<VersionDetail>(owner(pid,id)+`/versions/${part(versionId)}`,{signal}),
  sourceLinks:(pid:string,signal?:AbortSignal)=>request<NetworkLink[]>(`/api/v1/projects/${part(pid)}/network-links`,{signal}),
  sourceDeliveries:(pid:string,signal?:AbortSignal)=>request<Delivery[]>(`/api/v1/projects/${part(pid)}/cdc/deliveries`,{signal}),
  patchVersion:(pid:string,id:string,versionId:string,revision:number,fields:{reference?:string;comment?:string})=>request<{revision:number}>(owner(pid,id)+`/versions/${part(versionId)}`,json('PATCH',{...fields,expected_revision:revision})),
  upload:(pid:string,id:string,revision:number,file:File,reference:string,comment:string)=>{const body=new FormData();body.set('expected_revision',String(revision));body.set('file',file);body.set('reference',reference);body.set('comment',comment);return request<{revision:number}>(owner(pid,id)+'/versions/upload',{method:'POST',body});},
  network:(pid:string,id:string,revision:number,fields:{reference:string;comment:string;link_id:string;relative_path:string})=>request<{revision:number}>(owner(pid,id)+'/versions/network',json('POST',{...fields,expected_revision:revision})),
  cdc:(pid:string,id:string,revision:number,fields:{reference:string;comment:string;source_delivery_id:string})=>request<{revision:number}>(owner(pid,id)+'/versions/cdc',json('POST',{...fields,expected_revision:revision})),
  transition:(pid:string,id:string,revision:number,status:DocumentStatus,versionId:string,comment:string)=>request<{revision:number}>(owner(pid,id)+'/transition',json('POST',{expected_revision:revision,status,version_id:versionId,comment})),
  history:(pid:string,id:string,options:{offset?:number;limit?:number;signal?:AbortSignal}={})=>request<RevisionPage<DeliverableEvent>>(owner(pid,id)+'/history'+query(options),{signal:options.signal}),
  event:(pid:string,id:string,eventId:string,signal?:AbortSignal)=>request<EventDetail>(owner(pid,id)+`/history/${part(eventId)}`,{signal}),
  download:async(pid:string,id:string,versionId:string,kind:'file'|'manifest',signal?:AbortSignal)=>withActivity('Téléchargement du livrable…',async()=>{
    const controller=new AbortController();const abort=()=>controller.abort();signal?.addEventListener('abort',abort,{once:true});if(signal?.aborted)abort();
    const timeout=window.setTimeout(abort,60000);
    try {const response=await agentFetch(owner(pid,id)+`/versions/${part(versionId)}/${kind}`,{credentials:'same-origin',signal:controller.signal});
      if(!response.ok){let detail:unknown;try{detail=(await response.json()).detail;}catch{/* Non-JSON proxy/server error. */}
        throw new Error(typeof detail==='string'?detail:detail&&typeof detail==='object'&&'message' in detail?String(detail.message):`Téléchargement indisponible (${response.status})`);}
      return await response.blob();
    }finally{window.clearTimeout(timeout);signal?.removeEventListener('abort',abort);}
  }),
};
