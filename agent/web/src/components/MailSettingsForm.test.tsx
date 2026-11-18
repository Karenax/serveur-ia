import {afterEach,beforeEach,it,expect,vi} from "vitest";
import {act,render,screen,fireEvent,waitFor,cleanup} from "@testing-library/react";
import {MailSettingsForm} from "./SettingsForms";
import {api} from "../lib/api";
import {request} from "../lib/http";
vi.mock("../lib/http",()=>({request:vi.fn()}));
const status={connected:true,version:"0.2.0",accounts:[{id:"a",name:"Compte A"},{id:"b",name:"Compte B"}],
  folders:[{id:"in",account_id:"a",path:"/INBOX"},{id:"sent",account_id:"a",path:"/Envoyés"},{id:"other",account_id:"b",path:"/Projet"}],
  sync:{folder_ids:["in"],processed:2,total:5,running:true}};
beforeEach(()=>{
 vi.mocked(request).mockResolvedValue(status);
 vi.spyOn(api,"brainMailSettings").mockResolvedValue({source:"thunderbird",folder:"C:/archives",auto_scan:false,scan_interval_minutes:9,thunderbird_folder_ids:["in"]});
 vi.spyOn(api,"saveBrainMailSettings").mockResolvedValue({});
 vi.spyOn(api,"brainScanGlobal").mockResolvedValue({scanned:3,imported:2,duplicates:1});
});
afterEach(()=>{cleanup();vi.restoreAllMocks();vi.mocked(request).mockReset();});
it("affiche 75 % par défaut et enregistre le seuil personnalisé",async()=>{
 render(<MailSettingsForm/>);
 await screen.findByText("Thunderbird connecté");
 fireEvent.click(screen.getByText("Options de synchronisation et de classement"));
 const input=screen.getByLabelText("Seuil de classement automatique (%)") as HTMLInputElement;
 expect(input.value).toBe("75");
 fireEvent.change(input,{target:{value:"90"}});
 fireEvent.click(screen.getByRole("button",{name:"Enregistrer"}));
 await waitFor(()=>expect(api.saveBrainMailSettings).toHaveBeenCalledWith(expect.objectContaining({auto_classification_threshold:.9})));
});
it("charge le seuil conservé et empêche un seuil hors limites",async()=>{
 vi.mocked(api.brainMailSettings).mockResolvedValue({source:"folder",auto_classification_threshold:1});
 render(<MailSettingsForm/>);
 await waitFor(()=>expect((screen.getByLabelText("Seuil de classement automatique (%)") as HTMLInputElement).value).toBe("100"));
 fireEvent.click(screen.getByText("Options de synchronisation et de classement"));
 fireEvent.change(screen.getByLabelText("Seuil de classement automatique (%)"),{target:{value:"101"}});
 expect((screen.getByRole("button",{name:"Enregistrer"}) as HTMLButtonElement).disabled).toBe(true);
 expect(api.saveBrainMailSettings).not.toHaveBeenCalled();
});
it("sélectionne plusieurs dossiers et garde leur choix pendant une recherche",async()=>{
 render(<MailSettingsForm/>);
 await screen.findByText("Thunderbird connecté");
 fireEvent.click(screen.getByText(/Choisir les dossiers/));
 fireEvent.click(screen.getByRole("checkbox",{name:"Compte A · /Envoyés"}));
 fireEvent.change(screen.getByLabelText("Rechercher un dossier"),{target:{value:"Projet"}});
 expect(screen.queryByRole("checkbox",{name:"Compte A · /Envoyés"})).toBeNull();
 fireEvent.click(screen.getByRole("button",{name:"Enregistrer"}));
 await waitFor(()=>expect(api.saveBrainMailSettings).toHaveBeenCalledWith(expect.objectContaining({source:"thunderbird",thunderbird_folder_ids:["in","sent"]})));
 expect((screen.getByRole("progressbar") as HTMLProgressElement).value).toBe(2);
});
it("bascule vers EML et synchronise cette source après enregistrement",async()=>{
 render(<MailSettingsForm/>);
 await screen.findByText("Thunderbird connecté");
 fireEvent.change(screen.getByLabelText("Source des mails"),{target:{value:"folder"}});
 expect((screen.getByLabelText("Dossier des e-mails (côté serveur)") as HTMLInputElement).value).toBe("C:/archives");
 fireEvent.click(screen.getByRole("button",{name:"Synchroniser maintenant"}));
 await waitFor(()=>expect(api.brainScanGlobal).toHaveBeenCalledOnce());
 expect(api.saveBrainMailSettings).toHaveBeenCalledWith(expect.objectContaining({source:"folder",folder:"C:/archives",thunderbird_folder_ids:["in"]}));
});
it("permet une demande manuelle même si la synchronisation automatique est désactivée",async()=>{
 render(<MailSettingsForm/>);
 await screen.findByText("Thunderbird connecté");
 fireEvent.click(screen.getByRole("button",{name:"Synchroniser maintenant"}));
 await waitFor(()=>expect(request).toHaveBeenCalledWith("/v1/thunderbird/sync",expect.objectContaining({method:"POST",body:'{"folder_ids":["in"]}'})));
 expect(api.brainScanGlobal).not.toHaveBeenCalled();
});
it("analyse ponctuellement un dossier serveur sans modifier la synchronisation",async()=>{
 vi.mocked(request).mockImplementation(async path=>{
   if(path==="/v1/ingest/default-folder")return {folder:"D:/dossier-recette"};
   if(path==="/v1/ingest/scan")return {scanned:3,imported:2,duplicates:1};
   return status;
 });
 render(<MailSettingsForm/>);
 await screen.findByText("Thunderbird connecté");
 fireEvent.click(screen.getByText("Analyser un dossier EML ponctuellement"));
 fireEvent.click(screen.getByRole("button",{name:"Utiliser le dossier par défaut"}));
 await waitFor(()=>expect(screen.getByLabelText("Dossier EML sur le serveur")).toHaveProperty("value","D:/dossier-recette"));
 fireEvent.click(screen.getByRole("button",{name:"Analyser le dossier"}));
 await screen.findByText("3 mail(s) parcouru(s), 2 importé(s), 1 doublon(s).");
 expect(request).toHaveBeenCalledWith("/v1/ingest/scan",expect.objectContaining({
   method:"POST",body:'{"folder":"D:/dossier-recette"}'
 }),0);
 expect(api.saveBrainMailSettings).not.toHaveBeenCalled();
});

