import {useCallback,useEffect,useRef,useState} from 'react';
import {beginActivity} from '../lib/asyncActivity';
import {hasDesktopCapture,meetingSessions,sessionCommand,type MeetingSession,type NativeCaptureStatus,type NativeCaptureItem,type NativeCaptureRecovery} from '../lib/meetingSessions';

const commandKey=(id:string,action:string)=>`agent.meeting-command.v1.${id}.native-${action}`;
const failureText=(failure:unknown)=>failure instanceof Error?failure.message:String(failure);
const object=(value:unknown):value is Record<string,unknown>=>!!value&&typeof value==='object'&&!Array.isArray(value);
const identity=(value:unknown):value is string=>typeof value==='string'&&value.trim().length>0;
const tracks=(value:unknown)=>Array.isArray(value)&&value.every(track=>track==='mic'||track==='system');
function validItem(value:unknown,owner=false):boolean{
  if(!object(value)||!identity(value.session_id)||!identity(value.state)||!tracks(value.tracks))return false;
  if(value.can_control!==undefined&&typeof value.can_control!=='boolean')return false;
  if(value.process_alive!==undefined&&value.process_alive!==null&&typeof value.process_alive!=='boolean')return false;
  if(value.stop_confirmation_required!==undefined&&typeof value.stop_confirmation_required!=='boolean')return false;
  if(value.error!==undefined&&value.error!==null&&typeof value.error!=='string')return false;
  if(value.problem_code!==undefined&&!['interrupted','interruption-unpersisted','status-unknown'].includes(String(value.problem_code)))return false;
  return !owner||(['starting','recording','paused','interrupted','stopped','unknown'].includes(value.state)&&
    (typeof value.process_alive==='boolean'||value.process_alive===null)&&typeof value.can_control==='boolean'&&typeof value.stop_confirmation_required==='boolean');
}
function validRecovery(value:unknown):boolean{
  if(!object(value)||!identity(value.session_id)||!Number.isInteger(value.event_cursor)||Number(value.event_cursor)<0||
    !['interrupted','stop-unconfirmed','conservation-pending'].includes(String(value.reason))||typeof value.can_control!=='boolean')return false;
  return value.pending_stop===undefined||(object(value.pending_stop)&&identity(value.pending_stop.command_id)&&
    Number.isInteger(value.pending_stop.expected_revision)&&Number(value.pending_stop.expected_revision)>=0);
}
function captureStatus(value:unknown):NativeCaptureStatus{
  const valid=object(value)&&['installed','ready','loopback_ready','real_test_passed','microphone_test_passed'].every(key=>typeof value[key]==='boolean')&&
    Array.isArray(value.devices)&&value.devices.every(device=>object(device)&&identity(device.name)&&Number.isInteger(device.index)&&
      ['maxInputChannels','maxOutputChannels','defaultSampleRate'].every(key=>typeof device[key]==='number'&&Number.isFinite(device[key]))&&typeof device.isLoopbackDevice==='boolean')&&
    Array.isArray(value.active)&&value.active.every(item=>validItem(item))&&
    (value.session===undefined||value.session===null||validItem(value.session))&&
    (value.owners===undefined||(Array.isArray(value.owners)&&value.owners.every(item=>validItem(item,true))))&&
    (value.recovery===undefined||(Array.isArray(value.recovery)&&value.recovery.every(validRecovery)));
  if(!valid)throw new Error('Réponse de statut Windows invalide');
  return value as NativeCaptureStatus;
}
function owners(status:NativeCaptureStatus|null):NativeCaptureItem[]{
  if(status?.owners)return status.owners;
  const items=[...(status?.active||[])];
  if(status?.session&&!items.some(item=>item.session_id===status.session!.session_id))items.push(status.session);
  return items;
}
function running(item:NativeCaptureItem){
  return item.process_alive!==false&&item.process_alive!==null&&['recording','paused','starting'].includes(item.state);
}
function recoveryMessage(item:NativeCaptureItem|null|undefined,notice?:NativeCaptureRecovery){
  if(item?.problem_code==='interruption-unpersisted')return 'Capture Windows interrompue. Le journal d’interruption n’est pas encore confirmé dans la séance. Vérifiez son arrêt et les fichiers conservés.';
  if(item?.process_alive===null||item?.problem_code==='status-unknown')return 'L’état du processus Windows est inconnu. Son arrêt n’est pas confirmé.';
  if(item?.state==='stopped'&&hasDesktopCapture())return 'Capture arrêtée. Kiara reprend automatiquement le transfert des fragments conservés sur ce poste.';
  if(item?.state==='stopped')return 'Le processus Windows a signalé un arrêt. Sa fermeture et la conservation complète restent à confirmer.';
  if(notice?.reason==='stop-unconfirmed')return 'L’arrêt Windows n’a pas été confirmé. Vérifiez les fragments et le journal conservés dans la séance.';
  if(item?.problem_code==='interrupted'||item?.state==='interrupted'||item?.process_alive===false||notice?.reason==='interrupted')return 'Capture Windows interrompue. Les fragments déjà acquittés restent conservés. Ouvrez la séance pour vérifier la récupération.';
  return '';
}
function stopCommand(row:MeetingSession,notice?:NativeCaptureRecovery){
  return row.native_recovery?.find(item=>item.session_id===row.id)?.pending_stop||notice?.pending_stop||sessionCommand(row.revision);
}
function useCaptureStatus(id?:string,initial?:NativeCaptureStatus){
  const [status,setStatus]=useState<NativeCaptureStatus|null>(initial||null),[readError,setReadError]=useState(''),[tick,setTick]=useState(0),[loaded,setLoaded]=useState(false);
  const sequence=useRef(0);
  const invalidate=useCallback(()=>{sequence.current++;},[]);
  const refresh=useCallback(()=>{sequence.current++;setTick(value=>value+1);},[]);
  useEffect(()=>{
    const controller=new AbortController();let alive=true;
    const load=(quiet=false)=>{const current=++sequence.current;
      const read=id?Promise.all([quiet?meetingSessions.nativeStatus(id,controller.signal,true):meetingSessions.nativeStatus(id,controller.signal),quiet?meetingSessions.nativeStatus(undefined,controller.signal,true):meetingSessions.nativeStatus(undefined,controller.signal)])
        .then(([selected,global])=>{const value=captureStatus(selected),workspace=captureStatus(global);
          return {...value,active:workspace.active??value.active,owners:workspace.owners??value.owners,recovery:workspace.recovery??value.recovery};})
        :(quiet?meetingSessions.nativeStatus(undefined,controller.signal,true):meetingSessions.nativeStatus(undefined,controller.signal)).then(captureStatus);
      void read.then(value=>{if(alive&&!controller.signal.aborted&&current===sequence.current){setStatus(value);setLoaded(true);setReadError('');}})
        .catch(failure=>{if(alive&&!controller.signal.aborted&&current===sequence.current)setReadError(failureText(failure));});
    };
    load();const timer=setInterval(()=>load(true),5000);
    return()=>{alive=false;controller.abort();sequence.current++;clearInterval(timer);};
  },[id,tick]);
  return {status,readError,invalidate,refresh,loaded};
}
function useCommandLifetime(){
  const live=useRef(true),operation=useRef(false),controllers=useRef(new Set<AbortController>());
  useEffect(()=>{live.current=true;return()=>{live.current=false;for(const controller of controllers.current)controller.abort();controllers.current.clear();};},[]);
  const read=async(id:string)=>{const controller=new AbortController();controllers.current.add(controller);
    try{return await meetingSessions.get(id,controller.signal);}finally{controllers.current.delete(controller);}};
  return {live,operation,read};
}

