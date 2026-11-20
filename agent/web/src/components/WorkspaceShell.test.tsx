import { useLayoutEffect,useRef,useState,type ReactNode } from "react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { api, type CdcItem, type PortfolioRow } from "../lib/api";
import { getActivitySnapshot } from "../lib/asyncActivity";
import { identityApi } from "../lib/projectIdentity";
import { deliverableApi } from "../lib/projectDeliverables";
import { documentApi, type DocumentPreferences } from "../lib/projectDocuments";
import {fusionSources} from '../lib/fusionSources';
import {fusionInsights} from '../lib/fusionInsights';
import {meetingWorkspaceHref,requestMeetingWorkspace} from '../lib/meetingWorkspace';
import { WorkspaceShell, type ProjectWorkspaceProps, type ProjectCreateProps } from "./WorkspaceShell";
import { CdcReviewPanel } from "./CdcReviewPanel";

vi.mock("./SettingsForms", () => ({
  AiSettingsForm: () => <input aria-label="Brouillon général de test" />,
  MailSettingsForm: () => <input aria-label="Brouillon mails de test" />,
  MemorySettingsForm: () => <input aria-label="Brouillon recherche de test" />,
}));
vi.mock("./OperationsPanel", () => ({OperationsPanel: () => <p>Maintenance de test</p>}));
vi.mock("./SourceInspector", () => ({SourceInspector: () => null}));
vi.mock("./ThunderbirdPanel", () => ({ThunderbirdPanel: ({active}:{active?:boolean}) => <span data-testid="thunderbird-activity" data-active={String(active)} />}));
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
function ReleasableProject({projectId,registerCache}:ProjectWorkspaceProps) {
  const retained=useRef(false),[draft,setDraft]=useState('');
  useLayoutEffect(()=>registerCache?.(projectId,()=>!retained.current),[projectId,registerCache]);
  return <section aria-label={`Fiche ${projectId}`}><label>Saisie {projectId}<input value={draft} onChange={event=>{retained.current=true;setDraft(event.target.value);}}/></label></section>;
}
function UncertainProject({projectId,registerCache}:ProjectWorkspaceProps) {
  const [draft,setDraft]=useState('');
  useLayoutEffect(()=>registerCache?.(projectId,()=>{if(projectId==='p1')throw new Error('état inconnu');return true;}),[projectId,registerCache]);
  return <label>Saisie {projectId}<input value={draft} onChange={event=>setDraft(event.target.value)}/></label>;
}

it('limite les fiches libérables sans évincer les brouillons après de nombreux projets',()=>{
  const many=Array.from({length:12},(_,index)=>row(`p${index+1}`,`C-${String(index+1).padStart(2,'0')}`));
  window.history.replaceState(null,'','/app/projets');
  const {container}=render(<WorkspaceShell rows={many} reload={vi.fn().mockResolvedValue(undefined)} ProjectPanel={ReleasableProject}
    MailPanel={()=>null} CreatePanel={()=>null} SagePanel={()=>null}/>);
  const open=(index:number)=>fireEvent.click(screen.getByRole('button',{name:`C-${String(index).padStart(2,'0')} · Projet C-${String(index).padStart(2,'0')}`}));
  const portfolio=()=>fireEvent.click(screen.getByRole('link',{name:'Projets'}));
  open(1);fireEvent.change(screen.getByRole('textbox',{name:'Saisie p1'}),{target:{value:'Brouillon à conserver'}});portfolio();
  for(let index=2;index<=12;index++){open(index);portfolio();}
  expect(container.querySelectorAll('[data-workspace-view^="project:"]').length).toBeLessThanOrEqual(6);
  expect(container.querySelector('[data-workspace-view="project:p1"]')).toBeTruthy();
  expect(container.querySelector('[data-workspace-view="project:p2"]')).toBeNull();
  open(1);expect((screen.getByRole('textbox',{name:'Saisie p1'}) as HTMLInputElement).value).toBe('Brouillon à conserver');
});

it('conserve les fiches qui ne déclarent pas explicitement leur état libérable',()=>{
  const many=Array.from({length:8},(_,index)=>row(`p${index+1}`,`C-${String(index+1).padStart(2,'0')}`));
  window.history.replaceState(null,'','/app/projets');
  const {container}=render(<WorkspaceShell rows={many} reload={vi.fn().mockResolvedValue(undefined)} ProjectPanel={ProjectDraft}
    MailPanel={()=>null} CreatePanel={()=>null} SagePanel={()=>null}/>);
  for(let index=1;index<=8;index++){
    fireEvent.click(screen.getByRole('button',{name:`C-${String(index).padStart(2,'0')} · Projet C-${String(index).padStart(2,'0')}`}));
    fireEvent.click(screen.getByRole('link',{name:'Projets'}));
  }
  expect(container.querySelectorAll('[data-workspace-view^="project:"]')).toHaveLength(8);
});

