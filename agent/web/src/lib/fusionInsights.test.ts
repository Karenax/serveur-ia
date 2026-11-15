import {afterEach,expect,it,vi} from 'vitest';
import {fusionInsights} from './fusionInsights';
import {request} from './http';
vi.mock('./http',()=>({request:vi.fn()}));
afterEach(()=>vi.mocked(request).mockReset());
it('un réglage historique absent sérialise explicitement le direct désactivé sans changer les autres choix',async()=>{
  vi.mocked(request).mockResolvedValue({});
  await fusionInsights.save({enabled:true,proactive_enabled:true,auto_enhancement_enabled:false,mode:'local',onboarding_complete:false});
  const body=JSON.parse(String(vi.mocked(request).mock.calls[0][1]?.body));
  expect(body).toEqual({enabled:true,live_transcription_enabled:false,proactive_enabled:true,auto_enhancement_enabled:false,mode:'local',onboarding_complete:false});
});
it('un opt-in direct seul ne bascule ni le proactif ni les enrichissements',async()=>{
  vi.mocked(request).mockResolvedValue({});
  await fusionInsights.save({enabled:true,live_transcription_enabled:true,proactive_enabled:false,auto_enhancement_enabled:false,mode:'network',onboarding_complete:true});
  expect(JSON.parse(String(vi.mocked(request).mock.calls[0][1]?.body))).toEqual({enabled:true,live_transcription_enabled:true,proactive_enabled:false,auto_enhancement_enabled:false,mode:'network',onboarding_complete:true});
});
