import { request } from "./http";

export type TranscriptSegment = {id: string; start: number; end: number; speaker: string; text: string};
export type MeetingEvidence = {text: string; segment_id: string; quote: string};
export type MeetingAudioSummary = {overview: string; decisions: MeetingEvidence[];
  actions: (MeetingEvidence & {owner: string; due_date: string})[]; open_points: MeetingEvidence[];
  rejected_items?: number; chunks?: number};
export type MeetingRecording = {id: string; source_id: string; title: string; date: string; filename: string;
  num_speakers: number; segments: TranscriptSegment[]; speaker_names: Record<string, string>;
  revision: number; reviewed_revision: number; summary_revision: number; summary: Partial<MeetingAudioSummary>;
  summary_model: string; published_meeting_id: string | null; job_kind: string; job_status: string; stage: string;
  progress: number; processed_seconds: number; duration_seconds: number; cancel_requested: boolean;
  error: string | null; created_at: string; updated_at: string};
export type RecordingListItem = Omit<MeetingRecording, "segments" | "speaker_names" | "summary">;
export type AudioRuntime = {ready: boolean; model: string; device: string; detail: string; max_upload_mb: number; max_duration_minutes: number};
const path = (project: string, recording?: string) => `/api/v1/projects/${project}/recordings${recording ? `/${recording}` : ""}`;
export const meetingAudio = {
  status: () => request<AudioRuntime>("/api/v1/meeting-audio/status"),
  list: (project: string,quiet=false) => request<RecordingListItem[]>(path(project),quiet?{activity:false}:{}),
  get: (project: string, id: string, signal?: AbortSignal,quiet=false) => request<MeetingRecording>(path(project, id), {signal,activity:quiet?false:undefined}),
  upload: (project: string, body: FormData) => request<MeetingRecording>(path(project), {method: "POST", body}),
  transcribe: (project: string, id: string) => request<MeetingRecording>(path(project, id) + "/transcribe", {method: "POST"}),
  cancel: (project: string, id: string) => request<MeetingRecording>(path(project, id) + "/cancel", {method: "POST"}),
  review: (project: string, id: string, revision: number, segments: TranscriptSegment[], speaker_names: Record<string, string>, validate: boolean) =>
    request<MeetingRecording>(path(project, id) + "/transcript", {method: "PUT", body: JSON.stringify({revision, segments, speaker_names, validate})}),
  synthesize: (project: string, id: string) => request<MeetingRecording>(path(project, id) + "/synthesize", {method: "POST"}),
  publish: (project: string, id: string, revision: number, summary: MeetingAudioSummary) => request<MeetingRecording>(path(project, id) + "/publish", {
    method: "POST", body: JSON.stringify({revision, summary: {overview: summary.overview, decisions: summary.decisions, actions: summary.actions, open_points: summary.open_points}})}),
  audioUrl: (project: string, id: string) => path(project, id) + "/audio",
};