it('conserve la fiche lorsque son contrôle de libération échoue',()=>{
  const many=Array.from({length:8},(_,index)=>row(`p${index+1}`,`C-${String(index+1).padStart(2,'0')}`));
  window.history.replaceState(null,'','/app/projets');
  const {container}=render(<WorkspaceShell rows={many} reload={vi.fn().mockResolvedValue(undefined)} ProjectPanel={UncertainProject}
    MailPanel={()=>null} CreatePanel={()=>null} SagePanel={()=>null}/>);
  for(let index=1;index<=8;index++){
    fireEvent.click(screen.getByRole('button',{name:`C-${String(index).padStart(2,'0')} · Projet C-${String(index).padStart(2,'0')}`}));
    if(index===1)fireEvent.change(screen.getByRole('textbox',{name:'Saisie p1'}),{target:{value:'À préserver'}});
    fireEvent.click(screen.getByRole('link',{name:'Projets'}));
  }
  expect(container.querySelector<HTMLInputElement>('[data-workspace-view="project:p1"] input')?.value).toBe('À préserver');
  expect(container.querySelectorAll('[data-workspace-view^="project:"]').length).toBeLessThanOrEqual(6);
});

it('dépasse la limite plutôt que de supprimer plusieurs brouillons protégés',()=>{
  const many=Array.from({length:8},(_,index)=>row(`p${index+1}`,`C-${String(index+1).padStart(2,'0')}`));
  window.history.replaceState(null,'','/app/projets');
  const {container}=render(<WorkspaceShell rows={many} reload={vi.fn().mockResolvedValue(undefined)} ProjectPanel={ReleasableProject}
    MailPanel={()=>null} CreatePanel={()=>null} SagePanel={()=>null}/>);
  for(let index=1;index<=8;index++){
    fireEvent.click(screen.getByRole('button',{name:`C-${String(index).padStart(2,'0')} · Projet C-${String(index).padStart(2,'0')}`}));
    fireEvent.change(screen.getByRole('textbox',{name:`Saisie p${index}`}),{target:{value:`Brouillon ${index}`}});
    fireEvent.click(screen.getByRole('link',{name:'Projets'}));
  }
  expect(container.querySelectorAll('[data-workspace-view^="project:"]')).toHaveLength(8);
  for(let index=1;index<=8;index++){
    const input=container.querySelector<HTMLInputElement>(`[data-workspace-view="project:p${index}"] input`);
    expect(input?.value).toBe(`Brouillon ${index}`);
  }
});

it('évince la fiche libérable la moins récemment consultée',()=>{
  const many=Array.from({length:7},(_,index)=>row(`p${index+1}`,`C-${String(index+1).padStart(2,'0')}`));
  window.history.replaceState(null,'','/app/projets');
  const {container}=render(<WorkspaceShell rows={many} reload={vi.fn().mockResolvedValue(undefined)} ProjectPanel={ReleasableProject}
    MailPanel={()=>null} CreatePanel={()=>null} SagePanel={()=>null}/>);
  const open=(index:number)=>fireEvent.click(screen.getByRole('button',{name:`C-${String(index).padStart(2,'0')} · Projet C-${String(index).padStart(2,'0')}`}));
  const back=()=>fireEvent.click(screen.getByRole('link',{name:'Projets'}));
  for(let index=1;index<=6;index++){open(index);back();}
  open(1);back();open(7);back();
  expect(container.querySelector('[data-workspace-view="project:p1"]')).toBeTruthy();
  expect(container.querySelector('[data-workspace-view="project:p2"]')).toBeNull();
  expect(container.querySelectorAll('[data-workspace-view^="project:"]')).toHaveLength(6);
});
function setup(ProjectPanel = ProjectDraft) {
  return render(<WorkspaceShell rows={rows} reload={vi.fn().mockResolvedValue(undefined)} ProjectPanel={ProjectPanel}
    MailPanel={() => <section aria-label="Mails de test">Liste des mails</section>} CreatePanel={() => null} SagePanel={() => null} />);
}

it('renvoie l’ancienne rubrique Thunderbird vers les réglages de la liaison',async()=>{
  window.history.replaceState(null,'','/app/imports?connection=thunderbird');setup();
  expect(screen.queryByTestId('thunderbird-activity')).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'Ouvrir les réglages Thunderbird'}));
  expect(window.location.pathname+window.location.search).toBe('/app/settings?settings=mail');
  expect(await screen.findByRole('heading',{name:'Mails et Thunderbird'})).toBeTruthy();
  expect(screen.getByText('Installer ou mettre à jour la liaison Thunderbird')).toBeTruthy();
});

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
    expect((screen.getByRole("combobox",{name:"Thème"}) as HTMLSelectElement).value).toBe("dark");
    const settings = within(screen.getByRole("navigation",{name:"Réglages"}));
    fireEvent.click(settings.getByRole("button",{name:"Mon accès"}));
    expect(screen.getByRole("link",{name:"Ouvrir mon accès"}).getAttribute("href")).toBe("/chat#reglages");
    fireEvent.click(settings.getByRole("button",{name:"Mises à jour"}));
    expect(screen.getByRole("link",{name:"Ouvrir mises à jour"}).getAttribute("href")).toBe("/chat#reglages");
    expect(localStorage.getItem("agent-ui-theme")).toBe("light");
  } finally {
    delete document.body.dataset.kiaraDesktop;
    delete document.body.dataset.kiaraWindows;
  }
});

