import { agentPath } from '../lib/agentRoutes';
import { useCallback, useEffect, useRef, useState } from 'react';
import { reviewApi, reviewSections, reviewRelation, mergeReviewContent, sameReviewValue, type ReviewContent, type ReviewDetail,
  type ReviewPage, type ReviewItem, type ReviewEvidence, type ReviewEvent, type ReviewEventDetail,
  type RecordingChoice, type ReviewPublication, type ReviewBindings } from '../lib/projectReviews';
import { identityApi, personName, type Page, type ProjectPerson, type ProjectIdentity } from '../lib/projectIdentity';
import { deliverableApi, deliverableDate, type DeliverableRow } from '../lib/projectDeliverables';
import { meetingAudio, type MeetingRecording } from '../lib/meetingAudio';
import { ErrorState, LoadingState } from './Ui';
import { Pagination, Picker } from './IdentityPickers';
import { PlanningRelationPicker, useAlive, useEditorFocus } from './PlanningTasksPanel';
import { planningApi } from '../lib/projectPlanning';
import './project-reviews.css';

const message=(error:unknown)=>error instanceof Error?error.message:String(error);
const actionLabels:Record<string,string>={review_created:'Brouillon créé',review_saved:'Brouillon enregistré',
  review_revision_created:'Nouvelle révision',review_recording_imported:'Réunion importée',review_published:'Revue publiée'};

