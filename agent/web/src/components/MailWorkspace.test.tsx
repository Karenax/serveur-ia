import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ComponentProps } from "react";
import { api } from "../lib/api";
import { MailWorkspace } from "./MailWorkspace";

beforeEach(()=>{vi.spyOn(window,"confirm").mockReturnValue(true);vi.spyOn(api, "mailProjectUsage").mockResolvedValue({projects:[]});});

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

it("importe des EML dans le projet choisi avec un accès limité", async () => {
  vi.spyOn(api, "brainSourceDetail").mockResolvedValue({id:"source1",artifacts:[]});
  vi.spyOn(api, "classifiedMailPage").mockResolvedValue({rows:[],total:0,offset:0,limit:50,has_next:false});
  const upload = vi.spyOn(api, "brainImportEml")
    .mockResolvedValueOnce({status:"resolved"})
    .mockResolvedValueOnce({status:"duplicate"})
    .mockRejectedValueOnce(new Error("Le fichier est vide."));
  const p = props();
  p.projects = [{id:"p1",code:"P1",name:"Atelier"}, {id:"divers",code:"DIVERS",name:"Divers"}];
  render(<MailWorkspace {...p} scoped/>);
  openDetails("Options");
  fireEvent.click(screen.getByRole("button", {name:"Importer des mails EML"}));
  const form = screen.getByRole("form", {name:"Importer des mails EML"});
  expect(within(form).getByRole("combobox")).toBe(document.activeElement);
  expect(within(form).queryByRole("option", {name:/Divers/})).toBeNull();
  expect(within(form).queryByRole("option", {name:/Détecter le projet/})).toBeNull();
  const submit = within(form).getByRole("button", {name:"Importer"}) as HTMLButtonElement;
  expect(submit.disabled).toBe(true);
  fireEvent.change(within(form).getByLabelText("Projet de destination"), {target:{value:"p1"}});
  const files = ["nouveau.eml", "doublon.eml", "vide.eml"].map(name => new File([""], name));
  fireEvent.change(within(form).getByLabelText("Fichiers EML"), {target:{files}});
  expect(submit.disabled).toBe(false);
  fireEvent.submit(form);

  await screen.findByText("1 mail importé. 1 déjà présent. vide.eml — Le fichier est vide.");
  expect(upload.mock.calls).toEqual(files.map(file => ["p1", file]));
  expect(p.onReload).toHaveBeenCalled();
  expect(screen.getByRole("form", {name:"Importer des mails EML"})).toBeTruthy();
});

it("importe un EML sans destination et indique où le rattacher", async () => {
  vi.spyOn(api, "brainSourceDetail").mockResolvedValue({id:"source1",artifacts:[]});
  const upload=vi.spyOn(api,"brainImportEml").mockResolvedValue({status:"resolution_pending"});
  const p=props();p.projects=[];
  render(<MailWorkspace {...p}/>);
  openDetails("Options");
  fireEvent.click(screen.getByRole("button",{name:"Importer des mails EML"}));
  const form=screen.getByRole("form",{name:"Importer des mails EML"});
  const file=new File([""],"à-classer.eml");
  fireEvent.change(within(form).getByLabelText("Projet de destination"),{target:{value:"automatic"}});
  fireEvent.change(within(form).getByLabelText("Fichiers EML"),{target:{files:[file]}});
  fireEvent.submit(form);
  await screen.findByText("1 mail importé. 1 à rattacher dans Sources.");
  expect(upload).toHaveBeenCalledWith(null,file);
  expect(p.onReload).toHaveBeenCalled();
});

it("ne propose pas l’import EML en lecture seule", () => {
  vi.spyOn(api, "classifiedMailPage").mockResolvedValue({rows:[],total:0,offset:0,limit:50,has_next:false});
  const p = props();
  p.projects = [{id:"p1",code:"P1",name:"Atelier"}];
  render(<MailWorkspace {...p} scoped readOnly/>);
  openDetails("Options");
  expect(screen.queryByRole("button", {name:"Importer des mails EML"})).toBeNull();
});

