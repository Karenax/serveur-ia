import { afterEach, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { api, type PortfolioRow } from "../lib/api";
import { AssistantPanel } from "./AssistantPanel";
import {notesApi,type NoteVersion} from '../lib/projectNotes';
import * as assistantStreaming from '../lib/assistantStream';
import * as http from '../lib/http';
import type { AssistantMessage } from '../hooks/useAssistantHistory';
afterEach(()=>{cleanup();vi.restoreAllMocks();});

it('ouvre la version ERP citée sans la remplacer par un téléchargement brut absent',async()=>{
  const load=vi.spyOn(notesApi,'version').mockResolvedValue({id:'v2',project_id:'erp',note_id:'note',revision:2,title:'Version exacte',actor_id:'human',created_at:'2026-10-11T15:30:00Z',operation:'save',
    value:{title:'Version exacte',content:{version:1,blocks:[{type:'paragraph',align:'left',runs:[{text:'Devis non validé historique.',marks:[],href:null,color:null}]}]}},attachment_bindings:{}} as NoteVersion);
  vi.spyOn(api,'brainProjects').mockResolvedValue([]);
  vi.spyOn(api,'brainChat').mockResolvedValue({answer:'Réserve humaine [V1].',citations:[{reference:'V1',project_code:'QA',level:'validated',
    source_id:'source',source_url:'/api/v1/projects/erp/notes/note/versions/v2',excerpt:'Réserve humaine',locator:{note_version_id:'v2',block_index:0}}]});
  render(<AssistantPanel onClose={vi.fn()}/>);
  fireEvent.change(screen.getByLabelText('Question à l’assistant'),{target:{value:'Quelle réserve ?'}});
  fireEvent.click(screen.getByRole('button',{name:'Envoyer la question'}));
  fireEvent.click(await screen.findByRole('button',{name:'Voir la source V1'}));
  expect(screen.getByRole('link',{name:'Ouvrir la version citée'}).getAttribute('href')).toBe('/api/v1/projects/erp/notes/note/versions/v2');
  expect(screen.queryByRole('link',{name:'Télécharger la source originale'})).toBeNull();
  expect(screen.getByText(/Bloc: 1/)).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'Lire la version citée'}));await screen.findByText('Version exacte · version 2');
  expect(load).toHaveBeenCalledWith('erp','note','v2',expect.any(AbortSignal));
});

it("affiche le secours mémoire comme statut et permet de consulter la preuve depuis la réponse", async () => {
  vi.spyOn(api, "brainProjects").mockResolvedValue([{ id: "p1", code: "AIRB", name: "Projet" }]);
  const chat = vi.spyOn(api, "brainChat").mockResolvedValue({
    answer: "**Objectif :** Installer les sangles [P1].",
    citations: [{ reference: "P1", project_code: "AIRB", level: "proposed", excerpt: "Prévoir de nouvelles sangles." }],
    warnings: ["AIRB : DatasetNotFoundError ; recherche textuelle des sources classées"],
  });
  render(<AssistantPanel onClose={vi.fn()} />);
  await screen.findByRole("option", { name: "AIRB — Projet" });
  fireEvent.change(screen.getByLabelText("Projet interrogé"), { target: { value: "p1" } });
  fireEvent.change(screen.getByLabelText("Question à l’assistant"), { target: { value: "Tu sais quoi de ce projet ?" } });
  fireEvent.keyDown(screen.getByLabelText("Question à l’assistant"), { key: "Enter", shiftKey: true });
  expect(chat).not.toHaveBeenCalled();
  fireEvent.keyDown(screen.getByLabelText("Question à l’assistant"), { key: "Enter" });
  await screen.findByRole("button", { name: "Voir la source P1" });
  expect(chat).toHaveBeenCalledWith("Tu sais quoi de ce projet ?", "p1", true);
  expect(screen.queryByRole("alert")).toBeNull();
  expect(screen.getByText("Recherche textuelle des sources").closest("details")?.open).toBe(false);
  fireEvent.click(screen.getByRole("button", { name: "Voir la source P1" }));
  await waitFor(() => expect(screen.getByText("Prévoir de nouvelles sangles.").closest("details")?.open).toBe(true));
});

