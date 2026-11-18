import { afterEach, expect, it, vi } from "vitest";
import { act, cleanup, render, screen } from "@testing-library/react";
import { api, type PortfolioRow } from "./lib/api";
import { App } from "./App";

vi.mock("./components/WorkspaceShell",()=>({WorkspaceShell:({rows,error}:{rows:PortfolioRow[];error?:string})=><div><input aria-label="Saisie conservée"/>{error&&<p role="alert">{error}</p>}{rows.map(row=><span key={row.id}>{row.code}</span>)}</div>}));
const originalHidden=Object.getOwnPropertyDescriptor(document,"hidden");
afterEach(()=>{
  cleanup();vi.useRealTimers();vi.restoreAllMocks();
  if(originalHidden)Object.defineProperty(document,"hidden",originalHidden);else delete (document as any).hidden;
});
const rows=[{id:"a",code:"A-0806",title:"Projet A"}] as PortfolioRow[];
const refreshed=[...rows,{id:"b",code:"B-0807",title:"Projet B"}] as PortfolioRow[];
it.each([null,{},[null],[{id:'a',code:'A-0806',title:{malforme:true}}],[rows[0],rows[0]]])('conserve les projets et la saisie si le portefeuille est invalide : %j',async invalid=>{
  Object.defineProperty(document,'hidden',{configurable:true,value:false});window.history.replaceState(null,'','/app/projects');
  vi.spyOn(api,'portfolio').mockResolvedValueOnce(rows).mockResolvedValueOnce(invalid as PortfolioRow[]).mockResolvedValueOnce(refreshed);
  await act(async()=>{render(<App/>);});
  const input=screen.getByRole('textbox',{name:'Saisie conservée'}) as HTMLInputElement;
  input.value='Brouillon fictif';
  await act(async()=>{window.dispatchEvent(new Event('focus'));});
  expect(screen.getByText('A-0806')).toBeTruthy();expect(input.value).toBe('Brouillon fictif');
  expect(screen.getByRole('alert').textContent).toContain('Réponse du portefeuille invalide');
  await act(async()=>{window.dispatchEvent(new Event('focus'));});
  expect(screen.getByText('B-0807')).toBeTruthy();expect(input.isConnected).toBe(true);expect(input.value).toBe('Brouillon fictif');
  expect(screen.queryByRole('alert')).toBeNull();
});
it.each(["/app/projects","/app/mail"])("met à jour le catalogue visible sur %s quand un projet apparaît côté serveur", async(path)=>{
  vi.useFakeTimers();Object.defineProperty(document,"hidden",{configurable:true,value:false});
  window.history.replaceState(null,"",path);
  vi.spyOn(api,"portfolio").mockResolvedValueOnce(rows).mockResolvedValue(refreshed);
  await act(async()=>{render(<App/>);});
  expect(screen.queryByText("B-0807")).toBeNull();
  await act(async()=>{await vi.advanceTimersByTimeAsync(10_000);});
  expect(screen.getByText("B-0807")).toBeTruthy();
});
it("suspend le polling en arrière-plan puis actualise au retour de l’onglet", async()=>{
  vi.useFakeTimers();Object.defineProperty(document,"hidden",{configurable:true,value:false});
  window.history.replaceState(null,"","/app/projects");
  const portfolio=vi.spyOn(api,"portfolio").mockResolvedValueOnce(rows).mockResolvedValue(refreshed);
  await act(async()=>{render(<App/>);});
  Object.defineProperty(document,"hidden",{configurable:true,value:true});
  await act(async()=>{await vi.advanceTimersByTimeAsync(20_000);window.dispatchEvent(new Event("focus"));});
  expect(portfolio).toHaveBeenCalledOnce();
  Object.defineProperty(document,"hidden",{configurable:true,value:false});
  await act(async()=>{document.dispatchEvent(new Event("visibilitychange"));});
  expect(screen.getByText("B-0807")).toBeTruthy();expect(portfolio).toHaveBeenCalledTimes(2);
});
