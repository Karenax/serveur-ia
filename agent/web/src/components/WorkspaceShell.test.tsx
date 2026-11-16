import { useState,type ReactNode } from "react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { api, type PortfolioRow } from "../lib/api";
import { getActivitySnapshot } from "../lib/asyncActivity";
import { identityApi } from "../lib/projectIdentity";
import { deliverableApi } from "../lib/projectDeliverables";
import { documentApi, type DocumentPreferences } from "../lib/projectDocuments";
import {fusionSources} from '../lib/fusionSources';
import {meetingWorkspaceHref,requestMeetingWorkspace} from '../lib/meetingWorkspace';
import { WorkspaceShell, type ProjectWorkspaceProps, type ProjectCreateProps } from "./WorkspaceShell";

vi.mock("./SettingsForms", () => ({AiSettingsForm: () => null, MailSettingsForm: () => null, MemorySettingsForm: () => null}));
vi.mock("./OperationsPanel", () => ({OperationsPanel: () => null}));
vi.mock("./ThunderbirdPanel", () => ({ThunderbirdPanel: () => null}));
vi.mock("./ActionDashboard", () => ({ActionDashboard: () => <p>Actions de test</p>}));
vi.mock("./WorkspaceViews", () => ({
  GlobalMeetingsView: ({initialProjectId,creationRequest,studioNavigation,onStudioOpenChange}:{initialProjectId?:string;creationRequest?:{key:number;projectId?:string}|null;studioNavigation?:ReactNode;onStudioOpenChange?:(open:boolean)=>void}) => {
    const [open,setOpen]=useState(false);
    return <section aria-label="Réunions globales de test">Périmètre tous les projets
      <p>Projet du Studio : {initialProjectId||'tous'}</p>
      <button type="button" onClick={()=>{setOpen(true);onStudioOpenChange?.(true);}}>Ouvrir le Studio de test</button>
      {open&&<div className="meeting-studio"><details className="meeting-preparation" open><summary>Préparation</summary>{studioNavigation}<button type="button" onClick={()=>{setOpen(false);onStudioOpenChange?.(false);}}>Fermer le Studio de test</button></details></div>}
      {creationRequest&&<form aria-label="Préparation demandée depuis Sources"><output aria-label="Projet proposé">{creationRequest.projectId||'À rattacher'}</output></form>}
    </section>;
  },
  GlobalKnowledgeView: () => <section aria-label="Connaissance globale de test">Périmètre tous les projets</section>,
  GlobalJobsView: ({active}: {active: boolean}) => <section aria-label="Traitements de test" data-active={String(active)}>État serveur</section>,
  SourceInspector: () => null,
}));

beforeEach(() => {localStorage.clear(); window.history.replaceState(null, "", "/app/");});
afterEach(() => {cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals();});
const row = (id: string, code: string): PortfolioRow => ({id, code, title: `Projet ${code}`, status: "active", client_name: "Client test",
  jalon_en_cours: "Revue", jalon_echeance: "2026-10-09", avancement: 25, raf: 40, taches: "", en_retard: 0, corrections: 0, correction_label: "",
  initial_hours: 100, consumed_hours: 25, remaining_mode: "budget_balance", overrun_hours: 0, unconfirmed: 0, open_points: 0,
  brain_project_id: `brain-${id}`, brain_code: code});
