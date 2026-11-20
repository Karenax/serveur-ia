import { agentFetch } from './agentRoutes';
import { request } from './http';
import { beginActivity } from './asyncActivity';
import type { NoteContent, NoteDetail } from './projectNotes';
import {subscribeSessionEvents} from './sessionEvents';
import {HttpError} from './httpError';
import {matchesMeetingCommandReceipt, matchesMeetingCommandResult, type DurableAction} from './meetingCommandReceipts';

export type MeetingSessionState = 'created' | 'recording' | 'paused' | 'finalizing' | 'completed' | 'interrupted' | 'cancelled';
export type MeetingTrack = 'mic' | 'system';
export type SessionChunk = {id?:string;track: MeetingTrack; sequence: number; sha256: string; size_bytes: number; start_ms: number; duration_ms: number;created_at?:string;
  speech_status?:'retained'|'pending'|'running'|'completed'|'failed'|'batch_pending'|'batch_running';speech_error?:string|null};
export type LiveTranscriptSegment = {id: string; track: MeetingTrack; start_ms: number; end_ms: number; speaker: string; text: string; revision: number; finalized: boolean};
export type SessionTrack = {name: MeetingTrack; mime_type: string; filename: string; chunks: number; total_bytes: number; duration_seconds: number; complete: boolean};
export type SessionNote = {title: string; content: NoteContent; plain_text?: string; revision: number; version_id?: string};
export type SessionNoteVersion={id:string;session_id:string;revision:number;title:string;content:NoteContent;plain_text:string;sha256:string;created_at:string};
export type NativeCaptureOwner={session_id:string;state:string;tracks:MeetingTrack[];process_alive:boolean|null;
  stop_confirmation_required:boolean;can_control:boolean;problem_code?:'interrupted'|'interruption-unpersisted'|'status-unknown';error?:string};
export type NativeCaptureRecovery={session_id:string;event_cursor:number;reason:'interrupted'|'stop-unconfirmed'|'conservation-pending';
  can_control:boolean;pending_stop?:SessionCommand};
export type NativeCaptureItem={session_id:string;state:string;tracks:MeetingTrack[];can_control?:boolean;error?:string;
  process_alive?:boolean|null;stop_confirmation_required?:boolean;problem_code?:NativeCaptureOwner['problem_code']};
export type NativeCaptureStatus={installed:boolean;ready:boolean;loopback_ready:boolean;real_test_passed:boolean;microphone_test_passed:boolean;
  devices:{index:number;name:string;maxInputChannels:number;maxOutputChannels:number;defaultSampleRate:number;isLoopbackDevice:boolean}[];
  active?:NativeCaptureItem[];owners?:NativeCaptureOwner[];recovery?:NativeCaptureRecovery[];session?:NativeCaptureItem|null;error?:string};
export type BrowserCaptureOwner = {owner_id: string; state: 'reserved'|'recording'|'paused'; can_control: boolean};
export type MeetingSession = {
  id: string; title: string; kind: 'meeting' | 'note' | 'import'; project_id: string | null; brain_project_id: string | null;
  state: MeetingSessionState; revision: number; date: string; recording_id: string | null; note_id: string | null;
  note_revision?: number | null; note_version_id?: string | null; note?: NoteDetail | null; staged_note?: SessionNote | null;
  published_meeting_id?: string | null; published_note_version_id?: string | null; calendar_context?: Record<string, unknown> | null;
  native_capture?:NativeCaptureItem|null;native_recovery?:NativeCaptureRecovery[];browser_capture?:BrowserCaptureOwner|null;
  tracks: SessionTrack[]; chunks?: SessionChunk[]; total_bytes: number; duration_seconds: number;
  segments?: LiveTranscriptSegment[]; transcript_provisional?: boolean;transcript_processing_complete?:boolean;event_cursor?:number;live_transcription_enabled?:boolean;
  transcription_admission?:{policy:string;suspended:boolean;reason?:string|null;admitted_chunks:number;retained_chunks:number;
    retained_batch_only_chunks:number;recoverable_direct_chunks?:number;last_transition_at_utc?:string|null};
  transcription_batch?:SessionBatchStatus|null;
  issues: string[]; created_at: string; updated_at: string;
};
export type SessionCapabilities = {
  enabled: boolean;
  capture: {durable: boolean; max_upload_mb: number; max_capture_mb?: number; max_duration_minutes: number; tracks: MeetingTrack[]; browser_permission_required: boolean};
  transcription: {batch_ready: boolean;session_batch_ready?:boolean; live_ready: boolean;enabled?:boolean;installed?:boolean;live_operational?:boolean;qualified_live_latency?:boolean;industrial_quality_qualified?:boolean; detail: string};
  notes: {staging: boolean; erp_projection: boolean};
  assistant?: {ready?: boolean; enabled?: boolean};
  native_capture?:NativeCaptureStatus;
};
export type SessionCitation = {source_id?: string; title?: string; excerpt?: string; quote?: string; locator?: Record<string, unknown>; source_url?: string; audio_url?: string};
export type SessionAnswer = {answer: string;query?:string;scope?:SessionScope;source_ids?:string[];pinned?:boolean;useful?:boolean|null; citations?: SessionCitation[]; warnings?: string[]; revision?: number; stale?: boolean; id?: string; status?: string};
export type SessionQuestionProgress = {state:'idle'|'disabled'|'pending'|'completed'|'failed'|'interrupted'|'obsolete'|'unknown';
  elapsed_seconds:number;delayed:boolean;enabled:boolean;attempt_id:number|null};
