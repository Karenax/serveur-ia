import { useEffect, useState } from 'react';
import { categoryLabels, deliverableApi, type CheckDefinition, type ConditionTypology, type TypeDefinition } from '../lib/projectDeliverables';
import type { Page } from '../lib/projectIdentity';
import { Pagination } from './IdentityPickers';
import { message } from './PlanningTasksPanel';

export const emptyTypeDefinition = ():TypeDefinition => ({category:'studies',design:false,position:0,checklist:[]});
const codePattern=/^[a-z][a-z0-9_-]{0,63}$/;
export function deliverableDefinitionIssues(value:TypeDefinition):string[] {
  const errors:string[]=[];
  if(!['studies','fabrication','project_end'].includes(value.category))errors.push('Choisir une catégorie opérationnelle.');
  if(!Number.isInteger(value.position)||value.position<0||value.position>100000)errors.push('L’ordre doit être un entier compris entre 0 et 100 000.');
  if(value.checklist.length>250)errors.push('Une version est limitée à 250 contrôles.');
  if(new Set(value.checklist.map(row=>row.code)).size!==value.checklist.length)errors.push('Chaque code de contrôle doit être unique.');
  value.checklist.forEach((row,i)=>{
    if(!codePattern.test(row.code)||!row.label.trim()||row.label.length>500||row.milestone_code.length>64)errors.push(`Contrôle ${i+1} : code, intitulé ou code du jalon invalide.`);
    if(row.typology_codes.length>100||new Set(row.typology_codes).size!==row.typology_codes.length||row.typology_codes.some(code=>!code.trim()||code.length>64))errors.push(`Contrôle ${i+1} : conditions de typologie invalides (100 codes uniques maximum).`);
  });
  return errors;
}

function TypologyConditions({value,onChange,disabled,active}:{value:string[];onChange:(value:string[])=>void;disabled:boolean;active:boolean}) {
  const [page,setPage]=useState<Page<ConditionTypology>|null>(null);const [search,setSearch]=useState('');const [offset,setOffset]=useState(0);const [error,setError]=useState('');const [loading,setLoading]=useState(false);
  const [known,setKnown]=useState<Record<string,string>>({});const [manual,setManual]=useState('');
  useEffect(()=>{if(!active)return;const controller=new AbortController();setLoading(true);setError('');const timer=window.setTimeout(()=>{
    deliverableApi.conditionTypologies({search,offset,limit:50,include_inactive:true,signal:controller.signal}).then(result=>{if(controller.signal.aborted)return;setPage(result);setKnown(previous=>({...previous,...Object.fromEntries(result.items.map(row=>[row.condition_code,`${row.label} · ${row.code}${row.active?'':' · archivée'}`]))}));}).catch(e=>{if(!controller.signal.aborted)setError(message(e));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});
  },150);return()=>{controller.abort();window.clearTimeout(timer);};},[active,search,offset]);
  return <div className="deliverable-conditions">
    <p className="planning-note">Sans condition, le contrôle concerne toutes les typologies. Les codes existants sont conservés, même si leur référentiel est absent ou archivé.</p>
    {value.length>0&&<ul>{value.map(code=><li key={code}>{known[code]||`Code conservé · ${code}`} <code>{code}</code>{!disabled&&<button type="button" className="button secondary sm" aria-label={`Retirer la condition ${code}`} onClick={()=>onChange(value.filter(item=>item!==code))}>Retirer du brouillon</button>}</li>)}</ul>}
    {!disabled&&<><label>Rechercher une condition de typologie<input className="input" type="search" maxLength={200} value={search} onChange={e=>{setSearch(e.target.value);setOffset(0);}}/></label>
      {loading&&<p role="status">Recherche des typologies…</p>}{error&&<p role="alert">{error}</p>}
      {page&&<><Pagination offset={page.offset} total={page.total} limit={page.limit} onChange={setOffset} disabled={loading}/><div className="planning-checks">{page.items.map(row=><label key={row.id}><input type="checkbox" checked={value.includes(row.condition_code)} disabled={!value.includes(row.condition_code)&&(!row.active||row.condition_code.length>64||value.length>=100)} onChange={e=>onChange(e.target.checked?[...value,row.condition_code]:value.filter(code=>code!==row.condition_code))}/>{row.label} · {row.code}{!row.active?' · archivée':''}{row.condition_code.length>64?' · code trop long':''}</label>)}</div></>}
      <div className="planning-actions"><label>Code de condition explicite<input className="input" maxLength={64} value={manual} onChange={e=>setManual(e.target.value)}/></label><button type="button" className="button secondary sm" disabled={!manual.trim()||manual!==manual.trim()||value.includes(manual)||value.length>=100} onClick={()=>{onChange([...value,manual]);setManual('');}}>Ajouter ce code</button></div><p className="planning-note">Le code explicite doit correspondre exactement au code de condition du référentiel ; aucune conversion implicite n’est appliquée.</p></>}
  </div>;
}

