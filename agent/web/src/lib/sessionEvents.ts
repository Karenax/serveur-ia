import { agentFetch } from './agentRoutes';
/** Local read-only notifications. A notification never applies a note or citation. */
export type SessionEvent = {
  id: number; kind: string; data: Record<string, unknown>; revision: number; created_at?: string;
};
export type SessionEventError = {message: string; status?: number; retryable: boolean};
export type SessionEventOptions = {
  after: number; signal: AbortSignal;
  onEvent: (event: SessionEvent) => void;
  onConnected?: () => void;
  onError?: (error: SessionEventError) => void;
};

const MIN_RETRY = 500, MAX_RETRY = 5000, CONNECTION_TIMEOUT = 35_000;
const MAX_BUFFER = 1024 * 1024; // Per-frame decoded characters, independent of transport grouping.
class FeedFailure extends Error {
  constructor(message: string, readonly retryable: boolean, readonly status?: number) {super(message);}
}
const object = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value);
const cursor = (value: number) => Number.isSafeInteger(value) && value >= 0;
function pause(milliseconds: number, signal: AbortSignal): Promise<void> {
  return new Promise(resolve => {
    if (signal.aborted) {resolve(); return;}
    const finish = () => {clearTimeout(timer); signal.removeEventListener('abort', finish); resolve();};
    const timer = setTimeout(finish, milliseconds);
    signal.addEventListener('abort', finish, {once: true});
  });
}

