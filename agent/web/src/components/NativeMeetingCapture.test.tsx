import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {act,cleanup,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {NativeCaptureBar,NativeMeetingCapture} from './NativeMeetingCapture';
import {meetingSessions,type MeetingSession,type NativeCaptureStatus,type NativeCaptureOwner,type NativeCaptureRecovery} from '../lib/meetingSessions';
const row:MeetingSession={id:'sid',title:'Revue',kind:'meeting',project_id:null,brain_project_id:null,state:'created',revision:1,date:'2026-10-11',recording_id:null,note_id:null,tracks:[],total_bytes:0,duration_seconds:0,issues:[],created_at:'2026-10-11',updated_at:'2026-10-11'};
const native:NativeCaptureStatus={installed:true,ready:true,loopback_ready:true,real_test_passed:true,microphone_test_passed:false,devices:[],active:[],session:null};
const owner:NativeCaptureOwner={session_id:'sid',state:'recording',tracks:['system'],process_alive:true,stop_confirmation_required:true,can_control:true};
const owned=(item:NativeCaptureOwner):NativeCaptureStatus=>({...native,owners:[item],active:item.process_alive?[item]:[],session:item,recovery:[]});
const recovery:NativeCaptureRecovery={session_id:'sid',event_cursor:9,reason:'conservation-pending',can_control:true,
  pending_stop:{command_id:'server-stop-identity',expected_revision:3}};
function deferred<T>(){let resolve!:(value:T)=>void,reject!:(failure:Error)=>void;const promise=new Promise<T>((yes,no)=>{resolve=yes;reject=no;});return {promise,resolve,reject};}

it('conserve partiellement les seuls fragments acquittés au clic explicite après interruption',async()=>{
  const interrupted:MeetingSession={...row,state:'interrupted',tracks:[{name:'system',mime_type:'audio/wav',filename:'kept.wav',chunks:1,total_bytes:20,duration_seconds:5,complete:true}]};
  vi.mocked(meetingSessions.get).mockResolvedValue(interrupted);
  const finalized=vi.spyOn(meetingSessions,'command').mockResolvedValue({...interrupted,state:'completed'});
  const nativeCommand=vi.spyOn(meetingSessions,'native');
  const changed=vi.fn();
  render(<NativeMeetingCapture session={interrupted} capabilities={native} onChanged={changed} browserBusy={false}/>);
  expect(screen.getByText(/Conservation partielle/)).toBeTruthy();expect(finalized).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button',{name:'Conserver les fragments acquittés'}));
  await waitFor(()=>expect(finalized).toHaveBeenCalledWith('sid','finalize',expect.objectContaining({expected_revision:1})));
  expect(changed).toHaveBeenCalledWith(expect.objectContaining({state:'completed'}));expect(nativeCommand).not.toHaveBeenCalled();
});

it('masque la conservation partielle tant que le lecteur natif reste actif',()=>{
  const item={session_id:'sid',state:'paused',tracks:['system' as const]};
  const value={...native,active:[item],session:item};
  render(<NativeMeetingCapture session={{...row,state:'interrupted',tracks:[{name:'system',mime_type:'audio/wav',filename:'kept.wav',chunks:1,total_bytes:20,duration_seconds:5,complete:true}]}}
    capabilities={value} onChanged={vi.fn()} browserBusy={false}/>);
  expect(screen.queryByRole('button',{name:'Conserver les fragments acquittés'})).toBeNull();
  expect(screen.getByRole('button',{name:'Arrêter Windows et conserver la séance'})).toBeTruthy();
});

it('vérifie un propriétaire interrompu avant de proposer la conservation partielle',async()=>{
  const item={session_id:'sid',state:'interrupted',tracks:['system' as const],error:'Arrêt non confirmé'};
  const retained={...native,session:item};vi.mocked(meetingSessions.nativeStatus).mockResolvedValueOnce(retained).mockResolvedValue(native);
  const interrupted:MeetingSession={...row,state:'interrupted',tracks:[{name:'system',mime_type:'audio/wav',filename:'kept.wav',chunks:1,total_bytes:20,duration_seconds:5,complete:true}]};
  vi.mocked(meetingSessions.get).mockResolvedValue(interrupted);
  const stop=vi.spyOn(meetingSessions,'native').mockRejectedValue(new Error('Arrêt non confirmé ; fragments conservés'));
  const finalize=vi.spyOn(meetingSessions,'command');
  render(<NativeMeetingCapture session={interrupted} capabilities={retained} onChanged={vi.fn()} browserBusy={false}/>);
  expect(screen.queryByRole('button',{name:'Conserver les fragments acquittés'})).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'Vérifier l’arrêt Windows'}));
  await waitFor(()=>expect(stop).toHaveBeenCalledWith('sid','stop',expect.objectContaining({expected_revision:1})));
  await screen.findByRole('button',{name:'Conserver les fragments acquittés'});expect(finalize).not.toHaveBeenCalled();
});

it('garde l’erreur et le retour vers la séance après disparition de la capture globale',async()=>{
  vi.useFakeTimers();
  try{
    const item={session_id:'sid',state:'recording',tracks:['system' as const]};
    vi.mocked(meetingSessions.nativeStatus).mockResolvedValueOnce({...native,active:[item]}).mockResolvedValue(native);
    vi.spyOn(meetingSessions,'native').mockRejectedValue(new Error('Arrêt non confirmé ; audio conservé'));
    const open=vi.fn();render(<NativeCaptureBar onOpen={open}/>);
    await act(async()=>{await Promise.resolve();});
    await act(async()=>{fireEvent.click(screen.getByRole('button',{name:'Arrêter et conserver'}));});
    await act(async()=>{await vi.advanceTimersByTimeAsync(5000);});
    expect(screen.getByRole('region',{name:'Capture Windows à vérifier'})).toBeTruthy();
    expect(screen.getByRole('alert').textContent).toContain('Arrêt non confirmé');
    fireEvent.click(screen.getByRole('button',{name:'Ouvrir la séance à récupérer'}));expect(open).toHaveBeenCalledWith('sid');
  }finally{vi.useRealTimers();}
});