type ReviewsProps={projectId:string;active?:boolean;onSaved:()=>void;onOpenDocument?:(id:string,title:string)=>void};
export function ProjectReviewsPanel(props:ReviewsProps) {
  return <ReviewsView key={props.projectId} {...props}/>;
}
function ReviewsView({projectId,active=true,onSaved,onOpenDocument}:ReviewsProps) {
  const [page,setPage]=useState<ReviewPage|null>(null),[offset,setOffset]=useState(0),[tick,setTick]=useState(0);
  const [selectedId,setSelectedId]=useState<string|null>(null),[detail,setDetail]=useState<ReviewDetail|null>(null);
  const [dirty,setDirty]=useState(false),[busy,setBusy]=useState(false),[loading,setLoading]=useState(false),[opening,setOpening]=useState(false);
  const [error,setError]=useState(''),[readError,setReadError]=useState(''),[readTick,setReadTick]=useState(0);
  const alive=useAlive();const locked=busy||dirty;
  useEffect(()=>{if(!active)return;const controller=new AbortController();setLoading(true);setError('');
    reviewApi.list(projectId,offset,controller.signal).then(value=>{if(!controller.signal.aborted)setPage(value);})
      .catch(e=>{if(!controller.signal.aborted)setError(message(e));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return()=>controller.abort();},[projectId,active,offset,tick]);
  useEffect(()=>{if(!active||!selectedId||detail?.id===selectedId)return;const controller=new AbortController();setOpening(true);setReadError('');
    reviewApi.read(projectId,selectedId,controller.signal).then(value=>{if(!controller.signal.aborted)setDetail(value);})
      .catch(e=>{if(!controller.signal.aborted)setReadError(message(e));}).finally(()=>{if(!controller.signal.aborted)setOpening(false);});
    return()=>controller.abort();},[projectId,active,selectedId,readTick,detail?.id]);
  async function create(){if(!page||locked||loading)return;setBusy(true);setError('');
    try{const value=await reviewApi.create(projectId,page.revision);if(alive.current){setDetail(value);setSelectedId(value.id);setTick(v=>v+1);onSaved();}}
    catch(e){if(alive.current)setError(message(e));}finally{if(alive.current)setBusy(false);}}
  function saved(value:ReviewDetail){setDetail(value);setSelectedId(value.id);setTick(v=>v+1);onSaved();}
  return <section className="project-reviews" aria-label="Revues de lancement">
    <header className="planning-heading"><div><h3>Revue de lancement de projet</h3><p>Préparer les engagements, vérifier les sources puis publier une révision figée.</p></div>
      {page?.can_edit&&!page.total&&<button type="button" className="button primary" disabled={locked||loading||!active} onClick={()=>void create()}>Créer la revue de lancement</button>}</header>
    {error&&<ErrorState message={error} retry={()=>setTick(v=>v+1)}/>} {loading&&<LoadingState label="Chargement des revues"/>}
    {page&&!page.total&&!loading&&<p>Aucune revue de lancement. Les comptes rendus restent disponibles dans « Réunions et audio ».</p>}
    {page&&page.total>0&&<><div className="review-list" aria-label="Révisions de la revue">{page.items.map(row=><button type="button" key={row.id}
      className={`review-card ${selectedId===row.id?'selected':''}`} aria-label={`RLP · Révision ${row.number} — ouvrir le détail`} aria-pressed={selectedId===row.id} disabled={locked||opening||!active}
      onClick={()=>{setSelectedId(row.id);setDetail(null);}}><strong>RLP · Révision {row.number}</strong><span>{row.status==='published'?'Publiée · figée':'Brouillon'}</span>
      <small>{row.meeting_date||'Date à préciser'} · {row.participants} participant(s)</small></button>)}</div>
      <Pagination offset={page.offset} total={page.total} limit={page.limit} onChange={setOffset} disabled={locked||loading||opening}/></>}
    {readError&&<ErrorState message={readError} retry={()=>setReadTick(v=>v+1)}/>} {opening&&<LoadingState label="Lecture de la revue"/>}
    {detail&&<ReviewSheet key={detail.id} projectId={projectId} initial={detail} active={active} onSaved={saved} onDirty={setDirty} onBusy={setBusy} onOpenDocument={onOpenDocument}/>}
  </section>;
}

function ReviewSheet({projectId,initial,active,onSaved,onDirty,onBusy,onOpenDocument}:{projectId:string;initial:ReviewDetail;active:boolean;
  onSaved:(row:ReviewDetail)=>void;onDirty:(dirty:boolean)=>void;onBusy:(busy:boolean)=>void;onOpenDocument?:ReviewsProps['onOpenDocument']}) {
  const [base,setBase]=useState(initial),[draft,setDraft]=useState<ReviewContent>(structuredClone(initial.content));
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState(''),[confirmed,setConfirmed]=useState(false);
  const [latest,setLatest]=useState<ReviewDetail|null>(null),[choices,setChoices]=useState<Record<string,'mine'|'current'>>({});
  const [checking,setChecking]=useState(false),[downloading,setDownloading]=useState(false),[download,setDownload]=useState<{url:string;name:string}|null>(null);
  const [capturedDocuments,setCapturedDocuments]=useState<{id:string;title:string}[]|null>(null);
  const alive=useAlive(),focus=useEditorFocus(),downloadAbort=useRef<AbortController|null>(null);
  const dirty=!sameReviewValue(draft,base.content),allowed=base.can_edit&&active;
  const disabled=!allowed||busy||checking||!!latest;
  const merge=latest?mergeReviewContent(base.content,draft,latest.content,choices):null;
  useEffect(()=>{onDirty(dirty);return()=>onDirty(false);},[dirty,onDirty]);
  useEffect(()=>{onBusy(busy||checking||downloading);return()=>onBusy(false);},[busy,checking,downloading,onBusy]);
  useEffect(()=>()=>downloadAbort.current?.abort(),[]);
  useEffect(()=>()=>{if(download)URL.revokeObjectURL(download.url);},[download]);
  useEffect(()=>{if(!active)downloadAbort.current?.abort();},[active]);
  function change<K extends keyof ReviewContent>(key:K,value:ReviewContent[K]){setDraft(row=>({...row,[key]:value}));setConfirmed(false);setNotice('');}
  function accepted(row:ReviewDetail,text:string){setBase(row);setDraft(structuredClone(row.content));setLatest(null);setChoices({});setConfirmed(false);setNotice(text);onSaved(row);}
  async function mutate(kind:'save'|'publish'|'revision',source?:RecordingChoice){if(busy||!active||latest)return;
    if(kind==='publish'&&(!confirmed||dirty||base.publication_blockers.length))return;
    if(source&&dirty)return;setBusy(true);setError('');setNotice('');
    try{const row=source?await reviewApi.importRecording(projectId,base,source):kind==='save'?await reviewApi.save(projectId,base,draft):
      kind==='publish'?await reviewApi.publish(projectId,base):await reviewApi.newRevision(projectId,base);
      if(alive.current)accepted(row,source?'Propositions importées : relire chaque point et sa citation.':kind==='publish'?'Révision publiée et figée.':kind==='revision'?'Nouvelle révision indépendante créée.':'Brouillon enregistré.');}
    catch(e){if(alive.current)setError(message(e));}finally{if(alive.current)setBusy(false);}}
  async function compare(){if(checking||busy||!active)return;setChecking(true);setError('');
    try{const row=await reviewApi.read(projectId,base.id);if(alive.current){setLatest(row);setChoices({});}}
    catch(e){if(alive.current)setError(message(e));}finally{if(alive.current)setChecking(false);}}
  function reconcile(){if(!latest||!merge||merge.unresolved.length||!latest.can_edit)return;
    setDraft(merge.content);setBase(latest);setLatest(null);setConfirmed(false);setError('');setNotice('Comparaison appliquée. Vérifiez le brouillon avant de l’enregistrer.');}
  async function pdf(){if(downloading||!active)return;const controller=new AbortController();downloadAbort.current=controller;setDownloading(true);setError('');
    try{const blob=await reviewApi.pdf(projectId,base,controller.signal);if(alive.current&&!controller.signal.aborted){setDownload({url:URL.createObjectURL(blob),name:`RLP-revision-${base.number}.pdf`});setNotice('PDF vérifié : utilisez le lien pour l’enregistrer.');}}
    catch(e){if(alive.current&&!controller.signal.aborted)setError(message(e));}finally{if(alive.current)setDownloading(false);}}
  return <form ref={focus} tabIndex={-1} onSubmit={e=>e.preventDefault()} aria-label={`Fiche RLP révision ${base.number}`} className="card review-sheet" data-workspace-dirty={dirty?'true':undefined}>
    <header className="planning-heading"><div><h4>RLP · Révision {base.number}</h4><p>{base.status==='published'?'Publication figée':base.can_edit?'Brouillon modifiable':'Brouillon · lecture seule'} · Enregistrement {base.review_revision}</p></div>
      {base.can_create_revision&&<button type="button" className="button primary" disabled={busy||checking||!active} onClick={()=>void mutate('revision')}>Créer une nouvelle révision</button>}</header>
    {notice&&<p role="status">{notice}</p>}{error&&<div role="alert" className="planning-error"><p>{error}</p><p>Votre saisie est conservée.</p>
      <button type="button" className="button secondary" disabled={busy||checking||!active} onClick={()=>void compare()}>Comparer avec la version actuelle</button></div>}
    {latest&&merge&&<section aria-label="Comparaison de la revue" className="review-conflicts"><h4>Modifications concurrentes</h4>
      <p>Les champs modifiés sur un seul côté sont conservés. Choisissez une version pour chaque conflit.</p>
      {merge.conflicts.map(conflict=><fieldset key={conflict.key}><legend>{conflict.label}</legend>
        <details><summary>Valeur avant modification</summary><ReviewValue value={conflict.base}/></details>
        <label><input type="radio" name={conflict.key} checked={choices[conflict.key]==='mine'} onChange={()=>setChoices(row=>({...row,[conflict.key]:'mine'}))}/> Ma saisie</label><ReviewValue value={conflict.mine}/>
        <label><input type="radio" name={conflict.key} checked={choices[conflict.key]==='current'} onChange={()=>setChoices(row=>({...row,[conflict.key]:'current'}))}/> Version actuelle</label><ReviewValue value={conflict.current}/></fieldset>)}
      {!merge.conflicts.length&&<p>Aucun conflit de contenu. Les informations actuelles seront conservées.</p>}
      {!latest.can_edit&&<p role="alert">La revue est devenue figée ou vos droits ont changé. Copiez votre saisie avant d’ouvrir la version actuelle.</p>}
      {!latest.can_edit&&<button type="button" className="button secondary" onClick={()=>{if(window.confirm('Ouvrir la version actuelle et abandonner cette saisie non enregistrée ?'))accepted(latest,'Version actuelle ouverte.');}}>Ouvrir la version actuelle et abandonner ma saisie</button>}
      <button type="button" className="button primary" disabled={!latest.can_edit||!!merge.unresolved.length} onClick={reconcile}>Appliquer la comparaison au brouillon</button>
      <button type="button" className="button secondary" onClick={()=>{setLatest(null);setChoices({});}}>Garder ma saisie sans comparer</button>
      <details><summary>Copier ma saisie conservée</summary><textarea className="input" aria-label="Copie du brouillon" readOnly value={JSON.stringify(draft,null,2)} rows={8}/></details>
    </section>}
    <fieldset disabled={disabled} className="review-fields"><legend>Contexte de la revue</legend><div className="review-form-grid">
      <label>Date de revue<input className="input" type="date" value={draft.meeting_date} onChange={e=>change('meeting_date',e.target.value)}/></label>
      <label>Lieu<input className="input" maxLength={255} value={draft.location} onChange={e=>change('location',e.target.value)}/></label>
    </div><ReviewMilestone projectId={projectId} active={active} value={draft.milestone_id} disabled={disabled} onChange={value=>change('milestone_id',value)}/>
      <label>Notes de revue<textarea className="input" maxLength={20000} rows={4} value={draft.notes} onChange={e=>change('notes',e.target.value)}/></label></fieldset>
    <ReviewParticipants projectId={projectId} active={active} value={draft.participants} disabled={disabled} onChange={value=>change('participants',value)}/>
    <ReviewDocuments projectId={projectId} active={active} value={draft.deliverable_ids} disabled={disabled} published={base.status==='published'} captured={capturedDocuments} onChange={value=>change('deliverable_ids',value)}/>
    <div className="review-sections">{reviewSections.map(section=><section key={section.code} aria-label={section.label} className="review-section">
      <header className="planning-heading"><h4>{section.label}{section.required&&<small> · Requis</small>}</h4>
        {base.can_edit&&<button type="button" className="button secondary sm" disabled={disabled||draft.items.length>=300} onClick={()=>change('items',[...draft.items,
          {id:crypto.randomUUID(),section_code:section.code,text:'',reviewed:false,evidence_ids:[],owner:'',due_date:''}])}>Ajouter · {section.label}</button>}</header>
      {!draft.items.some(item=>item.section_code===section.code)&&<p>Aucun point renseigné.</p>}
      {draft.items.filter(item=>item.section_code===section.code).map((item,index)=><ReviewPoint key={item.id} item={item} index={index+1} disabled={disabled}
        projectId={projectId} active={active} provenance={base.provenance} onChange={value=>change('items',draft.items.map(row=>row.id===item.id?value:row))}
        onRemove={()=>{if(window.confirm('Retirer ce point du brouillon ? Sa trace reste dans les enregistrements précédents.'))change('items',draft.items.filter(row=>row.id!==item.id));}}/>)}
    </section>)}</div>
    {base.can_edit&&<><div className="review-save"><span role="status">{dirty?'Modifications non enregistrées':'Brouillon enregistré'}</span>
      <button type="button" className="button primary" disabled={disabled||!dirty||draft.items.some(item=>!item.text.trim())||draft.participants.some(person=>!person.name.trim())}
        onClick={()=>void mutate('save')}>{busy?'Enregistrement…':'Enregistrer le brouillon'}</button>
      {dirty&&<button type="button" className="button secondary" disabled={busy||checking} onClick={()=>{if(window.confirm('Abandonner les modifications non enregistrées ?')){setDraft(structuredClone(base.content));setLatest(null);setError('');setConfirmed(false);}}}>Abandonner mes modifications</button>}</div>
      <ReviewRecordingPicker projectId={projectId} active={active} disabled={busy||dirty||!!latest||checking} onImport={source=>void mutate('save',source)}/>
      <section className="review-publication" aria-label="Publication de la revue"><h4>Publier la revue</h4>
        {dirty?<p>Enregistrez le brouillon pour vérifier les conditions de publication.</p>:base.publication_blockers.length>0?
          <ul>{base.publication_blockers.map(blocker=><li key={blocker}>{blocker}</li>)}</ul>:<p>Les conditions de publication sont remplies.</p>}
        <label><input type="checkbox" checked={confirmed} disabled={disabled||dirty||!!base.publication_blockers.length} onChange={e=>setConfirmed(e.target.checked)}/>
          Je confirme la relecture des points, participants et livrables. Cette révision et son PDF seront figés.</label>
        <button type="button" className="button primary" disabled={disabled||dirty||!confirmed||!!base.publication_blockers.length} onClick={()=>void mutate('publish')}>Publier la révision</button></section></>}
    {base.publication&&<><PublishedReview projectId={projectId} row={base} active={active} onCaptured={setCapturedDocuments} onOpenDocument={onOpenDocument}/><button type="button" className="button secondary" disabled={downloading||!active} onClick={()=>void pdf()}>
      {downloading?'Vérification du PDF…':'Préparer le PDF publié'}</button>{download&&<p><a href={download.url} download={download.name}>Enregistrer {download.name}</a></p>}</>}
    <ReviewHistory key={`${base.id}:${base.review_revision}`} projectId={projectId} row={base} active={active}/>
  </form>;
}

function ReviewValue({value}:{value:unknown}) {
  if(value===undefined||value===null)return <p>Retiré ou non renseigné</p>;
  if(typeof value==='string')return <p className="review-text">{value||'Non renseigné'}</p>;
  if(Array.isArray(value))return <ul>{value.map((row,index)=><li key={index}><ReviewValue value={row}/></li>)}</ul>;
  if(typeof value==='object'){const row=value as Partial<ReviewItem & {name:string;function:string}>;return <p className="review-text">{row.text||row.name||JSON.stringify(value)}
    {row.function&&` · ${row.function}`}{typeof row.reviewed==='boolean'&&` · ${row.reviewed?'Relu':'À relire'}`}{row.owner&&` · Pilote : ${row.owner}`}{row.due_date&&` · Échéance : ${row.due_date}`}</p>;}
  return <p>{String(value)}</p>;
}

function ReviewPoint({item,index,disabled,provenance,projectId,active,onChange,onRemove}:{item:ReviewItem;index:number;disabled:boolean;projectId:string;active:boolean;
  provenance:Record<string,ReviewEvidence>;onChange:(item:ReviewItem)=>void;onRemove:()=>void}) {
  const section=reviewSections.find(row=>row.code===item.section_code)!.label;
  return <article className="review-point" aria-label={`${section} · Point ${index}`}><fieldset disabled={disabled}><legend>Point {index}</legend>
    <label>Texte du point<textarea className="input" rows={3} maxLength={4000} value={item.text} onChange={e=>onChange({...item,text:e.target.value,reviewed:false})}/></label>
    {item.section_code==='actions'&&<div className="review-form-grid"><label>Pilote de l’action<input className="input" maxLength={120} value={item.owner} onChange={e=>onChange({...item,owner:e.target.value,reviewed:false})}/></label>
      <label>Échéance de l’action<input className="input" type="date" value={item.due_date} onChange={e=>onChange({...item,due_date:e.target.value,reviewed:false})}/></label></div>}
    <label><input type="checkbox" checked={item.reviewed} onChange={e=>onChange({...item,reviewed:e.target.checked})}/> Point relu et vérifié</label></fieldset>
    {item.evidence_ids.map(id=><Evidence key={id} value={provenance[id]} projectId={projectId} active={active}/>)}
    {!disabled&&<button type="button" className="button secondary sm" onClick={onRemove}>Retirer ce point du brouillon</button>}</article>;
}
function Evidence({value,projectId,active=true,bindings}:{value:ReviewEvidence|undefined;projectId?:string;active?:boolean;bindings?:Partial<ReviewBindings>}) {return value?<details className="review-evidence"><summary>Source · {value.speaker} · {Math.floor(value.start/60)}:{String(Math.floor(value.start%60)).padStart(2,'0')}</summary>
  <blockquote>{value.quote}</blockquote><p className="review-text">Transcription conservée : {value.text}</p><small>Réunion {value.recording_id} · transcription révision {value.revision} · modèle {value.summary_model}</small>
  <p><small>Segment {value.segment_id} · {value.start}–{value.end} s</small></p><details><summary>Empreinte de synthèse</summary><code>{value.summary_sha256}</code></details>
  {projectId&&<RecordingEvidence projectId={projectId} active={active} proof={value} bindings={bindings}/>}
</details>:<p role="alert">Preuve absente : rechargez la revue avant publication.</p>;}

function RecordingEvidence({projectId,active,proof,bindings}:{projectId:string;active:boolean;proof:ReviewEvidence;bindings?:Partial<ReviewBindings>}) {
  const id=reviewRelation(proof.recording_id,'brain',bindings),sourceId=reviewRelation(proof.source_id,'brain',bindings);
  const [open,setOpen]=useState(false),[record,setRecord]=useState<MeetingRecording|null>(null),[error,setError]=useState(''),[tick,setTick]=useState(0);
  useEffect(()=>{setRecord(null);if(!open||!active)return;const controller=new AbortController();setError('');
    meetingAudio.get(projectId,id,controller.signal).then(value=>{if(controller.signal.aborted)return;
      if(value.id!==id||value.source_id!==sourceId)throw new Error('Source reçue différente de la réunion attendue.');setRecord(value);
    }).catch(e=>{if(!controller.signal.aborted)setError(message(e));});return()=>controller.abort();},[projectId,id,sourceId,active,open,tick]);
  const segment=record?.segments.find(value=>value.id===proof.segment_id);
  return <div><button type="button" className="button secondary sm" disabled={!active} onClick={()=>setOpen(value=>!value)}>{open?'Fermer la réunion source':'Consulter la réunion source'}</button>
    {open&&active&&<section aria-label="Réunion source actuelle">{error?<ErrorState message={error} retry={()=>setTick(value=>value+1)}/>:!record?<LoadingState label="Lecture de la réunion source"/>:
      <><h5>{record.title}</h5><p>Transcription actuelle · révision {record.revision}. La citation conservée provient de la révision {proof.revision}.</p>
        {segment?<><p>{record.speaker_names[segment.speaker]||segment.speaker} · {segment.start}–{segment.end} s</p><p className="review-text">{segment.text}</p></>:<p>Ce segment n’est plus présent dans la transcription actuelle. La citation conservée reste disponible ci-dessus.</p>}
        <audio controls preload="none" aria-label="Audio de la réunion source" src={agentPath(meetingAudio.audioUrl(projectId,id))}/></>}
    </section>}</div>;
}

function ReviewMilestone({projectId,active,value,disabled,onChange}:{projectId:string;active:boolean;value:string|null;disabled:boolean;onChange:(id:string|null)=>void}) {
  const [current,setCurrent]=useState<{id:string;title:string}|null>(null),[error,setError]=useState(''),[tick,setTick]=useState(0);
  useEffect(()=>{if(!active||!value){if(!value)setCurrent(null);return;}const controller=new AbortController();setError('');
    planningApi.milestone(projectId,value,controller.signal).then(row=>{if(!controller.signal.aborted)setCurrent(row.item);})
      .catch(e=>{if(!controller.signal.aborted)setError(message(e));});return()=>controller.abort();},[projectId,active,value,tick]);
  return <div>{error&&<ErrorState message={error} retry={()=>setTick(v=>v+1)}/>}<PlanningRelationPicker projectId={projectId} kind="milestones" label="Jalon de la revue" value={value} current={current} disabled={disabled||!active} onChange={onChange}/></div>;
}

const people=(search:string,offset:number,signal:AbortSignal)=>identityApi.people({search,offset,signal});
function ReviewParticipants({projectId,active,value,disabled,onChange}:{projectId:string;active:boolean;value:ReviewContent['participants'];disabled:boolean;onChange:(value:ReviewContent['participants'])=>void}) {
  const [team,setTeam]=useState<ProjectIdentity|null>(null),[error,setError]=useState(''),[tick,setTick]=useState(0);
  const [person,setPerson]=useState<ProjectPerson|null>(null),[name,setName]=useState(''),[job,setJob]=useState('');
  useEffect(()=>{if(!active)return;const controller=new AbortController();setError('');identityApi.read(projectId,controller.signal)
    .then(row=>{if(!controller.signal.aborted)setTeam(row);}).catch(e=>{if(!controller.signal.aborted)setError(message(e));});return()=>controller.abort();},[projectId,active,tick]);
  function add(person:ProjectPerson){if(value.length>=50||value.some(row=>row.person_id===person.id))return;
    onChange([...value,{person_id:person.id,name:personName(person),function:person.function,signature_required:true}]);setPerson(null);}
  return <section aria-label="Participants de la revue" className="review-section"><h4>Participants et signatures</h4><p>Les signatures attendues figurent sur le PDF. Elles restent à recueillir auprès des participants.</p>
    {error&&<ErrorState message={error} retry={()=>setTick(v=>v+1)}/>}
    <ul>{value.map((row,index)=><li key={row.person_id||`external-${index}`}><strong>{row.name}</strong> · {row.function||'Fonction à préciser'}
      <label><input type="checkbox" disabled={disabled} checked={row.signature_required} onChange={e=>onChange(value.map((item,i)=>i===index?{...item,signature_required:e.target.checked}:item))}/> Signature attendue</label>
      {!disabled&&<button type="button" className="button secondary sm" aria-label={`Retirer le participant ${row.name}`} onClick={()=>onChange(value.filter((_,i)=>i!==index))}>Retirer</button>}</li>)}</ul>
    {!value.length&&<p>Aucun participant.</p>}
    {!disabled&&<><details><summary>Ajouter depuis l’équipe projet</summary>{team?.members.filter(member=>member.active&&member.person.active).map(member=><button type="button" key={member.id}
      className="button secondary sm" disabled={value.length>=50||value.some(row=>row.person_id===member.person_id)} onClick={()=>add(member.person)}>{personName(member.person)} · {member.person.function||member.role}</button>)}
      {team&&!team.members.some(member=>member.active)&&<p>Complétez l’équipe dans « Fiche et équipe ».</p>}</details>
      <Picker<ProjectPerson> label="Personne du répertoire" value={person?.id||null} current={person} onChange={()=>{}} onPick={setPerson} load={people} display={personName} optionDisabled={row=>!row.active||value.some(item=>item.person_id===row.id)} disabled={value.length>=50||!active}/>
      <button type="button" className="button secondary sm" disabled={!person||value.length>=50} onClick={()=>person&&add(person)}>Ajouter la personne sélectionnée</button>
      <details><summary>Ajouter un participant externe</summary><div className="review-form-grid"><label>Nom du participant externe<input className="input" maxLength={120} value={name} onChange={e=>setName(e.target.value)}/></label>
        <label>Fonction du participant externe<input className="input" maxLength={120} value={job} onChange={e=>setJob(e.target.value)}/></label></div>
        <button type="button" className="button secondary sm" disabled={!name.trim()||value.length>=50} onClick={()=>{onChange([...value,{person_id:null,name:name.trim(),function:job.trim(),signature_required:true}]);setName('');setJob('');}}>Ajouter le participant externe</button></details></>}
  </section>;
}

function ReviewDocuments({projectId,active,value,disabled,published,captured,onChange}:{projectId:string;active:boolean;value:string[];disabled:boolean;published:boolean;captured:{id:string;title:string}[]|null;onChange:(ids:string[])=>void}) {
  const [names,setNames]=useState<Record<string,{title:string;active:boolean}>>({}),[candidate,setCandidate]=useState<DeliverableRow|null>(null),[error,setError]=useState(''),[tick,setTick]=useState(0);
  const load=useCallback((search:string,offset:number,signal:AbortSignal)=>deliverableApi.list(projectId,{search,offset,limit:50,signal}),[projectId]);
  useEffect(()=>{if(!active||published)return;const controller=new AbortController();setError('');
    Promise.allSettled(value.map(id=>deliverableApi.detail(projectId,id,controller.signal))).then(results=>{if(controller.signal.aborted)return;
      const updates:typeof names={};const errors:string[]=[];results.forEach((result,index)=>{if(result.status==='fulfilled')updates[value[index]]={title:result.value.title,active:result.value.active};else errors.push(message(result.reason));});
      setNames(old=>({...old,...updates}));if(errors.length)setError(errors.join(' · '));});return()=>controller.abort();},[projectId,active,value,tick,published]);
  return <section className="review-section" aria-label="Livrables de la revue"><h4>Livrables associés</h4>{error&&<ErrorState message={error} retry={()=>setTick(v=>v+1)}/>}
    <ul>{value.map(id=><li key={id}>{published?(captured?.find(row=>row.id===id)?.title||`Livrable figé · ${id}`):(names[id]?.title||id)}{!published&&names[id]&&!names[id].active&&<span role="alert"> · Archivé, choisir un livrable actif</span>}
      {!disabled&&<button type="button" className="button secondary sm" aria-label={`Retirer le livrable ${names[id]?.title||id}`} onClick={()=>onChange(value.filter(key=>key!==id))}>Retirer</button>}</li>)}</ul>
    {!value.length&&<p>Aucun livrable associé.</p>}{!disabled&&<><Picker<DeliverableRow> label="Livrable à associer" value={candidate?.id||null} current={candidate} load={load}
      display={row=>row.title} onChange={()=>{}} onPick={setCandidate} optionDisabled={row=>!row.active||value.includes(row.id)} disabled={value.length>=100||!active}/>
      <button type="button" className="button secondary sm" disabled={!candidate||value.length>=100} onClick={()=>{if(candidate&&!value.includes(candidate.id)){setNames(old=>({...old,[candidate.id]:candidate}));onChange([...value,candidate.id]);setCandidate(null);}}}>Associer le livrable sélectionné</button></>}
  </section>;
}

function ReviewRecordingPicker({projectId,active,disabled,onImport}:{projectId:string;active:boolean;disabled:boolean;onImport:(source:RecordingChoice)=>void}) {
  const [open,setOpen]=useState(false),[offset,setOffset]=useState(0),[page,setPage]=useState<Page<RecordingChoice>|null>(null);
  const [source,setSource]=useState<RecordingChoice|null>(null),[recording,setRecording]=useState<MeetingRecording|null>(null);
  const [loading,setLoading]=useState(false),[error,setError]=useState(''),[tick,setTick]=useState(0),[opening,setOpening]=useState(false);
  useEffect(()=>{if(!open||!active)return;const controller=new AbortController();setLoading(true);setError('');reviewApi.recordings(projectId,offset,controller.signal)
    .then(value=>{if(!controller.signal.aborted)setPage(value);}).catch(e=>{if(!controller.signal.aborted)setError(message(e));})
    .finally(()=>{if(!controller.signal.aborted)setLoading(false);});return()=>controller.abort();},[projectId,active,open,offset,tick]);
  useEffect(()=>{if(!source||!active||!open)return;const controller=new AbortController();setOpening(true);setRecording(null);setError('');
    meetingAudio.get(projectId,source.id,controller.signal).then(value=>{if(!controller.signal.aborted)setRecording(value);})
      .catch(e=>{if(!controller.signal.aborted)setError(message(e));}).finally(()=>{if(!controller.signal.aborted)setOpening(false);});return()=>controller.abort();},[projectId,source,active,open,tick]);
  const current=!!recording&&!!source&&recording.revision===source.revision&&recording.reviewed_revision===recording.revision&&recording.summary_revision===recording.revision;
  return <section className="review-recording" aria-label="Importer une réunion dans la revue"><h4>Propositions issues d’une réunion</h4>
    <p>La synthèse fournit des propositions. Chaque citation est conservée avec son interlocuteur et doit être relue.</p>
    {disabled&&<p>Enregistrez le brouillon et terminez la comparaison avant d’importer.</p>}
    <button type="button" className="button secondary" onClick={()=>setOpen(value=>!value)}>{open?'Fermer la sélection de réunion':'Choisir une réunion validée'}</button>
    {open&&<><button type="button" className="button secondary sm" disabled={loading||opening} onClick={()=>{setSource(null);setRecording(null);setTick(v=>v+1);}}>Recharger la sélection de réunion</button>{error&&<ErrorState message={error} retry={()=>setTick(v=>v+1)}/>} {loading&&<LoadingState label="Chargement des réunions validées"/>}
      {page&&!loading&&<><Pagination offset={page.offset} total={page.total} limit={page.limit} onChange={value=>{setOffset(value);setSource(null);setRecording(null);}} disabled={opening}/>
        {!page.total&&<p>Aucune réunion admissible. Validez la transcription puis générez sa synthèse dans « Réunions et audio ».</p>}
        {page.items.map(row=><button type="button" key={row.id} className="button secondary" aria-pressed={source?.id===row.id} disabled={opening} onClick={()=>setSource(row)}>{row.date} · {row.title} · transcription {row.revision}</button>)}</>}
      {opening&&<LoadingState label="Lecture de la transcription"/>}
      {recording&&<div aria-label="Aperçu de la réunion"><h5>{recording.title}</h5>{!current&&<p role="alert">La transcription a changé : rechargez la sélection de réunion.</p>}
        <p className="review-text">{recording.summary.overview||'Aucune synthèse générale'}</p>
        {(['decisions','actions','open_points'] as const).map(kind=><section key={kind}><h5>{kind==='decisions'?'Décisions proposées':kind==='actions'?'Actions proposées':'Points ouverts proposés'}</h5>
          {(recording.summary[kind]||[]).map((item,index)=>{const segment=recording.segments.find(row=>row.id===item.segment_id);return <article key={index} className="review-evidence"><p>{item.text}</p>
            <blockquote>{item.quote}</blockquote><small>{segment?`${recording.speaker_names[segment.speaker]||segment.speaker} · ${segment.start}–${segment.end} s`:'Segment absent'}</small></article>;})}</section>)}
        <button type="button" className="button primary" disabled={disabled||!current||!active} onClick={()=>{if(source){onImport(source);setOpen(false);setSource(null);setRecording(null);}}}>Importer les propositions à vérifier</button></div>}</>}
  </section>;
}

function PublishedReview({projectId,row,active,onCaptured,onOpenDocument}:{projectId:string;row:ReviewDetail;active:boolean;onCaptured:(value:{id:string;title:string}[])=>void;onOpenDocument?:ReviewsProps['onOpenDocument']}) {
  const [value,setValue]=useState<ReviewPublication|null>(null),[error,setError]=useState(''),[tick,setTick]=useState(0);
  useEffect(()=>{if(!active)return;const controller=new AbortController();setError('');reviewApi.publication(projectId,row.id,controller.signal)
    .then(result=>{if(!controller.signal.aborted){setValue(result);onCaptured(result.snapshot.deliverables.map(document=>({...document,id:reviewRelation(document.id,'erp',result.bindings)})));}}).catch(e=>{if(!controller.signal.aborted)setError(message(e));});return()=>controller.abort();},[projectId,row.id,active,tick,onCaptured]);
  return <section className="review-publication" aria-label="Publication figée"><h4>Publication figée</h4>{error&&<ErrorState message={error} retry={()=>setTick(v=>v+1)}/>}
    {value&&<><p>{value.snapshot.project.code} · {value.snapshot.project.title} · {deliverableDate(value.snapshot.published_at)}</p>
      <p>Publiée par {value.snapshot.published_by}. L’équipe et les livrables ci-dessous sont ceux capturés à la publication.</p>
      <h5>Équipe capturée</h5><ul>{value.snapshot.team.map((member,index)=><li key={index}>{member.name} · {member.role}</li>)}</ul>
      <h5>Livrables capturés</h5><ul>{value.snapshot.deliverables.map(document=><li key={document.id}><span>{document.title}</span>{onOpenDocument&&<button type="button" className="button secondary sm" disabled={!active}
        aria-label={`Ouvrir le livrable ${document.title}`} onClick={()=>onOpenDocument(reviewRelation(document.id,'erp',value.bindings),document.title)}>Ouvrir le livrable</button>}</li>)}</ul>
      <details><summary>Empreintes de publication</summary><p>Revue : <code>{value.sha256}</code></p><p>PDF : <code>{value.pdf_sha256}</code></p></details></>}
  </section>;
}

function ReviewHistory({projectId,row,active}:{projectId:string;row:ReviewDetail;active:boolean}) {
  const [open,setOpen]=useState(false),[page,setPage]=useState<Page<ReviewEvent>|null>(null),[offset,setOffset]=useState(0);
  const [eventId,setEventId]=useState<string|null>(null),[detail,setDetail]=useState<ReviewEventDetail|null>(null);
  const [error,setError]=useState(''),[detailError,setDetailError]=useState(''),[loading,setLoading]=useState(false),[tick,setTick]=useState(0),[detailTick,setDetailTick]=useState(0);
  useEffect(()=>{if(!active||!open)return;const controller=new AbortController();setLoading(true);setError('');reviewApi.history(projectId,row.id,offset,controller.signal)
    .then(value=>{if(!controller.signal.aborted)setPage(value);}).catch(e=>{if(!controller.signal.aborted)setError(message(e));})
    .finally(()=>{if(!controller.signal.aborted)setLoading(false);});return()=>controller.abort();},[projectId,row.id,offset,active,open,tick]);
  useEffect(()=>{if(!active||!open||!eventId)return;const controller=new AbortController();setDetail(null);setDetailError('');reviewApi.event(projectId,row.id,eventId,controller.signal)
    .then(value=>{if(!controller.signal.aborted)setDetail(value);}).catch(e=>{if(!controller.signal.aborted)setDetailError(message(e));});return()=>controller.abort();},[projectId,row.id,eventId,active,open,detailTick]);
  return <section className="review-history" aria-label="Historique de la revue"><h4>Historique des enregistrements</h4><button type="button" className="button secondary" onClick={()=>setOpen(value=>!value)}>{open?'Masquer l’historique':'Consulter l’historique'}</button>
    {open&&<>{error&&<ErrorState message={error} retry={()=>setTick(v=>v+1)}/>} {loading&&<LoadingState label="Chargement de l’historique"/>}
      {page&&<><Pagination offset={page.offset} total={page.total} limit={page.limit} disabled={loading} onChange={value=>{setOffset(value);setEventId(null);setDetail(null);}}/>
        <ol>{page.items.map(event=><li key={event.id}>{actionLabels[event.action]||event.action} · {deliverableDate(event.created_at)} · {event.actor_id}
          <button type="button" className="button secondary sm" onClick={()=>setEventId(event.id)}>Voir l’enregistrement {event.planning_revision}</button></li>)}</ol></>}
      {detailError&&<ErrorState message={detailError} retry={()=>setDetailTick(v=>v+1)}/>}
      {detail&&<div aria-label="Détail de l’enregistrement"><h5>{actionLabels[detail.action]||detail.action} · révision projet {detail.planning_revision}</h5>
        <details><summary>Avant cet enregistrement</summary><HistoricalContent value={detail.previous} bindings={detail.bindings} projectId={projectId} active={active}/></details>
        <details open><summary>Après cet enregistrement</summary><HistoricalContent value={detail.value} bindings={detail.bindings} projectId={projectId} active={active}/></details></div>}</>}
  </section>;
}
function HistoricalContent({value,bindings,projectId,active}:{value:Record<string,unknown>;bindings?:Partial<ReviewBindings>;projectId:string;active:boolean}) {
  const content=value.content as ReviewContent|undefined,provenance=value.provenance as Record<string,ReviewEvidence>|undefined;
  return content?<div><p>{content.meeting_date||'Date non renseignée'} · {content.location||'Lieu non renseigné'}</p><p className="review-text">{content.notes}</p>
    <p>Participants : {content.participants.map(person=>person.name).join(', ')||'Aucun'}</p><p>Jalon : {content.milestone_id?reviewRelation(content.milestone_id,'erp',bindings):'Non renseigné'}</p><p>Livrables : {content.deliverable_ids.map(id=>reviewRelation(id,'erp',bindings)).join(', ')||'Aucun'}</p>
    {content.items.map(item=><article key={item.id}><strong>{reviewSections.find(section=>section.code===item.section_code)?.label}</strong><ReviewValue value={item}/>
      {item.evidence_ids.map(key=><Evidence key={key} value={provenance?.[key]} projectId={projectId} active={active} bindings={bindings}/>)}</article>)}</div>:<ReviewValue value={value}/>;
}