it("relance une demande échouée sur son projet initial sans dupliquer la question", async () => {
  vi.spyOn(api, "brainProjects").mockResolvedValue([{ id: "p1", code: "AIRB", name: "Projet" }]);
  const chat = vi.spyOn(api, "brainChat").mockRejectedValueOnce(new Error("IA injoignable"))
    .mockResolvedValueOnce({ answer: "Aucune information trouvée.", citations: [], warnings: [] });
  render(<AssistantPanel onClose={vi.fn()} />);
  await screen.findByRole("option", { name: "AIRB — Projet" });
  fireEvent.change(screen.getByLabelText("Projet interrogé"), { target: { value: "p1" } });
  fireEvent.change(screen.getByLabelText("Question à l’assistant"), { target: { value: "Date FAT ?" } });
  fireEvent.click(screen.getByRole("button", { name: "Envoyer la question" }));
  await screen.findByRole("alert");
  fireEvent.change(screen.getByLabelText("Projet interrogé"), { target: { value: "" } });
  fireEvent.click(screen.getByRole("button", { name: "Réessayer" }));
  await screen.findByText("Aucune information trouvée.");
  expect(chat).toHaveBeenLastCalledWith("Date FAT ?", "p1", true);
  expect(screen.getAllByText("Date FAT ?")).toHaveLength(1);
});

it("ajoute les nouveaux projets ERP au sélecteur sans liaison implicite par code",async()=>{
  vi.spyOn(api,"brainProjects").mockResolvedValue([{id:"brain-other",code:"NEW",name:"Ancienne connaissance"}]);
  const ensure=vi.spyOn(api,"ensureBrainLink").mockResolvedValue({linked:true,brain_project_id:"brain-new",brain_code:"NEW",minipilot_code:"NEW"});
  const chat=vi.spyOn(api,"brainChat").mockResolvedValue({answer:"Réponse",citations:[],warnings:[]});
  const reload=vi.fn().mockResolvedValue(undefined);
  const view=render(<AssistantPanel onClose={vi.fn()} portfolio={[]} onProjectsChanged={reload}/>);
  await screen.findByRole("option",{name:"NEW — Ancienne connaissance"});
  view.rerender(<AssistantPanel onClose={vi.fn()} portfolio={[{id:"erp-new",code:"NEW",title:"Projet nouveau",brain_project_id:null} as PortfolioRow]} onProjectsChanged={reload}/>);
  await screen.findByRole("option",{name:"NEW — Projet nouveau"});expect(ensure).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("Projet interrogé"),{target:{value:"erp:erp-new"}});
  await waitFor(()=>expect(ensure).toHaveBeenCalledWith("erp-new"));await waitFor(()=>expect(reload).toHaveBeenCalledOnce());
  fireEvent.change(screen.getByLabelText("Question à l’assistant"),{target:{value:"Date FAT ?"}});
  fireEvent.click(screen.getByRole("button",{name:"Envoyer la question"}));await waitFor(()=>expect(chat).toHaveBeenCalledWith("Date FAT ?","brain-new",true));
});

it("bloque la question tant que la liaison sélectionnée est absente sans revenir à tous les projets",async()=>{
  vi.spyOn(api,"brainProjects").mockResolvedValue([]);
  const ensure=vi.spyOn(api,"ensureBrainLink").mockRejectedValue(new Error("Administration des liaisons réservée au propriétaire"));
  const chat=vi.spyOn(api,"brainChat").mockResolvedValue({answer:"Réponse"});
  render(<AssistantPanel onClose={vi.fn()} portfolio={[{id:"erp-new",code:"NEW",title:"Projet nouveau",brain_project_id:null} as PortfolioRow]}/>);
  fireEvent.change(screen.getByLabelText("Projet interrogé"),{target:{value:"erp:erp-new"}});await screen.findByRole("alert");
  expect((screen.getByLabelText("Projet interrogé") as HTMLSelectElement).value).toBe("erp:erp-new");
  fireEvent.change(screen.getByLabelText("Question à l’assistant"),{target:{value:"Date FAT ?"}});fireEvent.keyDown(screen.getByLabelText("Question à l’assistant"),{key:"Enter"});
  expect(chat).not.toHaveBeenCalled();expect((screen.getByRole("button",{name:"Envoyer la question"}) as HTMLButtonElement).disabled).toBe(true);
  ensure.mockResolvedValue({linked:true,brain_project_id:"brain-new",brain_code:"NEW",minipilot_code:"NEW"});fireEvent.click(screen.getByRole("button",{name:"Préparer la connaissance du projet"}));
  await waitFor(()=>expect((screen.getByLabelText("Projet interrogé") as HTMLSelectElement).value).toBe("brain-new"));
});

