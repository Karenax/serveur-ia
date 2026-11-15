import { request } from "./http";

export type ReferenceKind = "client" | "agency" | "business_unit" | "family" | "typology";
export const referenceKinds: {kind:ReferenceKind; label:string; plural:string; field:ReferenceField}[] = [
  {kind:"client",label:"Client",plural:"Clients",field:"client_id"},
  {kind:"agency",label:"Agence",plural:"Agences",field:"agency_id"},
  {kind:"business_unit",label:"Business unit",plural:"Business units",field:"business_unit_id"},
  {kind:"family",label:"Famille",plural:"Familles",field:"family_id"},
  {kind:"typology",label:"Typologie",plural:"Typologies",field:"typology_id"},
];
export type ReferenceField = "client_id" | "agency_id" | "business_unit_id" | "family_id" | "typology_id";
export type ProjectReference = {id:string; kind:ReferenceKind; code:string; label:string; active:boolean; revision:number};
export type PersonInput = {first_name:string; last_name:string; email:string; trigram:string; function:string; service:string; phone:string; agency_id:string|null};
export type ProjectPerson = PersonInput & {id:string; active:boolean; revision:number};
export type MemberRole = "responsable_projet" | "pilote_etude" | "be_3d" | "be_2d" | "verificateur_be" | "qualite" | "calcul" | "charge_fabrication" | "collaborateur_projet" | "lecteur_projet";
export type ProjectMember = {id:string; project_id:string; person_id:string; person:ProjectPerson; role:MemberRole; start_date:string; end_date:string; active:boolean; archived_at:string|null};
export type IdentityFields = Record<ReferenceField,string|null> & {
  responsible_id:string|null; description:string; client_reference:string; client_site:string; client_contact:string;
  equipment_number:string; quantity:number|null; start_date:string; planned_end_date:string; standby:boolean;
};
export type ProjectIdentity = IdentityFields & {
  project_id:string; code:string; title:string; status:string; legacy_client_name:string; offer_number:string;
  revision:number; actual_closure_date:string; references:Record<string,ProjectReference>; members:ProjectMember[];
  responsible:ProjectPerson|null; can_edit:boolean; roles:{code:MemberRole;label:string}[];
};
export type IdentityChange = {id:string; revision:number; actor_id:string; action:string; previous:Record<string,unknown>; value:Record<string,unknown>; created_at:string};
export type Page<T> = {items:T[]; total:number; offset:number; limit:number};
export type Operator = {id:string; role:"owner"|"editor"|"reader"; can_edit:boolean; can_administer:boolean; project_ids:string[]|null};
type PageOptions = {search?:string; offset?:number; include_inactive?:boolean; signal?:AbortSignal};
function pageQuery(options:PageOptions) {
  return new URLSearchParams({search:options.search||"",offset:String(options.offset||0),limit:"50",include_inactive:String(!!options.include_inactive)});
}
function command<T>(url:string, method:string, data:unknown) {return request<T>(url,{method,body:JSON.stringify(data)});}
const root="/api/v1";
const project=(id:string)=>`${root}/projects/${encodeURIComponent(id)}`;
export const identityApi = {
  session:()=>request<{operator:Operator}>(`${root}/session`),
  read:(id:string,signal?:AbortSignal)=>request<ProjectIdentity>(`${project(id)}/identity`,{signal}),
  patch:(id:string,revision:number,data:Partial<IdentityFields>)=>command<ProjectIdentity>(`${project(id)}/identity`,"PATCH",{...data,expected_revision:revision}),
  history:(id:string,offset=0,signal?:AbortSignal)=>request<Page<IdentityChange>>(`${project(id)}/identity/history?offset=${offset}&limit=50`,{signal}),
  references:(kind:ReferenceKind,options:PageOptions={})=>request<Page<ProjectReference>>(`${root}/project-references?${pageQuery(options)}&kind=${kind}`,{signal:options.signal}),
  people:(options:PageOptions={})=>request<Page<ProjectPerson>>(`${root}/project-people?${pageQuery(options)}`,{signal:options.signal}),
  createReference:(kind:ReferenceKind,code:string,label:string)=>command<ProjectReference>(`${root}/project-references`,"POST",{kind,code,label}),
  patchReference:(ref:ProjectReference,data:{label?:string;active?:boolean})=>command<ProjectReference>(`${root}/project-references/${encodeURIComponent(ref.id)}`,"PATCH",{...data,expected_revision:ref.revision}),
  createPerson:(data:PersonInput)=>command<ProjectPerson>(`${root}/project-people`,"POST",data),
  patchPerson:(person:ProjectPerson,data:Partial<PersonInput>&{active?:boolean})=>command<ProjectPerson>(`${root}/project-people/${encodeURIComponent(person.id)}`,"PATCH",{...data,expected_revision:person.revision}),
  addMember:(id:string,revision:number,data:{person_id:string;role:MemberRole;start_date:string;end_date:string})=>command<ProjectIdentity>(`${project(id)}/members`,"POST",{...data,expected_revision:revision}),
  patchMember:(id:string,revision:number,memberId:string,data:{role:MemberRole;start_date:string;end_date:string})=>command<ProjectIdentity>(`${project(id)}/members/${encodeURIComponent(memberId)}`,"PATCH",{...data,expected_revision:revision}),
  archiveMember:(id:string,revision:number,memberId:string)=>command<ProjectIdentity>(`${project(id)}/members/${encodeURIComponent(memberId)}/archive`,"POST",{expected_revision:revision}),
};
export function personName(person:ProjectPerson) {return `${person.first_name} ${person.last_name}${person.trigram?` · ${person.trigram}`:""}`;}
