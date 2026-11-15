import { request } from "./http";

export type DateField = "contractual_date" | "forecast_date" | "actual_date";
export type MilestoneEvidence = {kind: string; label: string; quote?: string; path?: string; source_id?: string; candidate_id?: string};
export type Milestone = {id: string; title: string; due_date: string; contractual_date?: string; forecast_date?: string;
  actual_date?: string; variance_days?: number | null; state?: string; date_sources?: Partial<Record<DateField, MilestoneEvidence>>};
export type MilestoneCandidate = {id: string; title: string; date_type: DateField; date: string; quote: string;
  evidence: MilestoneEvidence; confidence: number; current_value: string; conflict: boolean; milestone_id: string | null};
export type MilestoneJob = {id: string; status: string; processed: number; total: number; proposed: number;
  warnings: string[]; error: string | null; updated_at: string};
export type MilestoneReview = {candidates: MilestoneCandidate[]; pending_total: number; job: MilestoneJob | null;planning_revision?:number};
export type MilestoneChange = {id: string; field: string; previous: string; value: string; evidence: MilestoneEvidence; created_at: string};
const root = (id: string) => `/api/v1/projects/${encodeURIComponent(id)}/milestones`;
export const milestoneApi = {
  review: (id: string, signal?: AbortSignal,quiet=false) => request<MilestoneReview>(`${root(id)}/review`, {signal,activity:quiet?false:undefined}, 10000),
  scan: (id: string) => request<MilestoneJob>(`${root(id)}/scan`, {method: "POST"}),
  decide: (id: string, candidateId: string, body: {decision: "accept" | "reject"; expected_value: string; milestone_id?: string | null;expected_revision?:number}) =>
    request(`${root(id)}/candidates/${encodeURIComponent(candidateId)}/decision`, {method: "POST", body: JSON.stringify(body)}),
  history: (id: string, milestoneId: string) => request<MilestoneChange[]>(`${root(id)}/${encodeURIComponent(milestoneId)}/history`),
};
