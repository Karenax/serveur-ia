import type {SessionCommand} from './meetingSessions';

export type BrowserReservationCommand = SessionCommand & {owner_id: string};
export type BrowserReservation = {
  session_id: string; owner_id: string; reserve: BrowserReservationCommand;
  acknowledged: boolean; release?: BrowserReservationCommand;
};
export interface BrowserReservationStore {
  read(): BrowserReservation | null;
  write(value: BrowserReservation): void;
  clear(): void;
}
const key = 'agent.browser-capture-reservation.v1';
/** Persist identifiers before a request; reloading never reopens audio. */
export class LocalBrowserReservation implements BrowserReservationStore {
  read() {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const value = JSON.parse(raw) as BrowserReservation;
    const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    const validCommand = (body: BrowserReservationCommand | undefined) => !!body &&
      uuid.test(body.command_id) && body.owner_id === value.owner_id &&
      Number.isInteger(body.expected_revision) && body.expected_revision >= 1;
    if (!value || typeof value.session_id !== 'string' || !uuid.test(value.owner_id) ||
        typeof value.acknowledged !== 'boolean' || !validCommand(value.reserve) ||
        (value.release !== undefined && !validCommand(value.release))) {
      throw new Error('La réservation audio conservée doit être vérifiée ; aucun microphone ne sera ouvert.');
    }
    return value;
  }
  write(value: BrowserReservation) {localStorage.setItem(key, JSON.stringify(value));}
  clear() {localStorage.removeItem(key);}
}
