import {useEffect, useRef, useState, type KeyboardEvent} from 'react';
import {notesApi, personalNotesScope, type NoteDetail, type NotesProject} from '../lib/projectNotes';
import {ProjectNotesPanel} from './ProjectNotesPanel';
import {ErrorState, LoadingState} from './Ui';

const personal=personalNotesScope;
const label=(project:NotesProject)=>project.code||project.title;

export function NotesWorkspace({active}:{active:boolean}){
  const [catalogue,setCatalogue]=useState<{projects:NotesProject[];can_edit:boolean}>();
  const [selection,setSelection]=useState({scope:personal,note:undefined as string|undefined,key:0});
  const [chooseProject,setChooseProject]=useState(false),[destination,setDestination]=useState('');
  const [refresh,setRefresh]=useState(0),[error,setError]=useState(''),[notice,setNotice]=useState('');
  const panel=useRef<HTMLDivElement>(null),tablist=useRef<HTMLDivElement>(null);
  useEffect(()=>{
    if(!active)return;
    const controller=new AbortController();setError('');
    notesApi.catalogue(controller.signal).then(result=>{
      if(controller.signal.aborted)return;
      setCatalogue(result);
      setSelection(value=>value.scope!==personal&&!result.projects.some(project=>project.id===value.scope)
        ?{scope:personal,note:undefined,key:value.key+1}:value);
    }).catch(()=>{if(!controller.signal.aborted)setError('Impossible de charger les projets de vos notes.');});
    return()=>controller.abort();
  },[active,refresh]);

  const projects=catalogue?.projects??[];
  const tabs=[{id:personal,name:'Personnel',title:'Notes personnelles'},
    ...projects.filter(project=>project.has_notes).map(project=>({id:project.id,name:label(project),title:project.title}))];
  const selectedTab=tabs.some(tab=>tab.id===selection.scope)?selection.scope:null;
  const draftProject=selectedTab?undefined:projects.find(project=>project.id===selection.scope);

  function open(scope:string,note?:string){
    if(!note&&scope===selection.scope)return true;
    if(panel.current?.querySelector('[data-note-volatile="true"]')){
      setNotice('Attendez la fin de l’enregistrement ou réessayez de conserver le brouillon avant de changer d’onglet.');
      return false;
    }
    setNotice('');setChooseProject(false);
    setSelection(previous=>({scope,note,key:previous.key+1}));
    return true;
  }

  function switchTab(event:KeyboardEvent<HTMLButtonElement>,index:number){
    const last=tabs.length-1;
    const next={ArrowLeft:(index+last)%tabs.length,ArrowRight:(index+1)%tabs.length,Home:0,End:last}[event.key];
    if(next===undefined)return;
    event.preventDefault();
    if(open(tabs[next].id))tablist.current?.querySelectorAll<HTMLButtonElement>('[role="tab"]')[next]?.focus();
  }

  function showProjectTab(projectId:string){
    setCatalogue(value=>value&&({...value,projects:value.projects.map(project=>project.id===projectId?{...project,has_notes:true}:project)}));
    setRefresh(value=>value+1);
  }

  function showCopy(note:NoteDetail){
    showProjectTab(note.project_id);
    setSelection(previous=>({scope:note.project_id,note:note.id,key:previous.key+1}));
    setNotice('Note copiée dans le projet.');
    requestAnimationFrame(()=>tablist.current?.querySelector<HTMLButtonElement>('[aria-selected="true"]')?.focus());
  }

  return <>
    <div className="workspace-page-header notes-page-header">
      <h1>Notes</h1>
      {catalogue?.can_edit&&projects.length>0&&<button type="button" className="button secondary" aria-expanded={chooseProject}
        aria-controls="notes-choose-project" onClick={()=>setChooseProject(value=>!value)}>Nouvelle note de projet</button>}
    </div>
    {chooseProject&&<form id="notes-choose-project" className="note-project-picker note-project-start" onSubmit={event=>{
      event.preventDefault();if(destination&&open(destination,'new'))setDestination('');
    }}>
      <label>Projet<select className="input" value={destination} onChange={event=>setDestination(event.target.value)}>
        <option value="">Choisir un projet</option>{projects.map(project=><option value={project.id} key={project.id}>
          {project.code?`${project.code} — `:''}{project.title}</option>)}
      </select></label>
      <button type="submit" className="button" disabled={!destination}>Commencer la note</button>
    </form>}
    {error&&<ErrorState message={error} retry={()=>setRefresh(value=>value+1)}/>}
    {notice&&<p role="status" className="workspace-notice">{notice}</p>}
    <div className="workspace-tabs notes-tabs" role="tablist" aria-label="Carnets" ref={tablist}>
      {tabs.map((tab,index)=><button type="button" key={tab.id} id={`notes-tab-${tab.id}`} role="tab"
        aria-selected={selectedTab===tab.id} aria-controls="notes-active-tab" aria-label={tab.id===personal?undefined:
          tab.name===tab.title?tab.title:`${tab.name} — ${tab.title}`} title={tab.title}
        tabIndex={selectedTab===tab.id||!selectedTab&&index===0?0:-1} onClick={()=>open(tab.id)} onKeyDown={event=>switchTab(event,index)}>
        {tab.name}
      </button>)}
    </div>
    {!catalogue&&!error&&<LoadingState label="Chargement des projets…"/>}
    <div id="notes-active-tab" role={selectedTab?'tabpanel':undefined} aria-labelledby={selectedTab?`notes-tab-${selectedTab}`:undefined} ref={panel}>
      {draftProject&&<h2 className="notes-draft-title">Nouvelle note · {label(draftProject)}</h2>}
      <ProjectNotesPanel key={selection.key} projectId={selection.scope} initialNote={selection.note} active={active} workspace
        copyProjects={catalogue?.can_edit?projects:undefined} onCopied={showCopy}
        onNotesChanged={()=>{if(selection.scope!==personal)showProjectTab(selection.scope);}}/>
    </div>
  </>;
}
