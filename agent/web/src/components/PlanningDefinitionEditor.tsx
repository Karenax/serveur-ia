import { useId, useState } from 'react';
import { priorityLabels, type TemplateDefinition } from '../lib/projectPlanning';
import { Pagination } from './IdentityPickers';

type TaskSpec=TemplateDefinition['tasks'][number];
const keyPattern=/^[a-z][a-z0-9_-]{0,63}$/;
const validOffset=(value:number|null)=>value===null||Number.isInteger(value)&&Math.abs(value)<=10000;
export function definitionIssues(value:TemplateDefinition):string[] {
  const errors:string[]=[];const codes=new Set(value.milestones.map(row=>row.code));const tasks=new Map(value.tasks.map(row=>[row.key,row]));
  if(!value.name.trim()||value.name.length>255)errors.push('Le nom de la version est requis (255 caractères maximum).');
  if(value.milestones.length<1||value.milestones.length>100)errors.push('Le modèle doit contenir entre 1 et 100 jalons.');
  if(codes.size!==value.milestones.length)errors.push('Chaque code de jalon doit être unique.');
  if(tasks.size!==value.tasks.length)errors.push('Chaque clé de tâche doit être unique.');
  if(value.tasks.length>1000)errors.push('Le modèle est limité à 1 000 tâches.');
  const parents=new Set(value.tasks.map(row=>row.parent_key).filter(Boolean));
  value.milestones.forEach((row,index)=>{
    if(!keyPattern.test(row.code)||!row.title.trim()||row.title.length>255||!validOffset(row.offset_workdays))errors.push(`Jalon ${index+1} : code, intitulé ou décalage invalide.`);
  });
  value.tasks.forEach((row,index)=>{
    if(!keyPattern.test(row.key)||!row.title.trim()||row.title.length>255)errors.push(`Tâche ${index+1} : clé et intitulé requis.`);
    if(!validOffset(row.start_offset_workdays)||!validOffset(row.end_offset_workdays)||row.start_offset_workdays!==null&&row.end_offset_workdays!==null&&row.end_offset_workdays<row.start_offset_workdays)errors.push(`Tâche ${index+1} : décalages début/fin invalides.`);
    if(!Number.isFinite(row.planned_hours)||row.planned_hours<0||row.planned_hours>1000000)errors.push(`Tâche ${index+1} : charge invalide.`);
    if(row.milestone_code&&!codes.has(row.milestone_code))errors.push(`Tâche ${index+1} : jalon absent du modèle.`);
    if(parents.has(row.key)&&(row.planned_hours!==0||row.start_offset_workdays!==null||row.end_offset_workdays!==null))errors.push(`Groupe ${row.title||index+1} : vider ses dates et sa charge propres ; ses enfants les déterminent.`);
    const seen=new Set([row.key]);let parent=row.parent_key;
    while(parent){if(seen.has(parent)){errors.push(`Tâche ${index+1} : cycle de parents interdit.`);break;}seen.add(parent);const next=tasks.get(parent);if(!next){errors.push(`Tâche ${index+1} : parent absent du modèle.`);break;}parent=next.parent_key;}
  });
  return errors;
}
export function PlanningDefinitionEditor({value,onChange,readOnly=false}:{value:TemplateDefinition;onChange:(value:TemplateDefinition)=>void;readOnly?:boolean}) {
  const [milestoneOffset,setMilestoneOffset]=useState(0);const [taskOffset,setTaskOffset]=useState(0);const keysId=useId();
  const milestonePage=milestoneOffset>=value.milestones.length?0:milestoneOffset,taskPage=taskOffset>=value.tasks.length?0:taskOffset;
  const parents=new Set(value.tasks.map(row=>row.parent_key).filter(Boolean));
  const updateMilestone=(index:number,patch:Partial<TemplateDefinition['milestones'][number]>)=>onChange({...value,milestones:value.milestones.map((row,i)=>i===index?{...row,...patch}:row)});
  const updateTask=(index:number,patch:Partial<TaskSpec>)=>onChange({...value,tasks:value.tasks.map((row,i)=>i===index?{...row,...patch}:row)});
  function reorder(index:number,step:number){const milestones=[...value.milestones];[milestones[index],milestones[index+step]]=[milestones[index+step],milestones[index]];onChange({...value,milestones});}
  const offsetValue=(raw:string)=>raw===''?null:Number(raw);
  return <section className="planning-definition" aria-label="Définition structurée du modèle">
    <label>Nom de la version<input className="input" required maxLength={255} value={value.name} disabled={readOnly} onChange={e=>onChange({...value,name:e.target.value})}/></label>
    <p className="planning-note">Les décalages sont exprimés en jours ouvrés par rapport au début choisi à l’application. Un champ vide ne propose aucune date. Les dates contractuelles et réelles restent indépendantes.</p>
    <div className="planning-heading"><h4>Jalons du modèle · {value.milestones.length}</h4>{!readOnly&&<button type="button" className="button secondary sm" disabled={value.milestones.length>=100} onClick={()=>{onChange({...value,milestones:[...value.milestones,{code:'',title:'',offset_workdays:null}]});setMilestoneOffset(Math.floor(value.milestones.length/10)*10);}}>Ajouter un jalon au modèle</button>}</div>
    <Pagination offset={milestonePage} total={value.milestones.length} limit={10} onChange={setMilestoneOffset}/>
    {value.milestones.slice(milestonePage,milestonePage+10).map((row,local)=>{const index=milestonePage+local,n=index+1;return <fieldset key={index} className="planning-spec"><legend>Jalon {n} · {row.title||'Nouveau jalon'}</legend><div className="planning-form-grid">
      <label>Code du jalon {n}<input className="input" required pattern="[a-z][a-z0-9_-]{0,63}" maxLength={64} value={row.code} disabled={readOnly} onChange={e=>updateMilestone(index,{code:e.target.value})}/></label>
      <label>Intitulé du jalon {n}<input className="input" required maxLength={255} value={row.title} disabled={readOnly} onChange={e=>updateMilestone(index,{title:e.target.value})}/></label>
      <label>Décalage du jalon {n} (jours ouvrés)<input className="input" type="number" min={-10000} max={10000} step={1} value={row.offset_workdays??''} disabled={readOnly} onChange={e=>updateMilestone(index,{offset_workdays:offsetValue(e.target.value)})}/></label></div>
      {!readOnly&&<div className="planning-actions"><button type="button" className="button secondary sm" aria-label={`Monter le jalon ${n}`} disabled={index===0} onClick={()=>reorder(index,-1)}>Monter</button><button type="button" className="button secondary sm" aria-label={`Descendre le jalon ${n}`} disabled={index===value.milestones.length-1} onClick={()=>reorder(index,1)}>Descendre</button>
        <button type="button" className="button secondary sm" aria-label={`Retirer le jalon ${n} du brouillon`} disabled={value.milestones.length===1} onClick={()=>onChange({...value,milestones:value.milestones.filter((_,i)=>i!==index)})}>Retirer du brouillon</button></div>}</fieldset>;})}
    <div className="planning-heading"><h4>Tâches du modèle · {value.tasks.length}</h4>{!readOnly&&<button type="button" className="button secondary sm" disabled={value.tasks.length>=1000} onClick={()=>{onChange({...value,tasks:[...value.tasks,{key:'',title:'',parent_key:null,milestone_code:null,start_offset_workdays:null,end_offset_workdays:null,planned_hours:0,priority:'normal',design:false,manufacturing:false}]});setTaskOffset(Math.floor(value.tasks.length/10)*10);}}>Ajouter une tâche au modèle</button>}</div>
    <datalist id={keysId}>{value.tasks.filter(row=>row.key).map((row,index)=><option key={index} value={row.key}>{row.title}</option>)}</datalist>
    <Pagination offset={taskPage} total={value.tasks.length} limit={10} onChange={setTaskOffset}/>
    {value.tasks.slice(taskPage,taskPage+10).map((row,local)=>{const index=taskPage+local,n=index+1,group=parents.has(row.key);return <fieldset key={index} className="planning-spec"><legend>Tâche {n} · {row.title||'Nouvelle tâche'}</legend><div className="planning-form-grid">
      <label>Clé de la tâche {n}<input className="input" required pattern="[a-z][a-z0-9_-]{0,63}" maxLength={64} value={row.key} disabled={readOnly} onChange={e=>updateTask(index,{key:e.target.value})}/></label>
      <label>Intitulé de la tâche {n}<input className="input" required maxLength={255} value={row.title} disabled={readOnly} onChange={e=>updateTask(index,{title:e.target.value})}/></label>
      <label>Clé du parent de la tâche {n}<input className="input" list={keysId} maxLength={64} value={row.parent_key||''} disabled={readOnly} onChange={e=>updateTask(index,{parent_key:e.target.value||null})}/></label>
      <label>Jalon de la tâche {n}<select className="input" value={row.milestone_code||''} disabled={readOnly} onChange={e=>updateTask(index,{milestone_code:e.target.value||null})}><option value="">Sans jalon</option>{row.milestone_code&&!value.milestones.some(m=>m.code===row.milestone_code)&&<option value={row.milestone_code}>Jalon absent · {row.milestone_code}</option>}{value.milestones.filter(m=>m.code).map((m,i)=><option value={m.code} key={i}>{m.title} · {m.code}</option>)}</select></label>
      <label>Début de la tâche {n} (jours ouvrés)<input className="input" type="number" min={-10000} max={10000} step={1} value={row.start_offset_workdays??''} disabled={readOnly||group} onChange={e=>updateTask(index,{start_offset_workdays:offsetValue(e.target.value)})}/></label>
      <label>Fin de la tâche {n} (jours ouvrés)<input className="input" type="number" min={-10000} max={10000} step={1} value={row.end_offset_workdays??''} disabled={readOnly||group} onChange={e=>updateTask(index,{end_offset_workdays:offsetValue(e.target.value)})}/></label>
      <label>Charge de la tâche {n} (h)<input className="input" type="number" min={0} max={1000000} step="any" required value={row.planned_hours} disabled={readOnly||group} onChange={e=>updateTask(index,{planned_hours:Number(e.target.value)})}/></label>
      <label>Priorité de la tâche {n}<select className="input" value={row.priority} disabled={readOnly} onChange={e=>updateTask(index,{priority:e.target.value as TaskSpec['priority']})}>{Object.entries(priorityLabels).map(([key,label])=><option value={key} key={key}>{label}</option>)}</select></label></div>
      <div className="planning-checks"><label><input type="checkbox" checked={row.design} disabled={readOnly} onChange={e=>updateTask(index,{design:e.target.checked})}/>Bureau d’études · tâche {n}</label><label><input type="checkbox" checked={row.manufacturing} disabled={readOnly} onChange={e=>updateTask(index,{manufacturing:e.target.checked})}/>Fabrication · tâche {n}</label></div>
      {group&&<p className="planning-note">Ce groupe agrège les dates et heures de ses enfants.{!readOnly&&(row.planned_hours!==0||row.start_offset_workdays!==null||row.end_offset_workdays!==null)&&<button type="button" className="button secondary sm" onClick={()=>updateTask(index,{planned_hours:0,start_offset_workdays:null,end_offset_workdays:null})}>Vider les valeurs propres du groupe {n}</button>}</p>}
      {!readOnly&&<button type="button" className="button secondary sm" aria-label={`Retirer la tâche ${n} du brouillon`} onClick={()=>onChange({...value,tasks:value.tasks.filter((_,i)=>i!==index)})}>Retirer du brouillon</button>}</fieldset>;})}
    {!value.tasks.length&&<p>Aucune tâche dans cette version.</p>}
    <p className="planning-note">Les clés assurent le suivi des tâches lors des applications suivantes. Publier une version conserve les précédentes ; retirer un élément du brouillon ne supprime aucun jalon ni aucune tâche des projets.</p>
  </section>;
}
