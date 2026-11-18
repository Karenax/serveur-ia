import {meetingCapture, type CaptureOptions} from './meetingCapture';
import {meetingSessions, sessionCommand, type MeetingSession} from './meetingSessions';

type TransitionOptions = {
  sessionId: string;
  captureOptions: CaptureOptions;
  maxUploadMb: number;
  reload: () => Promise<MeetingSession>;
  accept: (row: MeetingSession) => void;
  run: (label: string, task: () => Promise<void>) => Promise<void>;
  setNotice: (message: string) => void;
  showTranscript: () => void;
  showSummary: () => void;
  onChanged?: () => void;
};

/** Orchestrate user actions without duplicating the capture or server session state. */
export function createMeetingTransitions({sessionId, captureOptions, maxUploadMb, reload, accept, run,
  setNotice, showTranscript, showSummary, onChanged}: TransitionOptions) {
  const start = () => void run('Démarrage', async () => {
    await meetingCapture.start(sessionId, captureOptions);
    await reload();
    showTranscript();
  });
  // Cancellation must remain available while the start operation is awaiting permission.
  const cancelStart = () => void meetingCapture.stop();
  const activatePrepared = () => void run('Partage audio', async () => {accept(await meetingCapture.activatePrepared());});
  const cancelPrepared = () => void run('Annulation', async () => {await meetingCapture.cancelPrepared(); await reload();});
  const pause = () => void run('Pause', () => meetingCapture.pause());
  const resume = () => void run('Reprise', () => meetingCapture.resume());
  const stop = () => void run('Conservation', async () => {await meetingCapture.stop(); await reload(); onChanged?.();});
  const recover = () => void run('Récupération', async () => {await meetingCapture.retryAndFinalize(); await reload(); onChanged?.();});
  const finalizeReceived = () => void run('Consolidation de la séance', async () => {
    const row = await reload();
    accept(await meetingSessions.command(sessionId, 'finalize', sessionCommand(row.revision)));
    onChanged?.();
  });
  const finishNotes = () => void run('Conservation de la séance', async () => {
    const row = await reload();
    accept(await meetingSessions.command(sessionId, 'finalize', sessionCommand(row.revision)));
    showSummary();
    onChanged?.();
  });
  const importAudio = (file: File) => void run('Import et conservation de l’audio', async () => {
    if (file.size > maxUploadMb * 1024 * 1024) throw new Error(`L’audio dépasse ${maxUploadMb} Mo.`);
    const row = await reload();
    const form = new FormData();
    const hash = await crypto.subtle.digest('SHA-256', await file.arrayBuffer());
    form.append('file', file); form.append('command_id', crypto.randomUUID());
    form.append('sha256', Array.from(new Uint8Array(hash), byte => byte.toString(16).padStart(2, '0')).join(''));
    form.append('start_ms', '0'); form.append('duration_ms', '0');
    const receipt = await meetingSessions.chunk(row.id, 'mic', 0, form);
    if (!receipt.acknowledged || receipt.session_id !== row.id || receipt.accepted_chunk?.track !== 'mic' ||
      receipt.accepted_chunk.seq !== 0 || receipt.accepted_chunk.size_bytes !== file.size ||
      receipt.accepted_chunk.sha256 !== form.get('sha256')) throw new Error('L’acquittement de l’audio importé ne correspond pas au fichier.');
    const latest = await meetingSessions.get(row.id);
    accept(await meetingSessions.command(row.id, 'finalize', sessionCommand(latest.revision)));
    onChanged?.();
  });
  const retryTranscription = () => void run('Reprise de la transcription', async () => {
    const row = await reload();
    const result = await meetingSessions.retryTranscription(sessionId, sessionCommand(row.revision));
    accept(result.session);
    setNotice(`${result.retried_chunks} fragment(s) admis pour transcription ; audio et corrections conservés.`
      +(result.remaining_recoverable_chunks ? ` ${result.remaining_recoverable_chunks} fragment(s) restent à reprendre.` : '')
      +(result.admission_blocked_reason ? ' La capacité est momentanément indisponible ; l’audio reste conservé.' : ''));
  });
  const cancelBatch = () => void run('Annulation du traitement complet', async () => {
    const row = await reload(), result = await meetingSessions.cancelBatchTranscription(sessionId, sessionCommand(row.revision));
    accept(result.session);
    setNotice('Annulation demandée ; les originaux et les transcriptions déjà conservées restent disponibles.');
  });
  const transcribeAudio = () => void run('Transcription de l’audio conservé', async () => {
    const row = await reload(), result = await meetingSessions.batchTranscription(sessionId, sessionCommand(row.revision));
    accept(result.session);
    setNotice('Traitement complet demandé ; audio et corrections conservés.');
  });
  return {start, cancelStart, activatePrepared, cancelPrepared, pause, resume, stop, recover, finalizeReceived,
    finishNotes, importAudio, retryTranscription, cancelBatch, transcribeAudio};
}
