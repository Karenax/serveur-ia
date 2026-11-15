import { useState } from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { DeliverableDefinitionEditor, deliverableDefinitionIssues } from './DeliverableDefinitionEditor';
import { deliverableApi, type CheckDefinition, type TypeDefinition } from '../lib/projectDeliverables';
const check=(n:number):CheckDefinition=>({code:`c${n}`,label:`Contrôle ${n}`,milestone_code:'pdr',active:true,is_gate:true,contributes:true,transverse:false,typology_codes:[]});
const initial:TypeDefinition={category:'studies',design:true,position:0,checklist:[{...check(1),typology_codes:['ancien_inconnu']}]};
afterEach(()=>{cleanup();vi.restoreAllMocks();});
it('valide unicité, bornes et conditions sans rejeter un code historique inconnu',()=>{
  expect(deliverableDefinitionIssues(initial)).toEqual([]);expect(deliverableDefinitionIssues({...initial,position:1.5,checklist:[check(1),{...check(1),typology_codes:['a','a']}]})).toHaveLength(3);expect(deliverableDefinitionIssues({...initial,checklist:[{...check(1),label:' ',milestone_code:'a'.repeat(65)}]})).toHaveLength(1);
});
it('borne le rendu à 10 contrôles et conserve les modifications sur les autres pages',()=>{
  function Harness(){const [value,setValue]=useState<TypeDefinition>({...initial,checklist:Array.from({length:23},(_,i)=>check(i+1))});return <DeliverableDefinitionEditor value={value} onChange={setValue}/>;}render(<Harness/>);
  fireEvent.change(screen.getByLabelText('Intitulé du contrôle 1'),{target:{value:'Préparation conservée'}});expect(screen.queryByLabelText('Intitulé du contrôle 11')).toBeNull();fireEvent.click(screen.getByRole('button',{name:'Suivant'}));expect(screen.getByLabelText('Intitulé du contrôle 11')).toBeTruthy();expect(screen.queryByLabelText('Intitulé du contrôle 1')).toBeNull();fireEvent.click(screen.getByRole('button',{name:'Précédent'}));expect((screen.getByLabelText('Intitulé du contrôle 1') as HTMLInputElement).value).toBe('Préparation conservée');
});
it('utilise le code conditionnel du serveur et conserve les anciennes conditions',async()=>{
  vi.spyOn(deliverableApi,'conditionTypologies').mockResolvedValue({items:[{id:'typ',kind:'typology',code:'ÉTUDE_ß',condition_code:'etude_ss',label:'Études',active:true,revision:1}],total:1,offset:0,limit:50});let value=structuredClone(initial);
  function Harness(){const [draft,setDraft]=useState(value);return <DeliverableDefinitionEditor value={draft} onChange={next=>{value=next;setDraft(next);}}/>;}render(<Harness/>);const details=screen.getByText('Conditions de typologie · contrôle 1 · 1').closest('details')!;details.open=true;fireEvent(details,new Event('toggle'));fireEvent.click(await screen.findByLabelText('Études · ÉTUDE_ß'));expect(value.checklist[0].typology_codes).toEqual(['ancien_inconnu','etude_ss']);expect(screen.getByText('Code conservé · ancien_inconnu')).toBeTruthy();
});
it('annule la recherche conditionnelle à la désactivation et ne remplace pas les codes conservés',async()=>{
  let signal:AbortSignal|undefined;let resolve!:(value:Awaited<ReturnType<typeof deliverableApi.conditionTypologies>>)=>void;vi.spyOn(deliverableApi,'conditionTypologies').mockImplementation(options=>{signal=options?.signal;return new Promise(done=>{resolve=done;});});const view=render(<DeliverableDefinitionEditor value={initial} onChange={vi.fn()} active/>);const details=screen.getByText('Conditions de typologie · contrôle 1 · 1').closest('details')!;details.open=true;fireEvent(details,new Event('toggle'));await waitFor(()=>expect(signal).toBeDefined());view.rerender(<DeliverableDefinitionEditor value={initial} onChange={vi.fn()} active={false}/>);expect(signal?.aborted).toBe(true);resolve({items:[],total:0,offset:0,limit:50});expect(screen.getByText('Code conservé · ancien_inconnu')).toBeTruthy();
});
