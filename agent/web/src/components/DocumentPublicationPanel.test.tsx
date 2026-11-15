import { beforeEach,afterEach,it,expect,vi } from 'vitest';
import { render,screen,fireEvent,waitFor,cleanup } from '@testing-library/react';
import { DocumentPublicationPanel } from './DocumentPublicationPanel';
import { publicationApi,pendingKey,type PublicationRecord,type PublicationCommand,type PublicationPreview } from '../lib/projectDocumentPublications';
import { documentApi,type DocumentWorkspace } from '../lib/projectDocuments';
const command:PublicationCommand={command_id:'stable',link_id:'link',relative_directory:'',replace_existing:false,reviewed:true,expected_revision:3,expected_preview_sha256:'a'.repeat(64)};
const record:PublicationRecord={project_id:'p1',job_id:'j1',job_revision:6,artifact_id:'copy',command_id:'stable',command,state:'succeeded',network_published:true,
  execution_blocked:false,needs_inspection:false,can_resume:true,can_abandon:false,destination:'D:/Fictif/CE.docx',candidate:'.candidate',receipt:{identity:'id',sha256:'b'.repeat(64),size_bytes:12},backup:null,backup_receipt:null,requested_revision:4,updated_revision:6};
const preview:PublicationPreview={project_id:'p1',job_id:'j1',job_revision:3,artifact_id:'copy',filename:'CE.docx',destination:'D:/Fictif/CE.docx',directory:'D:/Fictif',directory_identity:'id',
  preview_sha256:'a'.repeat(64),occupied:false,can_publish:true,blockers:[],publication_command_available:true,existing_receipt:null,link_id:'link',relative_directory:'',replace_existing:false,version:2};
const base={projectId:'p1',jobId:'j1',artifactId:'copy',revision:3,label:'Demande CE',active:true,canEdit:true,executionBlocked:false,jobActive:false,disabled:false,
  onBusy:vi.fn(),onDirty:vi.fn(),onChanged:vi.fn()};
beforeEach(()=>{localStorage.clear();vi.spyOn(documentApi,'workspace').mockResolvedValue({links:{items:[{id:'link',code:'doc',label:'Documents',path:'D:/Fictif',order:0}],total:1,offset:0,limit:100}} as DocumentWorkspace);
  vi.spyOn(publicationApi,'list').mockResolvedValue({project_id:'p1',job_id:'j1',job_revision:3,execution_blocked:false,items:[],total:0,offset:0,limit:20});
  vi.spyOn(publicationApi,'preview').mockResolvedValue(preview);vi.spyOn(publicationApi,'publish').mockResolvedValue(record);
  vi.spyOn(publicationApi,'abandon').mockResolvedValue({...record,state:'abandoned',can_resume:false,can_abandon:false});
});
afterEach(()=>{cleanup();vi.restoreAllMocks();vi.clearAllMocks();localStorage.clear();});
async function chooseLink(){await screen.findByRole('option',{name:/Documents.*D:\/Fictif/});
  fireEvent.change(screen.getByRole('combobox',{name:'Lien de destination'}),{target:{value:'link'}});}
async function inspect(){await chooseLink();
  await waitFor(()=>expect(screen.getByRole('button',{name:'Vérifier la destination'}).hasAttribute('disabled')).toBe(false));
  fireEvent.click(screen.getByRole('button',{name:'Vérifier la destination'}));await screen.findByText('CE.docx');}