it("interroge le lien explicite existant même si le code affiché correspond à un autre Brain",async()=>{
  vi.spyOn(api,"brainProjects").mockResolvedValue([{id:"brain-other",code:"ERP",name:"Autre Brain"}]);
  const ensure=vi.spyOn(api,"ensureBrainLink");const chat=vi.spyOn(api,"brainChat").mockResolvedValue({answer:"Réponse"});
  render(<AssistantPanel onClose={vi.fn()} portfolio={[{id:"erp-a",code:"ERP",title:"Projet ERP",brain_project_id:"brain-explicit"} as PortfolioRow]} suggestedErpProjectId="erp-a"/>);
  fireEvent.click(screen.getByRole("button",{name:"Interroger le projet affiché"}));
  fireEvent.change(screen.getByLabelText("Question à l’assistant"),{target:{value:"Date FAT ?"}});fireEvent.click(screen.getByRole("button",{name:"Envoyer la question"}));
  await waitFor(()=>expect(chat).toHaveBeenCalledWith("Date FAT ?","brain-explicit",true));expect(ensure).not.toHaveBeenCalled();
});

it("désactive l'envoi pendant la préparation de la connaissance",async()=>{
  vi.spyOn(api,"brainProjects").mockResolvedValue([]);let finish!:(value:Awaited<ReturnType<typeof api.ensureBrainLink>>)=>void;
  vi.spyOn(api,"ensureBrainLink").mockReturnValue(new Promise(done=>{finish=done;}));
  render(<AssistantPanel onClose={vi.fn()} portfolio={[{id:"erp-new",code:"NEW",title:"Projet nouveau",brain_project_id:null} as PortfolioRow]}/>);
  fireEvent.change(screen.getByLabelText("Projet interrogé"),{target:{value:"erp:erp-new"}});
  expect((screen.getByLabelText("Projet interrogé") as HTMLSelectElement).disabled).toBe(true);expect(screen.getByText("Préparation de la connaissance du projet…")).toBeTruthy();
  finish({linked:true,brain_project_id:"brain-new",brain_code:"NEW",minipilot_code:"NEW"});await waitFor(()=>expect((screen.getByLabelText("Projet interrogé") as HTMLSelectElement).disabled).toBe(false));
});


it("distingue une information retenue par défaut d'une confirmation humaine", async () => {
  vi.spyOn(api, "brainProjects").mockResolvedValue([{id: "p1", code: "AIRB", name: "Projet"}]);
  vi.spyOn(api, "brainChat").mockResolvedValue({answer: "Le diamètre est de 50 mm [V1].", citations: [{reference: "V1", project_code: "AIRB", level: "validated", validation_mode: "default", excerpt: "Diamètre : 50 mm", source_id: "s1"}], warnings: []});
  render(<AssistantPanel onClose={vi.fn()} />);
  await screen.findByRole("option", {name: "AIRB — Projet"});
  fireEvent.change(screen.getByLabelText("Projet interrogé"), {target: {value: "p1"}});
  fireEvent.change(screen.getByLabelText("Question à l’assistant"), {target: {value: "Diamètre ?"}});
  fireEvent.click(screen.getByRole("button", {name: "Envoyer la question"}));
  fireEvent.click(await screen.findByRole("button", {name: "Voir la source V1"}));
  expect(screen.getByText("Retenue par défaut")).toBeTruthy();
  expect(screen.queryByText("Confirmation humaine")).toBeNull();
  expect(screen.getByRole("link", {name: "Télécharger la source originale"}).getAttribute("href")).toBe("/v1/sources/s1/raw");
});

