import { agentPath, projectConversationHref } from '../lib/agentRoutes';
import { useCallback, useEffect, useLayoutEffect, useRef, useState, useSyncExternalStore, type ReactNode } from 'react';
import type { PortfolioRow } from '../lib/api';
import { beginActivity, withActivity } from '../lib/asyncActivity';
import { AsyncDownloadLink } from './AsyncDownloadLink';
import { meetingCapture } from '../lib/meetingCapture';
import { hasDesktopCapture, meetingSessions, sessionAudioUrl, sessionExportUrl, sessionCommand, type MeetingSession, type SessionAnswer,
  type SessionCapabilities, type SessionScope, type SessionSuggestion,type SessionAutomaticEnhancement,type SessionQuestionProgress,type MeetingTrack } from '../lib/meetingSessions';
import { blankNote, validNoteContent, type NoteContent } from '../lib/projectNotes';
import { NoteContentView, NoteRichEditor } from './NoteRichEditor';
import { MeetingAudioPanel } from './MeetingAudioPanel';
import { ChatMarkdown } from './ChatMarkdown';
import { fusionSources, type LibrarySource } from '../lib/fusionSources';
import { MeetingNotePublication } from './MeetingNotePublication';
import { MeetingCalendarContext } from './MeetingCalendarContext';
import { MeetingTranscriptEdit } from './MeetingTranscriptEdit';
import { NativeMeetingCapture } from './NativeMeetingCapture';
import { MeetingQuestionProgress } from './MeetingQuestionProgress';
import {citationSourceUrl,citationReaderUrl,citationAudioUrl,citationLocatorText,isNoteVersionUrl} from '../lib/citationLinks';
import {NoteVersionPreview} from './NoteVersionPreview';
import {useTranscriptFollow} from '../lib/useTranscriptFollow';
import './project-notes.css';
import '../meeting-studio.css';

