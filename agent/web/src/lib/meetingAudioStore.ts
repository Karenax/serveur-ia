import type {MeetingTrack} from './meetingSessions';
import {isLinuxWebKit} from './pcmAudioRecorder';
import {isProjectAudioSession} from './projectAudioId';

export type DurableAudioChunk = {
  id: string; session_id: string; track: MeetingTrack; seq: number; command_id: string; blob: Blob;
  sha256: string; start_ms: number; duration_ms: number; created_at: string;
};
export interface DurableChunkStore {
  ready(): Promise<void>;
  put(chunk: DurableAudioChunk): Promise<void>;
  list(sessionId?: string): Promise<DurableAudioChunk[]>;
  listStudio?(): Promise<DurableAudioChunk[]>;
  acknowledge(id: string): Promise<void>;
}

type StoredAudioChunk = DurableAudioChunk & {stableBytes?: ArrayBuffer; stableMime?: string};
export type ProjectChunkIdentity = {id:string; session_id:string; track:MeetingTrack; seq:number; command_id:string;
  sha256:string; start_ms:number; duration_ms:number; created_at:string; size:number; mime:string};

export function projectChunkIdentity(chunk: StoredAudioChunk): ProjectChunkIdentity {
  return {id:chunk.id, session_id:chunk.session_id, track:chunk.track, seq:chunk.seq, command_id:chunk.command_id,
    sha256:chunk.sha256, start_ms:chunk.start_ms, duration_ms:chunk.duration_ms, created_at:chunk.created_at,
    size:chunk.stableBytes instanceof ArrayBuffer ? chunk.stableBytes.byteLength : chunk.blob?.size ?? -1,
    mime:(chunk.stableBytes instanceof ArrayBuffer ? chunk.stableMime || chunk.blob?.type : chunk.blob?.type) ?? ''};
}

function restored(chunks: StoredAudioChunk[]): DurableAudioChunk[] {
  return chunks.map(chunk => {
    if (!(chunk.stableBytes instanceof ArrayBuffer)) return chunk;
    const {stableBytes, stableMime, ...legacy} = chunk;
    return {...legacy, blob: new Blob([stableBytes], {type: stableMime || chunk.blob?.type || 'application/octet-stream'})};
  }).sort((a, b) => a.track.localeCompare(b.track) || a.seq - b.seq);
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
      request.onblocked = () => reject(new Error('Fermez les autres pages Kiara pour ouvrir le stockage audio.'));
    }).catch(error => {this.opening = undefined; throw error;});
    return this.opening;
  }
  async ready() {await this.database();}
  private async write(chunk: DurableAudioChunk, overwrite: boolean) {
    const db = await this.database();
    let stored: StoredAudioChunk = chunk;
    if (isLinuxWebKit(navigator.userAgent)) {
      // Some WebKitGTK versions restore a Blob with its old size but no bytes.
      // Keep the legacy Blob for older clients and a byte copy for safe recovery.
      const stableBytes = await chunk.blob.arrayBuffer();
      if (stableBytes.byteLength !== chunk.blob.size) throw new Error('Le fragment audio local ne peut pas être relu.');
      stored = {...chunk, stableBytes, stableMime: chunk.blob.type};
    }
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction('chunks', 'readwrite');
      if (overwrite) tx.objectStore('chunks').put(stored); else tx.objectStore('chunks').add(stored);
      tx.oncomplete = () => resolve();
      tx.onerror = tx.onabort = () => reject(new Error('Le fragment audio n’a pas pu être sauvegardé sur cet appareil.'));
    });
  }
  async put(chunk: DurableAudioChunk) {await this.write(chunk, true);}
  /** A collision must preserve the existing fragment. */
  async addProjectChunk(chunk: DurableAudioChunk) {
    if (!isProjectAudioSession(chunk.session_id)) throw new Error('Capture de projet invalide.');
    await this.write(chunk, false);
  }
  private read(request: IDBRequest<StoredAudioChunk[]>) {
    return new Promise<DurableAudioChunk[]>((resolve, reject) => {
      request.onsuccess = () => resolve(restored(request.result));
      request.onerror = () => reject(new Error('Les fragments audio conservés ne peuvent pas être lus.'));
    });
  }
  async list(sessionId?: string) {
    const db = await this.database();
    const store = db.transaction('chunks', 'readonly').objectStore('chunks');
    return this.read(sessionId ? store.index('session_id').getAll(sessionId) : store.getAll());
  }
  /** Inspect session keys first so unrelated project recordings are never loaded into the studio. */
  async listStudio() {
    const db = await this.database();
    return new Promise<DurableAudioChunk[]>((resolve, reject) => {
      const tx = db.transaction('chunks', 'readonly');
      const index = tx.objectStore('chunks').index('session_id');
      const cursor = index.openKeyCursor(undefined, 'nextunique');
      const chunks: StoredAudioChunk[] = [];
      cursor.onsuccess = () => {
        const item = cursor.result;
        if (!item) return;
        if (typeof item.key !== 'string') {tx.abort(); return;}
        if (!isProjectAudioSession(item.key)) {
          const read = index.getAll(item.key);
          read.onsuccess = () => {for (const chunk of read.result) chunks.push(chunk);};
        }
        item.continue();
      };
      tx.oncomplete = () => resolve(restored(chunks));
      tx.onerror = tx.onabort = () => reject(new Error('Les fragments de séance ne peuvent pas être lus.'));
    });
  }
  async listProjectSessions(prefix: string) {
    if (!isProjectAudioSession(prefix)) throw new Error('Capture de projet invalide.');
    const db = await this.database();
    return new Promise<{sessionId: string; count: number}[]>((resolve, reject) => {
      const tx = db.transaction('chunks', 'readonly');
      const index = tx.objectStore('chunks').index('session_id');
      const request = index.openKeyCursor(IDBKeyRange.bound(prefix, prefix + '\uffff'));
      const sessions = new Map<string, number>();
      request.onsuccess = () => {
        const cursor = request.result;
        if (!cursor) return;
        if (typeof cursor.key !== 'string' || !cursor.key.startsWith(prefix)) {tx.abort(); return;}
        sessions.set(cursor.key, (sessions.get(cursor.key) ?? 0) + 1);
        if (sessions.size > 10000) {tx.abort(); return;}
        cursor.continue();
      };
      tx.oncomplete = () => resolve([...sessions].map(([sessionId, count]) => ({sessionId, count})));
      tx.onerror = tx.onabort = () => reject(new Error('Les captures de projet ne peuvent pas être inventoriées.'));
    });
  }
  /** Delete exactly the previously verified project fragments in one transaction. */
  async deleteProjectIfUnchanged(sessionId: string, expected: readonly ProjectChunkIdentity[]) {
    if (!isProjectAudioSession(sessionId) || !expected.length || expected.some(chunk => chunk.session_id !== sessionId)) {
      throw new Error('Capture de projet invalide.');
    }
    const db = await this.database();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction('chunks', 'readwrite');
      const store = tx.objectStore('chunks');
      const request = store.index('session_id').getAll(sessionId);
      request.onsuccess = () => {
        try {
          const rows = request.result as StoredAudioChunk[];
          const actual = rows.map(projectChunkIdentity).sort((a,b)=>a.seq-b.seq);
          if (JSON.stringify(actual) !== JSON.stringify(expected)) {tx.abort(); return;}
          for (const row of rows) store.delete(row.id);
        } catch {tx.abort();}
      };
      tx.oncomplete = () => resolve();
      tx.onerror = tx.onabort = () => reject(new Error('La copie locale a changé ou ne peut pas être libérée. Elle est conservée.'));
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