it('garde le même menu pour chaque réglage Windows et réutilise le panneau du relais',()=>{
  window.history.replaceState(null,'','/app/settings');
  Object.assign(document.body.dataset,{kiaraDesktop:'true',kiaraWindows:'true',kiaraDeviceSettings:'true',kiaraInlineSettings:'true'});
  try {
    setup();
    const menu=screen.getByRole('navigation',{name:'Réglages'});
    const panels=['Notifications','Mon accès','Conversation vocale','Dictée','Mises à jour','Connexion au serveur','API locale et intégrations'];
    let embedded: HTMLElement|undefined;
    for(const button of within(menu).getAllByRole('button')){
      const title=button.textContent!;
      fireEvent.click(button);
      expect(screen.getByRole('navigation',{name:'Réglages'})).toBe(menu);
      expect(button.getAttribute('aria-pressed')).toBe('true');
      if(panels.includes(title)){
        const frame=within(screen.getByRole('main')).getByTitle(title);
        expect(frame.getAttribute('src')).toBe('/device-settings');
        embedded??=frame;
        expect(frame).toBe(embedded);
      }
    }
  } finally {
    for(const name of ['kiaraDesktop','kiaraWindows','kiaraDeviceSettings','kiaraInlineSettings'])delete document.body.dataset[name];
  }
});

it('ouvre chaque réglage appareil à droite du même menu, à une URL dédiée',()=>{
  window.history.replaceState(null,'','/app/settings');
  const flags={kiaraDesktop:'true',kiaraWindows:'true',kiaraDeviceSettings:'true',kiaraInlineSettings:'true',kiaraNativeSettings:'true'};
  Object.assign(document.body.dataset,flags);
  try {
    setup();
    const menu=screen.getByRole('navigation',{name:'Réglages'});
    const entries=[
      ['Conversation vocale','vocal'], ['Dictée','dictee'], ['Connexion au serveur','connexion'],
      ['Mises à jour','mises-a-jour'], ['API locale et intégrations','api-locale'],
    ];
    for(const [title,section] of entries){
      const link=within(menu).getByRole('button',{name:title});
      fireEvent.click(link);
      const frame=screen.getByTitle(title);
      expect(screen.getByRole('navigation',{name:'Réglages'})).toBe(menu);
      expect(link.getAttribute('aria-pressed')).toBe('true');
      expect(frame.getAttribute('src')).toBe('/device-settings?section='+section);
      expect(frame.closest('[hidden]')).toBeNull();
      expect(window.location.search).toBe('?settings='+section);
    }
    expect(screen.getByTitle('Conversation vocale').closest('[hidden]')).toBeTruthy();
  } finally {
    for(const name of Object.keys(flags))delete document.body.dataset[name];
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
      "Conversations","Projets","Notes","Mails","Réunions","Activité"
    ]);
    fireEvent.click(within(menu).getByRole("link",{name:"Activité"}));
    expect(screen.getByRole("heading",{name:"À traiter"})).toBeTruthy();
    fireEvent.click(screen.getByRole("link",{name:"Kiara · Portefeuille des projets"}));
    expect(window.location.pathname).toBe("/app/projets");
    fireEvent.click(screen.getByRole("button",{name:"Accès rapide"}));
    expect(screen.getByLabelText('Ouvrir une rubrique, un projet ou un élément')).toBeTruthy();
    expect(within(screen.getByLabelText('Rubriques',{selector:'section'})).queryByRole("button",{name:/^Ouvrir la rubrique Accueil/})).toBeNull();
  } finally {
    delete document.body.dataset.kiaraDesktop;
    delete document.body.dataset.kiaraWindows;
  }
});

