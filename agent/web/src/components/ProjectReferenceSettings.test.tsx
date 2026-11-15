import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { identityApi, type ProjectPerson, type ProjectReference } from "../lib/projectIdentity";
import { ProjectReferenceSettings } from "./ProjectReferenceSettings";

const client:ProjectReference={id:"c1",kind:"client",code:"AIR",label:"Airbus",active:true,revision:4};
const person:ProjectPerson={id:"u1",first_name:"Alice",last_name:"Martin",email:"alice@example.test",trigram:"AMA",function:"BE",service:"Études",phone:"",agency_id:null,active:true,revision:2};
beforeEach(()=>{
  vi.spyOn(identityApi,"session").mockResolvedValue({operator:{id:"local",role:"owner",can_edit:true,can_administer:true,project_ids:null}});
  vi.spyOn(identityApi,"references").mockResolvedValue({items:[client],total:1,offset:0,limit:50});
  vi.spyOn(identityApi,"people").mockResolvedValue({items:[person],total:1,offset:0,limit:50});
});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
it("crée une référence dans le type choisi puis recharge la liste",async()=>{
  const create=vi.spyOn(identityApi,"createReference").mockResolvedValue({...client,id:"new"});render(<ProjectReferenceSettings/>);await screen.findByText("AIR · Airbus");
  fireEvent.click(screen.getByRole("button",{name:"Ajouter un client"}));fireEvent.change(screen.getByLabelText("Code"),{target:{value:"NEW"}});fireEvent.change(screen.getByLabelText("Libellé"),{target:{value:"Nouveau client"}});
  fireEvent.click(screen.getByRole("button",{name:"Enregistrer"}));await waitFor(()=>expect(create).toHaveBeenCalledWith("client","NEW","Nouveau client"));await screen.findByText("Liste mise à jour.");
  await waitFor(()=>expect(identityApi.references).toHaveBeenCalledTimes(2));
});
it("conserve le code stable, protège la révision et garde une saisie refusée",async()=>{
  const patch=vi.spyOn(identityApi,"patchReference").mockRejectedValue(new Error("Conflit de révision"));render(<ProjectReferenceSettings/>);await screen.findByText("AIR · Airbus");fireEvent.click(screen.getByRole("button",{name:"Modifier"}));
  expect((screen.getByLabelText("Code") as HTMLInputElement).disabled).toBe(true);
  fireEvent.change(screen.getByLabelText("Libellé"),{target:{value:"Airbus Toulouse"}});fireEvent.click(screen.getByRole("button",{name:"Enregistrer"}));await screen.findByRole("alert");
  expect(patch).toHaveBeenCalledWith(client,{label:"Airbus Toulouse"});expect((screen.getByLabelText("Libellé") as HTMLInputElement).value).toBe("Airbus Toulouse");
});
it("archive et réactive une référence sans commande de suppression",async()=>{
  const patch=vi.spyOn(identityApi,"patchReference").mockResolvedValue({...client,active:false,revision:5});render(<ProjectReferenceSettings/>);await screen.findByText("AIR · Airbus");
  vi.mocked(identityApi.references).mockResolvedValue({items:[{...client,active:false,revision:5}],total:1,offset:0,limit:50});fireEvent.click(screen.getByRole("button",{name:"Archiver"}));
  await waitFor(()=>expect(patch).toHaveBeenCalledWith(client,{active:false}));await screen.findByRole("button",{name:"Réactiver"});fireEvent.click(screen.getByRole("button",{name:"Réactiver"}));
  await waitFor(()=>expect(patch).toHaveBeenCalledWith({...client,active:false,revision:5},{active:true}));
});
it("crée et corrige une personne sans fusion sur son nom",async()=>{
  const create=vi.spyOn(identityApi,"createPerson").mockResolvedValue(person);const patch=vi.spyOn(identityApi,"patchPerson").mockResolvedValue({...person,phone:"123"});render(<ProjectReferenceSettings/>);
  await screen.findByText("AIR · Airbus");fireEvent.change(screen.getByLabelText("Liste"),{target:{value:"people"}});await screen.findByText("Alice Martin · AMA");
  fireEvent.click(screen.getByRole("button",{name:"Ajouter une personne"}));fireEvent.change(screen.getByLabelText("Prénom"),{target:{value:"Alice"}});fireEvent.change(screen.getByLabelText("Nom"),{target:{value:"Martin"}});fireEvent.click(screen.getByRole("button",{name:"Enregistrer"}));
  await waitFor(()=>expect(create).toHaveBeenCalledWith(expect.objectContaining({first_name:"Alice",last_name:"Martin",email:"",trigram:""})));
  await screen.findByText("Personne enregistrée.");await waitFor(()=>expect(identityApi.people).toHaveBeenCalledTimes(2));fireEvent.click(await screen.findByRole("button",{name:"Modifier"}));fireEvent.change(await screen.findByLabelText("Téléphone"),{target:{value:"123"}});fireEvent.click(screen.getByRole("button",{name:"Enregistrer"}));
  await waitFor(()=>expect(patch).toHaveBeenCalledWith(person,expect.objectContaining({phone:"123"})));
});
it("réserve les commandes globales au propriétaire de confiance",async()=>{
  vi.mocked(identityApi.session).mockResolvedValue({operator:{id:"editor",role:"editor",can_edit:true,can_administer:false,project_ids:["p1"]}});render(<ProjectReferenceSettings/>);await screen.findByText("AIR · Airbus");
  expect(screen.queryByRole("button",{name:"Ajouter un client"})).toBeNull();expect(screen.queryByRole("button",{name:"Archiver"})).toBeNull();expect(screen.queryByRole("button",{name:"Modifier"})).toBeNull();
});
it("cherche les références archivées par pages et réinitialise l'offset à la recherche",async()=>{
  vi.mocked(identityApi.references).mockResolvedValue({items:[client],total:51,offset:0,limit:50});render(<ProjectReferenceSettings/>);await screen.findByText("AIR · Airbus");
  fireEvent.click(screen.getByRole("button",{name:"Suivant"}));await waitFor(()=>expect(identityApi.references).toHaveBeenCalledWith("client",expect.objectContaining({offset:50})));
  fireEvent.change(screen.getByLabelText("Rechercher dans la liste"),{target:{value:"Air"}});fireEvent.click(screen.getByLabelText("Inclure les éléments archivés"));
  await waitFor(()=>expect(identityApi.references).toHaveBeenCalledWith("client",expect.objectContaining({offset:0,search:"Air",include_inactive:true})));
});
