import { request } from "./http";
export type PortfolioRow = {
  id: string; code: string; title: string; status: string; client_name: string;
  jalon_en_cours: string; jalon_echeance: string; avancement: number;
  raf: number; taches: string; en_retard: number;
  corrections: number; correction_label: string;
  initial_hours: number; consumed_hours: number; remaining_mode: "reestimated" | "budget_balance";
  overrun_hours: number; unconfirmed: number; open_points: number;
  brain_project_id: string | null; brain_code: string | null;
};

export type CdcSource = {
  id: string; ref: string; filename: string; revision: string;
  status: string; pages: number; size: string;
  extracted_pages?: number; analyzable?: boolean; hint?: string;
};

export type NetworkLink = {
  id: string; code: string; libelle: string; chemin: string | null;
  ordre: number; required: boolean;
};

export type MeetingAction = {
  id: string; title: string; owner: string; due_date: string; task_id: string | null;
};

export type SearchHit = {
  type: string; project_id: string; tab: string; label: string;
};

export type Meeting = {
  id: string; date: string; title: string; participants: string;
  decisions: string; actions: MeetingAction[]; open_actions: number;
};

export type BrainKnowledge = {
  id: string; kind: string; subject: string; value: string;
  status?:string; validation_mode?:'default'|'human';
  validated_at?:string|null; version?:number;
  citations?:import('./workspaceApi').WorkspaceCitation[];
};

export type BrainAction = { id: string; subject: string; value: string };

export type BrainLinkState = {
  linked: boolean; minipilot_code: string;
  brain_project_id?: string; brain_code?: string;
  memory?: { evidence_projections: number; truth_projections: number; truth_items?: number; failed?: number; pending?: number; obsolete?: number; health?: {status: string; engine: string} };
  memory_error?: string; pending?: { source_id: string }[];
  suggested?: { id: string; code: string; name: string } | null;
  brain_projects?: { id: string; code: string; name: string }[];
  brain_error?: string;
};

export type CdcItem = {
  id: string; kind: string; title: string; source_quote: string;
  physical_page: number; modality: string; priority: string; confidence: number;
  estimated_hours: number;
  human_id?: string | null; normalized_wording?: string;
  knowledge_status?: string; criterion?: string | null; unit?: string | null;
  acceptance_criterion?: string | null; responsible_party?: string | null;
  evidence?: { id?: string; source_id?: string; page: number; locator: string; quote: string; confidence?: number | null }[];
};

export type CdcReview = {
  total: number; reviewed: number; remaining: number;
  by_status: Record<string, number>; by_kind: Record<string, number>;
};

export type ProjectDetail = { id: string; code: string; title: string; status: string; remaining_hours: number | null; planning_revision?: number;
  tasks: {id: string; title: string; status: string; due_date: string}[];
  deliverables: {id: string; title: string; status: string}[];
  milestones: import("./milestones").Milestone[] };
export type TriageStats = {pending_sources: number; new_sources: number; queued: number; divers_project_id: string; divers_count: number};
export type TriageResult = {scanned: number; triaged: number; divers: number; skipped: number; auto_classified?: number;
  errors: {source_id: string; error: string}[]; force: boolean};
export type DiscardSuggestion = {probability: number | null; discarded_samples: number; retained_samples: number; reason: string; estimated: boolean};
export type PendingMail = {discard_suggestion?: DiscardSuggestion; proposal_id: string; source_id: string; sender: string; subject: string; received_at: string | null;
  excerpt: string; target_project_id: string | null; target_code: string | null; target_name: string | null; confidence: number; reason: string};
export type SourceMail = {source_id: string; author: string; project_id: string | null; received_at?: string | null;
  excerpt?: string; metadata: {subject?: string; attachments?: {filename: string; mime?: string}[]}};
export type MailPage<T> = {rows: T[]; total: number; offset: number; limit: number; has_next: boolean};
export type CdcJob = {id: string; project_id: string; created_at: string; source_id: string; status: "queued" | "running" | "completed" | "failed" | "cancelled" | "interrupted";
  completed_batches: number; total_batches: number; progress: number; cancel_requested: boolean; error: string | null;
  result: {created?: number; returned?: number; rejected?: number} | null; updated_at: string};