it("permet de relire un mail rejeté dans un accès limité aux projets", async () => {
  vi.spyOn(api,"brainSourceDetail").mockResolvedValue({id:"source1",artifacts:[]});
  const archive = vi.spyOn(api, "rejectedMailPage").mockResolvedValue({
    rows: [{source_id:"source1", project_id:null, author:"client@example.com", metadata:{subject:"Mail conservé après rejet"}}],
    total:1, offset:0, limit:100, has_next:false,
  });
  const discard=vi.spyOn(api,"brainDiscardSource");
  const p=props();
  render(<MailWorkspace {...p} scoped/>);
  fireEvent.click(screen.getByRole("button",{name:"Rejeter le mail"}));
  await screen.findByText("Mail rejeté. Retrouvez-le dans Options → Dossier → Mails rejetés.");
  expect(p.onReject).toHaveBeenCalledWith(p.queue[0]);
  expect(p.onReload).toHaveBeenCalled();
  expect(discard).not.toHaveBeenCalled();
  openDetails("Options");
  fireEvent.change(screen.getByLabelText("Dossier de mails"), {target:{value:"rejected"}});
  await screen.findByRole("heading", {name:"Mail conservé après rejet"});
  expect(archive).toHaveBeenCalledWith(0, "", "newest");
  expect(screen.queryByRole("button", {name:"Enregistrer le classement"})).toBeNull();
  expect(screen.queryByRole("button", {name:"Rejeter le mail"})).toBeNull();
});

it("classe directement dans Divers malgré une autre destination présélectionnée", async () => {
  vi.spyOn(api,"brainSourceDetail").mockResolvedValue({id:"source1",artifacts:[]});
  const p=props();
  p.projects=[{id:"p1",code:"P1",name:"Projet"},{id:"divers",code:"DIVERS",name:"Divers"}];
  p.queue[0]={...p.queue[0],target_project_id:"p1",target_code:"P1",confidence:.8};
  vi.mocked(p.onDecide).mockRejectedValueOnce(new Error("Classement indisponible"));
  render(<MailWorkspace {...p}/>);
  openDetails("Options du mail");
  fireEvent.click(screen.getByRole("button",{name:"Classer dans Divers"}));
  await waitFor(()=>expect(p.onDecide).toHaveBeenCalledWith(p.queue[0],"divers"));
  await screen.findByText("Classement indisponible");
  expect(screen.getByRole("heading",{name:"Offre publicitaire"})).toBeTruthy();
});

it("affiche clairement De, À, Copie et les liens des pièces jointes", async () => {
  vi.spyOn(api,"brainSourceDetail").mockResolvedValue({id:"source1", sender:"Alice <alice@example.com>", recipients:{to:["Bob <bob@example.com>"],cc:["Carole <carole@example.com>"]}, attachments:[{index:0,filename:"Plan.pdf",mime:"application/pdf",previewable:true},{index:1,filename:"Tableau.xlsx",mime:"application/octet-stream",previewable:false}],artifacts:[]});
  render(<MailWorkspace {...props()}/>);
  openDetails("Détails du mail");
  await screen.findByText("Bob <bob@example.com>");
  expect(screen.getByText("Carole <carole@example.com>")).toBeTruthy();
  expect(screen.getByText("De")).toBeTruthy();
  expect(screen.getByText("À")).toBeTruthy();
  expect(screen.getByText("Copie")).toBeTruthy();
  expect(screen.getByRole("link",{name:"Visualiser"}).getAttribute("href")).toBe("/v1/sources/source1/attachments/0");
  expect(screen.getAllByRole("link",{name:"Télécharger"})).toHaveLength(2);
});

it("réserve le lecteur au message et garde les coordonnées accessibles sans lancer de classement", async () => {
  vi.spyOn(api,"brainSourceDetail").mockResolvedValue({id:"source1",sender:"Alice <alice@example.com>",recipients:{to:["Bob <bob@example.com>"],cc:["Carole <carole@example.com>"]},artifacts:[{kind:"body_text",text:"Voici le contenu utile du message."}]});
  const discard=vi.spyOn(api,"brainDiscardSource");
  const p=props();
  render(<MailWorkspace {...p}/>);
  const reader=screen.getByRole("region",{name:"Espace de lecture"});
  const content=await within(reader).findByText("Voici le contenu utile du message.");
  const heading=within(reader).getByRole("heading",{name:"Offre publicitaire"});
  expect(heading.closest("header")?.nextElementSibling).toBe(content.closest("article"));
  expect(within(reader).queryByRole("button",{name:"Classer et suivant"})).toBeNull();
  expect(within(screen.getByRole("complementary",{name:"Projets de classement"})).getByRole("button",{name:"Classer et suivant"})).toBeTruthy();
  const details=screen.getByText("Détails du mail",{exact:true,selector:"summary"}).closest("details") as HTMLDetailsElement;
  expect(details.open).toBe(false);
  openDetails("Détails du mail");
  expect(details.open).toBe(true);
  expect(within(details).getByText("Bob <bob@example.com>")).toBeTruthy();
  expect(within(details).getByText("Carole <carole@example.com>")).toBeTruthy();
  openDetails("Détails du mail");
  expect(details.open).toBe(false);
  expect(p.onDecide).not.toHaveBeenCalled();
  expect(discard).not.toHaveBeenCalled();
});