const rows = [row("erp-a", "A-100"), row("erp-b", "B-200")];
it("affiche un nouveau projet après rechargement malgré les filtres du portefeuille précédent", async () => {
  window.history.replaceState(null,"","/app/projects");
  function Creator({onCreated}:ProjectCreateProps) {return <button onClick={()=>void onCreated?.("erp-new")}>Terminer la création</button>;}
  function Harness() {
    const [portfolio,setPortfolio]=useState(rows);
    return <WorkspaceShell rows={portfolio} reload={async()=>{setPortfolio([...rows,row("erp-new","NEW-0807")]);}}
      ProjectPanel={ProjectDraft} MailPanel={()=>null} CreatePanel={Creator} SagePanel={()=>null}/>;
  }
  render(<Harness/>);
  fireEvent.change(screen.getByRole("textbox",{name:"Rechercher un projet"}),{target:{value:"A-100"}});
  fireEvent.change(screen.getByLabelText("État des projets"),{target:{value:"closed"}});
  fireEvent.click(screen.getByRole("button",{name:/Nouveau projet/}));
  fireEvent.click(screen.getByRole("button",{name:"Terminer la création"}));
  await screen.findByRole("button",{name:"NEW-0807 · Projet NEW-0807"});
  expect(window.location.pathname).toBe("/app/projets");
  expect((screen.getByRole("textbox",{name:"Rechercher un projet"}) as HTMLInputElement).value).toBe("");
  expect((screen.getByLabelText("État des projets") as HTMLSelectElement).value).toBe("active");
});
function ProjectDraft({projectId, initialTab, onTabChange}: ProjectWorkspaceProps) {
  const [draft, setDraft] = useState("");
  return <section aria-label={`Projet ${projectId}`}><p>Rubrique projet : {initialTab}</p>
    <label>Brouillon {projectId}<input value={draft} onChange={event => setDraft(event.target.value)} /></label>
    <button type="button" onClick={() => onTabChange?.("cdc")}>Exigences du projet</button>
    <button type="button" onClick={() => onTabChange?.("documents")}>Documents du projet</button>
  </section>;
}
function setup(ProjectPanel = ProjectDraft) {
  return render(<WorkspaceShell rows={rows} reload={vi.fn().mockResolvedValue(undefined)} ProjectPanel={ProjectPanel}
    MailPanel={() => <section aria-label="Mails de test">Liste des mails</section>} CreatePanel={() => null} SagePanel={() => null} />);
}

it("propose le retour aux conversations uniquement dans le client Kiara", () => {
  const first = setup();
  expect(screen.queryByRole("link", {name: "Conversations"})).toBeNull();
  first.unmount();
  document.body.dataset.kiaraDesktop = "true";
  try {
    setup();
    expect(screen.getByRole("link", {name: "Conversations"}).getAttribute("href")).toBe("/chat");
    expect(screen.getByText("Serveur Kiara")).toBeTruthy();
  } finally {
    delete document.body.dataset.kiaraDesktop;
  }
});

it("reprend le thème des Conversations et renvoie vers son réglage sous Windows", () => {
  localStorage.setItem("fred-theme","dark");
  localStorage.setItem("agent-ui-theme","light");
  window.history.replaceState(null,"","/app/settings?settings=appearance");
  document.body.dataset.kiaraDesktop="true";
  document.body.dataset.kiaraWindows="true";
  try {
    const {container}=setup();
    expect(container.querySelector(".workspace-shell")?.getAttribute("data-workspace-theme")).toBe("dark");
    expect(screen.getByRole("link",{name:"Thème de Kiara"}).getAttribute("href")).toBe("/chat#apparence");
    expect(localStorage.getItem("agent-ui-theme")).toBe("light");
  } finally {
    delete document.body.dataset.kiaraDesktop;
    delete document.body.dataset.kiaraWindows;
  }
});

it("place les notifications dans l’en-tête Windows et protège les corrections ouvertes", () => {
  window.history.replaceState(null,"","/app/activite");
  document.body.dataset.kiaraDesktop="true";
  document.body.dataset.kiaraWindows="true";
  try {
    setup();
    const notification=screen.getByRole("link",{name:"Notifications"});
    expect(notification.closest("header")).toBeTruthy();
    expect(notification.getAttribute("href")).toBe("/chat#notifications");
    const correction=screen.getByRole("main");
    correction.dataset.workspaceDirty="true";
    expect(fireEvent.click(notification)).toBe(false);
    expect(screen.getByText("Enregistrez ou fermez la modification en cours avant de revenir à Conversations.")).toBeTruthy();
  } finally {
    delete document.body.dataset.kiaraDesktop;
    delete document.body.dataset.kiaraWindows;
  }
});

it("ouvre directement la liste Projets à l’entrée du portail Windows", () => {
  document.body.dataset.kiaraDesktop="true";
  document.body.dataset.kiaraWindows="true";
  try {
    setup();
    expect(window.location.pathname).toBe("/app/projets");
    const menu=screen.getByRole("navigation",{name:"Grandes rubriques"});
    expect(within(menu).getAllByRole("link").map(link=>link.textContent)).toEqual([
      "Conversations","Projets","Mails","Réunions","Activité"
    ]);
    fireEvent.click(within(menu).getByRole("link",{name:"Activité"}));
    expect(screen.getByRole("heading",{name:"À traiter"})).toBeTruthy();
    fireEvent.click(screen.getByRole("link",{name:"Kiara"}));
    expect(window.location.pathname).toBe("/app/projets");
    fireEvent.click(screen.getByRole("button",{name:"Accès rapide aux rubriques"}));
    expect(screen.queryByRole("button",{name:/^Accueil/})).toBeNull();
  } finally {
    delete document.body.dataset.kiaraDesktop;
    delete document.body.dataset.kiaraWindows;
  }
});