export type Delivery = {id: string; version: number; draft: boolean; file: string; sha256: string; created_at: string};
export type Actions = {actions: {project_id: string; project_code: string; kind: string; title: string; count: number; due_date: string; tab: string}[];
  pending_mails: number; total: number; horizon_days: number};
export type BackupState = {directory?: string; status: string; created_at?: string; verified_at?: string};
export type OperationsState = {backup: BackupState | null; migration_backups: {count: number; bytes: number}; disk_warning?: boolean;
  disk_free_bytes: number; disk_low: boolean; databases: {brain_bytes: number; erp_bytes: number}};
type SageSource = {source: string; folder: string; file_name: string; rows: number};
export type SageStatus = {
  batch: {status: "running" | "success" | "failed"; total_rows: number; error_message: string} | null;
  sources: SageSource[];
};
export type Purchases = {count: number; rows: {supplier: string; label: string; status: string; date: string}[]};
export type Tracking = {total_hours: number; by_person: {person: string; hours: number}[];
  entries: {id?: string; source: string; person: string; date: string; label: string; hours: number}[]};
export type Bom = {count: number; lines: {id: string; reference: string; designation: string; quantity: number; supplier: string; status: string}[]};

const BASE = "/api/v1";

async function req(path: string, init?: RequestInit & {activity?:string|false}, timeoutMs?: number) {
  return request<any>(BASE + path, init, timeoutMs);
}