it("suspend le statut Thunderbird hors de la vue et conserve les réglages non enregistrés",async()=>{
 vi.useFakeTimers();let hidden=false;
 vi.spyOn(document,'hidden','get').mockImplementation(()=>hidden);
 const view=render(<MailSettingsForm active/>);
 try{
   await act(async()=>{});
   fireEvent.change(screen.getByLabelText("Source des mails"),{target:{value:"folder"}});
   fireEvent.change(screen.getByLabelText("Dossier des e-mails (côté serveur)"),{target:{value:"D:/brouillon-fictif"}});
   let finish!:(value:unknown)=>void;
   vi.mocked(request).mockReturnValueOnce(new Promise(resolve=>{finish=resolve;}));
   const before=vi.mocked(request).mock.calls.length;
   await act(async()=>{await vi.advanceTimersByTimeAsync(30000);});
   expect(request).toHaveBeenCalledTimes(before+1);
   const calls=vi.mocked(request).mock.calls;
   const signal=calls[calls.length-1][1]!.signal as AbortSignal;
   view.rerender(<MailSettingsForm active={false}/>);
   expect(signal.aborted).toBe(true);
   await act(async()=>{await vi.advanceTimersByTimeAsync(60000);});
   expect(request).toHaveBeenCalledTimes(before+1);
   view.rerender(<MailSettingsForm active/>);await act(async()=>{});
   expect(request).toHaveBeenCalledTimes(before+2);
   await act(async()=>{finish({...status,connected:false});});
   expect(screen.getByLabelText("Dossier des e-mails (côté serveur)")).toHaveProperty('value','D:/brouillon-fictif');
   fireEvent.change(screen.getByLabelText("Source des mails"),{target:{value:"thunderbird"}});
   expect(screen.getByText('Thunderbird connecté')).toBeTruthy();
   fireEvent.change(screen.getByLabelText("Source des mails"),{target:{value:"folder"}});
   hidden=true;act(()=>document.dispatchEvent(new Event('visibilitychange')));
   await act(async()=>{await vi.advanceTimersByTimeAsync(60000);});
   expect(request).toHaveBeenCalledTimes(before+2);
   hidden=false;await act(async()=>{document.dispatchEvent(new Event('visibilitychange'));});
   expect(request).toHaveBeenCalledTimes(before+3);
   expect(api.saveBrainMailSettings).not.toHaveBeenCalled();
 }finally{view.unmount();vi.useRealTimers();}
});
