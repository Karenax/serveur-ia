import { afterEach, describe, expect, it, vi } from 'vitest';
import { deliverableApi, deliverableDate, deliverableVersionLabel } from './projectDeliverables';
import * as http from './http';
import type { SelectionInputs } from './projectDeliverables';
afterEach(()=>vi.restoreAllMocks());
describe('Contrats catalogue et sélection',()=>{
  it('lit les visas paginés dans le projet et jalon exacts avec annulation',async()=>{
    const read=vi.spyOn(http,'request').mockResolvedValue({});const controller=new AbortController();await deliverableApi.milestoneGates('p/1','m/1',{offset:25,limit:25,include_ready:true,signal:controller.signal});expect(read).toHaveBeenCalledWith('/api/v1/projects/p%2F1/deliverable-plan/milestones/m%2F1/gates/page?offset=25&limit=25&include_ready=true',{signal:controller.signal});
  });
  it('publie une nouvelle définition avec CAS et compose une typologie sans commande projet',async()=>{
    const read=vi.spyOn(http,'request').mockResolvedValue({});const definition={category:'studies' as const,design:true,position:0,checklist:[]};await deliverableApi.publishType('type/1',4,definition);await deliverableApi.patchType('type/1',5,{active:false});await deliverableApi.patchComposition('typ/1',7,['type/1']);
    expect(read).toHaveBeenNthCalledWith(1,'/api/v1/deliverable-types/type%2F1/versions',{method:'POST',body:JSON.stringify({expected_revision:4,definition})});expect(read).toHaveBeenNthCalledWith(2,'/api/v1/deliverable-types/type%2F1',{method:'PATCH',body:JSON.stringify({active:false,expected_revision:5})});expect(read).toHaveBeenNthCalledWith(3,'/api/v1/project-references/typ%2F1/deliverable-types',{method:'PATCH',body:JSON.stringify({expected_revision:7,type_ids:['type/1']})});
  });
  it('lit les codes conditionnels paginés et les propositions sans création implicite',async()=>{
    const read=vi.spyOn(http,'request').mockResolvedValue({});await deliverableApi.conditionTypologies({search:'étude',offset:50,limit:50,include_inactive:true});await deliverableApi.standardTypes();expect(read).toHaveBeenNthCalledWith(1,'/api/v1/deliverable-types/condition-typologies?search=%C3%A9tude&offset=50&limit=50&include_inactive=true',{signal:undefined});expect(read).toHaveBeenNthCalledWith(2,'/api/v1/deliverable-types/standard-definition',{signal:undefined});
  });
  it('lit la version exacte avec portée encodée et filtre serveur borné',async()=>{
    const read=vi.spyOn(http,'request').mockResolvedValue({});const controller=new AbortController();await deliverableApi.types({offset:25,limit:25,typology_id:'t/1',signal:controller.signal});await deliverableApi.typeVersion('type/1','v/1',controller.signal);
    expect(read).toHaveBeenNthCalledWith(1,'/api/v1/deliverable-types?offset=25&limit=25&typology_id=t%2F1',{signal:controller.signal});expect(read).toHaveBeenNthCalledWith(2,'/api/v1/deliverable-types/type%2F1/versions/v%2F1',{signal:controller.signal});
  });
  it('applique exactement les entrées capturées avec leur empreinte sans lecture supplémentaire',async()=>{
    const read=vi.spyOn(http,'request').mockResolvedValue({revision:8});const inputs:SelectionInputs={expected_revision:7,type_version_ids:['old-v1'],typology_id:null,milestone_mapping:{pdr:'m1'},excluded_milestone_codes:['cdr'],existing_mapping:{type1:'manual1'},deactivate_missing:true,responsible_id:null,verifier_id:'person1'};await deliverableApi.applySelection('p/1',inputs,'b'.repeat(64));
    expect(read).toHaveBeenCalledOnce();expect(read).toHaveBeenCalledWith('/api/v1/projects/p%2F1/deliverable-plan/selection/apply',{method:'POST',body:JSON.stringify({...inputs,expected_preview_sha256:'b'.repeat(64)})});
  });
});
describe('Horodatages de preuve Livrables',()=>{
  it('interprète les dates SQLite sans fuseau comme UTC et conserve les offsets explicites',()=>{
    const displayed=new Date('2026-10-06T00:32:10Z').toLocaleString('fr-FR');
    expect(deliverableDate('2026-10-06T00:32:10')).toBe(displayed);
    expect(deliverableDate('2026-10-06T00:32:10+00:00')).toBe(displayed);
    expect(deliverableDate('2026-10-06T02:32:10+02:00')).toBe(displayed);
    expect(deliverableDate('2026-10-06T00:32:10Z')).toBe(displayed);
  });
  it('conserve une ancienne valeur illisible pour consultation',()=>{expect(deliverableDate('ancienne date')).toBe('ancienne date');});
});
describe('Contexte exact de version documentaire',()=>{
  it('affiche le numéro, référence et fichier sans reprendre une révision de lecture plus récente',async()=>{
    const read=vi.spyOn(http,'request').mockResolvedValueOnce({revision:7,latest_version_id:'v1'}).mockResolvedValueOnce({id:'v1',number:1,reference:'BE-A',filename:'notice.pdf',revision:8});
    const detail=await deliverableApi.detail('p/1','d/1');expect(read).toHaveBeenNthCalledWith(2,'/api/v1/projects/p%2F1/deliverable-plan/d%2F1/versions/v1',{signal:undefined},15000);expect(detail.revision).toBe(7);expect(detail.latest_version_id).toBe('v1');expect(deliverableVersionLabel(detail)).toBe('V1 · BE-A · notice.pdf');
  });
  it('laisse la fiche et la preuve consultables si les métadonnées de version sont indisponibles',async()=>{
    vi.spyOn(http,'request').mockResolvedValueOnce({revision:7,latest_version_id:'v1'}).mockRejectedValueOnce(new Error('Manifeste indisponible'));
    const detail=await deliverableApi.detail('p1','d1');expect(detail.revision).toBe(7);expect(detail.latest_version_id).toBe('v1');expect(deliverableVersionLabel(detail)).toBe('Version publiée');
  });
});
describe('Téléchargement des preuves',()=>{
  it('retourne les octets originaux du manifeste avec une URL de portée encodée',async()=>{
    const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response('{"publication":"preuve"}',{headers:{'Content-Type':'application/json'}}));
    const result=await deliverableApi.download('p/1','d/1','v/1','manifest');expect(await result.text()).toBe('{"publication":"preuve"}');expect(fetch).toHaveBeenCalledWith('/api/v1/projects/p%2F1/deliverable-plan/d%2F1/versions/v%2F1/manifest',expect.objectContaining({credentials:'same-origin',signal:expect.any(AbortSignal)}));
  });
  it('affiche le refus de fichier modifié et tolère une erreur serveur non JSON',async()=>{
    vi.spyOn(globalThis,'fetch').mockResolvedValueOnce(new Response(JSON.stringify({detail:'Fichier modifié'}),{status:409})).mockResolvedValueOnce(new Response('indisponible',{status:503}));
    await expect(deliverableApi.download('p1','d1','v1','file')).rejects.toThrow('Fichier modifié');await expect(deliverableApi.download('p1','d1','v1','file')).rejects.toThrow('Téléchargement indisponible (503)');
  });
  it('propage l’annulation de navigation au téléchargement',async()=>{
    let signal:AbortSignal|undefined;vi.spyOn(globalThis,'fetch').mockImplementation(async(_url,init)=>{signal=init?.signal as AbortSignal;return new Response('preuve');});const controller=new AbortController();await deliverableApi.download('p1','d1','v1','file',controller.signal);expect(signal?.aborted).toBe(false);
    controller.abort();expect(signal?.aborted).toBe(false); // listener removed on terminal download
    const stopped=new AbortController();stopped.abort();await deliverableApi.download('p1','d1','v1','file',stopped.signal);expect(signal?.aborted).toBe(true);
  });
});
