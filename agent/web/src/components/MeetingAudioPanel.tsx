import { agentPath } from '../lib/agentRoutes';
import { useCallback, useEffect, useId, useRef, useState } from "react";
import { beginActivity } from '../lib/asyncActivity';
import { meetingAudio, type AudioRuntime, type MeetingRecording, type RecordingListItem,
  type TranscriptSegment, type MeetingAudioSummary } from "../lib/meetingAudio";
import {isLinuxWebKit, joinPcmWaves, needsPcmAudioRecorder, PcmAudioRecorder} from '../lib/pcmAudioRecorder';
import {identityApi} from '../lib/projectIdentity';
import {ProjectAudioDrafts} from '../lib/projectAudioDrafts';
import "../meeting-audio.css";
import "../progressive-options.css";

const emptySummary = (): MeetingAudioSummary => ({overview: "", decisions: [], actions: [], open_points: []});
const active = (record: MeetingRecording | null) => !!record && ["queued", "running"].includes(record.job_status);
const clock = (seconds: number) => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
const stages: Record<string, string> = {queued: "En attente", decoding: "Lecture de l’audio", speakers: "Séparation des interlocuteurs",
  transcribing: "Transcription", synthesizing: "Rédaction du compte rendu", consolidating: "Préparation du compte rendu"};
const today = () => {const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;};

type AudioView = 'audio' | 'transcript' | 'summary';
type SelectedCapture = {sessionId:string; operatorId:string; file:File; sealed:boolean};
type UploadedCapture = SelectedCapture & {recordingId:string; sourceId:string};
const canReadCapture = (operator:{id:string;project_ids:string[]|null}, capture:UploadedCapture, projectId:string) =>
  operator.id === capture.operatorId && (operator.project_ids === null || Array.isArray(operator.project_ids) && operator.project_ids.includes(projectId));
