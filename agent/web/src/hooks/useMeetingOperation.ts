import {useRef, useState, type RefObject} from 'react';
import {beginActivity} from '../lib/asyncActivity';
import {meetingErrorText, SessionReadFailure} from './useMeetingSessionSnapshot';

/** Only one user operation may own the session controls at a time. */
export function useMeetingOperation(alive:RefObject<boolean>, setError:(message:string)=>void) {
  const [operation,setOperation] = useState('');
  const running = useRef(false);
  const run = async (label:string, task:()=>Promise<void>) => {
    // React can batch multiple events before disabled buttons are rendered.
    if (running.current) return;
    running.current = true;
    setOperation(label);
    setError('');
    const finish = beginActivity(label);
    try {await task();}
    catch (failure) {if (alive.current && !(failure instanceof SessionReadFailure)) setError(meetingErrorText(failure));}
    finally {finish();running.current = false;if (alive.current) setOperation('');}
  };
  return {operation,run};
}
