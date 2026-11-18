import {useState} from 'react';
import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen} from '@testing-library/react';
import {ProjectDocumentViews} from '../App';

vi.mock('./ProjectDeliverablesPanel',()=>{throw new Error('Premier chargement indisponible');});
vi.mock('./ProjectDeliverablesPanel?kiara-retry=1',()=>({ProjectDeliverablesPanel:()=> <label>Livrable fictif<input defaultValue=""/></label>}));
vi.mock('./ProjectNotesPanel',()=>({ProjectNotesPanel:()=> <label>Note fictive<input defaultValue=""/></label>}));
afterEach(()=>{cleanup();vi.restoreAllMocks();});

it('reprend les livrables sans perdre une note ni une saisie déjà ouverte',async()=>{
  vi.spyOn(console,'error').mockImplementation(()=>{});
  function Fixture(){
    const [view,setView]=useState<'prepare'|'notes'|'deliverables'|'links'>('notes');
    return <ProjectDocumentViews projectId="p1" active view={view} setView={setView} onSaved={()=>{}} onFocusHandled={()=>{}}/>;
  }
  render(<Fixture/>);
  fireEvent.change(await screen.findByLabelText('Note fictive'),{target:{value:'Note conservée'}});
  fireEvent.click(screen.getByRole('tab',{name:'À remettre'}));
  expect(await screen.findByText(/Le chargement de cette rubrique a échoué/)).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'Réessayer'}));
  fireEvent.change(await screen.findByLabelText('Livrable fictif'),{target:{value:'Livrable non enregistré'}});
  fireEvent.click(screen.getByRole('tab',{name:'Notes'}));
  expect(screen.getByLabelText('Note fictive')).toHaveProperty('value','Note conservée');
  fireEvent.click(screen.getByRole('tab',{name:'À remettre'}));
  expect(screen.getByLabelText('Livrable fictif')).toHaveProperty('value','Livrable non enregistré');
});
