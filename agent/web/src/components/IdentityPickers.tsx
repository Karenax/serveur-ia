import { useEffect, useState } from "react";
import { identityApi, personName, type Page, type ProjectPerson, type ProjectReference, type ReferenceKind } from "../lib/projectIdentity";

export function Pagination({offset,total,limit=50,onChange,disabled=false}:{offset:number;total:number;limit?:number;onChange:(offset:number)=>void;disabled?:boolean}) {
  if (total <= limit && offset === 0) return null;
  return <div className="identity-pagination"><span>{!total?"Aucun résultat":offset>=total?`Aucun résultat sur cette page · ${total} au total`:`${offset+1}–${Math.min(offset+limit,total)} sur ${total}`}</span>
    <button type="button" className="button secondary sm" disabled={disabled||!offset} onClick={()=>onChange(Math.max(0,offset-limit))}>Précédent</button>
    <button type="button" className="button secondary sm" disabled={disabled||offset+limit>=total} onClick={()=>onChange(offset+limit)}>Suivant</button></div>;
}
type Pickable = {id:string;active:boolean};
export function Picker<T extends Pickable>({label,value,current,onChange,onPick,load,display,disabled=false,optionDisabled}:{label:string;value:string|null;current?:T|null;onChange:(id:string|null)=>void;onPick?:(row:T|null)=>void;load:(search:string,offset:number,signal:AbortSignal)=>Promise<Page<T>>;display:(row:T)=>string;disabled?:boolean;optionDisabled?:(row:T)=>boolean}) {
  const [search,setSearch]=useState("");const [offset,setOffset]=useState(0);
  const [page,setPage]=useState<Page<T>|null>(null);const [error,setError]=useState("");const [loading,setLoading]=useState(false);
  // Also retain selections made on a different search page until the parent saves.
  const [selected,setSelected]=useState<T|null>(current||null);
  useEffect(()=>{if(current)setSelected(current);else if(!value)setSelected(null);},[current,value]);
  useEffect(()=>{if(disabled){setLoading(false);return;}const controller=new AbortController();setLoading(true);setError("");setPage(null);
    const timer=window.setTimeout(()=>{load(search,offset,controller.signal).then(result=>{if(!controller.signal.aborted)setPage(result);})
      .catch(e=>{if(!controller.signal.aborted)setError(String(e.message||e));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});},150);
    return()=>{controller.abort();window.clearTimeout(timer);};},[load,search,offset,disabled]);
  const options=page?.items||[];
  const preserved=current?.id===value?current:selected?.id===value?selected:null;
  return <div className="identity-picker"><label>{label}<select className="input" value={value||""} disabled={disabled} onChange={e=>{const id=e.target.value;const chosen=options.find(row=>row.id===id)||preserved||null;setSelected(id?chosen:null);onPick?.(id?chosen:null);onChange(id||null);}}>
    <option value="">Non renseigné</option>{value&&!options.some(row=>row.id===value)&&<option value={value}>{preserved?display(preserved):"Sélection actuelle"}{preserved&&!preserved.active?" · archivé":""}</option>}
    {options.map(row=><option key={row.id} value={row.id} disabled={optionDisabled?.(row)}>{display(row)}</option>)}</select></label>
    {!disabled&&<><input className="input" aria-label={`Rechercher · ${label}`} placeholder="Rechercher…" value={search} onChange={e=>{setSearch(e.target.value);setOffset(0);}}/>
      {loading&&<small role="status">Recherche…</small>}{error&&<small role="alert">{error}</small>}
      {page&&<Pagination offset={page.offset} total={page.total} limit={page.limit} onChange={setOffset} disabled={loading}/>}</>}
  </div>;
}
const referenceLoaders=Object.fromEntries((["client","agency","business_unit","family","typology"] as ReferenceKind[]).map(kind=>[kind,
  (search:string,offset:number,signal:AbortSignal)=>identityApi.references(kind,{search,offset,signal})])) as Record<ReferenceKind,(search:string,offset:number,signal:AbortSignal)=>Promise<Page<ProjectReference>>>;
const peopleLoader=(search:string,offset:number,signal:AbortSignal)=>identityApi.people({search,offset,signal});
export function ReferencePicker(props:{kind:ReferenceKind;label:string;value:string|null;current?:ProjectReference|null;onChange:(id:string|null)=>void;disabled?:boolean}) {
  return <Picker {...props} load={referenceLoaders[props.kind]} display={row=>`${row.code} · ${row.label}`}/>;
}
export function PersonPicker(props:{label:string;value:string|null;current?:ProjectPerson|null;onChange:(id:string|null)=>void;disabled?:boolean}) {
  return <Picker {...props} load={peopleLoader} display={personName}/>;
}
