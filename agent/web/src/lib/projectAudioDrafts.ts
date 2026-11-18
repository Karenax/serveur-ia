import {IndexedAudioChunks, projectChunkIdentity, type DurableAudioChunk, type ProjectChunkIdentity} from './meetingAudioStore';
import {joinPcmWaves} from './pcmAudioRecorder';
import {projectAudioPrefix, projectAudioSession} from './projectAudioId';

type DraftStore = Pick<IndexedAudioChunks, 'ready' | 'addProjectChunk' | 'listProjectSessions' | 'list' | 'deleteProjectIfUnchanged'>;
type Digest = (blob: Blob) => Promise<string>;
type Seal = {version:1; sessionId:string; count:number; manifest:string; createdAt:string};
export type VerifiedProjectAudio = {recording_id:string; source_id:string; sha256:string; size:number};
const sealKey = (sessionId:string) => `kiara-project-audio-complete-v1:${sessionId}`;

async function bytes(blob: Blob): Promise<ArrayBuffer> {
  if (typeof blob.arrayBuffer === 'function') return blob.arrayBuffer();
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => reader.result instanceof ArrayBuffer ? resolve(reader.result) : reject(new Error('Audio local illisible.'));
    reader.onerror = () => reject(new Error('Audio local illisible.'));
    reader.readAsArrayBuffer(blob);
  });
}

async function sha256(blob: Blob) {
  if (!globalThis.crypto?.subtle) throw new Error('Vérification audio indisponible.');
  const digest = await crypto.subtle.digest('SHA-256', await bytes(blob));
  return Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, '0')).join('');
}

function checkedSession(operatorId: string, projectId: string, sessionId: string) {
  const prefix = projectAudioPrefix(operatorId, projectId);
  if (typeof sessionId !== 'string' || !sessionId.startsWith(prefix) ||
      projectAudioSession(operatorId, projectId, sessionId.slice(prefix.length)) !== sessionId) {
    throw new Error('Capture audio hors du projet ou du compte.');
  }
}

async function pcmRate(blob: Blob) {
  const data = await bytes(blob.slice(0, 44));
  if (data.byteLength !== 44) throw new Error('Fragment WAV incomplet.');
  const view = new DataView(data);
  const name = (start: number, length: number) => String.fromCharCode(...new Uint8Array(data, start, length));
  const rate = view.getUint32(24, true);
  if (name(0, 4) !== 'RIFF' || name(8, 4) !== 'WAVE' || name(12, 4) !== 'fmt ' || name(36, 4) !== 'data' ||
      view.getUint32(4, true) !== blob.size - 8 || view.getUint32(16, true) !== 16 ||
      view.getUint16(20, true) !== 1 || view.getUint16(22, true) !== 1 || view.getUint16(34, true) !== 16 ||
      !rate || view.getUint32(28, true) !== rate * 2 || view.getUint16(32, true) !== 2 ||
      view.getUint32(40, true) !== blob.size - 44) throw new Error('Fragment WAV invalide.');
  return rate;
}

/** Project captures use the established chunk schema; cleanup requires a completed and verified copy. */
export class ProjectAudioDrafts {
  constructor(private readonly store: DraftStore = new IndexedAudioChunks(), private readonly digest: Digest = sha256,
              private readonly storage: () => Storage = () => localStorage) {}

  async ready() {await this.store.ready();}

  create(operatorId: string, projectId: string) {
    if (!globalThis.crypto?.randomUUID) throw new Error('Création de capture indisponible.');
    return projectAudioSession(operatorId, projectId, crypto.randomUUID());
  }

  async append(operatorId: string, projectId: string, sessionId: string, seq: number, blob: Blob,
               startMs: number, durationMs: number) {
    checkedSession(operatorId, projectId, sessionId);
    if (!Number.isSafeInteger(seq) || seq < 0 || !Number.isSafeInteger(startMs) || startMs < 0 ||
        !Number.isSafeInteger(durationMs) || durationMs < 0 || !(blob instanceof Blob) || !blob.size || !blob.type ||
        blob.size > 256 * 1024 * 1024 || blob.type.length > 256 || !globalThis.crypto?.randomUUID) {
      throw new Error('Fragment audio invalide.');
    }
    const hash = await this.digest(blob);
    if (!/^[0-9a-f]{64}$/.test(hash)) throw new Error('Empreinte audio invalide.');
    const chunk: DurableAudioChunk = {id: `${sessionId}:mic:${seq}`, session_id: sessionId, track: 'mic', seq,
      command_id: crypto.randomUUID(), blob, sha256: hash, start_ms: startMs, duration_ms: durationMs,
      created_at: new Date().toISOString()};
    await this.store.addProjectChunk(chunk);
    return chunk;
  }

  async list(operatorId: string, projectId: string) {
    const sessions = await this.store.listProjectSessions(projectAudioPrefix(operatorId, projectId));
    for (const session of sessions) {
      checkedSession(operatorId, projectId, session.sessionId);
      if (!Number.isSafeInteger(session.count) || session.count < 1) throw new Error('Inventaire audio invalide.');
    }
    return sessions;
  }