it("propose l’assistant dans les fiches Windows avec le projet déjà sélectionné", () => {
  document.body.dataset.kiaraDesktop="true";
  document.body.dataset.kiaraWindows="true";
  document.body.dataset.kiaraProjectConversation="true";
  try {
    setup();
    expect(screen.queryByRole("link",{name:"Assistant de projet"})).toBeNull();
    fireEvent.click(screen.getByRole("button",{name:"A-100 · Projet A-100"}));
    expect(screen.getByRole("link",{name:"Assistant de projet"}).getAttribute("href")).toBe("/chat#projet=erp-a");
    fireEvent.click(screen.getByRole("link",{name:"Mails"}));
    expect(screen.queryByRole("link",{name:"Assistant de projet"})).toBeNull();
  } finally {
    delete document.body.dataset.kiaraDesktop;
    delete document.body.dataset.kiaraWindows;
    delete document.body.dataset.kiaraProjectConversation;
  }
});

it('ouvre le Studio commun filtré depuis le projet puis permet le retour à toutes les réunions',async()=>{
  window.history.replaceState(null,'','/app/projects/erp-a/reviews');
  function ProjectStudio(){return <a href={meetingWorkspaceHref('erp-a')} onClick={event=>{if(requestMeetingWorkspace('erp-a'))event.preventDefault();}}>Studio du projet</a>;}
  setup(ProjectStudio);
  fireEvent.click(await screen.findByRole('link',{name:'Studio du projet'}));
  await screen.findByText('Projet du Studio : erp-a');
  expect(window.location.pathname).toBe('/app/meetings');
  expect(window.location.search).toBe('?project=erp-a');
  expect(screen.queryByRole('form',{name:'Préparation demandée depuis Sources'})).toBeNull();
  fireEvent.click(screen.getByRole('link',{name:'Réunions'}));
  await screen.findByText('Projet du Studio : tous');
});

