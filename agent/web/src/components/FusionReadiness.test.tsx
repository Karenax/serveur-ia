import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {FusionReadiness} from './FusionReadiness';
import {fusionInsights,type FusionReadinessState} from '../lib/fusionInsights';
import {meetingCapture} from '../lib/meetingCapture';
afterEach(()=>{cleanup();vi.restoreAllMocks();});
const initial:FusionReadinessState={mode:'network',capture:{durable:true,installed:true,ready:true,physical_test_passed:false,requires_explicit_start:true},
  transcription:{batch:{ready:true},direct:{installed:true,ready:true,loaded:false}},embeddings:{network:{detail:'Connexion distincte'}},
  generation:{configured:true,placement:'network',model:'Modèle réseau',inventory:null,test:null},
  resources:{available_ram_bytes:1,total_ram_bytes:1,free_disk_bytes:1},offline:{qualified:false,detail:'Chaîne hors ligne à vérifier.'}};

it('lit les diagnostics sans lancer de capture, d’inventaire ou de génération',async()=>{
  const read=vi.spyOn(fusionInsights,'readiness').mockResolvedValue(initial),probe=vi.spyOn(fusionInsights,'probeReadiness'),test=vi.spyOn(fusionInsights,'testGeneration'),capture=vi.spyOn(meetingCapture,'start');
  render(<FusionReadiness/>);await screen.findByText('Modèle réseau');
  expect(read).toHaveBeenCalledOnce();expect(probe).not.toHaveBeenCalled();expect(test).not.toHaveBeenCalled();expect(capture).not.toHaveBeenCalled();
  expect(screen.getByText('Installé : Non vérifié · Chargé : Non vérifié')).toBeTruthy();
  expect(screen.getByRole('button',{name:'Tester une réponse'})).toHaveProperty('disabled',false);
});

it('un modèle installé et déchargé ne devient pas une génération testée',async()=>{
  vi.spyOn(fusionInsights,'readiness').mockResolvedValue(initial);
  vi.spyOn(fusionInsights,'probeReadiness').mockResolvedValue({...initial,generation:{...initial.generation,inventory:{reachable:true,installed:true,loaded:false,checked_at:'2026-10-16T02:00:00Z',detail:'Inventaire reçu'}}});
  const test=vi.spyOn(fusionInsights,'testGeneration');render(<FusionReadiness/>);
  fireEvent.click(await screen.findByRole('button',{name:'Vérifier les modèles'}));
  await screen.findByText('Installé : oui · Chargé : non');
  expect(screen.getByText('Aucune réponse réelle testée pour cette configuration.')).toBeTruthy();expect(test).not.toHaveBeenCalled();
});

it('annonce le travail puis affiche le résultat réel uniquement après clic',async()=>{
  vi.spyOn(fusionInsights,'readiness').mockResolvedValue(initial);
  let finish!:(value:FusionReadinessState)=>void;
  vi.spyOn(fusionInsights,'testGeneration').mockReturnValue(new Promise(resolve=>{finish=resolve;}));
  render(<FusionReadiness/>);await screen.findByText('Modèle réseau');
  fireEvent.click(screen.getByRole('button',{name:'Tester une réponse'}));
  expect(screen.getByText('Test de réponse en cours…')).toBeTruthy();
  expect(screen.getByRole('button',{name:'Vérifier les modèles'})).toHaveProperty('disabled',true);
  finish({...initial,generation:{...initial.generation,test:{ok:true,reply_received:true,checked_at:'2026-10-16T02:00:00Z',elapsed_seconds:1.2,detail:'Réponse réelle reçue'}}});
  await screen.findByText('Réponse testée · Serveur du réseau');
  expect(screen.queryByText('Test de réponse en cours…')).toBeNull();
});

it('un échec du contrôle conserve les étapes installées et permet de reprendre',async()=>{
  vi.spyOn(fusionInsights,'readiness').mockResolvedValue(initial);
  vi.spyOn(fusionInsights,'probeReadiness').mockRejectedValue(new Error('Serveur momentanément indisponible'));
  render(<FusionReadiness/>);await screen.findByText('Modèle réseau');
  fireEvent.click(screen.getByRole('button',{name:'Vérifier les modèles'}));
  expect((await screen.findByRole('alert')).textContent).toContain('Serveur momentanément indisponible');
  expect(screen.getByText('Index EG2')).toBeTruthy();
  expect(screen.getByRole('button',{name:'Vérifier les modèles'})).toHaveProperty('disabled',false);
});

it('une ancienne lecture ne remplace pas un contrôle plus récent',async()=>{
  const read=vi.spyOn(fusionInsights,'readiness').mockResolvedValueOnce(initial);
  let stale!:(value:FusionReadinessState)=>void;read.mockImplementationOnce(()=>new Promise(resolve=>{stale=resolve;}));
  vi.spyOn(fusionInsights,'probeReadiness').mockResolvedValue({...initial,generation:{...initial.generation,model:'Modèle courant'}});
  const view=render(<FusionReadiness/>);await screen.findByText('Modèle réseau');
  view.rerender(<FusionReadiness refreshKey={1}/>);
  await waitFor(()=>expect(read).toHaveBeenCalledTimes(2));
  fireEvent.click(screen.getByRole('button',{name:'Vérifier les modèles'}));await screen.findByText('Modèle courant');
  stale(initial);await Promise.resolve();expect(screen.queryByText('Modèle réseau')).toBeNull();
});