export const api = {
  session: (signal?:AbortSignal,timeoutMs=0) => request<{operator:{role:string;project_ids:string[]|null}}>('/api/v1/session',{signal},timeoutMs),
  portfolio: (quiet=false) => req("/portfolio",quiet?{activity:false}:undefined) as Promise<PortfolioRow[]>,
  createProject: (code: string, title: string) =>
    req("/projects", { method: "POST", body: JSON.stringify({ code, title }) }),
  scanFolder: (folder: string) =>
    req("/projects/scan", { method: "POST", body: JSON.stringify({ folder }) }),
  importFolder: (folder: string, code?: string, title?: string) =>
    req("/projects/import", { method: "POST", body: JSON.stringify({ folder, code, title }) }),
  patchProject: (id: string, body: object) =>
    req(`/projects/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  detail: (id: string) => req(`/projects/${id}`) as Promise<ProjectDetail>,
  addTask: (id: string, title: string, due_date: string) =>
    req(`/projects/${id}/tasks`, { method: "POST", body: JSON.stringify({ title, due_date }) }),
  cdcItems: (id: string) => req(`/projects/${id}/cdc/items`) as Promise<CdcItem[]>,
  cdcSources: (id: string) => req(`/projects/${id}/cdc/sources`) as Promise<CdcSource[]>,
  networkLinks: (id: string) => req(`/projects/${id}/network-links`) as Promise<NetworkLink[]>,
  saveNetworkLinks: (id: string, liens: { code: string; libelle: string; chemin: string | null }[]) =>
    req(`/projects/${id}/network-links`, { method: "PUT", body: JSON.stringify({ liens }) }),
  openPath: (path: string, project: string) =>
    req("/open-path", { method: "POST", body: JSON.stringify({ path, project }) }),
  addCdcItem: (id: string, body: object) =>
    req(`/projects/${id}/cdc/items`, { method: "POST", body: JSON.stringify(body) }),
  uploadCdc: async (id: string, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<any>(BASE + `/projects/${id}/cdc/sources/upload`, { method: "POST", body: fd });
  },
  transfer: (id: string, draft = false) => req(`/projects/${id}/cdc/transfer?draft=${draft}`, { method: "POST" }),
  analyzeCdc: (id: string, source_id: string) =>
    req(`/projects/${id}/cdc/jobs`, {
      method: "POST", body: JSON.stringify({ source_id, pages_per_batch: 2 }),
    }) as Promise<CdcJob>,
  cdcJobs: (id: string,quiet=false) => req(`/projects/${id}/cdc/jobs`,quiet?{activity:false}:undefined) as Promise<CdcJob[]>,
  cancelCdcJob: (id: string, job: string) => req(`/projects/${id}/cdc/jobs/${job}/cancel`, {method: "POST"}) as Promise<CdcJob>,
  retryCdcJob: (id: string, job: string) => req(`/projects/${id}/cdc/jobs/${job}/retry`, {method: "POST"}) as Promise<CdcJob>,
  deliveries: (id: string) => req(`/projects/${id}/cdc/deliveries`) as Promise<Delivery[]>,
  delivery: (id: string, version: string) => req(`/projects/${id}/cdc/deliveries/${version}`) as Promise<{markdown: string; version: number; snapshot: Record<string, unknown>}>,
  cdcChecks: (id: string) => req(`/projects/${id}/cdc/checks`),
  cdcReview: (id: string) => req(`/projects/${id}/cdc/review`),
  patchCdcItem: (id: string, itemId: string, body: object) =>
    req(`/projects/${id}/cdc/items/${itemId}`, { method: "PATCH", body: JSON.stringify(body) }),
  bulkCdcStatus: (id: string, ids: string[], knowledge_status: string) =>
    req(`/projects/${id}/cdc/items/bulk-status`, {
      method: "POST", body: JSON.stringify({ ids, knowledge_status }),
    }),
  cdcRuns: (id: string) => req(`/projects/${id}/cdc/runs`),
  cdcPages: (id: string, sourceId: string) =>
    req(`/projects/${id}/cdc/sources/${sourceId}/pages`),
  budgetsFromTdao: (id: string) => req(`/projects/${id}/budgets-from-tdao`, { method: "POST" }),
  meetings: (id: string) => req(`/projects/${id}/meetings`) as Promise<Meeting[]>,
  createMeeting: (id: string, body: object) =>
    req(`/projects/${id}/meetings`, { method: "POST", body: JSON.stringify(body) }),
  addAction: (pid: string, mid: string, body: object) =>
    req(`/projects/${pid}/meetings/${mid}/actions`, { method: "POST", body: JSON.stringify(body) }),
  actionToTask: (pid: string, mid: string, aid: string) =>
    req(`/projects/${pid}/meetings/${mid}/actions/${aid}/to-task`, { method: "POST" }),
  exportMeeting: (pid: string, mid: string) =>
    req(`/projects/${pid}/meetings/${mid}/export`),
  aiStatus: () => req("/ai/status"),
  brainStatus: () => req("/brain/status"),
  brainOverview: () => req("/brain/overview"),
  brainProposals: () => req("/brain/proposals"),
  brainScanGlobal: () => req("/brain/scan", { method: "POST" }),
  brainAiSettings: () => req("/brain/ai-settings"),
  saveBrainAiSettings: (body: object) =>
    req("/brain/ai-settings", { method: "PUT", body: JSON.stringify(body) }),
  brainAiTest: () => req("/brain/ai-test", { method: "POST" }),
  brainMailSettings: () => req("/brain/mail-settings"),
  saveBrainMailSettings: (body: object) =>
    req("/brain/mail-settings", { method: "PUT", body: JSON.stringify(body) }),
  brainMemorySettings: () => req("/brain/memory-settings"),
  brainMemoryTest: () => req("/brain/memory-test", { method: "POST" }, 900_000),
  brainChat: (query: string, project_id?: string | null, include_evidence = true) =>
    req("/brain/chat", {
      method: "POST",
      body: JSON.stringify({ query, project_id: project_id ?? null, include_evidence }),
    }, 300_000),
  saveBrainMemorySettings: (body: object) =>
    req("/brain/memory-settings", { method: "PUT", body: JSON.stringify(body) }),
  brainLink: (id: string) => req(`/projects/${id}/brain`) as Promise<BrainLinkState>,
  saveBrainLink: (id: string, brain_project_id: string) =>
    req(`/projects/${id}/brain`, { method: "PUT", body: JSON.stringify({ brain_project_id }) }),
  ensureBrainLink: (id: string) => req(`/projects/${id}/brain/ensure`, {method:"POST"}) as Promise<BrainLinkState>,
  unlinkBrain: (id: string) => req(`/projects/${id}/brain`, { method: "DELETE" }),
  brainKnowledge: (id: string, status = 'validated', offset = 0, limit = 200) =>
    req(`/projects/${id}/brain/knowledge?status=${status}&offset=${offset}&limit=${limit}`) as Promise<BrainKnowledge[]>,
  changeBrainKnowledge: (id:string, knowledgeId:string, action:'invalidate'|'restore') =>
    req(`/projects/${id}/brain/knowledge/${knowledgeId}/${action}`, {method:'POST',body:JSON.stringify({actor:'validator'})}),
  brainActions: (id: string) =>
    req(`/projects/${id}/brain/actions`) as Promise<BrainAction[]>,
  brainRisks: (id: string) =>
    req(`/projects/${id}/brain/risks`) as Promise<BrainAction[]>,
  brainTimeline: (id: string) => req(`/projects/${id}/brain/timeline`),
  brainScan: (id: string) => req(`/projects/${id}/brain/scan`, { method: "POST" }),
  brainRetryMemory: (id: string) => req(`/projects/${id}/brain/memory/retry`, { method: "POST" }) as Promise<{indexed: number; failed: number; forgotten: number}>,
  brainProjects: () => req("/brain/projects"),
  brainTriageStats: () => req("/brain/triage/stats") as Promise<TriageStats>,
  brainTriageQueue: (offset = 0) => req(`/brain/triage/queue?offset=${offset}`),
  brainSources: (status = "all", offset = 0, projectId?: string) => req(`/brain/sources?status=${encodeURIComponent(status)}&offset=${offset}${projectId ? `&project_id=${encodeURIComponent(projectId)}` : ""}`),
  pendingMailPage: (offset = 0, q = "", sort = "newest") => request<MailPage<PendingMail>>(
    `/v1/mail/page?scope=pending&limit=200&offset=${offset}&q=${encodeURIComponent(q)}&sort=${sort}`),
  mailProjectUsage: () => request<{projects:{project_id:string;score:number;count:number;last_used:string}[]}>("/v1/mail/project-usage"),
  classifiedMailPage: (offset = 0, q = "", sort = "newest", projectId?: string, signal?:AbortSignal) => request<MailPage<SourceMail>>(
    `/v1/mail/page?scope=resolved&limit=100&offset=${offset}&q=${encodeURIComponent(q)}&sort=${sort}${projectId ? `&project_id=${encodeURIComponent(projectId)}` : ""}`, {signal},30000),
  rejectedMailPage: (offset = 0, q = "", sort = "newest", signal?:AbortSignal) => request<MailPage<SourceMail>>(
    `/v1/mail/page?scope=rejected&limit=100&offset=${offset}&q=${encodeURIComponent(q)}&sort=${sort}`, {signal},30000),
  brainImportEml: (projectId: string | null, file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<{status: "resolved" | "duplicate" | "resolution_pending"}>(
      projectId ? `/v1/projects/${encodeURIComponent(projectId)}/import-eml` : "/v1/sources/upload-eml",
      {method: "POST", body, activity: "Import du mail"},
    );
  },
  brainSourceDetail: (sourceId: string, signal?: AbortSignal) =>
    request<any>(`/v1/sources/${encodeURIComponent(sourceId)}`, { signal }, 30_000),
  brainDiscardSource: (sourceId: string) => req(`/brain/sources/${encodeURIComponent(sourceId)}/discard`, { method: "POST" }),
  brainReassignSource: (sourceId: string, project_id: string) => req(`/brain/sources/${sourceId}/reassign`, { method: "POST", body: JSON.stringify({ project_id }) }),
  brainTriageRun: (limit = 50, offset = 0, force = false) =>
    req(`/brain/triage/run?limit=${limit}&offset=${offset}&force=${force}`, { method: "POST" }, 600_000) as Promise<TriageResult>,
  brainAutoStatus: () => req("/brain/ingest/auto-status"),
  brainTriageAccept: (proposalId: string) =>
    req(`/brain/triage/${proposalId}/accept`, {
      method: "POST", body: JSON.stringify({ actor: "validator" }),
    }),
  brainTriageReject: (proposalId: string) =>
    request<{source_id: string; status: "rejected"}>(`/v1/triage/${encodeURIComponent(proposalId)}/reject`, {method: "POST"}),
  brainTriageAssign: (proposalId: string, project_id: string) =>
    req(`/brain/triage/${proposalId}/assign`, {
      method: "POST", body: JSON.stringify({ project_id, actor: "validator" }),
    }),
  aiGenerate: (id: string, text: string, physical_page: number) =>
    req(`/projects/${id}/cdc/ai-generate`, {
      method: "POST", body: JSON.stringify({ text, physical_page }),
    }),
  search: (q: string, project_id?: string) =>
    req(`/search?q=${encodeURIComponent(q)}${project_id ? `&project_id=${project_id}` : ""}`),
  exportProject: (id: string) => req(`/projects/${id}/export`),
  importJson: (data: object, code?: string) =>
    req("/projects/import-json", { method: "POST", body: JSON.stringify({ data, code }) }),
  planning: (id: string) => req(`/projects/${id}/planning`),
  patchTask: (pid: string, tid: string, body: object) =>
    req(`/projects/${pid}/tasks/${tid}`, { method: "PATCH", body: JSON.stringify(body) }),
  addMilestone: (pid: string, title: string, due_date: string) =>
    req(`/projects/${pid}/milestones`, { method: "POST", body: JSON.stringify({ title, due_date }) }),
  addDeliverable: (pid: string, title: string) =>
    req(`/projects/${pid}/deliverables`, { method: "POST", body: JSON.stringify({ title }) }),
  patchMilestone: (pid: string, mid: string, body: object) =>
    req(`/projects/${pid}/milestones/${mid}`, { method: "PATCH", body: JSON.stringify(body) }),
  patchDeliverable: (pid: string, did: string, body: object) =>
    req(`/projects/${pid}/deliverables/${did}`, { method: "PATCH", body: JSON.stringify(body) }),
  sageConfig: () => req("/sage/config") as Promise<{root_path: string}>,
  saveSageConfig: (root_path: string) =>
    req("/sage/config", { method: "PUT", body: JSON.stringify({ root_path }) }),
  sageStatus: () => req("/sage/status") as Promise<SageStatus>,
  sageRun: () => req("/sage/run", { method: "POST" }) as Promise<{total_rows: number}>,
  purchases: (id: string) => req(`/projects/${id}/purchases`) as Promise<Purchases>,
  tracking: (id: string) => req(`/projects/${id}/time-tracking`) as Promise<Tracking>,
  addTimeEntry: (id: string, body: object) =>
    req(`/projects/${id}/time-entries`, { method: "POST", body: JSON.stringify(body) }),
  bom: (id: string) => req(`/projects/${id}/bom`) as Promise<Bom>,
  actions: (id?: string) => req(`/actions${id ? `?project_id=${encodeURIComponent(id)}` : ""}`) as Promise<Actions>,
  operations: () => req("/operations/status") as Promise<OperationsState>,
  verifyBackup: () => req("/operations/backup/verify", {method: "POST"}) as Promise<BackupState>,
  addBomLine: (id: string, body: object) =>
    req(`/projects/${id}/bom`, { method: "POST", body: JSON.stringify(body) }),
  patchBomLine: (pid: string, lid: string, body: object) =>
    req(`/projects/${pid}/bom/${lid}`, { method: "PATCH", body: JSON.stringify(body) }),
  importBomCsv: async (id: string, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<{created: number}>(BASE + `/projects/${id}/bom/import`, { method: "POST", body: fd });
  },
};