it('exige une relecture et fige la commande avant son envoi',async()=>{
  render(<DocumentPublicationPanel {...base}/>);await inspect();expect(screen.getByRole('button',{name:'Publier la copie'}).hasAttribute('disabled')).toBe(true);
  fireEvent.click(screen.getByRole('checkbox',{name:'J’ai relu la destination'}));
  vi.mocked(publicationApi.publish).mockImplementation(async(_pid,_jid,_aid,cmd)=>{
    expect(JSON.parse(localStorage.getItem(pendingKey('p1','copy'))!)).toEqual(cmd);
    return {...record,command_id:cmd.command_id,command:cmd};});
  fireEvent.click(screen.getByRole('button',{name:'Publier la copie'}));await screen.findByText(/Reçu de publication enregistré/);
  expect(publicationApi.publish).toHaveBeenCalledOnce();expect(localStorage.getItem(pendingKey('p1','copy'))).toBeNull();
});
it('une modification de destination invalide l’aperçu et sa confirmation',async()=>{
  render(<DocumentPublicationPanel {...base}/>);await inspect();fireEvent.click(screen.getByRole('checkbox',{name:'J’ai relu la destination'}));
  fireEvent.change(screen.getByRole('textbox',{name:'Sous-dossier existant'}),{target:{value:'Copies'}});
  expect(screen.queryByRole('button',{name:'Publier la copie'})).toBeNull();expect(publicationApi.publish).not.toHaveBeenCalled();
});
it('une réponse perdue garde la même commande après démontage et rechargement',async()=>{
  vi.mocked(publicationApi.publish).mockRejectedValue(new Error('Réponse perdue'));
  const view=render(<DocumentPublicationPanel {...base}/>);await inspect();fireEvent.click(screen.getByRole('checkbox',{name:'J’ai relu la destination'}));
  fireEvent.click(screen.getByRole('button',{name:'Publier la copie'}));await screen.findByText('Réponse perdue');
  const first=vi.mocked(publicationApi.publish).mock.calls[0][3];view.unmount();render(<DocumentPublicationPanel {...base}/>);
  fireEvent.click(await screen.findByRole('button',{name:'Réessayer la même publication'}));await waitFor(()=>expect(publicationApi.publish).toHaveBeenCalledTimes(2));
  expect(vi.mocked(publicationApi.publish).mock.calls[1][3]).toEqual(first);
});
it('le lecteur et les historiques suspendus consultent sans commande ni source de destination',async()=>{
  vi.mocked(publicationApi.list).mockResolvedValue({project_id:'p1',job_id:'j1',job_revision:7,execution_blocked:true,items:[{...record,execution_blocked:true,can_resume:false}],total:1,offset:0,limit:20});
  render(<DocumentPublicationPanel {...base} canEdit={false} executionBlocked/>);await screen.findByText('Publication enregistrée');
  expect(documentApi.workspace).not.toHaveBeenCalled();expect(screen.queryByRole('combobox')).toBeNull();
  expect(screen.queryByRole('button',{name:'Revérifier le reçu et les fichiers'})).toBeNull();
  expect(publicationApi.publish).not.toHaveBeenCalled();
});
it('remplacer requiert un nouvel aperçu et affiche la sauvegarde conservée',async()=>{
  render(<DocumentPublicationPanel {...base}/>);await chooseLink();
  fireEvent.click(screen.getByRole('checkbox',{name:/Remplacer le fichier existant/}));
  vi.mocked(publicationApi.preview).mockResolvedValue({...preview,replace_existing:true,occupied:true,existing_receipt:{identity:'old',sha256:'c'.repeat(64),size_bytes:2000}});
  fireEvent.click(screen.getByRole('button',{name:'Vérifier la destination'}));await screen.findByText(/Original à conserver/);
  expect(vi.mocked(publicationApi.preview).mock.calls[0][3].replace_existing).toBe(true);
  expect(screen.getByRole('button',{name:'Sauvegarder l’original et publier'}).hasAttribute('disabled')).toBe(true);
});
it('clôturer une intention exige confirmation et la révision lue, sans supprimer le candidat',async()=>{
  const unknown={...record,state:'requested' as const,network_published:false,receipt:null,needs_inspection:true,can_abandon:true,can_resume:false};
  vi.mocked(publicationApi.list).mockResolvedValue({project_id:'p1',job_id:'j1',job_revision:4,execution_blocked:false,items:[unknown],total:1,offset:0,limit:20});
  render(<DocumentPublicationPanel {...base}/>);const button=await screen.findByRole('button',{name:'Clôturer l’intention incertaine'});expect(button.hasAttribute('disabled')).toBe(true);
  fireEvent.click(screen.getByRole('checkbox',{name:/Je confirme la clôture/}));fireEvent.click(button);
  await waitFor(()=>expect(publicationApi.abandon).toHaveBeenCalledWith('p1','j1','copy','stable',{expected_revision:4,retain_files:true,reviewed:true},expect.any(AbortSignal)));
  expect(publicationApi.publish).not.toHaveBeenCalled();
});
it('un volet inactif ne lit ni liens ni reçus',()=>{
  render(<DocumentPublicationPanel {...base} active={false}/>);expect(publicationApi.list).not.toHaveBeenCalled();expect(documentApi.workspace).not.toHaveBeenCalled();
});
it('interrompre l’attente conserve la commande et transmet l’annulation',async()=>{
  localStorage.setItem(pendingKey('p1','copy'),JSON.stringify(command));let signal:AbortSignal|undefined;
  vi.mocked(publicationApi.publish).mockImplementation((_pid,_jid,_aid,_cmd,s)=>new Promise((_resolve,reject)=>{
    signal=s;s?.addEventListener('abort',()=>reject(new DOMException('Annulée','AbortError')));}));
  render(<DocumentPublicationPanel {...base}/>);fireEvent.click(await screen.findByRole('button',{name:'Réessayer la même publication'}));
  fireEvent.click(await screen.findByRole('button',{name:'Interrompre l’attente de publication'}));
  await waitFor(()=>expect(signal?.aborted).toBe(true));expect(JSON.parse(localStorage.getItem(pendingKey('p1','copy'))!)).toEqual(command);
});
