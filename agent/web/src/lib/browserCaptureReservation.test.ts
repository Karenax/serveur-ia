import {afterEach,expect,it} from 'vitest';
import {LocalBrowserReservation} from './browserCaptureReservation';

afterEach(()=>localStorage.clear());
const key='agent.browser-capture-reservation.v1';
const owner='2a62875a-2b27-4925-9a15-390032aee5b1';
const command='3a62875a-2b27-4925-9a15-390032aee5b1';
const lease='4a62875a-2b27-4925-9a15-390032aee5b1';
const original={session_id:'session-fictive',owner_id:owner,acknowledged:true,
  reserve:{command_id:command,expected_revision:1,owner_id:owner}};

it('relit les réservations antérieures et celles qui possèdent une boucle Linux',()=>{
  const store=new LocalBrowserReservation();store.write(original);expect(store.read()).toEqual(original);
  store.write({...original,linux_loopback_id:lease});expect(store.read()?.linux_loopback_id).toBe(lease);
});

it.each([null,42,'source-arbitraire'])('conserve une réservation dont l’identifiant de boucle est invalide : %s',invalid=>{
  const raw=JSON.stringify({...original,linux_loopback_id:invalid});localStorage.setItem(key,raw);
  expect(()=>new LocalBrowserReservation().read()).toThrow('réservation audio conservée');
  expect(localStorage.getItem(key)).toBe(raw);
});