const errorText = (error: unknown) => error instanceof Error ? error.message : String(error);
class SessionReadFailure extends Error {
  constructor(failure: unknown) {super(errorText(failure)); this.name='SessionReadFailure';}
}
const clock = (seconds: number) => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`;
const SESSION_STATES: Record<string, string> = {created: 'À préparer', recording: 'Enregistrement', paused: 'En pause',
  finalizing: 'Consolidation', completed: 'Conservée', interrupted: 'Interrompue', cancelled: 'Arrêtée'};
function nativeSessionPhase(row:MeetingSession){
  const native=row.native_capture;
  if(native?.session_id===row.id&&['recording','paused'].includes(row.state)){
    if(native.error||native.state==='interrupted'||['interrupted','interruption-unpersisted'].includes(native.problem_code||''))return 'interrupted';
    if(native.process_alive===null||native.state==='unknown'||native.problem_code==='status-unknown')return 'unknown';
    if(native.state==='starting')return 'starting';
    if(native.process_alive===false||native.state==='stopped')return 'stopped';
    if(native.state==='paused')return 'paused';
    if(native.state==='recording')return 'recording';
  }
  return null;
}
function sessionStateLabel(row:MeetingSession){
  const phase=nativeSessionPhase(row);
  if(phase)return {starting:'Ouverture audio en cours',interrupted:'Capture interrompue · conservation à vérifier',
    unknown:'État audio à vérifier',stopped:'Capture arrêtée · conservation à vérifier',paused:'En pause',recording:'Enregistrement'}[phase];
  return SESSION_STATES[row.state]||row.state;
}
function sessionCaptureNotice(row:MeetingSession){
  const phase=nativeSessionPhase(row);
  if(phase==='starting')return 'L’ouverture audio est en cours.';
  if(phase&&['interrupted','unknown','stopped'].includes(phase))return 'La capture audio et sa conservation restent à vérifier.';
  if(phase==='paused')return 'L’enregistrement est en pause.';
  return row.state==='recording'?'L’enregistrement continue.':row.state==='paused'?'L’enregistrement est en pause.':
    row.state==='completed'?'L’enregistrement est terminé et conservé.':'Les fragments audio restent conservés.';
}
const noteFrom = (row: MeetingSession) => row.note ?? row.staged_note;
const draftKey = (id: string) => `agent.meeting-note.v1.${id}`;
const contextStorageKey=(id:string)=>`agent.meeting-discussion-context.v1.${id}`;
function savedContext(id:string){
  try{const value=JSON.parse(localStorage.getItem(contextStorageKey(id))||'null');
    if(value&&['session','project','sources','global'].includes(value.scope)&&Array.isArray(value.sourceIds)&&value.sourceIds.length<=100&&
      value.sourceIds.every((source:unknown)=>typeof source==='string'&&/^[A-Za-z0-9_-]+$/.test(source)))
      return {scope:value.scope as SessionScope,sourceIds:[...new Set(value.sourceIds as string[])].sort()};
  }catch{/* A malformed preference cannot supply conversation evidence. */}
  return {scope:'session' as SessionScope,sourceIds:[] as string[]};
}
function textOf(content: NoteContent) {
  return content.blocks.map(block => block.type === 'image' ? block.caption : block.type === 'table'
    ? block.rows.map(row => row.map(cell => cell.map(run => run.text).join('')).join('\t')).join('\n')
    : block.type === 'list' ? block.items.map(item => item.runs.map(run => run.text).join('')).join('\n')
    : block.runs.map(run => run.text).join('')).join('\n');
}

export function MeetingCaptureBar({onOpen}: {onOpen: (sessionId: string) => void}) {
  const capture = useSyncExternalStore(meetingCapture.subscribe, meetingCapture.getSnapshot);
  const [operation, setOperation] = useState('');
  const [error, setError] = useState('');
  useEffect(() => {void meetingCapture.recover().catch(() => undefined);}, []);
  useEffect(()=>{
    const protect=(event:BeforeUnloadEvent)=>{if(!['idle','completed'].includes(capture.phase)){event.preventDefault();event.returnValue='';}};
    window.addEventListener('beforeunload',protect);return()=>window.removeEventListener('beforeunload',protect);
  },[capture.phase]);
  if (!capture.sessionId || ['idle', 'completed'].includes(capture.phase)) return null;
  const run = async (label: string, task: () => Promise<unknown>) => {
    setOperation(label); setError(''); try {await task();} catch (failure) {setError(errorText(failure));} finally {setOperation('');}
  };
  return <section className="meeting-capture-bar" aria-label="Capture de réunion active">
    <span><strong>{capture.title || 'Réunion'}</strong> · {clock(capture.seconds)} · {capture.tracks.map(track => track === 'mic' ? 'Micro' : 'Audio partagé').join(' + ')}
      {capture.pending > 0 && ` · ${capture.pending} fragment(s) à synchroniser`}</span>
    <button type="button" onClick={() => onOpen(capture.sessionId!)}>Revenir à la séance</button>
    {capture.phase === 'starting' && <button type="button" onClick={() => void run('Annulation du démarrage', () => meetingCapture.stop())}>Annuler le démarrage audio</button>}
    {capture.phase === 'recording' && <button type="button" disabled={!!operation} onClick={() => void run('Pause', () => meetingCapture.pause())}>Pause</button>}
    {capture.phase === 'ready' && <>
      <span role="status">Partage audio prêt à confirmer</span>
      <button type="button" disabled={!!operation} onClick={() => void run('Partage audio', () => meetingCapture.activatePrepared())}>Choisir l’audio du PC et démarrer</button>
      <button type="button" disabled={!!operation} onClick={() => void run('Annulation', () => meetingCapture.cancelPrepared())}>Annuler la préparation audio</button>
    </>}
    {capture.phase === 'paused' && <button type="button" disabled={!!operation} onClick={() => void run('Reprise', () => meetingCapture.resume())}>Reprendre</button>}
    {['recording', 'paused'].includes(capture.phase) && <button type="button" disabled={!!operation} onClick={() => void run('Conservation', () => meetingCapture.stop())}>Arrêter et conserver</button>}
    {capture.phase === 'pending' && <button type="button" disabled={!!operation} onClick={() => void run('Synchronisation', () => meetingCapture.retryAndFinalize())}>Synchroniser et finaliser</button>}
    {operation && <span role="status">{operation}…</span>}
    {(error || capture.error) && <p role="alert">{error || capture.error}</p>}
  </section>;
}

type Props = {sessionId: string; rows: PortfolioRow[]; capabilities: SessionCapabilities; onClose: () => void;
  navigation?: ReactNode;
  sessionList?: MeetingSession[]; onSelectSession?: (id:string)=>void; onNewSession?:()=>void;
  onOpenSource?:(citation:NonNullable<SessionAnswer['citations']>[number])=>void;
  onChanged?: () => void; onOpenProject: (id: string, tab: string) => void; active?: boolean};
export function MeetingStudio({sessionId, rows, capabilities, onClose, onChanged, onOpenProject,onOpenSource,active=true,navigation,sessionList,onSelectSession,onNewSession}: Props) {
  const [session, setSession] = useState<MeetingSession | null>(null);
  const [content, setContent] = useState<NoteContent>(blankNote);
  const [noteTitle, setNoteTitle] = useState('');
  const [noteSearch,setNoteSearch]=useState('');
  const draftRef = useRef({content: blankNote(), title: ''});
  const [dirty, setDirty] = useState(false);
  const [markdownDraft, setMarkdownDraft] = useState({pending: false, valid: true});
  const dirtyRef = useRef(false);
  const rowRef = useRef<MeetingSession | null>(null);
  const currentSessionId = useRef(sessionId);
  currentSessionId.current = sessionId;
  const sessionReadSequence = useRef(0);
  const acceptedReadSequence = useRef(0);
  const readOutcomeSequence = useRef(0);
  const restoredDraftSession = useRef<string | null>(null);
  const [noteConflict, setNoteConflict] = useState(false);
  const [recovered, setRecovered] = useState(false);
  const [error, setError] = useState('');
  const [sessionReadError, setSessionReadError] = useState('');
  const [eventReadError, setEventReadError] = useState('');
  const [sourceReadError, setSourceReadError] = useState('');
  const [notice, setNotice] = useState('');
  const [operation, setOperation] = useState('');
  const pendingNote = useRef<Parameters<typeof meetingSessions.saveNote>[1] | null>(null);
  const [project, setProject] = useState('');
  const [layout, setLayout] = useState<'editor' | 'enhanced' | 'assistant' | 'complete'>(() => {
    try {const saved = localStorage.getItem('agent-meeting-layout-v2');
      return saved === 'assistant' || saved === 'complete' || saved === 'enhanced' ? saved : 'editor';} catch {return 'editor';}
  });
  const [tab, setTab] = useState<'chat' | 'summary' | 'transcript' | 'questions'>('chat');
  const [systemAudio, setSystemAudio] = useState(false);
  const [browserMicrophone,setBrowserMicrophone]=useState('');
  const [browserDevices,setBrowserDevices]=useState<MediaDeviceInfo[]>([]);
  const [browserDevicesError,setBrowserDevicesError]=useState('');
  const [nativeBusy,setNativeBusy]=useState(false);
  const [nativeRecoveryControls,setNativeRecoveryControls]=useState(false);
  const [suggestions, setSuggestions] = useState<SessionSuggestion[]>([]);
  const [automatic,setAutomatic]=useState<SessionAutomaticEnhancement|null>(null),[automaticReadError,setAutomaticReadError]=useState('');
  const [automaticLoaded,setAutomaticLoaded]=useState(false);
  const [questionProgress,setQuestionProgress]=useState<{sessionId:string;status:SessionQuestionProgress|null}|null>(null);
  const [query, setQuery] = useState('');
  const [initialContext]=useState(()=>savedContext(sessionId));
  const [scope, setScope] = useState<SessionScope>(initialContext.scope);
  const [sourceIds, setSourceIds] = useState<string[]>(initialContext.sourceIds);
  const [sources,setSources] = useState<LibrarySource[]>([]),[sourceSearch,setSourceSearch] = useState('');
  const [conversation,setConversation]=useState<{key:string;items:{query:string;scope:SessionScope;result:SessionAnswer}[]}>({key:'',items:[]});
  const [historyLoading,setHistoryLoading]=useState(false),[historyError,setHistoryError]=useState(''),[historyTick,setHistoryTick]=useState(0);
  const historyReadSequence=useRef(0);
  const [liveAnswers, setLiveAnswers] = useState<SessionAnswer[]>([]);
  const capture = useSyncExternalStore(meetingCapture.subscribe, meetingCapture.getSnapshot);
  const alive = useRef(true);
  const audio = useRef<HTMLAudioElement>(null);
  const pendingAudioSeek=useRef<{url:string;seconds:number}|null>(null);
  useEffect(()=>{pendingAudioSeek.current=null;},[sessionId,layout,tab]);
  const applyAudioSeek=(player:HTMLAudioElement)=>{
    const request=pendingAudioSeek.current;
    if(!request||player!==audio.current||player.getAttribute('src')!==request.url)return;
    pendingAudioSeek.current=null;
    player.currentTime=request.seconds;
    void player.play().catch(()=>undefined);
  };
  const seekAudio=(track:MeetingTrack,startMs:number)=>{
    const player=audio.current;
    if(!player)return;
    const target=agentPath(sessionAudioUrl(sessionId,track)),changed=player.getAttribute('src')!==target;
    pendingAudioSeek.current={url:target,seconds:startMs/1000};
    if(changed)player.src=target;
    if(!changed&&player.readyState>=1)applyAudioSeek(player);
    else player.load();
  };
  const studioRoot=useRef<HTMLElement>(null);
  const assistantPane=useRef<HTMLElement>(null);
  const preparation=useRef<HTMLDetailsElement>(null);
  const preparationSummary=useRef<HTMLElement>(null);
  const captureHere = capture.sessionId === sessionId;
  const captureBusy = captureHere && ['ready', 'starting', 'recording', 'paused', 'stopping'].includes(capture.phase);
  const browserCaptureUnavailable = !['idle','completed','error'].includes(capture.phase);
  const transcriptLive=session?.id===sessionId&&['recording','paused'].includes(session.state);
  const directSuspended=session?.transcription_admission?.suspended===true;
  const admittedDirect=(session?.transcription_admission?.admitted_chunks||0)>0;
  const transcriptFollowLabel=directSuspended?(admittedDirect?'Transcription des passages en attente':'Direct suspendu'):'Suivi du direct';
  const transcriptFollow=useTranscriptFollow({sessionId,live:transcriptLive,
    visible:active&&tab==='transcript'&&(layout==='assistant'||layout==='complete'),
    update:session?.segments?.map(segment=>`${segment.id}:${segment.revision}`).join('|')||''});
  useEffect(()=>{
    if(!active||!navigator.mediaDevices?.enumerateDevices)return;
    let cancelled=false;
    let stopWaiting=()=>{};
    const abandoned=new Promise<MediaDeviceInfo[]>(resolve=>{stopWaiting=()=>resolve([]);});
    // Inventory only: microphone permission is requested exclusively by Start.
    void withActivity('Recherche des périphériques audio…',()=>Promise.race([navigator.mediaDevices.enumerateDevices(),abandoned]),{delayMs:800})
      .then(devices=>{if(!cancelled){setBrowserDevices(devices.filter(device=>device.kind==='audioinput'&&device.deviceId));setBrowserDevicesError('');}})
      .catch(()=>{if(!cancelled)setBrowserDevicesError('La liste des microphones du navigateur est indisponible. Vous pouvez utiliser le microphone par défaut.');});
    return()=>{cancelled=true;stopWaiting();};
  },[active,session?.kind]);
  const assistantReady = !!(capabilities.assistant?.enabled || capabilities.assistant?.ready);
  const selectedSources=[...new Set(sourceIds)].sort();
  const sourceKey=JSON.stringify(scope==='sources'?selectedSources:[]);
  const contextKey=JSON.stringify([sessionId,scope,sourceKey,session?.project_id||null,session?.brain_project_id||null]);
  const currentContext=useRef(contextKey),contextGeneration=useRef(0);
  if(currentContext.current!==contextKey){currentContext.current=contextKey;contextGeneration.current++;}
  const auxiliaryGeneration=useRef(0);
  const auxiliaryRequest=useRef(0);
  const replies=conversation.key===contextKey?conversation.items:[];
  const clearReplies=()=>setConversation({key:contextKey,items:[]});

  const accept = useCallback((row: MeetingSession) => {
    if (row.id !== currentSessionId.current) return false;
    const previous = rowRef.current;
    if (previous?.id === row.id && (row.revision < previous.revision ||
        (row.event_cursor !== undefined && previous.event_cursor !== undefined && row.event_cursor < previous.event_cursor))) return false;
    if (previous && previous.id !== row.id) {dirtyRef.current = false; setDirty(false); pendingNote.current = null; setNoteConflict(false); setRecovered(false);}
    rowRef.current = row; setSession(row); setProject(row.project_id || '');
    const note = noteFrom(row);
    if (!dirtyRef.current) {const next = {content: note?.content ?? blankNote(), title: note?.title || row.title};
      draftRef.current = next; setContent(next.content); setNoteTitle(next.title);}
    else if (previous && row.note_id && previous.note_version_id !== row.note_version_id) setNoteConflict(true);
    if (restoredDraftSession.current !== row.id) {
      restoredDraftSession.current = row.id;
      try {
        const raw = localStorage.getItem(draftKey(row.id));
        if (raw) {
          const draft = JSON.parse(raw);
          if (draft.session_id !== row.id || !validNoteContent(draft.content) || typeof draft.title !== 'string') throw new Error('Brouillon incompatible');
          if (JSON.stringify(draft.content) !== JSON.stringify(note?.content) || draft.title !== note?.title) {
            setContent(draft.content); setNoteTitle(draft.title); dirtyRef.current = true; setDirty(true); setRecovered(true);
            draftRef.current = {content: draft.content, title: draft.title};
            setNoteConflict(draft.note_version_id !== row.note_version_id || draft.revision !== row.revision);
            pendingNote.current = draft.command ?? null;
          }
        }
      } catch {setError('Un brouillon local ne peut pas être relu. Il reste conservé sur cet appareil.');}
    }
    return true;
  }, []);
  const readSession = useCallback(async (signal?: AbortSignal,quiet=false) => {
    const sequence = ++sessionReadSequence.current;
    try {
      const row = await (quiet?meetingSessions.get(sessionId,signal,true):signal ? meetingSessions.get(sessionId, signal) : meetingSessions.get(sessionId));
      if (!signal?.aborted && alive.current && currentSessionId.current === sessionId && sequence >= acceptedReadSequence.current && accept(row)) {
        acceptedReadSequence.current = sequence;
        if(sequence >= readOutcomeSequence.current){readOutcomeSequence.current=sequence;setSessionReadError('');}
      }
      return rowRef.current?.id === sessionId ? rowRef.current : row;
    } catch(failure) {
      if(!signal?.aborted&&alive.current&&currentSessionId.current===sessionId&&sequence>=readOutcomeSequence.current){
        readOutcomeSequence.current=sequence;setSessionReadError(errorText(failure));
      }
      throw new SessionReadFailure(failure);
    }
  }, [sessionId, accept]);
  const reload = useCallback(async (signal?: AbortSignal,quiet=false) => {
    const row = await readSession(signal,quiet);
    if (signal?.aborted || !alive.current || currentSessionId.current !== sessionId) return row;
    const generation=auxiliaryGeneration.current,request=++auxiliaryRequest.current;
    void Promise.all([quiet?meetingSessions.enhancements(sessionId,signal,true):meetingSessions.enhancements(sessionId,signal),quiet?meetingSessions.liveAnswers(sessionId,signal,true):meetingSessions.liveAnswers(sessionId,signal)])
      .then(([enhanced,answers])=>{if(!signal?.aborted&&alive.current&&generation===auxiliaryGeneration.current&&request===auxiliaryRequest.current){
        setSuggestions(enhanced.items);setLiveAnswers(answers.items);setAutomatic(enhanced.automatic||null);setQuestionProgress({sessionId,status:answers.automatic??null});setAutomaticReadError('');setAutomaticLoaded(true);}})
      .catch(failure=>{if(!signal?.aborted&&alive.current&&currentSessionId.current===sessionId&&generation===auxiliaryGeneration.current&&request===auxiliaryRequest.current){setAutomaticReadError(errorText(failure));}});
    return row;
  }, [sessionId, readSession,assistantReady]);
  useEffect(() => {
    alive.current = true;
    void readSession().catch(() => undefined);
    return () => {alive.current = false;};
  }, [sessionId, readSession]);
  useEffect(() => {
    if(!active)return;
    const timer = setInterval(() => {if (!document.hidden) void reload(undefined,true).catch(() => undefined);}, 5000);
    return () => clearInterval(timer);
  }, [reload,active]);
  useEffect(()=>{
    if(!active||typeof meetingSessions.watchEvents!=='function')return;
    let disposed=false,controller:AbortController|null=null,reading=false,queued=false,cursor=0;
    let retry:ReturnType<typeof setTimeout>|undefined;
    const refresh=async()=>{
      if(reading||disposed||document.hidden||!controller||controller.signal.aborted)return;
      reading=true;
      const current=controller;
      try{
        while(queued&&!disposed&&!document.hidden&&!current.signal.aborted){
          queued=false;
          const row=await reload(current.signal,true);
          if((row.event_cursor??0)<cursor){queued=true;break;}
        }
      }catch{/* The canonical polling fallback remains available; retain this wake-up. */queued=true;}
      finally{
        reading=false;
        if(queued&&!disposed&&!document.hidden&&controller&&!controller.signal.aborted){
          retry=setTimeout(()=>{retry=undefined;void refresh();},500);
        }
      }
    };
    const requestRefresh=()=>{queued=true;if(retry)clearTimeout(retry);retry=undefined;void refresh();};
    const visible=()=>{
      if(disposed)return;
      controller?.abort();controller=null;
      if(retry)clearTimeout(retry);retry=undefined;
      if(document.hidden)return;
      const current=new AbortController();controller=current;
      cursor=Math.max(cursor,rowRef.current?.id===sessionId?rowRef.current.event_cursor??0:0);
      void meetingSessions.watchEvents(sessionId,{
        after:cursor,signal:current.signal,
        onConnected:()=>{if(!disposed&&controller===current&&!current.signal.aborted){setEventReadError('');requestRefresh();}},
        onEvent:event=>{
          if(disposed||controller!==current||current.signal.aborted||event.id<=cursor)return;
          cursor=event.id;
          const known=rowRef.current?.id===sessionId?rowRef.current.event_cursor??0:0;
          if(event.id>known)requestRefresh();
        },
        onError:failure=>{
          if(!disposed&&controller===current&&!current.signal.aborted&&!failure.retryable){
            setEventReadError(failure.message);current.abort();
          }
        },
      }).catch(()=>{/* The five-second snapshot fallback also supports older servers. */});
    };
    visible();
    document.addEventListener('visibilitychange',visible);
    return()=>{disposed=true;controller?.abort();if(retry)clearTimeout(retry);document.removeEventListener('visibilitychange',visible);};
  },[active,sessionId,reload]);
  useEffect(()=>{
    const controller=new AbortController(),generation=auxiliaryGeneration.current,request=++auxiliaryRequest.current;
    void Promise.all([meetingSessions.enhancements(sessionId,controller.signal),meetingSessions.liveAnswers(sessionId,controller.signal)])
      .then(([enhanced,answers])=>{if(!controller.signal.aborted&&alive.current&&currentSessionId.current===sessionId&&generation===auxiliaryGeneration.current&&request===auxiliaryRequest.current){
        setSuggestions(enhanced.items);setLiveAnswers(answers.items);setAutomatic(enhanced.automatic||null);setQuestionProgress({sessionId,status:answers.automatic??null});setAutomaticReadError('');setAutomaticLoaded(true);}})
      .catch(failure=>{if(!controller.signal.aborted&&alive.current&&currentSessionId.current===sessionId&&generation===auxiliaryGeneration.current&&request===auxiliaryRequest.current){setAutomaticReadError(errorText(failure));}});
    return()=>controller.abort();
  },[sessionId,assistantReady]);
  useEffect(()=>{
    if(!active||!session)return;
    const controller=new AbortController(),key=contextKey,request=++historyReadSequence.current;
    setHistoryError('');setConversation({key,items:[]});
    try{localStorage.setItem(contextStorageKey(sessionId),JSON.stringify({scope,sourceIds:selectedSources}));}catch{/* The server remains the history authority. */}
    if(scope==='sources'&&!selectedSources.length){setHistoryLoading(false);return()=>controller.abort();}
    setHistoryLoading(true);
    void meetingSessions.askHistory(sessionId,scope,scope==='sources'?selectedSources:[],controller.signal).then(value=>{
      if(!controller.signal.aborted&&currentContext.current===key&&request===historyReadSequence.current)setConversation({key,items:value.items.map(result=>({query:result.query||'',scope,result}))});
    }).catch(failure=>{if(!controller.signal.aborted&&currentContext.current===key&&request===historyReadSequence.current)setHistoryError(errorText(failure));})
      .finally(()=>{if(!controller.signal.aborted&&currentContext.current===key&&request===historyReadSequence.current)setHistoryLoading(false);});
    return()=>controller.abort();
  },[sessionId,scope,sourceKey,session?.project_id,session?.brain_project_id,!!session,active,historyTick]);
  const hasConversation=conversation.key===contextKey&&conversation.items.length>0;
  useEffect(()=>{
    if(!active||tab!=='chat'||!['assistant','complete'].includes(layout)||!hasConversation||historyLoading)return;
    const controller=new AbortController(),key=contextKey;let inFlight=false;
    const refresh=async()=>{
      if(inFlight)return;inFlight=true;const request=++historyReadSequence.current;
      try{
        const value=await meetingSessions.askHistory(sessionId,scope,scope==='sources'?selectedSources:[],controller.signal,true);
        if(!controller.signal.aborted&&currentContext.current===key&&request===historyReadSequence.current){
          setConversation({key,items:value.items.map(result=>({query:result.query||'',scope,result}))});setHistoryError('');
        }
      }catch(failure){
        if(!controller.signal.aborted&&currentContext.current===key&&request===historyReadSequence.current){
          setConversation({key,items:[]});setHistoryError(errorText(failure));
        }
      }finally{inFlight=false;}
    };
    const timer=setInterval(()=>void refresh(),3000);
    return()=>{controller.abort();clearInterval(timer);};
  },[active,tab,layout,hasConversation,historyLoading,sessionId,scope,sourceKey,contextKey]);
  useEffect(()=>{
    if(scope!=='sources'){setSourceReadError('');return;}const controller=new AbortController();const timer=setTimeout(()=>{
      void fusionSources.list({query:sourceSearch,limit:50},controller.signal).then(page=>{if(!controller.signal.aborted){setSources(page.items.filter(item=>!!item.source_id));setSourceReadError('');}})
        .catch(failure=>{if(!controller.signal.aborted)setSourceReadError(errorText(failure));});
    },200);return()=>{clearTimeout(timer);controller.abort();};
  },[scope,sourceSearch]);
  useEffect(() => {
    const protect = (event: BeforeUnloadEvent) => {if (dirtyRef.current || markdownDraft.pending || captureBusy) {event.preventDefault(); event.returnValue = '';}};
    window.addEventListener('beforeunload', protect); return () => window.removeEventListener('beforeunload', protect);
  }, [captureBusy, markdownDraft.pending]);
  useEffect(() => {try {localStorage.setItem('agent-meeting-layout-v2', layout);} catch {/* current layout remains available */}}, [layout]);
  useLayoutEffect(()=>{
    // A wrapped context pane can sit below the notes in its scroll container.
    // Reveal it when switching views, without moving a reader on transcript updates.
    if(active&&(layout==='assistant'||layout==='complete'))
      assistantPane.current?.scrollIntoView?.({block:'nearest',inline:'nearest'});
  },[active,layout,tab,!!session]);
  useLayoutEffect(() => {
    const root=studioRoot.current;if(!root)return;
    const desktop=typeof window.matchMedia==='function'?window.matchMedia('(min-width:671px)'):null;
    const size=()=>{
      if(desktop?!desktop.matches:window.innerWidth<=670){root.style.removeProperty('--meeting-studio-height');return;}
      const top=root.getBoundingClientRect().top+window.scrollY;
      const main=root.closest('.workspace-main');
      const padding=main?Number.parseFloat(window.getComputedStyle(main).paddingBottom):8;
      const height=`${Math.max(0,Math.floor(window.innerHeight-Math.max(0,top)-(Number.isFinite(padding)?padding:8)))}px`;
      if(root.style.getPropertyValue('--meeting-studio-height')!==height)root.style.setProperty('--meeting-studio-height',height);
    };
    size();window.addEventListener('resize',size);desktop?.addEventListener?.('change',size);
    const main=root.closest('.workspace-main');
    const observer=typeof ResizeObserver==='undefined'?null:new ResizeObserver(size);observer?.observe(root);if(main)observer?.observe(main);
    const mutations=main&&typeof MutationObserver!=='undefined'?new MutationObserver(size):null;
    if(main)mutations?.observe(main,{childList:true,subtree:true,characterData:true});
    return()=>{window.removeEventListener('resize',size);desktop?.removeEventListener?.('change',size);observer?.disconnect();mutations?.disconnect();root.style.removeProperty('--meeting-studio-height');};
  },[layout,!!session]);
  const persistDraft = (nextContent: NoteContent, nextTitle: string, command = pendingNote.current) => {
    const row = rowRef.current;
    try {localStorage.setItem(draftKey(sessionId), JSON.stringify({session_id: sessionId, content: nextContent, title: nextTitle,
      revision: row?.revision, note_version_id: row?.note_version_id, command})); return true;}
    catch {setError('Brouillon non conservé sur cet appareil. Enregistrez la note avant de quitter.'); return false;}
  };
  const edit = (next: NoteContent, title = noteTitle) => {
    draftRef.current = {content: next, title};
    dirtyRef.current = true; setDirty(true); setContent(next); setNoteTitle(title);
    const persisted = persistDraft(next, title); setNotice(persisted ? 'Brouillon conservé sur cet appareil' : ''); return persisted;
  };
  const run = async (label: string, task: () => Promise<void>) => {
    if (operation) return; setOperation(label); setError('');
    const finish=beginActivity(label);
    try {await task();} catch (failure) {if (alive.current&&!(failure instanceof SessionReadFailure)) setError(errorText(failure));} finally {finish();if (alive.current) setOperation('');}
  };
  const save = async () => {
    if (markdownDraft.pending) return;
    const row = rowRef.current; if (!row || !validNoteContent(content) || !noteTitle.trim()) return;
    const sent = {title: noteTitle.trim(), content};
    const command = pendingNote.current ?? {...sessionCommand(row.revision), ...sent,
      ...(row.note_id ? {expected_note_revision: row.note_revision ?? row.note?.revision,
        expected_note_version_id: row.note_version_id ?? row.note?.version_id} : {})};
    pendingNote.current = command; persistDraft(content, noteTitle, command);
    let result: MeetingSession;
    try {result = await meetingSessions.saveNote(sessionId, command);}
    catch (failure) {
      try {
        const remote = await reload();
        if (remote.revision !== command.expected_revision || (remote.note_id && remote.note_revision !== command.expected_note_revision)) setNoteConflict(true);
      } catch {/* the frozen command and draft remain recoverable when offline */}
      throw failure;
    }
    if (!alive.current || currentSessionId.current !== sessionId) return;
    pendingNote.current = null;
    // A retry acknowledges its frozen payload; any newer typing remains a local draft.
    const live = draftRef.current;
    const current = JSON.stringify(command.content) === JSON.stringify(live.content) && command.title === live.title.trim();
    const latest = rowRef.current;
    const latestNote = latest && noteFrom(latest), resultNote = noteFrom(result);
    const latestNoteRevision = latest?.note_revision ?? latestNote?.revision;
    const resultNoteRevision = result.note_revision ?? resultNote?.revision;
    const latestNoteVersion = latest?.note_version_id ?? latestNote?.version_id;
    const resultNoteVersion = result.note_version_id ?? resultNote?.version_id;
    const newerNote = !!(latest?.id === result.id && (
      (latestNoteRevision !== undefined && resultNoteRevision !== undefined && latestNoteRevision > resultNoteRevision) ||
      (latestNoteVersion && resultNoteVersion && latestNoteVersion !== resultNoteVersion &&
        (latest.revision > result.revision || (latest.event_cursor !== undefined && result.event_cursor !== undefined && latest.event_cursor > result.event_cursor)))));
    if (current && !newerNote) {
      dirtyRef.current = false; setDirty(false); setRecovered(false); setNoteConflict(false); localStorage.removeItem(draftKey(sessionId));
    }
    accept(result); setNoteConflict(newerNote);
    if (!current || newerNote) persistDraft(live.content, live.title, null);
    onChanged?.(); setNotice(newerNote ? 'La commande a été enregistrée, mais une version de note plus récente existe. Votre texte reste en brouillon à comparer.'
      : current ? `Note enregistrée · version ${result.note_revision ?? resultNote?.revision ?? result.revision}`
      : 'Commande précédente enregistrée. Les nouvelles corrections restent à enregistrer.');
  };
  const leave = (action:()=>void) => {
    if (markdownDraft.pending) {
      if (!window.confirm('Un brouillon Markdown reste à appliquer à la note. Revenir à la liste ?')) return;
    } else {
      if(studioRoot.current?.querySelector('[data-workspace-dirty="true"]')&&!window.confirm('Une relecture ou une correction de transcription reste à enregistrer. Quitter la séance en perdant cette correction ?'))return;
      if (dirty && !window.confirm('La note est conservée en brouillon sur cet appareil. Revenir à la liste ?')) return;
    }
    action();
  };
  const close = () => leave(onClose);
  const assign = () => void run('Rattachement', async () => {
    if (markdownDraft.pending) return;
    const row = await reload(); if (!project) return;
    const result = await meetingSessions.assign(sessionId, {...sessionCommand(row.revision), project_id: project});
    accept(result); onChanged?.(); setNotice('Séance rattachée au projet.');
  });
  const start = () => void run('Démarrage', async () => {
    await meetingCapture.start(sessionId, {system: systemAudio, deviceId:browserMicrophone||undefined, maxBytes: (capabilities.capture.max_capture_mb ?? capabilities.capture.max_upload_mb) * 1024 * 1024,
      maxMinutes: capabilities.capture.max_duration_minutes}); await reload(); setLayout('assistant'); setTab('transcript');
  });
  const importAudio = async (file: File) => {
    if (file.size > capabilities.capture.max_upload_mb * 1024 * 1024) throw new Error(`L’audio dépasse ${capabilities.capture.max_upload_mb} Mo.`);
    const row = await reload(); const form = new FormData(); const hash = await crypto.subtle.digest('SHA-256', await file.arrayBuffer());
    form.append('file', file); form.append('command_id', crypto.randomUUID());
    form.append('sha256', Array.from(new Uint8Array(hash), byte => byte.toString(16).padStart(2, '0')).join(''));
    form.append('start_ms', '0'); form.append('duration_ms', '0');
    const receipt = await meetingSessions.chunk(row.id, 'mic', 0, form);
    if (!receipt.acknowledged || receipt.session_id !== row.id || receipt.accepted_chunk?.size_bytes !== file.size ||
      receipt.accepted_chunk.sha256 !== form.get('sha256')) throw new Error('L’acquittement de l’audio importé ne correspond pas au fichier.');
    const latest = await meetingSessions.get(row.id); accept(await meetingSessions.command(row.id, 'finalize', sessionCommand(latest.revision)));
    onChanged?.();
  };
  const ask = (questions = false) => void run(questions ? 'Recherche de réponse' : 'Recherche et rédaction', async () => {
    if (!query.trim()) return;
    const text = query.trim(),key=contextKey,generation=contextGeneration.current; const row = await reload();
    if(currentContext.current!==key||contextGeneration.current!==generation)throw new Error('Le périmètre a changé. Relancez la question dans le contexte affiché.');
    const history=replies.filter(reply=>reply.scope===scope).slice(-6).flatMap(reply=>[
      {role:'user' as const,content:reply.query.slice(0,4000)},{role:'assistant' as const,content:reply.result.answer.slice(0,4000)}]);
    while(history.reduce((total,item)=>total+item.content.length,0)>12000)history.splice(0,2);
    const result = questions ? await meetingSessions.liveAnswer(sessionId, text, row.revision) : await meetingSessions.ask(sessionId, {
      query: text, scope, source_ids: scope==='sources'?selectedSources:[],
      history,
    });
    if(!alive.current)return;
    if(currentContext.current!==key||contextGeneration.current!==generation)throw new Error('La réponse est conservée dans son contexte d’origine. Le périmètre affiché a changé ; elle n’y sera pas ajoutée.');
    if (questions) setLiveAnswers(previous => [...previous.filter(item=>!result.id||item.id!==result.id),{...result,pinned:result.pinned??previous.find(item=>item.id===result.id)?.pinned??false}]);
    else {
      // A history read begun before this answer cannot remove the new result.
      historyReadSequence.current++;
      setConversation(previous=>({key,items:[...(previous.key===key?previous.items:[]).filter(item=>!result.id||item.result.id!==result.id),{query:text,scope,result}]}));
    }
    setQuery(previous=>previous.trim()===text?'':previous);
  });
  const pin=(reply:SessionAnswer)=>void run('Épinglage de la réponse',async()=>{
    if(!reply.id)return;auxiliaryGeneration.current++;
    const result=await meetingSessions.pinAnswer(sessionId,reply.id,!reply.pinned);
    auxiliaryGeneration.current++;
    if(alive.current)setLiveAnswers(previous=>previous.map(item=>item.id===result.id?{...item,pinned:result.pinned}:item));
  });
  const rate=(reply:SessionAnswer,kind:'ask'|'live',useful:boolean|null)=>void run('Enregistrement de l’avis',async()=>{
    if(!reply.id)return;
    const key=currentContext.current;
    historyReadSequence.current++;auxiliaryGeneration.current++;
    const result=await meetingSessions.rateAnswer(sessionId,kind,reply.id,useful);
    historyReadSequence.current++;auxiliaryGeneration.current++;
    if(!alive.current||currentSessionId.current!==sessionId)return;
    if(kind==='live')setLiveAnswers(previous=>previous.map(item=>item.id===result.id?{...item,useful:result.useful}:item));
    else if(currentContext.current===key)setConversation(previous=>previous.key===key?{...previous,
      items:previous.items.map(item=>item.result.id===result.id?{...item,result:{...item.result,useful:result.useful}}:item)}:previous);
  });
  const enhance = () => void run('Amélioration des notes', async () => {
    if (markdownDraft.pending) return;
    if (dirtyRef.current) await save();
    if (dirtyRef.current) throw new Error('De nouvelles corrections restent à enregistrer. Enregistrez-les avant de relancer l’amélioration.');
    auxiliaryGeneration.current++;
    const row = await reload(); const result = await meetingSessions.enhance(sessionId, row.revision);
    auxiliaryGeneration.current++;
    setSuggestions(previous => [result, ...previous.filter(item => item.id !== result.id)]);
  });
  const decision = (suggestion: SessionSuggestion, value: 'accept' | 'reject') => void run('Décision', async () => {
    if (value === 'accept' && markdownDraft.pending) return;
    const row = await reload(); const result = await meetingSessions.decide(sessionId, suggestion.id, value, row.revision);
    accept(result); setSuggestions(previous => previous.map(item => item.id === suggestion.id ? {...item, status: value === 'accept' ? 'accepted' : 'rejected'} : item));
    onChanged?.();
  });
  if (!session) return <section className="meeting-studio"><button type="button" onClick={onClose}>Retour aux réunions</button>
    {error || sessionReadError ? <p role="alert">{error || sessionReadError}</p> : <p role="status">Ouverture de la séance…</p>}</section>;
  const title = rows.find(row => row.id === session.project_id);
  const projectAssistant = session.project_id ? projectConversationHref(session.project_id) : null;
  const frozen = session.state === 'cancelled';
  const version=noteFrom(session)?.version_id||session.note_version_id;
  const automaticState=automatic?.enabled&&automatic.note_version_id&&version&&automatic.note_version_id!==version&&
    ['running','completed'].includes(automatic.state)?'obsolete':automatic?.state||'disabled';
  const hasAdditions=(suggestion:SessionSuggestion)=>suggestion.content
    ? suggestion.content.blocks.length>0 : !!(suggestion.text||suggestion.answer||'').trim();
  const automaticProposal=suggestions.find(suggestion=>suggestion.note_version_id===automatic?.note_version_id&&['pending','prepared'].includes(suggestion.status));
  const automaticEmpty=automaticState==='completed'&&!!automaticProposal&&!hasAdditions(automaticProposal);
  const automaticLabels={disabled:'Désactivé',waiting:automatic?.retry_after_seconds!==undefined?'En attente du moteur IA':'En attente de stabilité',running:'Génération en cours',failed:'Tentative à reprendre',
    completed:automaticEmpty?'Aucun ajout utile':'Proposition disponible',obsolete:'Proposition à régénérer',stopped:'Arrêté'};
  const visibleSuggestions=suggestions.map(suggestion=>suggestion.note_version_id&&version&&suggestion.note_version_id!==version&&
    !['accepted','rejected'].includes(suggestion.status)?{...suggestion,status:'obsolete'}:suggestion);
  const suggestionCard=(suggestion:typeof visibleSuggestions[number])=><article className="meeting-suggestion" key={suggestion.id}><p className="meeting-studio-eyebrow">{hasAdditions(suggestion)||!['pending','prepared'].includes(suggestion.status)?({obsolete:'Ancienne analyse',accepted:'Acceptée',rejected:'Écartée',failed:'Analyse en échec',running:'Analyse en cours',prepared:'À relire',pending:'À vérifier'} as Record<string,string>)[suggestion.status]||suggestion.status:'Analyse terminée'} · révision {suggestion.revision ?? 'non précisée'}</p>
          {suggestion.note_revision!=null&&<p>Version de note analysée : {suggestion.note_revision}.</p>}
          {!hasAdditions(suggestion)?<p role="status">{suggestion.status==='obsolete'?'Cette analyse sans ajout concerne un ancien contexte de la séance.':'Aucun ajout utile à proposer pour cette note.'}</p>:<>
            {suggestion.content ? <NoteContentView content={suggestion.content} projectId={session.project_id || ''} noteId={session.note_id || ''} /> : <ChatMarkdown text={suggestion.text || suggestion.answer || ''} />}
            <CitationList citations={suggestion.citations || []} onOpenSource={onOpenSource}/>
            <button type="button" disabled={!!operation || dirty || markdownDraft.pending || ['accepted', 'rejected', 'obsolete'].includes(suggestion.status)} onClick={() => decision(suggestion, 'accept')}>Accepter comme nouvelle version</button>
            <button type="button" disabled={!!operation || ['accepted', 'rejected'].includes(suggestion.status)} onClick={() => decision(suggestion, 'reject')}>Écarter</button>
          </>}</article>;
  const nativeAudioContext=<>
      {(capabilities.native_capture||hasDesktopCapture())&&<NativeMeetingCapture session={session} capabilities={capabilities.native_capture} onChanged={row=>{if(row.state==='recording'&&rowRef.current?.state!=='recording'){setLayout('assistant');setTab('transcript');}accept(row);}} onAvailability={setNativeBusy} onRecoveryControls={setNativeRecoveryControls} browserBusy={!['idle','completed','error'].includes(capture.phase)}/>}
      {session.transcription_admission?.suspended&&<p className="meeting-studio-notice" role="status">
        {sessionCaptureNotice(session)}{' '}
        {session.state==='completed'?'La transcription directe a été suspendue.':'La transcription directe est suspendue.'}{' '}
        {admittedDirect?'Les derniers passages en attente sont encore traités.':'Les passages restants sont conservés pour une transcription ultérieure.'}{' '}
        Reprenez un petit lot ou demandez le traitement complet après la réunion, si le moteur est installé.</p>}
  </>;
  const tabs = [['chat','Discussion'],['summary','Compte rendu'],['transcript','Transcription'],['questions','Questions en direct']] as const;
  const closePreparation=()=>{if(preparation.current){preparation.current.open=false;preparationSummary.current?.focus();}};
  return <section ref={studioRoot} data-focused-panel={layout==='assistant'&&(tab==='summary'||tab==='transcript')?'true':undefined} className={`meeting-studio${layout==='complete'?' meeting-studio-complete':''}`} aria-label={`Séance ${session.title}`} data-workspace-dirty={dirty || markdownDraft.pending ? 'true' : undefined}>
    <header className="meeting-studio-heading">
      <button type="button" className="meeting-studio-back" onClick={close} aria-label="Retour aux réunions">←</button>
      <div className="meeting-studio-title"><h1 title={session.title}>{session.title}</h1><p>{session.date} · {sessionStateLabel(session)}</p></div>
      <nav className="meeting-view-actions" aria-label="Outils de la séance">
        <button type="button" aria-pressed={layout==='editor'} onClick={()=>setLayout('editor')}>Notes</button>
        <button type="button" aria-pressed={layout==='enhanced'||layout==='complete'} onClick={()=>setLayout(layout==='enhanced'?'editor':'enhanced')}>Notes enrichies</button>
        <button type="button" aria-pressed={layout==='assistant'&&tab==='transcript'} onClick={()=>{setLayout('assistant');setTab('transcript');}}>Transcription{session.segments?.length?` · ${session.segments.length}`:''}</button>
        <button type="button" aria-pressed={layout==='assistant'&&tab==='summary'} onClick={()=>{setLayout('assistant');setTab('summary');}}>Compte rendu</button>
        <button type="button" aria-pressed={layout==='assistant'&&tab==='chat'} onClick={()=>{setLayout('assistant');setTab('chat');}}>Assistant</button>
      </nav>
      <div className="meeting-audio-pill" aria-label="État de l’audio"><span className={captureHere && capture.phase === 'recording' ? 'meeting-recording-dot' : ''}>●</span>
        <strong>{!captureHere&&session.chunks?.some(chunk=>chunk.duration_ms===0)?'Durée inconnue':clock(captureHere ? capture.seconds : session.duration_seconds)}</strong>
        {captureHere && capture.phase === 'recording' && <button type="button" disabled={!!operation} onClick={() => void run('Pause', () => meetingCapture.pause())} aria-label="Mettre l’enregistrement en pause">Ⅱ</button>}
        {captureHere && capture.phase === 'paused' && <button type="button" disabled={!!operation} onClick={() => void run('Reprise', () => meetingCapture.resume())}>Reprendre</button>}
        {captureHere && ['recording', 'paused'].includes(capture.phase) && <button type="button" disabled={!!operation} onClick={() => void run('Conservation', async () => {await meetingCapture.stop(); await reload(); onChanged?.();})}>Arrêter</button>}
      </div>
      {session.kind==='note'&&session.state==='created'&&<button type="button" className="meeting-end-note" aria-label="Terminer la prise de notes"
        disabled={!!operation||dirty||markdownDraft.pending||captureBusy||nativeBusy||nativeRecoveryControls}
        onClick={()=>void run('Conservation de la séance',async()=>{
          const row=await reload();accept(await meetingSessions.command(sessionId,'finalize',sessionCommand(row.revision)));
          setLayout('assistant');setTab('summary');onChanged?.();
        })}>Terminer</button>}
      <details ref={preparation} className="meeting-preparation" onKeyDown={event=>{if(event.key==='Escape'){event.preventDefault();event.stopPropagation();closePreparation();}}}>
      <summary ref={preparationSummary} aria-label="Préparation">Options</summary>
      <div className="meeting-studio-setup" role="region" aria-label="Commandes et état de la séance" tabIndex={0}>
      {navigation}
      <p className="meeting-studio-eyebrow">{title ? `${title.code} · ${title.title}` : 'Séance à rattacher'}</p>
      <button type="button" className="meeting-preparation-close" onClick={closePreparation}>Fermer la préparation</button>
    <div className="meeting-studio-controls">
      <label>Disposition<select value={layout} onChange={event => setLayout(event.target.value as typeof layout)}>
        <option value="editor">Notes · pleine page</option><option value="enhanced">Notes personnelles et enrichies</option><option value="assistant">Notes et assistant</option>
        <option value="complete">Notes, enrichissement et assistant</option></select></label>
      {!session.project_id && <><label>Projet de la séance<select aria-label="Projet de la séance" value={project} onChange={event => setProject(event.target.value)}>
        <option value="">À choisir</option>{rows.map(row => <option key={row.id} value={row.id}>{row.code} — {row.title}</option>)}</select></label>
        <button type="button" disabled={!project || !!operation || dirty || markdownDraft.pending} onClick={assign}>Rattacher au projet</button></>}
      {session.project_id && <button type="button" onClick={() => onOpenProject(session.project_id!, 'reviews')}>Réunions du projet</button>}
      <AsyncDownloadLink className="meeting-export" href={sessionExportUrl(sessionId)} activityLabel="Préparation de l’archive de la séance…" filename="seance-agent.zip">Exporter et récupérer la séance</AsyncDownloadLink>
    </div>
    <MeetingCalendarContext session={session} onChanged={accept}/>
    <p className="meeting-capability" role="status">{capabilities.transcription.enabled === false ? 'Transcription en direct désactivée.'
      : capabilities.transcription.live_ready ? 'Transcription en direct disponible.' : capabilities.transcription.live_operational
      ? 'Direct en essai, non qualifié. Relecture nécessaire.'
      : capabilities.transcription.enabled === true && capabilities.transcription.installed === true
      ? 'Direct activé en essai, non qualifié. Relecture nécessaire.' : 'Transcription en direct indisponible.'}
      {capabilities.transcription.batch_ready&&' Transcription de l’audio conservé disponible.'}
      {capabilities.transcription.detail&&` ${capabilities.transcription.detail}`}</p>
    <section className="meeting-capability" aria-label="État de l’enrichissement automatique">
      <p role="status">{automaticLoaded?`Enrichissement automatique : ${automaticLabels[automaticState]}.`:'Lecture de l’état de l’enrichissement automatique…'}</p>
      {automatic?.detail&&<p>{automaticEmpty?'Les notes existantes sont conservées.':automatic.detail}</p>}
      {automatic?.enabled&&<p>Seules les versions enregistrées sont analysées. Les propositions nécessitent votre acceptation.</p>}
    </section>
    </div>
      </details>
      {!captureBusy && !session.recording_id && (['created','interrupted'].includes(session.state)||(session.state==='paused'&&!session.chunks?.length)) && <details className="meeting-browser-setup" open={!capabilities.native_capture?.installed}>
        <summary>{capabilities.native_capture?.installed?'Autre audio':'Audio : navigateur ou fichier'}</summary>
        <div className="meeting-studio-controls">
          <label>Microphone du navigateur<select value={browserMicrophone} disabled={!!operation||nativeBusy||browserCaptureUnavailable} onChange={event=>setBrowserMicrophone(event.target.value)}>
            <option value="">Microphone par défaut</option>{browserDevices.map((device,index)=><option key={device.deviceId} value={device.deviceId}>{device.label||`Microphone ${index+1} (nom visible après autorisation)`}</option>)}</select></label>
          <button className="meeting-start" type="button" disabled={!!operation || nativeBusy || browserCaptureUnavailable || !capabilities.enabled} onClick={start}>{systemAudio?'Préparer le partage audio':capabilities.native_capture?.installed?'Enregistrer au microphone (navigateur)':'Démarrer la réunion au microphone'}</button>
          <label className="meeting-file-choice">Importer un audio<input type="file" accept="audio/*,.m4a,.opus,.mp4,.webm" disabled={!!operation||nativeBusy}
            onChange={event => {const file = event.target.files?.[0]; if (file) void run('Import et conservation de l’audio', () => importAudio(file)); event.target.value = '';}} /></label>
          <label className="meeting-system-choice"><input type="checkbox" checked={systemAudio} disabled={!!operation||nativeBusy||browserCaptureUnavailable} onChange={event => setSystemAudio(event.target.checked)} />Partager aussi l’audio système</label>
        </div>
        <p>Au démarrage, autorisez le microphone. Pour le son du PC, sélectionnez aussi la fenêtre et son audio.</p>
        {browserDevicesError&&<p role="status">{browserDevicesError}</p>}
      </details>}
      {session.state==='completed'&&!nativeRecoveryControls?<details className="meeting-audio-context"><summary>Audio conservé · état et transcription</summary>{nativeAudioContext}</details>:nativeAudioContext}

    </header>
    <div className="meeting-studio-status">
      {captureHere && capture.phase === 'starting' && <button type="button" onClick={() => void meetingCapture.stop()}>Annuler le démarrage audio</button>}
      {captureHere && capture.phase === 'ready' && <section aria-label="Confirmer le partage audio">
        <p>Choisissez la fenêtre ou l’onglet et cochez son audio. L’enregistrement commencera après votre choix.</p>
        <button type="button" disabled={!!operation} onClick={() => void run('Partage audio', async () => {accept(await meetingCapture.activatePrepared());})}>Choisir l’audio du PC et démarrer</button>
        <button type="button" disabled={!!operation} onClick={() => void run('Annulation', async () => {await meetingCapture.cancelPrepared(); await reload();})}>Annuler la préparation audio</button>
      </section>}
      {(error || (captureHere && capture.error)) && <p className="meeting-studio-error" role="alert">{error || capture.error}</p>}
      {sessionReadError&&<p className="meeting-studio-error" role="alert">Lecture de la séance indisponible : {sessionReadError}</p>}
      {eventReadError&&<p className="meeting-studio-error" role="alert">{eventReadError}</p>}
      {sourceReadError&&<p className="meeting-studio-error" role="alert">Lecture des sources indisponible : {sourceReadError}</p>}
      {(notice || operation) && <p className="meeting-studio-notice" role="status">{operation ? `${operation}…` : notice}</p>}
        {markdownDraft.pending && <p role="status">{markdownDraft.valid
          ? 'Brouillon Markdown à appliquer avant d’enregistrer, d’améliorer ou de publier la note.'
          : 'Brouillon Markdown invalide : corrigez-le et appliquez-le avant d’enregistrer, d’améliorer ou de publier la note.'}</p>}
      {session.issues?.length > 0 && <p className="meeting-studio-notice">{session.issues.join(' · ')}</p>}
      {automatic?.error&&<p role="alert">{automatic.error}</p>}
      {automaticReadError&&<p role="alert">Lecture des données de séance indisponible : {automaticReadError}</p>}
      {['recording','paused','interrupted','finalizing'].includes(session.state)&&!nativeBusy&&!nativeRecoveryControls&&(!captureHere||capture.phase==='error')&&<button type="button" disabled={!!operation} onClick={()=>void run('Consolidation de la séance',async()=>{
        const row=await reload();accept(await meetingSessions.command(sessionId,'finalize',sessionCommand(row.revision)));onChanged?.();
      })}>Conserver les fragments reçus et finaliser</button>}
      {captureHere && capture.phase === 'pending' && <button type="button" disabled={!!operation} onClick={() => void run('Récupération', async () => {
        await meetingCapture.retryAndFinalize(); await reload(); onChanged?.();
      })}>Synchroniser les fragments conservés</button>}
    </div>
    <div className={`meeting-studio-body${sessionList&&onSelectSession?' meeting-with-index':''}`}>
      {sessionList&&onSelectSession&&<aside className="meeting-note-index" aria-label="Notes et séances">
        <label><span className="meeting-visually-hidden">Rechercher une note</span><input type="search" placeholder="Rechercher une note…" value={noteSearch} onChange={event=>setNoteSearch(event.target.value)}/></label>
        {onNewSession&&<button className="meeting-new-note" type="button" onClick={()=>leave(onNewSession)}>＋ Nouvelle note</button>}
        <small>{sessionList.length} séance{sessionList.length>1?'s':''}</small>
        <ul>{sessionList.map(item=>item.id===session.id?session:item).filter(item=>(item.id===sessionId?noteTitle||item.title:item.title).toLocaleLowerCase('fr').includes(noteSearch.toLocaleLowerCase('fr'))).map(item=><li key={item.id}>
          <button type="button" aria-current={item.id===sessionId?'page':undefined} onClick={()=>{if(item.id!==sessionId)leave(()=>onSelectSession(item.id));}}>
            <strong>{item.id===sessionId?noteTitle||item.title:item.title}</strong><small>{item.date} · {sessionStateLabel(item)}</small>
          </button></li>)}</ul>
      </aside>}
    <div className={`meeting-studio-panes meeting-layout-${layout}`}>
      <div className="meeting-notes-stack" hidden={layout==='assistant'&&(tab==='summary'||tab==='transcript')}>
      <section className="meeting-notes-pane" aria-label="Notes personnelles" tabIndex={0}>
        <header className="meeting-document-heading"><h2 className="meeting-visually-hidden">Notes personnelles</h2>
          <label className="meeting-note-title"><span className="meeting-visually-hidden">Titre de la note</span><input maxLength={255} value={noteTitle} readOnly={frozen} onChange={event => edit(content, event.target.value)} /></label>
          <span>{dirty ? 'Brouillon' : session.note_id ? `Version ${session.note_revision}` : 'À jour'}</span>
          <button className="meeting-save-note" type="button" disabled={!dirty || markdownDraft.pending || !noteTitle.trim() || !!operation || frozen || noteConflict || !validNoteContent(content)}
            onClick={() => void run('Enregistrement de la note', save)}>{pendingNote.current ? 'Reprendre l’enregistrement' : 'Enregistrer la note'}</button>
          <button type="button" onClick={() => {if(!navigator.clipboard){setError('Copie indisponible.');return;}void navigator.clipboard.writeText(textOf(content)).then(() => setNotice('Note copiée.')).catch(() => setError('Copie indisponible.'));}}>Copier</button>
        </header>
        {recovered && <p className="meeting-studio-notice">Brouillon retrouvé sur cet appareil ; votre saisie est conservée.</p>}
        {noteConflict && <div role="alert" className="meeting-note-conflict"><p>La version enregistrée a changé. Votre saisie est conservée.</p>
          {noteFrom(session) && <details><summary>Comparer la version enregistrée</summary>
            <NoteContentView content={noteFrom(session)!.content} projectId={session.project_id || ''} noteId={session.note_id || ''} />
          </details>}
          <button type="button" disabled={!!operation} onClick={() => {
            pendingNote.current = null; setNoteConflict(false); persistDraft(content, noteTitle, null);
            setNotice('Votre saisie reste conservée. Enregistrez-la explicitement sur la version actuellement affichée.');
          }}>Conserver ma saisie sur la version courante</button></div>}
        <NoteRichEditor content={content} onChange={next => edit(next)} projectId={session.project_id || ''} noteId={session.note_id || ''} disabled={frozen}
          draftId={sessionId} onMarkdownDraftState={setMarkdownDraft} />

        {automatic?.enabled&&(dirty||markdownDraft.pending)&&<p className="meeting-studio-notice">Vos modifications non enregistrées ne participent pas à l’analyse.</p>}
      </section>
      <section hidden={layout==='assistant'||layout==='editor'} className="meeting-enhanced-pane" aria-label="Notes enrichies" tabIndex={0}>
        <header><h2>Notes enrichies</h2><button type="button" disabled={!assistantReady || !!operation || noteConflict || markdownDraft.pending || frozen || !noteTitle.trim()} onClick={enhance}>Améliorer les notes</button></header>
        {!assistantReady && <p className="meeting-studio-notice">L’amélioration IA sera disponible après qualification du moteur. Vos notes restent enregistrables.</p>}
        {!suggestions.length && <div className="meeting-pane-empty"><span>✧</span><h3>Vos notes, enrichies par le contexte</h3><p>Une proposition conserve ses sources et sa version. Vous choisissez de l’accepter ou de garder vos notes.</p></div>}
        {visibleSuggestions.filter(suggestion=>suggestion.status!=='obsolete').map(suggestionCard)}
        {visibleSuggestions.some(suggestion=>suggestion.status==='obsolete')&&<details className="meeting-suggestion-history"><summary>Historique des analyses · {visibleSuggestions.filter(suggestion=>suggestion.status==='obsolete').length}</summary>{visibleSuggestions.filter(suggestion=>suggestion.status==='obsolete').map(suggestionCard)}</details>}
      </section>
      </div>
      <section ref={assistantPane} hidden={layout==='enhanced'||layout==='editor'} className="meeting-assistant-pane" aria-label="Assistant de la séance">
        <nav role="tablist" aria-label="Assistant de réunion">{tabs.map(([key, label],index) =>
          <button key={key} type="button" role="tab" tabIndex={tab===key?0:-1} id={`meeting-${sessionId}-${key}-tab`} aria-selected={tab === key} aria-controls={`meeting-${sessionId}-${key}-panel`} onClick={() => setTab(key)}
            onKeyDown={event=>{const next=event.key==='ArrowRight'?(index+1)%tabs.length:event.key==='ArrowLeft'?(index+tabs.length-1)%tabs.length:event.key==='Home'?0:event.key==='End'?tabs.length-1:null;
              if(next===null)return;event.preventDefault();setTab(tabs[next][0]);document.getElementById(`meeting-${sessionId}-${tabs[next][0]}-tab`)?.focus();}}>{label}</button>)}</nav>
        <div role="tabpanel" id={`meeting-${sessionId}-${tab}-panel`} aria-labelledby={`meeting-${sessionId}-${tab}-tab`} tabIndex={0}
          className={tab==='transcript'?'meeting-transcript-panel':undefined} ref={transcriptFollow.panelRef}
          onScroll={transcriptFollow.onScroll} onWheel={transcriptFollow.onWheel} onKeyDown={transcriptFollow.onKeyDown}
          onFocusCapture={transcriptFollow.onFocusCapture}>
          {(tab === 'chat' || tab === 'questions') && <>
            <>
              {tab === 'chat' && <label>Périmètre de la question<select value={scope} onChange={event => {setScope(event.target.value as SessionScope); clearReplies();}}>
                <option value="session">Cette séance</option><option value="project" disabled={!session.project_id}>Le projet</option><option value="sources">Sources choisies</option><option value="global">Tous les projets accessibles</option></select></label>}
              {scope === 'sources' && tab==='chat' && <fieldset className="meeting-source-picker"><legend>Sources de la question ({sourceIds.length} choisies)</legend>
                <label>Rechercher les sources<input type="search" value={sourceSearch} onChange={event=>setSourceSearch(event.target.value)}/></label>
                {sources.map(source=><label key={source.id}><input type="checkbox" checked={sourceIds.includes(source.id)} onChange={event=>{
                  setSourceIds(previous=>event.target.checked?[...previous,source.id]:previous.filter(id=>id!==source.id));clearReplies();
                }}/>{source.title} · {source.project_code||'Projet'}</label>)}
                <p>Les résultats respectent vos projets accessibles. Affinez la recherche si une source manque.</p></fieldset>}
              {tab==='questions'&&<MeetingQuestionProgress status={questionProgress?.sessionId===sessionId?questionProgress.status:null} readError={!!automaticReadError} manualAvailable={assistantReady}/>}
              <div className="meeting-chat-log" role="log" aria-label="Réponses de la séance">
                {(tab === 'chat' ? replies.map(reply => ({...reply.result, query: reply.query})) : [...liveAnswers].sort((a,b)=>Number(!!b.pinned)-Number(!!a.pinned))).map((reply, index) => <article key={reply.id || index}>
                  {'query' in reply && <h3>{String(reply.query)}</h3>}<ChatMarkdown text={reply.answer} /><CitationList citations={reply.citations || []} onOpenSource={onOpenSource}/>
                  {(reply.stale || reply.status === 'obsolete') && <p>Réponse fondée sur une ancienne version.</p>}
                  {reply.id&&<div role="group" aria-label="Utilité de cette réponse">
                    <button type="button" disabled={!!operation||frozen||session.note?.read_only} aria-pressed={reply.useful===true}
                      onClick={()=>rate(reply,tab==='questions'?'live':'ask',reply.useful===true?null:true)}>Utile</button>
                    <button type="button" disabled={!!operation||frozen||session.note?.read_only} aria-pressed={reply.useful===false}
                      onClick={()=>rate(reply,tab==='questions'?'live':'ask',reply.useful===false?null:false)}>Pas utile</button>
                    {reply.useful!=null&&<span> Avis enregistré · recliquer pour le retirer</span>}
                  </div>}
                  {tab==='questions'&&reply.id&&<button type="button" disabled={!!operation||frozen} aria-pressed={!!reply.pinned} onClick={()=>pin(reply)}>{reply.pinned?'Désépingler la réponse':'Épingler la réponse'}</button>}</article>)}</div>
              {tab==='chat'&&historyLoading&&<p role="status">Lecture de l’historique de ce contexte…</p>}
              {tab==='chat'&&historyError&&<div role="alert"><p>{historyError}</p><button type="button" onClick={()=>setHistoryTick(value=>value+1)}>Relire l’historique</button></div>}
              {assistantReady&&<form onSubmit={event => {event.preventDefault(); ask(tab === 'questions');}}><label>Question à l’assistant<textarea value={query} onChange={event => setQuery(event.target.value)} rows={3} /></label>
                <button type="submit" disabled={!query.trim() || !!operation || (tab==='chat'&&(conversation.key!==contextKey||historyLoading||!!historyError||scope === 'sources' && !sourceIds.length))}>Poser la question</button></form>}
              {tab === 'questions' && !capabilities.transcription.live_ready && <p>{assistantReady?'Le direct n’est pas qualifié ; vous pouvez demander une réponse explicitement.':'Le direct n’est pas qualifié.'}</p>}
            {!assistantReady&&<><p className="meeting-studio-notice">La génération ciblée est indisponible. Les réponses conservées restent consultables.</p>
              {projectAssistant && <a className="button secondary" href={projectAssistant} target="_blank" rel="noopener">Assistant de projet</a>}</>}
            </>
          </>}
          <div hidden={tab!=='summary'&&tab!=='transcript'}>{session.recording_id && session.project_id &&
            <MeetingAudioPanel projectId={session.project_id} initialRecordingId={session.recording_id}
              workspaceView={tab==='summary'?'summary':'transcript'} onWorkspaceViewChange={setTab}
              onPublished={() => {void reload(); onChanged?.();}} />}</div>
          <section hidden={tab!=='transcript'} className="meeting-live-transcript" aria-label="Transcription de la séance">
            <details open={!session.recording_id}>
              <summary>{session.recording_id?'Historique du direct (texte provisoire)':'Transcription en direct'}</summary>
              {session.recording_id&&<p>Les passages reçus pendant la capture sont conservés ici. La transcription complète et sa relecture sont disponibles ci-dessus.</p>}
              {session.state === 'completed' && session.tracks?.length > 0 && <audio ref={audio} controls preload="metadata" aria-label="Audio de la séance"
                style={{width:'100%',maxWidth:'100%'}} onLoadedMetadata={event=>applyAudioSeek(event.currentTarget)} src={agentPath(sessionAudioUrl(sessionId, session.tracks.some(track => track.name === 'mic') ? 'mic' : 'system'))} />}
            {transcriptLive&&<div className="meeting-transcript-follow"><span>{transcriptFollow.following?transcriptFollowLabel:'Lecture des passages précédents'}</span>
              {!transcriptFollow.following&&<button type="button" onClick={transcriptFollow.returnToLive}>{directSuspended?'Voir les derniers passages':'Revenir au direct'}</button>}</div>}
            <LiveTranscriptStatus session={session} enabled={capabilities.transcription.enabled}/>
            {(session.transcription_admission?.recoverable_direct_chunks!==undefined
              ?session.transcription_admission.recoverable_direct_chunks>0:session.chunks?.some(chunk=>chunk.speech_status==='failed'||chunk.speech_status==='retained'))&&<button type="button"
              disabled={!!operation||capabilities.transcription.enabled!==true||session.state==='cancelled'}
              onClick={()=>void run('Reprise de la transcription',async()=>{
                const row=await reload();
                const result=await meetingSessions.retryTranscription(sessionId,sessionCommand(row.revision));
                accept(result.session);
                setNotice(`${result.retried_chunks} fragment(s) admis pour transcription ; audio et corrections conservés.`
                  +(result.remaining_recoverable_chunks?` ${result.remaining_recoverable_chunks} fragment(s) restent à reprendre.`:'')
                  +(result.admission_blocked_reason?' La capacité est momentanément indisponible ; l’audio reste conservé.':''));
              })}>Reprendre un lot de transcription</button>}
            {session.transcription_batch&&session.transcription_batch.state!=='idle'&&<div className="meeting-studio-notice" role="status" aria-label="État du traitement complet">
              <p>Traitement complet : {session.transcription_batch.completed_chunks} / {session.transcription_batch.selected_chunks} fragment(s) traités.
                {session.transcription_batch.state==='completed'?' Traitement terminé ; relecture nécessaire.':
                  session.transcription_batch.state==='cancelling'?' Annulation en cours ; audio et texte conservés.':
                  session.transcription_batch.state==='cancelled'?' Traitement annulé ; audio et texte conservés.':
                  session.transcription_batch.state==='failed'||session.transcription_batch.state==='interrupted'?' Traitement interrompu ; audio et texte conservés.':' Traitement en cours.'}</p>
              {session.transcription_batch.error&&<p>{session.transcription_batch.error}</p>}
              {['admitted','running','cancelling'].includes(session.transcription_batch.state)&&<button type="button"
                disabled={!!operation||session.transcription_batch.state==='cancelling'} onClick={()=>void run('Annulation du traitement complet',async()=>{
                  const current=await reload(),result=await meetingSessions.cancelBatchTranscription(sessionId,sessionCommand(current.revision));
                  accept(result.session);setNotice('Annulation demandée ; les originaux et les transcriptions déjà conservées restent disponibles.');
                })}>Annuler le traitement complet</button>}
            </div>}
            {session.state==='completed'&&session.chunks?.some(chunk=>chunk.speech_status==='retained'||chunk.speech_status==='failed'||chunk.speech_status==='pending')&&
              !['admitted','running','cancelling'].includes(session.transcription_batch?.state||'')&&<div>
                <p>Le traitement complet utilise l’audio sauvegardé, sans ouvrir de microphone. Il peut prendre du temps et reste annulable.</p>
                <button type="button" disabled={!!operation||capabilities.transcription.session_batch_ready!==true}
                  onClick={()=>void run('Transcription de l’audio conservé',async()=>{
                    const current=await reload(),result=await meetingSessions.batchTranscription(sessionId,sessionCommand(current.revision));
                    accept(result.session);setNotice('Traitement complet demandé ; audio et corrections conservés.');
                  })}>Transcrire l’audio conservé</button>
                {capabilities.transcription.session_batch_ready!==true&&<p>Le moteur de transcription locale doit être installé pour ce traitement.</p>}
              </div>}
            {!!session.segments?.length&&<p>{session.transcript_provisional||session.segments.some(segment=>!segment.finalized) ? 'Texte provisoire ; la consolidation finale reste nécessaire.' : 'Segments stabilisés ; la relecture humaine reste nécessaire.'}</p>}
            <ol ref={transcriptFollow.listRef}>{session.segments?.map(segment => <li key={segment.id} data-segment-id={segment.id} data-segment-track={segment.track}>
              <button type="button" disabled={session.state !== 'completed'} onClick={() => seekAudio(segment.track,segment.start_ms)}>{clock(segment.start_ms / 1000)}–{clock(segment.end_ms / 1000)}</button>
              <span>{segment.speaker || 'Voix à identifier'} · {segment.track === 'mic' ? 'Micro' : 'Audio partagé'} · {segment.finalized ? 'Stabilisé' : 'Provisoire'}</span>
              <MeetingTranscriptEdit session={session} segment={segment} onChanged={accept}/></li>)}</ol>
            </details>
          </section>
          {!session.recording_id&&session.project_id&&<div hidden={tab!=='summary'}><MeetingNotePublication key={session.id} session={session} dirty={dirty || markdownDraft.pending} unfinished={session.state!=='completed'}
            onPublished={row=>{accept(row);onChanged?.();}} onOpenProject={onOpenProject}/></div>}
          <div hidden={tab!=='summary'&&tab!=='transcript'}>{!(session.recording_id && session.project_id)&&(tab!=='summary'||!session.project_id)&&<div className="meeting-pane-empty"><h3>{tab === 'summary' ? 'Compte rendu à préparer' : 'Transcription à préparer'}</h3>
            <p>{!session.project_id ? 'La transcription reçue reste consultable. Rattachez la séance à un projet pour publier.' : session.kind === 'note'
              ? 'Les notes seules restent disponibles dans Documents. Le compte rendu manuel du projet est conservé.' : 'Arrêtez et conservez l’audio avant sa relecture.'}</p>
            {!session.project_id&&<button type="button" onClick={()=>{if(preparation.current){preparation.current.open=true;preparation.current.scrollIntoView({block:'nearest'});preparation.current.querySelector<HTMLSelectElement>('[aria-label="Projet de la séance"]')?.focus();}}}>Choisir un projet</button>}{session.project_id && <button type="button" onClick={() => onOpenProject(session.project_id!, 'reviews')}>Ouvrir les comptes rendus du projet</button>}</div>}</div>
        </div>
      </section>
    </div>
    </div>
  </section>;
}
function LiveTranscriptStatus({session,enabled}:{session:MeetingSession;enabled?:boolean}){
  const chunks=session.chunks||[];
  const counts={retained:0,pending:0,running:0,failed:0,completed:0,batch_pending:0,batch_running:0,unknown:0};
  const backlog={mic:0,system:0},retained={mic:0,system:0};
  for(const chunk of chunks){
    const state=chunk.speech_status;
    if(state&&state in counts)counts[state]++;else counts.unknown++;
    if(state&&Number.isFinite(chunk.duration_ms)&&chunk.duration_ms>0){
      if(state==='retained')retained[chunk.track]+=chunk.duration_ms;
      else if(state==='pending'||state==='running')backlog[chunk.track]+=chunk.duration_ms;
    }
  }
  const complete=!!chunks.length&&session.transcript_processing_complete===true&&!counts.retained&&!counts.pending&&!counts.running&&!counts.batch_pending&&!counts.batch_running&&!counts.failed&&!counts.unknown;
  const firstError=chunks.find(chunk=>chunk.speech_status==='failed'&&chunk.speech_error)?.speech_error;
  return <div className="meeting-transcript-status" role="status" aria-label="État du traitement STT">
    {!!chunks.length&&enabled===false&&<p>La transcription directe est désactivée. Les fragments restent conservés ; son activation est distincte dans Préparation.</p>}
    {!chunks.length&&<p>{session.kind==='note'?'Cette séance contient des notes sans fragment audio.':'Aucun fragment audio reçu pour le moment.'}</p>}
    {!!chunks.length&&<p>Fragments STT : {counts.pending} en attente · {counts.running} en cours · {counts.retained} conservés hors direct · {counts.failed} à reprendre · {counts.completed} traités{counts.unknown?` · ${counts.unknown} sans état fourni`:''}.</p>}
    {(['mic','system'] as const).map(track=><div key={track}>
      {backlog[track]>0&&<p>{track==='mic'?'Microphone':'Audio partagé'} : {(backlog[track]/1000).toLocaleString('fr-FR',{maximumFractionDigits:1})} s dans la file du direct sur cette piste.</p>}
      {retained[track]>0&&<p>{track==='mic'?'Microphone':'Audio partagé'} : {(retained[track]/1000).toLocaleString('fr-FR',{maximumFractionDigits:1})} s sauvegardées hors du direct sur cette piste.</p>}
    </div>)}
    {counts.retained>0&&<p>Ces fragments sont sauvegardés sans traitement automatique. Leur reprise nécessite un geste explicite.</p>}
    {(counts.batch_pending>0||counts.batch_running>0)&&<p>Traitement complet : {counts.batch_pending} fragment(s) à traiter · {counts.batch_running} en cours.</p>}
    {counts.failed>0&&<p role="alert">Traitement à reprendre ; les fragments audio restent conservés.{firstError?` ${firstError}`:''}</p>}
    {complete&&<p>{session.segments?.length?'Traitement STT terminé ; le texte reste soumis à consolidation et relecture.':'Traitement STT terminé ; aucun segment de parole disponible.'}</p>}
    {!complete&&!!chunks.length&&!session.segments?.length&&<p>Aucun segment disponible pour le moment.</p>}
  </div>;
}
function CitationList({citations,onOpenSource}: {citations: NonNullable<SessionAnswer['citations']>;onOpenSource?:(citation:NonNullable<SessionAnswer['citations']>[number])=>void}) {
  if (!citations.length) return null;
  return <div className="meeting-citations">{citations.map((citation, index) => {const url=citationSourceUrl(citation),audio=citationAudioUrl(citation);return <details key={`${citation.source_id || ''}:${index}`}><summary>{citation.title || `Source ${index + 1}`}</summary>
    <blockquote>{citation.excerpt || citation.quote}</blockquote>
    {citation.locator && <p>{citationLocatorText(citation.locator)}</p>}
    {url&&<a href={agentPath(citationReaderUrl(citation)!)} target="_blank" rel="noreferrer">{isNoteVersionUrl(url)?'Ouvrir la version citée':'Consulter la source citée'}</a>}
    <NoteVersionPreview citation={citation}/>
    {citation.source_id&&/^[A-Za-z0-9_-]+$/.test(citation.source_id)&&onOpenSource&&<button type="button" onClick={()=>onOpenSource(citation)}>Examiner la source citée</button>}
    {audio&&<audio aria-label="Audio de la citation" controls preload="metadata" src={agentPath(audio)}/>}
  </details>;})}</div>;
}
