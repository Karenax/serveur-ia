import {afterEach,beforeEach,it,expect,vi} from "vitest";
import {act,cleanup,render,screen,fireEvent,waitFor} from "@testing-library/react";
import {MailActivity,type MailActivitySnapshot} from "./MailActivity";
import {request} from "../lib/http";
import {api} from "../lib/api";
vi.mock("../lib/http",()=>({request:vi.fn()}));
beforeEach(()=>{vi.spyOn(api,'session').mockResolvedValue({operator:{role:'owner',project_ids:null}});});
afterEach(()=>{cleanup();vi.useRealTimers();vi.restoreAllMocks();vi.resetAllMocks();});
function data():MailActivitySnapshot{return {source:"thunderbird",checked_at:"2026-10-05T10:00:00Z",
  transfer:{state:"running",processed:12,total:80,detail:"12 / 80 mails · Transfert en cours"},
  analysis:{state:"queued",processed:0,total:8,detail:"8 mails à analyser"},
  indexing:{state:"idle",processed:20,total:20,detail:"20 indexés · 0 en attente"},
  events:[{key:"Synchro",state:"running",text:"Synchro : 12 / 80 mails"}]};}
it("ne consulte pas l’activité globale lorsque l’accès est limité à des projets",async()=>{
  vi.mocked(api.session).mockResolvedValue({operator:{role:'reader',project_ids:['p1']}});
  const state=vi.fn();render(<MailActivity onOpen={()=>{}} onStateChange={state}/>);
  await waitFor(()=>expect(state).toHaveBeenLastCalledWith('unavailable'));
  expect(request).not.toHaveBeenCalled();
  expect(screen.queryByRole('region',{name:'Activité des mails'})).toBeNull();
});
it("reprend le suivi si le périmètre devient complet",async()=>{
  vi.useFakeTimers();
  vi.mocked(api.session).mockResolvedValue({operator:{role:'reader',project_ids:['p1']}});
  vi.mocked(request).mockResolvedValue(data());
  render(<MailActivity onOpen={()=>{}}/>);
  await act(async()=>{});
  expect(request).not.toHaveBeenCalled();
  vi.mocked(api.session).mockResolvedValue({operator:{role:'owner',project_ids:null}});
  await act(async()=>{await vi.advanceTimersByTimeAsync(30000);});
  expect(request).toHaveBeenCalledTimes(1);
  expect(screen.getByRole('region',{name:'Activité des mails'})).toBeTruthy();
});
it("affiche le transfert réel, son compteur, le journal et l’accès aux traitements",async()=>{
  vi.mocked(request).mockResolvedValue(data());const open=vi.fn();
  render(<MailActivity onOpen={open}/>);
  const bar=await screen.findByRole("progressbar",{name:"Traitement des mails en cours"});
  expect((bar as HTMLProgressElement).value).toBe(12);
  expect((bar as HTMLProgressElement).max).toBe(80);
  expect(screen.getByRole("region").classList.contains("is-active")).toBe(true);
  expect(screen.getByText("Détails").closest("details")).toHaveProperty("open",false);
  fireEvent.click(screen.getByText("Détails"));
  expect(screen.getByText("Synchro : 12 / 80 mails")).toBeTruthy();
  fireEvent.click(screen.getByRole("button",{name:"Voir les traitements →"}));expect(open).toHaveBeenCalledOnce();
});
it("ne fait pas tourner le témoin pour une file en attente ou un ancien transfert déconnecté",async()=>{
  const value=data();value.transfer.state="offline";value.analysis.state="queued";
  vi.mocked(request).mockResolvedValue(value);render(<MailActivity onOpen={()=>{}}/>);
  await waitFor(()=>expect(screen.getByRole("status").textContent).toBe("En attente"));
  expect(screen.queryByRole("progressbar",{name:"Traitement des mails en cours"})).toBeNull();
  expect(screen.getByRole("region").classList.contains("is-active")).toBe(false);
});
it("limite les lectures et tolère deux erreurs avant de signaler une déconnexion",async()=>{
  vi.useFakeTimers();
  vi.mocked(request).mockResolvedValue(data());render(<MailActivity onOpen={()=>{}}/>);
  await act(async()=>{});
  fireEvent.click(screen.getByText("Détails"));
  await act(async()=>{
    window.dispatchEvent(new Event("focus"));
    document.dispatchEvent(new Event("visibilitychange"));
    await vi.advanceTimersByTimeAsync(29999);
  });
  expect(request).toHaveBeenCalledTimes(1);
  await act(async()=>{await vi.advanceTimersByTimeAsync(1);});
  expect(request).toHaveBeenCalledTimes(2);
  expect(screen.getAllByText("Synchro : 12 / 80 mails")).toHaveLength(1);
  vi.mocked(request).mockRejectedValue(new Error("offline"));
  await act(async()=>{await vi.advanceTimersByTimeAsync(60000);});
  expect(screen.queryByText("État indisponible · reconnexion…")).toBeNull();
  await act(async()=>{await vi.advanceTimersByTimeAsync(30000);});
  expect(screen.getByText("État indisponible · reconnexion…")).toBeTruthy();
  expect(screen.getByRole("region").classList.contains("is-active")).toBe(false);
  vi.mocked(request).mockResolvedValue(data());
  await act(async()=>{await vi.advanceTimersByTimeAsync(30000);});
  expect(screen.queryByText("État indisponible · reconnexion…")).toBeNull();
  expect(screen.getByText("Connexion au serveur rétablie")).toBeTruthy();
  expect(screen.getAllByText("Synchro : 12 / 80 mails")).toHaveLength(1);
});

