import {useEffect,useRef,useState} from 'react';
import {meetingSessions,type LiveTranscriptSegment,type MeetingSession} from '../lib/meetingSessions';
export function MeetingTranscriptEdit({session,segment,onChanged}:{session:MeetingSession;segment:LiveTranscriptSegment;onChanged:(row:MeetingSession)=>void}){
  const [editing,setEditing]=useState(false),[text,setText]=useState(segment.text),[speaker,setSpeaker]=useState(segment.speaker||'Voix à identifier');
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[conflict,setConflict]=useState(false);
  const saving=useRef(false);
  const [pending,setPending]=useState<Parameters<typeof meetingSessions.editSegment>[2]|null>(null);
  const dirty=editing&&(busy||!!pending||text!==segment.text||speaker!==(segment.speaker||'Voix à identifier'));
  useEffect(()=>{
    if(!dirty)return;
    const protect=(event:BeforeUnloadEvent)=>{event.preventDefault();event.returnValue='';};
    window.addEventListener('beforeunload',protect);
    return()=>window.removeEventListener('beforeunload',protect);
  },[dirty]);
  if(!editing)return <><p>{segment.text}</p><button type="button" disabled={session.state==='cancelled'} onClick={()=>{setText(segment.text);setSpeaker(segment.speaker||'Voix à identifier');setEditing(true);}}>Corriger ce passage</button></>;
  const save=async()=>{
    if(saving.current)return;
    const body=pending||{command_id:crypto.randomUUID(),expected_session_revision:session.revision,expected_segment_revision:segment.revision,text:text.trim(),speaker:speaker.trim()};
    // A second event can arrive before React has disabled the button.
    saving.current=true;setBusy(true);setError('');setPending(body);
    try{const row=await meetingSessions.editSegment(session.id,segment.id,body);onChanged(row);setEditing(false);setPending(null);}
    catch(failure){setError(String((failure as Error).message));
      try{const remote=await meetingSessions.get(session.id);onChanged(remote);const current=remote.segments?.find(item=>item.id===segment.id);
        if(remote.revision!==body.expected_session_revision||current?.revision!==body.expected_segment_revision)setConflict(true);
      }catch{/* Keep the exact payload available for retry. */}
    }finally{saving.current=false;setBusy(false);}
  };
  return <div className="meeting-transcript-edit" data-workspace-dirty={dirty?'true':undefined}><label>Texte corrigé<textarea maxLength={10000} value={text} disabled={busy||!!pending&&!conflict} onChange={event=>setText(event.target.value)}/></label>
    <label>Intervenant<input maxLength={120} value={speaker} disabled={busy||!!pending&&!conflict} onChange={event=>setSpeaker(event.target.value)}/></label>
    <p>La correction conserve le timecode et reste soumise à relecture avant publication.</p>
    {error&&<p role="alert">{error}</p>}{conflict&&<><p role="alert">Ce passage ou la séance a changé. Votre correction reste conservée.</p><blockquote>{segment.text}</blockquote>
      <button type="button" onClick={()=>{setPending(null);setConflict(false);}}>Reprendre ma saisie sur la version affichée</button></>}
    <button type="button" disabled={busy||conflict||!text.trim()||!speaker.trim()} onClick={()=>void save()}>{pending?'Reprendre la correction':'Enregistrer cette correction'}</button>
    {!pending&&<button type="button" disabled={busy} onClick={()=>setEditing(false)}>Fermer la correction</button>}
  </div>;
}
