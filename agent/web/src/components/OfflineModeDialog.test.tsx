import {afterEach,it,expect,vi} from 'vitest';
import {cleanup,render,screen,fireEvent} from '@testing-library/react';
import {request} from '../lib/http';
import {ConnectionStatus} from './ConnectionStatus';

vi.mock('../lib/http',()=>({request:vi.fn()}));
Object.defineProperty(HTMLDialogElement.prototype,'showModal',{configurable:true,writable:true,value:function(this:HTMLDialogElement){this.setAttribute('open','');}});
Object.defineProperty(HTMLDialogElement.prototype,'close',{configurable:true,writable:true,value:function(this:HTMLDialogElement){this.removeAttribute('open');}});
afterEach(()=>{cleanup();vi.restoreAllMocks();vi.clearAllMocks();});
const offline={outage_id:'outage',remaining_seconds:0,approval_required:true,decision:null,using_fallback:false};
const service={state:'ok',detail:'Accessible'};
const snapshot={services:{llm:service,embedding:service,memory:service},refreshing:false};
function setup(approval=true){
  let current={...offline,approval_required:approval,remaining_seconds:approval?0:60};
  vi.spyOn(HTMLDialogElement.prototype,'showModal').mockImplementation(function(this:HTMLDialogElement){this.setAttribute('open','');});
  vi.spyOn(HTMLDialogElement.prototype,'close').mockImplementation(function(this:HTMLDialogElement){this.removeAttribute('open');});
  vi.mocked(request).mockImplementation(async(url,options)=>{
    if(String(url).includes('offline-decision')){
      const {decision}=JSON.parse(String(options?.body));
      current={...offline,approval_required:false,decision,using_fallback:decision==='offline'};
      return current;
    }
    return {...snapshot,offline:current};
  });
  render(<ConnectionStatus/>);
}
it('attend le délai serveur sans afficher de popup ni envoyer de consentement',async()=>{
  setup(false);
  await screen.findByText('Services accessibles');
  expect(screen.queryByRole('dialog')).toBeNull();
  expect(request).toHaveBeenCalledTimes(1);
});
it.each(['Attendre la connexion','Passer hors ligne'])('enregistre uniquement le choix explicite : %s',async(label)=>{
  setup();
  const modal=await screen.findByRole('dialog',{name:'Serveur IA sans réponse'});
  expect(modal.textContent).toContain('deux minutes');
  expect(request).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole('button',{name:label}));
  await vi.waitFor(()=>expect(screen.queryByRole('dialog')).toBeNull());
  expect(request).toHaveBeenCalledWith('/v1/settings/ai/offline-decision',expect.objectContaining({
    method:'POST',body:JSON.stringify({outage_id:'outage',decision:label==='Passer hors ligne'?'offline':'wait'})}),20000);
  if(label==='Attendre la connexion'){
    fireEvent.click(screen.getByText('État du système'));
    fireEvent.click(screen.getByRole('button',{name:'Choisir le mode hors ligne'}));
    expect(screen.getByRole('dialog')).toBeTruthy();
  }
});