it("conserve le dernier état valide lorsqu’une réponse est incomplète puis reprend",async()=>{
  vi.useFakeTimers();
  vi.mocked(request).mockResolvedValueOnce(data()).mockResolvedValueOnce({events:[]}).mockResolvedValue(data());
  render(<MailActivity onOpen={()=>{}}/>);
  await act(async()=>{});
  expect(screen.getByRole("progressbar",{name:"Traitement des mails en cours"})).toBeTruthy();
  await act(async()=>{await vi.advanceTimersByTimeAsync(30000);});
  expect(screen.getByRole("progressbar",{name:"Traitement des mails en cours"})).toBeTruthy();
  expect(screen.queryByText("État indisponible · reconnexion…")).toBeNull();
  await act(async()=>{await vi.advanceTimersByTimeAsync(30000);});
  expect(request).toHaveBeenCalledTimes(3);
  expect(screen.getByRole("progressbar",{name:"Traitement des mails en cours"})).toBeTruthy();
});

it("suspend l'activité masquée, ignore la réponse tardive et reprend au retour",async()=>{
  vi.useFakeTimers();
  const hidden=vi.spyOn(document,'hidden','get').mockReturnValue(false);
  let finish!:(value:unknown)=>void;
  const latest=data();latest.transfer.processed=42;latest.transfer.detail='42 mails en cours';
  vi.mocked(request).mockResolvedValueOnce(data()).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;})).mockResolvedValue(latest);
  render(<MailActivity onOpen={()=>{}}/>);await act(async()=>{});
  await act(async()=>{await vi.advanceTimersByTimeAsync(30000);});
  const signal=vi.mocked(request).mock.calls[1][1]!.signal as AbortSignal;
  hidden.mockReturnValue(true);act(()=>document.dispatchEvent(new Event('visibilitychange')));
  expect(signal.aborted).toBe(true);
  const stale=data();stale.transfer.state='failed';stale.transfer.detail='Ancienne erreur';
  await act(async()=>{finish(stale);await vi.advanceTimersByTimeAsync(60000);});
  expect(request).toHaveBeenCalledTimes(2);
  expect(screen.queryByText('Ancienne erreur')).toBeNull();
  expect((screen.getByRole('progressbar',{name:'Traitement des mails en cours'}) as HTMLProgressElement).value).toBe(12);
  hidden.mockReturnValue(false);act(()=>document.dispatchEvent(new Event('visibilitychange')));await act(async()=>{});
  expect(request).toHaveBeenCalledTimes(3);
  expect((screen.getByRole('progressbar',{name:'Traitement des mails en cours'}) as HTMLProgressElement).value).toBe(42);
});

it("ne lit pas l'activité après une session reçue pendant le masquage",async()=>{
  const hidden=vi.spyOn(document,'hidden','get').mockReturnValue(false);
  let finish!:(value:Awaited<ReturnType<typeof api.session>>)=>void;
  vi.mocked(api.session).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;}))
    .mockResolvedValue({operator:{role:'owner',project_ids:null}});
  vi.mocked(request).mockResolvedValue(data());render(<MailActivity onOpen={()=>{}}/>);
  const signal=vi.mocked(api.session).mock.calls[0][0]!;
  hidden.mockReturnValue(true);act(()=>document.dispatchEvent(new Event('visibilitychange')));
  expect(signal.aborted).toBe(true);
  await act(async()=>{finish({operator:{role:'owner',project_ids:null}});});
  expect(request).not.toHaveBeenCalled();
  hidden.mockReturnValue(false);act(()=>document.dispatchEvent(new Event('visibilitychange')));
  expect(await screen.findByRole('progressbar',{name:'Traitement des mails en cours'})).toBeTruthy();
  expect(request).toHaveBeenCalledTimes(1);
});

it("garde un échec visible quand les détails sont repliés",async()=>{
  const value=data();value.transfer.state="idle";value.analysis.state="failed";value.analysis.detail="Le serveur IA a refusé ce mail";
  vi.mocked(request).mockResolvedValue(value);render(<MailActivity onOpen={()=>{}}/>);
  expect(await screen.findByRole("alert")).toHaveProperty("textContent","Le serveur IA a refusé ce mail");
  expect(screen.getByText("Détails").closest("details")).toHaveProperty("open",false);
});
