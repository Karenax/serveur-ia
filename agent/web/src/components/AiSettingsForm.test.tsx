import {afterEach, expect, it, vi} from "vitest";
import {cleanup, fireEvent, render, screen, waitFor} from "@testing-library/react";
import {AiSettingsForm} from "./SettingsForms";
import {api} from "../lib/api";

afterEach(()=>{cleanup();vi.restoreAllMocks();});

it("conserve les choix de connexion et de secours après repli des options",async()=>{
  vi.spyOn(api,"brainAiSettings").mockResolvedValue({enabled:true,provider:"openai_compatible",model:"gemma",base_url:"http://server:1234"});
  vi.spyOn(api,"saveBrainAiSettings").mockResolvedValue({});
  render(<AiSettingsForm/>);
  await screen.findByLabelText("Service IA");
  expect(screen.getByText("Connexion et clé d’accès").closest("details")).toHaveProperty("open",false);
  fireEvent.click(screen.getByText("Connexion et clé d’accès"));
  fireEvent.change(screen.getByLabelText("Adresse du serveur"),{target:{value:"http://new:1234"}});
  fireEvent.change(screen.getByLabelText("Clé d’accès (API)"),{target:{value:"nouvelle-cle"}});
  fireEvent.click(screen.getByText("Connexion et clé d’accès"));
  fireEvent.click(screen.getByText("Secours local si le serveur ne répond pas"));
  fireEvent.click(screen.getByRole("checkbox",{name:"Utiliser le modèle local si le serveur principal est injoignable"}));
  fireEvent.click(screen.getByText("Secours local si le serveur ne répond pas"));
  fireEvent.click(screen.getByRole("button",{name:"Enregistrer"}));
  await waitFor(()=>expect(api.saveBrainAiSettings).toHaveBeenCalledWith(expect.objectContaining({base_url:"http://new:1234",api_key:"nouvelle-cle",fallback_enabled:true})));
  await screen.findByText("Enregistré.");
  expect(screen.getByLabelText("Clé d’accès (API)")).toHaveProperty("value","");
});

it("empêche une seconde demande pendant le test et décrit seulement l’accessibilité",async()=>{
  vi.spyOn(api,"brainAiSettings").mockResolvedValue({enabled:true,provider:"ollama"});
  let finish!:(value:any)=>void;
  vi.spyOn(api,"brainAiTest").mockImplementation(()=>new Promise(resolve=>{finish=resolve;}));
  render(<AiSettingsForm/>);
  fireEvent.click(await screen.findByRole("button",{name:"Tester"}));
  expect(screen.getByRole("button",{name:"Test en cours…"})).toHaveProperty("disabled",true);
  expect(screen.getByRole("button",{name:"Enregistrer"})).toHaveProperty("disabled",true);
  finish({ok:true});
  await screen.findByText("Assistant IA accessible.");
  expect(api.brainAiTest).toHaveBeenCalledOnce();
});
