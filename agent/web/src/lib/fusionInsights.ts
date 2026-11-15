import { request } from './http';
import type { SessionCapabilities } from './meetingSessions';
export type FusionStats={sources:{total:number;by_type:Record<string,number>;extracted:number;indexed:number|null;current:number};
  sessions:{total:number;by_state:Record<string,number>;duration_seconds:number;audio_bytes:number;chunks_by_track?:Record<string,number>};
  transcription?:{by_status:Record<string,number>;pending_chunks:number;pending_audio_seconds:number;oldest_pending_seconds:number|null};
  assistant:{answers:number;stale:number;enhancements:number;p50_seconds:number|null;p95_seconds:number|null;tokens:number|null;token_complete_answers?:number;token_partial_answers?:number;token_unmeasured_answers?:number;token_total_answers?:number;useful_answers?:number|null;evaluated_answers?:number;unhelpful_answers?:number;measured_latency_samples?:number};
  engines:{speech:Record<string,unknown>;generation:GenerationReadiness};
  index:{text_passages:number|null;profiles:unknown[]|number;size_bytes:number};formulas:Record<string,string>};
export type FusionSettings={enabled:boolean;live_transcription_enabled?:boolean;live_speech_device?:'cpu'|'cuda';speech_acceleration?:{selected:'cpu'|'cuda'|null;cuda_available:boolean;environment_override:boolean;detail:string;selection_starts_model:false};proactive_enabled:boolean;auto_enhancement_enabled?:boolean;mode:'network'|'local';onboarding_complete:boolean;capabilities:SessionCapabilities};
export type GenerationReadiness={placement:string;configured:boolean;model?:string;provider?:string;detail?:string;
  inventory?:{reachable:boolean;installed:boolean|null;loaded:boolean|null;announced?:boolean;checked_at:string;detail:string}|null;
  test?:{ok:boolean;reply_received:boolean;checked_at:string;detail:string;elapsed_seconds:number}|null};
export type FusionReadinessState={mode:'network'|'local';capture:{durable:boolean;installed:boolean|null;ready:boolean|null;physical_test_passed:boolean|null;requires_explicit_start:true};
  transcription:{batch:Record<string,unknown>;direct:Record<string,unknown>};embeddings:{network:{model?:string;detail:string}};
  generation:GenerationReadiness;resources:{available_ram_bytes:number|null;total_ram_bytes:number|null;free_disk_bytes:number|null};offline:{qualified:boolean;detail:string}};
export const fusionInsights={
  stats:(projectId?:string,signal?:AbortSignal)=>request<FusionStats>(`/api/v1/workspace/fusion-stats${projectId?`?project_id=${encodeURIComponent(projectId)}`:''}`,{signal}),
  settings:(signal?:AbortSignal)=>request<FusionSettings>('/api/v1/workspace/fusion-settings',{signal}),
  readiness:(signal?:AbortSignal)=>request<FusionReadinessState>('/api/v1/workspace/fusion-settings/readiness',{signal}),
  probeReadiness:()=>request<FusionReadinessState>('/api/v1/workspace/fusion-settings/readiness/probe',{method:'POST',activity:'Vérification des moteurs'}),
  testGeneration:()=>request<FusionReadinessState>('/api/v1/workspace/fusion-settings/readiness/generation-test',{method:'POST',activity:'Test de réponse du modèle configuré'}),
  save:(settings:Pick<FusionSettings,'enabled'|'live_transcription_enabled'|'live_speech_device'|'proactive_enabled'|'auto_enhancement_enabled'|'mode'|'onboarding_complete'>)=>request<FusionSettings>('/api/v1/workspace/fusion-settings',{method:'PUT',body:JSON.stringify({...settings,live_transcription_enabled:settings.live_transcription_enabled??false})}),
};
