import {useState} from 'react';
import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen} from '@testing-library/react';
import {ProjectDocumentViews} from '../App';

vi.mock('./ProjectNotesPanel',()=>{throw new Error('Premier chargement indisponible');});
vi.mock('./ProjectNotesPanel?kiara-retry=1',()=>({ProjectNotesPanel:()=> <label>Note fictive<input defaultValue=""/></label>}));
vi.mock('./ProjectDocumentsPanel',()=>({ProjectDocumentsPanel:()=> <label>Préparation fictive<input defaultValue=""/></label>}));
vi.mock('./ProjectDeliverablesPanel',()=>({ProjectDeliverablesPanel:()=>null}));
afterEach(()=>{cleanup();vi.restoreAllMocks();});

it('reprend le chargement des notes sans perdre la préparation ni le brouillon ouvert',async()=>{
  vi.spyOn(console,'error').mockImplementation(()=>{});
  function Fixture(){
    const [view,setView]=useState<'prepare'|'notes'|'deliverables'|'links'>('prepare');
    return <ProjectDocumentViews projectId="p1" active view={view} setView={setView} onSaved={()=>{}} onFocusHandled={()=>{}}/>;
  }
  render(<Fixture/>);
  fireEvent.change(await screen.findByLabelText('Préparation fictive'),{target:{value:'Préparation conservée'}});
  fireEvent.click(screen.getByRole('tab',{name:'Notes'}));
  expect(await screen.findByText(/Le chargement de cette rubrique a échoué/)).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'Réessayer'}));
  fireEvent.change(await screen.findByLabelText('Note fictive'),{target:{value:'Note non enregistrée'}});
  fireEvent.click(screen.getByRole('button',{name:'Préparer un document'}));
  expect(screen.getByLabelText('Préparation fictive')).toHaveProperty('value','Préparation conservée');
  fireEvent.click(screen.getByRole('tab',{name:'Notes'}));
  expect(screen.getByLabelText('Note fictive')).toHaveProperty('value','Note non enregistrée');
});
