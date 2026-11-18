import {beforeEach,afterEach,expect,it,vi} from 'vitest';
import {meetingSessions, type SessionCommand} from './meetingSessions';
import {request} from './http';
import {HttpError} from './httpError';
vi.mock('./http',()=>({request:vi.fn()}));
beforeEach(()=>{localStorage.clear();});afterEach(()=>{vi.restoreAllMocks();vi.mocked(request).mockReset();});
it('lit uniquement la version staging explicitement ciblée dans sa séance',async()=>{
  vi.mocked(request).mockResolvedValue({id:'v1',session_id:'sid'});const controller=new AbortController();
  await meetingSessions.noteVersion('sid','v1',controller.signal);
  expect(request).toHaveBeenCalledWith('/api/v1/meeting-sessions/sid/note-versions/v1',{signal:controller.signal},30_000);
});
it('lit l’historique d’un contexte avec identifiants répétés triés et dédupliqués',async()=>{
  vi.mocked(request).mockResolvedValue({items:[]});const controller=new AbortController();
  await meetingSessions.askHistory('sid','sources',['b','a','a'],controller.signal);
  expect(request).toHaveBeenCalledWith('/api/v1/meeting-sessions/sid/ask?scope=sources&source_ids=a&source_ids=b',{signal:controller.signal},30_000);
});
it('envoie l’épinglage explicite dans la séance concernée',async()=>{
  vi.mocked(request).mockResolvedValue({id:'answer',pinned:true});await meetingSessions.pinAnswer('sid','answer',true);
  expect(request).toHaveBeenCalledWith('/api/v1/meeting-sessions/sid/live-answers/answer/pin',{method:'PUT',body:'{"pinned":true}'},30_000);
});
it('enregistre et retire un avis explicite pour le type de réponse ciblé',async()=>{
  vi.mocked(request).mockResolvedValue({id:'answer',kind:'ask',useful:true});
  await meetingSessions.rateAnswer('sid','ask','answer',true);
  expect(request).toHaveBeenLastCalledWith('/api/v1/meeting-sessions/sid/answers/ask/answer/feedback',{
    method:'PUT',body:'{"useful":true}'},30_000);
  await meetingSessions.rateAnswer('sid','live','answer',null);
  expect(request).toHaveBeenLastCalledWith('/api/v1/meeting-sessions/sid/answers/live/answer/feedback',{
    method:'PUT',body:'{"useful":null}'},30_000);
});
it('rejoue la commande préparée de finalisation même après rechargement de la révision',async()=>{
  vi.mocked(request).mockRejectedValueOnce(new Error('Réseau absent')).mockResolvedValueOnce({id:'sid',state:'completed',revision:6});
  vi.spyOn(globalThis,'fetch').mockRejectedValue(new Error('Réseau absent'));
  const first={command_id:'command-a',expected_revision:4};
  await expect(meetingSessions.command('sid','finalize',first)).rejects.toThrow('Réseau absent');
  await meetingSessions.command('sid','finalize',{command_id:'command-b',expected_revision:5});
  expect(JSON.parse(String(vi.mocked(request).mock.calls[1][1]?.body))).toEqual(first);
  expect(localStorage.getItem('agent.meeting-command.v1.sid.finalize')).toBeNull();
});
it('autorise une nouvelle préparation seulement après vérification du rejet serveur',async()=>{
  vi.mocked(request).mockRejectedValueOnce(new Error('Révision différente')).mockResolvedValueOnce({id:'sid',state:'paused',revision:6});
  vi.spyOn(globalThis,'fetch').mockResolvedValue({ok:true,status:200,json:async()=>({id:'command-a',kind:'pause',status:'rejected'})} as Response);
  await expect(meetingSessions.command('sid','pause',{command_id:'command-a',expected_revision:4})).rejects.toThrow('Révision différente');
  await meetingSessions.command('sid','pause',{command_id:'command-b',expected_revision:5});
  expect(JSON.parse(String(vi.mocked(request).mock.calls[1][1]?.body))).toEqual({command_id:'command-b',expected_revision:5});
});
it('reprend la transcription par sa route locale et relit un reçu completed après perte de réponse',async()=>{
  const result={session:{id:'sid',revision:7},retried_chunks:2,chunk_ids:['mic-failed','system-pending']};
  vi.mocked(request).mockRejectedValueOnce(new Error('Réponse perdue'));
  const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue({ok:true,status:200,json:async()=>({id:'retry-command-a',kind:'retry-transcription',status:'completed',result})} as Response);
  const command={command_id:'retry-command-a',expected_revision:6};
  await expect(meetingSessions.retryTranscription('sid',command)).resolves.toEqual(result);
  expect(request).toHaveBeenCalledExactlyOnceWith('/api/v1/meeting-sessions/sid/transcription/retry',{
    method:'POST',body:JSON.stringify(command)},0);
  expect(fetch).toHaveBeenCalledWith('/api/v1/meeting-sessions/sid/commands/retry-command-a',{credentials:'same-origin'});
  expect(localStorage.getItem('agent.meeting-command.v1.sid.retry-transcription')).toBeNull();
});
it('fige l’UUID et la révision de reprise tant que le premier résultat reste inconnu',async()=>{
  const result={session:{id:'sid',revision:8},retried_chunks:1,chunk_ids:['mic-failed']};
  vi.mocked(request).mockRejectedValueOnce(new Error('Connexion interrompue')).mockResolvedValueOnce(result);
  vi.spyOn(globalThis,'fetch').mockRejectedValue(new Error('Reçu indisponible'));
  const first={command_id:'retry-command-a',expected_revision:6};
  await expect(meetingSessions.retryTranscription('sid',first)).rejects.toThrow('Connexion interrompue');
  await expect(meetingSessions.retryTranscription('sid',{command_id:'retry-command-b',expected_revision:8})).resolves.toEqual(result);
  expect(vi.mocked(request).mock.calls.map(call=>[call[0],JSON.parse(String(call[1]?.body))])).toEqual([
    ['/api/v1/meeting-sessions/sid/transcription/retry',first],['/api/v1/meeting-sessions/sid/transcription/retry',first]]);
  expect(localStorage.getItem('agent.meeting-command.v1.sid.retry-transcription')).toBeNull();
});
it('conserve un arrêt Windows acquitté HTTP mais encore en conservation et rejoue son identité',async()=>{
  const first={command_id:'stop-prepared',expected_revision:3};
  vi.mocked(request).mockResolvedValueOnce({id:'sid',state:'paused',revision:4}).mockResolvedValueOnce({id:'sid',state:'completed',revision:5});
  await expect(meetingSessions.native('sid','stop',first)).resolves.toMatchObject({state:'paused'});
  expect(JSON.parse(localStorage.getItem('agent.meeting-command.v1.sid.native-stop')!)).toEqual(first);
  await meetingSessions.native('sid','stop',{command_id:'replacement',expected_revision:4});
  expect(vi.mocked(request).mock.calls.map(call=>JSON.parse(String(call[1]?.body)))).toEqual([first,first]);
  expect(localStorage.getItem('agent.meeting-command.v1.sid.native-stop')).toBeNull();
});
it('ne transforme pas un reçu d’arrêt completed mais paused en fin de séance après réponse perdue',async()=>{
  const first={command_id:'stop-drained',expected_revision:3};
  vi.mocked(request).mockRejectedValue(new Error('Réponse perdue'));
  vi.spyOn(globalThis,'fetch').mockResolvedValue({ok:true,status:200,json:async()=>({id:'stop-drained',kind:'native.stop',status:'completed',result:{id:'sid',state:'paused'}})} as Response);
  await expect(meetingSessions.native('sid','stop',first)).rejects.toThrow('Réponse perdue');
  expect(JSON.parse(localStorage.getItem('agent.meeting-command.v1.sid.native-stop')!)).toEqual(first);
});
it('lit le statut Windows global ou ciblé avec le signal d’annulation sans envoyer de commande',async()=>{
  vi.mocked(request).mockResolvedValue({owners:[],recovery:[]});const controller=new AbortController();
  await meetingSessions.nativeStatus(undefined,controller.signal);await meetingSessions.nativeStatus('s / id',controller.signal);
  expect(vi.mocked(request).mock.calls).toEqual([
    ['/api/v1/workspace/native-capture',{signal:controller.signal},20_000],
    ['/api/v1/meeting-sessions/s%20%2F%20id/native-capture/status',{signal:controller.signal},20_000]]);
});
it.each([{id:'start-original',kind:'native.start',status:'prepared'},{id:'another-command',kind:'native.start',status:'rejected'}])('garde le démarrage natif si le reçu $id est $status',async receipt=>{
  const body={command_id:'start-original',expected_revision:1,tracks:['system' as const]};vi.mocked(request).mockRejectedValue(new Error('Démarrage non confirmé'));
  vi.spyOn(globalThis,'fetch').mockResolvedValue({ok:true,status:200,json:async()=>receipt} as Response);
  await expect(meetingSessions.native('sid','start',body)).rejects.toThrow('Démarrage non confirmé');
  expect(JSON.parse(localStorage.getItem('agent.meeting-command.v1.sid.native-start')!)).toEqual(body);
});
it('efface le démarrage natif seulement après rejet confirmé de son UUID exact',async()=>{
  const body={command_id:'start-original',expected_revision:1,tracks:['system' as const]};vi.mocked(request).mockRejectedValue(new Error('Propriétaire interrompu'));
  vi.spyOn(globalThis,'fetch').mockResolvedValue({ok:true,status:200,json:async()=>({id:'start-original',kind:'native.start',status:'rejected'})} as Response);
  await expect(meetingSessions.native('sid','start',body)).rejects.toThrow('Propriétaire interrompu');
  expect(localStorage.getItem('agent.meeting-command.v1.sid.native-start')).toBeNull();
});
it.each(['start','stop'] as const)('conserve la commande Windows %s lorsque son reçu 404 peut être masqué par les droits',async action=>{
  const body={command_id:'native-original',expected_revision:2};vi.mocked(request).mockRejectedValue(new Error('Accès interrompu'));
  vi.spyOn(globalThis,'fetch').mockResolvedValue({ok:false,status:404} as Response);
  await expect(meetingSessions.native('sid',action,body)).rejects.toThrow('Accès interrompu');
  expect(JSON.parse(localStorage.getItem(`agent.meeting-command.v1.sid.native-${action}`)!)).toEqual(body);
});
it('garde la préparation historique des commandes non natives lorsqu’un reçu est absent',async()=>{
  vi.mocked(request).mockRejectedValue(new HttpError(409,'La séance a changé ; conserver la saisie et recharger.'));vi.spyOn(globalThis,'fetch').mockResolvedValue({ok:false,status:404,
    json:async()=>({detail:'Commande introuvable dans cette séance'})} as Response);
  await expect(meetingSessions.command('sid','pause',{command_id:'session-original',expected_revision:2})).rejects.toThrow('La séance a changé');
  expect(localStorage.getItem('agent.meeting-command.v1.sid.pause')).toBeNull();
});

