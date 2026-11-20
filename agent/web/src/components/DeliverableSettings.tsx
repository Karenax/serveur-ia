import { useEffect, useState } from 'react';
import { DeliverableCataloguePanel } from './DeliverableCataloguePanel';
import { DeliverableTypologyComposition } from './DeliverableTypologyComposition';

export function DeliverableSettings({active,onBusy}:{active:boolean;onBusy:(busy:boolean)=>void}) {
  const [tab,setTab]=useState('catalogue');const [compositionStarted,setCompositionStarted]=useState(false);const [catalogueBusy,setCatalogueBusy]=useState(false);const [compositionBusy,setCompositionBusy]=useState(false);const busy=catalogueBusy||compositionBusy;
  useEffect(()=>{onBusy(busy);return()=>onBusy(false);},[busy,onBusy]);
  return <><h2>Modèles de livrables</h2><nav className="workspace-tabs" aria-label="Réglages des livrables"><button type="button" aria-pressed={tab==='catalogue'} disabled={busy} onClick={()=>setTab('catalogue')}>Catalogue et versions</button><button type="button" aria-pressed={tab==='composition'} disabled={busy} onClick={()=>{setCompositionStarted(true);setTab('composition');}}>Composition par typologie</button></nav>
    <div hidden={tab!=='catalogue'}><DeliverableCataloguePanel active={active&&tab==='catalogue'} onBusy={setCatalogueBusy}/></div><div hidden={tab!=='composition'}>{compositionStarted&&<DeliverableTypologyComposition active={active&&tab==='composition'} onBusy={setCompositionBusy}/>}</div></>;
}
