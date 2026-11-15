import { request } from './http';
export type Proof={knowledge_id:string;quote:string;reason?:string;sources:string[]};
export type KnowledgeFinding={id:string;human_id:string|null;title:string;kind:string;state:string;reason:string;proofs:Proof[]};
export type KnowledgeAnalysis={enabled:boolean;status:string;error:string|null;cursor:number;total_batches:number;next_due:string|null;retry_after:string|null;interval_hours:number;stale:boolean;
  activity:{active_calls:number;waiting_calls:number;background_active:boolean};
  report:{completed_at?:string;knowledge_count?:number;model?:string;counts?:Record<string,number>;dates_total?:number;highlights_total?:number;dates?:Array<Proof&{title:string;date_type:string;date:string}>;highlights?:Array<Proof&{reason:string}>};
  items:KnowledgeFinding[];total:number;offset:number;limit:number};
export const projectKnowledgeApi={read:(projectId:string,offset=0,signal?:AbortSignal,quiet=false)=>request<KnowledgeAnalysis>(`/api/v1/projects/${encodeURIComponent(projectId)}/knowledge-analysis?offset=${offset}&limit=20`,{signal,activity:quiet?false:undefined})};
