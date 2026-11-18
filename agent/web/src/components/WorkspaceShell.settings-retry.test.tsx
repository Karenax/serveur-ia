import {afterEach, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen} from '@testing-library/react';
import {WorkspaceShell} from './WorkspaceShell';

vi.mock('./SettingsForms', () => ({
  AiSettingsForm: () => <label>Réglage voisin<input defaultValue=""/></label>,
  MailSettingsForm: () => null,
  MemorySettingsForm: () => null,
}));
vi.mock('./DocumentSettings', () => {throw new Error('Module documentaire indisponible');});
vi.mock('./DocumentSettings?kiara-retry=1', () => ({
  DocumentSettings: () => <label>Réglage documentaire<input defaultValue=""/></label>,
}));
vi.mock('./ActionDashboard', () => ({ActionDashboard: () => null}));
vi.mock('./ConnectionStatus', () => ({ConnectionStatus: () => null}));
vi.mock('./MeetingCaptureBar', () => ({MeetingCaptureBar: () => null}));
vi.mock('./NativeMeetingCapture', () => ({NativeCaptureBar: () => null}));

afterEach(() => {cleanup(); vi.restoreAllMocks();});

it('réessaie les documents sans perdre les réglages voisins ni le formulaire rétabli', async () => {
  vi.spyOn(console, 'error').mockImplementation(() => {});
  window.history.replaceState(null, '', '/app/settings');
  render(<WorkspaceShell rows={[]} reload={async()=>undefined} ProjectPanel={()=>null}
    MailPanel={()=>null} CreatePanel={()=>null} SagePanel={()=>null}/>);
  fireEvent.change(await screen.findByLabelText('Réglage voisin'),{target:{value:'Brouillon général'}});
  fireEvent.click(screen.getByRole('button',{name:'Modèles de documents'}));
  expect(await screen.findByText(/Le chargement de cette rubrique a échoué/)).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'Réessayer'}));
  fireEvent.change(await screen.findByLabelText('Réglage documentaire'),{target:{value:'Brouillon documentaire'}});
  fireEvent.click(screen.getByRole('button',{name:'Général'}));
  expect((screen.getByLabelText('Réglage voisin') as HTMLInputElement).value).toBe('Brouillon général');
  fireEvent.click(screen.getByRole('button',{name:'Modèles de documents'}));
  expect((screen.getByLabelText('Réglage documentaire') as HTMLInputElement).value).toBe('Brouillon documentaire');
});