it("replie la barre Kiara avec Ctrl+B et partage l'état avec le client",()=>{
  vi.stubGlobal('matchMedia',(query:string)=>({matches:false,addEventListener:()=>{},removeEventListener:()=>{}}));
  document.body.dataset.kiaraDesktop="true";
  document.body.dataset.kiaraWindows="true";
  try{
    setup();
    const shell=document.querySelector<HTMLElement>('.workspace-shell')!;
    const menu=screen.getByRole("navigation",{name:"Grandes rubriques"});
    expect(within(menu).getAllByRole("link").map(link=>link.textContent)).toEqual([
      "Conversations","Projets","Notes","Mails","Réunions","Activité"
    ]);
    const sidebar=screen.getByRole("complementary",{name:"Menu principal"});
    expect(within(sidebar).getByRole("link",{name:"Réglages"})).toBeTruthy();
    expect(within(sidebar).getByText("Serveur Kiara")).toBeTruthy();
    expect(shell.getAttribute('data-sidebar-collapsed')).toBe('false');
    fireEvent.click(screen.getByRole("button",{name:"Afficher ou masquer la navigation"}));
    expect(shell.classList.contains('workspace-sidebar-collapsed')).toBe(true);
    expect(shell.getAttribute('data-sidebar-collapsed')).toBe('true');
    expect(localStorage.getItem("fred-sidebar-collapsed")).toBe("true");
    fireEvent.keyDown(window,{key:'b',ctrlKey:true});
    expect(shell.getAttribute('data-sidebar-collapsed')).toBe('false');
    expect(localStorage.getItem("fred-sidebar-collapsed")).toBe("false");
    const search=screen.getByRole('textbox',{name:'Rechercher un projet'});
    fireEvent.keyDown(search,{key:'b',ctrlKey:true});
    expect(shell.getAttribute('data-sidebar-collapsed')).toBe('false');
    localStorage.setItem("fred-sidebar-collapsed","true");
    setup();
    expect(document.querySelectorAll('.workspace-shell')[1].getAttribute('data-sidebar-collapsed')).toBe('true');
  }finally{
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
  fireEvent.click(screen.getByRole("button", { name: "Archives de projet" }));
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
  fireEvent.click(screen.getByRole("button", { name: "Archives de projet" }));
  fireEvent.change(container.querySelector('input[type="file"][accept="application/json,.json"]')!, { target: { files: [file] } });
  expect(getActivitySnapshot()?.labels).toContain("Importation d’une archive de projet…");
  await act(async () => { failRead(new Error("Lecture locale interrompue")); });
  await screen.findByText("Import impossible : Lecture locale interrompue");
  expect(getActivitySnapshot()?.labels ?? []).not.toContain("Importation d’une archive de projet…");
  expect(importJson).not.toHaveBeenCalled(); expect(reload).not.toHaveBeenCalled();
  expect((screen.getByRole("button", { name: "Importer une archive JSON" }) as HTMLButtonElement).disabled).toBe(false);
});

it('protège la navigation Nouvelle séance depuis Sources, puis transmet le projet ERP au parcours existant',async()=>{
  window.history.replaceState(null,'','/app/sources');
  vi.spyOn(fusionSources,'list').mockResolvedValue({items:[],total:0,offset:0,limit:25,has_next:false,labels:[]});
  const confirm=vi.spyOn(window,'confirm').mockReturnValue(false);
  setup();fireEvent.change(await screen.findByLabelText('Projet',{}, {timeout:5000}),{target:{value:'erp-b'}});
  const draft=document.createElement('div');draft.dataset.workspaceDirty='true';document.body.append(draft);
  try{
    fireEvent.click(screen.getByRole('button',{name:'Nouvelle séance'}));
    expect(confirm).toHaveBeenCalled();expect(window.location.pathname).toBe('/app/sources');
    expect(screen.queryByRole('form',{name:'Préparation demandée depuis Sources'})).toBeNull();
    confirm.mockReturnValue(true);fireEvent.click(screen.getByRole('button',{name:'Nouvelle séance'}));
    expect(window.location.pathname).toBe('/app/meetings');
    expect((await screen.findByLabelText('Projet proposé')).textContent).toBe('erp-b');
    fireEvent.click(screen.getByRole('button',{name:'Rechercher dans Kiara'}));
    fireEvent.click(screen.getByRole('button',{name:'Toutes les sources'}));
    const library=screen.getByRole('region',{name:'Bibliothèque des sources'});
    fireEvent.change(within(library).getByLabelText('Projet'),{target:{value:''}});
    fireEvent.click(within(library).getByRole('button',{name:'Nouvelle séance'}));
    expect(window.location.pathname).toBe('/app/meetings');
    expect(screen.getByLabelText('Projet proposé').textContent).toBe('À rattacher');
  }finally{draft.remove();}
});

it('conserve le même retour protégé dans Préparation et rétablit le fil d’Ariane hors Studio',async()=>{
  window.history.replaceState(null,'','/app/meetings');const {container}=setup();
  expect(screen.getByRole('navigation',{name:'Fil d’Ariane'}).closest('.meeting-preparation')).toBeNull();
  fireEvent.click(await screen.findByRole('button',{name:'Ouvrir le Studio de test'}));
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
  fireEvent.click(screen.getByRole('button',{name:'Rechercher dans Kiara'}));
  fireEvent.click(screen.getByRole('button',{name:'Toutes les sources'}));
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
function chooseSetting(name:string) {
  fireEvent.click(screen.getByRole("button",{name}));
}

it('ne monte les réglages qu’à leur ouverture et conserve leurs brouillons', async () => {
  window.history.replaceState(null, '', '/app/settings');
  setup();
  const general = await screen.findByLabelText('Brouillon général de test') as HTMLInputElement;
  expect(screen.queryByLabelText('Brouillon mails de test')).toBeNull();
  expect(screen.queryByLabelText('Brouillon recherche de test')).toBeNull();
  expect(screen.queryByText('Maintenance de test')).toBeNull();
  fireEvent.change(general, {target:{value:'À conserver'}});
  fireEvent.click(screen.getByRole('button',{name:'Mails et Thunderbird'}));
  const mail = await screen.findByLabelText('Brouillon mails de test') as HTMLInputElement;
  fireEvent.change(mail, {target:{value:'Autre brouillon'}});
  chooseSetting('Sauvegarde du service Projets');
  await screen.findByText('Maintenance de test');
  fireEvent.click(screen.getByRole('button',{name:'Assistant IA'}));
  expect((screen.getByLabelText('Brouillon général de test') as HTMLInputElement).value).toBe('À conserver');
  fireEvent.click(screen.getByRole('button',{name:'Mails et Thunderbird'}));
  expect((screen.getByLabelText('Brouillon mails de test') as HTMLInputElement).value).toBe('Autre brouillon');
  expect(screen.queryByLabelText('Brouillon recherche de test')).toBeNull();
});

it.each(['/app/settings?settings=preparation', '/app/preparation'])('conserve les réglages de réunion non enregistrés depuis %s', async (path) => {
  window.history.replaceState(null, '', path);
  vi.spyOn(fusionInsights,'personal').mockResolvedValue({live_transcription_enabled:false,
    proactive_enabled:false,auto_enhancement_enabled:false,mode:'network'});
  vi.spyOn(window,'confirm').mockReturnValue(true);
  setup();
  const direct=await screen.findByLabelText('Transcrire mes réunions en direct') as HTMLInputElement;
  fireEvent.click(direct);expect(direct.checked).toBe(true);
  fireEvent.click(screen.getByRole('link',{name:'Mails'}));
  fireEvent.click(screen.getByRole('link',{name:'Réglages'}));
  expect((await screen.findByLabelText('Transcrire mes réunions en direct') as HTMLInputElement).checked).toBe(true);
  fireEvent.click(screen.getByRole('button',{name:'Apparence et lecture'}));
  chooseSetting('Réunions et transcription');
  expect((await screen.findByLabelText('Transcrire mes réunions en direct') as HTMLInputElement).checked).toBe(true);
  fireEvent.click(screen.getByRole('link',{name:'Mails'}));
  fireEvent.click(screen.getByRole('link',{name:'Réglages'}));
  expect((await screen.findByLabelText('Transcrire mes réunions en direct') as HTMLInputElement).checked).toBe(true);
});

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
  setup();expect(read).not.toHaveBeenCalled();chooseSetting("Modèles de documents");
  await screen.findByLabelText('Modifier les recherches des trames',{}, {timeout:3000});
  await waitFor(()=>expect(screen.getByRole('button',{name:'Comparer avec les réglages enregistrés'}).matches(':disabled')).toBe(false));
  fireEvent.change(screen.getAllByLabelText('Libellé')[0],{target:{value:'Brouillon commun'}});
  fireEvent.click(screen.getByRole('button',{name:'Apparence et lecture'}));expect(screen.getByRole('region',{name:'Réglages documentaires'})).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'Apparence et lecture'}));expect(screen.queryByRole('region',{name:'Réglages documentaires'})).toBeNull();
  chooseSetting("Modèles de documents");expect((screen.getAllByLabelText('Libellé')[0] as HTMLInputElement).value).toBe('Brouillon commun');
  expect(read).toHaveBeenCalledTimes(1);expect(confirm).toHaveBeenCalledTimes(2);
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer les réglages'}));fireEvent.click(screen.getByRole('link',{name:'Mails'}));
  expect(window.location.pathname).toBe('/app/settings');expect(screen.getByText(/Réglages documentaires en cours/)).toBeTruthy();
  finish({...preferences,revision:3,items:preferences.items.map((item,index)=>({...item,label:index?'Trame '+(index+1):'Brouillon commun'}))});
  await screen.findByText('Réglages enregistrés · version 3.');
});

