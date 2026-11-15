import {expect,it} from "vitest";
import type {PortfolioRow} from "./api";
import {mailProjects} from "./mailProjects";

it("réunit projets reliés, nouveaux projets ERP et DIVERS sans doublon",()=>{
  const rows=[{id:"a",code:" A0806 ",title:"Titre ERP à jour",brain_project_id:null},
    {id:"b",code:"B0807",title:"Projet nouveau",brain_project_id:null}] as PortfolioRow[];
  expect(mailProjects(rows,[{id:"brain-a",code:"a0806",name:"Ancien titre"},{id:"divers",code:"DIVERS",name:"Divers"}]))
    .toEqual([{id:"brain-a",code:" A0806 ",name:"Titre ERP à jour"},{id:"erp:b",code:"B0807",name:"Projet nouveau"},
      {id:"divers",code:"DIVERS",name:"Divers"}]);
});
it("respecte le lien explicite et ne choisit pas arbitrairement entre deux codes identiques",()=>{
  const brain=[{id:"one",code:"A",name:"Un"},{id:"two",code:"a",name:"Deux"}];
  expect(mailProjects([{id:"erp-a",code:"A",title:"Ambigu",brain_project_id:null}] as PortfolioRow[],brain)[0].id).toBe("erp:erp-a");
  expect(mailProjects([{id:"erp-a",code:"A",title:"Relié",brain_project_id:"two"}] as PortfolioRow[],brain)[0].id).toBe("two");
});