it('garde les commandes d’un propriétaire enregistré même si l’inventaire devient indisponible',()=>{
  const item={session_id:'sid',state:'interrupted',tracks:['system' as const]};
  const retained={...native,installed:false,ready:false,session:item};vi.mocked(meetingSessions.nativeStatus).mockResolvedValue(retained);
  const recovery=vi.fn();
  render(<NativeMeetingCapture session={{...row,state:'interrupted'}} capabilities={retained} onChanged={vi.fn()} onRecoveryControls={recovery} browserBusy={false}/>);
  expect(screen.getByRole('button',{name:'Vérifier l’arrêt Windows'})).toBeTruthy();
  expect(screen.getByRole('button',{name:'Démarrer la réunion'})).toHaveProperty('disabled',true);
  expect(recovery).toHaveBeenCalledWith(true);
});
const devices:NativeCaptureStatus['devices']=[
  {index:13,name:'Casque Jabra',maxInputChannels:0,maxOutputChannels:2,defaultSampleRate:48000,isLoopbackDevice:false},
  {index:15,name:'Microphone Jabra',maxInputChannels:1,maxOutputChannels:0,defaultSampleRate:48000,isLoopbackDevice:false},
  {index:17,name:'Casque Jabra (loopback)',maxInputChannels:2,maxOutputChannels:0,defaultSampleRate:48000,isLoopbackDevice:true},
  {index:14,name:'Microphone Realtek',maxInputChannels:2,maxOutputChannels:0,defaultSampleRate:48000,isLoopbackDevice:false},
];
beforeEach(()=>{localStorage.clear();vi.spyOn(meetingSessions,'get').mockResolvedValue(row);vi.spyOn(meetingSessions,'nativeStatus').mockResolvedValue(native);});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
it('démarre seulement la sortie Windows par défaut et exige un choix explicite pour le microphone',async()=>{
  const start=vi.spyOn(meetingSessions,'native').mockResolvedValue({...row,state:'recording'});
  render(<NativeMeetingCapture session={row} capabilities={native} onChanged={vi.fn()} browserBusy={false}/>);
  expect(screen.getByLabelText('Source audio de la réunion')).toHaveProperty('value','system');
  expect(screen.getByLabelText('Microphone à utiliser')).toHaveProperty('disabled',true);
  expect(screen.getByText(/Votre voix n’est pas enregistrée/)).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'Démarrer la réunion'}));
  await waitFor(()=>expect(start).toHaveBeenCalledWith('sid','start',expect.objectContaining({expected_revision:1,tracks:['system'],devices:{}})));
  expect(screen.getByText(/Microphone non qualifié/)).toBeTruthy();
});
it('bloque Windows pendant une capture navigateur active',()=>{
  render(<NativeMeetingCapture session={row} capabilities={native} onChanged={vi.fn()} browserBusy/>);
  expect(screen.getByRole('button',{name:'Démarrer la réunion'})).toHaveProperty('disabled',true);
});

