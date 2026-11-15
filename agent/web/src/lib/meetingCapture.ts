import {LocalBrowserReservation, type BrowserReservation, type BrowserReservationStore} from './browserCaptureReservation';
import { meetingSessions, sessionCommand, type MeetingSession, type MeetingTrack } from './meetingSessions';

export type DurableAudioChunk = {
  id: string; session_id: string; track: MeetingTrack; seq: number; command_id: string; blob: Blob;
  sha256: string; start_ms: number; duration_ms: number; created_at: string;
};
export interface DurableChunkStore {
  ready(): Promise<void>;
  put(chunk: DurableAudioChunk): Promise<void>;
  list(sessionId?: string): Promise<DurableAudioChunk[]>;
  acknowledge(id: string): Promise<void>;
}

/** Only acknowledged cache fragments are removed. The backend retains the original audio. */
export class IndexedAudioChunks implements DurableChunkStore {
  private opening?: Promise<IDBDatabase>;
  private database() {
    this.opening ??= new Promise<IDBDatabase>((resolve, reject) => {
      if (typeof indexedDB === 'undefined') {reject(new Error('Le stockage audio durable est indisponible dans ce navigateur. Importez un fichier audio.')); return;}
      const request = indexedDB.open('agent-meeting-audio-v1', 1);
      request.onupgradeneeded = () => {
        const store = request.result.createObjectStore('chunks', {keyPath: 'id'});
        store.createIndex('session_id', 'session_id');
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(new Error('Le stockage audio local ne peut pas être ouvert.'));
      request.onblocked = () => reject(new Error('Fermez les autres pages Agent pour ouvrir le stockage audio.'));
    }).catch(error => {this.opening = undefined; throw error;});
    return this.opening;
  }
  async ready() {await this.database();}
  async put(chunk: DurableAudioChunk) {
    const db = await this.database();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction('chunks', 'readwrite'); tx.objectStore('chunks').put(chunk);
      tx.oncomplete = () => resolve();
      tx.onerror = tx.onabort = () => reject(new Error('Le fragment audio n’a pas pu être sauvegardé sur cet appareil.'));
    });
  }
  async list(sessionId?: string) {
    const db = await this.database();
    return new Promise<DurableAudioChunk[]>((resolve, reject) => {
      const store = db.transaction('chunks', 'readonly').objectStore('chunks');
      const request = sessionId ? store.index('session_id').getAll(sessionId) : store.getAll();
      request.onsuccess = () => resolve((request.result as DurableAudioChunk[]).sort((a, b) => a.track.localeCompare(b.track) || a.seq - b.seq));
      request.onerror = () => reject(new Error('Les fragments audio conservés ne peuvent pas être lus.'));
    });
  }
  async acknowledge(id: string) {
    const db = await this.database();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction('chunks', 'readwrite'); tx.objectStore('chunks').delete(id);
      tx.oncomplete = () => resolve();
      tx.onerror = tx.onabort = () => reject(new Error('L’acquittement du fragment audio doit être repris.'));
    });
  }
}

type CaptureApi = Pick<typeof meetingSessions, 'get' | 'command' | 'chunk' | 'browserReserve' | 'browserRelease' | 'commandReceipt'>;
export type CaptureSnapshot = {
  sessionId: string | null; title: string; phase: 'idle' | 'ready' | 'starting' | 'recording' | 'paused' | 'stopping' | 'pending' | 'completed' | 'error';
  tracks: MeetingTrack[]; seconds: number; totalBytes: number; savedBytes: number; pending: number; error: string;
};
type CaptureEnvironment = {
  devices: () => MediaDevices; recorder: () => typeof MediaRecorder; now: () => number;
  lock: () => Promise<() => void>; hash: (blob: Blob) => Promise<string>;
};
export type CaptureOptions = {microphone?: boolean; system?: boolean; deviceId?: string; maxBytes?: number; maxMinutes?: number};
const message = (error: unknown) => error instanceof Error ? error.message : String(error);

export async function acquireCaptureLock() {
  if (!navigator.locks?.request) throw new Error('Ce navigateur ne permet pas de protéger le microphone entre les onglets. Utilisez Chrome ou Edge, ou importez un audio.');
  return new Promise<() => void>((resolve, reject) => {
    void navigator.locks.request('agent-durable-meeting-capture', {ifAvailable: true}, async lock => {
      if (!lock) {reject(new Error('Une réunion enregistre déjà dans un autre onglet Agent.')); return;}
      await new Promise<void>(release => resolve(release));
    }).catch(reject);
  });
}
async function audioHash(blob: Blob) {
  if (!crypto.subtle) throw new Error('Le navigateur ne permet pas de vérifier les fragments audio.');
  const bytes = await crypto.subtle.digest('SHA-256', await blob.arrayBuffer());
  return Array.from(new Uint8Array(bytes), byte => byte.toString(16).padStart(2, '0')).join('');
}

