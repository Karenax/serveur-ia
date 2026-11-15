import { useEffect, useRef, useState } from "react";
import { identityApi, personName, referenceKinds, type Operator, type Page, type PersonInput, type ProjectPerson, type ProjectReference, type ReferenceKind } from "../lib/projectIdentity";
import { Pagination, ReferencePicker } from "./IdentityPickers";
import { Badge, LoadingState } from "./Ui";
import "../project-identity.css";

const emptyPerson:PersonInput={first_name:"",last_name:"",email:"",trigram:"",function:"",service:"",phone:"",agency_id:null};
const personFields=[ ["first_name","Prénom",120], ["last_name","Nom",120], ["trigram","Trigramme",12], ["email","Email",255], ["function","Fonction",120], ["service","Service",120], ["phone","Téléphone",40] ] as const;
const addLabels:Record<ReferenceKind|"people",string>={client:"Ajouter un client",agency:"Ajouter une agence",business_unit:"Ajouter une unité d’activité",family:"Ajouter une famille",typology:"Ajouter un type de projet",people:"Ajouter une personne"};
type Selection={mode:"reference";original:ProjectReference|null;code:string;label:string}|{mode:"person";original:ProjectPerson|null;data:PersonInput};
export function ProjectReferenceSettings() {
  const [kind,setKind]=useState<ReferenceKind|"people">("client");const [search,setSearch]=useState("");const [offset,setOffset]=useState(0);const [inactive,setInactive]=useState(false);
  const [operator,setOperator]=useState<Operator|null>(null);const [page,setPage]=useState<Page<ProjectReference|ProjectPerson>|null>(null);
  const [selection,setSelection]=useState<Selection|null>(null);const [error,setError]=useState("");const [notice,setNotice]=useState("");const [busy,setBusy]=useState(false);const [refresh,setRefresh]=useState(0);
  const alive=useRef(true);
  useEffect(()=>{alive.current=true;identityApi.session().then(session=>{if(alive.current)setOperator(session.operator);}).catch(e=>{if(alive.current)setError(String(e.message||e));});return()=>{alive.current=false;};},[]);
  useEffect(()=>{const controller=new AbortController();setPage(null);setError("");
    const timer=window.setTimeout(()=>{const options={search,offset,include_inactive:inactive,signal:controller.signal};
      const request=kind==="people"?identityApi.people(options):identityApi.references(kind,options);
      request.then(result=>{if(!controller.signal.aborted)setPage(result);}).catch(e=>{if(!controller.signal.aborted)setError(String(e.message||e));});},150);
    return()=>{controller.abort();window.clearTimeout(timer);};},[kind,search,offset,inactive,refresh]);
  const canAdmin=!!operator?.can_administer;const locked=busy||!!selection;
  async function command(action:()=>Promise<unknown>,message:string) {
    if(!canAdmin||busy)return;setBusy(true);setError("");setNotice("");
    try{await action();if(alive.current){setSelection(null);setNotice(message);setRefresh(value=>value+1);}}
    catch(e){if(alive.current)setError(String((e as Error).message||e));}
    finally{if(alive.current)setBusy(false);}
  }
  function edit(row:ProjectReference|ProjectPerson) {
    setError("");setNotice("");setSelection("kind" in row?{mode:"reference",original:row,code:row.code,label:row.label}:{mode:"person",original:row,data:{first_name:row.first_name,last_name:row.last_name,email:row.email,trigram:row.trigram,function:row.function,service:row.service,phone:row.phone,agency_id:row.agency_id}});
  }
  function submit() {
    if(!selection)return;
    if(selection.mode==="reference") {
      const {original,code,label}=selection;
      void command(()=>original?identityApi.patchReference(original,{label}):identityApi.createReference(kind as ReferenceKind,code,label),"Liste mise à jour.");
    }else{const {original,data}=selection;void command(()=>original?identityApi.patchPerson(original,data):identityApi.createPerson(data),"Personne enregistrée.");}
  }
  return <section className="reference-settings" aria-label="Clients, équipe et catégories" data-workspace-dirty={selection?"true":undefined}>
    <div className="card"><h2>Clients, équipe et catégories</h2><p>Les listes communes utilisées dans les projets : clients, personnes, agences et catégories.</p>
      {operator&&!canAdmin&&<p role="status">Consultation seule. Seul le propriétaire peut modifier ces listes.</p>}
      <div className="workspace-toolbar"><label>Liste<select className="input" value={kind} disabled={locked} onChange={e=>{setKind(e.target.value as ReferenceKind|"people");setOffset(0);setSearch("");setNotice("");}}>{referenceKinds.map(ref=><option key={ref.kind} value={ref.kind}>{ref.plural}</option>)}<option value="people">Personnes</option></select></label>
        <label>Rechercher dans la liste<input className="input" value={search} disabled={locked} placeholder={kind==="people"?"Nom, email, trigramme…":"Code ou libellé…"} onChange={e=>{setSearch(e.target.value);setOffset(0);}}/></label>
        <label className="identity-checkbox"><input type="checkbox" disabled={locked} checked={inactive} onChange={e=>{setInactive(e.target.checked);setOffset(0);}}/>Inclure les éléments archivés</label>
        {canAdmin&&<button type="button" className="button primary" disabled={locked} onClick={()=>{setError("");setNotice("");setSelection(kind==="people"?{mode:"person",original:null,data:{...emptyPerson}}:{mode:"reference",original:null,code:"",label:""});}}>{addLabels[kind]}</button>}
      </div>
    </div>
    {error&&<div className="identity-error" role="alert"><strong>{error}</strong>{selection&&<p>Votre saisie est conservée. Annulez l’édition puis rechargez la liste en cas de conflit.</p>}<button type="button" className="button secondary" disabled={busy} onClick={()=>{setSelection(null);setRefresh(value=>value+1);}}>Recharger et abandonner le brouillon</button></div>}
    {notice&&<p role="status" className="identity-notice">{notice}</p>}
    {selection&&<form className="card identity-member-form" onSubmit={e=>{e.preventDefault();submit();}}><h3>{selection.original?"Modifier":"Créer"} {selection.mode==="person"?"une personne":"une référence"}</h3>
      <div className="identity-grid">{selection.mode==="reference"?<><label>Code<input className="input" required maxLength={64} value={selection.code} disabled={busy||!!selection.original} onChange={e=>setSelection({...selection,code:e.target.value})}/></label><label>Libellé<input className="input" required maxLength={255} disabled={busy} value={selection.label} onChange={e=>setSelection({...selection,label:e.target.value})}/></label></>:
        <>{personFields.map(([key,label,max])=><label key={key}>{label}<input className="input" required={key==="first_name"||key==="last_name"} maxLength={max} disabled={busy} value={selection.data[key]} onChange={e=>setSelection({...selection,data:{...selection.data,[key]:e.target.value}})}/></label>)}
          <ReferencePicker kind="agency" label="Agence de la personne" value={selection.data.agency_id} onChange={agency_id=>setSelection({...selection,data:{...selection.data,agency_id}})} disabled={busy}/></>}
      </div><div className="identity-actions"><button type="submit" className="button primary" disabled={busy}>{busy?"Enregistrement…":"Enregistrer"}</button><button type="button" className="button secondary" disabled={busy} onClick={()=>{setSelection(null);setError("");}}>Annuler l’édition</button></div>
    </form>}
    {!page&&!error&&<LoadingState label="Chargement de la liste"/>}{page&&<div className="card"><Pagination offset={page.offset} total={page.total} limit={page.limit} disabled={locked} onChange={setOffset}/>
      <div className="identity-member-list">{page.items.map(row=><article className="identity-member" key={row.id}><div><strong>{"kind" in row?`${row.code} · ${row.label}`:personName(row)}</strong>{!("kind" in row)&&<p>{[row.function,row.service,row.email].filter(Boolean).join(" · ")}</p>}{!row.active&&<Badge value="Archivé"/>}</div>
        {canAdmin&&<div className="identity-actions"><button type="button" className="button secondary sm" disabled={locked} onClick={()=>edit(row)}>Modifier</button><button type="button" className="button secondary sm" disabled={locked} onClick={()=>void command(()=>"kind" in row?identityApi.patchReference(row,{active:!row.active}):identityApi.patchPerson(row,{active:!row.active}),row.active?"Élément archivé ; les données historiques sont conservées.":"Élément réactivé.")}>{row.active?"Archiver":"Réactiver"}</button></div>}
      </article>)}</div>
    </div>}
  </section>;
}
