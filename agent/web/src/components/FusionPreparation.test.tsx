import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {FusionInsights} from './FusionInsights';
import {fusionInsights,type FusionSettings,type FusionStats} from '../lib/fusionInsights';
import {meetingCapture} from '../lib/meetingCapture';

const settings:FusionSettings={enabled:true,proactive_enabled:false,auto_enhancement_enabled:false,mode:'network',onboarding_complete:false,
  capabilities:{enabled:true,capture:{durable:true,max_upload_mb:50,max_duration_minutes:120,tracks:['mic'],browser_permission_required:true},
    transcription:{batch_ready:true,live_ready:false,live_operational:true,detail:'Direct disponible en essai ; relecture nécessaire.'},notes:{staging:true,erp_projection:true}}};
const stats:FusionStats={sources:{total:0,by_type:{},extracted:0,indexed:0,current:0},sessions:{total:0,by_state:{},duration_seconds:0,audio_bytes:0},
  assistant:{answers:0,stale:0,enhancements:0,p50_seconds:null,p95_seconds:null,tokens:null},engines:{speech:{},generation:{placement:'network',configured:false}},
  index:{text_passages:0,profiles:[],size_bytes:0},formulas:{}};
beforeEach(()=>{
  vi.spyOn(fusionInsights,'readiness').mockReturnValue(new Promise(()=>{}));
  vi.spyOn(fusionInsights,'settings').mockResolvedValue(settings);vi.spyOn(fusionInsights,'stats').mockResolvedValue(stats);
  vi.spyOn(meetingCapture,'getSnapshot').mockReturnValue({sessionId:null,title:'',phase:'idle',tracks:[],seconds:0,totalBytes:0,savedBytes:0,pending:0,error:''});
});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
it('enregistre le calcul GPU sans activer la transcription ni ouvrir le microphone',async()=>{
  const existing:FusionSettings={...settings,live_speech_device:'cpu',speech_acceleration:{selected:'cpu',cuda_available:true,environment_override:false,detail:'GPU disponible en essai.',selection_starts_model:false}};
  vi.mocked(fusionInsights.settings).mockResolvedValue(existing);
  const save=vi.spyOn(fusionInsights,'save').mockResolvedValue({...existing,live_speech_device:'cuda'}),start=vi.spyOn(meetingCapture,'start');
  render(<FusionInsights rows={[]} initialTab="preparation"/>);
  const choice=await screen.findByLabelText('Calcul de la transcription directe');
  fireEvent.change(choice,{target:{value:'cuda'}});
  expect(screen.getByLabelText('Autoriser la transcription directe en essai')).toHaveProperty('checked',false);
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer les réglages'}));
  await waitFor(()=>expect(save).toHaveBeenCalledExactlyOnceWith({enabled:true,live_transcription_enabled:false,live_speech_device:'cuda',proactive_enabled:false,auto_enhancement_enabled:false,mode:'network',onboarding_complete:false}));
  expect(start).not.toHaveBeenCalled();expect(choice).toHaveProperty('value','cuda');
});

it('garde le GPU indisponible et respecte un calcul imposé par le service',async()=>{
  const existing:FusionSettings={...settings,live_speech_device:'cpu',speech_acceleration:{selected:'cpu',cuda_available:false,environment_override:true,detail:'Installation absente.',selection_starts_model:false}};
  vi.mocked(fusionInsights.settings).mockResolvedValue(existing);
  render(<FusionInsights rows={[]} initialTab="preparation"/>);
  expect(await screen.findByLabelText('Calcul de la transcription directe')).toHaveProperty('disabled',true);
  expect(screen.getByRole('option',{name:/Carte graphique/})).toHaveProperty('disabled',true);
});
it('un moteur disponible ne fait aucun opt-in implicite et conserve installation inconnue distincte de désactivation',async()=>{
  const save=vi.spyOn(fusionInsights,'save'),start=vi.spyOn(meetingCapture,'start');
  render(<FusionInsights rows={[]} initialTab="preparation"/>);
  expect(await screen.findByLabelText('Autoriser la transcription directe en essai')).toHaveProperty('checked',false);
  expect(screen.getByText(/Installation du moteur direct : non renseignée/).textContent).toContain('Activation enregistrée : désactivée');
  expect(screen.getByText(/Installation du moteur direct : non renseignée/).textContent).toContain('Moteur direct : disponible pour essai');
  expect(screen.getByText(/Direct en essai, qualité et latence non qualifiées/)).toBeTruthy();
  expect(save).not.toHaveBeenCalled();expect(start).not.toHaveBeenCalled();
});
it('enregistre le seul opt-in direct en gardant proactif et enrichissement à leurs valeurs existantes',async()=>{
  const existing={...settings,proactive_enabled:true,auto_enhancement_enabled:true};vi.mocked(fusionInsights.settings).mockResolvedValue(existing);
  const save=vi.spyOn(fusionInsights,'save').mockResolvedValue({...existing,live_transcription_enabled:true});
  render(<FusionInsights rows={[]} initialTab="preparation"/>);
  fireEvent.click(await screen.findByLabelText('Autoriser la transcription directe en essai'));
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer les réglages'}));
  await waitFor(()=>expect(save).toHaveBeenCalledExactlyOnceWith({enabled:true,live_transcription_enabled:true,proactive_enabled:true,auto_enhancement_enabled:true,mode:'network',onboarding_complete:false}));
  expect(screen.getByLabelText('Activer l’espace de séance')).toHaveProperty('checked',true);
});
it('une sauvegarde refusée garde l’activation serveur désactivée et le choix local sans lancer de capture',async()=>{
  const save=vi.spyOn(fusionInsights,'save').mockRejectedValue(new Error('Réglage refusé')),start=vi.spyOn(meetingCapture,'start');
  render(<FusionInsights rows={[]} initialTab="preparation"/>);
  fireEvent.click(await screen.findByLabelText('Autoriser la transcription directe en essai'));
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer les réglages'}));
  expect((await screen.findByRole('alert')).textContent).toContain('Réglage refusé');
  expect(screen.getByLabelText('Autoriser la transcription directe en essai')).toHaveProperty('checked',true);
  expect(screen.getByText(/Installation du moteur direct/).textContent).toContain('Activation enregistrée : désactivée');
  expect(save).toHaveBeenCalledOnce();expect(start).not.toHaveBeenCalled();
});
it('terminer la préparation conserve le direct désactivé malgré disponibilité batch et moteur',async()=>{
  const save=vi.spyOn(fusionInsights,'save').mockResolvedValue({...settings,onboarding_complete:true});
  render(<FusionInsights rows={[]} initialTab="preparation"/>);
  await screen.findByLabelText('Autoriser la transcription directe en essai');
  fireEvent.click(screen.getByRole('button',{name:'Terminer la préparation'}));
  await waitFor(()=>expect(save).toHaveBeenCalledExactlyOnceWith({enabled:true,live_transcription_enabled:false,proactive_enabled:false,auto_enhancement_enabled:false,mode:'network',onboarding_complete:true}));
});
