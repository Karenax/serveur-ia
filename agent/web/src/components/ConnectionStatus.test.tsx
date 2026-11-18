import {afterEach, beforeEach, expect, it, vi} from "vitest";
import {act,cleanup,render,screen,fireEvent} from "@testing-library/react";
import {request} from "../lib/http";
import {ConnectionStatus} from "./ConnectionStatus";
import {AiSettingsForm} from "./SettingsForms";
import {api} from "../lib/api";

vi.mock('../lib/http',()=>({request:vi.fn()}));
beforeEach(()=>{vi.spyOn(api,'session').mockResolvedValue({operator:{role:'owner',project_ids:null}});});
afterEach(()=>{cleanup();vi.useRealTimers();vi.restoreAllMocks();vi.clearAllMocks();});

it('affiche les trois états réels sans masquer une mémoire dégradée',async()=>{
  vi.mocked(request).mockResolvedValue({services:{llm:{state:'ok',detail:'Serveur accessible',model:'local'},embedding:{state:'error',detail:'Vecteur absent'},memory:{state:'warning',detail:'Indexations en échec'}},refreshing:false});
  render(<ConnectionStatus/>);
  await screen.findByText('Service indisponible');
  expect(screen.getByText('État du système').closest('details')).toHaveProperty('open',false);
  fireEvent.click(screen.getByText('État du système'));
  expect(screen.getByRole('status',{name:'Assistant IA : Accessible'})).toBeTruthy();
  expect(screen.getByRole('status',{name:'Recherche dans les documents : Indisponible'})).toBeTruthy();
  expect(screen.getByRole('status',{name:'Informations indexées : Dégradée'}).title).toContain('Indexations en échec');
  expect(screen.getByText(/Une réponse ou une indexation réussie se vérifie/)).toBeTruthy();
});

it('ne garde pas de témoin vert si le serveur de statut est inaccessible',async()=>{
  vi.mocked(request).mockRejectedValue(new Error('Hors ligne'));
  render(<ConnectionStatus/>);
  await screen.findByText('État non vérifié');
  fireEvent.click(screen.getByText('État du système'));
  expect(screen.getByRole('status',{name:'Assistant IA : Non vérifié'})).toBeTruthy();
  expect(screen.getByRole('status',{name:'Recherche dans les documents : Non vérifié'})).toBeTruthy();
  expect(screen.getByRole('status',{name:'Informations indexées : Non vérifié'})).toBeTruthy();
});

const connections=(state:string)=>({services:{llm:{state,detail:'LLM'},embedding:{state:'ok',detail:'Vecteur'},memory:{state:'warning',detail:'Mémoire'}},refreshing:false});

it('espace les lectures, ignore les retours rapides et confirme une panne après trois échecs',async()=>{
  vi.useFakeTimers();
  vi.mocked(request).mockResolvedValue(connections('ok'));
  render(<ConnectionStatus/>);
  await act(async()=>{});
  fireEvent.click(screen.getByText('État du système'));
  vi.mocked(request).mockRejectedValue(new Error('timeout'));
  await act(async()=>{
    document.dispatchEvent(new Event('visibilitychange'));
    await vi.advanceTimersByTimeAsync(59999);
  });
  expect(request).toHaveBeenCalledTimes(1);
  await act(async()=>{await vi.advanceTimersByTimeAsync(1);});
  expect(request).toHaveBeenCalledTimes(2);
  expect(screen.getByRole('status',{name:'Assistant IA : Accessible'})).toBeTruthy();
  await act(async()=>{await vi.advanceTimersByTimeAsync(60000);});
  expect(screen.getByRole('status',{name:'Assistant IA : Accessible'})).toBeTruthy();
  await act(async()=>{await vi.advanceTimersByTimeAsync(60000);});
  expect(screen.getByRole('status',{name:'Assistant IA : Non vérifié'})).toBeTruthy();
  vi.mocked(request).mockResolvedValue(connections('ok'));
  await act(async()=>{await vi.advanceTimersByTimeAsync(60000);});
  expect(screen.getByRole('status',{name:'Assistant IA : Accessible'})).toBeTruthy();
});

it.each([true,false])('actualise immédiatement le témoin après le test LLM : succès %s',async(ok)=>{
  vi.spyOn(api,'brainAiSettings').mockResolvedValue({enabled:true,provider:'ollama'});
  vi.spyOn(api,'brainAiTest').mockImplementation(async()=>{
    vi.mocked(request).mockResolvedValue(connections(ok?'ok':'error'));
    return {ok};
  });
  vi.mocked(request).mockResolvedValue(connections(ok?'error':'ok'));
  render(<><ConnectionStatus/><AiSettingsForm/></>);
  fireEvent.click(screen.getByText('État du système'));
  await screen.findByRole('status',{name:ok?'Assistant IA : Indisponible':'Assistant IA : Accessible'});
  fireEvent.click(await screen.findByRole('button',{name:'Tester'}));
  await screen.findByRole('status',{name:ok?'Assistant IA : Accessible':'Assistant IA : Indisponible'});
  expect(screen.getByRole('status',{name:'Informations indexées : Dégradée'})).toBeTruthy();
});