/** Fictitious transport and storage; uses the real panel and history hook, no server. */
function persistentStreamFixture(abortRejectsWithItsReason = true, saveError?: string, keepHistory = true) {
  vi.spyOn(api, 'brainProjects').mockResolvedValue([]);
  const writes: AssistantMessage[][] = [];
  let saved: { id: string; title: string; project_id: string | null; revision: number; messages: AssistantMessage[] } | null = null;
  const requests = vi.spyOn(http, 'request').mockImplementation(async (url, init) => {
    if (url === '/api/v1/workspace/assistant-threads?limit=100') return { items: saved ? [saved] : [] } as never;
    if ((url === '/api/v1/workspace/assistant-threads' && init?.method === 'POST')
        || (url === '/api/v1/workspace/assistant-threads/stop-fixture' && init?.method === 'PUT')) {
      if (saveError) throw new Error(saveError);
      const body = JSON.parse(String(init?.body));
      if (saved && body.expected_revision !== saved.revision) throw new Error('Fixture revision differs');
      saved = { id: 'stop-fixture', title: body.title, project_id: body.project_id,
        revision: (saved?.revision || 0) + 1, messages: body.messages };
      writes.push(body.messages);
      return saved as never;
    }
    throw new Error('Unexpected fixture history request: ' + url);
  });
  type Result = Awaited<ReturnType<typeof assistantStreaming.streamAssistant>>;
  const calls: { signal: AbortSignal; history: AssistantMessage[];
    update: Parameters<typeof assistantStreaming.streamAssistant>[5]; resolve: (value: Result) => void; reject: (error: unknown) => void }[] = [];
  vi.spyOn(assistantStreaming, 'streamAssistant').mockImplementation((_query, _project, _evidence, history, signal, update) =>
    new Promise<Result>((resolve, reject) => {
      calls.push({ signal, history, update, resolve, reject });
      if (abortRejectsWithItsReason) signal.addEventListener('abort', () => reject(signal.reason), { once: true });
    }));
  render(<AssistantPanel onClose={vi.fn()} persistHistory />);
  if(keepHistory)fireEvent.click(screen.getByRole('checkbox',{name:'Conversation éphémère'}));
  const start = async (query = 'Analyse du dossier fictif ?') => {
    const next = calls.length + 1;
    fireEvent.change(screen.getByLabelText('Question à l’assistant'), { target: { value: query } });
    fireEvent.click(screen.getByRole('button', { name: 'Envoyer la question' }));
    await waitFor(() => expect(calls).toHaveLength(next));
    return calls[next - 1];
  };
  const lastWrittenMessage = () => {
    const last = writes[writes.length - 1];
    return last ? last[last.length - 1] : undefined;
  };
  return { calls, writes, start, lastWrittenMessage, requests };
}

