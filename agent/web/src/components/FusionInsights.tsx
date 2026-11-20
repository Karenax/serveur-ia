import { useEffect, useState } from 'react';
import type { PortfolioRow } from '../lib/api';
import { fusionInsights, type FusionSettings, type FusionStats } from '../lib/fusionInsights';
import { meetingCapture } from '../lib/meetingCapture';
import {FusionReadiness,generationState,generationPlacement} from './FusionReadiness';
import '../fusion-library.css';
const fail=(error:unknown)=>error instanceof Error?error.message:String(error);
const number=(value:number|null|undefined)=>value==null?'Indisponible':new Intl.NumberFormat('fr-FR',{maximumFractionDigits:2}).format(value);
const bytes=(value:number|null|undefined)=>value==null?'Indisponible':`${number(value/1024/1024)} Mo`;
const engineReady=(engine:Record<string,unknown>|undefined)=>engine?.ready===true?'Prêt':engine?.ready===false?'Indisponible':'Non qualifié';
export function FusionInsights({rows,active=true,initialTab='stats'}:{rows:PortfolioRow[];active?:boolean;initialTab?:'stats'|'preparation'}){
  const tab=initialTab;
  const [project,setProject]=useState(''),[stats,setStats]=useState<FusionStats|null>(null);
  const [settings,setSettings]=useState<FusionSettings|null>(null),[draft,setDraft]=useState<Pick<FusionSettings,'enabled'|'live_transcription_enabled'|'live_speech_device'|'proactive_enabled'|'auto_enhancement_enabled'|'mode'|'onboarding_complete'>|null>(null);
  const [loading,setLoading]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false),[tick,setTick]=useState(0);
  const brain=rows.find(row=>row.id===project)?.brain_project_id||undefined;
  const canEdit=settings?.can_edit!==false;
  useEffect(()=>{
    if(!active)return;const controller=new AbortController();setLoading(true);setError('');
    void Promise.allSettled([fusionInsights.stats(brain,controller.signal),fusionInsights.settings(controller.signal)]).then(([value,result])=>{
      if(controller.signal.aborted)return;if(value.status==='fulfilled')setStats(value.value);else setError(fail(value.reason));
      if(result.status==='fulfilled'){const config=result.value;setSettings(config);setDraft(previous=>previous??{
        enabled:config.enabled,live_transcription_enabled:config.live_transcription_enabled??false,...(config.live_speech_device?{live_speech_device:config.live_speech_device}:{}),proactive_enabled:config.proactive_enabled,auto_enhancement_enabled:config.auto_enhancement_enabled??false,mode:config.mode,onboarding_complete:config.onboarding_complete});}
      else if(initialTab==='preparation')setError(fail(result.reason));
    }).catch(failure=>{if(!controller.signal.aborted)setError(fail(failure));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return()=>controller.abort();
  },[active,brain,tick]);
  const save=async(complete=false)=>{
    if(!draft||!canEdit||busy)return;
    const capture=meetingCapture.getSnapshot();
    if(!draft.enabled&&(capture.pending>0||['starting','recording','paused','stopping','pending'].includes(capture.phase))){
      setNotice('');
      setError('Une capture navigateur est en cours ou reste à synchroniser. Dans la barre de capture, utilisez « Arrêter et conserver » puis, si nécessaire, « Synchroniser et finaliser » avant de désactiver l’espace de séance.');
      return;
    }
    setBusy(true);setError('');setNotice('');
    try{const config=await fusionInsights.save({...draft,onboarding_complete:complete||draft.onboarding_complete});setSettings(config);
      setDraft({enabled:config.enabled,live_transcription_enabled:config.live_transcription_enabled??false,...(config.live_speech_device?{live_speech_device:config.live_speech_device}:{}),proactive_enabled:config.proactive_enabled,auto_enhancement_enabled:config.auto_enhancement_enabled??false,mode:config.mode,onboarding_complete:config.onboarding_complete});
      window.dispatchEvent(new Event('agent-fusion-settings-changed'));
      setNotice(complete?'Préparation enregistrée. Chaque moteur conserve son état de disponibilité.':'Réglages enregistrés.');setTick(value=>value+1);
    }catch(failure){setError(fail(failure));}finally{setBusy(false);}
  };
  return <section className="fusion-insights" aria-label="Statistiques et préparation des réunions">
    <header className="fusion-page-heading"><div><h1>{tab==='stats'?'Statistiques':'Préparer les réunions'}</h1>
      <p>{tab==='stats'?'Activité enregistrée et état réel des moteurs.':'Configurer la capture, les moteurs et le fonctionnement sur ce PC.'}</p></div>
      <button type="button" disabled={loading||busy} onClick={()=>setTick(value=>value+1)}>Actualiser</button></header>
    <div>
    {error&&<p role="alert" className="fusion-error">{error}</p>}{notice&&<p role="status" className="fusion-notice">{notice}</p>}
    {loading&&!stats&&<p role="status">Lecture des états…</p>}
    {tab==='stats'&&stats&&<>
      <label className="fusion-project-filter">Projet mesuré<select value={project} onChange={event=>setProject(event.target.value)}><option value="">Tous les projets accessibles</option>
        {rows.map(row=><option key={row.id} value={row.id} disabled={!row.brain_project_id}>{row.code} — {row.title}</option>)}</select></label>
      <div className="fusion-stat-grid">
        <Stat label="Sources conservées" value={number(stats.sources.total)} detail={`${number(stats.sources.current)} dans le rappel courant`}/>
        <Stat label="Sources indexées" value={number(stats.sources.indexed)} detail={`${number(stats.sources.extracted)} avec texte extrait`}/>
        <Stat label="Séances" value={number(stats.sessions.total)} detail={Object.entries(stats.sessions.by_state).map(([state,count])=>`${state}: ${count}`).join(' · ')}/>
        <Stat label="Audio conservé" value={`${number(stats.sessions.duration_seconds/60)} min`} detail={bytes(stats.sessions.audio_bytes)}/>
        {stats.sessions.chunks_by_track&&<Stat label="Fragments par piste" value={number(Object.values(stats.sessions.chunks_by_track).reduce((a,b)=>a+b,0))} detail={Object.entries(stats.sessions.chunks_by_track).map(([track,count])=>`${track==='mic'?'Microphone':track==='system'?'Son système':track} : ${number(count)}`).join(' · ')}/>}
        {stats.transcription&&<Stat label="Audio direct en attente" value={`${number(stats.transcription.pending_audio_seconds)} s`} detail={`${number(stats.transcription.pending_chunks)} fragment(s) · ${stats.transcription.oldest_pending_seconds==null?'Aucun fragment en attente':`Le plus ancien attend depuis ${number(stats.transcription.oldest_pending_seconds)} s`}`}/>}
        <Stat label="Réponses de l’assistant" value={number(stats.assistant.answers)} detail={`${number(stats.assistant.stale)} réponse(s) devenue(s) obsolète(s)`}/>
        <Stat label="Réponses jugées utiles" value={number(stats.assistant.useful_answers)} detail={stats.assistant.evaluated_answers==null?'L’utilité nécessite un avis explicite ; aucun score déduit du nombre de réponses':`${number(stats.assistant.evaluated_answers)} réponse(s) évaluée(s), dont ${number(stats.assistant.unhelpful_answers)} jugée(s) pas utiles · dernier avis explicite conservé`}/>
        <Stat label="Propositions de notes" value={number(stats.assistant.enhancements)} detail="Propositions distinctes de vos notes enregistrées"/>
        <Stat label="Temps de réponse médian" value={stats.assistant.p50_seconds==null?'Indisponible':`${number(stats.assistant.p50_seconds)} s`} detail={stats.assistant.p95_seconds==null?'P95 indisponible':`P95 : ${number(stats.assistant.p95_seconds)} s`}/>
        <Stat label="Passages recherchables" value={number(stats.index.text_passages)} detail={`${bytes(stats.index.size_bytes)}`}/>
        <Stat label="Tokens mesurés" value={number(stats.assistant.tokens)} detail={stats.assistant.token_total_answers==null?'Aucune économie calculée sans mesure et référence':`${number(stats.assistant.token_complete_answers)} réponse(s) avec mesure complète · ${number(stats.assistant.token_partial_answers)} partielle(s) · ${number(stats.assistant.token_unmeasured_answers)} sans mesure. Aucune économie estimée.`}/>
      </div>
      <section className="fusion-engine-list" aria-label="État des moteurs"><h2>Moteurs</h2>
        <Engine title="Transcription" state={engineReady(stats.engines.speech)} detail={String(stats.engines.speech.detail||'')}/>
        <Engine title="Génération" state={generationState(stats.engines.generation)} detail={generationPlacement(stats.engines.generation)}/>
      </section>
      <details className="fusion-formulas"><summary>Définition des mesures</summary><dl>{Object.entries(stats.formulas).map(([key,value])=><div key={key}><dt>{key}</dt><dd>{value}</dd></div>)}</dl></details>
    </>}
    {tab==='preparation'&&settings&&draft&&<>
      <ol className="fusion-onboarding" aria-label="Étapes de préparation">
        <li><h2>1. Conserver la séance</h2><p>{settings.capabilities.capture.durable?'Sauvegarde progressive des fragments disponible.':'Sauvegarde progressive indisponible.'}</p>
          <p>Le navigateur demande les pistes audio au démarrage. Leur présence est contrôlée pendant la capture.</p></li>
        <li><h2>2. Transcrire les voix</h2><p>{settings.capabilities.transcription.batch_ready?'Transcription des fichiers prête.':'Transcription des fichiers indisponible.'}
          {' '}{settings.capabilities.transcription.live_ready?'Direct qualifié selon le statut enregistré.':'Direct en essai, qualité et latence non qualifiées.'}</p>
          <p>Installation du moteur direct : {settings.capabilities.transcription.installed===true?'installé':settings.capabilities.transcription.installed===false?'non installé':'non renseignée'}.
            {' '}Activation enregistrée : {settings.capabilities.transcription.enabled===true?'autorisée en essai':'désactivée'}.
            {' '}Moteur direct : {settings.capabilities.transcription.live_operational===true?'disponible pour essai':settings.capabilities.transcription.live_operational===false?'indisponible':'état non renseigné'}.</p>
          <p>{settings.capabilities.transcription.detail}</p></li>
        <li><h2>3. Retrouver les documents</h2><p>{stats?`${number(stats.index.text_passages)} passages texte indexés.`:'État de la recherche indisponible.'}</p>
          <p>Importez un document choisi dans Sources puis contrôlez son état d’extraction et d’indexation.</p></li>
        <li><h2>4. Répondre et enrichir les notes</h2><p>{settings.capabilities.assistant?.ready?'Assistance configurée ; validez une question réelle.':'La génération doit être vérifiée sur une question réelle.'}</p>
          <p>Les propositions conservent leurs sources ; leur acceptation enregistre une nouvelle version de note.</p></li>
      </ol>
      {!canEdit&&<p role="status">Vous pouvez consulter les réglages communs des réunions. Le propriétaire de Kiara peut les modifier.</p>}
      <form onSubmit={event=>{event.preventDefault();void save();}}>
        <fieldset className="fusion-settings-form" disabled={!canEdit} aria-label="Réglages communs des réunions">
        <label className="fusion-check"><input type="checkbox" checked={draft.enabled} disabled={busy} onChange={event=>setDraft({...draft,enabled:event.target.checked})}/>Activer l’espace de séance</label>
        <label className="fusion-check"><input type="checkbox" checked={draft.live_transcription_enabled??false} disabled={busy} onChange={event=>setDraft({...draft,live_transcription_enabled:event.target.checked})}/>Autoriser la transcription directe en essai</label>
        <p className="fusion-meta">Ce réglage distinct autorise le traitement des fragments enregistrés. Il ne démarre pas le microphone. Le texte direct reste provisoire et doit être relu ; activer l’essai ne qualifie ni sa qualité ni sa latence.</p>
        {settings.speech_acceleration&&<>
          <label>Calcul de la transcription directe<select value={draft.live_speech_device??'cpu'} disabled={busy||settings.speech_acceleration.environment_override}
            onChange={event=>setDraft({...draft,live_speech_device:event.target.value as 'cpu'|'cuda'})}>
            <option value="cpu">Processeur (CPU)</option><option value="cuda" disabled={!settings.speech_acceleration.cuda_available}>Carte graphique (GPU) · en essai</option>
          </select></label>
          <p className="fusion-meta">{settings.speech_acceleration.environment_override&&'Choix imposé par la configuration du service. '}{settings.speech_acceleration.detail} Le modèle est chargé au prochain traitement. La transcription complète conserve son réglage actuel.</p>
        </>}
        <label className="fusion-check"><input type="checkbox" checked={draft.proactive_enabled} disabled={busy} onChange={event=>setDraft({...draft,proactive_enabled:event.target.checked})}/>Proposer des réponses aux questions entendues automatiquement</label>
        <label className="fusion-check"><input type="checkbox" checked={draft.auto_enhancement_enabled??false} disabled={busy} onChange={event=>setDraft({...draft,auto_enhancement_enabled:event.target.checked})}/>Proposer des enrichissements des notes automatiquement</label>
        <p className="fusion-meta">L’enrichissement attend au moins huit secondes de stabilité de la dernière note et des segments enregistrés. Vos modifications non enregistrées ne participent pas à l’analyse. Chaque ajout proposé attend votre acceptation.</p>
        <label>Exécution des nouveaux traitements<select value={draft.mode} disabled={busy} onChange={event=>setDraft({...draft,mode:event.target.value as FusionSettings['mode']})}>
          <option value="network">Serveur du réseau</option><option value="local">Entièrement sur ce PC</option></select></label>
        <p className="fusion-meta">Le mode choisi conserve l’ancien fonds documentaire. Le diagnostic indique ce qui est disponible ; le mode local doit fonctionner sans réseau pour chaque moteur.</p>
        {canEdit&&<div><button type="submit" disabled={busy}>{busy?'Enregistrement…':'Enregistrer les réglages'}</button>
          <button type="button" disabled={busy} onClick={()=>void save(true)}>{settings.onboarding_complete?'Préparation déjà enregistrée':'Terminer la préparation'}</button></div>}
        </fieldset>
      </form>
      {canEdit&&<details className="progressive-options">
        <summary>Diagnostic des moteurs</summary>
        <FusionReadiness active={active} refreshKey={tick}/>
      </details>}
    </>}
    </div>
  </section>;
}
function Stat({label,value,detail}:{label:string;value:string;detail:string}){return <article><h2>{label}</h2><strong>{value}</strong><p>{detail}</p></article>;}
function Engine({title,state,detail}:{title:string;state:string;detail:string}){return <article><div><h3>{title}</h3><p>{detail}</p></div><strong>{state}</strong></article>;}
