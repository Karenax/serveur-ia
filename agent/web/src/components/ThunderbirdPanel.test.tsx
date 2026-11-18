import { afterEach, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import * as http from "../lib/http";
import { ThunderbirdPanel } from "./ThunderbirdPanel";

const originalHidden=Object.getOwnPropertyDescriptor(document,'hidden');
afterEach(() => {cleanup();vi.useRealTimers();vi.restoreAllMocks();if(originalHidden)Object.defineProperty(document,'hidden',originalHidden);else Reflect.deleteProperty(document,'hidden');});

it("suspend le suivi hors rubrique et au masquage sans perdre le message",async()=>{
  vi.useFakeTimers();
  const read=vi.spyOn(http,"request").mockResolvedValue({connected:true,folders:[],accounts:[],jobs:[]});
  const view=render(<ThunderbirdPanel compose active/>);await act(async()=>{});
  expect(read).toHaveBeenCalledTimes(1);const first=read.mock.calls[0][1]!.signal as AbortSignal;
  fireEvent.change(screen.getByLabelText("Message"),{target:{value:"Brouillon de réponse conservé"}});
  view.rerender(<ThunderbirdPanel compose active={false}/>);expect(first.aborted).toBe(true);
  await act(async()=>{await vi.advanceTimersByTimeAsync(60000);});expect(read).toHaveBeenCalledTimes(1);
  view.rerender(<ThunderbirdPanel compose active/>);await act(async()=>{});expect(read).toHaveBeenCalledTimes(2);
  const second=read.mock.calls[1][1]!.signal as AbortSignal;
  Object.defineProperty(document,'hidden',{configurable:true,value:true});await act(async()=>{document.dispatchEvent(new Event('visibilitychange'));});
  expect(second.aborted).toBe(true);await act(async()=>{await vi.advanceTimersByTimeAsync(60000);});expect(read).toHaveBeenCalledTimes(2);
  Object.defineProperty(document,'hidden',{configurable:true,value:false});await act(async()=>{document.dispatchEvent(new Event('visibilitychange'));});
  expect(read).toHaveBeenCalledTimes(3);expect((screen.getByLabelText("Message") as HTMLTextAreaElement).value).toBe("Brouillon de réponse conservé");
});

it("affiche le fichier à installer si Windows refuse la stratégie utilisateur", async () => {
  const manualPath = "C:\\Kiara\\agent-thunderbird-0.3.1.xpi";
  vi.spyOn(http, "request")
    .mockResolvedValueOnce({version: "0.3.1", managed: false})
    .mockResolvedValueOnce({version: "0.3.1", managed: false, manual_path: manualPath});
  render(<ThunderbirdPanel extensionOnly />);
  fireEvent.click(await screen.findByRole("button", {name: "Installer l’extension"}));
  const input = await screen.findByRole("textbox", {name: "Fichier de l’extension"}) as HTMLInputElement;
  expect(input.value).toBe(manualPath);
  expect(input.readOnly).toBe(true);
});

it("prépare une réponse avec la source et l'identité choisies sans commande d'envoi", async () => {
  const request = vi.spyOn(http, "request").mockResolvedValue({ connected: true,
    accounts: [{ id: "account1", name: "Travail", identities: [{ id: "identity1", name: "Moi", email: "moi@example.com" }] }],
    folders: [], jobs: [] });
  render(<ThunderbirdPanel reply={{ sourceId: "source1", sender: "Client <client@example.com>", subject: "Commande" }} />);
  await screen.findByText("Connecté à Kiara");
  expect((screen.getByText("Connexion et synchronisation").closest("details") as HTMLDetailsElement).open).toBe(false);
  fireEvent.change(screen.getByLabelText("Message"), { target: { value: "Bonjour, voici notre réponse." } });
  expect(request.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(0);
  fireEvent.click(screen.getByRole("button", { name: "Créer le brouillon" }));
  await waitFor(() => expect(request).toHaveBeenCalledWith("/v1/thunderbird/drafts", expect.anything()));
  const call = request.mock.calls.find(([url]) => url === "/v1/thunderbird/drafts")!;
  expect(JSON.parse(call[1]!.body as string)).toMatchObject({ to: ["client@example.com"], subject: "Re: Commande",
    identity_id: "identity1", reply_source_id: "source1", open_window: false });
  expect(request.mock.calls.some(([url]) => url.includes("/send"))).toBe(false);
});

it("conserve l’accès à la synchronisation depuis les détails du message", async () => {
  const request=vi.spyOn(http,"request").mockResolvedValue({connected:true,folders:[{id:"inbox",name:"Réception",path:"INBOX",account_id:"account1"}],accounts:[],jobs:[]});
  render(<ThunderbirdPanel compose/>);
  await screen.findByText("Connecté à Kiara");
  expect(screen.getByLabelText("Message")).toBeTruthy();
  expect((screen.getByText("Connexion et synchronisation").closest("details") as HTMLDetailsElement).open).toBe(false);
  fireEvent.click(screen.getByText("Connexion et synchronisation"));
  expect((screen.getByText("Connexion et synchronisation").closest("details") as HTMLDetailsElement).open).toBe(true);
  expect(screen.getByRole("button",{name:"Synchroniser les dossiers choisis"})).toBeTruthy();
  expect(request.mock.calls.some(([, init])=>init?.method==="POST")).toBe(false);
});

it("montre la création du brouillon et empêche deux demandes simultanées", async () => {
  let finish!:(value:unknown)=>void;
  const request=vi.spyOn(http,"request").mockImplementation((url)=>url==="/v1/thunderbird/drafts"?new Promise(resolve=>{finish=resolve;}):Promise.resolve({connected:true,accounts:[{id:"account1",identities:[{id:"identity1",name:"Moi",email:"moi@example.com"}]}],folders:[],jobs:[]}));
  render(<ThunderbirdPanel reply={{sourceId:"source1",sender:"client@example.com",subject:"Commande"}}/>);
  await screen.findByText("Connecté à Kiara");
  const button=screen.getByRole("button",{name:"Créer le brouillon"});
  fireEvent.click(button);fireEvent.click(button);
  await waitFor(()=>expect(request.mock.calls.filter(([url])=>url==="/v1/thunderbird/drafts")).toHaveLength(1));
  expect(screen.getByText("Création du brouillon…")).toBeTruthy();
  expect((button as HTMLButtonElement).disabled).toBe(true);
  finish({});
  await screen.findByText("Création du brouillon demandée dans Thunderbird.");
});