it.each([{detail:'Séance introuvable'}, {detail:'Projet introuvable'}, {detail:'Accès refusé'}, null])(
  'conserve une commande de séance quand un 404 ne confirme pas explicitement son absence : %s',async response=>{
    const first={command_id:'session-original',expected_revision:2};
    vi.mocked(request).mockRejectedValueOnce(new Error('Accès interrompu')).mockResolvedValueOnce({id:'sid',state:'completed'});
    vi.spyOn(globalThis,'fetch').mockResolvedValue({ok:false,status:404,json:async()=>response} as Response);
    await expect(meetingSessions.command('sid','finalize',first)).rejects.toThrow('Accès interrompu');
    expect(JSON.parse(localStorage.getItem('agent.meeting-command.v1.sid.finalize')!)).toEqual(first);
    await meetingSessions.command('sid','finalize',{command_id:'replacement',expected_revision:3});
    expect(JSON.parse(String(vi.mocked(request).mock.calls[1][1]?.body))).toEqual(first);
  });

it('conserve la commande si un 404 de reçu suit une réponse réseau incertaine',async()=>{
  const first={command_id:'network-original',expected_revision:2};
  vi.mocked(request).mockRejectedValueOnce(new Error('Connexion interrompue')).mockResolvedValueOnce({id:'sid',state:'completed'});
  vi.spyOn(globalThis,'fetch').mockResolvedValue({ok:false,status:404,
    json:async()=>({detail:'Commande introuvable dans cette séance'})} as Response);
  await expect(meetingSessions.command('sid','finalize',first)).rejects.toThrow('Connexion interrompue');
  expect(JSON.parse(localStorage.getItem('agent.meeting-command.v1.sid.finalize')!)).toEqual(first);
  await meetingSessions.command('sid','finalize',{command_id:'replacement',expected_revision:3});
  expect(JSON.parse(String(vi.mocked(request).mock.calls[1][1]?.body))).toEqual(first);
});

