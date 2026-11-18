type DurableAction = 'pause'|'resume'|'finalize'|'cancel'|'assign-project'|'retry-transcription'|
  'batch-transcription'|'cancel-batch-transcription'|`native-${'start'|'stop'|'pause'|'resume'}`;

const record=(value:unknown):Record<string,unknown>|null=>
  value!==null&&typeof value==='object'&&!Array.isArray(value)?value as Record<string,unknown>:null;
const resultingState:Partial<Record<DurableAction,string>>={pause:'paused',resume:'recording',finalize:'completed',cancel:'cancelled'};

export function matchesMeetingCommandResult(value:unknown,sessionId:string,action:DurableAction,owner:unknown):boolean {
  const result=record(value);
  const enveloped=action==='retry-transcription'||action==='batch-transcription'||action==='cancel-batch-transcription';
  const session=enveloped?record(result?.session):result;
  if(!session||session.id!==sessionId)return false;
  const expected=resultingState[action];
  if(expected&&session.state!==expected)return false;
  if(owner){
    const capture=record(session.browser_capture);
    if(capture?.owner_id!==owner||capture.can_control!==true)return false;
  }
  return true;
}

/** Validate a saved command receipt before it changes local recovery state. */
export function matchesMeetingCommandReceipt(value:unknown,sessionId:string,action:DurableAction,
  commandId:unknown,owner:unknown):boolean {
  const receipt=record(value);
  const expectedKind=action==='batch-transcription'?'transcription-batch':
    action==='cancel-batch-transcription'?'cancel-transcription-batch':
    action.startsWith('native-')?action.replace('native-','native.'):action;
  if(!receipt||receipt.id!==commandId||receipt.kind!==expectedKind)return false;
  if(receipt.status!=='completed')return true;
  if(!matchesMeetingCommandResult(receipt.result,sessionId,action,owner))return false;
  if(action==='native-stop'&&record(receipt.result)?.state!=='completed')return false;
  return true;
}

export type {DurableAction};
