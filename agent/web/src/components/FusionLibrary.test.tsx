import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {SourcesLibrary} from './SourcesLibrary';
import {FusionInsights} from './FusionInsights';
import {fusionSources,type LibrarySource} from '../lib/fusionSources';
import {fusionInsights,type FusionSettings,type FusionStats} from '../lib/fusionInsights';
import {meetingCapture,type CaptureSnapshot} from '../lib/meetingCapture';
import type {PortfolioRow} from '../lib/api';
import {meetingSessions} from '../lib/meetingSessions';
const rows=[{id:'erp-a',brain_project_id:'brain-a',code:'A-100',title:'Projet industriel'} as PortfolioRow];
const source:LibrarySource={id:'source-1',source_id:'source-1',title:'Note validée',kind:'note',project_id:'brain-a',erp_project_id:'erp-a',project_code:'A-100',labels:['Mécanique'],status:'resolved',current:true,date:'2026-10-11',extraction_status:'extracted',index_status:'indexed'};
const settings:FusionSettings={enabled:false,proactive_enabled:false,mode:'network',onboarding_complete:false,
  capabilities:{enabled:false,capture:{durable:true,max_upload_mb:50,max_duration_minutes:120,tracks:['mic'],browser_permission_required:true},
    transcription:{batch_ready:false,live_ready:false,detail:'Moteur absent'},notes:{staging:true,erp_projection:true}}};
const stats:FusionStats={sources:{total:1,by_type:{note:1},extracted:1,indexed:1,current:1},sessions:{total:0,by_state:{},duration_seconds:0,audio_bytes:0},
  assistant:{answers:0,stale:0,enhancements:0,p50_seconds:null,p95_seconds:null,tokens:null},engines:{speech:{ready:false},generation:{placement:'network',configured:true}},
  index:{text_passages:1,profiles:[],size_bytes:200},formulas:{sources:'Sources présentes'}};
beforeEach(()=>{
  vi.spyOn(fusionInsights,'readiness').mockReturnValue(new Promise(()=>{}));
  vi.spyOn(fusionSources,'list').mockResolvedValue({items:[source],total:1,offset:0,limit:25,has_next:false,labels:['Mécanique']});
  vi.spyOn(fusionSources,'driveStatus').mockResolvedValue({configured:false});
  vi.spyOn(fusionInsights,'stats').mockResolvedValue(stats);vi.spyOn(fusionInsights,'settings').mockResolvedValue(settings);
});