it('conserve aussi une révision refusée si le 404 masque l’accès au projet',async()=>{
  const first={command_id:'scope-original',expected_revision:2};
  vi.mocked(request).mockRejectedValue(new HttpError(409,'La séance a changé ; conserver la saisie et recharger.'));
  vi.spyOn(globalThis,'fetch').mockResolvedValue({ok:false,status:404,json:async()=>({detail:'Projet introuvable'})} as Response);
  await expect(meetingSessions.command('sid','finalize',first)).rejects.toThrow('La séance a changé');
  expect(JSON.parse(localStorage.getItem('agent.meeting-command.v1.sid.finalize')!)).toEqual(first);
});

it('conserve la commande initiale quand un autre opérateur ne peut pas rejouer sa clé',async()=>{
  const original={command_id:'commande-autre-operateur',expected_revision:2};
  vi.mocked(request).mockRejectedValue(new HttpError(409,'Clé de commande réutilisée avec un autre contenu.'));
  vi.spyOn(globalThis,'fetch').mockResolvedValue({ok:false,status:403,
    json:async()=>({detail:'Reçu réservé à son opérateur'})} as Response);
  await expect(meetingSessions.command('sid','finalize',original)).rejects.toThrow('Clé de commande réutilisée');
  expect(JSON.parse(localStorage.getItem('agent.meeting-command.v1.sid.finalize')!)).toEqual(original);
});