it("indique l’import d’archive dès la lecture locale et jusqu’à la fin du rechargement", async () => {
  window.history.replaceState(null, "", "/app/imports");
  let finishRead!: (value: string) => void;
  let finishReload!: () => void;
  const reading = new Promise<string>(resolve => { finishRead = resolve; });
  const reloading = new Promise<void>(resolve => { finishReload = resolve; });
  const read = vi.fn(() => reading);
  const file = new File(["archive fictive"], "archive.json", { type: "application/json" });
  Object.defineProperty(file, "text", { value: read });
  const importJson = vi.spyOn(api, "importJson").mockResolvedValue({});
  const reload = vi.fn(() => reloading);
  const { container } = render(<WorkspaceShell rows={rows} reload={reload} ProjectPanel={ProjectDraft}
    MailPanel={() => null} CreatePanel={() => null} SagePanel={() => null} />);
  fireEvent.click(screen.getByRole("button", { name: "Archives JSON" }));
  const input = container.querySelector('input[type="file"][accept="application/json,.json"]')!;
  fireEvent.change(input, { target: { files: [file] } });
  expect(getActivitySnapshot()?.labels).toContain("Importation d’une archive de projet…");
  expect(importJson).not.toHaveBeenCalled();
  expect((screen.getByRole("button", { name: "Importer une archive JSON" }) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.change(input, { target: { files: [file] } });
  expect(read).toHaveBeenCalledTimes(1);
  await act(async () => { finishRead('{"project":{"code":"FAKE"}}'); });
  expect(importJson).toHaveBeenCalledWith({ project: { code: "FAKE" } });
  expect(reload).toHaveBeenCalledTimes(1);
  expect(getActivitySnapshot()?.labels).toContain("Importation d’une archive de projet…");
  await act(async () => { finishReload(); });
  await screen.findByText("Archive importée. Les projets existants sont conservés.");
  expect(getActivitySnapshot()?.labels ?? []).not.toContain("Importation d’une archive de projet…");
  expect((screen.getByRole("button", { name: "Importer une archive JSON" }) as HTMLButtonElement).disabled).toBe(false);
});

it("clôture le travail et conserve l’erreur existante quand la lecture de l’archive échoue", async () => {
  window.history.replaceState(null, "", "/app/imports");
  let failRead!: (failure: Error) => void;
  const reading = new Promise<string>((_resolve, reject) => { failRead = reject; });
  const file = new File([], "archive.json", { type: "application/json" });
  Object.defineProperty(file, "text", { value: () => reading });
  const importJson = vi.spyOn(api, "importJson").mockResolvedValue({});
  const reload = vi.fn().mockResolvedValue(undefined);
  const { container } = render(<WorkspaceShell rows={rows} reload={reload} ProjectPanel={ProjectDraft}
    MailPanel={() => null} CreatePanel={() => null} SagePanel={() => null} />);
  fireEvent.click(screen.getByRole("button", { name: "Archives JSON" }));
  fireEvent.change(container.querySelector('input[type="file"][accept="application/json,.json"]')!, { target: { files: [file] } });
  expect(getActivitySnapshot()?.labels).toContain("Importation d’une archive de projet…");
  await act(async () => { failRead(new Error("Lecture locale interrompue")); });
  await screen.findByText("Import impossible : Lecture locale interrompue");
  expect(getActivitySnapshot()?.labels ?? []).not.toContain("Importation d’une archive de projet…");
  expect(importJson).not.toHaveBeenCalled(); expect(reload).not.toHaveBeenCalled();
  expect((screen.getByRole("button", { name: "Importer une archive JSON" }) as HTMLButtonElement).disabled).toBe(false);
});

it('protège la navigation Nouvelle séance depuis Sources, puis transmet le projet ERP au parcours existant',()=>{
  window.history.replaceState(null,'','/app/sources');
  vi.spyOn(fusionSources,'list').mockResolvedValue({items:[],total:0,offset:0,limit:25,has_next:false,labels:[]});
  const confirm=vi.spyOn(window,'confirm').mockReturnValue(false);
  setup();fireEvent.change(screen.getByLabelText('Projet'),{target:{value:'erp-b'}});
  const draft=document.createElement('div');draft.dataset.workspaceDirty='true';document.body.append(draft);
  try{
    fireEvent.click(screen.getByRole('button',{name:'Nouvelle séance'}));
    expect(confirm).toHaveBeenCalled();expect(window.location.pathname).toBe('/app/sources');
    expect(screen.queryByRole('form',{name:'Préparation demandée depuis Sources'})).toBeNull();
    confirm.mockReturnValue(true);fireEvent.click(screen.getByRole('button',{name:'Nouvelle séance'}));
    expect(window.location.pathname).toBe('/app/meetings');
    expect(screen.getByLabelText('Projet proposé').textContent).toBe('erp-b');
    fireEvent.click(screen.getByRole('link',{name:'Réglages'}));
    fireEvent.click(screen.getByRole('button',{name:'Sources'}));
    fireEvent.change(screen.getByLabelText('Projet'),{target:{value:''}});
    fireEvent.click(screen.getByRole('button',{name:'Nouvelle séance'}));
    expect(window.location.pathname).toBe('/app/meetings');
    expect(screen.getByLabelText('Projet proposé').textContent).toBe('À rattacher');
  }finally{draft.remove();}
});

it('conserve le même retour protégé dans Préparation et rétablit le fil d’Ariane hors Studio',()=>{
  window.history.replaceState(null,'','/app/meetings');const {container}=setup();
  expect(screen.getByRole('navigation',{name:'Fil d’Ariane'}).closest('.meeting-preparation')).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'Ouvrir le Studio de test'}));
  expect(container.querySelector('.workspace-shell')?.getAttribute('data-meeting-studio')).toBe('true');
  expect(screen.getAllByRole('navigation',{name:'Fil d’Ariane'})).toHaveLength(1);
  expect(screen.getByRole('navigation',{name:'Fil d’Ariane'}).closest('.meeting-preparation')).not.toBeNull();
  const confirm=vi.spyOn(window,'confirm').mockReturnValue(false),draft=document.createElement('div');draft.dataset.workspaceDirty='true';document.body.append(draft);
  try{
    fireEvent.click(within(screen.getByRole('navigation',{name:'Fil d’Ariane'})).getByRole('link',{name:'Espace de travail'}));
    expect(confirm).toHaveBeenCalled();expect(window.location.pathname).toBe('/app/meetings');
    confirm.mockReturnValue(true);fireEvent.click(within(screen.getByRole('navigation',{name:'Fil d’Ariane'})).getByRole('link',{name:'Espace de travail'}));
    expect(window.location.pathname).toBe('/app/');expect(container.querySelector('.workspace-shell')?.hasAttribute('data-meeting-studio')).toBe(false);
    fireEvent.click(screen.getByRole('link',{name:'Réunions'}));fireEvent.click(screen.getByRole('button',{name:'Fermer le Studio de test'}));
    expect(screen.getByRole('navigation',{name:'Fil d’Ariane'}).closest('.meeting-preparation')).toBeNull();
    expect(container.querySelector('.workspace-shell')?.hasAttribute('data-meeting-studio')).toBe(false);
  }finally{draft.remove();}
});

