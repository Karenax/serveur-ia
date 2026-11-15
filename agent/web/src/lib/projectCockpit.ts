import { request } from './http';
import type { ItemPage, PlanningMilestone, PlanningTask } from './projectPlanning';
import type { DocumentStatus } from './projectDeliverables';

export type CockpitMilestone = PlanningMilestone & {past:boolean;task_count:number;deliverable_count:number};
export type CockpitDocument = {id:string;title:string;status:string;document_status:DocumentStatus;milestone_ids:string[]};
export type CockpitAlert = {kind:string;entity_kind:'task'|'milestone'|'deliverable'|'candidate'|'cdc';id:string;title:string;severity:string;due_date:string};
export type CockpitStructure = ItemPage<CockpitMilestone> & {
  project:{id:string;code:string;title:string;status:string;client_name:string;start_date:string;planned_end_date:string};can_edit:boolean;
  current_milestone:PlanningMilestone|null;tasks:{total:number;done:number;active:number;open:number;blocked:number;overdue:number};progress:number;
  hours:{initial_hours:number;consumed_hours:number;raf:number;remaining_mode:string;overrun_hours:number};
  deliverables_total:number;milestones_total:number;unassigned_tasks:number;unassigned_deliverables:number;
};
export type CockpitOptions={search?:string;show_past?:boolean;milestone_id?:string|null;unassigned?:boolean;offset?:number;limit?:number;signal?:AbortSignal};
const root=(pid:string)=>`/api/v1/projects/${encodeURIComponent(pid)}/cockpit`;
function query(options:CockpitOptions) {
  const params=new URLSearchParams();
  for(const [key,value] of Object.entries(options))if(key!=='signal'&&value!=null&&value!=='')params.set(key,String(value));
  return params.size?`?${params}`:'';
}
export const cockpitApi={
  structure:(pid:string,options:CockpitOptions={})=>request<CockpitStructure>(root(pid)+query(options),{signal:options.signal}),
  tasks:(pid:string,options:CockpitOptions={})=>request<ItemPage<PlanningTask>>(root(pid)+'/items/tasks'+query(options),{signal:options.signal}),
  documents:(pid:string,options:CockpitOptions={})=>request<ItemPage<CockpitDocument>>(root(pid)+'/items/deliverables'+query(options),{signal:options.signal}),
  alerts:(pid:string,options:CockpitOptions={})=>request<ItemPage<CockpitAlert>>(root(pid)+'/alerts'+query(options),{signal:options.signal}),
};
