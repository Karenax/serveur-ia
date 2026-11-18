import {useCallback, useRef, useState, type Dispatch, type RefObject, type SetStateAction} from 'react';
import {meetingSessions, type MeetingSession} from '../lib/meetingSessions';
import {blankNote, validNoteContent, type NoteContent} from '../lib/projectNotes';

export const meetingErrorText = (error: unknown) => error instanceof Error ? error.message : String(error);
export class SessionReadFailure extends Error {
  constructor(failure: unknown) {super(meetingErrorText(failure)); this.name = 'SessionReadFailure';}
}
export const meetingNoteFrom = (row: MeetingSession) => row.note ?? row.staged_note;
export const meetingDraftKey = (id: string) => `agent.meeting-note.v1.${id}`;

/** Own the canonical session snapshot and the local note that must survive refreshes. */
export function useMeetingSessionSnapshot(sessionId: string, alive: RefObject<boolean>, setError: Dispatch<SetStateAction<string>>) {
  const [session, setSession] = useState<MeetingSession | null>(null);
  const [content, setContent] = useState<NoteContent>(blankNote);
  const [noteTitle, setNoteTitle] = useState('');
  const draftRef = useRef({content: blankNote(), title: ''});
  const [dirty, setDirty] = useState(false);
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
  const [sessionReadError, setSessionReadError] = useState('');
  const pendingNote = useRef<Parameters<typeof meetingSessions.saveNote>[1] | null>(null);
  const [project, setProject] = useState('');

  const accept = useCallback((row: MeetingSession) => {
    if (row.id !== currentSessionId.current) return false;
    const previous = rowRef.current;
    if (previous?.id === row.id && (row.revision < previous.revision ||
        (row.event_cursor !== undefined && previous.event_cursor !== undefined && row.event_cursor < previous.event_cursor))) return false;
    if (previous && previous.id !== row.id) {dirtyRef.current = false; setDirty(false); pendingNote.current = null; setNoteConflict(false); setRecovered(false);}
    rowRef.current = row; setSession(row); setProject(row.project_id || '');
    const note = meetingNoteFrom(row);
    if (!dirtyRef.current) {const next = {content: note?.content ?? blankNote(), title: note?.title || row.title};
      draftRef.current = next; setContent(next.content); setNoteTitle(next.title);}
    else if (previous && row.note_id && previous.note_version_id !== row.note_version_id) setNoteConflict(true);
    if (restoredDraftSession.current !== row.id) {
      restoredDraftSession.current = row.id;
      try {
        const raw = localStorage.getItem(meetingDraftKey(row.id));
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
  }, [setError]);
  const readSession = useCallback(async (signal?: AbortSignal, quiet = false) => {
    const sequence = ++sessionReadSequence.current;
    try {
      const row = await (quiet ? meetingSessions.get(sessionId, signal, true) : signal ? meetingSessions.get(sessionId, signal) : meetingSessions.get(sessionId));
      if (!signal?.aborted && alive.current && currentSessionId.current === sessionId && sequence >= acceptedReadSequence.current && accept(row)) {
        acceptedReadSequence.current = sequence;
        if (sequence >= readOutcomeSequence.current) {readOutcomeSequence.current = sequence; setSessionReadError('');}
      }
      return rowRef.current?.id === sessionId ? rowRef.current : row;
    } catch (failure) {
      if (!signal?.aborted && alive.current && currentSessionId.current === sessionId && sequence >= readOutcomeSequence.current) {
        readOutcomeSequence.current = sequence; setSessionReadError(meetingErrorText(failure));
      }
      throw new SessionReadFailure(failure);
    }
  }, [sessionId, accept, alive]);

  return {session, content, setContent, noteTitle, setNoteTitle, draftRef, dirty, setDirty, dirtyRef, rowRef,
    currentSessionId, noteConflict, setNoteConflict, recovered, setRecovered, sessionReadError, pendingNote,
    project, setProject, accept, readSession};
}