it("garde le même seuil de menu entre les réunions, les sources et les projets",()=>{
  vi.stubGlobal('innerWidth',900);window.history.replaceState(null,'','/app/meetings');setup();
  const sidebar=screen.getByRole('complementary',{name:'Menu principal'});
  expect(sidebar.hasAttribute('inert')).toBe(false);
  screen.getByRole('link',{name:'Réunions'}).focus();
  vi.stubGlobal('innerWidth',850);fireEvent(window,new Event('resize'));
  expect(sidebar.getAttribute('aria-hidden')).toBe('true');
  expect(document.activeElement).toBe(screen.getByRole('button',{name:'Ouvrir le menu'}));
  fireEvent.click(screen.getByRole('button',{name:'Ouvrir le menu'}));
  fireEvent.click(screen.getByRole('link',{name:'Réglages'}));
  fireEvent.click(screen.getByRole('button',{name:'Sources'}));
  expect(sidebar.getAttribute('aria-hidden')).toBe('true');
  fireEvent.click(screen.getByRole('button',{name:'Ouvrir le menu'}));
  fireEvent.click(screen.getByRole('link',{name:'Projets'}));
  expect(sidebar.getAttribute('aria-hidden')).toBe('true');
  vi.stubGlobal('innerWidth',900);fireEvent(window,new Event('resize'));
  expect(sidebar.hasAttribute('inert')).toBe(false);
});

it('accorde le menu au seuil CSS lorsque la largeur entière diffère de la largeur de mise en page',()=>{
  vi.stubGlobal('innerWidth',850);
  let standardNarrow=false;
  const listeners=new Set<()=>void>();
  vi.stubGlobal('matchMedia',(query:string)=>({matches:query==='(min-width:671px)'||standardNarrow,
    addEventListener:(_event:string,listener:()=>void)=>listeners.add(listener),
    removeEventListener:(_event:string,listener:()=>void)=>listeners.delete(listener)}));
  window.history.replaceState(null,'','/app/sources');
  setup();
  const sidebar=screen.getByRole('complementary',{name:'Menu principal'});
  screen.getByRole('link',{name:'Projets'}).focus();
  fireEvent.click(screen.getByRole('link',{name:'Projets'}));
  expect(screen.getByRole('complementary',{name:'Menu principal'}).hasAttribute('inert')).toBe(false);
  standardNarrow=true;
  fireEvent(window,new Event('resize'));
  expect(sidebar.hasAttribute('inert')).toBe(true);
  expect(document.activeElement).toBe(screen.getByRole('button',{name:'Ouvrir le menu'}));
});
function chooseExtraSetting(name:string) {
  fireEvent.click(screen.getByRole("button",{name:/^Autres réglages/}));
  fireEvent.click(screen.getByRole("button",{name}));
}

it("ouvre les rubriques de la fiche en conservant le brouillon et l’URL",()=>{
  window.history.replaceState(null,"","/app/projects/erp-b/cdc");
  setup(ProjectDraft);
  expect(screen.getByText("Rubrique projet : cdc")).toBeTruthy();
  fireEvent.change(screen.getByRole("textbox",{name:"Brouillon erp-b"}),{target:{value:"À conserver"}});
  fireEvent.click(screen.getByRole("button",{name:"Documents du projet"}));
  expect(window.location.pathname).toBe("/app/projets/erp-b/documents");
  expect((screen.getByRole("textbox",{name:"Brouillon erp-b"}) as HTMLInputElement).value).toBe("À conserver");
  fireEvent.click(screen.getByRole("button",{name:"Rechercher dans Kiara"}));
  expect(window.location.pathname).toBe("/app/search");
});

