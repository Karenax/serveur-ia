import {afterEach, beforeEach, expect, it, vi} from "vitest";
import {act, cleanup, fireEvent, render, screen, waitFor, within} from "@testing-library/react";
import {MailApp} from "../App";
import {api, type PortfolioRow} from "../lib/api";

const triageHook=vi.hoisted(()=>vi.fn(()=>({start:vi.fn(),cancel:vi.fn()})));
vi.mock("../hooks/useDurableMailTriage",()=>({useDurableMailTriage:triageHook}));
const project = {id:"erp-a",code:"A0806",title:"Projet A",brain_project_id:"brain-a",brain_code:"A0806"} as PortfolioRow;
const entries = [1,2].map(n=>({proposal_id:`proposal-${n}`,source_id:`source-${n}`,sender:"client@example.com",subject:`Mail ${n}`,
  received_at:null,excerpt:"Un échange",target_project_id:"divers",target_code:"DIVERS",target_name:"Divers",confidence:.4,reason:"À vérifier"}));
const page = {rows:entries,total:2,has_next:false,offset:0,limit:200};
beforeEach(()=>{
  vi.spyOn(api,"session").mockResolvedValue({operator:{role:'owner',project_ids:null}});
  vi.spyOn(api,"mailProjectUsage").mockResolvedValue({projects:[]});
  vi.spyOn(api,"portfolio").mockResolvedValue([project]);
  vi.spyOn(api,"brainProjects").mockResolvedValue([{id:"brain-a",code:"A0806",name:"Projet A"},{id:"divers",code:"DIVERS",name:"Divers"}]);
  vi.spyOn(api,"pendingMailPage").mockResolvedValue(page);
  vi.spyOn(api,"brainTriageStats").mockResolvedValue({pending_sources:2,new_sources:0,queued:2,divers_project_id:"divers",divers_count:0});
  vi.spyOn(api,"brainAutoStatus").mockResolvedValue(null);
  vi.spyOn(api,"brainSourceDetail").mockImplementation(async(id)=>({id,artifacts:[{kind:"body_text",text:`Corps de ${id}`}]}));
});
afterEach(()=>{cleanup();vi.restoreAllMocks();});

it("transmet la visibilité de Mails au suivi sans désactiver les droits",async()=>{
  const rows=[project];
  const view=render(<MailApp rows={rows} active/>);
  await screen.findByRole('heading',{name:'Mail 1'},{timeout:3000});
  await waitFor(()=>expect(triageHook).toHaveBeenLastCalledWith(expect.objectContaining({enabled:true,active:true})));
  view.rerender(<MailApp rows={rows} active={false}/>);
  expect(triageHook).toHaveBeenLastCalledWith(expect.objectContaining({enabled:true,active:false}));
  view.rerender(<MailApp rows={rows} active/>);
  expect(triageHook).toHaveBeenLastCalledWith(expect.objectContaining({enabled:true,active:true}));
});

it("ne recharge pas les mails cachés quand le portefeuille change et conserve la recherche au retour",async()=>{
  const view=render(<MailApp rows={[project]} active/>);
  await screen.findByRole('heading',{name:'Mail 1'});
  const search=screen.getByRole('textbox',{name:'Rechercher dans tous les mails du dossier'}) as HTMLInputElement;
  fireEvent.change(search,{target:{value:'client fictif'}});
  await waitFor(()=>expect(api.pendingMailPage).toHaveBeenCalledWith(0,'client fictif','newest'),{timeout:3000});
  const calls=vi.mocked(api.pendingMailPage).mock.calls.length;
  view.rerender(<MailApp rows={[{...project,title:'Projet actualisé'}]} active={false}/>);
  view.rerender(<MailApp rows={[{...project,title:'Projet actualisé encore'}]} active={false}/>);
  await act(async()=>{await new Promise(resolve=>setTimeout(resolve,350));});
  expect(api.pendingMailPage).toHaveBeenCalledTimes(calls);
  expect(search.value).toBe('client fictif');
  view.rerender(<MailApp rows={[project]} active/>);
  await waitFor(()=>expect(api.pendingMailPage).toHaveBeenCalledTimes(calls+1));
  expect(search.value).toBe('client fictif');
});