it("explique la probabilité d’écartement sans déclencher de décision", async () => {
  vi.spyOn(api, "brainSourceDetail").mockResolvedValue({id:"source1",artifacts:[]});
  const discard = vi.spyOn(api,"brainDiscardSource");
  const p=props();
  p.queue[0]={...p.queue[0],discard_suggestion:{probability:.76,discarded_samples:4,retained_samples:1,reason:"Même objet et même expéditeur",estimated:true}};
  render(<MailWorkspace {...p}/>);
  openDetails("Pourquoi cette proposition ?");
  expect(screen.getByText("Suggestion de suppression : 76 %")).toBeTruthy();

  expect(discard).not.toHaveBeenCalled();
  expect(p.onDecide).not.toHaveBeenCalled();
});

it("présélectionne la suggestion sans valider et conserve le choix humain au rafraîchissement", async () => {
  vi.spyOn(api, "brainSourceDetail").mockResolvedValue({id:"source1",artifacts:[]});
  const p=props();
  p.projects=[{id:"p1",code:"P1",name:"Projet suggéré"},{id:"p2",code:"P2",name:"Autre projet"}];
  p.queue[0]={...p.queue[0],target_code:"P1",target_name:"Projet suggéré",confidence:.9};
  const view=render(<MailWorkspace {...p}/>);
  const selector=screen.getByRole("combobox",{name:"Projet de classement"}) as HTMLSelectElement;
  await waitFor(()=>expect(selector.value).toBe("p1"));
  expect(p.onDecide).not.toHaveBeenCalled();
  fireEvent.change(selector,{target:{value:"p2"}});
  view.rerender(<MailWorkspace {...p} projects={[...p.projects]}/>);
  expect(selector.value).toBe("p2");
  fireEvent.click(screen.getByRole("button",{name:"Classer et suivant"}));
  expect(p.onDecide).toHaveBeenCalledWith(p.queue[0],"p2");
});

function props(): ComponentProps<typeof MailWorkspace> {
  return {
    queue: [{ proposal_id: "proposal1", source_id: "source1", sender: "spam@example.com", subject: "Offre publicitaire",
      received_at: null, excerpt: "Offre", target_project_id: "p1", target_code: "DIVERS", target_name: "Divers", confidence: .35, reason: "Sans projet" }],
    projects: [{ id: "p1", code: "DIVERS", name: "Divers" }], portfolio: [], links: {}, stats: null,
    query: "", onQuery: vi.fn(), sort: "newest", onSort: vi.fn(), queueTotal: 1,
    selected: new Set(), onToggle: vi.fn(), onSelectAll: vi.fn(), onClearSelected: vi.fn(),
    offset: 0, onPage: vi.fn(), pageHasNext: false, onReload: vi.fn().mockResolvedValue(undefined),
    onRunTriage: vi.fn(), onCancelTriage: vi.fn(), triaging: false, busy: "", dropping: false,
    autoInfo: "", message: "", onDecide: vi.fn(), onReject: vi.fn(), onDragStart: vi.fn(), onDrop: vi.fn(), dragOver: null, onDragOver: vi.fn(),
  };
}

function openDetails(label: string) {
  fireEvent.click(screen.getByText(label, {exact:true,selector:"summary"}));
}

it("garde les résultats trouvés par le serveur au-delà de l'aperçu et affiche le total", () => {
  const p = {...props(), query: "tolérance", queueTotal: 253, pageHasNext: true};
  render(<MailWorkspace {...p} />);
  expect(screen.getByRole("heading", {name: "Offre publicitaire"})).toBeTruthy();
  expect(screen.getByText(/Mail 1 \/ 253/)).toBeTruthy();
});