export type SessionSuggestion = {
  id: string; text?: string; answer?: string; content?: NoteContent; status: string; revision?: number;
  citations?: SessionCitation[]; created_at?: string; note_revision?: number;note_version_id?:string|null;
};
export type SessionAutomaticEnhancement={enabled:boolean;state:'disabled'|'waiting'|'running'|'failed'|'completed'|'obsolete'|'stopped';
  detail:string;error:string|null;note_version_id:string|null;stable_seconds:number;attempt_id:string|null;retry_after_seconds?:number};
export type SessionScope = 'session' | 'project' | 'sources' | 'global';
export type SessionHistory = {role: 'user' | 'assistant'; content: string}[];
export type SessionFilter = {project_id?: string; q?: string; offset?: number; limit?: number};
export type SessionCommand = {command_id: string; expected_revision: number; browser_capture_owner_id?: string};
export type NoteEvidence = {text: string; block_index: number; quote: string};
export type NotesSummary = {overview: string; decisions: NoteEvidence[]; actions: (NoteEvidence & {owner: string; due_date: string})[]; open_points: NoteEvidence[]};
export type NotesPublication = SessionCommand & {expected_note_revision: number; expected_note_version_id: string; summary: NotesSummary};
export type SessionChunkReceipt = {session_id: string; accepted_chunk: {track: MeetingTrack; seq: number; sha256: string; size_bytes: number};
  revision: number; replayed: boolean; acknowledged: boolean};
export type TranscriptionRetryResult={session:MeetingSession;retried_chunks:number;chunk_ids:string[];
  remaining_recoverable_chunks?:number;retained_batch_only_chunks?:number;admission_resumed?:boolean;admission_blocked_reason?:string|null};
export type SessionBatchStatus={command_id:string|null;state:'idle'|'admitted'|'running'|'cancelling'|'interrupted'|'completed'|'failed'|'cancelled';
  selected_chunks:number;completed_chunks:number;error:string|null};
export type SessionBatchResult={session:MeetingSession;batch:SessionBatchStatus};
const root = '/api/v1/meeting-sessions';
const path = (id: string) => `${root}/${encodeURIComponent(id)}`;
export const sessionCommand = (revision: number): SessionCommand => ({command_id: crypto.randomUUID(), expected_revision: revision});
export const hasDesktopCapture = () => document.body.dataset.kiaraCapture === 'true';
export const sessionAudioUrl = (id: string, track: MeetingTrack) => `${path(id)}/audio?track=${track}`;
export const sessionExportUrl=(id:string)=>`${path(id)}/export`;
async function durableCommand<T>(id:string,action:DurableAction,body:Record<string,unknown>,url:string):Promise<T>{
  const owner=body.browser_capture_owner_id;
  const key=`agent.meeting-command.v1.${id}.${action}${owner?`.owner.${owner}.revision.${body.expected_revision}`:''}`;
  const previous=localStorage.getItem(key);
  const payload=previous?JSON.parse(previous):body;
  if(owner&&(payload.browser_capture_owner_id!==owner||payload.expected_revision!==body.expected_revision))throw new Error('Cette commande audio appartient à une autre réservation.');
  if(!previous)localStorage.setItem(key,JSON.stringify(payload));
  try{
    const result=await request<T>(url,{method:'POST',body:JSON.stringify(payload)},0);
    if(!matchesMeetingCommandResult(result,id,action,owner))throw new Error('Réponse de séance incohérente ; commande conservée pour vérification.');
    // A successful HTTP stop may only have drained the helper: conservation can
    // still be pending. Keep its original identity until the session is complete.
    if(action!=='native-stop'||(result as {state?:string})?.state==='completed')localStorage.removeItem(key);
    return result;
  }catch(failure){
    // A rejected or never-started command can be prepared again. Prepared commands
    // and uncertain network results retain the exact original payload.
    const finish=beginActivity('Vérification de la commande de réunion…',{delayMs:800});
    try{
      const response=await agentFetch(`${path(id)}/commands/${encodeURIComponent(String(payload.command_id))}`,{credentials:'same-origin'});
      // A 404 may hide the session, and a request lost in transit may still
      // arrive after this read. Release only a confirmed stale-revision
      // precondition with an explicitly absent receipt.
      if(response.status===404&&!action.startsWith('native-')&&failure instanceof HttpError&&failure.status===409&&
        failure.message==='La séance a changé ; conserver la saisie et recharger.'){
        const missing=await response.json() as {detail?:unknown}|null;
        if(missing?.detail==='Commande introuvable dans cette séance')localStorage.removeItem(key);
      }
      else if(response.ok){const receipt=await response.json();
        const matching=matchesMeetingCommandReceipt(receipt,id,action,payload.command_id,owner);
        if(matching&&receipt.status==='rejected')localStorage.removeItem(key);
        else if(matching&&receipt.status==='completed'){localStorage.removeItem(key);return receipt.result as T;}}
    }catch{/* Offline receipt remains recoverable. */}finally{finish();}
    throw failure;
  }
}