it.each([
  {id:'autre',kind:'finalize',status:'rejected',result:null},
  {id:'original',kind:'pause',status:'rejected',result:null},
  {id:'autre',kind:'finalize',status:'completed',result:{id:'sid',state:'completed'}},
  {id:'original',kind:'pause',status:'completed',result:{id:'sid',state:'completed'}},
  {id:'original',kind:'finalize',status:'completed',result:{id:'autre-sid',state:'completed'}},
  {id:'original',kind:'finalize',status:'completed',result:null},
])('conserve une finalisation incertaine si le reçu ne correspond pas : %s',async receipt=>{
  const original={command_id:'original',expected_revision:2};
  vi.mocked(request).mockRejectedValue(new Error('Connexion interrompue'));
  vi.spyOn(globalThis,'fetch').mockResolvedValue({ok:true,status:200,json:async()=>receipt} as Response);
  await expect(meetingSessions.command('sid','finalize',original)).rejects.toThrow('Connexion interrompue');
  expect(JSON.parse(localStorage.getItem('agent.meeting-command.v1.sid.finalize')!)).toEqual(original);
});

it('n’accepte pas le reçu de transcription d’une autre séance',async()=>{
  const original={command_id:'original',expected_revision:2};
  vi.mocked(request).mockRejectedValue(new Error('Connexion interrompue'));
  vi.spyOn(globalThis,'fetch').mockResolvedValue({ok:true,status:200,json:async()=>({id:'original',kind:'retry-transcription',
    status:'completed',result:{session:{id:'autre-sid'},retried_chunks:1,chunk_ids:['fictif']}})} as Response);
  await expect(meetingSessions.retryTranscription('sid',original)).rejects.toThrow('Connexion interrompue');
  expect(JSON.parse(localStorage.getItem('agent.meeting-command.v1.sid.retry-transcription')!)).toEqual(original);
});

it.each([
  {action:'finalize',kind:'finalize',result:{id:'sid',state:'completed'},
    call:(body:SessionCommand)=>meetingSessions.command('sid','finalize',body)},
  {action:'batch-transcription',kind:'transcription-batch',result:{session:{id:'sid'},batch:{state:'admitted'}},
    call:(body:SessionCommand)=>meetingSessions.batchTranscription('sid',body)},
  {action:'cancel-batch-transcription',kind:'cancel-transcription-batch',result:{session:{id:'sid'},batch:{state:'cancelling'}},
    call:(body:SessionCommand)=>meetingSessions.cancelBatchTranscription('sid',body)},
  {action:'native-stop',kind:'native.stop',result:{id:'sid',state:'completed'},
    call:(body:SessionCommand)=>meetingSessions.native('sid','stop',body)},
])('accepte le reçu exact de la commande $action après réponse perdue',async ({action,kind,result,call})=>{
  vi.mocked(request).mockRejectedValue(new Error('Connexion interrompue'));
  vi.spyOn(globalThis,'fetch').mockResolvedValue({ok:true,status:200,json:async()=>({id:'original',kind,status:'completed',result})} as Response);
  await expect(call({command_id:'original',expected_revision:2})).resolves.toEqual(result);
  expect(localStorage.getItem(`agent.meeting-command.v1.sid.${action}`)).toBeNull();
});

