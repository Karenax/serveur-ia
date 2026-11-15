import { request } from './http';
import type { Milestone } from './milestones';
import type { Page, ProjectPerson } from './projectIdentity';

export type TaskStatus='todo'|'assigned'|'in_progress'|'blocked'|'done'|'cancelled';
export type Priority='low'|'normal'|'high'|'urgent';
export type WorkflowStatus='pending'|'open'|'validated'|'blocked'|'skipped';
export type PlanningMilestone=Milestone & {code:string|null;order:number;workflow_status:WorkflowStatus;comment:string;active:boolean};
export type PlanningTask={id:string;title:string;status:TaskStatus;due_date:string;parent_id:string|null;milestone_id:string|null;
  responsible_id:string|null;template_id:string|null;template_key:string|null;priority:Priority;start_date:string;end_date:string;
  planned_hours:number;design:boolean;manufacturing:boolean;comment:string;active:boolean;
  parent_title?:string|null;milestone_title?:string|null;responsible_name?:string|null};
export type PlanningInfo={project_id:string;revision:number;can_edit:boolean;excluded_dates:string[];active_template_version_id:string|null;
  task_statuses:TaskStatus[];workflow:{code:string;title:string}[]};
export type ItemPage<T>=Page<T>&{revision:number};
export type ItemDetail<T>={item:T;revision:number;can_edit:boolean;parent?:{id:string;title:string}|null;
  milestone?:{id:string;title:string}|null;responsible?:ProjectPerson|null;children_total?:number};
export type TaskInput={title?:string;status?:TaskStatus;parent_task_id?:string|null;milestone_id?:string|null;responsible_id?:string|null;
  priority?:Priority;start_date?:string;end_date?:string;planned_hours?:number;design?:boolean;manufacturing?:boolean;comment?:string;active?:boolean};
export type MilestoneInput={title?:string;code?:string|null;position?:number|null;workflow_status?:WorkflowStatus;comment?:string;active?:boolean;
  contractual_date?:string;forecast_date?:string;actual_date?:string};
export type BaselineKind='initial'|'contractual'|'review'|'amendment';
export type Baseline={id:string;kind:BaselineKind;label:string;capture_label:string;comment:string;active:boolean;metadata_revision:number;revision:number;sha256:string;actor_id:string;created_at:string};
export type BaselineMetadata={label:string;comment:string;active:boolean};
export type BaselineDetail={baseline:Baseline;revision:number;can_edit:boolean};
export type PlanningChange={id:string;revision:number;actor_id:string;action:string;created_at:string};
export type PlanningDiff={revision?:number;baseline_revision?:number;project_comparison_available?:boolean;project_budget_hours_delta?:number|null;changes:{kind:'tasks'|'milestones'|'project';id:string;title?:string;field:string|null;severity:'high'|'normal';before:unknown;after:unknown}[];
  planned_hours_delta:number;calendar?:{before:string[];after:string[]};template_version_id?:{before:string|null;after:string|null}};
export type TemplateDefinition={name:string;milestones:{code:string;title:string;offset_workdays:number|null}[];
  tasks:{key:string;title:string;parent_key:string|null;milestone_code:string|null;start_offset_workdays:number|null;end_offset_workdays:number|null;
  planned_hours:number;priority:Priority;design:boolean;manufacturing:boolean}[]};
export type TemplateVersion={id:string;number:number;sha256?:string;actor_id?:string;created_at?:string};
export type TemplateVersionDetail=TemplateVersion&{definition:TemplateDefinition};
export type PlanningTemplate={id:string;code:string;name:string;typology_id:string|null;active:boolean;revision:number;latest_version:TemplateVersion|null};
export type TemplateDetail=PlanningTemplate&{can_manage:boolean};
export type TemplateInputs={expected_revision:number;start_date:string;excluded_dates:string[];milestone_mapping:Record<string,string>;
  forecast_policy:'preserve'|'fill_empty'|'replace';update_tasks:boolean};
export type TemplatePreview={project_id:string;revision:number;version_id:string;preview_sha256:string;milestone_map:Record<string,string>;
  task_map:Record<string,string>;milestones:PlanningMilestone[];tasks:PlanningTask[];changes:PlanningDiff;inputs:TemplateInputs};
