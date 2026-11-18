import {useEffect, useState, useSyncExternalStore} from 'react';
import {meetingCapture} from '../lib/meetingCapture';
import '../meeting-studio.css';
const errorText = (error: unknown) => error instanceof Error ? error.message : String(error);
const clock = (seconds: number) => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`;

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
