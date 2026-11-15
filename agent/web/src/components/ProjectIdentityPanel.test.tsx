import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { identityApi, type ProjectIdentity, type ProjectPerson, type ProjectReference } from "../lib/projectIdentity";
import { ProjectIdentityPanel } from "./ProjectIdentityPanel";
import { ReferencePicker } from "./IdentityPickers";

export const client:ProjectReference={id:"client-a",kind:"client",code:"AIR",label:"Airbus",active:true,revision:1};
export const person:ProjectPerson={id:"person-a",first_name:"Alice",last_name:"Martin",email:"alice@example.test",trigram:"AMA",function:"BE",service:"Études",phone:"",agency_id:null,active:true,revision:2};
export const identity:ProjectIdentity={project_id:"p1",code:"AIRB26LTH0205-A",title:"LED 2026",status:"active",legacy_client_name:"Ancien libellé",offer_number:"OF-12",revision:7,
  client_id:client.id,agency_id:null,business_unit_id:null,family_id:null,typology_id:null,responsible_id:person.id,
  description:"Périmètre existant",client_reference:"REF-1",client_site:"",client_contact:"",equipment_number:"OUT-2",quantity:2,start_date:"2026-10-01",planned_end_date:"2026-12-01",actual_closure_date:"",standby:false,
  references:{[client.id]:client},responsible:person,can_edit:true,
  members:[{id:"m1",project_id:"p1",person_id:person.id,person,role:"responsable_projet",start_date:"2026-10-01",end_date:"",active:true,archived_at:null}],
  roles:[{code:"responsable_projet",label:"Responsable projet"},{code:"collaborateur_projet",label:"Collaborateur projet"},{code:"qualite",label:"Qualité"}],
};
beforeEach(()=>{
  vi.spyOn(identityApi,"read").mockResolvedValue(identity);
  vi.spyOn(identityApi,"references").mockImplementation(async kind=>({items:kind==="client"?[client]:[],total:kind==="client"?1:0,offset:0,limit:50}));
  vi.spyOn(identityApi,"people").mockResolvedValue({items:[person],total:1,offset:0,limit:50});
  vi.spyOn(identityApi,"history").mockResolvedValue({items:[],total:0,offset:0,limit:50});
});
afterEach(()=>{cleanup();vi.restoreAllMocks();});