export type PageOptions={search?:string;offset?:number;limit?:number;include_inactive?:boolean;signal?:AbortSignal};
const root=(id:string)=>`/api/v1/projects/${encodeURIComponent(id)}/planning`;
const catalog='/api/v1/planning-templates';
function query(options:PageOptions={}) {return new URLSearchParams({search:options.search||'',offset:String(options.offset||0),limit:String(options.limit||25),include_inactive:String(!!options.include_inactive)});}
function command<T>(url:string,method:string,body:unknown) {return request<T>(url,{method,body:JSON.stringify(body)});}
export const planningApi={
  info:(id:string,signal?:AbortSignal)=>request<PlanningInfo>(`${root(id)}/state`,{signal}),
  tasks:(id:string,options:PageOptions={})=>request<ItemPage<PlanningTask>>(`${root(id)}/items/tasks?${query(options)}`,{signal:options.signal}),
  milestones:(id:string,options:PageOptions={})=>request<ItemPage<PlanningMilestone>>(`${root(id)}/items/milestones?${query(options)}`,{signal:options.signal}),
  task:(id:string,taskId:string,signal?:AbortSignal)=>request<ItemDetail<PlanningTask>>(`${root(id)}/items/tasks/${encodeURIComponent(taskId)}`,{signal}),
  milestone:(id:string,milestoneId:string,signal?:AbortSignal)=>request<ItemDetail<PlanningMilestone>>(`${root(id)}/items/milestones/${encodeURIComponent(milestoneId)}`,{signal}),
  patchTask:(id:string,taskId:string,revision:number,body:TaskInput)=>command<{revision:number;task:PlanningTask}>(`${root(id)}/tasks/${encodeURIComponent(taskId)}`,'PATCH',{...body,expected_revision:revision}),
  createTask:(id:string,revision:number,body:TaskInput&{title:string})=>command<{revision:number;task:PlanningTask}>(`${root(id)}/tasks`,'POST',{...body,expected_revision:revision}),
  patchMilestone:(id:string,milestoneId:string,revision:number,body:MilestoneInput)=>command<{revision:number;milestone:PlanningMilestone}>(`${root(id)}/milestones/${encodeURIComponent(milestoneId)}`,'PATCH',{...body,expected_revision:revision}),
  createMilestone:(id:string,revision:number,title:string)=>command(`/api/v1/projects/${encodeURIComponent(id)}/milestones`,'POST',{title,expected_revision:revision}),
  baselines:(id:string,offset=0,signal?:AbortSignal,includeInactive=false)=>request<Page<Baseline>>(`${root(id)}/baselines?offset=${offset}&limit=25&include_inactive=${includeInactive}`,{signal}),
  createBaseline:(id:string,revision:number,kind:BaselineKind,label:string)=>command<Pick<Baseline,'id'|'kind'|'label'|'revision'|'sha256'>>(`${root(id)}/baselines`,'POST',{kind,label,expected_revision:revision}),
  baseline:(id:string,baselineId:string,signal?:AbortSignal)=>request<BaselineDetail>(`${root(id)}/baselines/${encodeURIComponent(baselineId)}`,{signal}),
  patchBaseline:(id:string,baselineId:string,revision:number,body:Partial<BaselineMetadata>)=>command<{baseline:Baseline;revision:number}>(`${root(id)}/baselines/${encodeURIComponent(baselineId)}`,'PATCH',{...body,expected_revision:revision}),
  compare:(id:string,baselineId:string,signal?:AbortSignal)=>request<PlanningDiff>(`${root(id)}/baselines/${encodeURIComponent(baselineId)}/compare`,{signal}),
  history:(id:string,offset=0,signal?:AbortSignal)=>request<Page<PlanningChange>>(`${root(id)}/history?offset=${offset}&limit=25`,{signal}),
  historyDetail:(id:string,changeId:string,signal?:AbortSignal)=>request<{id:string;revision:number;previous:Record<string,unknown>;value:Record<string,unknown>}>(`${root(id)}/history/${encodeURIComponent(changeId)}`,{signal}),
  templates:(options:PageOptions={})=>request<Page<PlanningTemplate>&{can_manage:boolean}>(`${catalog}?${query(options)}`,{signal:options.signal}),
  template:(templateId:string,signal?:AbortSignal)=>request<TemplateDetail>(`${catalog}/${encodeURIComponent(templateId)}`,{signal}),
  standard:()=>request<TemplateDefinition>(`${catalog}/standard-definition`),
  createTemplate:(body:{code:string;name:string;typology_id:string|null;definition:TemplateDefinition})=>command<Omit<PlanningTemplate,'latest_version'>&{version:TemplateVersion}>(catalog,'POST',body),
  patchTemplate:(row:PlanningTemplate,body:{name?:string;typology_id?:string|null;active?:boolean})=>command<PlanningTemplate>(`${catalog}/${encodeURIComponent(row.id)}`,'PATCH',{...body,expected_revision:row.revision}),
  versions:(templateId:string,offset=0,signal?:AbortSignal)=>request<Page<TemplateVersion>>(`${catalog}/${encodeURIComponent(templateId)}/versions?offset=${offset}&limit=25`,{signal}),
  version:(templateId:string,versionId:string,signal?:AbortSignal)=>request<TemplateVersionDetail>(`${catalog}/${encodeURIComponent(templateId)}/versions/${encodeURIComponent(versionId)}`,{signal}),
  publish:(row:PlanningTemplate,definition:TemplateDefinition)=>command<TemplateVersion>(`${catalog}/${encodeURIComponent(row.id)}/versions`,'POST',{definition,expected_revision:row.revision}),
  mappingProposals:(id:string,signal?:AbortSignal)=>request<{revision:number;items:{milestone_id:string;title:string;suggested_code:string|null;human_confirmation_required:boolean;reason:string}[]}>(`${root(id)}/mapping-proposals`,{signal}),
  preview:(id:string,versionId:string,body:TemplateInputs)=>command<TemplatePreview>(`${root(id)}/templates/${encodeURIComponent(versionId)}/preview`,'POST',body),
  apply:(id:string,preview:TemplatePreview)=>command<{revision:number}>(`${root(id)}/templates/${encodeURIComponent(preview.version_id)}/apply`,'POST',{...preview.inputs,expected_preview_sha256:preview.preview_sha256}),
};
export const taskStatusLabels:Record<TaskStatus,string>={todo:'À faire',assigned:'Affectée',in_progress:'En cours',blocked:'Bloquée',done:'Terminée',cancelled:'Annulée'};
export const priorityLabels:Record<Priority,string>={low:'Basse',normal:'Normale',high:'Haute',urgent:'Urgente'};
export const workflowLabels:Record<WorkflowStatus,string>={pending:'En attente',open:'Ouvert',validated:'Validé',blocked:'Bloqué',skipped:'Sauté'};