it('laisse Pause et Arrêt accessibles lorsque les diagnostics sont repliés',async()=>{
  const item={session_id:'sid',state:'recording',tracks:['system' as const]};
  const value={...native,active:[item],session:item};vi.mocked(meetingSessions.nativeStatus).mockResolvedValue(value);
  const control=vi.spyOn(meetingSessions,'native').mockResolvedValue({...row,state:'paused'});
  render(<NativeMeetingCapture session={{...row,state:'recording'}} capabilities={value} onChanged={vi.fn()} browserBusy={false}/>);
  const pause=screen.getByRole('button',{name:'Mettre Windows en pause'}),stop=screen.getByRole('button',{name:'Arrêter Windows et conserver la séance'});
  const diagnostics=screen.getByText('État des périphériques').closest('details')!;
  diagnostics.open=false;fireEvent(diagnostics,new Event('toggle'));
  expect(stop.closest('details')).toBeNull();expect(pause.closest('details')).toBeNull();
  expect(diagnostics.open).toBe(false);
  expect(pause.compareDocumentPosition(screen.getByText(/Microphone non qualifié/))&Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  fireEvent.click(pause);await waitFor(()=>expect(control).toHaveBeenCalledWith('sid','pause',expect.objectContaining({expected_revision:1})));
});

it('affiche les périphériques et le démarrage sans ouvrir de microphone ni envoyer de commande',async()=>{
  const status={...native,devices};vi.mocked(meetingSessions.nativeStatus).mockResolvedValue(status);
  const start=vi.spyOn(meetingSessions,'native');
  render(<NativeMeetingCapture session={row} capabilities={status} onChanged={vi.fn()} browserBusy={false}/>);
  const region=screen.getByRole('region',{name:'Audio de la réunion'});
  const output=within(region).getByLabelText('Sortie Windows à enregistrer');
  const microphone=within(region).getByLabelText('Microphone à utiliser');
  const deviceOptions=output.closest('details')!;
  expect(deviceOptions.open).toBe(false);expect(microphone.closest('details')).toBe(deviceOptions);
  fireEvent.click(within(deviceOptions).getByText('Périphériques'));deviceOptions.open=true;
  expect(within(region).getByRole('button',{name:'Démarrer la réunion'}).closest('details')).toBeNull();
  expect(within(output).getAllByRole('option').map(option=>(option as HTMLOptionElement).value)).toEqual(['','17']);
  expect(within(microphone).getAllByRole('option').map(option=>(option as HTMLOptionElement).value)).toEqual(['','15','14']);
  fireEvent.change(output,{target:{value:'17'}});
  fireEvent.change(within(region).getByLabelText('Source audio de la réunion'),{target:{value:'both'}});
  fireEvent.change(microphone,{target:{value:'15'}});
  expect(microphone).toHaveProperty('disabled',false);
  await waitFor(()=>expect(meetingSessions.nativeStatus).toHaveBeenCalled());
  expect(start).not.toHaveBeenCalled();expect(meetingSessions.get).not.toHaveBeenCalled();
});

it('transmet la sortie et le microphone choisis seulement au clic de démarrage explicite',async()=>{
  const status={...native,devices};vi.mocked(meetingSessions.nativeStatus).mockResolvedValue(status);
  const start=vi.spyOn(meetingSessions,'native').mockResolvedValue({...row,state:'recording'});
  vi.mocked(meetingSessions.get).mockResolvedValue({...row,revision:7});
  render(<NativeMeetingCapture session={row} capabilities={status} onChanged={vi.fn()} browserBusy={false}/>);
  fireEvent.change(screen.getByLabelText('Sortie Windows à enregistrer'),{target:{value:'17'}});
  fireEvent.change(screen.getByLabelText('Source audio de la réunion'),{target:{value:'both'}});
  fireEvent.change(screen.getByLabelText('Microphone à utiliser'),{target:{value:'15'}});
  expect(start).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button',{name:'Démarrer la réunion'}));
  await waitFor(()=>expect(start).toHaveBeenCalledWith('sid','start',expect.objectContaining({expected_revision:7,tracks:['mic','system'],devices:{system:17,mic:15}})));
});

it('enregistre une réunion en salle avec le seul microphone au démarrage explicite',async()=>{
  const status={...native,devices};vi.mocked(meetingSessions.nativeStatus).mockResolvedValue(status);
  const start=vi.spyOn(meetingSessions,'native').mockResolvedValue({...row,state:'recording'});
  render(<NativeMeetingCapture session={row} capabilities={status} onChanged={vi.fn()} browserBusy={false}/>);
  fireEvent.change(screen.getByLabelText('Sortie Windows à enregistrer'),{target:{value:'17'}});
  fireEvent.change(screen.getByLabelText('Source audio de la réunion'),{target:{value:'mic'}});
  fireEvent.change(screen.getByLabelText('Microphone à utiliser'),{target:{value:'15'}});
  expect(screen.getByLabelText('Sortie Windows à enregistrer')).toHaveProperty('disabled',true);
  expect(screen.getByText(/personnes présentes dans la salle/)).toBeTruthy();
  expect(start).not.toHaveBeenCalled();expect(meetingSessions.get).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button',{name:'Démarrer la réunion'}));
  await waitFor(()=>expect(start).toHaveBeenCalledWith('sid','start',expect.objectContaining({tracks:['mic'],devices:{mic:15}})));
});

it('conserve le verrou d’une autre séance en consultant aussi le statut global',async()=>{
  const other={session_id:'other',state:'recording',tracks:['system' as const]};
  vi.mocked(meetingSessions.nativeStatus).mockImplementation(async id=>id?native:{...native,active:[other]});
  const start=vi.spyOn(meetingSessions,'native'),availability=vi.fn();
  render(<NativeMeetingCapture session={row} capabilities={native} onChanged={vi.fn()} browserBusy={false} onAvailability={availability}/>);
  await waitFor(()=>expect(screen.getByRole('button',{name:'Démarrer la réunion'})).toHaveProperty('disabled',true));
  expect(screen.getByText(/Une autre séance utilise déjà/)).toBeTruthy();
  expect(availability).toHaveBeenLastCalledWith(true);
  fireEvent.click(screen.getByRole('button',{name:'Démarrer la réunion'}));expect(start).not.toHaveBeenCalled();
});

it('omet le microphone choisi lorsque la source revient au seul son du PC',async()=>{
  const status={...native,devices};vi.mocked(meetingSessions.nativeStatus).mockResolvedValue(status);
  const start=vi.spyOn(meetingSessions,'native').mockResolvedValue({...row,state:'recording'});
  render(<NativeMeetingCapture session={row} capabilities={status} onChanged={vi.fn()} browserBusy={false}/>);
  fireEvent.change(screen.getByLabelText('Source audio de la réunion'),{target:{value:'both'}});
  fireEvent.change(screen.getByLabelText('Microphone à utiliser'),{target:{value:'15'}});
  fireEvent.change(screen.getByLabelText('Source audio de la réunion'),{target:{value:'system'}});
  expect(screen.getByLabelText('Microphone à utiliser')).toHaveProperty('disabled',true);
  fireEvent.click(screen.getByRole('button',{name:'Démarrer la réunion'}));
  await waitFor(()=>expect(start).toHaveBeenCalledWith('sid','start',expect.objectContaining({tracks:['system'],devices:{}})));
});

it.each([{name:'une autre séance Windows',status:{...native,active:[{session_id:'other',state:'recording',tracks:['system' as const]}]}},
  {name:'un moteur indisponible',status:{...native,ready:false}}])('bloque le démarrage pour $name sans envoyer de commande',async({status})=>{
  vi.mocked(meetingSessions.nativeStatus).mockResolvedValue(status);
  const start=vi.spyOn(meetingSessions,'native');
  render(<NativeMeetingCapture session={row} capabilities={status} onChanged={vi.fn()} browserBusy={false}/>);
  const button=screen.getByRole('button',{name:'Démarrer la réunion'});
  expect(button).toHaveProperty('disabled',true);fireEvent.click(button);
  await waitFor(()=>expect(meetingSessions.nativeStatus).toHaveBeenCalled());
  expect(start).not.toHaveBeenCalled();
});

it('conserve et verrouille les périphériques de la commande Windows à reprendre',async()=>{
  const pending={command_id:'already-prepared',expected_revision:1,tracks:['mic','system'],devices:{system:17,mic:15}};
  localStorage.setItem('agent.meeting-command.v1.sid.native-start',JSON.stringify(pending));
  const status={...native,devices};vi.mocked(meetingSessions.nativeStatus).mockResolvedValue(status);
  const start=vi.spyOn(meetingSessions,'native').mockResolvedValue({...row,state:'recording'});
  render(<NativeMeetingCapture session={row} capabilities={status} onChanged={vi.fn()} browserBusy={false}/>);
  await waitFor(()=>expect(screen.getByLabelText('Microphone à utiliser')).toHaveProperty('value','15'));
  expect(screen.getByLabelText('Sortie Windows à enregistrer')).toHaveProperty('value','17');
  expect(screen.getByLabelText('Sortie Windows à enregistrer')).toHaveProperty('disabled',true);
  expect(screen.getByLabelText('Microphone à utiliser')).toHaveProperty('disabled',true);
  expect(screen.getByLabelText('Source audio de la réunion')).toHaveProperty('value','both');
  expect(screen.getByLabelText('Source audio de la réunion')).toHaveProperty('disabled',true);
  expect(start).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button',{name:'Reprendre le démarrage Windows conservé'}));
  await waitFor(()=>expect(start).toHaveBeenCalledWith('sid','start',expect.objectContaining({tracks:['mic','system'],devices:{system:17,mic:15}})));
});

it('reprend aussi une commande durable de microphone seul sans ajouter le son du PC',async()=>{
  localStorage.setItem('agent.meeting-command.v1.sid.native-start',JSON.stringify({command_id:'mic-retry',expected_revision:1,tracks:['mic'],devices:{mic:15}}));
  const status={...native,devices};vi.mocked(meetingSessions.nativeStatus).mockResolvedValue(status);
  const start=vi.spyOn(meetingSessions,'native').mockResolvedValue({...row,state:'recording'});
  render(<NativeMeetingCapture session={row} capabilities={status} onChanged={vi.fn()} browserBusy={false}/>);
  expect(screen.getByLabelText('Source audio de la réunion')).toHaveProperty('value','mic');
  expect(screen.getByLabelText('Source audio de la réunion')).toHaveProperty('disabled',true);
  fireEvent.click(screen.getByRole('button',{name:'Reprendre le démarrage Windows conservé'}));
  await waitFor(()=>expect(start).toHaveBeenCalledWith('sid','start',expect.objectContaining({tracks:['mic'],devices:{mic:15}})));
});

it('garde dans la barre une capture morte spontanément sans commande et permet le retour à sa séance',async()=>{
  vi.useFakeTimers();try{
    const dead={...owner,state:'interrupted',process_alive:false,problem_code:'interrupted' as const};
    vi.mocked(meetingSessions.nativeStatus).mockResolvedValueOnce(owned(owner)).mockResolvedValue(owned(dead));
    const command=vi.spyOn(meetingSessions,'native'),open=vi.fn();render(<NativeCaptureBar onOpen={open}/>);
    await act(async()=>{await Promise.resolve();});expect(screen.getByRole('button',{name:'Pause'})).toBeTruthy();
    await act(async()=>{await vi.advanceTimersByTimeAsync(5000);});
    expect(screen.getByRole('region',{name:'Capture Windows à vérifier'})).toBeTruthy();
    expect(screen.queryByRole('button',{name:'Pause'})).toBeNull();expect(screen.getByRole('button',{name:'Vérifier l’arrêt Windows'})).toHaveProperty('disabled',false);
    fireEvent.click(screen.getByRole('button',{name:'Revenir à la séance'}));expect(open).toHaveBeenCalledWith('sid');expect(command).not.toHaveBeenCalled();
  }finally{vi.useRealTimers();}
});
it('garde une capture réellement en pause comme propriétaire vivant et reprend seulement au clic',async()=>{
  const paused={...owner,state:'paused'};vi.mocked(meetingSessions.nativeStatus).mockResolvedValue(owned(paused));
  vi.mocked(meetingSessions.get).mockResolvedValue({...row,state:'paused',native_capture:paused});
  const command=vi.spyOn(meetingSessions,'native').mockResolvedValue({...row,state:'recording'});
  render(<NativeCaptureBar onOpen={vi.fn()}/>);const button=await screen.findByRole('button',{name:'Reprendre'});
  expect(screen.getByText('Capture Windows · En pause')).toBeTruthy();expect(command).not.toHaveBeenCalled();fireEvent.click(button);
  await waitFor(()=>expect(command).toHaveBeenCalledWith('sid','resume',expect.objectContaining({expected_revision:1})));
});
it('retrouve un arrêt préparé côté serveur après rechargement sans localStorage et rejoue son UUID dans la séance',async()=>{
  const retained={...native,owners:[],recovery:[recovery]};vi.mocked(meetingSessions.nativeStatus).mockResolvedValue(retained);
  vi.mocked(meetingSessions.get).mockResolvedValue({...row,state:'interrupted',revision:8,native_recovery:[recovery]});
  const command=vi.spyOn(meetingSessions,'native').mockResolvedValue({...row,state:'completed'});
  render(<NativeMeetingCapture session={{...row,state:'interrupted',native_recovery:[recovery]}} capabilities={retained} onChanged={vi.fn()} browserBusy={false}/>);
  const button=await screen.findByRole('button',{name:'Reprendre la conservation Windows'});expect(command).not.toHaveBeenCalled();
  expect(localStorage.getItem('agent.meeting-command.v1.sid.native-stop')).toBeNull();fireEvent.click(button);
  await waitFor(()=>expect(command).toHaveBeenCalledWith('sid','stop',expect.objectContaining(recovery.pending_stop!)));
});
it('retrouve dans la barre une conservation durable seule après redémarrage et ne réouvre aucun périphérique',async()=>{
  vi.mocked(meetingSessions.nativeStatus).mockResolvedValue({...native,installed:false,ready:false,owners:[],recovery:[recovery]});
  vi.mocked(meetingSessions.get).mockResolvedValue({...row,state:'paused',revision:7,native_recovery:[recovery]});
  const command=vi.spyOn(meetingSessions,'native').mockResolvedValue({...row,state:'completed'}),open=vi.fn();
  render(<NativeCaptureBar onOpen={open}/>);const resume=await screen.findByRole('button',{name:'Reprendre la conservation Windows'});
  expect(screen.getByRole('region',{name:'Capture Windows à vérifier'})).toBeTruthy();expect(command).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button',{name:'Revenir à la séance'}));expect(open).toHaveBeenCalledWith('sid');fireEvent.click(resume);
  await waitFor(()=>expect(command).toHaveBeenCalledWith('sid','stop',recovery.pending_stop));
});
it.each(['bar','session'] as const)('respecte le contrôle en lecture seule dans %s tout en conservant le retour et les informations',async surface=>{
  const readonly=owned({...owner,can_control:false});vi.mocked(meetingSessions.nativeStatus).mockResolvedValue(readonly);
  const command=vi.spyOn(meetingSessions,'native');
  render(surface==='bar'?<NativeCaptureBar onOpen={vi.fn()}/>:<NativeMeetingCapture session={{...row,state:'recording'}} capabilities={readonly} onChanged={vi.fn()} browserBusy={false}/>);
  const stop=await screen.findByRole('button',{name:surface==='bar'?'Arrêter et conserver':'Arrêter Windows et conserver la séance'});
  expect(stop).toHaveProperty('disabled',true);fireEvent.click(stop);expect(command).not.toHaveBeenCalled();expect(screen.getByText(/accessible en lecture seule/)).toBeTruthy();
});
it('ne cache pas le propriétaire ni son arrêt à vérifier quand le GET global échoue puis guérit seulement la lecture',async()=>{
  vi.useFakeTimers();try{
    vi.mocked(meetingSessions.nativeStatus).mockResolvedValueOnce(owned({...owner,process_alive:false,state:'interrupted'}))
      .mockRejectedValueOnce(new Error('HTTP 500 SQL')).mockResolvedValue(owned({...owner,process_alive:false,state:'interrupted'}));
    const command=vi.spyOn(meetingSessions,'native');render(<NativeCaptureBar onOpen={vi.fn()}/>);
    await act(async()=>{await Promise.resolve();});await act(async()=>{await vi.advanceTimersByTimeAsync(5000);});
    expect(screen.getAllByRole('alert').some(item=>item.textContent?.includes('HTTP 500 SQL'))).toBe(true);expect(screen.getByRole('button',{name:'Vérifier l’arrêt Windows'})).toBeTruthy();
    await act(async()=>{await vi.advanceTimersByTimeAsync(5000);});expect(screen.queryByText(/État Windows indisponible/)).toBeNull();expect(screen.getByRole('alert').textContent).toContain('Capture Windows interrompue');expect(command).not.toHaveBeenCalled();
  }finally{vi.useRealTimers();}
});
it('ignore une ancienne réponse globale vivante arrivée après la lecture plus récente d’un propriétaire mort',async()=>{
  vi.useFakeTimers();try{
    const old=deferred<NativeCaptureStatus>();vi.mocked(meetingSessions.nativeStatus).mockReturnValueOnce(old.promise).mockResolvedValue(owned({...owner,process_alive:false,state:'interrupted'}));
    render(<NativeCaptureBar onOpen={vi.fn()}/>);await act(async()=>{await vi.advanceTimersByTimeAsync(5000);});
    await act(async()=>{old.resolve(owned(owner));await old.promise;});
    expect(screen.getByRole('button',{name:'Vérifier l’arrêt Windows'})).toBeTruthy();expect(screen.queryByRole('button',{name:'Pause'})).toBeNull();
  }finally{vi.useRealTimers();}
});
it('ignore aussi une ancienne erreur globale après une lecture fraîche réussie',async()=>{
  vi.useFakeTimers();try{
    const old=deferred<NativeCaptureStatus>();vi.mocked(meetingSessions.nativeStatus).mockReturnValueOnce(old.promise).mockResolvedValue(owned(owner));
    render(<NativeCaptureBar onOpen={vi.fn()}/>);await act(async()=>{await vi.advanceTimersByTimeAsync(5000);});
    await act(async()=>{old.reject(new Error('Ancienne panne'));await Promise.resolve();});
    expect(screen.queryByRole('alert')).toBeNull();expect(screen.getByRole('button',{name:'Pause'})).toBeTruthy();
  }finally{vi.useRealTimers();}
});
it('conserve l’erreur fraîche lorsqu’une ancienne réussite globale arrive en retard',async()=>{
  vi.useFakeTimers();try{
    const old=deferred<NativeCaptureStatus>();vi.mocked(meetingSessions.nativeStatus).mockReturnValueOnce(old.promise).mockRejectedValue(new Error('Panne actuelle'));
    render(<NativeCaptureBar onOpen={vi.fn()}/>);await act(async()=>{await vi.advanceTimersByTimeAsync(5000);});
    await act(async()=>{old.resolve(native);await old.promise;});expect(screen.getByRole('alert').textContent).toContain('Panne actuelle');
  }finally{vi.useRealTimers();}
});
it('annule le GET préalable et n’envoie aucun démarrage quand la séance change avant sa réponse',async()=>{
  const old=deferred<MeetingSession>();vi.mocked(meetingSessions.get).mockReturnValueOnce(old.promise);
  const command=vi.spyOn(meetingSessions,'native'),changed=vi.fn();
  const view=render(<NativeMeetingCapture session={row} capabilities={native} onChanged={changed} browserBusy={false}/>);
  fireEvent.click(screen.getByRole('button',{name:'Démarrer la réunion'}));await waitFor(()=>expect(meetingSessions.get).toHaveBeenCalled());
  const signal=vi.mocked(meetingSessions.get).mock.calls[0][1]!;
  view.rerender(<NativeMeetingCapture session={{...row,id:'new-session'}} capabilities={native} onChanged={changed} browserBusy={false}/>);
  expect(signal.aborted).toBe(true);await act(async()=>{old.resolve(row);await old.promise;});
  expect(command).not.toHaveBeenCalled();expect(changed).not.toHaveBeenCalled();expect(screen.getByRole('button',{name:'Démarrer la réunion'})).toHaveProperty('disabled',false);
});
it('ignore une réponse de commande de l’ancienne séance après changement sans effacer sa reprise durable',async()=>{
  const old=deferred<MeetingSession>(),changed=vi.fn();
  vi.spyOn(meetingSessions,'native').mockImplementation(()=>{localStorage.setItem('agent.meeting-command.v1.sid.native-start',JSON.stringify({command_id:'kept',expected_revision:1,tracks:['system']}));return old.promise;});
  const view=render(<NativeMeetingCapture session={row} capabilities={native} onChanged={changed} browserBusy={false}/>);
  fireEvent.click(screen.getByRole('button',{name:'Démarrer la réunion'}));await waitFor(()=>expect(meetingSessions.native).toHaveBeenCalled());
  view.rerender(<NativeMeetingCapture session={{...row,id:'new-session'}} capabilities={native} onChanged={changed} browserBusy={false}/>);
  await act(async()=>{old.resolve({...row,state:'recording'});await old.promise;});
  expect(changed).not.toHaveBeenCalled();expect(localStorage.getItem('agent.meeting-command.v1.sid.native-start')).not.toBeNull();
  expect(screen.queryByRole('button',{name:'Reprendre le démarrage Windows conservé'})).toBeNull();
});
it('ne prétend pas finir un arrêt HTTP réussi mais paused et conserve son erreur après les lectures suivantes',async()=>{
  vi.useFakeTimers();try{
    const retained={...native,owners:[],recovery:[recovery]};vi.mocked(meetingSessions.nativeStatus).mockResolvedValue(retained);
    vi.mocked(meetingSessions.get).mockResolvedValue({...row,state:'paused',native_recovery:[recovery]});
    const changed=vi.fn();vi.spyOn(meetingSessions,'native').mockResolvedValue({...row,state:'paused'});
    render(<NativeMeetingCapture session={{...row,state:'paused'}} capabilities={retained} onChanged={changed} browserBusy={false}/>);
    await act(async()=>{fireEvent.click(screen.getByRole('button',{name:'Reprendre la conservation Windows'}));});
    await act(async()=>{await vi.advanceTimersByTimeAsync(5000);});
    expect(screen.getByRole('alert').textContent).toContain('reste à terminer');expect(changed).toHaveBeenCalledWith(expect.objectContaining({state:'paused'}));
    expect(changed).not.toHaveBeenCalledWith(expect.objectContaining({state:'completed'}));expect(screen.getByRole('button',{name:'Reprendre la conservation Windows'})).toBeTruthy();
  }finally{vi.useRealTimers();}
});
it('garde une réservation morte d’une autre séance pour bloquer le navigateur et un nouveau démarrage Windows',async()=>{
  const retained=owned({...owner,session_id:'other',state:'stopped',process_alive:false});vi.mocked(meetingSessions.nativeStatus).mockResolvedValue(retained);
  const available=vi.fn(),command=vi.spyOn(meetingSessions,'native');
  render(<NativeMeetingCapture session={row} capabilities={retained} onChanged={vi.fn()} onAvailability={available} browserBusy={false}/>);
  await waitFor(()=>expect(available).toHaveBeenLastCalledWith(true));expect(screen.getByRole('button',{name:'Démarrer la réunion'})).toHaveProperty('disabled',true);
  fireEvent.click(screen.getByRole('button',{name:'Démarrer la réunion'}));expect(command).not.toHaveBeenCalled();
});
it('relit les droits avant une commande affichée et refuse le contrôle devenu lecteur',async()=>{
  vi.mocked(meetingSessions.nativeStatus).mockResolvedValue(owned(owner));vi.mocked(meetingSessions.get).mockResolvedValue({...row,state:'recording',native_capture:{...owner,can_control:false}});
  const command=vi.spyOn(meetingSessions,'native');render(<NativeMeetingCapture session={{...row,state:'recording'}} capabilities={owned(owner)} onChanged={vi.fn()} browserBusy={false}/>);
  fireEvent.click(screen.getByRole('button',{name:'Arrêter Windows et conserver la séance'}));
  await screen.findByText(/Lecture de la séance : Cette séance est accessible en lecture seule/);expect(command).not.toHaveBeenCalled();
});
it('bloque un nouveau démarrage après une erreur de statut ciblé et le réactive après lecture complète réussie',async()=>{
  vi.useFakeTimers();try{
    vi.mocked(meetingSessions.nativeStatus).mockRejectedValueOnce(new Error('Statut non lu')).mockResolvedValue(native);
    const command=vi.spyOn(meetingSessions,'native'),available=vi.fn();
    render(<NativeMeetingCapture session={row} capabilities={native} onChanged={vi.fn()} onAvailability={available} browserBusy={false}/>);
    await act(async()=>{await Promise.resolve();});expect(screen.getByRole('button',{name:'Démarrer la réunion'})).toHaveProperty('disabled',true);
    expect(available).toHaveBeenLastCalledWith(true);fireEvent.click(screen.getByRole('button',{name:'Démarrer la réunion'}));expect(command).not.toHaveBeenCalled();
    await act(async()=>{await vi.advanceTimersByTimeAsync(5000);});expect(screen.queryByRole('alert')).toBeNull();expect(screen.getByRole('button',{name:'Démarrer la réunion'})).toHaveProperty('disabled',false);
  }finally{vi.useRealTimers();}
});
it('vérifie explicitement un démarrage conservé avec propriétaire mort puis garde son arrêt à vérifier après rejet',async()=>{
  localStorage.setItem('agent.meeting-command.v1.sid.native-start',JSON.stringify({command_id:'prepared-start',expected_revision:1,tracks:['system'],devices:{}}));
  const retained={...owned({...owner,state:'interrupted',process_alive:false}),installed:false,ready:false};vi.mocked(meetingSessions.nativeStatus).mockResolvedValue(retained);
  vi.mocked(meetingSessions.get).mockResolvedValue({...row,state:'interrupted',native_capture:retained.session});
  const command=vi.spyOn(meetingSessions,'native').mockImplementation(async()=>{localStorage.removeItem('agent.meeting-command.v1.sid.native-start');throw new Error('Démarrage conservé rejeté ; arrêt à vérifier');});
  render(<NativeMeetingCapture session={{...row,state:'interrupted'}} capabilities={retained} onChanged={vi.fn()} browserBusy={false}/>);
  const verify=screen.getByRole('button',{name:'Vérifier le démarrage conservé'});expect(verify).toHaveProperty('disabled',false);expect(command).not.toHaveBeenCalled();fireEvent.click(verify);
  await waitFor(()=>expect(command).toHaveBeenCalledWith('sid','start',expect.objectContaining({tracks:['system'],devices:{}})));
  await waitFor(()=>expect(screen.queryByRole('button',{name:'Vérifier le démarrage conservé'})).toBeNull());
  expect(screen.getByRole('button',{name:'Vérifier l’arrêt Windows'})).toHaveProperty('disabled',false);
  expect(screen.getByRole('button',{name:'Démarrer la réunion'})).toHaveProperty('disabled',true);expect(screen.getAllByRole('alert').some(item=>item.textContent?.includes('rejeté'))).toBe(true);
});
it('verrouille le navigateur avant le premier statut global quand la séance contient un propriétaire durable',async()=>{
  const pending=deferred<NativeCaptureStatus>();vi.mocked(meetingSessions.nativeStatus).mockReturnValue(pending.promise);
  const availability=vi.fn();render(<NativeMeetingCapture session={{...row,state:'recording',native_capture:owner}} capabilities={native} onChanged={vi.fn()} onAvailability={availability} browserBusy={false}/>);
  expect(availability).toHaveBeenLastCalledWith(true);expect(screen.getByRole('button',{name:'Arrêter Windows et conserver la séance'})).toBeTruthy();
  await act(async()=>{pending.resolve({...native,owners:[],recovery:[],session:null});await pending.promise;});
  expect(availability).toHaveBeenLastCalledWith(false);expect(screen.queryByRole('button',{name:'Arrêter Windows et conserver la séance'})).toBeNull();
});
it('refuse la conservation partielle quand un propriétaire apparaît dans la relecture préalable',async()=>{
  const interrupted:MeetingSession={...row,state:'interrupted',tracks:[{name:'system',mime_type:'audio/wav',filename:'kept.wav',chunks:1,total_bytes:20,duration_seconds:5,complete:true}]};
  vi.mocked(meetingSessions.get).mockResolvedValue({...interrupted,native_capture:{...owner,process_alive:false,state:'interrupted'}});
  const finalize=vi.spyOn(meetingSessions,'command');render(<NativeMeetingCapture session={interrupted} capabilities={native} onChanged={vi.fn()} browserBusy={false}/>);
  fireEvent.click(screen.getByRole('button',{name:'Conserver les fragments acquittés'}));
  await screen.findByText(/Lecture de la séance : Vérifiez l’arrêt Windows/);expect(finalize).not.toHaveBeenCalled();
});
it('refuse la reprise d’une pause affichée si le processus devient inconnu au GET préalable',async()=>{
  const paused={...owner,state:'paused'};vi.mocked(meetingSessions.nativeStatus).mockResolvedValue(owned(paused));
  vi.mocked(meetingSessions.get).mockResolvedValue({...row,state:'paused',native_capture:{...paused,process_alive:null}});
  const command=vi.spyOn(meetingSessions,'native');render(<NativeCaptureBar onOpen={vi.fn()}/>);
  fireEvent.click(await screen.findByRole('button',{name:'Reprendre'}));
  await screen.findByText(/Lecture de la séance : La capture Windows est interrompue/);expect(command).not.toHaveBeenCalled();
});
it.each(['recording','starting'])('vérifie le démarrage conservé avec propriétaire vivant %s sans autre commande ni nouvel UUID',async state=>{
  const original={command_id:'prepared-start',expected_revision:1,tracks:['system'],devices:{system:17}};
  localStorage.setItem('agent.meeting-command.v1.sid.native-start',JSON.stringify(original));
  const retained=owned({...owner,state});vi.mocked(meetingSessions.nativeStatus).mockResolvedValue(retained);
  vi.mocked(meetingSessions.get).mockResolvedValue({...row,state:'recording',revision:9,native_capture:retained.session});
  const command=vi.spyOn(meetingSessions,'native').mockResolvedValue({...row,state:'recording'});
  render(<NativeMeetingCapture session={{...row,state:'recording'}} capabilities={retained} onChanged={vi.fn()} browserBusy={false}/>);
  const verify=screen.getByRole('button',{name:'Vérifier le démarrage conservé'});expect(verify).toHaveProperty('disabled',false);
  expect(screen.getByRole('button',{name:'Arrêter Windows et conserver la séance'})).toHaveProperty('disabled',true);expect(command).not.toHaveBeenCalled();
  fireEvent.click(verify);await waitFor(()=>expect(command).toHaveBeenCalledWith('sid','start',original));
});
it('la barre dirige le démarrage préparé vers sa séance et désactive les commandes d’un autre UUID',async()=>{
  localStorage.setItem('agent.meeting-command.v1.sid.native-start',JSON.stringify({command_id:'prepared-start',expected_revision:1,tracks:['system']}));
  vi.mocked(meetingSessions.nativeStatus).mockResolvedValue(owned(owner));const command=vi.spyOn(meetingSessions,'native'),open=vi.fn();render(<NativeCaptureBar onOpen={open}/>);
  const stop=await screen.findByRole('button',{name:'Arrêter et conserver'});expect(stop).toHaveProperty('disabled',true);expect(screen.getByRole('button',{name:'Pause'})).toHaveProperty('disabled',true);
  fireEvent.click(stop);expect(command).not.toHaveBeenCalled();fireEvent.click(screen.getByRole('button',{name:'Revenir à la séance'}));expect(open).toHaveBeenCalledWith('sid');
});
it('une interruption durable sans propriétaire ni arrêt préparé ouvre sa séance sans proposer un arrêt impossible',async()=>{
  const notice={...recovery,reason:'interrupted' as const,pending_stop:undefined};vi.mocked(meetingSessions.nativeStatus).mockResolvedValue({...native,owners:[],recovery:[notice]});
  const command=vi.spyOn(meetingSessions,'native'),open=vi.fn();render(<NativeCaptureBar onOpen={open}/>);
  fireEvent.click(await screen.findByRole('button',{name:'Revenir à la séance'}));expect(open).toHaveBeenCalledWith('sid');
  expect(screen.queryByRole('button',{name:'Vérifier l’arrêt Windows'})).toBeNull();expect(screen.queryByRole('button',{name:'Reprendre la conservation Windows'})).toBeNull();
  expect(screen.getByRole('alert').textContent).toContain('fragments déjà acquittés restent conservés');expect(command).not.toHaveBeenCalled();
});
it('une interruption durable sans propriétaire propose seulement la conservation partielle explicite des fragments',async()=>{
  const notice={...recovery,reason:'stop-unconfirmed' as const,pending_stop:undefined},retained={...native,owners:[],recovery:[notice]};
  vi.mocked(meetingSessions.nativeStatus).mockResolvedValue(retained);
  const interrupted:MeetingSession={...row,state:'interrupted',native_recovery:[notice],tracks:[{name:'system',mime_type:'audio/wav',filename:'kept.wav',chunks:1,total_bytes:20,duration_seconds:5,complete:true}]};
  const command=vi.spyOn(meetingSessions,'native'),finalize=vi.spyOn(meetingSessions,'command');
  render(<NativeMeetingCapture session={interrupted} capabilities={retained} onChanged={vi.fn()} browserBusy={false}/>);
  expect(screen.getByRole('button',{name:'Conserver les fragments acquittés'})).toBeTruthy();expect(screen.queryByRole('button',{name:'Vérifier l’arrêt Windows'})).toBeNull();
  expect(screen.getByRole('alert').textContent).toContain('n’a pas été confirmé');expect(command).not.toHaveBeenCalled();expect(finalize).not.toHaveBeenCalled();
});
it('alerte explicitement dans la barre lorsque la persistance de l’interruption reste non confirmée',async()=>{
  vi.mocked(meetingSessions.nativeStatus).mockResolvedValue(owned({...owner,state:'interrupted',process_alive:false,problem_code:'interruption-unpersisted'}));
  const command=vi.spyOn(meetingSessions,'native');render(<NativeCaptureBar onOpen={vi.fn()}/>);
  expect((await screen.findByRole('alert')).textContent).toContain('journal d’interruption n’est pas encore confirmé');
  expect(screen.getByRole('button',{name:'Vérifier l’arrêt Windows'})).toBeTruthy();expect(command).not.toHaveBeenCalled();
});
it('alerte quand le lecteur a signalé stopped mais reste vivant avant confirmation de fermeture',async()=>{
  vi.mocked(meetingSessions.nativeStatus).mockResolvedValue(owned({...owner,state:'stopped',process_alive:true}));
  const command=vi.spyOn(meetingSessions,'native');render(<NativeCaptureBar onOpen={vi.fn()}/>);
  expect((await screen.findByRole('alert')).textContent).toContain('fermeture et la conservation complète restent à confirmer');
  expect(screen.getByRole('button',{name:'Vérifier l’arrêt Windows'})).toBeTruthy();expect(screen.queryByRole('button',{name:'Pause'})).toBeNull();expect(command).not.toHaveBeenCalled();
});
it('ne masque pas le propriétaire après un HTTP 200 vide ou malformé dans la barre',async()=>{
  vi.useFakeTimers();try{
    vi.mocked(meetingSessions.nativeStatus).mockResolvedValueOnce(owned(owner)).mockResolvedValue({} as NativeCaptureStatus);
    const command=vi.spyOn(meetingSessions,'native');render(<NativeCaptureBar onOpen={vi.fn()}/>);
    await act(async()=>{await Promise.resolve();});await act(async()=>{await vi.advanceTimersByTimeAsync(5000);});
    expect(screen.getByRole('region',{name:'Capture Windows active'})).toBeTruthy();expect(screen.getByRole('button',{name:'Arrêter et conserver'})).toBeTruthy();
    expect(screen.getByRole('alert').textContent).toContain('Réponse de statut Windows invalide');expect(command).not.toHaveBeenCalled();
  }finally{vi.useRealTimers();}
});
it.each(['session','workspace'] as const)('refuse un HTTP200 %s invalide avant merge sans effacer la capture ni libérer le navigateur',async invalid=>{
  vi.useFakeTimers();try{
    let bad=false;vi.mocked(meetingSessions.nativeStatus).mockImplementation(async id=>bad&&((invalid==='session'&&id)||(invalid==='workspace'&&!id))?{} as NativeCaptureStatus:owned(owner));
    const availability=vi.fn(),command=vi.spyOn(meetingSessions,'native');
    render(<NativeMeetingCapture session={{...row,state:'recording'}} capabilities={owned(owner)} onChanged={vi.fn()} onAvailability={availability} browserBusy={false}/>);
    await act(async()=>{await Promise.resolve();});bad=true;await act(async()=>{await vi.advanceTimersByTimeAsync(5000);});
    expect(screen.getByText(/Enregistrement en cours/)).toBeTruthy();expect(screen.getByRole('button',{name:'Arrêter Windows et conserver la séance'})).toBeTruthy();
    expect(screen.getByRole('alert').textContent).toContain('Réponse de statut Windows invalide');expect(availability).toHaveBeenLastCalledWith(true);expect(command).not.toHaveBeenCalled();
  }finally{vi.useRealTimers();}
});
it.each([
  {field:'active',value:{...native,active:false}},
  {field:'owners',value:{...native,owners:[{...owner,process_alive:'false'}]}},
  {field:'recovery',value:{...native,recovery:[{...recovery,pending_stop:{command_id:'bad',expected_revision:'3'}}]}},
])('refuse la forme invalide de $field tout en conservant le dernier propriétaire connu',async({value})=>{
  vi.useFakeTimers();try{
    vi.mocked(meetingSessions.nativeStatus).mockResolvedValueOnce(owned(owner)).mockResolvedValue(value as unknown as NativeCaptureStatus);
    render(<NativeCaptureBar onOpen={vi.fn()}/>);await act(async()=>{await Promise.resolve();});await act(async()=>{await vi.advanceTimersByTimeAsync(5000);});
    expect(screen.getByRole('alert').textContent).toContain('Réponse de statut Windows invalide');expect(screen.getByRole('button',{name:'Pause'})).toBeTruthy();
  }finally{vi.useRealTimers();}
});