it("conserve les réglages documentaires entre sous-rubriques et protège une sauvegarde en cours",async()=>{
  window.history.replaceState(null,"","/app/settings");
  const preferences:DocumentPreferences={available:true,revision:2,version_id:'s2',items:[
    'offer_lt_simple','tdao','tdsp','manufacturing_specification','user_manual','ce_request','customer_satisfaction_product','customer_satisfaction_fixed_price'
  ].map((id,index)=>({document_id:id as DocumentPreferences['items'][number]['document_id'],label:`Trame ${index+1}`,format:'DOCX',relative_paths:['.'],filename_patterns:['Trame'],excluded_tokens:[],preferred_version:null,active:true,order:index}))};
  const read=vi.spyOn(documentApi,'preferences').mockResolvedValue(preferences);
  let finish!:(value:DocumentPreferences)=>void;vi.spyOn(documentApi,'savePreferences').mockReturnValue(new Promise(resolve=>{finish=resolve;}));
  const confirm=vi.spyOn(window,'confirm').mockReturnValueOnce(false).mockReturnValueOnce(true);
  setup();expect(read).not.toHaveBeenCalled();chooseExtraSetting("Modèles de documents");
  await screen.findByLabelText('Modifier les recherches des trames');await waitFor(()=>expect(screen.getByRole('button',{name:'Comparer avec les réglages enregistrés'}).matches(':disabled')).toBe(false));
  fireEvent.change(screen.getAllByLabelText('Libellé')[0],{target:{value:'Brouillon commun'}});
  fireEvent.click(screen.getByRole('button',{name:'Apparence'}));expect(screen.getByRole('region',{name:'Réglages documentaires'})).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'Apparence'}));expect(screen.queryByRole('region',{name:'Réglages documentaires'})).toBeNull();
  chooseExtraSetting("Modèles de documents");expect((screen.getAllByLabelText('Libellé')[0] as HTMLInputElement).value).toBe('Brouillon commun');
  expect(read).toHaveBeenCalledTimes(1);expect(confirm).toHaveBeenCalledTimes(2);
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer les réglages'}));fireEvent.click(screen.getByRole('link',{name:'Mails'}));
  expect(window.location.pathname).toBe('/app/settings');expect(screen.getByText(/Réglages documentaires en cours/)).toBeTruthy();
  finish({...preferences,revision:3,items:preferences.items.map((item,index)=>({...item,label:index?'Trame '+(index+1):'Brouillon commun'}))});
  await screen.findByText('Réglages enregistrés · version 3.');
});

it("charge le catalogue seulement à l’ouverture de Livrables et conserve le brouillon entre rubriques",async()=>{
  window.history.replaceState(null,"","/app/settings");const types=vi.spyOn(deliverableApi,"types").mockResolvedValue({items:[],total:0,offset:0,limit:25,can_manage:true});setup();expect(types).not.toHaveBeenCalled();chooseExtraSetting("Modèles de livrables");fireEvent.click(await screen.findByRole("button",{name:"Créer un type de livrable"}));fireEvent.change(screen.getByLabelText("Libellé du type de livrable"),{target:{value:"Brouillon conservé"}});fireEvent.click(screen.getByRole("button",{name:"Apparence"}));chooseExtraSetting("Modèles de livrables");expect((screen.getByLabelText("Libellé du type de livrable") as HTMLInputElement).value).toBe("Brouillon conservé");
});

it("ouvre les référentiels depuis Réglages et charge leur liste à la demande", async () => {
  window.history.replaceState(null,"","/app/settings");
  vi.spyOn(identityApi,"session").mockResolvedValue({operator:{id:"local",role:"owner",can_edit:true,can_administer:true,project_ids:null}});
  const references=vi.spyOn(identityApi,"references").mockResolvedValue({items:[],total:0,offset:0,limit:50});
  setup();expect(references).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button",{name:"Clients et équipe"}));
  expect(await screen.findByRole("region",{name:"Clients, équipe et catégories"})).toBeTruthy();
  await waitFor(()=>expect(references).toHaveBeenCalledWith("client",expect.objectContaining({offset:0})));
  fireEvent.click(screen.getByRole("button",{name:"Ajouter un client"}));
  fireEvent.change(screen.getByLabelText("Libellé"),{target:{value:"Brouillon conservé"}});
  fireEvent.click(screen.getByRole("button",{name:"Apparence"}));
  fireEvent.click(screen.getByRole("button",{name:"Clients et équipe"}));
  expect((screen.getByLabelText("Libellé") as HTMLInputElement).value).toBe("Brouillon conservé");
});

it("restaure une URL directe avec le bon projet et sa rubrique", () => {
  window.history.replaceState(null, "", "/app/projects/erp-b/cdc");
  setup();
  expect(screen.getByRole("region", {name: "Projet erp-b"})).toBeTruthy();
  expect(screen.queryByRole("region", {name: "Projet erp-a"})).toBeNull();
  expect(screen.getByText("Rubrique projet : cdc")).toBeTruthy();
  expect(document.title).toBe("B-200 · Kiara");
});

