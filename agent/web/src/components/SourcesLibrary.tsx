import {useQueryState} from '../hooks/useQueryState';
import {ProjectIndexing} from './ProjectIndexing';
import { useEffect, useId, useMemo, useRef, useState } from 'react';
import type { PortfolioRow } from '../lib/api';
import { FILE_FORMATS, fusionSources, type DriveConnection, type LibrarySource, type SourceSearchHit, type SourceFilters, type SourceGraph, type SourcePage } from '../lib/fusionSources';
import '../fusion-library.css';
import {navigateTabs} from '../lib/uiTabs';
import type {WorkspaceCitation} from '../lib/workspaceApi';
import {citationLocatorText} from '../lib/citationLinks';
import {AsyncDownloadLink} from './AsyncDownloadLink';
import { Icon } from '../os/icons';
import {agentPath} from '../lib/agentRoutes';
const fail=(error:unknown)=>error instanceof Error?error.message:String(error);
const date=(value:string)=>{const parsed=new Date(value);return Number.isNaN(parsed.getTime())?value:parsed.toLocaleDateString('fr-FR');};
const KINDS:Record<string,string>={document:'Document',mail:'Mail',note:'Note',meeting:'Réunion',phone:'Téléphone'};
const INDEX:Record<string,string>={indexed:'Indexée',completed:'Indexée',pending:'À indexer',queued:'En attente',running:'Indexation',failed:'Échec',not_indexed:'Non indexée',extracted:'Texte extrait',ocr_required:'Texte du scan à reconnaître',partially_extracted:'Texte partiellement extrait',ocr_extracted:'Texte OCR · relecture nécessaire',ocr_partial:'OCR partiel · relecture nécessaire',empty:'Sans texte',canonical_note:'Note du projet',projection_pending:'Projection en attente',multimodal_pending:'Sans texte'};
const canRecognize=(source:LibrarySource)=>!!source.source_id&&!!source.version_id&&source.current&&source.file_format==='pdf'&&['ocr_required','partially_extracted','ocr_partial'].includes(source.extraction_status);
const originalLabel=(source:LibrarySource)=>source.kind==='note'&&source.version_id?'Télécharger la version de note':'Ouvrir l’original';
export type SourcesLibraryProps={rows:PortfolioRow[];active?:boolean;onOpenSource:(id:string,title?:string,evidence?:WorkspaceCitation[])=>void;onOpenProject?:(id:string,tab:string)=>void;onCreateMeeting?:(projectId?:string)=>boolean|void};
export function SourcesLibrary({rows,active=true,onOpenSource,onOpenProject,onCreateMeeting}:SourcesLibraryProps){
  const tabId=useId();
  const sourcesPath=agentPath('/app/sources');
  const [knowledgeProject,setKnowledgeProject]=useQueryState<string>('knowledge_project','',sourcesPath);
  const [page,setPage]=useState<SourcePage|null>(null),[project,setProject]=useQueryState<string>('project','',sourcesPath),[query,setQuery]=useQueryState<string>('q','',sourcesPath),[kind,setKind]=useQueryState<string>('kind','all',sourcesPath);
  const [label,setLabel]=useQueryState<string>('label','',sourcesPath),[status,setStatus]=useQueryState<string>('status','all',sourcesPath),[sort,setSort]=useQueryState<NonNullable<SourceFilters['sort']>>('sort','date_desc',sourcesPath);
  const [fileFormat,setFileFormat]=useQueryState<NonNullable<SourceFilters['file_format']>>('format','all',sourcesPath);
  const perimeterLabel=`Périmètre et filtres${kind!=='all'?` · ${KINDS[kind]||kind}`:''}${fileFormat!=='all'?` · ${fileFormat==='unknown'?'Format non reconnu':FILE_FORMATS[fileFormat!]}`:''}${status!=='all'?` · ${status==='resolved'?'Sources rattachées':'À rattacher'}`:''}${label?` · ${label}`:''}`;
  const [offset,setOffset]=useQueryState<number>('offset',0,sourcesPath),[tick,setTick]=useState(0),[loading,setLoading]=useState(false),[error,setError]=useState('');
  const [indexing,setIndexing]=useQueryState<boolean>('indexing',false,sourcesPath);
  const [view,setView]=useQueryState<'list'|'grid'|'graph'>('view','list',sourcesPath),[graph,setGraph]=useState<SourceGraph|null>(null);
  const [pageScope,setPageScope]=useState<string|undefined>(),[graphScope,setGraphScope]=useState<string|undefined>();
  const [selected,setSelectedState]=useState<string[]>([]),[labelDraft,setLabelDraft]=useState(''),[busy,setBusy]=useState('');
  const [imports,setImports]=useState(false),[url,setUrl]=useState(''),[driveFile,setDriveFile]=useState(''),[drive,setDrive]=useState<DriveConnection|null>(null);
  const [accessToken,setAccessToken]=useState(''),[notice,setNotice]=useState('');
  const [assignment,setAssignment]=useState<{source:LibrarySource;destinations:Awaited<ReturnType<typeof fusionSources.destinations>>}|null>(null);
  const [recognizing,setRecognizing]=useState<string|null>(null);
  const [progress,setProgress]=useState<{done:number;total:number;success:number;unchanged:number;errors:string[]}|null>(null);
  const [calendar,setCalendar]=useState<{title:string;date:string;description:string}[]>([]);
  const [semantic,setSemantic]=useState<SourceSearchHit[]|null>(null);
  const [semanticResultScope,setSemanticResultScope]=useState<string|null>(null);
  const [semanticPendingScope,setSemanticPendingScope]=useState<string|null>(null);
  const semanticRevision=useRef(0),semanticMounted=useRef(true),semanticCurrentScope=useRef('');
  const invalidateSemantic=()=>{semanticRevision.current+=1;setSemantic(null);setSemanticResultScope(null);setSemanticPendingScope(null);setError('');setNotice('');};
  // Every existing selection path uses this updater, including page/clear/labels/pagination.
  const setSelected=(value:string[]|((previous:string[])=>string[]))=>{invalidateSemantic();setSelectedState(value);};
  const labelEditor=useRef<HTMLInputElement>(null),[focusLabels,setFocusLabels]=useState(false);
  const brain=knowledgeProject||rows.find(row=>row.id===project)?.brain_project_id||undefined;
  const semanticScopeKey=JSON.stringify([brain??null,query.trim(),[...selected].sort(),active]);
  // A props-derived Brain change is witnessed synchronously, before effects or async callbacks.
  semanticCurrentScope.current=semanticScopeKey;
  useEffect(()=>{semanticMounted.current=true;return()=>{semanticMounted.current=false;semanticRevision.current+=1;};},[]);
  useEffect(()=>{invalidateSemantic();},[brain,active]);
  useEffect(()=>{
    if(!active)return;const controller=new AbortController();setLoading(true);setError('');
    const timer=setTimeout(()=>{
      const operation=view==='graph'?fusionSources.graph(brain,controller.signal,offset):fusionSources.list({query,project_id:brain,source_type:kind,file_format:fileFormat,label,status,sort,offset,limit:25},controller.signal);
      void operation.then(value=>{
        if(controller.signal.aborted)return;if(view==='graph'){setGraph(value as SourceGraph);setGraphScope(brain);}
        else {setPage(value as SourcePage);setPageScope(brain);}
      }).catch(failure=>{if(!controller.signal.aborted)setError(fail(failure));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    },200);
    return()=>{clearTimeout(timer);controller.abort();};
  },[active,brain,query,kind,fileFormat,label,status,sort,offset,tick,view]);
  useEffect(()=>{
    setDrive(null);if(!imports)return;let current=true;
    void fusionSources.driveStatus().then(value=>{if(current)setDrive(value);}).catch(()=>undefined);
    return()=>{current=false;};
  },[imports]);
  useEffect(()=>{if(focusLabels&&selected.length){labelEditor.current?.focus();setFocusLabels(false);}},[focusLabels,selected]);
  const filtered=(action:()=>void)=>{action();setOffset(0);setSelected([]);};
  // A pending scope change cannot expose source actions from the previous project.
  const visiblePage=pageScope===brain?page:null,visibleGraph=graphScope===brain?graph:null;
  const run=async(name:string,action:()=>Promise<void>)=>{
    if(busy)return;setBusy(name);setError('');setNotice('');try{await action();}catch(failure){setError(fail(failure));}finally{setBusy('');}
  };
  const files=(files:FileList|null,folder=false)=>{
    if(!files?.length||!brain)return;const chosen=Array.from(files);
    void run('Import',async()=>{
      const result={done:0,total:chosen.length,success:0,unchanged:0,errors:[] as string[]};setProgress({...result});
      for(const file of chosen){
        try{const imported=await fusionSources.file(brain,file,folder);if(imported.unchanged||imported.replayed)result.unchanged++;else result.success++;
          if(imported.extraction_error)result.errors.push(`${file.name} : ${imported.extraction_error}`);
        }catch(failure){result.errors.push(`${file.name} : ${fail(failure)}`);}finally{result.done++;setProgress({...result,errors:[...result.errors]});}
      }
      setTick(value=>value+1);setNotice(`${result.success} import(s), ${result.unchanged} fichier(s) déjà conservé(s), ${result.errors.length} erreur(s).`);
    });
  };
  const importURL=()=>void run('Import du lien',async()=>{if(!brain||!url.trim())return;const result=await fusionSources.url(brain,url.trim());setUrl('');setTick(value=>value+1);
    setNotice(result.reinterpreted?'Interprétation au bon format conservée ; l’original et l’ancienne extraction restent consultables. L’état de traitement est visible dans la liste.':'Lien importé. L’état d’extraction et d’indexation est visible dans la liste.');});
  const importDrive=()=>void run('Import Google Drive',async()=>{if(drive?.enabled!==true||!brain||!driveFile.trim())return;await fusionSources.drive(brain,driveFile.trim());setTick(value=>value+1);setDrive(await fusionSources.driveStatus());setNotice('Fichier Drive conservé dans Kiara.');});
  const labelSelection=()=>void run('Enregistrement des labels',async()=>{
    const labels=labelDraft.split(',').map(value=>value.trim()).filter(Boolean);
    for(const id of selected)await fusionSources.labels(id,labels);setTick(value=>value+1);setSelected([]);setLabelDraft('');setNotice('Labels enregistrés.');
  });
  const selectedSources=visiblePage?.items.filter(item=>selected.includes(item.id))||[];
  const toggle=(id:string)=>setSelected(previous=>previous.includes(id)?previous.filter(value=>value!==id):[...previous,id]);
  const editLabels=(source?:LibrarySource)=>{
    if(source?.source_id){setSelected([source.id]);setFocusLabels(true);return;}
    if(selected.length){labelEditor.current?.focus();return;}
    setNotice('Sélectionnez une ou plusieurs sources, puis ouvrez leur éditeur de labels. Le remplacement reste explicite.');
  };
  const open=(source:LibrarySource)=>{if(source.source_id)onOpenSource(source.source_id,source.title);else if(source.erp_project_id)onOpenProject?.(source.erp_project_id,'documents');};
  const assignmentAction=(source:LibrarySource)=>source.status==='resolution_pending'&&source.source_id&&
    <button type="button" disabled={!!busy} onClick={()=>void run('Chargement des projets',async()=>{
      const destinations=await fusionSources.destinations();
      if(!destinations.length){setNotice('Aucun projet accessible pour ce rattachement.');return;}
      setAssignment({source,destinations});
    })}>Rattacher au projet</button>;
  const recognize=(source:LibrarySource)=>void run(`Reconnaissance de ${source.title}`,async()=>{
    setRecognizing(source.source_id!);
    try {
    const result=await fusionSources.ocr(source.source_id!);invalidateSemantic();setSelected([]);setTick(value=>value+1);
    setNotice(`${result.recognized_pages} page(s) reconnue(s)${result.empty_pages?`, ${result.empty_pages} page(s) sans texte reconnu`:''}. ${result.recognized_pages?'Texte OCR à relire ; l’original et l’ancienne extraction sont conservés. L’indexation du texte est demandée.':'L’original est conservé ; aucun texte n’a été ajouté.'}`);
    } finally {setRecognizing(null);}
  });
  return <section className="fusion-library" aria-label="Bibliothèque des sources">
    <header className="fusion-page-heading"><h1>Sources</h1>
      {recognizing&&<button type="button" onClick={()=>void fusionSources.cancelOcr(recognizing).then(()=>setNotice('Annulation demandée ; l’original et les pages traitées seront conservés.')).catch(failure=>setError(fail(failure)))}>Annuler la reconnaissance</button>}
      <label className="fusion-project-current"><span className="fusion-sr-only">Projet</span><select value={knowledgeProject?'knowledge':project} disabled={!!busy} onChange={event=>filtered(()=>{setKnowledgeProject('');setProject(event.target.value);})}><option value="">Tous les projets accessibles</option>
        {knowledgeProject&&<option value="knowledge">Projet de connaissance sélectionné</option>}
        {rows.map(row=><option key={row.id} value={row.id} disabled={!row.brain_project_id}>{row.code} — {row.title}{!row.brain_project_id?' (connaissance à relier)':''}</option>)}</select></label>
      {onCreateMeeting&&<button type="button" className="fusion-primary" disabled={!!busy} title="Préparer une séance ; le micro démarre seulement à votre demande" onClick={()=>onCreateMeeting(rows.some(row=>row.id===project)?project:undefined)}>Nouvelle séance</button>}
      </header>
    {assignment&&<form key={assignment.source.id} className="fusion-imports" aria-label="Rattacher la source"
      onSubmit={event=>{
        event.preventDefault();
        const target=new FormData(event.currentTarget).get('project');
        if(!assignment.source.source_id||typeof target!=='string'||!assignment.destinations.some(row=>row.id===target))return;
        const sourceId=assignment.source.source_id;
        void run('Rattachement',async()=>{
          await fusionSources.attach(sourceId,target);
          setAssignment(null);setTick(value=>value+1);setNotice('Source rattachée au projet.');
        });
      }}>
      <strong>{assignment.source.title}</strong>
      <label>Projet de destination<select autoFocus required name="project" defaultValue="" disabled={!!busy}>
        <option value="">Choisir un projet</option>
        {assignment.destinations.map(row=><option key={row.id} value={row.id}>{row.code} · {row.name}</option>)}
      </select></label>
      <button type="submit" disabled={!!busy}>Confirmer le rattachement</button>
      <button type="button" disabled={!!busy} onClick={()=>setAssignment(null)}>Annuler</button>
    </form>}
    <div className="fusion-library-tabs" role="tablist" aria-label="Présentation des sources" onKeyDown={navigateTabs}>
      <button type="button" role="tab" id={`${tabId}-list`} tabIndex={view==='graph'?-1:0} aria-controls={`${tabId}-panel`} aria-selected={view!=='graph'} onClick={()=>{setView('list');setOffset(0);}}>Liste des fichiers</button>
      <button type="button" role="tab" id={`${tabId}-graph`} tabIndex={view==='graph'?0:-1} aria-controls={`${tabId}-panel`} aria-selected={view==='graph'} onClick={()=>{setView('graph');setOffset(0);}}>Vue des relations</button>

    </div>
    <div className="fusion-indexing-toggle"><button type="button" aria-expanded={indexing} aria-controls={`${tabId}-indexing`} onClick={()=>setIndexing(value=>!value)}>{indexing?'Masquer':'Afficher'} l’état de l’indexation</button></div><div id={`${tabId}-indexing`} hidden={!indexing}>{indexing&&<ProjectIndexing active={active} projectId={brain}/>}</div>
    <div role="tabpanel" id={`${tabId}-panel`} aria-labelledby={`${tabId}-${view==='graph'?'graph':'list'}`}>
    {view!=='graph'&&<>
      <div className="fusion-search-row"><label className="fusion-search"><span className="fusion-sr-only">Rechercher une source</span><input type="search" disabled={!!busy} maxLength={2000} placeholder="Rechercher dans les sources" value={query} onChange={event=>filtered(()=>setQuery(event.target.value))}/></label>
        <button type="button" className="fusion-primary" onClick={()=>setImports(value=>!value)} aria-expanded={imports}>{imports?'Fermer l’import':'Ajouter une source'}</button>
        <button type="button" aria-label="Actualiser les sources" disabled={!!busy} onClick={()=>setTick(value=>value+1)}>↻</button>
      <details className="fusion-library-advanced discrete-icon-menu icon-menu-details" onKeyDown={event=>{if(event.key==='Escape'){event.stopPropagation();event.currentTarget.open=false;event.currentTarget.querySelector('summary')?.focus();}}}>
        <summary className="discrete-icon-summary icon-menu-summary" aria-label="Filtres et options des sources" title="Filtres et options des sources"><Icon name="filter" size={16} />{perimeterLabel}</summary>
      <div className="fusion-library-toolbar icon-menu-popover">
        <p>Documents, notes et réunions de vos projets, avec leurs versions et leurs preuves. Le projet visible gouverne les imports et la préparation d’une séance.</p>
      <div className="fusion-label-filter-row" aria-label="Labels des sources">
        <button type="button" disabled={!!busy} onClick={()=>editLabels()}>Ajouter un label</button>
        <button type="button" aria-pressed={!label} onClick={()=>filtered(()=>setLabel(''))}>Tous les labels</button>
        {visiblePage?.labels.map(value=><button type="button" key={value} aria-pressed={label===value} onClick={()=>filtered(()=>setLabel(label===value?'':value))}>{value}</button>)}
      </div>
        <div className="fusion-format-shortcuts" aria-label="Formats des sources">{(['pdf','png','txt','xlsx'] as const).map(value=><button type="button" key={value} aria-pressed={fileFormat===value} onClick={()=>filtered(()=>setFileFormat(fileFormat===value?'all':value))}>{FILE_FORMATS[value]}</button>)}</div>
        <label>Type de source<select value={kind} onChange={event=>filtered(()=>setKind(event.target.value))}><option value="all">Tous</option>{Object.entries(KINDS).map(([key,value])=><option key={key} value={key}>{value}</option>)}</select></label>
        <label>Format<select value={fileFormat} onChange={event=>filtered(()=>setFileFormat(event.target.value as NonNullable<SourceFilters['file_format']>))}><option value="all">Tous</option>{Object.entries(FILE_FORMATS).map(([key,value])=><option key={key} value={key}>{value}</option>)}<option value="unknown">Sans format de fichier reconnu</option></select></label>
        <label>Label<select value={label} onChange={event=>filtered(()=>setLabel(event.target.value))}><option value="">Tous</option>{visiblePage?.labels.map(value=><option key={value} value={value}>{value}</option>)}</select></label>
        <label>État<select value={status} onChange={event=>filtered(()=>setStatus(event.target.value))}><option value="all">Tous</option><option value="resolved">Sources rattachées</option><option value="pending">À rattacher</option></select></label>
        <button type="button" disabled={query.trim().length<2||!!busy} onClick={()=>void run('Recherche dans les sources',async()=>{
          const revision=semanticRevision.current,requestScope=semanticScopeKey;
          const current=()=>semanticMounted.current&&revision===semanticRevision.current&&requestScope===semanticCurrentScope.current;
          setSemanticPendingScope(requestScope);
          try {
            const result=await fusionSources.search(query.trim(),brain,selected);
            if(!current())return;
            setSemantic(result.items);setSemanticResultScope(requestScope);
            if(result.issues?.length)setNotice(`${result.issues.length} source(s) écartée(s) ; relisez leur état avant de les utiliser.`);
          } catch(failure) {if(current())setError(fail(failure));}
          finally {if(current())setSemanticPendingScope(null);}
        })}>{semanticPendingScope===semanticScopeKey?'Recherche en cours…':'Rechercher dans le contenu des sources'}</button>
        {semanticPendingScope===semanticScopeKey&&<p role="status">Recherche dans le périmètre choisi…</p>}
      </div></details>
      </div>
      </>}
    <div className="fusion-library-summary">
      {view==='graph'&&<><button type="button" className="fusion-primary" onClick={()=>setImports(value=>!value)} aria-expanded={imports}>{imports?'Fermer l’import':'Ajouter une source'}</button>
        <button type="button" aria-label="Actualiser les sources" disabled={!!busy} onClick={()=>setTick(value=>value+1)}>↻</button>
        <details className="fusion-library-advanced discrete-icon-menu icon-menu-details">
          <summary className="discrete-icon-summary icon-menu-summary" aria-label="Périmètre des sources" title="Périmètre des sources"><Icon name="filter" size={16} /><span className="fusion-sr-only">{perimeterLabel}</span></summary>
          <div className="fusion-library-toolbar icon-menu-popover"><p>Documents, notes et réunions de vos projets, avec leurs versions et leurs preuves. Le projet visible gouverne les imports et la préparation d’une séance.</p></div>
        </details></>}
      {view!=='graph'&&<><span className="fusion-source-total">{visiblePage?`${visiblePage.total} source${visiblePage.total===1?'':'s'}`:'Lecture du périmètre…'}</span>
        <label className="fusion-sort"><span className="fusion-sr-only">Trier</span><select value={sort} onChange={event=>filtered(()=>setSort(event.target.value as NonNullable<SourceFilters['sort']>))}><option value="date_desc">Imports récents</option><option value="date_asc">Imports anciens</option><option value="title_asc">Nom A–Z</option><option value="title_desc">Nom Z–A</option></select></label>
        <button type="button" aria-label="Afficher la liste" aria-pressed={view==='list'} onClick={()=>setView('list')}>☷</button>
        <button type="button" aria-label="Afficher la grille" aria-pressed={view==='grid'} onClick={()=>setView('grid')}>▦</button>
      </>}
    </div>
    {imports&&<section className="fusion-import-panel" aria-label="Ajouter des sources">
      <h2>Importer dans {rows.find(row=>row.id===project)?.code||'un projet'}</h2>
      {!brain&&<p role="status">Choisissez un projet pour importer ses documents et liens.</p>}
      <div className="fusion-import-options"><label>Fichiers sélectionnés<input type="file" multiple disabled={!brain||!!busy} onChange={event=>{files(event.target.files);event.target.value='';}}/></label>
        <label>Dossier choisi<input type="file" multiple ref={element=>element?.setAttribute('webkitdirectory','')} disabled={!brain||!!busy} onChange={event=>{files(event.target.files,true);event.target.value='';}}/></label>
        <form onSubmit={event=>{event.preventDefault();importURL();}}><label>Page ou document web<input type="url" value={url} onChange={event=>setUrl(event.target.value)} placeholder="https://…" disabled={!!busy}/></label><button type="submit" disabled={!brain||!url.trim()||!!busy}>Importer le lien</button></form>
        {drive?.enabled===true&&<form onSubmit={event=>{event.preventDefault();importDrive();}}><label>Fichier Google Drive<input value={driveFile} onChange={event=>setDriveFile(event.target.value)} placeholder="Identifiant du fichier Drive" disabled={!!busy}/></label><button type="submit" disabled={!brain||!drive.configured||!driveFile.trim()||!!busy}>Importer à nouveau</button></form>}
      </div>
      {visiblePage?.can_import_audio&&<details><summary>Importer un enregistrement audio</summary>
        <form aria-label="Importer un enregistrement audio" onSubmit={event=>{
          event.preventDefault();
          const form=event.currentTarget, body=new FormData(form);
          if(brain)body.set('candidate_project_id',brain);
          void run('Import audio',async()=>{
            const result=await fusionSources.audio(body);
            setTick(value=>value+1);form.reset();
            setNotice(result.status==='duplicate'?'Cet enregistrement est déjà présent.':
              result.status==='resolution_pending'?'Audio importé. Il reste à rattacher dans Sources.':'Audio importé dans le projet.');
          });
        }}>
          <label>Enregistrement<input name="file" type="file" accept="audio/*,.wav,.mp3,.m4a,.webm,.ogg" required disabled={!!busy}/></label>
          <label>Type d’enregistrement<select name="source_type" disabled={!!busy}><option value="meeting">Réunion</option><option value="phone">Téléphone</option></select></label>
          <label>Transcription existante<textarea name="transcript" disabled={!!busy}/></label>
          <button type="submit" disabled={!!busy}>Importer l’audio</button>
        </form>
      </details>}
      {drive?.enabled===true&&<><p className="fusion-meta">Google Drive : {drive.configured?'connecté à Kiara':'connexion à configurer'}{drive.last_import?` · dernier import ${date(drive.last_import)}`:''}.</p>
      <details><summary>Connexion avancée Google Drive</summary><p>Le jeton Google permet d’importer le fichier que vous sélectionnez.</p>
        <form onSubmit={event=>{event.preventDefault();if(drive.enabled!==true)return;void run('Connexion Drive',async()=>{setDrive(await fusionSources.connectDrive(accessToken));setAccessToken('');setNotice('Connexion Google Drive enregistrée.');});}}>
          <label>Jeton d’accès Google<input type="password" autoComplete="off" value={accessToken} onChange={event=>setAccessToken(event.target.value)} disabled={!!busy}/></label>
          <button type="submit" disabled={accessToken.length<20||!!busy}>Enregistrer la connexion</button></form></details></>}
      <details><summary>Contexte de calendrier</summary><label>Exporter puis sélectionner un calendrier ICS<input type="file" accept=".ics,text/calendar" disabled={!!busy} onChange={event=>{
        const file=event.target.files?.[0];if(file)void run('Lecture du calendrier',async()=>{
          const result=await fusionSources.calendar(file);setCalendar((result.events||[]).map(item=>({title:item.summary||'Événement',date:item.dtstart||'',description:item.description||''})));
        });event.target.value='';}}/></label>
        {calendar.map((item,index)=><article key={index}><strong>{item.title}</strong><p>{item.date}</p><p>{item.description}</p></article>)}
        {calendar.length>0&&<p>Ces informations restent une prévisualisation. Elles ne créent aucune réunion automatiquement.</p>}</details>
      {progress&&<div role="status"><progress value={progress.done} max={progress.total} aria-label="Progression des imports"/><p>{progress.done}/{progress.total} traités · {progress.success} importés · {progress.unchanged} déjà conservés</p>
        {progress.errors.length>0&&<ul>{progress.errors.map((value,index)=><li key={index}>{value}</li>)}</ul>}</div>}
    </section>}
    {error&&<p role="alert" className="fusion-error">{error}</p>}{notice&&<p role="status" className="fusion-notice">{notice}</p>}
    {loading&&<p role="status">Lecture des sources…</p>}
    {busy&&<p role="status" aria-live="polite">{busy} en cours…</p>}
    {semanticResultScope===semanticScopeKey&&semantic&&<section className="fusion-semantic-results" aria-label="Résultats de recherche"><h2>Résultats cités</h2>
      <p>Les correspondances restent des preuves à examiner ; leur proximité ne valide pas une information.</p><button type="button" onClick={invalidateSemantic}>Fermer les résultats</button>
      {!semantic.length&&<p>Aucun résultat. Modifiez la recherche ou le périmètre.</p>}
      {semantic.map(hit=><article key={hit.id}><button type="button" onClick={()=>onOpenSource(hit.source_id,undefined,[{
        source_id:hit.source_id,source_url:hit.source_url,excerpt:hit.excerpt||hit.text,locator:hit.locator,
      }])}>Consulter la source · {({text:'Texte',image:'Image',audio:'Audio',pdf:'Page PDF'})[hit.modality]||hit.modality}</button>
        <p>{hit.excerpt||hit.text}</p><p>{citationLocatorText(hit.locator,' : ')}</p>
        <AsyncDownloadLink href={fusionSources.original(hit.source_id)}>Ouvrir l’original cité</AsyncDownloadLink></article>)}
    </section>}
    {!loading&&!error&&view!=='graph'&&visiblePage&&!visiblePage.items.length&&<div className="fusion-empty"><h2>Aucune source pour ce périmètre</h2><p>Modifiez les filtres ou ajoutez une source au projet choisi.</p></div>}
    {view==='graph'?visibleGraph&&<><SourceRelations graph={visibleGraph} onOpenSource={onOpenSource}/>
      {visibleGraph.total!=null&&<nav aria-label="Pages des relations"><span role="status">{visibleGraph.total?`${(visibleGraph.offset??0)+1}–${Math.min(visibleGraph.total,(visibleGraph.offset??0)+(visibleGraph.limit??200))}`:'0'} / {visibleGraph.total} sources</span>
        <button type="button" disabled={loading||!(visibleGraph.offset??0)} onClick={()=>setOffset(Math.max(0,(visibleGraph.offset??0)-(visibleGraph.limit??200)))}>Relations précédentes</button>
        <button type="button" disabled={loading||!visibleGraph.has_next} onClick={()=>setOffset((visibleGraph.offset??0)+(visibleGraph.limit??200))}>Relations suivantes</button></nav>}
    </>:<>
      {selected.length>0&&<div className="fusion-selection" aria-label="Sources sélectionnées"><strong>{selected.length} source(s) choisie(s)</strong>
        <label>Labels de la sélection<input ref={labelEditor} maxLength={1600} value={labelDraft} onChange={event=>setLabelDraft(event.target.value)} placeholder="Technique, Réunion…"/></label>
        <button type="button" disabled={!!busy} onClick={labelSelection}>Remplacer les labels</button><button type="button" onClick={()=>setSelected([])}>Désélectionner</button>
        <p>Cette opération remplace tous les labels des sources sélectionnées. Elle n’ajoute pas automatiquement aux labels déjà conservés.</p>
        <span>{selectedSources.map(item=>item.title).join(' · ')}</span></div>}
      {visiblePage?.items.length?view==='grid'?<div className="fusion-source-grid">{visiblePage.items.map(source=><article key={source.id}>
        <label><input type="checkbox" aria-label={`Sélectionner ${source.title}`} disabled={!source.source_id} checked={selected.includes(source.id)} onChange={()=>toggle(source.id)}/><span>{KINDS[source.kind]||source.kind}{source.file_format?` · ${FILE_FORMATS[source.file_format]}`:''}</span></label>
        <button type="button" className="fusion-source-title" onClick={()=>open(source)}>{source.title}</button>
        <SourceMetadata source={source}/><div className="fusion-labels">{source.labels.map(value=><button type="button" key={value} onClick={()=>filtered(()=>setLabel(value))}>{value}</button>)}</div>
        {canRecognize(source)&&<button type="button" disabled={!!busy} onClick={()=>recognize(source)}>Reconnaître le texte du scan</button>}
        {assignmentAction(source)}
        {source.source_id?<AsyncDownloadLink href={fusionSources.original(source.source_id)}>{originalLabel(source)}</AsyncDownloadLink>:<span>Projection vers la connaissance en attente</span>}
      </article>)}</div>:<div className="fusion-table-scroll"><table><thead><tr>
        <th><input type="checkbox" aria-label="Sélectionner la page des sources" checked={visiblePage.items.some(source=>!!source.source_id)&&visiblePage.items.filter(source=>!!source.source_id).every(source=>selected.includes(source.id))}
          onChange={event=>setSelected(event.target.checked?visiblePage.items.filter(source=>!!source.source_id).map(source=>source.id):[])}/></th><th>Format</th><th>Nom</th><th>Import</th><th>Labels</th><th><span className="fusion-sr-only">Détails</span></th><th><span className="fusion-sr-only">Original</span></th>
      </tr></thead><tbody>{visiblePage.items.map(source=><tr key={source.id}><td><input type="checkbox" aria-label={`Sélectionner ${source.title}`} disabled={!source.source_id} checked={selected.includes(source.id)} onChange={()=>toggle(source.id)}/></td>
        <td>{source.file_format?FILE_FORMATS[source.file_format]:KINDS[source.kind]||source.kind}</td><td><button type="button" className="fusion-source-title" onClick={()=>open(source)}>{source.title}</button></td>
        <td>{date(source.date)}</td><td><div className="fusion-labels">{source.labels.map(value=><button type="button" key={value} onClick={()=>filtered(()=>setLabel(value))}>{value}</button>)}
          {!source.labels.length&&source.source_id&&<button type="button" aria-label={`Ajouter un label à ${source.title}`} onClick={()=>editLabels(source)}>Ajouter un label</button>}</div></td>
        <td><details className="fusion-source-details"><summary aria-label={`Détails de ${source.title}`}>⋯</summary><div>
          {source.file_format&&<p>{KINDS[source.kind]||source.kind}</p>}
          <p>{source.version_id?'Version conservée':'Source originale'}{!source.current?' · version hors rappel courant':''}</p>
          {source.erp_project_id&&onOpenProject?<button type="button" className="fusion-text-button" onClick={()=>onOpenProject(source.erp_project_id!,'documents')}>{source.project_code||'Projet'}</button>:<p>{source.project_code||'—'}</p>}
          <p>{INDEX[source.extraction_status]||source.extraction_status} · {INDEX[source.index_status]||source.index_status}</p>
          {canRecognize(source)&&<button type="button" disabled={!!busy} onClick={()=>recognize(source)}>Reconnaître le texte du scan</button>}
          {assignmentAction(source)}
          </div></details></td>
        <td>{source.source_id?<AsyncDownloadLink href={fusionSources.original(source.source_id)} aria-label={`${originalLabel(source)} : ${source.title}`}>↗</AsyncDownloadLink>:<span>À projeter</span>}</td></tr>)}</tbody></table></div>:null}
      {visiblePage&&<nav className="fusion-pagination" aria-label="Pagination des sources"><span>{visiblePage.total?`${visiblePage.offset+1}–${Math.min(visiblePage.offset+visiblePage.limit,visiblePage.total)} sur ${visiblePage.total}`:'0 source'}</span>
        <button type="button" disabled={loading||!offset} onClick={()=>{setOffset(Math.max(0,offset-25));setSelected([]);}}>Précédentes</button>
        <button type="button" disabled={loading||!visiblePage.has_next} onClick={()=>{setOffset(offset+25);setSelected([]);}}>Suivantes</button></nav>}
    </>}
    </div>
  </section>;
}
function SourceMetadata({source}:{source:LibrarySource}){return <p className="fusion-meta">{source.project_code||'Projet'} · {date(source.date)}<br/>
  {INDEX[source.extraction_status]||source.extraction_status} · {INDEX[source.index_status]||source.index_status}{!source.current?' · hors rappel courant':''}</p>;}
function SourceRelations({graph,onOpenSource}:{graph:SourceGraph;onOpenSource:SourcesLibraryProps['onOpenSource']}){
  const [selectedId,setSelected]=useState<string|null>(null),[zoom,setZoom]=useState(1);
  const selected=graph.nodes.find(node=>node.id===selectedId);
  const positions=useMemo(()=>{const counts:Record<string,number>={};return new Map(graph.nodes.map(node=>{
    const index=counts[node.kind]||0;counts[node.kind]=index+1;return [node.id,{x:({project:100,source:340,knowledge:580,session:820})[node.kind],y:70+index*70}];}));},[graph]);
  const height=Math.max(350,...[...positions.values()].map(position=>position.y+70));
  const links=graph.edges.filter(edge=>positions.has(edge.source)&&positions.has(edge.target));
  return <section className="fusion-graph" aria-label="Relations et provenance des sources"><p className="fusion-meta">Projets · Sources · Informations. Les liens représentent une appartenance ou une citation connue.</p>
    {graph.truncated&&<p role="status">{graph.total!=null?'Les sources sont présentées par pages ; leurs citations enregistrées sont toutes conservées.':'La vue est limitée. Choisissez un projet pour explorer ses relations.'}</p>}
    {!graph.nodes.length?<p>Aucune relation pour ce périmètre.</p>:<>
      <div className="fusion-graph-controls"><button type="button" aria-label="Agrandir le graphe" onClick={()=>setZoom(value=>Math.min(2,value+.25))}>+</button>
        <button type="button" aria-label="Réduire le graphe" onClick={()=>setZoom(value=>Math.max(.5,value-.25))}>−</button><button type="button" onClick={()=>setZoom(1)}>Taille initiale</button></div>
      <div className="fusion-graph-scroll"><svg viewBox={`0 0 960 ${height}`} style={{width:960*zoom,height:height*zoom}} role="img" aria-label="Graphe des appartenances et des citations">
        <g className="fusion-graph-edges">{links.map(edge=>{const a=positions.get(edge.source)!,b=positions.get(edge.target)!;return <line key={edge.id} x1={a.x} y1={a.y} x2={b.x} y2={b.y}><title>{edge.kind==='cites'?'Citation':edge.kind==='belongs_to'?'Appartenance':'Source de séance'}</title></line>;})}</g>
        {graph.nodes.map(node=>{const position=positions.get(node.id)!;return <g key={node.id} transform={`translate(${position.x},${position.y})`} className={`fusion-graph-node fusion-graph-${node.kind}`}
          role="button" tabIndex={0} aria-label={`${({project:'Projet',source:'Source',knowledge:'Information',session:'Séance'})[node.kind]} : ${node.label}`}
          onClick={()=>setSelected(node.id)} onKeyDown={event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();setSelected(node.id);}}}>
          <rect x={-94} y={-20} width={188} height={40} rx={8}/><text textAnchor="middle" dominantBaseline="middle">{node.label.length>25?`${node.label.slice(0,24)}…`:node.label}</text><title>{node.label}</title></g>;})}
      </svg></div>
      {selected&&<div className="fusion-graph-detail" role="status"><strong>{selected.label}</strong><p>{links.filter(edge=>edge.source===selected.id||edge.target===selected.id).length} relation(s)</p>
        {selected.source_id&&<button type="button" onClick={()=>onOpenSource(selected.source_id!,selected.label)}>Consulter la source</button>}</div>}
      <details><summary>Liste des relations</summary><ul>{links.map(edge=><li key={edge.id}>{graph.nodes.find(node=>node.id===edge.source)?.label} → {graph.nodes.find(node=>node.id===edge.target)?.label} ({edge.kind==='cites'?'citation':edge.kind==='belongs_to'?'appartenance':'source de séance'})</li>)}</ul></details>
    </>}
  </section>;
}
