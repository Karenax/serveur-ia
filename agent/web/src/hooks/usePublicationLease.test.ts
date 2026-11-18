import {afterEach, expect, it, vi} from 'vitest';
import {act, cleanup, renderHook, waitFor} from '@testing-library/react';
import {usePublicationLease} from './usePublicationLease';

const original=Object.getOwnPropertyDescriptor(navigator,'locks');
afterEach(()=>{cleanup();if(original)Object.defineProperty(navigator,'locks',original);else delete (navigator as {locks?:LockManager}).locks;});
function installLocks(){
 const held=new Set<string>();
 Object.defineProperty(navigator,'locks',{configurable:true,value:{request:(name:string,_options:unknown,callback:(lock:Lock|null)=>Promise<void>)=>{
  if(held.has(name))return callback(null);
  held.add(name);
  return callback({name,mode:'exclusive'} as Lock).finally(()=>held.delete(name));
 }}});
 return held;
}
it('protège une séance entre fenêtres et permet la reprise après fermeture',async()=>{
 const held=installLocks(),firstAcquired=vi.fn(()=>true),secondAcquired=vi.fn(()=>true);
 const first=renderHook(()=>usePublicationLease('session-a',true,firstAcquired));
 await waitFor(()=>expect(first.result.current.state).toBe('held'));
 const second=renderHook(()=>usePublicationLease('session-a',true,secondAcquired));
 await waitFor(()=>expect(second.result.current.state).toBe('busy'));
 expect(secondAcquired).not.toHaveBeenCalled();
 expect(first.result.current.owns.current).toBe(true);
 first.unmount();await waitFor(()=>expect(held.size).toBe(0));
 act(()=>second.result.current.retry());
 await waitFor(()=>expect(second.result.current.state).toBe('held'));
 expect(secondAcquired).toHaveBeenCalledTimes(1);
});
it('ne bloque pas la publication d’une autre séance',async()=>{
 installLocks();
 const first=renderHook(()=>usePublicationLease('session-a',true,()=>true));
 const second=renderHook(()=>usePublicationLease('session-b',true,()=>true));
 await waitFor(()=>expect([first.result.current.state,second.result.current.state]).toEqual(['held','held']));
});
it('désactive la modification si la protection du navigateur est absente',async()=>{
 Object.defineProperty(navigator,'locks',{configurable:true,value:undefined});
 const acquired=vi.fn(()=>true),view=renderHook(()=>usePublicationLease('session-a',true,acquired));
 await waitFor(()=>expect(view.result.current.state).toBe('unavailable'));
 expect(acquired).not.toHaveBeenCalled();expect(view.result.current.owns.current).toBe(false);
});
it('ne conserve pas le verrou quand le formulaire est fermé avant son attribution',async()=>{
 let callback!:(lock:Lock|null)=>Promise<void>;
 Object.defineProperty(navigator,'locks',{configurable:true,value:{request:(_name:string,_options:unknown,handler:typeof callback)=>{callback=handler;return new Promise(()=>{});}}});
 const acquired=vi.fn(()=>true),view=renderHook(()=>usePublicationLease('session-a',true,acquired));
 view.unmount();await callback({name:'session-a',mode:'exclusive'} as Lock);
 expect(acquired).not.toHaveBeenCalled();
});