it("charge le catalogue seulement à l’ouverture de Livrables et conserve le brouillon entre rubriques",async()=>{
  window.history.replaceState(null,"","/app/settings");
  const types=vi.spyOn(deliverableApi,"types").mockResolvedValue({items:[],total:0,offset:0,limit:25,can_manage:true});
  setup();expect(types).not.toHaveBeenCalled();chooseSetting("Modèles de livrables");
  fireEvent.click(await screen.findByRole("button",{name:"Créer un type de livrable"},{timeout:3000}));
  fireEvent.change(screen.getByLabelText("Libellé du type de livrable"),{target:{value:"Brouillon conservé"}});
  fireEvent.click(screen.getByRole("button",{name:"Apparence et lecture"}));chooseSetting("Modèles de livrables");
  expect((screen.getByLabelText("Libellé du type de livrable") as HTMLInputElement).value).toBe("Brouillon conservé");
});

it("ouvre les référentiels depuis Réglages et charge leur liste à la demande", async () => {
  window.history.replaceState(null,"","/app/settings");
  vi.spyOn(identityApi,"session").mockResolvedValue({operator:{id:"local",role:"owner",can_edit:true,can_administer:true,project_ids:null}});
  const references=vi.spyOn(identityApi,"references").mockResolvedValue({items:[],total:0,offset:0,limit:50});
  setup();expect(references).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button",{name:"Clients et équipe"}));
  expect(await screen.findByRole("region",{name:"Clients, équipe et catégories"},{timeout:5000})).toBeTruthy();
  await waitFor(()=>expect(references).toHaveBeenCalledWith("client",expect.objectContaining({offset:0})));
  fireEvent.click(screen.getByRole("button",{name:"Ajouter un client"}));
  fireEvent.change(screen.getByLabelText("Libellé"),{target:{value:"Brouillon conservé"}});
  fireEvent.click(screen.getByRole("button",{name:"Apparence et lecture"}));
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
  await waitFor(() => expect(window.location.pathname).toBe("/app/projets/erp-a/reunions"));
  await waitFor(() => expect(screen.getByRole("region", {name: "Projet erp-a"})).toBeTruthy());
  expect(screen.getByText("Rubrique projet : reviews")).toBeTruthy();
});