export const meetingSessions = {
  watchEvents: subscribeSessionEvents,
  capabilities: (signal?: AbortSignal) => request<SessionCapabilities>(`${root}/capabilities`, {signal}, 20_000),
  list: (filters: SessionFilter = {}, signal?: AbortSignal) => {
    const query = new URLSearchParams();
    Object.entries({...filters, limit: filters.limit ?? 25}).forEach(([key, value]) => {if (value !== undefined && value !== '') query.set(key, String(value));});
    return request<{items: MeetingSession[]; total: number; offset: number; limit: number}>(`${root}?${query}`, {signal}, 30_000);
  },
  get: (id: string, signal?: AbortSignal, quiet=false) => request<MeetingSession>(path(id), {signal,activity:quiet?false:undefined}, 30_000),
  noteVersion:(id:string,versionId:string,signal?:AbortSignal)=>request<SessionNoteVersion>(`${path(id)}/note-versions/${encodeURIComponent(versionId)}`,{signal},30_000),
  create: (body: {command_id: string; title: string; kind: MeetingSession['kind']; project_id: string | null; date: string}) =>
    request<MeetingSession>(root, {method: 'POST', body: JSON.stringify(body)}, 30_000),
  command: (id: string, action: 'pause' | 'resume' | 'finalize' | 'cancel', body: SessionCommand) =>
    durableCommand<MeetingSession>(id,action,body,`${path(id)}/${action}`),
  commandReceipt:(id:string,commandId:string)=>request<{id:string;kind:string;status:string;result?:MeetingSession}>(`${path(id)}/commands/${encodeURIComponent(commandId)}`,{},20_000),
  browserReserve:(id:string,body:SessionCommand&{owner_id:string})=>
    request<MeetingSession>(`${path(id)}/browser-capture/reserve`,{method:'POST',body:JSON.stringify(body)},30_000),
  browserRelease:(id:string,body:SessionCommand&{owner_id:string})=>
    request<MeetingSession>(`${path(id)}/browser-capture/release`,{method:'POST',body:JSON.stringify(body)},30_000),
  retryTranscription:(id:string,body:SessionCommand)=>
    durableCommand<TranscriptionRetryResult>(id,'retry-transcription',body,`${path(id)}/transcription/retry`),
  batchTranscription:(id:string,body:SessionCommand)=>
    durableCommand<SessionBatchResult>(id,'batch-transcription',body,`${path(id)}/transcription/batch`),
  cancelBatchTranscription:(id:string,body:SessionCommand)=>
    durableCommand<SessionBatchResult>(id,'cancel-batch-transcription',body,`${path(id)}/transcription/batch/cancel`),
  batchTranscriptionStatus:(id:string,signal?:AbortSignal)=>request<SessionBatchStatus>(`${path(id)}/transcription/batch`,{signal},20_000),
  assign: (id: string, body: SessionCommand & {project_id: string}) =>
    durableCommand<MeetingSession>(id,'assign-project',body,`${path(id)}/assign-project`),
  saveNote: (id: string, body: SessionCommand & {title: string; content: NoteContent; expected_note_revision?: number; expected_note_version_id?: string}) =>
    request<MeetingSession>(`${path(id)}/notes`, {method: 'PUT', body: JSON.stringify(body)}, 60_000),
  chunk: (id: string, track: MeetingTrack, seq: number, body: FormData) =>
    request<SessionChunkReceipt>(`${path(id)}/chunks/${track}/${seq}`, {method: 'PUT', body,activity:false}, 600_000),
  ask: (id: string, body: {query: string; scope: SessionScope; source_ids: string[]; history: SessionHistory}) =>
    request<SessionAnswer>(`${path(id)}/ask`, {method: 'POST', body: JSON.stringify(body)}),
  askHistory:(id:string,scope:SessionScope,sourceIds:string[]=[],signal?:AbortSignal,quiet=false)=>{
    const query=new URLSearchParams({scope});[...new Set(sourceIds)].sort().forEach(source=>query.append('source_ids',source));
    return request<{items:SessionAnswer[]}>(`${path(id)}/ask?${query}`,{signal,activity:quiet?false:undefined},30_000);
  },
  enhance: (id: string, revision: number) =>
    request<SessionSuggestion>(`${path(id)}/enhancements`, {method: 'POST', body: JSON.stringify({expected_revision: revision})}),
  enhancements: (id: string, signal?: AbortSignal, quiet=false) => request<{items: SessionSuggestion[];automatic?:SessionAutomaticEnhancement}>(`${path(id)}/enhancements`, {signal,activity:quiet?false:undefined}),
  decide: (id: string, suggestionId: string, decision: 'accept' | 'reject', revision: number) =>
    request<MeetingSession>(`${path(id)}/enhancements/${encodeURIComponent(suggestionId)}/decision`, {
      method: 'POST', body: JSON.stringify({decision, expected_revision: revision})}),
  liveAnswers: (id: string, signal?: AbortSignal, quiet=false) => request<{items: SessionAnswer[];automatic?:SessionQuestionProgress}>(`${path(id)}/live-answers`, {signal,activity:quiet?false:undefined}),
  liveAnswer: (id: string, query: string, revision: number) => request<SessionAnswer>(`${path(id)}/live-answers`, {
    method: 'POST', body: JSON.stringify({query, expected_revision: revision})}),
  pinAnswer:(id:string,answerId:string,pinned:boolean)=>request<{id:string;pinned:boolean}>(`${path(id)}/live-answers/${encodeURIComponent(answerId)}/pin`,{
    method:'PUT',body:JSON.stringify({pinned})},30_000),
  rateAnswer:(id:string,kind:'ask'|'live',answerId:string,useful:boolean|null)=>request<{id:string;kind:'ask'|'live';useful:boolean|null}>(`${path(id)}/answers/${kind}/${encodeURIComponent(answerId)}/feedback`,{
    method:'PUT',body:JSON.stringify({useful})},30_000),
  publishNotes: (id: string, body: NotesPublication) => request<{session: MeetingSession; meeting_id: string; action_ids: string[]; published_note_version_id: string; replayed: boolean}>(
    `${path(id)}/publish-notes`, {method: 'POST', body: JSON.stringify(body)}, 90_000),
  editSegment: (id: string, segmentId: string, body: {command_id: string; expected_session_revision: number; expected_segment_revision: number; text: string; speaker: string}) =>
    request<MeetingSession>(`${path(id)}/segments/${encodeURIComponent(segmentId)}`, {method: 'PUT', body: JSON.stringify(body)}),
  calendar: (id: string, body: FormData) => request<MeetingSession>(`${path(id)}/calendar-context`, {method: 'POST', body}, 30_000),
  nativeStatus:(id?:string,signal?:AbortSignal,quiet=false)=>request<NativeCaptureStatus>(id?`${path(id)}/native-capture/status`:'/api/v1/workspace/native-capture',{signal,activity:quiet?false:undefined},20_000),
  stopDesktopCapture:(id:string)=>request<MeetingSession>(`${path(id)}/native-capture/stop`,{method:'POST',body:'{}'},90_000),
  native:(id:string,action:'start'|'pause'|'resume'|'stop',body:SessionCommand&{tracks?:MeetingTrack[];devices?:{mic?:number;system?:number}})=>{
    const url=`${path(id)}/native-capture/${action}`;
    return hasDesktopCapture()
      ? request<MeetingSession>(url,{method:'POST',body:JSON.stringify(body)},90_000)
      : durableCommand<MeetingSession>(id,`native-${action}`,body,url);
  },
};