it("respecte le retour du navigateur après avoir quitté une rubrique projet", async () => {
  window.history.replaceState(null, "", "/app/projects/erp-a/reviews");
  setup();
  fireEvent.click(screen.getByRole("link", {name: "Mails"}));
  expect(window.location.pathname).toBe("/app/mail");
  expect(screen.getByRole("region", {name: "Mails de test"})).toBeTruthy();
  window.history.back();
  await waitFor(() => expect(window.location.pathname).toBe("/app/projects/erp-a/reviews"));
  await waitFor(() => expect(screen.getByRole("region", {name: "Projet erp-a"})).toBeTruthy());
  expect(screen.getByText("Rubrique projet : reviews")).toBeTruthy();
});

it("ouvre une vue globale sans choisir ni monter implicitement le premier projet", () => {
  window.history.replaceState(null, "", "/app/meetings");
  const project = vi.fn(ProjectDraft);
  setup(project);
  expect(screen.getByRole("region", {name: "Réunions globales de test"})).toBeTruthy();
  expect(project).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("link",{name:/^Projets$/}));
  fireEvent.click(screen.getByRole("button",{name:"B-200 · Projet B-200"}));
  expect(window.location.pathname).toBe("/app/projets/erp-b/vue-ensemble");
  expect(screen.getByRole("region", {name: "Projet erp-b"})).toBeTruthy();
  expect(screen.queryByRole("region", {name: "Projet erp-a"})).toBeNull();
});

it("conserve un brouillon du projet en allant vers les mails puis en revenant", () => {
  window.history.replaceState(null, "", "/app/projects/erp-a/reviews");
  setup();
  fireEvent.change(screen.getByRole("textbox", {name: "Brouillon erp-a"}), {target: {value: "Décision en cours de relecture"}});
  fireEvent.click(screen.getByRole("link", {name: "Mails"}));
  expect(screen.queryByRole("textbox", {name: "Brouillon erp-a"})).toBeNull();
  fireEvent.click(screen.getByRole("link",{name:/^Projets$/}));
  fireEvent.click(screen.getByRole("button",{name:"A-100 · Projet A-100"}));
  expect((screen.getByRole("textbox", {name: "Brouillon erp-a"}) as HTMLInputElement).value).toBe("Décision en cours de relecture");
});

it("préserve les états de deux projets distincts et les changements de rubrique", () => {
  window.history.replaceState(null, "", "/app/projects/erp-a/pilotage");
  setup();
  fireEvent.change(screen.getByRole("textbox", {name: "Brouillon erp-a"}), {target: {value: "Brouillon A"}});
  fireEvent.click(screen.getByRole("button", {name: "Exigences du projet"}));
  expect(window.location.pathname).toBe("/app/projets/erp-a/pilotage/cdc");
  expect((screen.getByRole("textbox", {name: "Brouillon erp-a"}) as HTMLInputElement).value).toBe("Brouillon A");
  fireEvent.click(screen.getByRole("link", {name:/^Projets$/}));
  fireEvent.click(screen.getByRole("button", {name:"B-200 · Projet B-200"}));
  expect((screen.getByRole("textbox", {name: "Brouillon erp-b"}) as HTMLInputElement).value).toBe("");
  fireEvent.change(screen.getByRole("textbox", {name: "Brouillon erp-b"}), {target: {value: "Brouillon B"}});
  fireEvent.click(screen.getByRole("link", {name:/^Projets$/}));
  fireEvent.click(screen.getByRole("button", {name:"A-100 · Projet A-100"}));
  expect((screen.getByRole("textbox", {name: "Brouillon erp-a"}) as HTMLInputElement).value).toBe("Brouillon A");
  fireEvent.click(screen.getByRole("link", {name:/^Projets$/}));
  fireEvent.click(screen.getByRole("button", {name:"B-200 · Projet B-200"}));
  expect((screen.getByRole("textbox", {name: "Brouillon erp-b"}) as HTMLInputElement).value).toBe("Brouillon B");
});

