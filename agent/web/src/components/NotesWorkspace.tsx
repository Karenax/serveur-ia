import {useEffect, useRef, useState, type KeyboardEvent} from 'react';
import {allNotesScope as all, notesApi, personalNotesScope as personal, type NoteDetail, type NotesProject} from '../lib/projectNotes';
import {ProjectNotesPanel} from './ProjectNotesPanel';
import {ErrorState, LoadingState} from './Ui';

type Selection = {id:string;scope:string};
const label = (project:NotesProject) => project.code || project.title;

export function NotesWorkspace({active,initialProjectId,onReturn}:{active:boolean;initialProjectId?:string;onReturn?:()=>void}){
  const [catalogue,setCatalogue]=useState<{projects:NotesProject[];can_edit:boolean}>();
  const [selection,setSelection]=useState<{scope:string;note?:Selection;key:number}>({scope:initialProjectId??personal,key:0});
  const [projectChoices,setProjectChoices]=useState<string[]|null>(null);
  const [refresh,setRefresh]=useState(0),[error,setError]=useState(''),[notice,setNotice]=useState('');
  const panel=useRef<HTMLDivElement>(null),tablist=useRef<HTMLDivElement>(null);
  const [toolbar,setToolbar]=useState<HTMLDivElement|null>(null);
  const lastNote=useRef(new Map<string,Selection>());
  useEffect(()=>{
    if(!active)return;
    const controller=new AbortController();setError('');
    notesApi.catalogue(controller.signal).then(result=>{
      if(controller.signal.aborted)return;
      setCatalogue(result);
      if(initialProjectId&&!result.projects.some(project=>project.id===initialProjectId))setNotice('Ce carnet de projet est indisponible avec votre accès.');
      setSelection(value=>value.scope!==personal&&value.scope!==all&&!result.projects.some(project=>project.id===value.scope)
        ?{scope:personal,key:value.key+1}:value);
    }).catch(()=>{if(!controller.signal.aborted)setError('Impossible de charger les projets de vos notes.');});
    return()=>controller.abort();
  },[active,refresh,initialProjectId]);

  useEffect(()=>{
    const scope=initialProjectId??personal;
    if(initialProjectId&&catalogue&&!catalogue.projects.some(project=>project.id===scope)){
      setNotice('Ce carnet de projet est indisponible avec votre accès.');
      return;
    }
    if(initialProjectId)setProjectChoices(previous=>previous&&!previous.includes(scope)?[...previous,scope]:previous);
    setSelection(previous=>previous.scope===scope?previous:{scope,note:lastNote.current.get(scope),key:previous.key+1});
  },[initialProjectId]);

  const projects=catalogue?.projects??[];
  const displayed=projects.filter(project=>projectChoices?projectChoices.includes(project.id):project.has_notes||project.id===selection.scope);
  const tabs=[{id:all,name:'Toutes les notes',title:'Toutes les notes'},{id:personal,name:'Personnel',title:'Notes personnelles'},
    ...displayed.map(project=>({id:project.id,name:label(project),title:project.title}))];
  const selectedTab=tabs.some(tab=>tab.id===selection.scope)?selection.scope:null;
  const selectedProject=projects.find(project=>project.id===selection.scope);

  function open(scope:string){
    if(scope===selection.scope)return true;
    if(panel.current?.querySelector('[data-note-volatile="true"]')){
      setNotice('Attendez la fin de l’enregistrement ou réessayez de conserver le brouillon avant de changer d’onglet.');
      return false;
    }
    setNotice('');
    setSelection(previous=>({scope,note:lastNote.current.get(scope),key:previous.key+1}));
    return true;
  }

  function switchTab(event:KeyboardEvent<HTMLButtonElement>,index:number){
    const last=tabs.length-1;
    const next={ArrowLeft:(index+last)%tabs.length,ArrowRight:(index+1)%tabs.length,Home:0,End:last}[event.key];
    if(next===undefined)return;
    event.preventDefault();
    if(open(tabs[next].id))tablist.current?.querySelectorAll<HTMLButtonElement>('[role="tab"]')[next]?.focus();
  }

  function toggleProject(projectId:string,checked:boolean){
    if(panel.current?.querySelector('[data-note-volatile="true"]')){
      setNotice('Attendez la fin de l’opération en cours avant de modifier les carnets affichés.');return;
    }
    const ids=displayed.map(project=>project.id);
    setNotice('');
    if(!checked&&selection.scope===projectId)open(all);
    if(!checked&&lastNote.current.get(all)?.scope===projectId)lastNote.current.delete(all);
    setProjectChoices(checked?[...ids,projectId]:ids.filter(id=>id!==projectId));
  }

  function showCopy(note:NoteDetail){
    setCatalogue(value=>value&&({...value,projects:value.projects.map(project=>project.id===note.project_id?{...project,has_notes:true}:project)}));
    setProjectChoices(previous=>previous&&!previous.includes(note.project_id)?[...previous,note.project_id]:previous);
    setRefresh(value=>value+1);
    setSelection(previous=>({scope:note.project_id,note:{id:note.id,scope:note.project_id},key:previous.key+1}));
    setNotice('Note copiée dans le projet.');
    requestAnimationFrame(()=>tablist.current?.querySelector<HTMLButtonElement>('[aria-selected="true"]')?.focus());
  }

  const projectPicker=projects.length>0&&<details data-dismiss-outside className="notes-project-filter" onBlur={event=>{
    if(event.relatedTarget&&!event.currentTarget.contains(event.relatedTarget))event.currentTarget.open=false;
  }} onKeyDown={event=>{
    if(event.key!=='Escape'||!event.currentTarget.open)return;
    event.stopPropagation();event.currentTarget.open=false;event.currentTarget.querySelector<HTMLElement>('summary')?.focus();
  }}>
    <summary className="button secondary">Projets affichés</summary>
    <fieldset className="notes-project-options">
      <legend className="sr-only">Projets affichés</legend>
      {projects.map(project=><label key={project.id}>
        <input type="checkbox" checked={displayed.some(item=>item.id===project.id)} onChange={event=>toggleProject(project.id,event.target.checked)}/>
        <span>{project.code&&project.code!==project.title?`${project.code} — `:''}{project.title}</span>
      </label>)}
    </fieldset>
  </details>;

  return <>
    <header className="notes-workspace-header">
      <h1>Notes</h1>
      <div className="workspace-tabs notes-tabs" role="tablist" aria-label="Carnets" ref={tablist}>
        {tabs.map((tab,index)=><button type="button" key={tab.id} id={`notes-tab-${tab.id}`} role="tab"
          aria-selected={selectedTab===tab.id} aria-controls="notes-active-tab" aria-label={tab.id===personal?undefined:
            tab.name===tab.title?tab.title:`${tab.name} — ${tab.title}`} title={tab.title}
          tabIndex={selectedTab===tab.id||!selectedTab&&index===0?0:-1} onClick={()=>open(tab.id)} onKeyDown={event=>switchTab(event,index)}>
          {tab.name}
        </button>)}
      </div>
      <div className="notes-header-actions">
        <div ref={setToolbar} className="note-actions"/>
      </div>
    </header>
    {error&&<ErrorState message={error} retry={()=>setRefresh(value=>value+1)}/>}
    {notice&&<p role="status" className="workspace-notice">{notice}</p>}
    {!catalogue&&!error&&<LoadingState label="Chargement des projets…"/>}
    <div id="notes-active-tab" role={selectedTab?'tabpanel':undefined} aria-labelledby={selectedTab?`notes-tab-${selectedTab}`:undefined} ref={panel}>
      {selectedProject&&<div className="notes-project-context">
        <span>{selectedProject.title}</span>
        {onReturn&&<button type="button" className="workspace-text-button" onClick={onReturn}>Retour à la fiche projet</button>}
      </div>}
      {(!initialProjectId||catalogue)&&<ProjectNotesPanel key={selection.key} projectId={selection.scope} initialNote={selection.note?.id}
        initialNoteScope={selection.note?.scope} active={active} workspace toolbar={toolbar} listedProjects={displayed} folderPicker={projectPicker}
        onSelected={item=>{if(item)lastNote.current.set(selection.scope,item);else lastNote.current.delete(selection.scope);}}
        copyProjects={catalogue?.can_edit?projects:undefined} onCopied={showCopy}
        onNotesChanged={scope=>{if(scope!==personal)setRefresh(value=>value+1);}}/>}
    </div>
  </>;
}
