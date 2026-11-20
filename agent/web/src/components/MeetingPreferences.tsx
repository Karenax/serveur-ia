import {useEffect, useState} from 'react';
import {fusionInsights, type MeetingPreferences as Preferences} from '../lib/fusionInsights';

export function MeetingPreferences({active,onBusy}: {active:boolean;onBusy:(busy:boolean)=>void}) {
  const [saved,setSaved]=useState<Preferences|null>(null);
  const [draft,setDraft]=useState<Preferences|null>(null);
  const [attempt,setAttempt]=useState(0);
  const [saving,setSaving]=useState(false);
  const [error,setError]=useState('');
  const [confirmed,setConfirmed]=useState(false);
  const dirty=!!saved&&!!draft&&JSON.stringify(saved)!==JSON.stringify(draft);
  useEffect(()=>{
    if(!active||saved)return;
    const controller=new AbortController();
    fusionInsights.personal(controller.signal).then(value=>{
      if(!controller.signal.aborted){setSaved(value);setDraft(value);}
    }).catch(problem=>{if(!controller.signal.aborted)setError(String(problem.message||problem));});
    return()=>controller.abort();
  },[active,attempt,saved]);
  useEffect(()=>{onBusy(saving);return()=>onBusy(false);},[onBusy,saving]);

  async function save(){
    if(!draft||!dirty||saving)return;
    setSaving(true);setError('');setConfirmed(false);
    try {
      const value=await fusionInsights.savePersonal(draft);
      setSaved(value);setDraft(value);setConfirmed(true);
      window.dispatchEvent(new Event('agent-fusion-settings-changed'));
    }catch(problem){setError(problem instanceof Error?problem.message:String(problem));}
    finally{setSaving(false);}
  }

  return <section className="card" data-workspace-dirty={dirty?'true':undefined}>
    <h2>Mes réglages de réunion</h2>
    <p>Ces choix s’appliquent aux séances que vous créez, y compris dans un projet partagé.</p>
    {error&&<p role="alert">{error}</p>}
    {!draft&&(error
      ? <button type="button" className="button secondary" onClick={()=>{setError('');setAttempt(value=>value+1);}}>Réessayer</button>
      : <p role="status">Chargement des réglages…</p>)}
    {draft&&<form onSubmit={event=>{event.preventDefault();void save();}}>
      <fieldset className="settings-fields workspace-settings-form" disabled={saving||!active}>
        <label><input type="checkbox" checked={draft.live_transcription_enabled}
          onChange={event=>{setConfirmed(false);setDraft({...draft,live_transcription_enabled:event.target.checked});}}/>
          Transcrire mes réunions en direct</label>
        <label><input type="checkbox" checked={draft.proactive_enabled}
          onChange={event=>{setConfirmed(false);setDraft({...draft,proactive_enabled:event.target.checked});}}/>
          Proposer des réponses aux questions entendues</label>
        <label><input type="checkbox" checked={draft.auto_enhancement_enabled}
          onChange={event=>{setConfirmed(false);setDraft({...draft,auto_enhancement_enabled:event.target.checked});}}/>
          Proposer des enrichissements pour mes notes</label>
        <label>Moteur de l’assistant de réunion<select className="input" value={draft.mode}
          onChange={event=>{setConfirmed(false);setDraft({...draft,mode:event.target.value as Preferences['mode']});}}>
          <option value="network">Moteur du réseau</option>
          <option value="local">Moteur local du service</option>
        </select></label>
        <p>La capture audio et les moteurs doivent être disponibles sur le service Kiara.</p>
        <button type="submit" className="button primary" disabled={!dirty}>Enregistrer mes réglages de réunion</button>
      </fieldset>
    </form>}
    {confirmed&&<p role="status">Réglages personnels enregistrés.</p>}
  </section>;
}