it("ignore une réponse de mails arrivée après avoir quitté la rubrique",async()=>{
  const view=render(<MailApp rows={[project]} active/>);
  await screen.findByRole('heading',{name:'Mail 1'});
  let resolveOld!:(value:typeof page)=>void;
  vi.mocked(api.pendingMailPage).mockImplementationOnce(()=>new Promise(resolve=>{resolveOld=resolve;}));
  const calls=vi.mocked(api.pendingMailPage).mock.calls.length;
  view.rerender(<MailApp rows={[{...project,title:'Actualisé'}]} active/>);
  await waitFor(()=>expect(api.pendingMailPage).toHaveBeenCalledTimes(calls+1));
  view.rerender(<MailApp rows={[project]} active={false}/>);
  await act(async()=>{resolveOld({...page,rows:[{...entries[0],subject:'Mail périmé'}]});});
  expect(screen.getByRole('heading',{name:'Mail 1'})).toBeTruthy();
  expect(screen.queryByRole('heading',{name:'Mail périmé'})).toBeNull();
  view.rerender(<MailApp rows={[project]} active/>);
  await waitFor(()=>expect(api.pendingMailPage).toHaveBeenCalledTimes(calls+2));
});

it("ne lance pas les lectures de mails si la session répond après le départ",async()=>{
  let resolveSession!:(value:Awaited<ReturnType<typeof api.session>>)=>void;
  vi.mocked(api.session).mockImplementationOnce(()=>new Promise(resolve=>{resolveSession=resolve;}));
  const rows=[project];
  const view=render(<MailApp rows={rows} active/>);
  await waitFor(()=>expect(api.session).toHaveBeenCalled());
  view.rerender(<MailApp rows={rows} active={false}/>);
  await act(async()=>{resolveSession({operator:{role:'owner',project_ids:null}});});
  expect(api.pendingMailPage).not.toHaveBeenCalled();
  expect(api.brainTriageStats).not.toHaveBeenCalled();
  expect(api.brainProjects).not.toHaveBeenCalled();
  view.rerender(<MailApp rows={rows} active/>);
  expect(await screen.findByRole('heading',{name:'Mail 1'})).toBeTruthy();
});

it("ouvre les mails classés en lecture seule pour un accès limité aux projets",async()=>{
  vi.mocked(api.session).mockResolvedValue({operator:{role:'reader',project_ids:['erp-a']}});
  vi.spyOn(api,'classifiedMailPage').mockResolvedValue({rows:[{source_id:'source-1',project_id:'brain-a',author:'client@example.com',metadata:{subject:'Mail autorisé'}}],total:1,offset:0,limit:100,has_next:false});
  render(<MailApp rows={[project]}/>);
  expect(await screen.findByRole('heading',{name:'Mail autorisé'})).toBeTruthy();
  expect(await screen.findByText('Seuls les mails classés dans vos projets sont accessibles.')).toBeTruthy();
  expect(api.pendingMailPage).not.toHaveBeenCalled();
  expect(api.brainTriageStats).not.toHaveBeenCalled();
  expect(screen.queryByRole('button',{name:'Analyser les nouveaux mails'})).toBeNull();
  expect(screen.queryByRole('button',{name:'Enregistrer le classement'})).toBeNull();
});

it("permet au propriétaire de valider une proposition dans ses projets",async()=>{
  vi.mocked(api.session).mockResolvedValue({operator:{role:'owner',project_ids:['erp-a']}});
  vi.mocked(api.brainProjects).mockResolvedValue([{id:'brain-a',code:'A0806',name:'Projet A'}]);
  vi.mocked(api.pendingMailPage).mockResolvedValue({...page,rows:[{...entries[0],target_project_id:'brain-a',target_code:'A0806',confidence:.9}]});
  vi.spyOn(api,'brainTriageAccept').mockResolvedValue({});
  render(<MailApp rows={[project]}/>);
  await screen.findByRole('heading',{name:'Mail 1'});
  fireEvent.click(screen.getByRole('button',{name:'Classer et suivant'}));
  await waitFor(()=>expect(api.brainTriageAccept).toHaveBeenCalledWith('proposal-1'));
  expect(screen.queryByRole('button',{name:'Analyser les nouveaux mails'})).toBeNull();
  expect(api.brainTriageStats).not.toHaveBeenCalled();
});

async function dragMail(subject="Mail 1",multiple=false) {
  const data=new Map<string,string>();
  const transfer={setData:(key:string,value:string)=>data.set(key,value),getData:(key:string)=>data.get(key)||"",effectAllowed:"move"};
  const body=await screen.findByText(`Corps de source-${subject.split(" ")[1]}`);
  const handle=subject==="Mail 1" ? screen.getByRole("heading",{name:subject}).closest("header")! : body.closest("article")!;
  expect(handle.draggable).toBe(true);
  fireEvent.dragStart(handle,{dataTransfer:transfer});
  if(multiple)data.set("application/x-triage-mails",JSON.stringify(entries.map(entry=>entry.proposal_id)));
  fireEvent.drop(screen.getByRole("button",{name:/A0806.*Projet A/}),{dataTransfer:transfer});
}