it('démarre sans historique, garde le contexte éphémère et ne transmet pas cet échange au mode enregistré', async()=>{
  const fixture=persistentStreamFixture(true,undefined,false);
  const finish=(call:typeof fixture.calls[number],answer:string)=>act(()=>{
    call.update(answer,{citations:[],warnings:[]});call.resolve({answer,citations:[],warnings:[]});
  });
  expect((screen.getByRole('checkbox',{name:'Conversation éphémère'}) as HTMLInputElement).checked).toBe(true);
  expect(screen.queryByLabelText('Historique des discussions')).toBeNull();
  expect(fixture.requests).not.toHaveBeenCalled();
  const first=await fixture.start('Question confidentielle ?');
  expect((screen.getByRole('checkbox',{name:'Conversation éphémère'}) as HTMLInputElement).disabled).toBe(true);
  finish(first,'Réponse temporaire.');
  await screen.findByText('Réponse temporaire.');
  const second=await fixture.start('Précise ce point ?');
  expect(second.history.map(item=>item.text)).toEqual(['Question confidentielle ?','Réponse temporaire.']);
  finish(second,'Précision temporaire.');
  await screen.findByText('Précision temporaire.');
  expect(fixture.requests).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('checkbox',{name:'Conversation éphémère'}));
  await screen.findByLabelText('Historique des discussions');
  expect(screen.queryByText('Réponse temporaire.')).toBeNull();
  expect(fixture.writes).toHaveLength(0);
  const third=await fixture.start('Discussion à conserver ?');
  expect(third.history).toEqual([]);
  finish(third,'Réponse conservée.');
  await screen.findByText('Enregistrée localement');
  expect(fixture.lastWrittenMessage()?.text).toBe('Réponse conservée.');
  const count=fixture.writes.length;
  fireEvent.click(screen.getByRole('checkbox',{name:'Conversation éphémère'}));
  expect(screen.queryByText('Réponse conservée.')).toBeNull();
  const fourth=await fixture.start('Retour temporaire ?');
  expect(fourth.history).toEqual([]);
  finish(fourth,'Sans trace dans les discussions.');
  await screen.findByText('Sans trace dans les discussions.');
  expect(fixture.writes).toHaveLength(count);
  cleanup();
  fixture.requests.mockClear();
  render(<AssistantPanel onClose={vi.fn()} persistHistory/>);
  expect((screen.getByRole('checkbox',{name:'Conversation éphémère'}) as HTMLInputElement).checked).toBe(true);
  expect(screen.queryByText('Sans trace dans les discussions.')).toBeNull();
  expect(fixture.requests).not.toHaveBeenCalled();
});

it('ouvre le lecteur de source depuis une citation sans quitter la conversation',async()=>{
  vi.spyOn(api,'brainProjects').mockResolvedValue([]);
  vi.spyOn(api,'brainChat').mockResolvedValue({answer:'Exigence [V1].',citations:[{reference:'V1',project_code:'QA',level:'validated',source_id:'mail',excerpt:'Extrait.'}]});
  const open=vi.fn();
  render(<AssistantPanel onClose={vi.fn()} onSourceOpen={open}/>);
  fireEvent.change(screen.getByLabelText('Question à l’assistant'),{target:{value:'Exigence ?'}});
  fireEvent.click(screen.getByRole('button',{name:'Envoyer la question'}));
  fireEvent.click(await screen.findByRole('button',{name:'Voir la source V1'}));
  const link=screen.getByRole('link',{name:'Consulter la source citée'});
  expect(link.getAttribute('href')).toBe('/app/sources?source=mail');
  fireEvent.click(link);
  expect(open).toHaveBeenCalledWith('mail','V1');
});

it('conserve le fragment, ses citations et son historique après Stop sans erreur ni relance automatique', async () => {
  const fixture = persistentStreamFixture();
  const stream = await fixture.start();
  const citations = [{ reference: 'P1', project_code: 'QA', level: 'proposed', excerpt: 'Preuve fictive conservée.' }];
  act(() => stream.update('Fragment conservé.', { citations, warnings: [] }));
  fireEvent.click(screen.getByRole('button', { name: 'Arrêter la réponse' }));
  await screen.findByText('[Réponse interrompue] Fragment conservé.');
  expect(stream.signal.aborted).toBe(true);
  expect(stream.signal.reason).toMatchObject({ name: 'AbortError', message: 'Réponse arrêtée à votre demande' });
  expect(screen.queryByRole('alert')).toBeNull();
  expect(screen.queryByRole('button', { name: 'Réessayer' })).toBeNull();
  expect(screen.queryByRole('button', { name: 'Arrêter la réponse' })).toBeNull();
  await waitFor(() => expect(fixture.lastWrittenMessage()).toEqual({ role: 'assistant',
    text: '[Réponse interrompue] Fragment conservé.', citations }));
  expect(fixture.calls).toHaveLength(1);
  const next = await fixture.start('Question suivante ?');
  const context = assistantStreaming.conversationContext(next.history);
  expect(context.some(message => message.content.startsWith('[Réponse interrompue]'))).toBe(false);
  expect(next.history.filter(message => message.text === 'Analyse du dossier fictif ?')).toHaveLength(1);
  act(() => {
    next.update('Réponse suivante.', { citations: [], warnings: [] });
    next.resolve({ answer: 'Réponse suivante.', citations: [], warnings: [] });
  });
  await screen.findByText('Réponse suivante.');
});