it("ouvre une vue globale sans choisir ni monter implicitement le premier projet", async () => {
  window.history.replaceState(null, "", "/app/meetings");
  const project = vi.fn(ProjectDraft);
  setup(project);
  expect(await screen.findByRole("region", {name: "Réunions globales de test"})).toBeTruthy();
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

it("conserve deux brouillons distincts pendant vingt changements de destination", () => {
  window.history.replaceState(null, "", "/app/projects/erp-a/pilotage");
  setup();
  fireEvent.change(screen.getByRole("textbox", {name: "Brouillon erp-a"}), {target: {value: "Texte projet A"}});
  fireEvent.click(screen.getByRole("link", {name: /^Projets$/}));
  fireEvent.click(screen.getByRole("button", {name: "B-200 · Projet B-200"}));
  fireEvent.change(screen.getByRole("textbox", {name: "Brouillon erp-b"}), {target: {value: "Texte projet B"}});
  for (let i = 0; i < 20; i++) {
    fireEvent.click(screen.getByRole("link", {name: "Mails"}));
    fireEvent.click(screen.getByRole("link", {name: /^Projets$/}));
    const first = i % 2 === 0;
    fireEvent.click(screen.getByRole("button", {name: first ? "A-100 · Projet A-100" : "B-200 · Projet B-200"}));
    expect((screen.getByRole("textbox", {name: first ? "Brouillon erp-a" : "Brouillon erp-b"}) as HTMLInputElement).value)
      .toBe(first ? "Texte projet A" : "Texte projet B");
  }
});

it("conserve les vraies saisies CDC de deux projets en changeant de rubrique", () => {
  const item: CdcItem = {id:"exigence", title:"Titre initial", human_id:"EXI-001", kind:"requirement",
    source_quote:"Exigence fictive", physical_page:1, modality:"mandatory", priority:"unclassified",
    confidence:1, estimated_hours:0, knowledge_status:"candidate", evidence:[]};
  const items = [item];
  function ProjectReview({projectId}: ProjectWorkspaceProps) {
    return <section aria-label={`Revue CDC ${projectId}`}><CdcReviewPanel projectId={projectId}
      items={items} review={null} reviewKind="all" setReviewKind={()=>{}} reviewStatus="all"
      setReviewStatus={()=>{}} reviewQuery="" setReviewQuery={()=>{}} selected={new Set()}
      setSelected={()=>{}} refresh={()=>{}} reloadReview={()=>{}} /></section>;
  }
  window.history.replaceState(null, "", "/app/projects/erp-a/cdc");
  setup(ProjectReview);
  const sidebar = screen.getByRole("complementary", {name:"Menu principal"});
  const links = within(sidebar).getAllByRole("link").map(link => link.textContent);
  const title = (project: string) => within(screen.getByRole("region", {name:`Revue CDC ${project}`})).getByLabelText("Titre") as HTMLInputElement;
  fireEvent.change(title("erp-a"), {target:{value:"Exigence modifiée A"}});
  fireEvent.click(screen.getByRole("link", {name:"Projets"}));
  fireEvent.click(screen.getByRole("button", {name:"B-200 · Projet B-200"}));
  fireEvent.change(title("erp-b"), {target:{value:"Exigence modifiée B"}});
  for (let i=0; i<4; i++) {
    fireEvent.click(screen.getByRole("link", {name:"Mails"}));
    expect(within(sidebar).getAllByRole("link").map(link => link.textContent)).toEqual(links);
    fireEvent.click(screen.getByRole("link", {name:"Projets"}));
    const a = i % 2 === 0;
    fireEvent.click(screen.getByRole("button", {name:a ? "A-100 · Projet A-100" : "B-200 · Projet B-200"}));
    expect(title(a ? "erp-a" : "erp-b").value).toBe(a ? "Exigence modifiée A" : "Exigence modifiée B");
    expect(within(sidebar).getAllByRole("link").map(link => link.textContent)).toEqual(links);
  }
});

it("désactive le polling de la vue des traitements lorsqu'elle est cachée", async () => {
  window.history.replaceState(null, "", "/app/jobs");
  setup();
  const jobs = await screen.findByRole("region", {name: "Traitements de test"});
  expect(jobs.getAttribute("data-active")).toBe("true");
  fireEvent.click(screen.getByRole("link", {name: "Mails"}));
  expect(jobs.getAttribute("data-active")).toBe("false");
  expect(jobs.closest("[data-workspace-view]")?.hasAttribute("hidden")).toBe(true);
  window.history.pushState(null,"","/app/jobs");fireEvent.popState(window);
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
it('rend visibles les statistiques et les réglages de transcription',async()=>{
  setup();
  expect(screen.queryByRole('link',{name:'Statistiques'})).toBeNull();
  fireEvent.click(screen.getByRole('link',{name:'Réglages'}));
  expect(within(screen.getByRole('group',{name:'Espace de travail'})).getByRole('button',{name:'Réunions et transcription'})).toBeTruthy();
  fireEvent.click(screen.getByRole('link',{name:'Activité'}));
  expect(screen.getByRole('button',{name:'Statistiques'})).toBeTruthy();
});

it('réserve les réglages aux paramètres et garde les connexions accessibles',()=>{
  vi.spyOn(fusionSources,'list').mockResolvedValue({items:[],total:0,offset:0,limit:25,has_next:false,labels:[]});
  setup();
  const sidebar=screen.getByRole('complementary',{name:'Menu principal'});
  for(const label of ['Sources','Informations','Suivi des analyses','Connexions et imports']){
    expect(within(sidebar).queryByRole('link',{name:label})).toBeNull();
  }
  fireEvent.click(within(sidebar).getByRole('link',{name:'Réglages'}));
  const tabs=screen.getByRole('navigation',{name:'Réglages'});
  for(const label of ['Sources','Informations','Suivi des analyses'])expect(within(tabs).queryByRole('button',{name:label})).toBeNull();
  fireEvent.click(within(tabs).getByRole('button',{name:'Connexions et imports'}));
  expect(window.location.pathname).toBe('/app/imports');
  expect(within(screen.getByRole('navigation',{name:'Réglages'})).getByRole('button',{name:'Connexions et imports'}).getAttribute('aria-pressed')).toBe('true');
  fireEvent.click(within(screen.getByRole('navigation',{name:'Réglages'})).getByRole('button',{name:'Assistant IA'}));
  expect(window.location.pathname).toBe('/app/settings');
  expect(screen.getByRole('button',{name:'Assistant IA'}).getAttribute('aria-pressed')).toBe('true');
});

it.each([['sources','Sources'],['knowledge','Connaissance globale de test'],['jobs','Traitements de test']])('conserve le lien direct vers %s hors des réglages', async(page,label)=>{
  vi.spyOn(fusionSources,'list').mockResolvedValue({items:[],total:0,offset:0,limit:25,has_next:false,labels:[]});
  window.history.replaceState(null,'','/app/'+page);
  setup();
  expect(screen.queryByRole('navigation',{name:'Réglages'})).toBeNull();
  if(page==='sources')expect(await screen.findByRole('heading',{name:label})).toBeTruthy();
  else expect(await screen.findByRole('region',{name:label})).toBeTruthy();
});
it('isole une erreur de rubrique sans masquer la navigation ni les autres brouillons', async()=>{
  vi.spyOn(console,'error').mockImplementation(()=>{});
  let fail=true;
  function ProjectWithFailure(props:ProjectWorkspaceProps){
    if(props.projectId==='erp-b'&&fail)throw new Error('erreur de recette');
    return <ProjectDraft {...props}/>;
  }
  window.history.replaceState(null,'','/app/projets');
  setup(ProjectWithFailure);
  fireEvent.click(screen.getByRole('button',{name:'A-100 · Projet A-100'}));
  fireEvent.change(screen.getByRole('textbox',{name:'Brouillon erp-a'}),{target:{value:'À conserver'}});
  fireEvent.click(screen.getByRole('link',{name:'Projets'}));
  fireEvent.click(screen.getByRole('button',{name:'B-200 · Projet B-200'}));
  expect(screen.getByText('Cette rubrique ne peut pas être affichée.')).toBeTruthy();
  expect(screen.getByRole('navigation',{name:'Grandes rubriques'})).toBeTruthy();
  fail=false;fireEvent.click(screen.getByRole('button',{name:'Réessayer'}));
  expect(screen.getByRole('textbox',{name:'Brouillon erp-b'})).toBeTruthy();
  fireEvent.click(screen.getByRole('link',{name:'Projets'}));
  fireEvent.click(screen.getByRole('button',{name:'A-100 · Projet A-100'}));
  expect((screen.getByRole('textbox',{name:'Brouillon erp-a'}) as HTMLInputElement).value).toBe('À conserver');
});
it('garde les favoris dans Projets sans modifier la barre de navigation',()=>{
  window.history.replaceState(null,'','/app/projets');setup();
  const sidebar=screen.getByRole('complementary',{name:'Menu principal'});
  const labels=within(sidebar).getAllByRole('link').map(link=>link.textContent);
  fireEvent.click(screen.getByRole('button',{name:'Ajouter A-100 aux favoris'}));
  expect(within(sidebar).getAllByRole('link').map(link=>link.textContent)).toEqual(labels);
  expect(within(sidebar).queryByText('Projets favoris')).toBeNull();
  fireEvent.click(screen.getByText('Projets favoris'));
  fireEvent.click(within(screen.getByText('Projets favoris').closest('details')!).getByRole('button',{name:/A-100.*Projet A-100/}));
  expect(window.location.pathname).toContain('/app/projets/erp-a');
});
it('ouvre la recherche depuis les documents sans perdre le brouillon du projet',async()=>{
  window.history.replaceState(null,'','/app/projets');setup();
  fireEvent.click(screen.getByRole('button',{name:'A-100 · Projet A-100'}));
  fireEvent.change(screen.getByRole('textbox',{name:'Brouillon erp-a'}),{target:{value:'Brouillon préservé'}});
  fireEvent.click(screen.getByRole('button',{name:'Documents du projet'}));
  fireEvent.click(screen.getByRole('button',{name:'Rechercher dans tous les projets'}));
  expect(window.location.pathname).toBe('/app/search');
  fireEvent.click(screen.getByRole('link',{name:'Projets'}));
  fireEvent.click(screen.getByRole('button',{name:'A-100 · Projet A-100'}));
  expect((screen.getByRole('textbox',{name:'Brouillon erp-a'}) as HTMLInputElement).value).toBe('Brouillon préservé');
});
it('ouvre les informations depuis la recherche et les traitements depuis Activité',async()=>{
  setup();
  fireEvent.click(screen.getByRole('button',{name:'Rechercher dans Kiara'}));
  fireEvent.click(screen.getByRole('button',{name:'Toutes les informations'}));
  expect(window.location.pathname).toBe('/app/knowledge');
  expect(await screen.findByRole('region',{name:'Connaissance globale de test'})).toBeTruthy();
  fireEvent.click(screen.getByRole('link',{name:'Activité'}));
  expect(window.location.pathname).toBe('/app/activite');
  fireEvent.click(screen.getByRole('button',{name:'Analyses'}));
  expect(window.location.search).toBe('?view=analyses');
  expect(await screen.findByRole('region',{name:'Traitements de test'})).toBeTruthy();
});
it('protège aussi les modifications non enregistrées avant de quitter le portail web',()=>{
  document.body.dataset.kiaraWebConversations='true';
  window.history.replaceState(null,'','/kiara/app/settings');
  try {
    setup();
    const settings=within(screen.getByRole('navigation',{name:'Réglages'}));
    expect(settings.queryByRole('button',{name:'Mises à jour'})).toBeNull();
    fireEvent.click(settings.getByRole('button',{name:'Mon accès'}));
    expect(screen.getByTitle('Mon accès').getAttribute('src')).toBe('/kiara/app/device-settings');
    const dirty=document.createElement('div');dirty.dataset.workspaceDirty='true';document.body.append(dirty);
    try {
      const notifications=screen.getByRole('link',{name:'Notifications'});
      expect(notifications.getAttribute('href')).toBe('/kiara/app/conversations#notifications');
      expect(fireEvent.click(notifications)).toBe(false);
      expect(screen.getByText('Enregistrez ou fermez la modification en cours avant de revenir à Conversations.')).toBeTruthy();
    } finally {dirty.remove();}
  } finally {delete document.body.dataset.kiaraWebConversations;}
});