it("retire le mail dès la validation, avant le rafraîchissement, et ignore une page périmée",async()=>{
  let finishRefresh!:(value:typeof page)=>void;
  vi.mocked(api.pendingMailPage).mockResolvedValueOnce(page).mockImplementation(()=>new Promise(resolve=>{finishRefresh=resolve;}));
  vi.spyOn(api,"brainTriageAssign").mockResolvedValue({});
  render(<MailApp rows={[project]}/>);
  // Cette attente prépare le lecteur et tolère l’ordonnancement des suites concurrentes.
  // Les assertions de classement et de rejet d’une page périmée gardent leurs délais.
  await screen.findByRole("heading",{name:"Mail 1"},{timeout:3_000});
  await dragMail();
  await waitFor(()=>expect(api.brainTriageAssign).toHaveBeenCalledWith("proposal-1","brain-a"));
  await waitFor(()=>expect(screen.queryByRole("heading",{name:"Mail 1"})).toBeNull());
  expect(await screen.findByRole("heading",{name:"Mail 2"})).toBeTruthy();
  // A stalled catalogue refresh must not prevent classifying the next mail.
  await waitFor(()=>expect(screen.getByRole("button",{name:"Classer et suivant"}).hasAttribute("disabled")).toBe(false));
  await dragMail("Mail 2");
  await waitFor(()=>expect(api.brainTriageAssign).toHaveBeenCalledWith("proposal-2","brain-a"));
  await act(async()=>{finishRefresh(page);});
  expect(screen.queryByRole("heading",{name:"Mail 1"})).toBeNull();
  expect(screen.queryByRole("heading",{name:"Mail 2"})).toBeNull();
});

it("garde le rejet si la file ne peut pas être actualisée ou renvoie encore le mail", async () => {
  vi.spyOn(window, "confirm").mockReturnValue(true);
  vi.spyOn(api, "brainTriageReject").mockResolvedValue({source_id:"source-1", status:"rejected"});
  vi.mocked(api.pendingMailPage).mockResolvedValueOnce(page)
    .mockRejectedValueOnce(new Error("Réseau indisponible"))
    .mockResolvedValue(page);
  render(<MailApp rows={[project]}/>);
  await screen.findByRole("heading", {name:"Mail 1"});
  fireEvent.click(screen.getByRole("button", {name:"Rejeter le mail"}));
  await screen.findByRole("heading", {name:"Mail 2"});
  expect(api.brainTriageReject).toHaveBeenCalledWith("proposal-1");
  expect(screen.queryByRole("heading", {name:"Mail 1"})).toBeNull();

  fireEvent.click(screen.getByRole("button", {name:"Actualiser la boîte"}));
  await waitFor(() => expect(api.pendingMailPage).toHaveBeenCalledTimes(3));
  expect(screen.getByRole("button", {name:"Mail précédent"}).hasAttribute("disabled")).toBe(true);
  expect(screen.queryByRole("heading", {name:"Mail 1"})).toBeNull();
});

it("un dépôt multiple retire les réussites et conserve les échecs sélectionnés",async()=>{
  vi.spyOn(api,"brainTriageAssign").mockResolvedValueOnce({}).mockRejectedValueOnce(new Error("Classement indisponible"));
  render(<MailApp rows={[project]}/>);
  await screen.findByRole("heading",{name:"Mail 1"});
  await dragMail("Mail 1",true);
  await screen.findByText(/1\/2 classé\(s\).*Classement indisponible/);
  expect(screen.queryByRole("heading",{name:"Mail 1"})).toBeNull();
  expect(await screen.findByRole("heading",{name:"Mail 2"})).toBeTruthy();
  expect(await screen.findByText("Corps de source-2")).toBeTruthy();
});