export async function subscribeSessionEvents(id: string, options: SessionEventOptions): Promise<void> {
  const {signal, onEvent, onConnected, onError} = options;
  if (signal.aborted) return;
  if (!id || !cursor(options.after)) {
    onError?.({message: 'Séance ou curseur événement invalide.', retryable: false}); return;
  }
  let after = options.after, retry = MIN_RETRY, failures = 0;
  while (!signal.aborted) {
    const controller = new AbortController();
    const abort = () => controller.abort(signal.reason);
    signal.addEventListener('abort', abort, {once: true});
    let expired = false, reader: ReadableStreamDefaultReader<Uint8Array> | undefined;
    const timeout = setTimeout(() => {expired = true; controller.abort();}, CONNECTION_TIMEOUT);
    const cancelReader = () => {void reader?.cancel().catch(() => undefined);};
    controller.signal.addEventListener('abort', cancelReader, {once: true});
    let failure: SessionEventError | undefined;
    try {
      const query = new URLSearchParams({follow: 'true', after: String(after)});
      const response = await agentFetch(`/api/v1/meeting-sessions/${encodeURIComponent(id)}/events?${query}`, {
        method: 'GET', credentials: 'same-origin', headers: {Accept: 'text/event-stream'}, signal: controller.signal,
      });
      if (!response.ok) {
        const retryable = response.status >= 500 || response.status === 408 || response.status === 429;
        let message = `Lecture des événements indisponible (HTTP ${response.status}).`;
        try {const data: unknown = await response.json(); if (object(data) && typeof data.detail === 'string') message = data.detail.slice(0, 500);}
        catch {/* A non-JSON error keeps its explicit HTTP status. */}
        throw new FeedFailure(message, retryable, response.status);
      }
      if (!response.body || !response.headers.get('content-type')?.toLowerCase().startsWith('text/event-stream')) {
        throw new FeedFailure('Le serveur ne fournit pas un flux d’événements lisible.', false);
      }
      reader = response.body.getReader();
      if (signal.aborted) return;
      if (controller.signal.aborted) throw new FeedFailure('La connexion aux événements a expiré ; reprise en cours.', true);
      if (!signal.aborted) onConnected?.();
      failures = 0;
      const decoder = new TextDecoder('utf-8', {fatal: true});
      let buffer = '';
      const frame = (text: string) => {
        let event = 'message', identifier: string | undefined;
        const parts: string[] = [];
        for (const line of text.split(/\r\n|\r|\n/)) {
          if (!line || line.startsWith(':')) continue;
          const colon = line.indexOf(':');
          const key = colon < 0 ? line : line.slice(0, colon);
          let value = colon < 0 ? '' : line.slice(colon + 1);
          if (value.startsWith(' ')) value = value.slice(1);
          if (key === 'event') event = value;
          else if (key === 'id') identifier = value;
          else if (key === 'data') parts.push(value);
          else if (key === 'retry' && /^\d+$/.test(value)) {
            const requested = Number(value);
            if (Number.isSafeInteger(requested)) retry = Math.max(MIN_RETRY, Math.min(MAX_RETRY, requested));
          }
        }
        if (!parts.length) return; // Heartbeats and ready comments are not notifications.
        if (event === 'stream.denied') {
          let denial: unknown;
          try {denial = JSON.parse(parts.join('\n'));}
          catch {throw new FeedFailure('Contrôle d’accès du flux invalide.', false);}
          if (!object(denial) || (denial.status !== 403 && denial.status !== 404)) {
            throw new FeedFailure('Contrôle d’accès du flux invalide.', false);
          }
          throw new FeedFailure('L’accès à cette séance n’est plus autorisé.', false, denial.status);
        }
        if (!identifier || !/^\d+$/.test(identifier) || !cursor(Number(identifier)) || Number(identifier) === 0) {
          throw new FeedFailure('Identifiant d’événement invalide ; relisez la séance.', false);
        }
        const eventId = Number(identifier);
        if (eventId <= after) return; // Replayed or older IDs never regress the feed.
        let value: unknown;
        try {value = JSON.parse(parts.join('\n'));}
        catch {throw new FeedFailure('Événement incomplet ou incompatible ; relisez la séance.', false);}
        if (!object(value) || typeof value.kind !== 'string' || value.kind !== event || !object(value.data)
            || typeof value.revision !== 'number' || !cursor(value.revision)) {
          throw new FeedFailure('Événement incompatible ; relisez la séance.', false);
        }
        const createdAt = value.created_at;
        if (createdAt !== undefined && (typeof createdAt !== 'string' || !/(?:Z|\+00:00)$/.test(createdAt) || !Number.isFinite(Date.parse(createdAt)))) {
          throw new FeedFailure('Date d’événement UTC invalide ; relisez la séance.', false);
        }
        if (signal.aborted) return;
        onEvent({id: eventId, kind: value.kind, data: value.data, revision: value.revision,
          ...(typeof createdAt === 'string' ? {created_at: createdAt} : {})});
        after = eventId;
      };
      while (!controller.signal.aborted) {
        const {value, done} = await reader.read();
        if (controller.signal.aborted) break;
        try {buffer += done ? decoder.decode() : decoder.decode(value, {stream: true});}
        catch {throw new FeedFailure('Encodage d’événement invalide ; relisez la séance.', false);}
        let match: RegExpMatchArray | null;
        while ((match = buffer.match(/\r\n\r\n|\n\n|\r\r/))) {
          const index = match.index!;
          if (index > MAX_BUFFER) throw new FeedFailure('Événement trop volumineux ; relisez la séance.', false);
          frame(buffer.slice(0, index)); buffer = buffer.slice(index + match[0].length);
        }
        // A delimiter split between reads is framing, not part of the event.
        const delimiterPrefix = buffer.endsWith('\r\n\r') ? 3 : buffer.endsWith('\r\n') ? 2 : /[\r\n]$/.test(buffer) ? 1 : 0;
        if (buffer.length - delimiterPrefix > MAX_BUFFER) throw new FeedFailure('Événement trop volumineux ; relisez la séance.', false);
        if (done) {
          if (buffer.trim() && !buffer.trim().startsWith(':')) throw new FeedFailure('Flux interrompu au milieu d’un événement ; relisez la séance.', true);
          break;
        }
      }
      if (expired && !signal.aborted) throw new FeedFailure('La connexion aux événements a expiré ; reprise en cours.', true);
    } catch (error) {
      if (!signal.aborted) {
        failure = error instanceof FeedFailure ? {message: error.message, retryable: error.retryable,
          ...(error.status !== undefined ? {status: error.status} : {})}
          : {message: expired ? 'La connexion aux événements a expiré ; reprise en cours.' : 'Connexion aux événements interrompue ; reprise en cours.', retryable: true};
      }
    } finally {
      clearTimeout(timeout); signal.removeEventListener('abort', abort);
      controller.signal.removeEventListener('abort', cancelReader);
      if (reader) {await reader.cancel().catch(() => undefined); reader.releaseLock();}
    }
    if (signal.aborted) return;
    if (failure) {
      onError?.(failure);
      if (!failure.retryable) return;
      failures++;
    }
    await pause(Math.min(MAX_RETRY, retry * 2 ** Math.min(failures, 4)), signal);
  }
}