it('garde les notes ERP non projetées consultables dans Documents et hors des labels',async()=>{
  vi.mocked(fusionSources.list).mockResolvedValue({items:[{...source,id:'erp-note:note-1',source_id:null,index_status:'not_indexed'}],total:1,offset:0,limit:25,has_next:false,labels:[]});
  const open=vi.fn(),project=vi.fn();render(<SourcesLibrary rows={rows} onOpenSource={open} onOpenProject={project}/>);
  fireEvent.click(await screen.findByRole('button',{name:'Note validée'}));
  expect(project).toHaveBeenCalledWith('erp-a','documents');expect(open).not.toHaveBeenCalled();
  expect(screen.getByRole('checkbox',{name:'Sélectionner Note validée'})).toHaveProperty('disabled',true);
});
it('nomme et télécharge la version exacte d’une note conservée hors du rappel courant',async()=>{
  vi.mocked(fusionSources.list).mockResolvedValue({items:[{...source,version_id:'note-version-2',current:false}],total:1,offset:0,limit:25,has_next:false,labels:[]});
  render(<SourcesLibrary rows={rows} onOpenSource={vi.fn()}/>);
  const link=await screen.findByRole('link',{name:'Télécharger la version de note : Note validée'});
  expect(screen.getByText(/Texte extrait · Indexée/)).toBeTruthy();
  expect(link.getAttribute('href')).toBe('/api/v1/workspace/sources/source-1/original');
  expect(screen.getByText('Version conservée · version hors rappel courant')).toBeTruthy();
});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
it('importe un audio téléphonique avec sa transcription depuis Sources',async()=>{
  vi.mocked(fusionSources.list).mockResolvedValue({items:[source],total:1,offset:0,limit:25,has_next:false,labels:[],can_import_audio:true});
  const upload=vi.spyOn(fusionSources,'audio').mockResolvedValue({status:'resolution_pending'});
  render(<SourcesLibrary rows={rows} onOpenSource={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button',{name:'Ajouter une source'}));
  fireEvent.click(await screen.findByText('Importer un enregistrement audio'));
  const form=screen.getByRole('form',{name:'Importer un enregistrement audio'});
  fireEvent.change(within(form).getByLabelText('Type d’enregistrement'),{target:{value:'phone'}});
  fireEvent.change(within(form).getByLabelText('Transcription existante'),{target:{value:'Texte fictif'}});
  fireEvent.submit(form);
  await screen.findByText('Audio importé. Il reste à rattacher dans Sources.');
  expect(upload.mock.calls[0][0].get('source_type')).toBe('phone');
  expect(upload.mock.calls[0][0].get('transcript')).toBe('Texte fictif');
  expect(upload.mock.calls[0][0].has('candidate_project_id')).toBe(false);
});
it('rattache une source en attente à un projet accessible depuis la bibliothèque',async()=>{
  window.history.replaceState(null,'','/kiara/app/sources?status=pending');
  try {
    vi.mocked(fusionSources.list).mockResolvedValue({items:[{...source,status:'resolution_pending'}],
      total:1,offset:0,limit:25,has_next:false,labels:[]});
    vi.spyOn(fusionSources,'destinations').mockResolvedValue([{id:'brain-seul',code:'B-42',name:'Projet de connaissance'}]);
    const attach=vi.spyOn(fusionSources,'attach').mockResolvedValue({source_id:'source-1',project_id:'brain-seul'});
    render(<SourcesLibrary rows={rows} onOpenSource={vi.fn()}/>);
    await screen.findByRole('button',{name:'Note validée'});
    expect(fusionSources.list).toHaveBeenCalledWith(expect.objectContaining({status:'pending'}),expect.anything());
    fireEvent.click(screen.getByLabelText('Détails de Note validée'));
    fireEvent.click(screen.getByRole('button',{name:'Rattacher au projet'}));
    fireEvent.change(await screen.findByLabelText('Projet de destination'),{target:{value:'brain-seul'}});
    fireEvent.click(screen.getByRole('button',{name:'Confirmer le rattachement'}));
    await screen.findByText('Source rattachée au projet.');
    expect(attach).toHaveBeenCalledOnce();
    expect(attach).toHaveBeenCalledWith('source-1','brain-seul');
  } finally {
    window.history.replaceState(null,'','/');
  }
});
it('filtre avec identité Brain et ouvre la source canonique sans confondre le projet ERP',async()=>{
  const open=vi.fn();render(<SourcesLibrary rows={rows} onOpenSource={open}/>);
  await screen.findByRole('button',{name:'Note validée'});
  fireEvent.change(screen.getByLabelText('Projet'),{target:{value:'erp-a'}});
  await waitFor(()=>expect(fusionSources.list).toHaveBeenLastCalledWith(expect.objectContaining({project_id:'brain-a',offset:0}),expect.any(AbortSignal)));
  fireEvent.click(screen.getByRole('button',{name:'Note validée'}));expect(open).toHaveBeenCalledWith('source-1','Note validée');
});
it('ouvre la préparation d’une séance depuis Sources sans créer ni enregistrer et propose le projet ERP choisi',async()=>{
  const prepare=vi.fn(),create=vi.spyOn(meetingSessions,'create'),command=vi.spyOn(meetingSessions,'command'),capture=vi.spyOn(meetingCapture,'start');
  const {rerender}=render(<SourcesLibrary rows={rows} onOpenSource={vi.fn()} onCreateMeeting={prepare}/>);
  fireEvent.click(screen.getByRole('button',{name:'Nouvelle séance'}));
  expect(prepare).toHaveBeenLastCalledWith(undefined);
  fireEvent.change(screen.getByLabelText('Projet'),{target:{value:'erp-a'}});
  fireEvent.click(screen.getByRole('button',{name:'Nouvelle séance'}));
  expect(prepare).toHaveBeenLastCalledWith('erp-a');
  // The old select value must never become a hidden project default after access disappears.
  rerender(<SourcesLibrary rows={[]} onOpenSource={vi.fn()} onCreateMeeting={prepare}/>);
  fireEvent.click(screen.getByRole('button',{name:'Nouvelle séance'}));
  expect(prepare).toHaveBeenLastCalledWith(undefined);
  expect(create).not.toHaveBeenCalled();expect(command).not.toHaveBeenCalled();expect(capture).not.toHaveBeenCalled();
});
it('sépare le type Document du format PDF et conserve les actions de sa source exacte',async()=>{
  const documents:LibrarySource[]=[
    {...source,id:'pdf-1',source_id:'pdf-1',kind:'document',title:'Plan.pdf',file_format:'pdf',mime_type:'application/pdf'},
    {...source,id:'png-1',source_id:'png-1',kind:'document',title:'Plan.png',file_format:'png',mime_type:'image/png'},
    {...source,id:'txt-1',source_id:'txt-1',kind:'document',title:'Plan.txt',file_format:'txt',mime_type:'text/plain'},
  ];
  vi.mocked(fusionSources.list).mockImplementation(filters=>{
    const items=filters?.file_format==='pdf'?documents.slice(0,1):documents;
    return Promise.resolve({items,total:items.length,offset:0,limit:25,has_next:false,labels:[]});
  });
  const open=vi.fn();render(<SourcesLibrary rows={rows} onOpenSource={open}/>);
  await screen.findByRole('button',{name:'Plan.png'});
  fireEvent.change(screen.getByLabelText('Projet'),{target:{value:'erp-a'}});
  fireEvent.change(screen.getByLabelText('Type de source'),{target:{value:'document'}});
  fireEvent.change(screen.getByLabelText('Format',{exact:true}),{target:{value:'pdf'}});
  await waitFor(()=>expect(fusionSources.list).toHaveBeenLastCalledWith(expect.objectContaining({
    project_id:'brain-a',source_type:'document',file_format:'pdf',offset:0,
  }),expect.any(AbortSignal)));
  await waitFor(()=>expect(screen.queryByRole('button',{name:'Plan.png'})).toBeNull());
  expect(screen.queryByRole('button',{name:'Plan.txt'})).toBeNull();
  const pdf=screen.getByRole('button',{name:'Plan.pdf'});
  expect(within(pdf.closest('tr')!).getByText('PDF')).toBeTruthy();
  expect(within(pdf.closest('tr')!).getByText('Document')).toBeTruthy();
  fireEvent.click(pdf);expect(open).toHaveBeenCalledExactlyOnceWith('pdf-1','Plan.pdf');
  expect(screen.getByRole('link',{name:'Ouvrir l’original : Plan.pdf'}).getAttribute('href')).toBe('/api/v1/workspace/sources/pdf-1/original');
});
it('ne présente aucun format fictif pour une Note canonique et garde le choix inconnu distinct',async()=>{
  render(<SourcesLibrary rows={rows} onOpenSource={vi.fn()}/>);
  const note=await screen.findByRole('button',{name:'Note validée'});
  expect(within(note.closest('tr')!).queryByText('PDF')).toBeNull();
  fireEvent.change(screen.getByLabelText('Format',{exact:true}),{target:{value:'unknown'}});
  fireEvent.click(screen.getByText(/Périmètre et filtres/));
  await waitFor(()=>expect(fusionSources.list).toHaveBeenLastCalledWith(expect.objectContaining({
    source_type:'all',file_format:'unknown',offset:0,
  }),expect.any(AbortSignal)));
  expect(screen.getByRole('option',{name:'Sans format de fichier reconnu'})).toBeTruthy();
});
it.each([
  {modality:'pdf',name:'Page PDF',locator:{physical_page:2,artifact_id:'page-2'},label:'Page physique : 2'},
  {modality:'text',name:'Texte',locator:{sheet:'Devis',range:'A4:C4',artifact_id:'row-4'},label:'Feuille : Devis · Plage : A4:C4'},
  {modality:'audio',name:'Audio',locator:{start_ms:5000,end_ms:10000,kind:'audio'},label:'Début (ms) : 5000 · Fin (ms) : 10000'},
])('transmet le repère $name exact au clic du résultat de recherche',async({modality,name,locator,label})=>{
  const hit={id:'hit-version-2',source_id:'source-version-2',project_id:'brain-a',modality,text:'Texte complet',excerpt:'Ne pas dépasser 12 Nm.',
    locator,score:.91,source_url:'/v1/sources/source-version-2',profile_key:'profile-qa'};
  vi.spyOn(fusionSources,'search').mockResolvedValue({items:[hit]});
  const open=vi.fn();render(<SourcesLibrary rows={rows} onOpenSource={open}/>);
  fireEvent.change(screen.getByLabelText('Rechercher une source'),{target:{value:'couple visserie'}});
  fireEvent.click(screen.getByText(/Périmètre et filtres/));
  fireEvent.click(screen.getByRole('button',{name:'Rechercher dans le contenu des sources'}));
  fireEvent.click(await screen.findByRole('button',{name:`Consulter la source · ${name}`}));
  expect(open).toHaveBeenCalledExactlyOnceWith('source-version-2',undefined,[{
    source_id:hit.source_id,source_url:hit.source_url,excerpt:hit.excerpt,locator,
  }]);
  expect(screen.getByText(label)).toBeTruthy();
  expect(screen.queryByText(/Page imprimée|profile-qa|artifact_id/)).toBeNull();
});
it('conserve les filtres montés dans leur volet, annonce les valeurs actives et restaure le focus avec Échap',async()=>{
  render(<SourcesLibrary rows={rows} onOpenSource={vi.fn()}/>);await screen.findByRole('button',{name:'Note validée'});
  const summary=screen.getByText('Périmètre et filtres'),details=summary.closest('details')!;
  expect(details.open).toBe(false);fireEvent.click(summary);
  const type=screen.getByLabelText('Type de source');fireEvent.change(type,{target:{value:'note'}});
  fireEvent.change(screen.getByLabelText('Format',{exact:true}),{target:{value:'unknown'}});
  fireEvent.keyDown(type,{key:'Escape'});
  expect(details.open).toBe(false);expect(document.activeElement).toBe(summary);
  expect(summary.textContent).toBe('Périmètre et filtres · Note · Format non reconnu');
  expect(screen.getByLabelText('Type de source')).toBe(type);expect(type).toHaveProperty('value','note');
  expect(screen.getByLabelText('Projet')).toHaveProperty('value','');
  await waitFor(()=>expect(fusionSources.list).toHaveBeenLastCalledWith(expect.objectContaining({source_type:'note',file_format:'unknown',offset:0}),expect.any(AbortSignal)));
});
it('affiche le total serveur et commute liste grille avec les mêmes identités sans fabriquer des comptes de format',async()=>{
  vi.mocked(fusionSources.list).mockResolvedValue({items:[source],total:63,offset:0,limit:25,has_next:true,labels:['Mécanique']});
  const open=vi.fn();render(<SourcesLibrary rows={rows} onOpenSource={open}/>);await screen.findByText('63 sources');
  expect(screen.getByRole('button',{name:'Afficher la liste'}).getAttribute('aria-pressed')).toBe('true');
  const formats=screen.getByLabelText('Formats des sources');expect(formats.textContent).toBe('PDFPNGTXTXLSX');
  fireEvent.click(screen.getByRole('button',{name:'Afficher la grille'}));
  expect(screen.getByRole('button',{name:'Afficher la grille'}).getAttribute('aria-pressed')).toBe('true');
  fireEvent.click(screen.getByRole('button',{name:'Note validée'}));expect(open).toHaveBeenCalledWith('source-1','Note validée');
  fireEvent.click(screen.getByRole('button',{name:'Afficher la liste'}));expect(screen.getByRole('table')).toBeTruthy();
  expect(screen.getByRole('link',{name:'Ouvrir l’original : Note validée'}).getAttribute('href')).toBe('/api/v1/workspace/sources/source-1/original');
});
it('filtre les chips de labels et ouvre leur remplacement explicite seulement après sélection',async()=>{
  const save=vi.spyOn(fusionSources,'labels').mockResolvedValue({source_id:'source-1',labels:['À confirmer']});
  render(<SourcesLibrary rows={rows} onOpenSource={vi.fn()}/>);await screen.findByRole('button',{name:'Note validée'});
  fireEvent.click(screen.getByRole('button',{name:'Ajouter un label'}));
  expect(screen.getByText(/Sélectionnez une ou plusieurs sources/)).toBeTruthy();expect(save).not.toHaveBeenCalled();
  const band=screen.getByLabelText('Labels des sources');fireEvent.click(within(band).getByRole('button',{name:'Mécanique'}));
  await waitFor(()=>expect(fusionSources.list).toHaveBeenLastCalledWith(expect.objectContaining({label:'Mécanique',offset:0}),expect.any(AbortSignal)));
  fireEvent.click(screen.getByRole('checkbox',{name:'Sélectionner Note validée'}));fireEvent.click(screen.getByRole('button',{name:'Ajouter un label'}));
  const editor=screen.getByLabelText('Labels de la sélection');expect(document.activeElement).toBe(editor);
  expect(screen.getByText(/Cette opération remplace tous les labels/)).toBeTruthy();
  fireEvent.change(editor,{target:{value:'À confirmer'}});fireEvent.click(screen.getByRole('button',{name:'Remplacer les labels'}));
  await waitFor(()=>expect(save).toHaveBeenCalledExactlyOnceWith('source-1',['À confirmer']));
});
it('sélectionne la source sans labels de la ligne pour ouvrir le même éditeur sans mutation automatique',async()=>{
  vi.mocked(fusionSources.list).mockResolvedValue({items:[{...source,labels:[]}],total:1,offset:0,limit:25,has_next:false,labels:[]});
  const save=vi.spyOn(fusionSources,'labels');render(<SourcesLibrary rows={rows} onOpenSource={vi.fn()}/>);
  fireEvent.click(await screen.findByRole('button',{name:'Ajouter un label à Note validée'}));
  expect(screen.getByRole('checkbox',{name:'Sélectionner Note validée'})).toHaveProperty('checked',true);
  expect(document.activeElement).toBe(screen.getByLabelText('Labels de la sélection'));expect(save).not.toHaveBeenCalled();
});
it('garde un label de quatre-vingts caractères exact dans sa chip, le filtre et son résumé',async()=>{
  const label='W'.repeat(80);
  vi.mocked(fusionSources.list).mockResolvedValue({items:[{...source,labels:[label]}],total:1,offset:0,limit:25,has_next:false,labels:[label]});
  render(<SourcesLibrary rows={rows} onOpenSource={vi.fn()}/>);
  const band=screen.getByLabelText('Labels des sources');
  fireEvent.click(await within(band).findByRole('button',{name:label}));
  expect(screen.getByText(`Périmètre et filtres · ${label}`).textContent).toBe(`Périmètre et filtres · ${label}`);
  await waitFor(()=>expect(fusionSources.list).toHaveBeenLastCalledWith(expect.objectContaining({label}),expect.any(AbortSignal)));
});
it.each([{configured:true},{configured:true,enabled:false}])('masque Drive désactivé ou sans capacité explicite tout en gardant les imports locaux (%j)',async(status)=>{
  vi.mocked(fusionSources.driveStatus).mockResolvedValue(status);
  const driveImport=vi.spyOn(fusionSources,'drive'),connect=vi.spyOn(fusionSources,'connectDrive');
  render(<SourcesLibrary rows={rows} onOpenSource={vi.fn()}/>);await screen.findByRole('button',{name:'Note validée'});
  fireEvent.click(screen.getByRole('button',{name:'Ajouter une source'}));
  await waitFor(()=>expect(fusionSources.driveStatus).toHaveBeenCalledOnce());
  expect(screen.queryByLabelText('Fichier Google Drive')).toBeNull();
  expect(screen.queryByText('Connexion avancée Google Drive')).toBeNull();
  expect(screen.queryByText(/Google Drive :/)).toBeNull();
  expect(screen.queryByLabelText('Jeton d’accès Google')).toBeNull();
  expect(screen.getByLabelText('Fichiers sélectionnés')).toBeTruthy();
  expect(screen.getByLabelText('Dossier choisi')).toBeTruthy();
  expect(screen.getByLabelText('Page ou document web')).toBeTruthy();
  expect(screen.getByLabelText('Exporter puis sélectionner un calendrier ICS')).toBeTruthy();
  expect(driveImport).not.toHaveBeenCalled();expect(connect).not.toHaveBeenCalled();
});
it('conserve le connecteur existant derrière une activation explicite distincte',async()=>{
  vi.mocked(fusionSources.driveStatus).mockResolvedValue({configured:true,enabled:true});
  render(<SourcesLibrary rows={rows} onOpenSource={vi.fn()}/>);await screen.findByRole('button',{name:'Note validée'});
  fireEvent.click(screen.getByRole('button',{name:'Ajouter une source'}));
  expect(await screen.findByLabelText('Fichier Google Drive')).toBeTruthy();
  expect(screen.getByText('Connexion avancée Google Drive')).toBeTruthy();
  expect(screen.getByLabelText('Jeton d’accès Google')).toBeTruthy();
});
it('affiche les échecs partiels d’un import et compte les fichiers déjà conservés',async()=>{
  vi.spyOn(fusionSources,'file').mockResolvedValueOnce({unchanged:true}).mockRejectedValueOnce(new Error('Format non extrait'));
  render(<SourcesLibrary rows={rows} onOpenSource={vi.fn()}/>);await screen.findByRole('button',{name:'Note validée'});
  fireEvent.change(screen.getByLabelText('Projet'),{target:{value:'erp-a'}});fireEvent.click(screen.getByRole('button',{name:'Ajouter une source'}));
  fireEvent.change(screen.getByLabelText('Fichiers sélectionnés'),{target:{files:[new File(['one'],'one.pdf'),new File(['two'],'two.bad')]}});
  await screen.findByText('0 import(s), 1 fichier(s) déjà conservé(s), 1 erreur(s).');
  expect(screen.getByText('two.bad : Format non extrait')).toBeTruthy();
  expect(fusionSources.file).toHaveBeenCalledWith('brain-a',expect.any(File),false);
});
it('rend les relations connues accessibles au clavier sans inventer de proximité',async()=>{
  vi.spyOn(fusionSources,'graph').mockResolvedValue({nodes:[{id:'node',label:'Note validée',kind:'source',project_id:'brain-a',source_id:'source-1'}],edges:[],truncated:true});
  const open=vi.fn();render(<SourcesLibrary rows={rows} onOpenSource={open}/>);
  fireEvent.click(screen.getByRole('tab',{name:'Vue des relations'}));
  const node=await screen.findByRole('button',{name:'Source : Note validée'});fireEvent.keyDown(node,{key:'Enter'});
  fireEvent.click(screen.getByRole('button',{name:'Consulter la source'}));expect(open).toHaveBeenCalledWith('source-1','Note validée');
  expect(screen.getByText(/La vue est limitée/)).toBeTruthy();
});
it('retire la source sélectionnée du graphe dès le changement de projet et après sa réponse',async()=>{
  let resolveB!:(graph:Awaited<ReturnType<typeof fusionSources.graph>>)=>void;
  const graphB=new Promise<Awaited<ReturnType<typeof fusionSources.graph>>>(resolve=>{resolveB=resolve;});
  vi.spyOn(fusionSources,'graph').mockImplementation(project=>project==='brain-b'?graphB:Promise.resolve({
    nodes:[{id:'node-a',label:'Source ancienne A',kind:'source',project_id:'brain-a',source_id:'source-a'}],edges:[],truncated:false}));
  const open=vi.fn();render(<SourcesLibrary rows={[...rows,{id:'erp-b',brain_project_id:'brain-b',code:'B-200',title:'Autre projet'} as PortfolioRow]} onOpenSource={open}/>);
  fireEvent.change(screen.getByLabelText('Projet'),{target:{value:'erp-a'}});
  fireEvent.click(screen.getByRole('tab',{name:'Vue des relations'}));
  fireEvent.click(await screen.findByRole('button',{name:'Source : Source ancienne A'}));
  expect(screen.getByRole('button',{name:'Consulter la source'})).toBeTruthy();
  fireEvent.change(screen.getByLabelText('Projet'),{target:{value:'erp-b'}});
  // Old source actions must disappear while the new project request is pending.
  expect(screen.queryByRole('button',{name:'Consulter la source'})).toBeNull();
  await waitFor(()=>expect(fusionSources.graph).toHaveBeenLastCalledWith('brain-b',expect.any(AbortSignal),0));
  resolveB({nodes:[{id:'node-b',label:'Source courante B',kind:'source',project_id:'brain-b',source_id:'source-b'}],edges:[],truncated:false});
  fireEvent.click(await screen.findByRole('button',{name:'Source : Source courante B'}));
  fireEvent.click(screen.getByRole('button',{name:'Consulter la source'}));
  expect(open).toHaveBeenCalledExactlyOnceWith('source-b','Source courante B');
  expect(screen.queryByText('Source ancienne A')).toBeNull();
});
it('retire aussi les actions de la liste précédente pendant le chargement d’un nouveau projet',async()=>{
  let resolveB!:(page:Awaited<ReturnType<typeof fusionSources.list>>)=>void;
  const pageB=new Promise<Awaited<ReturnType<typeof fusionSources.list>>>(resolve=>{resolveB=resolve;});
  vi.mocked(fusionSources.list).mockImplementation(filters=>filters?.project_id==='brain-b'?pageB:Promise.resolve({items:[source],total:1,offset:0,limit:25,has_next:false,labels:[]}));
  const open=vi.fn();render(<SourcesLibrary rows={[...rows,{id:'erp-b',brain_project_id:'brain-b',code:'B-200',title:'Autre projet'} as PortfolioRow]} onOpenSource={open}/>);
  await screen.findByRole('button',{name:'Note validée'});
  fireEvent.change(screen.getByLabelText('Projet'),{target:{value:'erp-b'}});
  expect(screen.queryByRole('button',{name:'Note validée'})).toBeNull();
  expect(screen.queryByRole('link',{name:'Ouvrir l’original : Note validée'})).toBeNull();
  await waitFor(()=>expect(fusionSources.list).toHaveBeenLastCalledWith(expect.objectContaining({project_id:'brain-b'}),expect.any(AbortSignal)));
  resolveB({items:[{...source,id:'source-b',source_id:'source-b',title:'Source B',project_id:'brain-b'}],total:1,offset:0,limit:25,has_next:false,labels:[]});
  fireEvent.click(await screen.findByRole('button',{name:'Source B'}));
  expect(open).toHaveBeenCalledExactlyOnceWith('source-b','Source B');
});
it('ne modifie aucun réglage au montage et conserve la distinction configured/ready et métrique absente',async()=>{
  vi.mocked(fusionInsights.stats).mockResolvedValue({...stats,index:{...stats.index,text_passages:null}});
  const save=vi.spyOn(fusionInsights,'save').mockResolvedValue({...settings,enabled:true,mode:'local'});
  const view=render(<FusionInsights rows={rows}/>);await screen.findByText('Configurée ; génération à vérifier');
  expect(save).not.toHaveBeenCalled();expect(screen.getAllByText('Indisponible').length).toBeGreaterThan(0);
  expect(screen.getByRole('heading',{name:'Passages recherchables'}).closest('article')?.querySelector('strong')?.textContent).toBe('Indisponible');
  expect(screen.queryByRole('tab',{name:'Préparation et réglages'})).toBeNull();
  view.rerender(<FusionInsights rows={rows} initialTab="preparation"/>);
  fireEvent.click(screen.getByLabelText('Activer l’espace de séance'));
  fireEvent.change(screen.getByLabelText('Exécution des nouveaux traitements'),{target:{value:'local'}});
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer les réglages'}));
  await waitFor(()=>expect(save).toHaveBeenCalledWith({enabled:true,live_transcription_enabled:false,proactive_enabled:false,auto_enhancement_enabled:false,mode:'local',onboarding_complete:false}));
});
it('sépare les réponses proactives et les enrichissements opt-in, sans les activer au montage',async()=>{
  const save=vi.spyOn(fusionInsights,'save').mockResolvedValue({...settings,enabled:true,auto_enhancement_enabled:true});
  render(<FusionInsights rows={rows} initialTab="preparation"/>);
  const automatic=await screen.findByLabelText('Proposer des enrichissements des notes automatiquement');
  expect(automatic).toHaveProperty('checked',false);
  expect(screen.getByLabelText('Proposer des réponses aux questions entendues automatiquement')).toHaveProperty('checked',false);
  expect(save).not.toHaveBeenCalled();
  fireEvent.click(screen.getByLabelText('Activer l’espace de séance'));fireEvent.click(automatic);
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer les réglages'}));
  await waitFor(()=>expect(save).toHaveBeenCalledExactlyOnceWith({enabled:true,live_transcription_enabled:false,proactive_enabled:false,auto_enhancement_enabled:true,mode:'network',onboarding_complete:false}));
  expect(screen.getByText(/Vos modifications non enregistrées ne participent pas à l’analyse/)).toBeTruthy();
});
it.each(['recording','pending'] as const)('préserve une capture %s et refuse la désactivation avant sa conservation',async(phase)=>{
  vi.mocked(fusionInsights.settings).mockResolvedValue({...settings,enabled:true});
  const capture:CaptureSnapshot={sessionId:'session-1',title:'Séance active',phase,tracks:['mic'],seconds:12,totalBytes:200,savedBytes:100,pending:phase==='pending'?1:0,error:''};
  const snapshot=vi.spyOn(meetingCapture,'getSnapshot').mockReturnValue(capture);
  const stop=vi.spyOn(meetingCapture,'stop'),save=vi.spyOn(fusionInsights,'save');
  render(<FusionInsights rows={rows} initialTab="preparation"/>);
  fireEvent.click(await screen.findByLabelText('Activer l’espace de séance'));
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer les réglages'}));
  expect((await screen.findByRole('alert')).textContent).toContain('avant de désactiver l’espace de séance');
  expect(save).not.toHaveBeenCalled();expect(stop).not.toHaveBeenCalled();expect(snapshot()).toBe(capture);
});
