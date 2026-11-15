import {expect,it} from 'vitest';
import {noteToMarkdown,parseNoteMarkdown} from './noteMarkdown';
import {blankNote,validNoteContent,type NoteBlock,type NoteContent,type NoteMark} from './projectNotes';
const run=(text:string,marks:NoteMark[]=[],href:string|null=null)=>({text,marks,href,color:null});
const paragraph=(text:string):NoteBlock=>({type:'paragraph',align:'left',runs:[run(text)]});
const document=(blocks:NoteBlock[]):NoteContent=>({version:1,blocks});

it('conserve négations, unités, références, échappements et valeurs industrielles au retour riche',()=>{
  const text='Ne pas valider : 12 Nm ± 0,5 ; IP65 non confirmé. AIRB25LTH0806-A / 350 lux. 1. [x] # *_ ` \\ <5 bar >3 | a.b (atelier).\nCommande provisoire.';
  const original=document([paragraph(text)]),encoded=noteToMarkdown(original);
  expect(encoded.ok).toBe(true);if(!encoded.ok)return;
  const decoded=parseNoteMarkdown(encoded.value);expect(decoded).toEqual({ok:true,value:original});
});
it('accepte le vrai ordre du DTO ERP heading puis trois paragraphes sans perdre le contenu',()=>{
  // NoteContent.model_dump(): Paragraph is declared type, runs, align;
  // parseNoteMarkdown creates type, align, runs. Their meaning is identical.
  const dto:NoteContent={version:1,blocks:[
    {type:'heading',level:1,runs:[run('Réunion fictive')]},
    {type:'paragraph',runs:[run('Puissance 250 W non validée.')],align:'left'},
    {type:'paragraph',runs:[run('Livraison du 23 octobre non confirmée.')],align:'left'},
    {type:'paragraph',runs:[run('Paul doit contrôler vendredi, sans engagement de commande.')],align:'left'},
  ]};
  const snapshot=JSON.stringify(dto);
  expect(Object.keys(dto.blocks[1])).toEqual(['type','runs','align']);
  const encoded=noteToMarkdown(dto);expect(encoded.ok).toBe(true);if(!encoded.ok)return;
  expect(parseNoteMarkdown(encoded.value)).toEqual({ok:true,value:dto});
  expect(JSON.stringify(dto)).toBe(snapshot);
});
it('compare explicitement les champs de titres, listes et éléments quel que soit leur ordre JSON',()=>{
  const original=document([
    {runs:[run('Ne pas approuver',['bold'])],level:2,type:'heading'},
    {items:[{indent:1,checked:true,runs:[run('Contrôle 12 Nm ± 0,5')]}],kind:'checklist',type:'list'},
  ]);
  const snapshot=JSON.stringify(original),encoded=noteToMarkdown(original);
  expect(encoded.ok).toBe(true);if(!encoded.ok)return;
  expect(parseNoteMarkdown(encoded.value)).toEqual({ok:true,value:original});
  expect(JSON.stringify(original)).toBe(snapshot);
});
it('retourne sans perte titres, listes, retraits, cases et styles/liens réversibles',()=>{
  const original=document([
    {type:'heading',level:1,runs:[run('Revue IP65',['bold'])]},
    {type:'heading',level:2,runs:[run('Réserves',['italic'])]},
    {type:'heading',level:3,runs:[run('Mesures')]},
    {type:'paragraph',align:'left',runs:[run('Ne pas publier. '),run('12 Nm',['bold','italic']),run(' doc',[], 'https://example.test/fiche(v2)?ref=12')]},
    {type:'list',kind:'bullet',items:[{runs:[run('Tube 316L')],checked:false,indent:0},{runs:[run('Code `A`',['code'])],checked:false,indent:2}]},
    {type:'list',kind:'ordered',items:[{runs:[run('Vérifier')],checked:false,indent:0},{runs:[run('Confirmer')],checked:false,indent:1}]},
    {type:'list',kind:'checklist',items:[{runs:[run('Essai non reçu')],checked:false,indent:0},{runs:[run('Plan reçu')],checked:true,indent:0}]},
  ]);
  const encoded=noteToMarkdown(original);expect(encoded.ok).toBe(true);if(!encoded.ok)return;
  expect(parseNoteMarkdown(encoded.value)).toEqual({ok:true,value:original});
});
it.each(['x`y','`edge`',' `edge` ','   ','** _ [x]','12 Nm','C:\\atelier\\'])('conserve exactement le code inline %s',text=>{
  const original=document([{type:'paragraph',align:'left',runs:[run(text,['code'])]}]);
  const encoded=noteToMarkdown(original);expect(encoded.ok).toBe(true);if(encoded.ok)expect(parseNoteMarkdown(encoded.value)).toEqual({ok:true,value:original});
});
it.each([
  {type:'table',header:true,rows:[[[run('IP65')]]]},
  {type:'image',attachment_id:'11111111-1111-4111-8111-111111111111',caption:'Plan conservé'},
  {type:'paragraph',align:'center',runs:[run('Centré')]},
  {type:'paragraph',align:'left',runs:[{...run('Couleur'),color:'#ff0000'}]},
  {type:'paragraph',align:'left',runs:[run('Souligné',['underline'])]},
  {type:'paragraph',align:'left',runs:[run('Barré',['strike'])]},
] as NoteBlock[])('refuse sans mutation un bloc riche non représentable $type',block=>{
  const original=document([block]),snapshot=JSON.stringify(original);
  expect(noteToMarkdown(original).ok).toBe(false);expect(JSON.stringify(original)).toBe(snapshot);
});
it.each(['**Réserve','`12 Nm','[doc](javascript:alert(1))','[doc](https://user:pass@example.test)','[doc](file:///C:/Agent/db)',
  '[a](mailto:fred@example.test?subject=x)','<script>alert(1)</script>','![plan](https://example.test/a.png)','| Article |','~~Validé~~','#### Réserve','5. Mesure'])('refuse un Markdown invalide ou hors du sous-ensemble : %s',text=>{
  expect(parseNoteMarkdown(text).ok).toBe(false);
});
it('permet HTML échappé en texte et ne crée jamais de bloc HTML ou lien actif non sûr',()=>{
  const result=parseNoteMarkdown('\\<script\\>12 Nm\\</script\\>');
  expect(result).toEqual({ok:true,value:document([paragraph('<script>12 Nm</script>')])});
});
it('ne supprime pas les antislashs ordinaires des chemins industriels',()=>{
  expect(parseNoteMarkdown('Dossier C:\\atelier\\')).toEqual({ok:true,value:document([paragraph('Dossier C:\\atelier\\')])});
});
it('préserve une note vide simple et refuse les séparations qui perdraient des blocs vides',()=>{
  expect(noteToMarkdown(blankNote())).toEqual({ok:true,value:''});
  expect(parseNoteMarkdown('')).toEqual({ok:true,value:blankNote()});
  expect(noteToMarkdown(document([paragraph('Avant'),{type:'paragraph',align:'left',runs:[]},paragraph('Après')])).ok).toBe(false);
});
it('vérifie les limites du schéma avant émission du contenu',()=>{
  const result=parseNoteMarkdown(Array.from({length:501},(_,index)=>`Paragraphe ${index}`).join('\n\n'));
  expect(result.ok).toBe(false);
  const long=parseNoteMarkdown('A'.repeat(6000));expect(long.ok).toBe(true);
  if(long.ok){expect(validNoteContent(long.value)).toBe(true);expect(long.value.blocks[0]).toHaveProperty('runs');}
});