export function MeetingAudioPanel({projectId, onPublished, initialRecordingId, workspaceView, onWorkspaceViewChange, viewActive=true}: {
  projectId: string; onPublished: () => void; initialRecordingId?:string;
  viewActive?: boolean;
  workspaceView?: Exclude<AudioView, 'audio'>; onWorkspaceViewChange?: (view: Exclude<AudioView, 'audio'>) => void;
}) {
  const [runtime, setRuntime] = useState<AudioRuntime | null>(null);
  const [list, setList] = useState<RecordingListItem[]>([]);
  const [record, setRecord] = useState<MeetingRecording | null>(null);
  const [segments, setSegments] = useState<TranscriptSegment[]>([]);
  const [names, setNames] = useState<Record<string, string>>({});
  const [summary, setSummary] = useState<MeetingAudioSummary>(emptySummary);
  const [dirty, setDirty] = useState(false);
  const [summaryDirty, setSummaryDirty] = useState(false);
  const drafts = useRef({dirty,summaryDirty});
  drafts.current = {dirty,summaryDirty};
  const [page, setPage] = useState(0);
  const [title, setTitle] = useState("");
  const [date, setDate] = useState(today);
  const [speakerCount, setSpeakerCount] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const latestFile = useRef<File | null>(null);
  latestFile.current = file;
  const [selectedCapture, setSelectedCapture] = useState<SelectedCapture | null>(null);
  const [uploadedCapture, setUploadedCapture] = useState<UploadedCapture | null>(null);
  const [cleanupNotice, setCleanupNotice] = useState('');
  const [previewUrl, setPreviewUrl] = useState('');
  const [error, setError] = useState("");
  const [operation, setOperation] = useState("");
  const [recordingMic, setRecordingMic] = useState(false);
  const [savingMic, setSavingMic] = useState(false);
  const [localCaptures, setLocalCaptures] = useState<{sessionId:string;count:number}[]>([]);
  const [localCaptureError, setLocalCaptureError] = useState('');
  const [captureRefresh, setCaptureRefresh] = useState(0);
  const inventorySequence = useRef(0);
  const audioDrafts = useRef(new ProjectAudioDrafts());
  const [localView, setLocalView] = useState<AudioView>('audio');
  const view = workspaceView ?? localView;
  const setView = (next: AudioView) => {
    setLocalView(next);
    if (next !== 'audio') onWorkspaceViewChange?.(next);
  };
  const panelId=useId();
  const audio = useRef<HTMLAudioElement>(null);
  const microphone = useRef<MediaRecorder | PcmAudioRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const startingMic = useRef(false);
  const releasingCapture = useRef(false);
  const scopeKey = JSON.stringify([projectId, initialRecordingId ?? null]);
  const scope = useRef({key: scopeKey});
  if (scope.current.key !== scopeKey) scope.current = {key: scopeKey};
  const currentScope = scope.current;
  const alive = useRef(true);
  useEffect(() => {alive.current = true; return () => {alive.current = false;};}, []);
  useEffect(() => {
    window.dispatchEvent(new CustomEvent("agent-microphone", {detail:{projectId,recording:recordingMic}}));
    return () => {window.dispatchEvent(new CustomEvent("agent-microphone", {detail:{projectId,recording:false}}));};
  }, [projectId,recordingMic]);
  useEffect(() => {
    if (!file || typeof URL.createObjectURL !== 'function') {setPreviewUrl(''); return;}
    const url = URL.createObjectURL(file); setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  useEffect(()=>{
    const stop=(event:Event)=>{
      if((event as CustomEvent<{projectId:string}>).detail?.projectId===projectId && microphone.current?.state==="recording")microphone.current.stop();
    };
    const show=(event:Event)=>{if((event as CustomEvent<{projectId:string}>).detail?.projectId===projectId)setView("audio");};
    window.addEventListener("agent-stop-recording",stop);window.addEventListener("agent-show-recording",show);
    return()=>{window.removeEventListener("agent-stop-recording",stop);window.removeEventListener("agent-show-recording",show);};
  },[projectId]);
  useEffect(() => {
    const protect=(event:BeforeUnloadEvent)=>{if(recordingMic || savingMic || file || dirty || summaryDirty){event.preventDefault();event.returnValue="";}};
    window.addEventListener("beforeunload",protect);return()=>window.removeEventListener("beforeunload",protect);
  },[recordingMic,savingMic,file,dirty,summaryDirty]);
  useEffect(() => {setLocalCaptures([]); setLocalCaptureError('');}, [projectId,initialRecordingId]);
  useEffect(() => {
    if (initialRecordingId) return;
    let disposed = false;
    const sequence = ++inventorySequence.current;
    setLocalCaptureError('');
    void (async () => {
      try {
        const {operator} = await identityApi.session();
        await audioDrafts.current.ready();
        const items = await audioDrafts.current.list(operator.id, projectId);
        if (!disposed && sequence === inventorySequence.current) {setLocalCaptures(items); setLocalCaptureError('');}
      } catch {
        if (!disposed && sequence === inventorySequence.current) setLocalCaptureError('Les captures locales ne peuvent pas être vérifiées. Réessayez pour les retrouver.');
      }
    })();
    return () => {disposed = true;};
  }, [projectId,initialRecordingId,captureRefresh]);
  const accept = useCallback((row: MeetingRecording, preserveSummaryDraft=false, preserveTranscriptDraft=false) => {
    setRecord(row);
    if (!preserveTranscriptDraft) {setSegments(row.segments); setNames(row.speaker_names); setDirty(false);}
    if (!preserveSummaryDraft) {setSummary({...emptySummary(), ...row.summary}); setSummaryDirty(false);}
  }, []);
  const reload = useCallback(async () => {
    const rows = await meetingAudio.list(projectId);
    if (alive.current && scope.current === currentScope) setList(initialRecordingId?rows.filter(row=>row.id===initialRecordingId):rows);
  }, [projectId,initialRecordingId,currentScope]);
  useEffect(() => {
    let disposed = false;
    setList([]); setRecord(null); setSegments([]); setNames({}); setDirty(false); setError(""); setPage(0);
    setFile(null); setSelectedCapture(null); setUploadedCapture(null); setCleanupNotice(''); setTitle(""); setOperation(""); setRecordingMic(false); setSavingMic(false); setSummaryDirty(false); setLocalView("audio");
    Promise.all([meetingAudio.list(projectId), meetingAudio.status(),initialRecordingId?meetingAudio.get(projectId,initialRecordingId):Promise.resolve(null)]).then(([rows, status,initial]) => {
      if (!disposed) {
        setList(initialRecordingId?rows.filter(row=>row.id===initialRecordingId):rows); setRuntime(status);
        if(initial){accept(initial);setLocalView(initial.revision>0&&initial.reviewed_revision===initial.revision?'summary':'transcript');}
      }
    }).catch(e => {if (!disposed) setError(String(e.message ?? e));});
    return () => {disposed = true; if (microphone.current?.state === "recording") microphone.current.stop(); stream.current?.getTracks().forEach(t => t.stop()); microphone.current = null; stream.current = null;};
  }, [projectId,initialRecordingId,accept]);
  useEffect(() => {
    if (!viewActive || !active(record)) return;
    let disposed = false, polling = false, controller:AbortController|null=null;
    let timer: number | undefined;
    const id = record!.id;
    const poll = async () => {
      if (polling || disposed || document.hidden) return;
      polling = true;
      const request=new AbortController();controller=request;
      try {
        const row = await meetingAudio.get(projectId, id,request.signal,true);
        if (!disposed && !request.signal.aborted) {
          accept(row, drafts.current.summaryDirty, drafts.current.dirty);
          // The final status already contains the fields shown in the list.
          if (!active(row)) setList(entries => entries.map(entry => entry.id === row.id
            ? {...entry, date: row.date, title: row.title, published_meeting_id: row.published_meeting_id}
            : entry));
        }
      } catch (e) {if (!disposed && !request.signal.aborted) setError(String((e as Error).message));}
      finally {if(controller===request){controller=null;polling=false;}}
    };
    const stop = () => {
      window.clearInterval(timer);
      timer = undefined;
      controller?.abort();
      controller = null;
      polling = false;
    };
    const visibility = () => {
      if (document.hidden) stop();
      else if (timer === undefined) {
        void poll();
        timer = window.setInterval(() => void poll(), 2000);
      }
    };
    document.addEventListener('visibilitychange',visibility);
    visibility();
    return () => {disposed = true; stop(); document.removeEventListener('visibilitychange',visibility);};
  }, [projectId, record?.id, record?.job_status, accept, viewActive]);

  const execute = async (label: string, task: () => Promise<MeetingRecording>, preserveSummaryDraft=false) => {
    const finish=beginActivity(label);
    setOperation(label); setError("");
    try {
      const row = await task();
      if (alive.current && scope.current === currentScope) {accept(row, preserveSummaryDraft && summaryDirty && record?.id===row.id); await reload();}
      return row;
    } catch (e) {if (alive.current && scope.current === currentScope) setError(String((e as Error).message));}
    finally {finish();if (alive.current && scope.current === currentScope) setOperation("");}
  };
  const upload = () => {
    if (!file || !title.trim()) return;
    if (file.size > 256 * 1024 * 1024) {setError("L’enregistrement dépasse 256 Mio. Utiliser un format compressé ou découper la réunion."); return;}
    const capture = selectedCapture?.file === file && selectedCapture.sealed ? selectedCapture : null;
    const originScope = currentScope;
    const body = new FormData(); body.append("file", file); body.append("title", title.trim()); body.append("date", date); body.append("num_speakers", String(speakerCount));
    void execute("Import de l’audio", () => meetingAudio.upload(projectId, body)).then(row => {
      if (row && capture && latestFile.current === capture.file && row.id && row.source_id && alive.current && scope.current === originScope) {
        setUploadedCapture({...capture,recordingId:row.id,sourceId:row.source_id});
      }
    });
  };
  const startMic = async () => {
    setError("");
    if (startingMic.current) return;
    if (file && !window.confirm('Le fichier sélectionné sera remplacé par le nouvel enregistrement. Continuer ?')) return;
    if (document.querySelector('[data-mic-recording="true"]')) {setError("Un microphone enregistre déjà une réunion. Revenez à cette réunion pour l’arrêter."); return;}
    const Recorder = typeof MediaRecorder === 'undefined' ? null : MediaRecorder;
    const pcm = isLinuxWebKit(navigator.userAgent || '') && (!Recorder || needsPcmAudioRecorder(navigator.userAgent, Recorder));
    if (!navigator.mediaDevices?.getUserMedia || (!Recorder && !pcm)) {setError("Ce navigateur ne permet pas l’enregistrement. Importer un fichier audio."); return;}
    const originScope = currentScope;
    let media: MediaStream | undefined;
    startingMic.current = true;
    try {
      if (!globalThis.crypto?.subtle) throw new Error('La vérification du stockage audio est indisponible.');
      const {operator} = await identityApi.session();
      await audioDrafts.current.ready();
      const sessionId = audioDrafts.current.create(operator.id, projectId);
      if (!alive.current || scope.current !== originScope) return;
      media = await navigator.mediaDevices.getUserMedia({audio: true});
      if (!alive.current || scope.current !== originScope) {media.getTracks().forEach(t => t.stop()); return;}
      stream.current = media;
      const captured = media;
      const recorder = pcm ? new PcmAudioRecorder(captured) : new Recorder!(captured, {audioBitsPerSecond: 32000});
      const chunks: Blob[] = [];
      let bytes = 0, failed = false, saveFailed = false, released = false, finalized = false, sequence = 0;
      let pending:Promise<void> = Promise.resolve();
      const startedAt = Date.now();
      const release = () => {
        if (!released) {released = true; captured.getTracks().forEach(t => t.stop());}
        if (stream.current === captured) stream.current = null;
        if (microphone.current === recorder) microphone.current = null;
      };
      recorder.ondataavailable = e => {
        if (e.data.size) {
          const type = recorder.mimeType || e.data.type || 'audio/webm';
          const part = e.data.type === type ? e.data : new Blob([e.data], {type});
          chunks.push(part); bytes += part.size;
          const seq = sequence++, elapsed = Math.max(0, Date.now() - startedAt);
          pending = pending.then(async () => {
            if (!saveFailed) await audioDrafts.current.append(operator.id, projectId, sessionId, seq, part, elapsed, 0);
          }).catch(() => {
            saveFailed = true;
            if (alive.current && scope.current === originScope) setError('La sauvegarde locale a échoué. Gardez cette page ouverte et importez l’audio récupéré.');
            try {if (recorder.state === 'recording') recorder.stop();} catch {finish();}
          });
        }
        if (bytes > 256 * 1024 * 1024 && recorder.state === "recording") {recorder.stop(); setError("Limite de 256 Mio atteinte ; enregistrer plusieurs parties.");}
      };
      const finish = () => {
        if (finalized) return;
        finalized = true;
        release();
        if (!alive.current || scope.current !== originScope) return;
        setRecordingMic(false);
        setSavingMic(true);
        void pending.then(async () => {
          let sealed = false;
          if (!failed && !saveFailed && bytes) {
            try {await audioDrafts.current.seal(operator.id, projectId, sessionId); sealed = true;}
            catch {
              if (alive.current && scope.current === originScope) setError('La fin de la capture ne peut pas être confirmée. La copie locale reste conservée.');
            }
          }
          if (!alive.current || scope.current !== originScope) return;
          if (sealed) setSelectedCapture(current=>current?.sessionId === sessionId ? {...current,sealed:true} : current);
          setSavingMic(false);
          const sequence = ++inventorySequence.current;
          try {
            const items = await audioDrafts.current.list(operator.id, projectId);
            if (alive.current && scope.current === originScope && sequence === inventorySequence.current) {setLocalCaptures(items); setLocalCaptureError('');}
          } catch {
            if (alive.current && scope.current === originScope && sequence === inventorySequence.current) setLocalCaptureError('Les captures locales ne peuvent pas être vérifiées. Réessayez pour les retrouver.');
          }
        });
        if (!bytes) {if (!failed) setError("Aucun son n’a été enregistré. Vérifiez le microphone et réessayez."); return;}
        try {
          const type = recorder.mimeType || "audio/webm";
          const extension = type.includes("wav") ? "wav" : type.includes("mp4") ? "m4a" : type.includes("ogg") ? "ogg" : "webm";
          const parts = recorder instanceof PcmAudioRecorder ? [joinPcmWaves(chunks, recorder.sampleRate ?? 0)] : chunks;
          const next = new File(parts, `reunion-${Date.now()}.${extension}`, {type});
          setFile(next); setSelectedCapture({sessionId,operatorId:operator.id,file:next,sealed:false}); setUploadedCapture(null); setCleanupNotice('');
          if (saveFailed) setError('La sauvegarde locale a échoué. Gardez cette page ouverte et importez l’audio récupéré.');
          else if (failed) setError("Enregistrement interrompu. Vérifiez l’audio récupéré avant de l’importer.");
        } catch {setError("Impossible de préparer l’audio. Vérifiez le microphone et réessayez.");}
      };
      recorder.onstop = finish;
      recorder.onerror = () => {
        failed = true;
        try {if (recorder.state !== 'inactive') recorder.stop();}
        catch {finish();}
        finally {release();}
        if (alive.current && scope.current === originScope) {setRecordingMic(false); if (!finalized || !bytes) setError("Enregistrement interrompu par le navigateur.");}
      };
      microphone.current = recorder; recorder.start(1000); setRecordingMic(true);
    } catch (e) {
      media?.getTracks().forEach(t => t.stop());
      if (stream.current === media) stream.current = null;
      microphone.current = null;
      if (alive.current && scope.current === originScope) setError("Microphone indisponible : " + String((e as Error).message));
    } finally {startingMic.current = false;}
  };
  const restoreCapture = async (sessionId:string) => {
    if (file && !window.confirm('Le fichier sélectionné sera remplacé par cette capture. Continuer ?')) return;
    const originScope = currentScope;
    setOperation('Récupération de l’audio'); setError('');
    try {
      const {operator} = await identityApi.session();
      const recovered = await audioDrafts.current.read(operator.id, projectId, sessionId);
      if (!alive.current || scope.current !== originScope) return;
      const extension = recovered.blob.type.includes('wav') ? 'wav' : recovered.blob.type.includes('mp4') ? 'm4a' : recovered.blob.type.includes('ogg') ? 'ogg' : 'webm';
      const next = new File([recovered.blob], `reunion-recuperee-${Date.now()}.${extension}`, {type:recovered.blob.type});
      let sealed = false;
      try {sealed = audioDrafts.current.isSealed(operator.id, projectId, sessionId);} catch { /* Keep captures whose end cannot be verified. */ }
      setFile(next); setSelectedCapture({sessionId,operatorId:operator.id,file:next,sealed}); setUploadedCapture(null); setCleanupNotice('');
      setError('Audio récupéré : il peut être incomplet. Vérifiez-le avant de l’importer.');
    } catch (e) {if (alive.current && scope.current === originScope) setError('Récupération impossible : ' + String((e as Error).message));}
    finally {if (alive.current && scope.current === originScope) setOperation('');}
  };
  const releaseLocalCapture = async (capture:UploadedCapture) => {
    if (releasingCapture.current) return;
    const originScope = currentScope;
    releasingCapture.current = true; setOperation('Vérification de la copie sur le serveur'); setError(''); setCleanupNotice('');
    try {
      const {operator} = await identityApi.session();
      if (!canReadCapture(operator,capture,projectId)) throw new Error('Le compte ou l’accès au projet a changé. La copie locale est conservée.');
      const receipt = await meetingAudio.integrity(projectId, capture.recordingId);
      const current = await identityApi.session();
      if (!canReadCapture(current.operator,capture,projectId)) throw new Error('Le compte ou l’accès au projet a changé. La copie locale est conservée.');
      if (!alive.current || scope.current !== originScope) return;
      await audioDrafts.current.releaseVerified(operator.id, projectId, capture.sessionId, receipt, capture.recordingId, capture.sourceId, async()=>{
        const latest = await meetingAudio.integrity(projectId, capture.recordingId);
        if (latest.recording_id !== receipt.recording_id || latest.source_id !== receipt.source_id || latest.sha256 !== receipt.sha256 || latest.size !== receipt.size) {
          throw new Error('La copie sur le serveur a changé. La copie locale est conservée.');
        }
        const final = await identityApi.session();
        if (!alive.current || scope.current !== originScope || !canReadCapture(final.operator,capture,projectId)) {
          throw new Error('Le compte ou l’accès au projet a changé. La copie locale est conservée.');
        }
      });
      if (!alive.current || scope.current !== originScope) return;
      ++inventorySequence.current;
      setLocalCaptures(items=>items.filter(item=>item.sessionId !== capture.sessionId));
      setSelectedCapture(current=>current?.sessionId === capture.sessionId ? null : current);
      setFile(current=>current === capture.file ? null : current);
      setUploadedCapture(current=>current?.sessionId === capture.sessionId ? null : current);
      setCleanupNotice('Copie locale libérée. L’audio reste conservé dans le projet.');
    } catch (e) {if (alive.current && scope.current === originScope) setError(String((e as Error).message));}
    finally {releasingCapture.current = false; if (alive.current && scope.current === originScope) setOperation('');}
  };
  const running = active(record), published = !!record?.published_meeting_id;
  const locked = running || published || record?.stage === "publishing" || !!operation;
  const reviewed = !!record && record.reviewed_revision === record.revision && !dirty && record.revision > 0;
  const draftCurrent = !!record?.summary_revision && record.summary_revision === record.revision && reviewed;
  const speakers = Array.from(new Set([...segments.map(s => s.speaker), ...Object.keys(names)]));
  const label = (id: string) => names[id] || (id === "UNKNOWN" ? "Voix à identifier" : `Interlocuteur ${id.replace(/^SPEAKER_0?/, "")}`);
  const seek = (seconds: number) => {if (audio.current) {audio.current.currentTime = seconds; void audio.current.play().catch(() => {});}};
  const editSegment = (id: string, changes: Partial<TranscriptSegment>) => {setSegments(rows => rows.map(s => s.id === id ? {...s, ...changes} : s)); setDirty(true);};
  const select = (id: string) => {
    if ((dirty || summaryDirty) && !window.confirm("Des corrections ne sont pas enregistrées. Ouvrir un autre enregistrement ?")) return;
    setPage(0); void execute("Ouverture", () => meetingAudio.get(projectId, id)).then(row=>{
      if(row && alive.current && scope.current === currentScope)setView(row.summary_revision===row.revision && row.summary_revision>0?"summary":row.segments.length?"transcript":"audio");
    });
  };

  return <section className="meeting-audio" aria-label="Réunion audio" data-mic-recording={recordingMic ? "true" : "false"} data-workspace-dirty={dirty||summaryDirty||recordingMic||savingMic||!!file?'true':undefined}>
    <header><h3>Réunion audio</h3><p>Importez un audio, relisez la transcription, puis préparez le compte rendu.</p></header>
    {error && <p className="meeting-error" role="alert">{error}</p>}
    {!initialRecordingId && localCaptureError && <div className="meeting-error" role="alert">{localCaptureError} <button type="button" className="button secondary" onClick={()=>setCaptureRefresh(value=>value+1)}>Réessayer</button></div>}
    {selectedCapture && !selectedCapture.sealed && !recordingMic && !savingMic && <p role="status">La copie locale reste conservée : la fin de cette capture n’a pas été confirmée.</p>}
    {cleanupNotice && <p role="status">{cleanupNotice}</p>}
    {uploadedCapture && <div className="meeting-job" role="status"><span>L’audio a été importé dans le projet. La copie de cet appareil peut être libérée après vérification.</span>
      <button type="button" className="button secondary" disabled={!!operation || recordingMic || savingMic} onClick={()=>void releaseLocalCapture(uploadedCapture)}>Libérer la copie locale</button></div>}
    <p className={runtime && !runtime.ready?"meeting-error":"muted"} role="status">{runtime?.ready?"Transcription disponible sur ce poste.":runtime?"Transcription indisponible sur ce poste.":"Vérification de la transcription…"}</p>
    {list.length > 0 && <nav className="meeting-recording-list" aria-label="Enregistrements de réunion">{list.map(row => <button key={row.id} className={`button ${record?.id === row.id ? "primary" : "secondary"}`} disabled={!!operation} onClick={() => select(row.id)}>
      {row.date} · {row.title}{row.published_meeting_id ? " · Enregistré" : ""}</button>)}</nav>}
    {record&&<h4>{record.title}</h4>}
    {record&&<audio key={record.id} ref={audio} controls preload="metadata" src={agentPath(meetingAudio.audioUrl(projectId, record.id))} aria-label="Enregistrement de la réunion" />}
    {record&&running && <div className="meeting-job" aria-live="polite"><strong>{stages[record.stage] || record.stage} · {Math.round(record.progress)} %</strong>
      <progress value={record.progress} max={100} aria-label="Progression du traitement audio" />
      {record.job_kind === "transcription" && record.duration_seconds > 0 && <span>{clock(record.processed_seconds)} / {clock(record.duration_seconds)}</span>}
      <button className="button secondary" disabled={record.cancel_requested || !!operation} onClick={() => void execute("Annulation", () => meetingAudio.cancel(projectId, record.id))}>{record.cancel_requested ? "Annulation demandée…" : "Interrompre"}</button></div>}
    {record?.error && <p className="meeting-error" role="alert">{record.error}</p>}
    {recordingMic&&<div className="meeting-job" role="status"><strong>Enregistrement au microphone en cours</strong><button className="button secondary" onClick={()=>microphone.current?.stop()}>Arrêter l’enregistrement</button></div>}
    {!workspaceView&&<nav className="meeting-audio-tabs" role="tablist" aria-label="Étapes de la réunion audio">{([["audio","Audio"],["transcript","Transcription"],["summary","Compte rendu"]] as const).map(([key,label])=><button key={key} type="button" role="tab" id={`${panelId}-${key}-tab`} aria-selected={view===key} aria-controls={`${panelId}-${key}-panel`} onClick={()=>setView(key)}>{label}{key==='transcript'&&dirty || key==='summary'&&summaryDirty?' · corrections en cours':''}</button>)}</nav>}
    <div role={workspaceView?undefined:'tabpanel'} id={`${panelId}-audio-panel`} aria-labelledby={workspaceView?undefined:`${panelId}-audio-tab`} hidden={view!=="audio"}>
    {!initialRecordingId&&<details className="card" open={!record}>
      <summary>Importer ou enregistrer une réunion</summary>
      {localCaptures.length > 0 && <div className="card"><p>Captures conservées sur cet appareil pour ce projet. Leur fin peut manquer après une interruption.</p>
        {localCaptures.map((item,index)=><button key={item.sessionId} type="button" className="button secondary" disabled={recordingMic || savingMic || !!operation} onClick={()=>void restoreCapture(item.sessionId)}>Récupérer la capture {index+1} ({item.count} fragments)</button>)}</div>}
      <div className="meeting-upload">
        <label>Titre de la réunion<input className="input" value={title} onChange={e => setTitle(e.target.value)} maxLength={255} /></label>
        <label>Date de la réunion<input className="input" type="date" value={date} onChange={e => setDate(e.target.value)} /></label>
        <label>Fichier audio<input type="file" accept="audio/*,video/mp4,video/webm,.m4a,.opus" disabled={recordingMic} onChange={e => {setFile(e.target.files?.[0] ?? null);setSelectedCapture(null);setUploadedCapture(null);setCleanupNotice('');}} /></label>
      </div>
      <details className="progressive-options"><summary>Options de l’audio</summary>
        <label>Nombre d’interlocuteurs<select className="input" value={speakerCount} onChange={e => setSpeakerCount(Number(e.target.value))}><option value={0}>Détection automatique</option>{Array.from({length: 20}, (_, i) => <option key={i + 1} value={i + 1}>{i + 1}</option>)}</select></label>
        {runtime&&<p className="muted">{runtime.detail} · Modèle : {runtime.model} · Calcul : {runtime.device}</p>}
      </details>
      <div className="inline-form">
        {!recordingMic && <button className="button secondary" disabled={!!operation || savingMic} onClick={() => void startMic()}>Enregistrer au microphone</button>}
        {file && <span>{file.name} · {(file.size / 1024 / 1024).toFixed(1)} Mo</span>}
        <button className="button primary" disabled={!file || !title.trim() || !!operation || recordingMic || savingMic} onClick={upload}>Importer l’audio</button>
      </div>
      {previewUrl && <audio controls preload="metadata" src={previewUrl} aria-label="Écouter le fichier avant import" />}
      <p className="muted">{runtime?.max_upload_mb ?? 256} Mio maximum, jusqu’à 2 heures. Audio conservé dans le projet ; transcription locale.</p>
    </details>}
    {record&&<button type="button" className="button primary" onClick={()=>setView("transcript")}>Ouvrir la transcription</button>}
    </div>
    <div role={workspaceView?undefined:'tabpanel'} id={`${panelId}-transcript-panel`} aria-labelledby={workspaceView?undefined:`${panelId}-transcript-tab`} hidden={view!=="transcript"}>
    {!record&&<p>Importez un audio ou ouvrez un enregistrement pour le transcrire.</p>}
    {record && <>
      <section className="card" aria-label="Phase 1 : transcription">
        <h4>Transcription</h4>
        {!record.segments.length ? <><p>{runtime?.ready ? "Transcription et séparation des voix disponibles sur ce poste." : runtime ? "Transcription indisponible sur ce poste." : "Vérification de la transcription…"}</p>
          <button className="button primary" disabled={!runtime?.ready || locked} onClick={() => void execute("Démarrage", () => meetingAudio.transcribe(projectId, record.id))}>{["failed", "cancelled", "interrupted"].includes(record.job_status) ? "Reprendre la transcription" : "Transcrire et séparer les voix"}</button></>
          : <p>{segments.length} interventions · {clock(record.duration_seconds)} · {speakers.length} interlocuteur(s)</p>}
      </section>
      {segments.length > 0 && <section className="card" aria-label="Phase 2 : relecture par interlocuteur">
        <h4>Relire et valider</h4><p>Corrige les noms, les affectations et le texte, puis valide la transcription.</p>
        <details className="progressive-options"><summary>Noms des interlocuteurs</summary>
        <div className="meeting-speakers">{speakers.map(id => <label key={id}>{id === "UNKNOWN" ? "Voix non attribuée" : label(id)}<input className="input" aria-label={`Nom ${id}`} value={names[id] ?? ""} placeholder={label(id)} disabled={locked} maxLength={120} onChange={e => {setNames(old => ({...old, [id]: e.target.value})); setDirty(true);}} /></label>)}
          <button className="button secondary" disabled={locked} onClick={() => {const id = `MANUAL_${speakers.length + 1}`; setNames(old => ({...old, [id]: `Interlocuteur ${speakers.length + 1}`})); setDirty(true);}}>Ajouter un interlocuteur</button></div>
        </details>
        <div className="meeting-transcript">{segments.slice(page * 40, page * 40 + 40).map(segment => <article className="meeting-turn" key={segment.id}>
          <div className="meeting-turn-heading"><button className="button secondary" aria-label={`Écouter à ${clock(segment.start)}`} onClick={() => seek(segment.start)}>{clock(segment.start)}–{clock(segment.end)}</button>
            <select className="input" aria-label={`Interlocuteur ${segment.id}`} value={segment.speaker} disabled={locked} onChange={e => editSegment(segment.id, {speaker: e.target.value})}>{speakers.map(id => <option value={id} key={id}>{label(id)}</option>)}</select></div>
          <textarea className="input" aria-label={`Texte ${segment.id}`} rows={Math.min(6, Math.max(2, Math.ceil(segment.text.length / 100)))} value={segment.text} disabled={locked} onChange={e => editSegment(segment.id, {text: e.target.value})} />
        </article>)}</div>
        {segments.length > 40 && <div className="inline-form"><button className="button secondary" disabled={!page} onClick={() => setPage(p => p - 1)}>Précédentes</button><span>Interventions {page * 40 + 1}–{Math.min(segments.length, page * 40 + 40)} / {segments.length}</span><button className="button secondary" disabled={(page + 1) * 40 >= segments.length} onClick={() => setPage(p => p + 1)}>Suivantes</button></div>}
        <div className="inline-form"><button className="button secondary" disabled={locked || !dirty} onClick={() => void execute("Enregistrement", () => meetingAudio.review(projectId, record.id, record.revision, segments, Object.fromEntries(Object.entries(names).filter(([, name]) => name.trim()).map(([id, name]) => [id, name.trim()])), false), true)}>Enregistrer les corrections</button>
          <button className="button primary" disabled={locked || reviewed} onClick={() => void execute("Validation", () => meetingAudio.review(projectId, record.id, record.revision, segments, Object.fromEntries(speakers.map(id => [id, names[id]?.trim() || label(id)])), true), true).then(row=>{
            if(row&&alive.current&&scope.current===currentScope&&row.reviewed_revision===row.revision)setView('summary');
          })}>Valider la transcription</button>
          <span aria-live="polite">{reviewed ? "Transcription validée" : dirty ? "Corrections à enregistrer et valider" : "Transcription à valider"}</span></div>
      </section>}
    </>}
    </div>
    <div role={workspaceView?undefined:'tabpanel'} id={`${panelId}-summary-panel`} aria-labelledby={workspaceView?undefined:`${panelId}-summary-tab`} hidden={view!=="summary"}>
      {(!record || !segments.length)&&<p>Transcrivez l’audio et validez sa relecture pour préparer le compte rendu.</p>}
      {record&&segments.length > 0 && <section className="card" aria-label="Compte rendu de la réunion">
        <h4>Compte rendu</h4>
        {!reviewed && <p>Validez la transcription pour préparer le compte rendu.</p>}
        {record.summary_revision > 0 && !draftCurrent && <p className="meeting-error">La transcription a changé. Refaites le compte rendu après validation.</p>}
        <button className="button primary" disabled={locked || !reviewed} onClick={() => {
          if(summaryDirty&&!window.confirm("Les corrections non enregistrées du compte rendu seront remplacées. Continuer ?"))return;
          void execute("Préparation du compte rendu", () => meetingAudio.synthesize(projectId, record.id));
        }}>{record.summary_revision ? "Refaire le compte rendu" : "Préparer le compte rendu"}</button>
        {(draftCurrent || summaryDirty) && <>
          <p className="muted">Modèle : {record.summary_model} · Vérifie le compte rendu avant son enregistrement.</p>
          {!!record.summary.rejected_items && <p className="meeting-error">{record.summary.rejected_items} élément(s) sans citation vérifiable ont été écartés par le contrôle.</p>}
          <label>Résumé<textarea className="input meeting-overview" aria-label="Résumé de la réunion" rows={6} value={summary.overview} disabled={locked} onChange={e => {setSummary(old => ({...old, overview: e.target.value})); setSummaryDirty(true);}} /></label>
          {(["decisions", "actions", "open_points"] as const).map(kind => <div className="meeting-summary-section" key={kind}><h5>{{decisions: "Décisions", actions: "Actions", open_points: "Points ouverts"}[kind]}</h5>
            {!summary[kind].length && <p className="muted">Aucun élément relevé.</p>}
            {summary[kind].map((item, index) => <article key={`${kind}-${index}`}>
              <textarea className="input" rows={2} aria-label={`${kind} ${index + 1}`} value={item.text} disabled={locked} onChange={e => {setSummary(old => ({...old, [kind]: old[kind].map((entry, i) => i === index ? {...entry, text: e.target.value} : entry)})); setSummaryDirty(true);}} />
              {kind === "actions" && <div className="inline-form"><label>Responsable<input className="input" aria-label={`Responsable action ${index + 1}`} disabled={locked} value={summary.actions[index].owner} maxLength={120} onChange={e => {setSummary(old => ({...old, actions: old.actions.map((entry, i) => i === index ? {...entry, owner: e.target.value} : entry)}));setSummaryDirty(true);}} /></label>
                <label>Échéance<input className="input" type="date" aria-label={`Échéance action ${index + 1}`} disabled={locked} value={summary.actions[index].due_date} onChange={e => {setSummary(old => ({...old, actions: old.actions.map((entry, i) => i === index ? {...entry, due_date: e.target.value} : entry)}));setSummaryDirty(true);}} /></label></div>}
              <blockquote>« {item.quote} » <button className="button secondary" onClick={() => {const segment = segments.find(s => s.id === item.segment_id); if (segment) {setPage(Math.floor(segments.indexOf(segment) / 40)); setView("transcript"); seek(segment.start);}}}>Écouter la source</button></blockquote>
              {!locked && <button className="button secondary" onClick={() => {setSummary(old => ({...old, [kind]: old[kind].filter((_, i) => i !== index)})); setSummaryDirty(true);}}>Écarter du compte rendu</button>}
            </article>)}</div>)}
          {!published ? <button className="button primary" disabled={running || !!operation || !draftCurrent} onClick={async () => {const row = await execute("Enregistrement du compte rendu", () => meetingAudio.publish(projectId, record.id, record.revision, summary)); if (row?.published_meeting_id && alive.current && scope.current === currentScope) onPublished();}}>Valider et enregistrer le compte rendu</button>
            : <p role="status">Compte rendu enregistré dans les Revues et dans la connaissance du projet. Les actions peuvent être converties en tâches ci-dessous.</p>}
        </>}
      </section>}
    </div>
    {operation && <p role="status">{operation}…</p>}
  </section>;
}
