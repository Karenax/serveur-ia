import type {MeetingSession} from './meetingSessions';

export type NativeCapturePhase = 'starting' | 'interrupted' | 'unknown' | 'stopped' | 'paused' | 'recording';

const SESSION_STATES: Record<string, string> = {created: 'À préparer', recording: 'Enregistrement', paused: 'En pause',
  finalizing: 'Consolidation', completed: 'Conservée', interrupted: 'Interrompue', cancelled: 'Arrêtée'};

export function nativeSessionPhase(row:MeetingSession):NativeCapturePhase|null {
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

export function sessionStateLabel(row:MeetingSession){
  const phase=nativeSessionPhase(row);
  if(phase)return {starting:'Ouverture audio en cours',interrupted:'Capture interrompue · conservation à vérifier',
    unknown:'État audio à vérifier',stopped:'Capture arrêtée · conservation à vérifier',paused:'En pause',recording:'Enregistrement'}[phase];
  return SESSION_STATES[row.state]||row.state;
}

export function sessionCaptureNotice(row:MeetingSession){
  const phase=nativeSessionPhase(row);
  if(phase==='starting')return 'L’ouverture audio est en cours.';
  if(phase&&['interrupted','unknown','stopped'].includes(phase))return 'La capture audio et sa conservation restent à vérifier.';
  if(phase==='paused')return 'L’enregistrement est en pause.';
  return row.state==='recording'?'L’enregistrement continue.':row.state==='paused'?'L’enregistrement est en pause.':
    row.state==='completed'?'L’enregistrement est terminé et conservé.':'Les fragments audio restent conservés.';
}