it("désactive le polling de la vue des traitements lorsqu'elle est cachée", () => {
  window.history.replaceState(null, "", "/app/jobs");
  setup();
  const jobs = screen.getByRole("region", {name: "Traitements de test"});
  expect(jobs.getAttribute("data-active")).toBe("true");
  fireEvent.click(screen.getByRole("link", {name: "Mails"}));
  expect(jobs.getAttribute("data-active")).toBe("false");
  expect(jobs.closest("[data-workspace-view]")?.hasAttribute("hidden")).toBe(true);
  fireEvent.click(screen.getByRole('link',{name:'Réglages'}));
  fireEvent.click(screen.getByRole("button", {name: "Suivi des analyses"}));
  expect(jobs.getAttribute("data-active")).toBe("true");
});

it("ouvre le composeur commun avec le projet courant sur le portail privé", () => {
  document.body.dataset.kiaraWebConversations = "true";
  window.history.replaceState(null, "", "/kiara/app/projects/erp-a/pilotage");
  try {
    setup();
    expect(screen.getByRole("link", {name: "Assistant de projet"}).getAttribute("href"))
      .toBe("/kiara/app/conversations#projet=erp-a");
    expect(screen.queryByRole("button", {name: "Assistant"})).toBeNull();
  } finally { delete document.body.dataset.kiaraWebConversations; }
});

it("ouvre le composeur commun dans le relais de bureau", () => {
  document.body.dataset.kiaraDesktop = "true";
  document.body.dataset.kiaraProjectConversation = "true";
  try {
    setup();
    expect(screen.getByRole("link", {name: "Assistant de projet"}).getAttribute("href")).toBe("/chat#projet=");
    expect(screen.queryByRole("button", {name: "Assistant"})).toBeNull();
  } finally {
    delete document.body.dataset.kiaraDesktop;
    delete document.body.dataset.kiaraProjectConversation;
  }
});
it('range les statistiques dans les autres réglages et les sépare de la préparation',async()=>{
  setup();
  expect(screen.queryByRole('link',{name:'Statistiques'})).toBeNull();
  fireEvent.click(screen.getByRole('link',{name:'Réglages'}));
  fireEvent.click(screen.getByRole('button',{name:'Autres réglages'}));
  const options=screen.getByRole('group',{name:'Réglages supplémentaires'});
  expect(within(options).getByRole('button',{name:'Statistiques'})).toBeTruthy();
  expect(within(options).getByRole('button',{name:'Réunions et transcription'})).toBeTruthy();
});

it('regroupe les quatre rubriques dans les onglets Réglages en conservant leurs routes',()=>{
  vi.spyOn(fusionSources,'list').mockResolvedValue({items:[],total:0,offset:0,limit:25,has_next:false,labels:[]});
  setup();
  const sidebar=screen.getByRole('complementary',{name:'Menu principal'});
  for(const label of ['Sources','Informations','Suivi des analyses','Connexions & imports']){
    expect(within(sidebar).queryByRole('link',{name:label})).toBeNull();
  }
  fireEvent.click(within(sidebar).getByRole('link',{name:'Réglages'}));
  for(const [page,label] of [['sources','Sources'],['knowledge','Informations'],['jobs','Suivi des analyses'],['imports','Connexions & imports']]){
    const tabs=screen.getByRole('navigation',{name:'Réglages'});
    fireEvent.click(within(tabs).getByRole('button',{name:label}));
    expect(window.location.pathname).toBe('/app/'+page);
    expect(screen.getAllByRole('navigation',{name:'Réglages'})).toHaveLength(1);
    expect(within(screen.getByRole('navigation',{name:'Réglages'})).getByRole('button',{name:label}).getAttribute('aria-pressed')).toBe('true');
    expect(within(sidebar).getByRole('link',{name:'Réglages'}).classList.contains('workspace-nav-parent-active')).toBe(true);
  }
  fireEvent.click(within(screen.getByRole('navigation',{name:'Réglages'})).getByRole('button',{name:'Général'}));
  expect(window.location.pathname).toBe('/app/settings');
  expect(screen.getByRole('button',{name:'Général'}).getAttribute('aria-pressed')).toBe('true');
});

it.each([['sources','Sources'],['knowledge','Informations'],['jobs','Suivi des analyses'],['imports','Connexions & imports']])('repère la rubrique %s ouverte par lien direct', (page,label)=>{
  vi.spyOn(fusionSources,'list').mockResolvedValue({items:[],total:0,offset:0,limit:25,has_next:false,labels:[]});
  window.history.replaceState(null,'','/app/'+page);
  setup();
  expect(within(screen.getByRole('navigation',{name:'Réglages'})).getByRole('button',{name:label}).getAttribute('aria-pressed')).toBe('true');
});
