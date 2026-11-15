import { request } from "./http";

export type WorkspacePage<T> = {items: T[]; total: number};
export type WorkspaceFilter = {project_id?: string; offset?: number; limit?: number; q?: string; status?: string; review_only?: boolean};
export type WorkspaceCitation = {
  source_id: string; source_type?: string; title?: string; author?: string; excerpt?: string;
  locator?: Record<string, unknown>; source_url?: string; audio_url?: string | null;
  recording_id?: string | null; erp_project_id?: string | null;
};
export type WorkspaceMeeting = {
  id: string; meeting_id: string | null; recording_id: string | null; session_id?: string | null;
  project_id: string; brain_project_id: string | null; project_code: string; project_title: string;
  title: string; date: string; participants: string; decisions: string;
  actions: {id: string; title: string; owner: string; due_date: string; task_id: string | null}[];
  stage: string; status: string; created_at: string;
  recording: {id: string; job_status: string; stage: string; progress: number; reviewed_revision: number; revision: number} | null;
};
export type WorkspaceJob = {
  id: string; engine: "cdc" | "audio" | "triage" | "mail" | "milestones"; kind: string; title: string;
  project_id: string | null; brain_project_id: string | null; project_code: string; project_title: string;
  source_id: string | null; status: string; stage: string; progress: number; processed: number; total: number;
  unit: "batches" | "seconds" | "mails" | "steps" | "passages"; can_cancel: boolean; can_retry: boolean;
  cancel_url: string | null; retry_url: string | null; error: string | null; created_at: string; updated_at: string;
};
export type WorkspaceKnowledge = {
  id: string; project_id: string | null; brain_project_id: string | null; project_code: string; project_name: string;
  erp_projects: {id: string; code: string; title: string}[];
  kind: string; subject: string; value: string; status: string; citations: WorkspaceCitation[];
  validated_at?: string | null; version?: number; confidence?: number | null;
  validation_mode?: 'default' | 'human';
  context?: {source_state: string; needs_review: boolean; review_reasons: string[]; review_messages: string[]; can_confirm: boolean};
  reason?: string | null; source_id?: string | null; operation?: string;
};
export type WorkspaceSource = {
  body_html?:string|null; inline_images?:Record<string,string>;
  id: string; type: string; status: string; project_id: string | null; author: string;
  received_at?: string | null; metadata: {subject?: string; filename?: string;origin_kind?:string;erp_project_id?:string;note_id?:string;note_version_id?:string};
  artifacts: {id: string; kind: string; text: string}[];
};
export type DurableTriageJob = {
  id: string; status: "queued" | "running" | "completed" | "failed" | "cancelled" | "interrupted";
  force: boolean; processed: number; total: number; progress: number; cancel_requested: boolean;
  result: {triaged?: number; skipped?: number; divers?: number; auto_classified?: number; errors?: {source_id: string; error: string}[]};
  error: string | null; can_cancel: boolean; can_retry: boolean; created_at: string; updated_at: string;
};
export type ProposalDecision = {actor?: string; comment?: string; subject?: string; value?: string; supersedes_id?: string};

function pageUrl(path: string, filters: WorkspaceFilter = {}) {
  const search = new URLSearchParams();
  Object.entries({...filters, limit: filters.limit ?? 25}).forEach(([key, value]) => {
    if (value !== undefined && value !== "") search.set(key, String(value));
  });
  return `/api/v1/workspace/${path}?${search}`;
}

export const workspaceApi = {
  meetings: (filters: WorkspaceFilter = {}, signal?: AbortSignal,quiet=false) => request<WorkspacePage<WorkspaceMeeting>>(pageUrl("meetings", filters), {signal,activity:quiet?false:undefined}),
  jobs: (filters: WorkspaceFilter = {}, signal?: AbortSignal,quiet=false) => request<WorkspacePage<WorkspaceJob>>(pageUrl("jobs", filters), {signal,activity:quiet?false:undefined}),
  proposals: (filters: WorkspaceFilter = {}, signal?: AbortSignal) => request<WorkspacePage<WorkspaceKnowledge>>(pageUrl("proposals", filters), {signal}),
  knowledge: (filters: WorkspaceFilter = {}, signal?: AbortSignal) => request<WorkspacePage<WorkspaceKnowledge>>(pageUrl("knowledge", filters), {signal}),
  changeKnowledge: (projectId: string, id: string, action: 'invalidate' | 'restore' | 'confirm') => request<{id:string;status:string}>(
    `/v1/projects/${encodeURIComponent(projectId)}/knowledge/${encodeURIComponent(id)}/${action}`, {method:'POST',body:JSON.stringify({actor:'validator'})}),
  source: (id: string, signal?: AbortSignal) => request<WorkspaceSource>(`/v1/sources/${encodeURIComponent(id)}`, {signal}),
  decide: (id: string, action: "accept" | "reject" | "edit-and-accept", body: ProposalDecision = {}) => request<{status: string}>(
    `/v1/proposals/${encodeURIComponent(id)}/${action}`, {method: "POST", body: JSON.stringify({actor: "validator", ...body})}),
  jobAction: (url: string) => {
    if (!url.startsWith("/api/v1/") || url.startsWith("//")) throw new Error("Adresse de traitement invalide");
    return request<unknown>(url, {method: "POST"});
  },
  triageJobs: (signal?: AbortSignal) => request<WorkspacePage<DurableTriageJob>>("/api/v1/workspace/triage-jobs?limit=1&offset=0", {signal}),
  latestTriage: (signal?: AbortSignal,quiet=false) => request<{job: DurableTriageJob | null}>("/api/v1/workspace/triage-jobs/latest", {signal,activity:quiet?false:undefined}),
  triageJob: (id: string, signal?: AbortSignal,quiet=false) => request<DurableTriageJob>(`/api/v1/workspace/triage-jobs/${encodeURIComponent(id)}`, {signal,activity:quiet?false:undefined}),
  startTriage: (force = false) => request<DurableTriageJob>("/api/v1/workspace/triage-jobs", {method: "POST", body: JSON.stringify({force})}),
  cancelTriage: (id: string) => request<DurableTriageJob>(`/api/v1/workspace/triage-jobs/${encodeURIComponent(id)}/cancel`, {method: "POST"}),
};
