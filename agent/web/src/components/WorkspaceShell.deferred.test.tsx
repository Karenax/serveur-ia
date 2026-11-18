import {useState} from 'react';
import {afterEach, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen} from '@testing-library/react';
import {WorkspaceShell, type ProjectWorkspaceProps} from './WorkspaceShell';

vi.mock('./WorkspaceViews', () => {throw new Error('Module initial indisponible');});
vi.mock('./WorkspaceViews?kiara-retry=1', () => ({
  GlobalMeetingsView: () => <p>Réunions retrouvées</p>,
  GlobalJobsView: () => <p>Traitements retrouvés</p>,
  GlobalKnowledgeView: () => <p>Informations retrouvées</p>,
}));
vi.mock('./ActionDashboard', () => ({ActionDashboard: () => null}));
vi.mock('./ConnectionStatus', () => ({ConnectionStatus: () => null}));
vi.mock('./MeetingCaptureBar', () => ({MeetingCaptureBar: () => null}));
vi.mock('./NativeMeetingCapture', () => ({NativeCaptureBar: () => null}));

afterEach(() => {cleanup(); vi.restoreAllMocks();});

it('réessaie les vues globales sans perdre le brouillon projet et réutilise le module rétabli', async () => {
  vi.spyOn(console, 'error').mockImplementation(() => {});
  window.history.replaceState(null, '', '/app/projects/p1/cdc');
  function Project(_props:ProjectWorkspaceProps) {
    const [draft,setDraft] = useState('');
    return <label>Brouillon projet<input value={draft} onChange={event=>setDraft(event.target.value)}/></label>;
  }
  render(<WorkspaceShell rows={[]} reload={async()=>undefined} ProjectPanel={Project}
    MailPanel={()=>null} CreatePanel={()=>null} SagePanel={()=>null}/>);
  fireEvent.change(screen.getByLabelText('Brouillon projet'), {target:{value:'À conserver'}});
  fireEvent.click(screen.getByRole('link', {name:'Réunions'}));
  expect(await screen.findByText(/Le chargement de cette rubrique a échoué/)).toBeTruthy();
  fireEvent.click(screen.getByRole('button', {name:'Réessayer'}));
  expect(await screen.findByText('Réunions retrouvées')).toBeTruthy();
  fireEvent.click(screen.getByRole('link', {name:'Activité'}));
  expect(await screen.findByText('Traitements retrouvés')).toBeTruthy();
  window.history.pushState(null,'','/app/projects/p1/cdc');
  fireEvent.popState(window);
  expect((screen.getByLabelText('Brouillon projet') as HTMLInputElement).value).toBe('À conserver');
});