export function DeliverableDefinitionEditor({value,onChange,readOnly=false,active=true}:{value:TypeDefinition;onChange:(value:TypeDefinition)=>void;readOnly?:boolean;active?:boolean}) {
  const [offset,setOffset]=useState(0);const [conditions,setConditions]=useState<number|null>(null);const page=offset>=value.checklist.length?0:offset;
  const update=(index:number,patch:Partial<CheckDefinition>)=>onChange({...value,checklist:value.checklist.map((row,i)=>i===index?{...row,...patch}:row)});
  function reorder(index:number,step:number){const checklist=[...value.checklist];[checklist[index],checklist[index+step]]=[checklist[index+step],checklist[index]];setConditions(null);onChange({...value,checklist});}
  return <section className="planning-definition" aria-label="Définition structurée du livrable"><div className="planning-form-grid">
    <label>Catégorie du livrable<select className="input" value={value.category} disabled={readOnly} onChange={e=>onChange({...value,category:e.target.value as TypeDefinition['category']})}>{(['studies','fabrication','project_end'] as const).map(code=><option value={code} key={code}>{categoryLabels[code]}</option>)}</select></label>
    <label>Ordre dans le catalogue<input className="input" type="number" min={0} max={100000} step={1} value={value.position} disabled={readOnly} onChange={e=>onChange({...value,position:Number(e.target.value)})}/></label>
    <label className="identity-checkbox"><input type="checkbox" checked={value.design} disabled={readOnly} onChange={e=>onChange({...value,design:e.target.checked})}/>Livrable du bureau d’études</label></div>
    <div className="planning-heading"><h4>Contrôles · {value.checklist.length}</h4>{!readOnly&&<button type="button" className="button secondary sm" disabled={value.checklist.length>=250} onClick={()=>{onChange({...value,checklist:[...value.checklist,{code:'',label:'',milestone_code:'',active:true,is_gate:false,transverse:false,contributes:true,typology_codes:[]}]});setOffset(Math.floor(value.checklist.length/10)*10);setConditions(null);}}>Ajouter un contrôle</button>}</div>
    <Pagination offset={page} total={value.checklist.length} limit={10} onChange={next=>{setOffset(next);setConditions(null);}}/>
    {!value.checklist.length&&<p>Aucun contrôle dans cette définition.</p>}
    {value.checklist.slice(page,page+10).map((row,local)=>{const index=page+local,n=index+1;return <fieldset className="planning-spec" key={index}><legend>Contrôle {n} · {row.label||'Nouveau contrôle'}</legend><div className="planning-form-grid">
      <label>Code du contrôle {n}<input className="input" required maxLength={64} pattern="[a-z][a-z0-9_-]{0,63}" value={row.code} disabled={readOnly} onChange={e=>update(index,{code:e.target.value})}/></label>
      <label>Intitulé du contrôle {n}<input className="input" required maxLength={500} value={row.label} disabled={readOnly} onChange={e=>update(index,{label:e.target.value})}/></label>
      <label>Code du jalon du contrôle {n}<input className="input" maxLength={64} value={row.milestone_code} disabled={readOnly} onChange={e=>update(index,{milestone_code:e.target.value})}/></label></div>
      <div className="planning-checks">{(['active','is_gate','transverse','contributes'] as const).map(key=><label key={key}><input type="checkbox" checked={row[key]} disabled={readOnly} onChange={e=>update(index,{[key]:e.target.checked})}/>{({active:'Actif',is_gate:'Visa obligatoire',transverse:'Contrôle transverse',contributes:'Compte dans l’avancement'})[key]} · contrôle {n}</label>)}</div>
      <p className="planning-note">Le code du jalon sera rattaché explicitement lors de la sélection dans un projet. Un visa obligatoire exige une preuve sur la version du document concernée.</p>
      <details onToggle={e=>{const open=e.currentTarget.open;setConditions(current=>open?index:current===index?null:current);}}><summary>Conditions de typologie · contrôle {n} · {row.typology_codes.length||'toutes'}</summary>{conditions===index&&<TypologyConditions key={index} value={row.typology_codes} onChange={codes=>update(index,{typology_codes:codes})} disabled={readOnly} active={active}/>}</details>
      {!readOnly&&<div className="planning-actions"><button type="button" className="button secondary sm" disabled={index===0} onClick={()=>reorder(index,-1)} aria-label={`Monter le contrôle ${n}`}>Monter</button><button type="button" className="button secondary sm" disabled={index===value.checklist.length-1} onClick={()=>reorder(index,1)} aria-label={`Descendre le contrôle ${n}`}>Descendre</button><button type="button" className="button secondary sm" aria-label={`Retirer le contrôle ${n} du brouillon`} onClick={()=>{setConditions(null);onChange({...value,checklist:value.checklist.filter((_,i)=>i!==index)});}}>Retirer du brouillon</button></div>}
    </fieldset>;})}
    <p className="planning-note">Ces réglages définissent une future publication. Les contrôles et documents des projets existants sont conservés avec leur version d’origine.</p>
  </section>;
}