it("classe un dépôt groupé vers un projet probable sans créer de liaison ERP",async()=>{
  vi.mocked(api.brainProjects).mockResolvedValue([
    {id:"brain-a",code:"A0806",name:"Projet A"},
    {id:"brain-only",code:"B0810",name:"Projet sans ligne ERP"},
    {id:"divers",code:"DIVERS",name:"Divers"},
  ]);
  vi.mocked(api.pendingMailPage).mockResolvedValue({...page,rows:entries.map(entry=>({...entry,
    candidates:[{project_id:"brain-only",code:"B0810",score:.9}],
  }))});
  const ensure=vi.spyOn(api,"ensureBrainLink");
  const assign=vi.spyOn(api,"brainTriageAssign").mockResolvedValue({});
  render(<MailApp rows={[project]}/>);
  const header=(await screen.findByRole("heading",{name:"Mail 1"})).closest("header")!;
  await screen.findByText("Corps de source-1");
  const data=new Map<string,string>();
  const transfer={setData:(key:string,value:string)=>data.set(key,value),getData:(key:string)=>data.get(key)||"",effectAllowed:"move"};
  fireEvent.dragStart(header,{dataTransfer:transfer});
  data.set("application/x-triage-mails",JSON.stringify(entries.map(entry=>entry.proposal_id)));
  fireEvent.drop(screen.getByRole("button",{name:/B0810.*Projet sans ligne ERP/}),{dataTransfer:transfer});
  await waitFor(()=>expect(assign).toHaveBeenCalledWith("proposal-1","brain-only"));
  await waitFor(()=>expect(assign).toHaveBeenCalledWith("proposal-2","brain-only"));
  expect(ensure).not.toHaveBeenCalled();
});

it("actualise les cibles d’un mail ouvert quand le portefeuille change, sans fermer le lecteur",async()=>{
  const view=render(<MailApp rows={[project]}/>);
  await screen.findByRole("heading",{name:"Mail 1"});
  await screen.findByText("Corps de source-1");
  const added={id:"erp-b",code:"B0807",title:"Projet nouveau",brain_project_id:null,brain_code:null} as PortfolioRow;
  vi.mocked(api.portfolio).mockResolvedValue([project,added]);
  view.rerender(<MailApp rows={[project,added]}/>);
  await waitFor(()=>expect(within(screen.getByRole("combobox",{name:"Projet de classement"})).getByRole("option",{name:/B0807 — Projet nouveau/})).toBeTruthy());
  expect(screen.getByText("Corps de source-1")).toBeTruthy();
  const ensure=vi.spyOn(api,"ensureBrainLink").mockResolvedValue({linked:true,minipilot_code:"B0807",brain_project_id:"brain-b",brain_code:"B0807"});
  const assign=vi.spyOn(api,"brainTriageAssign").mockResolvedValue({});
  fireEvent.change(screen.getByRole("combobox",{name:"Projet de classement"}),{target:{value:"erp:erp-b"}});
  fireEvent.click(screen.getByRole("button",{name:"Classer et suivant"}));
  await waitFor(()=>expect(assign).toHaveBeenCalledWith("proposal-1","brain-b"));
  expect(ensure).toHaveBeenCalledWith("erp-b");
  await waitFor(()=>expect(screen.queryByRole("heading",{name:"Mail 1"})).toBeNull());
});

it("relie un projet nouvellement créé lors du dépôt et garde le mail si la liaison échoue",async()=>{
  const unlinked={...project,brain_project_id:null,brain_code:null};
  vi.mocked(api.portfolio).mockResolvedValue([unlinked]);
  vi.mocked(api.brainProjects).mockResolvedValue([{id:"divers",code:"DIVERS",name:"Divers"}]);
  const ensure=vi.spyOn(api,"ensureBrainLink").mockRejectedValueOnce(new Error("Moteur temporairement indisponible"))
    .mockResolvedValue({linked:true,minipilot_code:"A0806",brain_project_id:"brain-new",brain_code:"A0806"});
  const assign=vi.spyOn(api,"brainTriageAssign").mockResolvedValue({});
  render(<MailApp rows={[unlinked]}/>);
  await screen.findByRole("heading",{name:"Mail 1"});
  await dragMail();
  await screen.findByText("Moteur temporairement indisponible");
  await waitFor(()=>expect(screen.getByRole("button",{name:"Classer et suivant"}).hasAttribute("disabled")).toBe(false));
  expect(screen.getByRole("heading",{name:"Mail 1"})).toBeTruthy();
  expect(assign).not.toHaveBeenCalled();
  await dragMail();
  await waitFor(()=>expect(assign).toHaveBeenCalledWith("proposal-1","brain-new"));
  expect(ensure).toHaveBeenCalledTimes(2);
  await waitFor(()=>expect(screen.queryByRole("heading",{name:"Mail 1"})).toBeNull());
});

it("revient à une page valide après le classement du dernier mail de la dernière page",async()=>{
  let assigned=false;
  vi.mocked(api.pendingMailPage).mockImplementation(async(offset=0)=> offset===200
    ? {rows:assigned?[]:[entries[0]],total:assigned?200:201,offset:200,limit:200,has_next:false}
    : {rows:[entries[1]],total:assigned?200:201,offset:0,limit:200,has_next:!assigned});
  vi.spyOn(api,"brainTriageAssign").mockImplementation(async()=>{assigned=true;return {};});
  render(<MailApp rows={[project]}/>);
  await screen.findByRole("heading",{name:"Mail 2"});
  fireEvent.click(screen.getByRole("button",{name:"Mail suivant"}));
  await screen.findByRole("heading",{name:"Mail 1"});
  await dragMail();
  await screen.findByRole("heading",{name:"Mail 2"});
  expect(screen.getByText(/Mail 1 \/ 200/)).toBeTruthy();
  expect(screen.queryByRole("heading",{name:"Mail 1"})).toBeNull();
});

