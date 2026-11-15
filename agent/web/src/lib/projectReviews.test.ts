import { expect, it } from 'vitest';
import { mergeReviewContent, reviewRelation, type ReviewContent, type ReviewItem } from './projectReviews';
const item:ReviewItem={id:'a',section_code:'actions',text:'Essai FAT',reviewed:false,evidence_ids:['proof'],owner:'Alice',due_date:'2026-10-20'};
const base:ReviewContent={meeting_date:'2026-10-10',location:'Salle 1',notes:'Initial',milestone_id:null,participants:[],deliverable_ids:['doc'],items:[item]};
it('résout une relation dans son espace sans changer les valeurs locales ou la publication',()=>{
  const bindings={erp:{same:'document-actuel'},brain:{same:'audio-actuel'}};
  const snapshot={id:'same',notes:'same',items:[{id:'same',text:'same'}]};const before=structuredClone(snapshot);
  expect(reviewRelation(snapshot.id,'erp',bindings)).toBe('document-actuel');
  expect(reviewRelation(snapshot.id,'brain',bindings)).toBe('audio-actuel');
  expect(reviewRelation('absent','erp',bindings)).toBe('absent');expect(snapshot).toEqual(before);
  expect(reviewRelation('same','erp',{})).toBe('same');expect(reviewRelation('same','brain')).toBe('same');
  expect(reviewRelation('toString','erp',bindings)).toBe('toString');
  const own=JSON.parse('{"erp":{"__proto__":"document-proto"}}');
  expect(reviewRelation('__proto__','erp',own)).toBe('document-proto');
});
it('fusionne les champs indépendants et conserve les points ajoutés par les deux auteurs',()=>{
  const mine={...base,notes:'Ma note',items:[item,{...item,id:'b',text:'Mon essai'}]},current={...base,location:'Salle 2',items:[item,{...item,id:'c',text:'Essai équipe'}]};
  const merged=mergeReviewContent(base,mine,current);
  expect(merged.unresolved).toEqual([]);expect(merged.content.notes).toBe('Ma note');expect(merged.content.location).toBe('Salle 2');
  expect(merged.content.items.map(row=>row.id)).toEqual(['a','c','b']);expect(base.items).toEqual([item]);
});
it('exige une décision pour la suppression concurrente d’un point modifié et les notes en conflit',()=>{
  const mine={...base,notes:'Moi',items:[]},current={...base,notes:'Équipe',items:[{...item,owner:'Bob'}]};
  expect(mergeReviewContent(base,mine,current).unresolved.map(row=>row.key)).toEqual(['notes','item:a']);
  const resolved=mergeReviewContent(base,mine,current,{'notes':'mine','item:a':'current'});
  expect(resolved.unresolved).toEqual([]);expect(resolved.content.notes).toBe('Moi');expect(resolved.content.items[0].owner).toBe('Bob');
  expect(mergeReviewContent(base,mine,current,{'notes':'current','item:a':'mine'}).content.items).toEqual([]);
});
it('retient les changements distants si le brouillon local n’a pas changé, sans ressusciter un point retiré',()=>{
  const current={...base,items:[],participants:[{person_id:null,name:'Client',function:'Qualité',signature_required:true}]};
  expect(mergeReviewContent(base,base,current).content).toEqual(current);
  expect(mergeReviewContent(base,{...base,items:[]},current).unresolved).toEqual([]);
});
