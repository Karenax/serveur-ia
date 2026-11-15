import {useEffect,useRef,useState} from 'react';
import {fusionInsights,type FusionReadinessState,type GenerationReadiness} from '../lib/fusionInsights';

const flag=(value:unknown,yes:string,no:string)=>value===true?yes:value===false?no:'Non vérifié';
const date=(value:string)=>new Date(value).toLocaleString('fr-FR');
const memory=(value:number|null)=>value==null?'Indisponible':`${(value/1024**3).toLocaleString('fr-FR',{maximumFractionDigits:1})} Go`;
export const generationState=(value:GenerationReadiness)=>!value.configured?'Non configurée':value.test?.ok===true?'Réponse testée':value.test?.ok===false?'Test de réponse en échec':'Configurée ; génération à vérifier';
export const generationPlacement=(value:GenerationReadiness)=>value.placement==='local'?'Sur ce PC':value.placement==='network'?'Serveur du réseau':'Placement non vérifié';

export function FusionReadiness({active=true,refreshKey=0}:{active?:boolean;refreshKey?:number}){
  const [data,setData]=useState<FusionReadinessState|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState('');
  const revision=useRef(0),alive=useRef(true);
  useEffect(()=>{alive.current=true;return()=>{alive.current=false;revision.current++;};},[]);
  useEffect(()=>{
    if(!active)return;const controller=new AbortController(),current=++revision.current;setError('');
    void fusionInsights.readiness(controller.signal).then(value=>{if(current===revision.current&&!controller.signal.aborted)setData(value);})
      .catch(failure=>{if(current===revision.current&&!controller.signal.aborted)setError(String((failure as Error).message));});
    return()=>{controller.abort();revision.current++;};
  },[active,refreshKey]);
  const run=async(kind:'inventory'|'generation')=>{
    if(busy)return;const current=++revision.current;setBusy(kind);setError('');
    try{const result=await(kind==='inventory'?fusionInsights.probeReadiness():fusionInsights.testGeneration());if(alive.current&&current===revision.current)setData(result);}
    catch(failure){if(alive.current&&current===revision.current)setError(String((failure as Error).message));}
    finally{if(alive.current)setBusy('');}
  };
  const generation=data?.generation,inventory=generation?.inventory;
  return <section className="fusion-readiness" aria-label="Diagnostic des moteurs">
    <h2>Disponibilité des moteurs</h2><p>Diagnostic de la configuration enregistrée. Vérifier les modèles n’ouvre pas le microphone et ne lance pas de réponse.</p>
    {error&&<p role="alert">{error}</p>}
    {!data&&!error&&<p role="status">Lecture du diagnostic…</p>}
    {busy&&<p role="status">{busy==='inventory'?'Vérification des modèles en cours…':'Test de réponse en cours…'}</p>}
    {data&&<><div className="fusion-stat-grid">
      <article><h3>Capture</h3><p>{data.capture.durable?'Conservation progressive disponible':'Conservation indisponible'}</p>
        <p>{flag(data.capture.ready,'Périphériques disponibles','Périphériques indisponibles')} · {flag(data.capture.physical_test_passed,'Essai système qualifié','Recette matérielle à compléter')}</p></article>
      <article><h3>Transcription</h3><p>Fichiers : {flag(data.transcription.batch.ready,'prête','indisponible')} · Direct : {flag(data.transcription.direct.ready,'disponible en essai','indisponible')}</p>
        <p>Direct installé : {flag(data.transcription.direct.installed,'oui','non')} · Chargé : {flag(data.transcription.direct.loaded,'oui','non')}</p>
        <p>La disponibilité en essai ne qualifie pas la qualité ou la latence.</p></article>
      <article><h3>Recherche dans les sources</h3><p>{data.embeddings.network.model||'Index EG2'}</p>
        <p>Recherche dans le texte, y compris le texte reconnu et les transcriptions indexées.</p></article>
      <article><h3>Génération</h3><p>{generationState(data.generation)} · {generationPlacement(data.generation)}</p><p>{data.generation.model||'Modèle non configuré'}</p>
        <p>Installé : {flag(inventory?.installed,'oui','non')} · Chargé : {flag(inventory?.loaded,'oui','non')}</p>
        <p>{inventory?.detail||'Inventaire non vérifié.'}{inventory?` Vérifié le ${date(inventory.checked_at)}.`:''}</p>
        <p>{data.generation.test?`${data.generation.test.detail}. Test du ${date(data.generation.test.checked_at)}.`:'Aucune réponse réelle testée pour cette configuration.'}</p></article>
      </div>
      <p>Mémoire disponible : {memory(data.resources.available_ram_bytes)} · Disque disponible : {memory(data.resources.free_disk_bytes)}.</p>
      <p>{data.offline.detail}</p>
    </>}
    <div><button type="button" disabled={!data||!!busy} onClick={()=>void run('inventory')}>Vérifier les modèles</button>
      <button type="button" disabled={!generation?.configured||!!busy} onClick={()=>void run('generation')}>Tester une réponse</button></div>
    <p className="fusion-meta">Le test envoie seulement « Réponds uniquement OK » au modèle sélectionné, sans document ni note. Le serveur peut charger ce modèle à la demande ; ce n’est pas un test de qualité métier.</p>
  </section>;
}