it.each([{id:'autre-sid',state:'completed'},null])('conserve la commande si la réponse directe de finalisation est incohérente : %s',async result=>{
  const original={command_id:'original',expected_revision:2};
  vi.mocked(request).mockResolvedValueOnce(result);
  vi.spyOn(globalThis,'fetch').mockRejectedValue(new Error('Reçu indisponible'));
  await expect(meetingSessions.command('sid','finalize',original)).rejects.toThrow('Réponse de séance incohérente');
  expect(JSON.parse(localStorage.getItem('agent.meeting-command.v1.sid.finalize')!)).toEqual(original);
});

it('réconcilie une réponse directe incohérente avec le reçu exact du service',async()=>{
  const original={command_id:'original',expected_revision:2},completed={id:'sid',state:'completed'};
  vi.mocked(request).mockResolvedValueOnce({id:'autre-sid'});
  vi.spyOn(globalThis,'fetch').mockResolvedValue({ok:true,status:200,json:async()=>({id:'original',kind:'finalize',status:'completed',result:completed})} as Response);
  await expect(meetingSessions.command('sid','finalize',original)).resolves.toEqual(completed);
  expect(localStorage.getItem('agent.meeting-command.v1.sid.finalize')).toBeNull();
});

it.each([
  {action:'finalize' as const,state:'paused'},
  {action:'pause' as const,state:'recording'},
  {action:'resume' as const,state:'paused'},
  {action:'cancel' as const,state:'completed'},
])('conserve $action quand le résultat décrit un état inattendu : $state',async({action,state})=>{
  const original={command_id:'original',expected_revision:2};
  vi.mocked(request).mockResolvedValueOnce({id:'sid',state});
  vi.spyOn(globalThis,'fetch').mockRejectedValue(new Error('Reçu indisponible'));
  await expect(meetingSessions.command('sid',action,original)).rejects.toThrow('Réponse de séance incohérente');
  expect(JSON.parse(localStorage.getItem(`agent.meeting-command.v1.sid.${action}`)!)).toEqual(original);
});

it('une commande navigateur nouvelle n’emprunte jamais un ancien propriétaire ou sa révision',async()=>{
  const old={command_id:'old',expected_revision:3,browser_capture_owner_id:'owner-a'};
  localStorage.setItem('agent.meeting-command.v1.sid.resume',JSON.stringify(old));
  localStorage.setItem('agent.meeting-command.v1.sid.resume.owner.owner-b.revision.4',JSON.stringify({...old,browser_capture_owner_id:'owner-b',expected_revision:4}));
  const fresh={command_id:'fresh',expected_revision:8,browser_capture_owner_id:'owner-b'};
  vi.mocked(request).mockResolvedValue({id:'sid',state:'recording',browser_capture:{owner_id:'owner-b',can_control:true}});
  await meetingSessions.command('sid','resume',fresh);
  expect(JSON.parse(String(vi.mocked(request).mock.calls[0][1]?.body))).toEqual(fresh);
  expect(localStorage.getItem('agent.meeting-command.v1.sid.resume')).toBe(JSON.stringify(old));
});

it('ne transforme pas le reçu d’un autre propriétaire en reprise de média',async()=>{
  const fresh={command_id:'fresh',expected_revision:8,browser_capture_owner_id:'owner-b'};
  vi.mocked(request).mockRejectedValue(new Error('Propriétaire refusé'));
  vi.spyOn(globalThis,'fetch').mockResolvedValue({ok:true,status:200,json:async()=>({id:'fresh',kind:'resume',status:'completed',result:{id:'sid',state:'recording',browser_capture:{owner_id:'owner-a',can_control:true}}})} as Response);
  await expect(meetingSessions.command('sid','resume',fresh)).rejects.toThrow('Propriétaire refusé');
});