export function NativeCaptureBar({onOpen}:{onOpen:(id:string)=>void}){
  const {status,readError,invalidate,refresh}=useCaptureStatus(),{live,operation,read}=useCommandLifetime();
  const [busy,setBusy]=useState(''),[error,setError]=useState(''),[preflightError,setPreflightError]=useState(''),[failedSession,setFailedSession]=useState<string|null>(null);
  const registered=owners(status),recovery=status?.recovery||[];
  const entries=[...registered.map(item=>({item,notice:recovery.find(value=>value.session_id===item.session_id)})),
    ...recovery.filter(notice=>!registered.some(item=>item.session_id===notice.session_id)).map(notice=>({item:null,notice}))];
  const control=async(id:string,action:'pause'|'resume'|'stop',notice?:NativeCaptureRecovery)=>{
    if(operation.current)return;operation.current=true;setBusy(action);setError('');setPreflightError('');setFailedSession(id);invalidate();
    const finish=beginActivity(action==='stop'?'Arrêt et conservation de la réunion…':action==='pause'?'Mise en pause de la réunion…':'Reprise de la réunion…');
    let dispatched=false;
    try{
      if(action==='stop'&&hasDesktopCapture()){
        dispatched=true;
        await meetingSessions.stopDesktopCapture(id);
        if(live.current)setFailedSession(null);
        return;
      }
      const row=await read(id);if(!live.current)return;
      if(row.native_capture?.can_control===false||row.native_recovery?.some(item=>item.session_id===id&&!item.can_control))throw new Error('Cette séance est accessible en lecture seule.');
      if(action!=='stop'&&(row.native_capture?.process_alive===false||row.native_capture?.process_alive===null))throw new Error('La capture Windows est interrompue. Vérifiez son arrêt.');
      dispatched=true;
      const result=await meetingSessions.native(id,action,action==='stop'?stopCommand(row,notice):sessionCommand(row.revision));
      if(!live.current)return;
      if(action==='stop'&&result.state!=='completed')setError('La conservation Windows reste à terminer. Vérifiez l’arrêt avant de reprendre.');
      else setFailedSession(null);
    }catch(failure){if(live.current){(dispatched?setError:setPreflightError)(failureText(failure));setFailedSession(id);}}
    finally{finish();operation.current=false;if(live.current){setBusy('');refresh();}}
  };
  if(!entries.length&&!error&&!readError&&!preflightError)return null;
  const hasRunning=registered.some(running);
  return <section className="meeting-capture-bar" aria-label={hasRunning?'Capture Windows active':'Capture Windows à vérifier'}>
    {entries.map(({item,notice})=>{const id=item?.session_id||notice!.session_id,active=!!item&&running(item),canControl=item?.can_control!==false&&notice?.can_control!==false;
      const startPending=!!localStorage.getItem(commandKey(id,'start')),recoveryError=recoveryMessage(item,notice);
      return <div key={id}><strong>Capture Windows · {active?(item!.state==='paused'?'En pause':item!.state==='starting'?'Démarrage':'Enregistrement'):
        notice?.reason==='conservation-pending'?'Conservation à terminer':'Arrêt à vérifier'}</strong>
        {item&&<span> · {item.tracks.map(track=>track==='mic'?'Microphone':'Audio de Windows').join(' + ')}</span>}
        <button type="button" onClick={()=>onOpen(id)}>Revenir à la séance</button>
        {active&&<button type="button" disabled={!!busy||!canControl||startPending||item!.state==='starting'} onClick={()=>void control(id,item!.state==='paused'?'resume':'pause',notice)}>{item!.state==='paused'?'Reprendre':'Pause'}</button>}
        {(item||notice?.pending_stop)&&<button type="button" disabled={!!busy||!canControl||startPending} onClick={()=>void control(id,'stop',notice)}>{active?'Arrêter et conserver':notice?.pending_stop?'Reprendre la conservation Windows':'Vérifier l’arrêt Windows'}</button>}
        {startPending&&<p>Le démarrage conservé reste à vérifier dans la séance.</p>}
        {recoveryError&&<p role="alert">{recoveryError}</p>}
        {!canControl&&<p>Cette séance est accessible en lecture seule.</p>}</div>;
    })}
    {busy&&<p role="status">Traitement de la capture Windows…</p>}
    {readError&&<p role="alert">État Windows indisponible : {readError}. L’arrêt n’est pas confirmé.</p>}
    {preflightError&&<p role="alert">Lecture de la séance : {preflightError}</p>}{error&&<p role="alert">{error}</p>}
    {failedSession&&(error||preflightError)&&<button type="button" onClick={()=>onOpen(failedSession)}>Ouvrir la séance à récupérer</button>}
  </section>;
}