it("affiche le compteur et garde la progression après une interruption", () => {
  const p = props();
  const progress = {processed: 15, total: 232, classified: 14, divers: 2, errors: 1, status: "running" as const};
  const view = render(<MailWorkspace {...p} triaging triageProgress={progress} message="Analyse en cours" />);
  expect(screen.getByText("15 / 232 mails traités")).toBeTruthy();
  const bar = screen.getByRole("progressbar", {name: "Mails traités"}) as HTMLProgressElement;
  expect(bar.value).toBe(15);
  expect(bar.max).toBe(232);
  expect(screen.getByText("1 mail(s) en échec")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", {name: "Interrompre l’analyse"}));
  expect(p.onCancelTriage).toHaveBeenCalledTimes(1);
  view.rerender(<MailWorkspace {...p} triageProgress={{...progress, status: "interrupted"}} message="Analyse interrompue" />);
  expect(screen.getByText("15 / 232 mails traités")).toBeTruthy();
  expect(screen.queryByRole("button", {name: "Interrompre l’analyse"})).toBeNull();
});

it("écarte le mail ouvert sans l'affecter à un projet", async () => {
  vi.spyOn(api, "brainSources").mockResolvedValue([]);
  vi.spyOn(api, "brainSourceDetail").mockResolvedValue({ id: "source1", artifacts: [{ kind: "body_text", text: "Offre sans intérêt" }] });
  const discard = vi.spyOn(api, "brainDiscardSource").mockResolvedValue({ status: "discarded" });
  const p = props();
  render(<MailWorkspace {...p} />);

  await screen.findByText("Offre sans intérêt");
  fireEvent.change(screen.getByLabelText("Projet de classement"), { target: { value: "DISCARD" } });
  expect(discard).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Supprimer le contenu de Kiara" }));
  await waitFor(() => expect(discard).toHaveBeenCalledWith("source1"));
  await waitFor(() => expect(p.onReload).toHaveBeenCalled());
  expect(p.onDecide).not.toHaveBeenCalled();
});

it("le dépôt sur Écarter utilise les IDs sources des seules propositions déposées", async () => {
  vi.spyOn(api, "brainSources").mockResolvedValue([]);
  const discard = vi.spyOn(api, "brainDiscardSource").mockResolvedValue({ status: "discarded" });
  const p = props();
  render(<MailWorkspace {...p} />);
  fireEvent.drop(screen.getByRole("button", { name: /Supprimer de Kiara/ }), {
    dataTransfer: { getData: (type: string) => type === "application/x-triage-mails" ? '["proposal1"]' : "" },
  });
  await waitFor(() => expect(discard).toHaveBeenCalledWith("source1"));
  expect(p.onDrop).not.toHaveBeenCalled();
  expect(p.onDecide).not.toHaveBeenCalled();
});

it("actualise les mails classés sans rouvrir le dossier pour un accès limité", async () => {
  vi.useFakeTimers();
  try {
    vi.spyOn(api, "brainSourceDetail").mockResolvedValue({id:"source1",artifacts:[]});
    const old = {source_id:"source1",project_id:"p1",author:"client@example.com",metadata:{subject:"Mail ouvert"}};
    const recent = {...old, source_id:"source2", metadata:{subject:"Nouveau mail classé"}};
    const initial = {rows:[old],total:1,has_next:false,offset:0,limit:100};
    const fetchPage = vi.spyOn(api, "classifiedMailPage")
      .mockResolvedValueOnce(initial)
      .mockResolvedValue({...initial, rows:[recent, old], total:2});
    const p = props();
    p.stats = null;
    const view = render(<MailWorkspace {...p} scoped readOnly />);
    await act(async () => {});
    expect(screen.getByRole("heading",{name:"Mail ouvert"})).toBeTruthy();
    expect(fetchPage).toHaveBeenCalledTimes(1);

    await act(async () => { await vi.advanceTimersByTimeAsync(15_000); });
    expect(screen.getByText("Mail 2 / 2")).toBeTruthy();
    expect(screen.getByRole("heading",{name:"Mail ouvert"})).toBeTruthy();
    await act(async () => { fireEvent.click(screen.getByRole("button",{name:"Mail précédent"})); });
    expect(screen.getByRole("heading",{name:"Nouveau mail classé"})).toBeTruthy();

    view.rerender(<MailWorkspace {...p} scoped readOnly active={false} />);
    await act(async () => { await vi.advanceTimersByTimeAsync(30_000); });
    expect(fetchPage).toHaveBeenCalledTimes(2);
  } finally {
    vi.useRealTimers();
  }
});

it("un mail classé peut être déplacé vers un nouveau projet ERP via la même résolution de cible",async()=>{
  vi.spyOn(api,"classifiedMailPage").mockResolvedValue({rows:[{source_id:"source1",project_id:"p1",author:"client@example.com",metadata:{subject:"Mail conservé"}}],total:1,has_next:false,offset:0,limit:100});
  const reassign=vi.spyOn(api,"brainReassignSource").mockResolvedValue({});
  const resolve=vi.fn().mockResolvedValue("brain-new");
  render(<MailWorkspace {...props()} portfolio={[{id:"erp-new",code:"NEW0807",title:"Projet nouveau"} as any]} onResolveTarget={resolve}/>);
  openDetails("Options");
  fireEvent.change(screen.getByLabelText("Dossier de mails"),{target:{value:"classified"}});
  await screen.findByRole("heading",{name:"Mail conservé"});
  fireEvent.drop(screen.getByRole("button",{name:/NEW0807.*Projet nouveau/}),{dataTransfer:{getData:()=> '["source1"]'}});
  await waitFor(()=>expect(reassign).toHaveBeenCalledWith("source1","brain-new"));
  expect(resolve).toHaveBeenCalledWith("erp:erp-new");
});

it("retire immédiatement un mail déplacé du dossier d’origine malgré une actualisation périmée",async()=>{
  vi.spyOn(api,"classifiedMailPage").mockResolvedValue({rows:[{source_id:"source1",project_id:"p1",author:"client@example.com",metadata:{subject:"Mail conservé"}}],total:1,has_next:false,offset:0,limit:100});
  vi.spyOn(api,"brainReassignSource").mockResolvedValue({});
  const p=props();
  p.projects=[{id:"p1",code:"A0806",name:"Origine"},{id:"p2",code:"B0809",name:"Destination"}];
  p.portfolio=[{id:"erp-a",code:"A0806",title:"Origine",brain_project_id:"p1"},{id:"erp-b",code:"B0809",title:"Destination",brain_project_id:"p2"}] as any;
  p.links={"erp-a":{brainId:"p1",brainCode:"A0806",linked:true},"erp-b":{brainId:"p2",brainCode:"B0809",linked:true}};
  render(<MailWorkspace {...p}/>);
  openDetails("Options");
  fireEvent.change(screen.getByLabelText("Dossier de mails"),{target:{value:"project:p1"}});
  await screen.findByRole("heading",{name:"Mail conservé"});
  fireEvent.drop(screen.getByRole("button",{name:/B0809.*Destination/}),{dataTransfer:{getData:()=> '["source1"]'}});
  await waitFor(()=>expect(api.brainReassignSource).toHaveBeenCalledWith("source1","p2"));
  await waitFor(()=>expect(screen.queryByRole("heading",{name:"Mail conservé"})).toBeNull());
  expect(screen.getByText(/0 mail sur 0/)).toBeTruthy();
});

it("ouvre un seul mail, présélectionne le meilleur candidat et avance après classement",async()=>{
  vi.spyOn(api,"brainSourceDetail").mockResolvedValue({id:"source1",artifacts:[]});
  const p=props();p.projects=[{id:"p1",code:"P1",name:"Premier"},{id:"p2",code:"P2",name:"Meilleur"}];
  p.queue=[{...p.queue[0],confidence:.3,candidates:[{project_id:"p2",code:"P2",score:.9}]},{...p.queue[0],source_id:"source2",proposal_id:"proposal2",subject:"Second mail"}];
  const view=render(<MailWorkspace {...p}/>);
  await waitFor(()=>expect((screen.getByLabelText("Projet de classement") as HTMLSelectElement).value).toBe("p2"));
  expect(screen.queryByRole("heading",{name:"Second mail"})).toBeNull();
  expect(screen.queryByText("Pourquoi ce projet ?")).toBeNull();
  fireEvent.click(screen.getByRole("button",{name:"Classer et suivant"}));
  await waitFor(()=>expect(p.onDecide).toHaveBeenCalledWith(p.queue[0],"p2"));
  view.rerender(<MailWorkspace {...p} queue={[p.queue[1]]}/>);
  await screen.findByRole("heading",{name:"Second mail"});
});

it("rejette le mail courant directement sans classer sa destination présélectionnée", async () => {
  vi.spyOn(api, "brainSourceDetail").mockResolvedValue({id:"source1",artifacts:[]});
  const discard=vi.spyOn(api,"brainDiscardSource").mockResolvedValue({status:"discarded"});
  const p=props();
  render(<MailWorkspace {...p}/>);
  openDetails("Options du mail");
  fireEvent.click(screen.getByRole("button",{name:"Supprimer ce mail de Kiara"}));
  await waitFor(()=>expect(discard).toHaveBeenCalledWith("source1"));
  expect(p.onDecide).not.toHaveBeenCalled();
  await waitFor(()=>expect(p.onReload).toHaveBeenCalled());
});

it("conserve le mail et affiche l'erreur si le rejet échoue", async () => {
  vi.spyOn(api, "brainSourceDetail").mockResolvedValue({id:"source1",artifacts:[]});
  vi.spyOn(api,"brainDiscardSource").mockRejectedValue(new Error("Rejet indisponible"));
  render(<MailWorkspace {...props()}/>);
  openDetails("Options du mail");
  fireEvent.click(screen.getByRole("button",{name:"Supprimer ce mail de Kiara"}));
  await screen.findByText(/Rejet indisponible/);
  expect(screen.getByRole("heading",{name:"Offre publicitaire"})).toBeTruthy();
});

it("ouvre les dossiers et les commandes secondaires à la demande sans décider un classement", async () => {
  vi.spyOn(api,"brainSourceDetail").mockResolvedValue({id:"source1",artifacts:[]});
  const discard=vi.spyOn(api,"brainDiscardSource");
  const p=props();
  render(<MailWorkspace {...p}/>);
  expect((screen.getByRole("combobox",{name:"Dossier de mails"}).closest("details") as HTMLDetailsElement).open).toBe(false);
  const sidebar=screen.getByRole("complementary",{name:"Projets de classement"});
  const selector=within(sidebar).getByRole("combobox",{name:"Projet de classement"});
  const classify=within(sidebar).getByRole("button",{name:"Classer et suivant"});
  expect(selector.closest("details")).toBeNull();
  expect(selector.closest(".maildesk-decision")).toBe(classify.closest(".maildesk-decision"));
  expect(selector.closest(".maildesk-decision")).not.toBeNull();
  expect(selector.compareDocumentPosition(classify) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(screen.queryByText("Autre projet",{exact:true,selector:"summary"})).toBeNull();
  expect((screen.getByRole("button",{name:"Supprimer ce mail de Kiara"}).closest("details") as HTMLDetailsElement).open).toBe(false);
  openDetails("Options");
  expect(screen.getByRole("combobox",{name:"Dossier de mails"})).toBeTruthy();
  expect((screen.getByRole("combobox",{name:"Dossier de mails"}).closest("details") as HTMLDetailsElement).open).toBe(true);
  expect(screen.queryByRole("button",{name:"Mails classés"})).toBeNull();
  expect(within(sidebar).getByRole("combobox",{name:"Projet de classement"})).toBe(selector);
  expect(discard).not.toHaveBeenCalled();
  expect(p.onDecide).not.toHaveBeenCalled();
});

it("affiche les indices du meilleur candidat seulement dans le détail de la proposition", async () => {
  vi.spyOn(api,"brainSourceDetail").mockResolvedValue({id:"source1",artifacts:[]});
  const p=props();
  p.projects=[{id:"p1",code:"P1",name:"Premier"},{id:"p2",code:"P2",name:"Projet retenu"}];
  p.queue[0]={...p.queue[0],confidence:.3,candidates:[{project_id:"p2",code:"P2",score:.9,evidence:[{key:"explicit_code",label:"Référence P2 trouvée dans l’objet",weight:.9}]}]};
  render(<MailWorkspace {...p}/>);
  expect((screen.getByText("Pourquoi cette proposition ?").closest("details") as HTMLDetailsElement).open).toBe(false);
  openDetails("Pourquoi cette proposition ?");
  expect(screen.getByText("Score de correspondance : 90 %")).toBeTruthy();
  expect(screen.getByText("Référence P2 trouvée dans l’objet")).toBeTruthy();
  expect(p.onDecide).not.toHaveBeenCalled();
});

it("verrouille la validation pendant le classement et empêche un double clic", async () => {
  vi.spyOn(api,"brainSourceDetail").mockResolvedValue({id:"source1",artifacts:[]});
  const p=props();
  let finish!:()=>void;
  vi.mocked(p.onDecide).mockImplementation(()=>new Promise<void>(resolve=>{finish=resolve;}));
  render(<MailWorkspace {...p}/>);
  const button=screen.getByRole("button",{name:"Classer et suivant"});
  fireEvent.click(button);fireEvent.click(button);
  expect(p.onDecide).toHaveBeenCalledTimes(1);
  expect((screen.getByRole("button",{name:"Classement…"}) as HTMLButtonElement).disabled).toBe(true);
  finish();
  await waitFor(()=>expect((screen.getByRole("button",{name:"Classer et suivant"}) as HTMLButtonElement).disabled).toBe(false));
});

it("affiche quatre vignettes classées selon le mail courant et garde les autres projets en repli", async()=>{
  vi.spyOn(api,"brainSourceDetail").mockResolvedValue({id:"source1",artifacts:[]});
  const p=props();
  p.projects=Array.from({length:6},(_,index)=>({id:`p${index+1}`,code:`P${index+1}`,name:`Projet ${index+1}`}));
  p.projects.push({id:"divers",code:"DIVERS",name:"Divers"});
  p.portfolio=p.projects.filter(project=>project.id!=="divers").map(project=>({id:`erp-${project.id}`,code:project.code,title:project.name,brain_project_id:project.id})) as any;
  p.queue=[{...p.queue[0],target_project_id:"divers",confidence:.35,candidates:[{project_id:"p2",code:"P2",score:.9},{project_id:"p3",code:"P3",score:.8},{project_id:"p4",code:"P4",score:.7},{project_id:"p5",code:"P5",score:.6},{project_id:"p6",code:"P6",score:.5}]},
    {...p.queue[0],source_id:"source2",proposal_id:"proposal2",subject:"Mail suivant",target_project_id:"p1",confidence:.95,candidates:[{project_id:"p6",code:"P6",score:.8}]}];
  render(<MailWorkspace {...p}/>);
  const likely=screen.getByLabelText("Projets proposés — déposez le mail dessus");
  await waitFor(()=>expect(within(likely).getAllByRole("button")[0].textContent).toContain("P2"));
  expect(within(likely).getAllByRole("button")).toHaveLength(4);
  expect(within(likely).getAllByRole("button").map(button=>button.textContent)).toEqual(["P2Projet 290 %","P3Projet 380 %","P4Projet 470 %","P5Projet 560 %"]);
  expect(within(likely).queryByRole("button",{name:/DIVERS/})).toBeNull();
  const otherProjects=screen.getByLabelText("Autres projets de classement");
  expect((otherProjects.closest("details") as HTMLDetailsElement).open).toBe(false);
  expect(within(otherProjects).getByRole("button",{name:/P1.*Projet 1/})).toBeTruthy();
  fireEvent.click(screen.getByRole("button",{name:"Mail suivant"}));
  await screen.findByRole("heading",{name:"Mail suivant"});
  expect(within(likely).getAllByRole("button").map(button=>button.textContent)).toEqual(["P1Projet 195 %","P6Projet 680 %"]);
  expect(p.onDecide).not.toHaveBeenCalled();
});

it("les vignettes visibles rétablissent le dépôt groupé vers un projet ERP ou sans fiche ERP", async()=>{
  vi.spyOn(api,"brainSourceDetail").mockResolvedValue({id:"source1",artifacts:[]});
  const p=props();
  p.projects=[{id:"brain-linked",code:"P1",name:"Lié"},{id:"brain-only",code:"P2",name:"Sans fiche ERP"}];
  p.portfolio=[{id:"erp-one",code:"P1",title:"Lié",brain_project_id:"brain-linked"}] as any;
  p.links={"erp-one":{brainId:"brain-linked",brainCode:"P1",linked:true}};
  p.queue[0]={...p.queue[0],target_project_id:"brain-linked",confidence:.8,candidates:[{project_id:"brain-only",code:"P2",score:.7}]};
  render(<MailWorkspace {...p}/>);
  const dataTransfer={getData:(type:string)=>type==="application/x-triage-mails"?'["proposal1"]':""};
  const tiles=screen.getByLabelText("Projets proposés — déposez le mail dessus");
  const linked=within(tiles).getByRole("button",{name:/P1.*Lié/});
  const standalone=within(tiles).getByRole("button",{name:/P2.*Sans fiche ERP/});
  fireEvent.dragOver(linked,{dataTransfer});
  expect(p.onDragOver).toHaveBeenCalledWith("mini:erp-one");
  fireEvent.drop(linked,{dataTransfer});
  expect(p.onDrop).toHaveBeenCalledWith(expect.anything(),"erp-one","brain-linked");
  fireEvent.drop(standalone,{dataTransfer});
  expect(p.onDrop).toHaveBeenCalledWith(expect.anything(),"brain-only","brain-only");
  expect(p.onDecide).not.toHaveBeenCalled();
});

it("le dépôt d’un mail déjà classé vers un projet sans fiche ERP conserve son identifiant",async()=>{
  vi.spyOn(api,"brainSourceDetail").mockResolvedValue({id:"source1",artifacts:[]});
  vi.spyOn(api,"classifiedMailPage").mockResolvedValue({rows:[{source_id:"source1",project_id:"original",author:"client@example.com",metadata:{subject:"Mail conservé"}}],total:1,has_next:false,offset:0,limit:100});
  const reassign=vi.spyOn(api,"brainReassignSource").mockResolvedValue({});
  const resolve=vi.fn().mockResolvedValue("brain-only");
  const p=props();p.projects=[{id:"original",code:"P1",name:"Origine"},{id:"brain-only",code:"P2",name:"Destination sans fiche ERP"}];
  render(<MailWorkspace {...p} onResolveTarget={resolve}/>);
  openDetails("Options");
  fireEvent.change(screen.getByLabelText("Dossier de mails"),{target:{value:"classified"}});
  await screen.findByRole("heading",{name:"Mail conservé"});
  fireEvent.drop(screen.getByRole("button",{name:/P2.*Destination sans fiche ERP/}),{dataTransfer:{getData:()=> '["source1"]'}});
  await waitFor(()=>expect(reassign).toHaveBeenCalledWith("source1","brain-only"));
  expect(resolve).toHaveBeenCalledWith("brain-only");
});

it("permet de replier le détail de l’analyse malgré les mises à jour et conserve compteurs, erreurs et interruption",()=>{
  const p=props();
  const progress={processed:15,total:232,classified:14,divers:2,errors:1,status:"running" as const};
  const view=render(<MailWorkspace {...p} triaging triageProgress={progress} message="Analyse en cours : longue explication"/>);
  const detailButton=screen.getByRole("button",{name:"Détails"});
  const detailId=detailButton.getAttribute("aria-controls")!;
  expect(document.getElementById(detailId)?.hidden).toBe(true);
  fireEvent.click(detailButton);
  expect(document.getElementById(detailId)?.hidden).toBe(false);
  fireEvent.click(screen.getByRole("button",{name:"Réduire"}));
  view.rerender(<MailWorkspace {...p} triaging triageProgress={{...progress,processed:20}} message="Analyse en cours : autre explication"/>);
  expect(document.getElementById(detailId)?.hidden).toBe(true);
  expect(screen.getByRole("button",{name:"Détails"}).getAttribute("aria-expanded")).toBe("false");
  expect(screen.getByText("20 / 232 mails traités")).toBeTruthy();
  expect(screen.getByText("1 mail(s) en échec")).toBeTruthy();
  fireEvent.click(screen.getByRole("button",{name:"Interrompre l’analyse"}));
  expect(p.onCancelTriage).toHaveBeenCalledTimes(1);
});

it("referme les options au lancement de chaque analyse",()=>{
  const p=props();
  render(<MailWorkspace {...p}/>);
  openDetails("Options");
  const options=screen.getByText("Options",{exact:true}).closest("details") as HTMLDetailsElement;
  expect(options.open).toBe(true);
  fireEvent.click(screen.getByRole("button",{name:"Analyser les nouveaux mails"}));
  expect(options.open).toBe(false);
  expect(p.onRunTriage).toHaveBeenCalledWith(false);
  openDetails("Options");
  fireEvent.click(screen.getByRole("button",{name:"Tout ré-analyser"}));
  expect(options.open).toBe(false);
  expect(p.onRunTriage).toHaveBeenCalledWith(true);
});


it('préfère le HTML original au texte extrait dans À trier',async()=>{
  vi.spyOn(api,'brainSourceDetail').mockResolvedValue({id:'source1',body_html:'<table width="600" style="background:#0085ad"><tr><td>Mail original</td></tr></table><img src="cid:logo">',inline_images:{logo:'data:image/png;base64,YQ=='},artifacts:[{kind:'body_text',text:'Alternative texte simplifiée'}]});
  const p=props();render(<MailWorkspace {...p}/>);
  const frame=await screen.findByTitle('Contenu du message');
  expect(frame.getAttribute('srcdoc')).toContain('width="600"');
  expect(frame.getAttribute('srcdoc')).toContain('background:#0085ad');
  expect(frame.getAttribute('srcdoc')).toContain('src="data:image/png;base64,YQ=="');
  expect(screen.queryByText('Alternative texte simplifiée')).toBeNull();
  expect(p.onDecide).not.toHaveBeenCalled();
});

it.each(['direct','destination','depot'])('annuler la suppression %s ne purge aucun mail',async chemin=>{
  vi.spyOn(window,'confirm').mockReturnValue(false);
  const discard=vi.spyOn(api,'brainDiscardSource');
  render(<MailWorkspace {...props()}/>);
  await screen.findByRole('heading',{name:'Offre publicitaire'});
  if(chemin==='direct'){openDetails('Options du mail');fireEvent.click(screen.getByRole('button',{name:'Supprimer ce mail de Kiara'}));}
  else if(chemin==='destination'){fireEvent.change(screen.getByLabelText('Projet de classement'),{target:{value:'DISCARD'}});fireEvent.click(screen.getByRole('button',{name:'Supprimer le contenu de Kiara'}));}
  else fireEvent.drop(screen.getByRole('button',{name:/Supprimer de Kiara/}),{dataTransfer:{getData:(type:string)=>type==='application/x-triage-mails'?'["proposal1"]':''}});
  await waitFor(()=>expect(window.confirm).toHaveBeenCalledOnce());
  expect(discard).not.toHaveBeenCalled();
  expect(vi.mocked(window.confirm).mock.calls[0][0]).toContain('originaux dans votre messagerie sont conservés');
});
