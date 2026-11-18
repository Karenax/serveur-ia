import {useState, type ComponentType} from 'react';
import {cleanup, fireEvent, render, screen} from '@testing-library/react';
import {afterEach, expect, it, vi} from 'vitest';
import {api} from './lib/api';
import {WorkspaceViewBoundary} from './components/WorkspaceViewBoundary';
import {App} from './AppEntry';

vi.mock('./App', () => {throw new Error('Module initial indisponible');});
vi.mock('./App?kiara-retry=1', () => ({
  ProjectWindow: () => <p>Projet retrouvé</p>,
  MailApp: () => <p>Mails retrouvés</p>,
  ScanImport: () => null,
  SagePanel: () => null,
}));
vi.mock('./components/WorkspaceShell', () => ({
  WorkspaceShell: ({ProjectPanel, MailPanel}: {ProjectPanel:ComponentType<any>; MailPanel:ComponentType<any>}) => {
    const [mail, setMail] = useState(false);
    return <>
      <button onClick={() => setMail(true)}>Ouvrir les mails</button>
      <label>Brouillon voisin<input defaultValue="Texte conservé" /></label>
      <div hidden={mail}><WorkspaceViewBoundary><ProjectPanel projectId="p1" /></WorkspaceViewBoundary></div>
      {mail && <WorkspaceViewBoundary><MailPanel /></WorkspaceViewBoundary>}
    </>;
  },
}));

afterEach(() => {cleanup(); vi.restoreAllMocks();});

it('réutilise le module rétabli pour une autre vue sans toucher au brouillon voisin', async () => {
  vi.spyOn(console, 'error').mockImplementation(() => {});
  vi.spyOn(api, 'session').mockResolvedValue({operator:{role:'owner',project_ids:null}} as never);
  vi.spyOn(api, 'portfolio').mockResolvedValue([]);
  render(<App />);
  expect(await screen.findByText(/Le chargement de cette rubrique a échoué/)).toBeTruthy();
  fireEvent.change(screen.getByLabelText('Brouillon voisin'), {target:{value:'À conserver'}});
  fireEvent.click(screen.getByRole('button', {name:'Réessayer'}));
  expect(await screen.findByText('Projet retrouvé')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', {name:'Ouvrir les mails'}));
  expect(await screen.findByText('Mails retrouvés')).toBeTruthy();
  expect((screen.getByLabelText('Brouillon voisin') as HTMLInputElement).value).toBe('À conserver');
});