type CaptureProps={session:MeetingSession;capabilities?:NativeCaptureStatus;onChanged:(row:MeetingSession)=>void;browserBusy:boolean;
  onAvailability?:(busy:boolean)=>void;onRecoveryControls?:(available:boolean)=>void};
export function NativeMeetingCapture(props:CaptureProps){return <SessionNativeCapture key={props.session.id} {...props}/>;}
function SessionNativeCapture({session,capabilities,onChanged,browserBusy,onAvailability,onRecoveryControls}:CaptureProps){
  const {status,readError,invalidate,refresh,loaded}=useCaptureStatus(session.id,capabilities),{live,operation,read}=useCommandLifetime();
  const [source,setSource]=useState<'system'|'mic'|'both'>('system'),[system,setSystem]=useState(''),[mic,setMic]=useState(''),[busy,setBusy]=useState(''),[error,setError]=useState(''),[preflightError,setPreflightError]=useState('');
  const [pendingStart,setPendingStart]=useState(()=>{try{return JSON.parse(localStorage.getItem(commandKey(session.id,'start'))||'null');}catch{return null;}});
  const [pendingStop,setPendingStop]=useState(()=>!!localStorage.getItem(commandKey(session.id,'stop')));
  const registered=owners(status),owner=registered.find(item=>item.session_id===session.id)||
    (status?.session?.session_id===session.id?status.session:null)||(!loaded?session.native_capture:null);
  const notice=(loaded?status?.recovery||[]:[...(status?.recovery||[]),...(session.native_recovery||[])]).find(item=>item.session_id===session.id);
  const active=owner&&running(owner)?owner:null,others=registered.some(item=>item.session_id!==session.id);
  const canControl=owner?.can_control!==false&&notice?.can_control!==false;
  const stopPending=pendingStop||!!notice?.pending_stop;
  const prepareCapture=!active&&(session.state!=='completed'||!!pendingStart);
  const verifyStart=!!pendingStart&&!!owner;
  const recoveryError=recoveryMessage(owner,notice);
  const panelAvailable=!!(status?.installed||owner||notice||pendingStop||pendingStart||readError);
  const partial=panelAvailable&&!owner&&!stopPending&&!pendingStart&&session.state==='interrupted'&&session.tracks?.length>0;
  useEffect(()=>{if(!pendingStart)return;setSource(pendingStart.tracks?.includes('mic')?(pendingStart.tracks?.includes('system')?'both':'mic'):'system');setSystem(pendingStart.devices?.system==null?'':String(pendingStart.devices.system));setMic(pendingStart.devices?.mic==null?'':String(pendingStart.devices.mic));},[pendingStart]);
  useEffect(()=>{onAvailability?.(!loaded||!!registered.length||!!owner||!!readError);},[status,owner,loaded,readError,onAvailability]);
  useEffect(()=>{onRecoveryControls?.(!!(owner||notice||pendingStop||pendingStart||partial||readError));},[owner,notice,pendingStop,pendingStart,partial,readError,onRecoveryControls]);
  useEffect(()=>()=>onRecoveryControls?.(false),[onRecoveryControls]);
  const control=async(action:'start'|'pause'|'resume'|'stop'|'finalize')=>{
    if(operation.current||!canControl)return;operation.current=true;setBusy(action);setError('');setPreflightError('');invalidate();let dispatched=false;
    const finish=beginActivity(action==='start'?'Démarrage de la réunion…':action==='pause'?'Mise en pause de la réunion…':action==='resume'?'Reprise de la réunion…':'Conservation de la réunion…');
    try{
      const latest=action==='stop'&&hasDesktopCapture()?session:await read(session.id);if(!live.current)return;
      if(latest.native_capture?.can_control===false||latest.native_recovery?.some(item=>item.session_id===session.id&&!item.can_control))throw new Error('Cette séance est accessible en lecture seule.');
      if((action==='pause'||action==='resume')&&(latest.native_capture?.process_alive===false||latest.native_capture?.process_alive===null))throw new Error('La capture Windows est interrompue. Vérifiez son arrêt.');
      if(action==='finalize'&&latest.native_capture)throw new Error('Vérifiez l’arrêt Windows avant de conserver les fragments.');
      const body={...(action==='stop'?stopCommand(latest,notice):action==='start'&&pendingStart?pendingStart:sessionCommand(latest.revision)),...(action==='start'&&!pendingStart?{
        tracks:source==='both'?['mic','system'] as const:source==='mic'?['mic'] as const:['system'] as const,
        devices:{...(source!=='mic'&&system!==''?{system:Number(system)}:{}),...(source!=='system'&&mic!==''?{mic:Number(mic)}:{})}}:{})};
      if(action==='start')setPendingStart(body);dispatched=true;
      const result=action==='stop'&&hasDesktopCapture()?await meetingSessions.stopDesktopCapture(session.id):
        action==='finalize'?await meetingSessions.command(session.id,'finalize',body):
        await meetingSessions.native(session.id,action,{...body,tracks:body.tracks?[...body.tracks]:undefined});
      if(!live.current)return;onChanged(result);
      if(action==='start')setPendingStart(null);
      if(action==='stop'){setPendingStop(result.state!=='completed'||!!localStorage.getItem(commandKey(session.id,'stop')));
        if(result.state!=='completed')setError('La conservation Windows reste à terminer. Vérifiez l’arrêt avant de reprendre.');}
    }catch(failure){if(!live.current)return;(dispatched?setError:setPreflightError)(failureText(failure));
      if(action==='start'&&!localStorage.getItem(commandKey(session.id,'start')))setPendingStart(null);
      if(action==='stop'){
        setPendingStop(!!localStorage.getItem(commandKey(session.id,'stop')));
        try{const latest=await read(session.id);if(live.current)onChanged(latest);}catch{/* Read failure cannot confirm completion or erase the command error. */}
      }
    }finally{finish();operation.current=false;if(live.current){setBusy('');refresh();}}
  };
  if(!status?.installed&&!owner&&!notice&&!pendingStop&&!pendingStart&&!readError)return null;
  return <section className="meeting-native meeting-audio-setup" aria-label="Audio de la réunion"><h2 className={prepareCapture?'meeting-visually-hidden':undefined}>Audio de la réunion</h2>
    {active&&<><p role="status">{active.state==='paused'?'Enregistrement en pause.':active.state==='starting'?'Démarrage Windows en cours.':'Enregistrement en cours.'} {active.tracks.map(track=>track==='mic'?'Microphone':'Son du PC').join(' + ')}</p>
      <button type="button" disabled={!!busy||!canControl||!!pendingStart||active.state==='starting'} onClick={()=>void control(active.state==='paused'?'resume':'pause')}>{active.state==='paused'?'Reprendre la capture Windows':'Mettre Windows en pause'}</button>
      <button type="button" disabled={!!busy||!canControl||!!pendingStart} onClick={()=>void control('stop')}>Arrêter Windows et conserver la séance</button></>}
    {verifyStart&&<button className="meeting-start" type="button" disabled={!!busy||browserBusy||!!readError||!canControl||!!others} onClick={()=>void control('start')}>Vérifier le démarrage conservé</button>}
    {!active&&stopPending&&<button type="button" disabled={!!busy||!canControl||!!pendingStart} onClick={()=>void control('stop')}>Reprendre la conservation Windows</button>}
    {!active&&owner&&!stopPending&&<button type="button" disabled={!!busy||!canControl||!!pendingStart} onClick={()=>void control('stop')}>Vérifier l’arrêt Windows</button>}
    {partial&&<div className="meeting-interrupted-conservation"><p>Conservation partielle : seuls les fragments déjà acquittés seront regroupés. Les fichiers et journaux natifs restent conservés pour récupération.</p>
      <button type="button" disabled={!!busy||browserBusy||!canControl||!!readError} onClick={()=>void control('finalize')}>Conserver les fragments acquittés</button></div>}
    {owner&&!active&&<p role="status">La capture Windows reste à vérifier. Son arrêt et la conservation complète ne sont pas confirmés.</p>}
    {!canControl&&<p>Cette séance est accessible en lecture seule.</p>}
    {recoveryError&&<p role="alert">{recoveryError}</p>}
    {status?.session?.error&&<p role="alert">{status.session.error}</p>}
    {prepareCapture&&<div className="meeting-audio-devices"><label>Source audio de la réunion<select value={source} disabled={!!busy||!!pendingStart||!canControl} onChange={event=>setSource(event.target.value as typeof source)}>
      <option value="system">À distance · son du PC</option><option value="both">À distance · son du PC + ma voix</option><option value="mic">En salle · microphone</option>
      </select></label><details className="meeting-device-options"><summary>Périphériques</summary><div><label>Sortie Windows à enregistrer<select value={system} disabled={source==='mic'||!!busy||!!pendingStart||!canControl} onChange={event=>setSystem(event.target.value)}><option value="">Sortie par défaut</option>
      {(status?.devices||[]).filter(device=>device.isLoopbackDevice).map(device=><option key={device.index} value={device.index}>{device.name}</option>)}</select></label>
      <div className="meeting-audio-microphone"><label>Microphone à utiliser<select value={mic} disabled={source==='system'||!!busy||!!pendingStart||!canControl} onChange={event=>setMic(event.target.value)}><option value="">Microphone par défaut</option>
          {(status?.devices||[]).filter(device=>device.maxInputChannels>0&&!device.isLoopbackDevice).map(device=><option key={device.index} value={device.index}>{device.name}</option>)}</select></label></div><details className="meeting-audio-diagnostics"><summary>État des périphériques</summary><p>{status?.loopback_ready?'Audio de Windows qualifié sur ce PC.':'Audio de Windows détecté ; test réel à effectuer.'} {status?.microphone_test_passed?'Microphone qualifié.':'Microphone non qualifié ; il reste désactivé par défaut.'}</p></details></div></details>
      {!verifyStart&&<button className="meeting-start" type="button" disabled={!!busy||browserBusy||!!readError||!canControl||!!others||!status?.ready||!!registered.length||!!notice||(!pendingStart&&!['created','interrupted'].includes(session.state))} onClick={()=>void control('start')}>{pendingStart?'Reprendre le démarrage Windows conservé':'Démarrer la réunion'}</button>}
      {pendingStart&&<p>La reprise utilise les pistes et périphériques affichés, conservés dans la commande initiale.</p>}</div>}
    {prepareCapture&&<p className="meeting-audio-help">{source==='system'?'Votre voix n’est pas enregistrée (son du PC).':source==='mic'?'Microphone : personnes présentes dans la salle.':'Son du PC et votre voix seront enregistrés.'}{source!=='system'&&' Microphone activé au démarrage.'}</p>}
    {!active&&session.state==='completed'&&!pendingStart&&!owner&&!notice&&!stopPending&&<p className="meeting-audio-help">Enregistrement terminé et conservé. Créez une nouvelle séance pour enregistrer une autre réunion.</p>}
    {!!others&&<p role="status">Une autre séance utilise déjà la capture Windows ou garde une réservation à vérifier. Arrêtez-la depuis la barre de capture avant de démarrer ici.</p>}
    {browserBusy&&<p role="status">Un enregistrement navigateur est en cours ou reste à conserver.</p>}
    {!status?.ready&&<p role="status">La capture Windows est indisponible.{status?.error&&` ${status.error}`}</p>}
    {!prepareCapture&&<><details className="meeting-audio-diagnostics"><summary>État des périphériques</summary><p>{status?.loopback_ready?'Audio de Windows qualifié sur ce PC.':'Audio de Windows détecté ; test réel à effectuer.'} {status?.microphone_test_passed?'Microphone qualifié.':'Microphone non qualifié ; il reste désactivé par défaut.'}</p></details></>}
    {busy&&<p role="status">Traitement de la capture Windows…</p>}
    {readError&&<p role="alert">État Windows indisponible : {readError}. L’arrêt n’est pas confirmé.</p>}
    {preflightError&&<p role="alert">Lecture de la séance : {preflightError}</p>}{error&&<p role="alert">{error}</p>}
  </section>;
}
