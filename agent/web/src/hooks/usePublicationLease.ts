import {useEffect, useRef, useState} from 'react';

export type PublicationLeaseState = 'checking' | 'held' | 'busy' | 'unavailable' | 'inactive';

/** Keep one local writer for a session until the publication view is closed. */
export function usePublicationLease(sessionId:string, enabled:boolean, onAcquired:()=>boolean) {
  const [state,setState]=useState<PublicationLeaseState>(enabled?'checking':'inactive');
  const [attempt,setAttempt]=useState(0);
  const owns=useRef(false);
  const acquired=useRef(onAcquired);acquired.current=onAcquired;
  useEffect(()=>{
    let alive=true,release:(()=>void)|undefined;
    owns.current=false;
    if(!enabled){setState('inactive');return;}
    if(!navigator.locks?.request){setState('unavailable');return;}
    setState('checking');
    try{
      void navigator.locks.request(`agent-meeting-publication:${sessionId}`,{ifAvailable:true},async lock=>{
        if(!alive)return;
        if(!lock){setState('busy');return;}
        if(!acquired.current()){setState('unavailable');return;}
        owns.current=true;setState('held');
        try{await new Promise<void>(resolve=>{release=resolve;});}
        finally{owns.current=false;}
      }).catch(()=>{if(alive){owns.current=false;setState('unavailable');}});
    }catch{if(alive){owns.current=false;setState('unavailable');}}
    return()=>{alive=false;owns.current=false;release?.();};
  },[sessionId,enabled,attempt]);
  return {state,owns,retry:()=>setAttempt(value=>value+1)};
}