it("enregistre les seuls champs modifiés avec la révision chargée et actualise le projet",async()=>{
  const patch=vi.spyOn(identityApi,"patch").mockResolvedValue({...identity,revision:8,client_reference:"REF-2"});const refresh=vi.fn();
  render(<ProjectIdentityPanel projectId="p1" onSaved={refresh}/>);
  const input=await screen.findByLabelText("Référence client");fireEvent.change(input,{target:{value:"REF-2"}});
  expect(screen.getByRole("region",{name:"Fiche et équipe du projet"}).dataset.workspaceDirty).toBe("true");
  fireEvent.click(screen.getByRole("button",{name:"Enregistrer la fiche"}));
  await waitFor(()=>expect(patch).toHaveBeenCalledWith("p1",7,{client_reference:"REF-2"}));
  await screen.findByText("Fiche enregistrée.");expect(refresh).toHaveBeenCalledOnce();
  expect(screen.getByRole("region",{name:"Fiche et équipe du projet"}).dataset.workspaceDirty).toBeUndefined();
});
it("garde un brouillon en conflit et ne remplace pas silencieusement la révision",async()=>{
  const patch=vi.spyOn(identityApi,"patch").mockRejectedValue(new Error("Modification concurrente : recharger la fiche et l'équipe"));
  render(<ProjectIdentityPanel projectId="p1"/>);fireEvent.change(await screen.findByLabelText("Description"),{target:{value:"Mon brouillon"}});
  fireEvent.click(screen.getByRole("button",{name:"Enregistrer la fiche"}));await screen.findByRole("alert");
  expect((screen.getByLabelText("Description") as HTMLTextAreaElement).value).toBe("Mon brouillon");
  expect(patch).toHaveBeenCalledTimes(1);
  vi.mocked(identityApi.read).mockResolvedValue({...identity,revision:8,description:"Modification d’un collègue"});
  fireEvent.click(screen.getByRole("button",{name:"Recharger et abandonner le brouillon"}));
  await waitFor(()=>expect((screen.getByLabelText("Description") as HTMLTextAreaElement).value).toBe("Modification d’un collègue"));
});
it("rend la fiche et l'équipe consultables sans commande pour un lecteur",async()=>{
  vi.mocked(identityApi.read).mockResolvedValue({...identity,can_edit:false});render(<ProjectIdentityPanel projectId="p1"/>);
  expect((await screen.findByLabelText("Description") as HTMLTextAreaElement).disabled).toBe(true);
  expect(screen.queryByRole("button",{name:"Enregistrer la fiche"})).toBeNull();
  fireEvent.click(screen.getByRole("button",{name:/Équipe/}));expect(screen.getByText("Alice Martin · AMA")).toBeTruthy();
  expect(screen.queryByRole("button",{name:"Archiver l’affectation"})).toBeNull();
  expect(identityApi.references).not.toHaveBeenCalled();
});
it("ajoute un membre choisi par UUID et garde la portée et la révision du projet",async()=>{
  const add=vi.spyOn(identityApi,"addMember").mockResolvedValue({...identity,revision:8});render(<ProjectIdentityPanel projectId="p1"/>);
  await screen.findByLabelText("Description");fireEvent.click(screen.getByRole("button",{name:/Équipe/}));fireEvent.click(screen.getByRole("button",{name:"Ajouter une affectation"}));
  const select=screen.getByLabelText("Personne à affecter");await waitFor(()=>expect(within(select).getByRole("option",{name:"Alice Martin · AMA"})).toBeTruthy());
  fireEvent.change(select,{target:{value:person.id}});fireEvent.change(screen.getByLabelText("Rôle métier"),{target:{value:"qualite"}});
  fireEvent.change(screen.getByLabelText("Début de l’affectation"),{target:{value:"2026-10-06"}});fireEvent.click(screen.getByRole("button",{name:"Enregistrer l’affectation"}));
  await waitFor(()=>expect(add).toHaveBeenCalledWith("p1",7,{person_id:person.id,role:"qualite",start_date:"2026-10-06",end_date:""}));
});
it("édite les dates d'une affectation et archive sans supprimer les lignes",async()=>{
  const patch=vi.spyOn(identityApi,"patchMember").mockResolvedValue({...identity,revision:8});const archive=vi.spyOn(identityApi,"archiveMember").mockResolvedValue({...identity,revision:9,members:identity.members.map(row=>({...row,active:false,archived_at:"2026-10-05"}))});
  render(<ProjectIdentityPanel projectId="p1"/>);await screen.findByLabelText("Description");fireEvent.click(screen.getByRole("button",{name:/Équipe/}));fireEvent.click(screen.getByRole("button",{name:"Modifier l’affectation"}));
  expect((screen.getByLabelText("Personne à affecter") as HTMLSelectElement).disabled).toBe(true);
  fireEvent.change(screen.getByLabelText("Fin de l’affectation"),{target:{value:"2026-11-01"}});fireEvent.click(screen.getByRole("button",{name:"Enregistrer l’affectation"}));
  await waitFor(()=>expect(patch).toHaveBeenCalledWith("p1",7,"m1",expect.objectContaining({end_date:"2026-11-01"})));
  await screen.findByText("Affectation enregistrée.");fireEvent.click(screen.getByRole("button",{name:"Archiver l’affectation"}));
  await waitFor(()=>expect(archive).toHaveBeenCalledWith("p1",8,"m1"));await screen.findByText(/Affectation archivée ;/);
  expect(screen.queryByText("Alice Martin · AMA")).toBeNull();fireEvent.click(screen.getByLabelText("Afficher les affectations archivées"));expect(screen.getByText("Alice Martin · AMA")).toBeTruthy();
});
it("ignore une réponse tardive du projet quitté",async()=>{
  let resolve!:(data:ProjectIdentity)=>void;vi.mocked(identityApi.read).mockReturnValueOnce(new Promise(done=>{resolve=done;})).mockResolvedValue({...identity,project_id:"p2",description:"Projet B"});
  const view=render(<ProjectIdentityPanel projectId="p1"/>);view.rerender(<ProjectIdentityPanel projectId="p2"/>);
  await screen.findByLabelText("Description");resolve(identity);await waitFor(()=>expect((screen.getByLabelText("Description") as HTMLTextAreaElement).value).toBe("Projet B"));
});
it("consulte un historique paginé sans charger toute la base",async()=>{
  vi.mocked(identityApi.history).mockResolvedValue({items:[{id:"h1",revision:7,actor_id:"operateur",action:"identity_updated",previous:{description:"Avant"},value:{description:"Après"},created_at:"2026-10-05"}],total:51,offset:0,limit:50});
  render(<ProjectIdentityPanel projectId="p1"/>);await screen.findByLabelText("Description");fireEvent.click(screen.getByRole("button",{name:"Historique"}));
  await screen.findByText(/Fiche modifiée/);fireEvent.click(screen.getByRole("button",{name:"Suivant"}));
  await waitFor(()=>expect(identityApi.history).toHaveBeenCalledWith("p1",50,expect.any(AbortSignal)));
});
it("retrouve une référence hors première page sans perdre la référence historique archivée",async()=>{
  const archived={...client,active:false};vi.mocked(identityApi.references).mockResolvedValue({items:[],total:51,offset:0,limit:50});const change=vi.fn();
  render(<ReferencePicker kind="client" label="Client" value={archived.id} current={archived} onChange={change}/>);
  expect(screen.getByRole("option",{name:"AIR · Airbus · archivé"})).toBeTruthy();await screen.findByText("1–50 sur 51");
  fireEvent.click(screen.getByRole("button",{name:"Suivant"}));await waitFor(()=>expect(identityApi.references).toHaveBeenCalledWith("client",expect.objectContaining({offset:50})));
  vi.mocked(identityApi.references).mockResolvedValue({items:[{...client,id:"new",code:"NEW",label:"Autre client"}],total:1,offset:0,limit:50});
  fireEvent.change(screen.getByLabelText("Rechercher · Client"),{target:{value:"NEW"}});await screen.findByRole("option",{name:"NEW · Autre client"});
  fireEvent.change(screen.getByLabelText("Client"),{target:{value:"new"}});expect(change).toHaveBeenCalledWith("new");
});