/** Application-level controller: removing a view never stops capture or discards blobs. */
export class MeetingCaptureController {
  private reservationStore: BrowserReservationStore;
  private reservation?: BrowserReservation;
  private prepared?: {session: MeetingSession; options: CaptureOptions};
  private startTask?: Promise<MeetingSession>;
  private stopRequested = false;
  private store: DurableChunkStore;
  private api: CaptureApi;
  private environment: CaptureEnvironment;
  private state: CaptureSnapshot = {sessionId: null, title: '', phase: 'idle', tracks: [], seconds: 0, totalBytes: 0, savedBytes: 0, pending: 0, error: ''};
  private listeners = new Set<() => void>();
  private recorders = new Map<MeetingTrack, MediaRecorder>();
  private streams: MediaStream[] = [];
  private releaseLock?: () => void;
  private persistence = Promise.resolve();
  private syncing?: Promise<void>;
  private stopping?: Promise<MeetingSession | null>;
  private timer?: ReturnType<typeof setInterval>;
  private started = 0;
  private pausedAt = 0;
  private pausedMs = 0;
  private stops = new Map<MeetingTrack, Promise<void>>();
  private sequences = new Map<MeetingTrack, number>();
  private ends = new Map<MeetingTrack, number>();
  private durabilityFailed = false;
  private unsaved = new Map<string, DurableAudioChunk>();
  constructor(options: {reservationStore?: BrowserReservationStore; store?: DurableChunkStore; api?: CaptureApi; environment?: Partial<CaptureEnvironment>} = {}) {
    this.reservationStore = options.reservationStore ?? new LocalBrowserReservation();
    this.store = options.store ?? new IndexedAudioChunks(); this.api = options.api ?? meetingSessions;
    this.environment = {
      devices: () => navigator.mediaDevices, recorder: () => MediaRecorder, now: () => performance.now(),
      lock: acquireCaptureLock, hash: audioHash, ...options.environment,
    };
  }
  getSnapshot = () => this.state;
  subscribe = (listener: () => void) => {this.listeners.add(listener); return () => {this.listeners.delete(listener);};};
  private update(value: Partial<CaptureSnapshot>) {this.state = {...this.state, ...value}; this.listeners.forEach(listener => listener());}
  private elapsed() {return Math.max(0, (this.pausedAt || this.environment.now()) - this.started - this.pausedMs);}
  private closeStreams() {
    if (this.timer) clearInterval(this.timer); this.timer = undefined;
    this.streams.forEach(stream => stream.getTracks().forEach(track => track.stop())); this.streams = [];
  }
  private releaseMedia() {
    this.closeStreams(); this.releaseLock?.(); this.releaseLock = undefined;
  }
  private async counts() {const chunks = await this.store.list(this.state.sessionId ?? undefined); this.update({pending: chunks.length + this.unsaved.size}); return chunks;}
  async recover() {
    if (['ready', 'starting', 'recording', 'paused', 'stopping'].includes(this.state.phase)) return;
    const reservation = this.reservationStore.read();
    if (reservation) {
      this.reservation = reservation;
      this.update({sessionId: reservation.session_id, title: 'Capture navigateur à vérifier', phase: 'pending',
        error: 'Une réservation audio est conservée. Vérifiez sa libération avant de démarrer une autre capture.'});
    }
    const recoveryState = this.state;
    const chunks = await this.store.list();
    if (this.state !== recoveryState) return;
    if (chunks.length) {
      const first = reservation ? chunks.find(chunk => chunk.session_id === reservation.session_id) : chunks[0];
      if (!first) return; // Recover the explicit owner before other sessions' cached audio.
      const sessionChunks = chunks.filter(chunk => chunk.session_id === first.session_id);
      this.update({sessionId: first.session_id, title: 'Audio à récupérer', phase: 'pending', pending: sessionChunks.length,
        tracks: Array.from(new Set(sessionChunks.map(chunk => chunk.track))), totalBytes: sessionChunks.reduce((n, chunk) => n + chunk.blob.size, 0),
        error: 'Des fragments sont conservés sur cet appareil. Synchronisez-les avant de finaliser la séance.'});
    }
  }
  async start(sessionId: string, options: CaptureOptions = {}) {
    if (['ready', 'starting', 'recording', 'paused', 'stopping', 'pending'].includes(this.state.phase)) throw new Error('Une capture ou une récupération est déjà ouverte.');
    if (this.startTask || this.reservationStore.read()) throw new Error('Une réservation audio reste à vérifier.');
    this.stopRequested = false;
    const task = this.runStart(sessionId, options); this.startTask = task;
    try {return await task;} finally {if (this.startTask === task) this.startTask = undefined;}
  }
  async activatePrepared() {
    if (this.state.phase !== 'ready' || !this.prepared || this.startTask) throw new Error('Le partage audio n’est pas prêt.');
    const {session, options} = this.prepared;
    this.stopRequested = false;
    // runStart invokes getDisplayMedia synchronously, before its first await.
    const task = this.runStart(session.id, options, true); this.startTask = task;
    try {return await task;} finally {if (this.startTask === task) this.startTask = undefined;}
  }
  private async releaseReservation() {
    const held = this.reservation;
    if (!held) return;
    const acquiredHere = !this.releaseLock;
    if (acquiredHere) this.releaseLock = await this.environment.lock();
    try {
    if (!held.release) {
      if (!held.acknowledged) {
        let receipt = await this.api.get(held.session_id);
        if (receipt.browser_capture === null && receipt.revision > held.reserve.expected_revision) {
          // With monotonic revisions and the server's writer-side revision
          // check, this old reserve can no longer commit, even if delayed.
          this.reservationStore.clear(); this.reservation = undefined; this.prepared = undefined; return;
        }
        if (receipt.browser_capture?.owner_id !== held.owner_id || !receipt.browser_capture.can_control)
          try {receipt = await this.api.browserReserve(held.session_id, held.reserve);}
          catch (error) {
            const refusal = await this.api.commandReceipt(held.session_id, held.reserve.command_id);
            if (refusal.id !== held.reserve.command_id || refusal.kind !== 'browser.reserve' || refusal.status !== 'rejected') throw error;
            this.reservationStore.clear(); this.reservation = undefined; this.prepared = undefined; return;
          }
        if (receipt.browser_capture?.owner_id !== held.owner_id || !receipt.browser_capture.can_control)
          throw new Error('La réservation audio n’est pas confirmée.');
        held.acknowledged = true; this.reservationStore.write(held);
      }
      const row = await this.api.get(held.session_id);
      held.release = {...sessionCommand(row.revision), owner_id: held.owner_id};
      this.reservationStore.write(held);
    }
    let row: MeetingSession;
    try {row = await this.api.browserRelease(held.session_id, held.release);}
    catch (error) {
      const latest = await this.api.get(held.session_id);
      if (latest.browser_capture?.owner_id !== held.owner_id || !latest.browser_capture.can_control ||
          latest.revision <= held.release.expected_revision) throw error;
      // The stale version cannot commit later. Retry only this same owner,
      // once, with a new command identity and the newly observed revision.
      held.release = {...sessionCommand(latest.revision), owner_id: held.owner_id};
      this.reservationStore.write(held);
      row = await this.api.browserRelease(held.session_id, held.release);
    }
    if (row.browser_capture?.owner_id === held.owner_id) throw new Error('La réservation audio reste active.');
    this.reservationStore.clear(); this.reservation = undefined; this.prepared = undefined;
    } finally {if (acquiredHere) {this.releaseLock?.(); this.releaseLock = undefined;}}
  }
  async cancelPrepared() {
    if (this.state.phase !== 'ready') return;
    this.closeStreams();
    try {
      await this.releaseReservation();
      this.update({phase: 'idle', sessionId: null, tracks: [], error: ''});
    } catch (error) {this.update({phase: 'pending', error: message(error)}); throw error;}
    finally {this.releaseMedia();}
  }
  private async runStart(sessionId: string, options: CaptureOptions, prepared = false) {
    if (!prepared && ['ready', 'starting', 'recording', 'paused', 'stopping', 'pending'].includes(this.state.phase)) throw new Error('Une capture ou une récupération est déjà ouverte.');
    this.update({phase: 'starting', sessionId, error: '', seconds: 0, totalBytes: 0, savedBytes: 0, pending: 0, tracks: []});
    this.durabilityFailed = false; this.sequences.clear(); this.ends.clear(); this.recorders.clear(); this.stops.clear();
    let session: MeetingSession;
    let declaredRecording = false;
    try {
      if (!prepared) {
      await this.store.ready(); this.releaseLock = await this.environment.lock();
      session = await this.api.get(sessionId); this.update({title: session.title, totalBytes: session.total_bytes, savedBytes: session.total_bytes});
      if (!['created', 'paused', 'interrupted'].includes(session.state)) throw new Error('Cette séance ne peut plus démarrer une capture.');
      if ((session.chunks?.length || session.total_bytes) && session.state !== 'created') {
        throw new Error('Conservez et finalisez la capture interrompue, puis démarrez une nouvelle séance.');
      }
      const ownerId = crypto.randomUUID();
      const held: BrowserReservation = {session_id: sessionId, owner_id: ownerId,
        reserve: {...sessionCommand(session.revision), owner_id: ownerId}, acknowledged: false};
      this.reservationStore.write(held); this.reservation = held;
      session = await this.api.browserReserve(sessionId, held.reserve);
      if (session.browser_capture?.owner_id !== ownerId || !session.browser_capture.can_control)
        throw new Error('La réservation audio n’est pas confirmée ; aucun microphone ouvert.');
      held.acknowledged = true; this.reservationStore.write(held);
      if (this.stopRequested) throw new Error('Démarrage audio annulé.');
      this.prepared = {session, options: {...options}};
      if (options.system) {
        this.update({phase: 'ready', tracks: []}); return session;
      }
      } else {
        session = this.prepared!.session;
      }
      const devices = this.environment.devices(); const Recorder = this.environment.recorder();
      if (!devices?.getUserMedia || !Recorder) throw new Error('Capture audio indisponible dans ce navigateur. Importez un fichier.');
      const tracks: [MeetingTrack, MediaStream][] = [];
      if (options.system) {
        if (!devices.getDisplayMedia) throw new Error('La capture système n’est pas disponible dans ce navigateur.');
        const media = await devices.getDisplayMedia({video: true, audio: true}); this.streams.push(media);
        if (!media.getAudioTracks().length) throw new Error('Aucune piste audio système partagée. Choisissez une surface avec son audio.');
        tracks.push(['system', new MediaStream(media.getAudioTracks())]);
      }
      if (this.stopRequested) throw new Error('Démarrage audio annulé.');
      if (options.microphone !== false) {
        const media = await devices.getUserMedia({audio: options.deviceId ? {deviceId: {exact: options.deviceId}} : true});
        this.streams.push(media); tracks.push(['mic', media]);
      }
      if (this.stopRequested) throw new Error('Démarrage audio annulé.');
      if (!tracks.length) throw new Error('Sélectionnez au moins une piste audio.');
      session = await this.api.get(sessionId); // Notes may have changed during the permission dialog.
      if (session.browser_capture?.owner_id !== this.reservation!.owner_id || !session.browser_capture.can_control)
        throw new Error('La réservation audio a changé ; les pistes seront fermées.');
      if (this.stopRequested) throw new Error('Démarrage audio annulé.');
      session = await this.api.command(sessionId, 'resume', {...sessionCommand(session.revision), browser_capture_owner_id: this.reservation!.owner_id});
      if (session.browser_capture?.owner_id !== this.reservation!.owner_id || !session.browser_capture.can_control)
        throw new Error('Le reçu de démarrage ne correspond pas à cette réservation audio.');
      declaredRecording = true;
      if (this.stopRequested) throw new Error('Démarrage audio annulé.');
      this.started = this.environment.now(); this.pausedAt = 0; this.pausedMs = 0;
      for (const [track, media] of tracks) {
        const mimeType = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4'].find(type => Recorder.isTypeSupported?.(type));
        const recorder = new Recorder(media, mimeType ? {mimeType, audioBitsPerSecond: 32000} : {audioBitsPerSecond: 32000});
        const previous = session.chunks?.filter(chunk => chunk.track === track) ?? [];
        this.sequences.set(track, previous.length ? Math.max(...previous.map(chunk => chunk.sequence)) + 1 : 0);
        this.ends.set(track, 0);
        const stopped = new Promise<void>(resolve => {recorder.onstop = () => resolve();});
        recorder.ondataavailable = event => {
          if (!event.data.size) return;
          const seq = this.sequences.get(track)!; this.sequences.set(track, seq + 1);
          const start = this.ends.get(track)!; const end = this.elapsed(); this.ends.set(track, end);
          this.update({totalBytes: this.state.totalBytes + event.data.size});
          const chunk: DurableAudioChunk = {id: `${sessionId}:${track}:${seq}`, session_id: sessionId, track, seq,
              command_id: crypto.randomUUID(), blob: event.data, sha256: '',
              start_ms: Math.round(start), duration_ms: Math.max(0, Math.round(end - start)), created_at: new Date().toISOString()};
          this.unsaved.set(chunk.id, chunk);
          this.persistence = this.persistence.then(async () => {
            chunk.sha256 = await this.environment.hash(event.data);
            await this.store.put(chunk); this.unsaved.delete(chunk.id); await this.counts();
          }).then(() => {void this.syncPending().catch(() => undefined);}).catch(error => {
            this.durabilityFailed = true;
            this.update({pending: Math.max(1, this.state.pending), error: `Un fragment reste en mémoire uniquement. Gardez cette page ouverte et reprenez sa sauvegarde : ${message(error)}`});
            void this.stop().catch(() => undefined);
          });
          if (this.state.totalBytes > (options.maxBytes ?? 512 * 1024 * 1024)) {
            this.update({error: 'Limite de taille atteinte. La partie déjà sauvegardée est conservée.'}); void this.stop().catch(() => undefined);
          }
        };
        recorder.onerror = () => {this.update({error: 'La capture a été interrompue par le navigateur.'}); void this.stop().catch(() => undefined);};
        media.getAudioTracks().forEach(audio => {audio.onended = () => {
          if (['recording', 'paused'].includes(this.state.phase)) {this.update({error: 'Une piste audio a été interrompue.'}); void this.stop().catch(() => undefined);}
        };});
        this.recorders.set(track, recorder); recorder.start(2000); this.stops.set(track, stopped);
      }
      this.update({phase: 'recording', tracks: tracks.map(([track]) => track)});
      this.timer = setInterval(() => {
        this.update({seconds: Math.floor(this.elapsed() / 1000)});
        if (this.elapsed() > (options.maxMinutes ?? 720) * 60_000) {
          this.update({error: 'Durée maximale atteinte. La réunion est conservée.'}); void this.stop().catch(() => undefined);
        }
      }, 1000);
      return session;
    } catch (error) {
      this.recorders.forEach(recorder => {if (recorder.state !== 'inactive') recorder.stop();});
      await Promise.all(this.stops.values()); await this.persistence;
      this.closeStreams(); this.update({phase: 'error', error: message(error)});
      if (declaredRecording) {
        try {
          const latest = await this.api.get(sessionId);
          if (latest.state === 'recording') await this.api.command(sessionId, 'pause', {...sessionCommand(latest.revision), browser_capture_owner_id: this.reservation?.owner_id});
        } catch { /* Keep the original capture error; a network failure must not retain the microphone. */ }
      }
      if (this.reservation) {
        if (this.reservation.acknowledged) {
          try {await this.releaseReservation();}
          catch (releaseError) {this.update({phase: 'pending', error: `${message(error)} · Réservation à libérer : ${message(releaseError)}`});}
        } else this.update({phase: 'pending', error: `${message(error)} · Réservation à vérifier, aucun microphone ouvert.`});
      }
      this.releaseMedia(); throw error;
    }
  }
  async pause() {
    if (this.state.phase !== 'recording' || !this.state.sessionId) return;
    const row = await this.api.get(this.state.sessionId);
    if (row.browser_capture?.owner_id !== this.reservation?.owner_id || !row.browser_capture?.can_control)
      throw new Error('Le propriétaire de cette capture a changé.');
    if (row.state !== 'paused') await this.api.command(row.id, 'pause', {...sessionCommand(row.revision), browser_capture_owner_id: this.reservation?.owner_id});
    const latest = await this.api.get(row.id);
    if (latest.state !== 'paused' || latest.browser_capture?.owner_id !== this.reservation?.owner_id || !latest.browser_capture?.can_control)
      throw new Error('La pause de cette capture n’est pas confirmée.');
    this.recorders.forEach(recorder => {if (recorder.state === 'recording') recorder.pause();});
    this.pausedAt = this.environment.now(); this.update({phase: 'paused'});
  }
  async resume() {
    if (this.state.phase !== 'paused' || !this.state.sessionId) return;
    const row = await this.api.get(this.state.sessionId);
    if (row.browser_capture?.owner_id !== this.reservation?.owner_id || !row.browser_capture?.can_control)
      throw new Error('Le propriétaire de cette capture a changé.');
    if (row.state !== 'recording') await this.api.command(row.id, 'resume', {...sessionCommand(row.revision), browser_capture_owner_id: this.reservation?.owner_id});
    const latest = await this.api.get(row.id);
    if (latest.state !== 'recording' || latest.browser_capture?.owner_id !== this.reservation?.owner_id || !latest.browser_capture?.can_control)
      throw new Error('La reprise de cette capture n’est pas confirmée.');
    this.pausedMs += this.environment.now() - this.pausedAt; this.pausedAt = 0;
    this.recorders.forEach(recorder => {if (recorder.state === 'paused') recorder.resume();}); this.update({phase: 'recording'});
  }
  async syncPending(sessionId = this.state.sessionId) {
    if (!sessionId) return;
    if (this.syncing) return this.syncing;
    this.syncing = (async () => {
      const chunks = await this.store.list(sessionId);
      for (const chunk of chunks) {
        const form = new FormData();
        const extension = chunk.blob.type.includes('mp4') ? 'm4a' : chunk.blob.type.includes('ogg') ? 'ogg' : 'webm';
        form.append('file', chunk.blob, `${chunk.track}-${chunk.seq}.${extension}`); form.append('command_id', chunk.command_id);
        form.append('sha256', chunk.sha256); form.append('start_ms', String(chunk.start_ms)); form.append('duration_ms', String(chunk.duration_ms));
        const receipt = await this.api.chunk(chunk.session_id, chunk.track, chunk.seq, form);
        const accepted = receipt.accepted_chunk;
        if (!receipt.acknowledged || receipt.session_id !== chunk.session_id || accepted?.track !== chunk.track ||
          accepted.seq !== chunk.seq || accepted.sha256 !== chunk.sha256 || accepted.size_bytes !== chunk.blob.size) {
          throw new Error('L’acquittement reçu ne correspond pas au fragment conservé.');
        }
        await this.store.acknowledge(chunk.id);
        this.update({savedBytes: this.state.savedBytes + chunk.blob.size}); await this.counts();
      }
      if (!this.durabilityFailed) this.update({error: ''});
    })().catch(error => {
      this.update({error: `Audio conservé sur cet appareil ; synchronisation à reprendre : ${message(error)}`}); throw error;
    }).finally(() => {this.syncing = undefined;});
    return this.syncing;
  }
  async stop(): Promise<MeetingSession | null> {
    if (this.stopping) return this.stopping;
    if (!this.state.sessionId) return null;
    this.stopRequested = true;
    this.closeStreams(); this.update({phase: 'stopping'});
    this.stopping = (async () => {
      if (this.startTask) {try {await this.startTask;} catch {/* Streams closed by the start error path. */}}
      const sessionId = this.state.sessionId!; this.update({phase: 'stopping'});
      this.recorders.forEach(recorder => {if (recorder.state !== 'inactive') recorder.stop();});
      await Promise.all(this.stops.values()); this.closeStreams(); await this.persistence;
      try {
        await this.releaseReservation();
        await this.syncPending(sessionId);
        if ((await this.store.list(sessionId)).length) await this.syncPending(sessionId);
        if ((await this.store.list(sessionId)).length || this.durabilityFailed) {
          this.update({phase: 'pending'}); return null;
        }
        const row = await this.api.get(sessionId);
        const finalized = row.state === 'completed' ? row : await this.api.command(sessionId, 'finalize', sessionCommand(row.revision));
        this.update({phase: 'completed', error: '', pending: 0});
        return finalized;
      } catch (error) {this.update({phase: 'pending', error: message(error)}); return null;}
      finally {this.releaseMedia();}
    })().finally(() => {this.stopping = undefined;});
    return this.stopping;
  }
  async retryAndFinalize() {
    // An old reservation may belong to a still-open tab. Never release it
    // until this origin's capture lock proves that no such tab holds media.
    if (this.reservation && !this.releaseLock) this.releaseLock = await this.environment.lock();
    for (const chunk of this.unsaved.values()) {
      if (!chunk.sha256) chunk.sha256 = await this.environment.hash(chunk.blob);
      await this.store.put(chunk); this.unsaved.delete(chunk.id);
    }
    this.durabilityFailed = false; await this.counts(); await this.syncPending(); return this.stop();
  }
}

export const meetingCapture = new MeetingCaptureController();
