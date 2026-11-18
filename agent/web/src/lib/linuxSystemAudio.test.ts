import {afterEach,expect,it,vi} from 'vitest';
import {linuxSystemAudio} from './linuxSystemAudio';

afterEach(()=>{delete document.body.dataset.kiaraLinuxSystemAudio;vi.unstubAllGlobals();});

it('réserve et libère la boucle auprès du relais local sans session distante',async()=>{
  document.body.dataset.kiaraLinuxSystemAudio='true';
  const fetch=vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({lease_id:'fictif',label:'source'})))
    .mockResolvedValueOnce(new Response(JSON.stringify({closed:true})));
  vi.stubGlobal('fetch',fetch);
  expect(linuxSystemAudio.available()).toBe(true);
  await linuxSystemAudio.start('fictif');await linuxSystemAudio.stop('fictif');
  expect(fetch).toHaveBeenCalledTimes(2);
  expect(fetch.mock.calls.map(call=>[call[0],JSON.parse(String(call[1].body)),call[1].credentials])).toEqual([
    ['/api/v1/kiara/linux-system-audio',{action:'start',lease_id:'fictif'},'same-origin'],
    ['/api/v1/kiara/linux-system-audio',{action:'stop',lease_id:'fictif'},'same-origin'],
  ]);
});

it('expose une fermeture locale non confirmée sans déclarer la boucle fermée',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({detail:'Fermeture non confirmée'}),{status:400})));
  await expect(linuxSystemAudio.stop('fictif')).rejects.toThrow('Fermeture non confirmée');
});