it('relit le statut si le test se termine pendant une requête précédente',async()=>{
  let finish!:(value:unknown)=>void;
  vi.mocked(request).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;}));
  vi.mocked(request).mockResolvedValue(connections('ok'));
  render(<ConnectionStatus/>);
  fireEvent.click(screen.getByText('État du système'));
  await act(async()=>{
    window.dispatchEvent(new Event('agent:connections-refresh'));
    finish(connections('error'));
  });
  await screen.findByRole('status',{name:'Assistant IA : Accessible'});
  expect(request).toHaveBeenCalledTimes(2);
});

it('suspend le statut masqué, ignore une réponse ancienne et relit au retour',async()=>{
  vi.useFakeTimers();
  const hidden=vi.spyOn(document,'hidden','get').mockReturnValue(false);
  let finish!:(value:unknown)=>void;
  vi.mocked(request).mockResolvedValueOnce(connections('ok'))
    .mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;}))
    .mockResolvedValue(connections('error'));
  render(<ConnectionStatus/>);await act(async()=>{});
  fireEvent.click(screen.getByText('État du système'));
  await act(async()=>{await vi.advanceTimersByTimeAsync(60000);});
  const signal=vi.mocked(request).mock.calls[1][1]!.signal as AbortSignal;
  hidden.mockReturnValue(true);act(()=>document.dispatchEvent(new Event('visibilitychange')));
  expect(signal.aborted).toBe(true);
  await act(async()=>{finish(connections('warning'));await vi.advanceTimersByTimeAsync(120000);});
  expect(request).toHaveBeenCalledTimes(2);
  expect(screen.getByRole('status',{name:'Assistant IA : Accessible'})).toBeTruthy();
  hidden.mockReturnValue(false);act(()=>document.dispatchEvent(new Event('visibilitychange')));await act(async()=>{});
  expect(request).toHaveBeenCalledTimes(3);
  expect(screen.getByRole('status',{name:'Assistant IA : Indisponible'})).toBeTruthy();
});

it('attend le retour de la fenêtre avant la première lecture du statut',async()=>{
  const hidden=vi.spyOn(document,'hidden','get').mockReturnValue(true);
  vi.mocked(request).mockResolvedValue(connections('ok'));
  render(<ConnectionStatus/>);await act(async()=>{});
  expect(request).not.toHaveBeenCalled();
  hidden.mockReturnValue(false);act(()=>document.dispatchEvent(new Event('visibilitychange')));
  expect(await screen.findByText('À vérifier')).toBeTruthy();
  expect(request).toHaveBeenCalledTimes(1);
});

it('regroupe le suivi des mails et garde les erreurs visibles dans le témoin unique',async()=>{
  const open=vi.fn();
  const service={state:'ok',detail:'Accessible'};
  const step={state:'idle',detail:'Au repos',processed:0,total:0};
  vi.mocked(request).mockImplementation(async(url)=>String(url).includes('mail-activity')?{
    source:'thunderbird',transfer:step,analysis:{...step,state:'failed',detail:'Deux mails à reprendre'},
    indexing:{...step,processed:42,total:42,detail:'42 indexés'},events:[{key:'analysis',text:'Analyse à reprendre',state:'failed'}],checked_at:'2026-11-04T10:00:00Z',
  }:{services:{llm:service,embedding:service,memory:service},refreshing:false});
  render(<ConnectionStatus onOpenJobs={open}/>);
  await screen.findByText('Mails à reprendre');
  const popup=screen.getByText('État du système').closest('details')!;
  expect(popup.open).toBe(false);
  fireEvent.click(screen.getByText('État du système'));
  const mails=screen.getByRole('region',{name:'Activité des mails'});
  expect(popup.contains(mails)).toBe(true);
  expect(screen.getByRole('alert').textContent).toBe('Deux mails à reprendre');
  fireEvent.click(screen.getByText('Détails'));
  expect(screen.getByText('42 indexés')).toBeTruthy();
  expect(screen.getByRole('list',{name:'Dernières activités des mails'})).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'Voir les traitements →'}));
  expect(open).toHaveBeenCalledOnce();
  expect(popup.open).toBe(false);
});
