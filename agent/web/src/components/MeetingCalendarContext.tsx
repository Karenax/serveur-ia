import {useState} from 'react';
import {fusionSources,type CalendarEvent} from '../lib/fusionSources';
import {meetingSessions,sessionCommand,type MeetingSession} from '../lib/meetingSessions';
export function MeetingCalendarContext({session,onChanged}:{session:MeetingSession;onChanged:(session:MeetingSession)=>void}){
  const [file,setFile]=useState<File|null>(null),[events,setEvents]=useState<CalendarEvent[]>([]),[uid,setUid]=useState('');
  const [error,setError]=useState(''),[busy,setBusy]=useState(false),[command,setCommand]=useState<{command_id:string;expected_revision:number}|null>(null);
  return <details className="meeting-calendar"><summary>Contexte du calendrier</summary><p>Choisissez un événement du fichier ICS pour joindre son contexte à la séance.</p>
    {session.calendar_context&&<p>Un contexte de calendrier est conservé pour cette séance.</p>}
    <label>Calendrier ICS<input type="file" accept=".ics,text/calendar" disabled={busy||!!command} onChange={event=>{
      const selected=event.target.files?.[0];event.target.value='';if(!selected)return;setBusy(true);setError('');
      void fusionSources.calendar(selected).then(result=>{setFile(selected);setEvents(result.events);setUid('');}).catch(failure=>setError(String(failure.message||failure))).finally(()=>setBusy(false));
    }}/></label>
    {events.length>0&&<><label>Événement à joindre<select value={uid} disabled={busy||!!command} onChange={event=>setUid(event.target.value)}>
      <option value="">Choisir un événement</option>{events.map(item=><option key={item.uid} value={item.uid}>{item.summary||'Événement'} · {item.dtstart||'Date non précisée'}</option>)}</select></label>
      {events.filter(item=>item.uid===uid).map(item=><div key={item.uid}><p>{item.description}</p><p>{item.location}</p><p>{item.attendees?.map(attendee=>attendee.value.replace(/^mailto:/i,'')).join(' · ')}</p></div>)}
      <p>Dates et participants sont des métadonnées du calendrier. Relisez-les avant d’en déduire des faits sur la réunion.</p>
      <button type="button" disabled={!uid||!file||busy} onClick={()=>{if(!file)return;const frozen=command||sessionCommand(session.revision);setCommand(frozen);setBusy(true);setError('');
        const form=new FormData();form.append('file',file);form.append('uid',uid);form.append('command_id',frozen.command_id);form.append('expected_revision',String(frozen.expected_revision));
        void meetingSessions.calendar(session.id,form).then(row=>{onChanged(row);setCommand(null);setFile(null);setEvents([]);}).catch(failure=>setError(String(failure.message||failure))).finally(()=>setBusy(false));
      }}>{busy?'Lecture…':command?'Reprendre le rattachement':'Joindre cet événement à la séance'}</button></>}
    {error&&<p role="alert">{error}</p>}
  </details>;
}