it("une erreur d’actualisation conserve le lecteur et les mails déjà chargés",async()=>{
  const view=render(<MailApp rows={[project]}/>);
  await screen.findByRole("heading",{name:"Mail 1"});
  await screen.findByText("Corps de source-1");
  vi.mocked(api.portfolio).mockRejectedValueOnce(new Error("Réseau temporairement indisponible"));
  view.rerender(<MailApp rows={[{...project,title:"Titre actualisé"}]}/>);
  await screen.findByText(/Actualisation impossible.*Réseau temporairement indisponible/);
  expect(screen.getByText("Corps de source-1")).toBeTruthy();
  expect(screen.getByRole("heading",{name:"Mail 1"})).toBeTruthy();
  expect(screen.getByRole("combobox",{name:"Projet de classement"})).toBeTruthy();
});

it("crée une destination depuis le lecteur puis classe seulement après confirmation",async()=>{
  const added={id:"erp-b",code:"B0809",title:"Nouveau projet",brain_project_id:null,brain_code:null} as PortfolioRow;
  const create=vi.spyOn(api,"createProject").mockImplementation(async()=>{
    vi.mocked(api.portfolio).mockResolvedValue([project,added]);
    return {id:added.id,code:added.code,title:added.title,status:"active"};
  });
  const ensure=vi.spyOn(api,"ensureBrainLink").mockResolvedValue({linked:true,minipilot_code:"B0809",brain_project_id:"brain-b",brain_code:"B0809"});
  const assign=vi.spyOn(api,"brainTriageAssign").mockResolvedValue({});
  const reload=vi.fn().mockResolvedValue(undefined);
  render(<MailApp rows={[project]} reloadProjects={reload}/>);
  await screen.findByRole("heading",{name:"Mail 1"});
  await screen.findByText("Corps de source-1");
  fireEvent.change(screen.getByRole("combobox",{name:"Projet de classement"}),{target:{value:"CREATE"}});
  fireEvent.change(screen.getByLabelText("Code du projet (facultatif)"),{target:{value:" B0809 "}});
  fireEvent.change(screen.getByLabelText("Nom du projet"),{target:{value:" Nouveau projet "}});
  fireEvent.submit(screen.getByRole("form",{name:"Créer un projet depuis ce mail"}));
  await waitFor(()=>expect(create).toHaveBeenCalledWith("B0809","Nouveau projet"));
  await waitFor(()=>expect((screen.getByRole("combobox",{name:"Projet de classement"}) as HTMLSelectElement).value).toBe("erp:erp-b"));
  expect(reload).toHaveBeenCalledTimes(1);
  expect(assign).not.toHaveBeenCalled();
  expect(ensure).not.toHaveBeenCalled();
  expect(screen.getByText("Corps de source-1")).toBeTruthy();
  expect(screen.getByRole("button",{name:/B0809.*Nouveau projet/})).toBeTruthy();
  fireEvent.click(screen.getByRole("button",{name:"Classer et suivant"}));
  await waitFor(()=>expect(assign).toHaveBeenCalledWith("proposal-1","brain-b"));
  await waitFor(()=>expect(screen.queryByRole("heading",{name:"Mail 1"})).toBeNull());
});

it("conserve le formulaire et le mail si la création du projet échoue",async()=>{
  vi.spyOn(api,"createProject").mockRejectedValue(new Error("Code déjà utilisé"));
  render(<MailApp rows={[project]}/>);
  await screen.findByRole("heading",{name:"Mail 1"});
  await screen.findByText("Corps de source-1");
  fireEvent.change(screen.getByRole("combobox",{name:"Projet de classement"}),{target:{value:"CREATE"}});
  fireEvent.change(screen.getByLabelText("Nom du projet"),{target:{value:"Projet"}});
  fireEvent.submit(screen.getByRole("form",{name:"Créer un projet depuis ce mail"}));
  await screen.findByText("Code déjà utilisé");
  expect((screen.getByLabelText("Nom du projet") as HTMLInputElement).value).toBe("Projet");
  expect(screen.getByText("Corps de source-1")).toBeTruthy();
});