  private async reconstruct(operatorId: string, projectId: string, sessionId: string) {
    checkedSession(operatorId, projectId, sessionId);
    const chunks = (await this.store.list(sessionId)).slice().sort((a, b) => a.seq - b.seq);
    if (!chunks.length) throw new Error('Audio local introuvable.');
    const mime = chunks[0].blob?.type;
    if (!mime || mime.length > 256) throw new Error('Type audio local invalide.');
    let total = 0, rate: number | undefined;
    for (let seq = 0; seq < chunks.length; seq++) {
      const chunk = chunks[seq];
      if (chunk.session_id !== sessionId || chunk.id !== `${sessionId}:mic:${seq}` || chunk.seq !== seq || chunk.track !== 'mic' ||
          !(chunk.blob instanceof Blob) || !chunk.blob.size || chunk.blob.type !== mime ||
          typeof chunk.command_id !== 'string' || !chunk.command_id || typeof chunk.created_at !== 'string' || !Number.isFinite(Date.parse(chunk.created_at)) ||
          !Number.isSafeInteger(chunk.start_ms) || chunk.start_ms < 0 || !Number.isSafeInteger(chunk.duration_ms) || chunk.duration_ms < 0 ||
          !/^[0-9a-f]{64}$/.test(chunk.sha256) || await this.digest(chunk.blob) !== chunk.sha256) {
        throw new Error('Fragment audio local incomplet ou modifié.');
      }
      total += chunk.blob.size;
      if (total > 256 * 1024 * 1024) throw new Error('Audio local trop volumineux.');
      if (mime === 'audio/wav') {
        const current = await pcmRate(chunk.blob);
        if (rate !== undefined && current !== rate) throw new Error('Fréquences audio incompatibles.');
        rate = current;
      }
    }
    const blob = mime === 'audio/wav' ? joinPcmWaves(chunks.map(chunk => chunk.blob), rate!) : new Blob(chunks.map(chunk => chunk.blob), {type: mime});
    return {blob, createdAt: chunks[0].created_at, count: chunks.length, identities: chunks.map(projectChunkIdentity)};
  }

  async read(operatorId: string, projectId: string, sessionId: string) {
    const {blob, createdAt, count} = await this.reconstruct(operatorId, projectId, sessionId);
    return {blob, createdAt, count};
  }

  private async manifest(identities: readonly ProjectChunkIdentity[]) {
    return this.digest(new Blob([JSON.stringify(identities)], {type:'application/json'}));
  }

  private getSeal(operatorId:string, projectId:string, sessionId:string): Seal | null {
    checkedSession(operatorId, projectId, sessionId);
    const raw = this.storage().getItem(sealKey(sessionId));
    if (raw === null) return null;
    let seal: Seal;
    try {seal = JSON.parse(raw) as Seal;} catch {throw new Error('La fin de la capture locale ne peut pas être vérifiée.');}
    if (!seal || seal.version !== 1 || seal.sessionId !== sessionId || !Number.isSafeInteger(seal.count) || seal.count < 1 ||
        !/^[a-f0-9]{64}$/.test(seal.manifest) || typeof seal.createdAt !== 'string' || !Number.isFinite(Date.parse(seal.createdAt))) {
      throw new Error('La fin de la capture locale ne peut pas être vérifiée.');
    }
    return seal;
  }

  isSealed(operatorId:string, projectId:string, sessionId:string) {
    return this.getSeal(operatorId, projectId, sessionId) !== null;
  }

  /** Called only after the recorder has stopped and every fragment was persisted. */
  async seal(operatorId:string, projectId:string, sessionId:string) {
    const capture = await this.reconstruct(operatorId, projectId, sessionId);
    const seal: Seal = {version:1, sessionId, count:capture.count, manifest:await this.manifest(capture.identities), createdAt:capture.createdAt};
    const key = sealKey(sessionId), value = JSON.stringify(seal), storage = this.storage();
    const old = storage.getItem(key);
    if (old !== null && old !== value) throw new Error('Une fin de capture différente est déjà conservée.');
    if (old === null) storage.setItem(key, value);
    if (storage.getItem(key) !== value) throw new Error('La fin de la capture ne peut pas être confirmée.');
  }

  /** Keep local fragments unless the completed capture and live server copy match exactly. */
  async releaseVerified(operatorId:string, projectId:string, sessionId:string, receipt:VerifiedProjectAudio,
                        recordingId:string, sourceId:string, revalidate:()=>Promise<void>) {
    const seal = this.getSeal(operatorId, projectId, sessionId);
    if (!seal) throw new Error('La fin de cette capture n’a pas été confirmée. La copie locale est conservée.');
    if (!recordingId || !sourceId || !receipt || receipt.recording_id !== recordingId || receipt.source_id !== sourceId ||
        !/^[a-f0-9]{64}$/.test(receipt.sha256) || !Number.isSafeInteger(receipt.size) || receipt.size < 1) {
      throw new Error('La copie sur le serveur ne peut pas être vérifiée. La copie locale est conservée.');
    }
    const capture = await this.reconstruct(operatorId, projectId, sessionId);
    if (capture.count !== seal.count || capture.createdAt !== seal.createdAt || await this.manifest(capture.identities) !== seal.manifest ||
        capture.blob.size !== receipt.size || await this.digest(capture.blob) !== receipt.sha256) {
      throw new Error('Les copies audio ne correspondent pas. La copie locale est conservée.');
    }
    await revalidate();
    await this.store.deleteProjectIfUnchanged(sessionId, capture.identities);
    // A stale seal is harmless if this cleanup fails after the atomic deletion.
    try {this.storage().removeItem(sealKey(sessionId));} catch { /* Keep the already verified server copy. */ }
  }
}