it('conserve une réponse explicitement interrompue si Stop précède le premier fragment', async () => {
  const fixture = persistentStreamFixture();
  await fixture.start();
  fireEvent.click(screen.getByRole('button', { name: 'Arrêter la réponse' }));
  await screen.findByText('[Réponse interrompue] Aucun texte reçu.');
  expect(screen.queryByRole('alert')).toBeNull();
  await waitFor(() => expect(fixture.lastWrittenMessage()?.text).toBe('[Réponse interrompue] Aucun texte reçu.'));
  expect(within(screen.getByRole('log', { name: 'Conversation' })).getAllByText('Analyse du dossier fictif ?')).toHaveLength(1);
});

it.each([
  ['erreur SSE', () => new Error('Modèle indisponible')],
  ['EOF sans done', () => new Error('Connexion interrompue avant la fin de la réponse')],
  ['panne réseau', () => new TypeError('Failed to fetch')],
] as const)('garde une %s indépendante visible même après un Stop concurrent', async (_kind, makeError) => {
  const fixture = persistentStreamFixture(false);
  const stream = await fixture.start();
  act(() => stream.update('Partiel fiable.', { citations: [], warnings: [] }));
  fireEvent.click(screen.getByRole('button', { name: 'Arrêter la réponse' }));
  const error = makeError();
  act(() => stream.reject(error));
  await waitFor(() => expect(screen.getByRole('alert').textContent).toContain(error.message));
  expect(screen.getByRole('button', { name: 'Réessayer' })).toBeTruthy();
  expect(screen.getByText('[Réponse interrompue] Partiel fiable.')).toBeTruthy();
});

it('ne masque pas une AbortError étrangère au sentinel du Stop, même avec le même message', async () => {
  const fixture = persistentStreamFixture(false);
  const stream = await fixture.start();
  fireEvent.click(screen.getByRole('button', { name: 'Arrêter la réponse' }));
  const foreign = new DOMException('Réponse arrêtée à votre demande', 'AbortError');
  expect(foreign).not.toBe(stream.signal.reason);
  act(() => stream.reject(foreign));
  await waitFor(() => expect(screen.getByRole('alert').textContent).toContain(foreign.message));
  expect(screen.getByRole('button', { name: 'Réessayer' })).toBeTruthy();
});

it('conserve une vraie erreur réseau sans Stop et le brouillon partiel à reprendre', async () => {
  const fixture = persistentStreamFixture();
  const stream = await fixture.start();
  act(() => { stream.update('Fragment réseau.', { citations: [], warnings: [] }); stream.reject(new TypeError('Failed to fetch')); });
  await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('Failed to fetch'));
  expect(stream.signal.aborted).toBe(false);
  expect(screen.getByRole('button', { name: 'Réessayer' })).toBeTruthy();
  await waitFor(() => expect(fixture.lastWrittenMessage()?.text).toBe('[Réponse interrompue] Fragment réseau.'));
});

it('ne masque pas un échec indépendant de sauvegarde après un Stop volontaire', async () => {
  const fixture = persistentStreamFixture(true, 'Historique local indisponible');
  const stream = await fixture.start();
  act(() => stream.update('Brouillon local conservé.', { citations: [], warnings: [] }));
  fireEvent.click(screen.getByRole('button', { name: 'Arrêter la réponse' }));
  await screen.findByText('[Réponse interrompue] Brouillon local conservé.');
  await screen.findByText('Historique local indisponible');
  expect(screen.getByRole('button', { name: 'Réessayer l’enregistrement' })).toBeTruthy();
  expect(screen.queryByRole('button', { name: 'Réessayer' })).toBeNull();
  expect(screen.queryByRole('alert')).toBeNull();
});
