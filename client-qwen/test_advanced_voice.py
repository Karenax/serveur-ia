"""Profile routing, owned inference and honest readiness without model downloads."""
import base64
import hashlib
import json
from pathlib import Path
import queue
import tempfile
import threading
import unittest
import time
from unittest.mock import patch
from advanced_voice import AdvancedVoice, audio_request, choose_execution


class AdvancedVoiceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.service=AdvancedVoice(self.temp.name);self.addCleanup(self.service.close)

    def install_fixture(self,passed=True):
        for file in self.service.paths():
            file.parent.mkdir(parents=True,exist_ok=True);file.write_text('{}',encoding='utf-8')
        (self.service.home/'benchmark.json').write_text(json.dumps({'passed':passed,'fingerprint':self.service.fingerprint(),'latency_ms':900}),encoding='utf-8')

    def gpu_fixture(self):
        root=self.service.home/'packs/fixture-v4';manifest={}
        for name in ('max-worker.exe','native/qwen.dll','native/ggml-base.dll','asr/model.onnx'):
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True);raw=b'fixture native data';path.write_bytes(raw)
            manifest[name]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        (self.service.home/'runtime.json').write_text(json.dumps({'format':2,'root':str(root),'manifest':manifest,
            'catalogue':{'runtime_api':4,'models':[{'name':'asr/model.onnx'}]}}),encoding='utf-8')
        cards=[{'id':'a'*24,'name':'Vulkan0','description':'AMD Radeon Graphics','kind':'integrated','free_bytes':48*1024**3,'total_bytes':64*1024**3},
               {'id':'b'*24,'name':'Vulkan1','description':'AMD Radeon RX 7800 XT','kind':'dedicated','free_bytes':2*1024**3,'total_bytes':16*1024**3}]
        self.service.gpu_inventory={'checked':True,'cards':cards,'recommended':'b'*24,'error':''};self.service.gpu_inventory_pack=str(root)
        return root,cards

    def test_gpu_selection_is_persisted_and_invalidates_measurements_without_requiring_a_new_test(self):
        _,cards=self.gpu_fixture();self.service.save_report({'fingerprint':self.service.fingerprint(),'passed':True,'latency_ms':700})
        with patch.object(self.service,'unload') as unload:
            status=self.service.set_gpu(cards[1]['id']);unload.assert_called_once_with('tts')
        self.assertTrue(status['available']);self.assertIsNone(status['test_passed']);self.assertEqual(status['gpu']['selection'],'b'*24)
        reopened=AdvancedVoice(self.service.home);self.addCleanup(reopened.close)
        self.assertEqual(reopened.gpu_selection(),'b'*24)
        self.assertEqual(reopened.native_command('tts')[-2:],['--gpu','b'*24])
        self.assertNotIn('--gpu',reopened.native_command('asr'))

    def test_french_voice_update_is_offered_without_disabling_installed_max_or_gpu_choice(self):
        self.gpu_fixture()
        before=self.service.status()
        self.assertTrue(before['update_recommended']);self.assertTrue(before['available']);self.assertTrue(before['gpu']['supported'])
        config=self.service.configuration();config['catalogue']['runtime_api']=6
        root=Path(config['root']);(root/'native/kiara-asr.dll').write_bytes(b'new ASR')
        config['manifest']['native/kiara-asr.dll']={'bytes':7,'sha256':hashlib.sha256(b'new ASR').hexdigest()}
        (self.service.home/'runtime.json').write_text(json.dumps(config),encoding='utf-8')
        after=self.service.status()
        self.assertFalse(after['update_recommended']);self.assertTrue(after['available']);self.assertTrue(after['gpu']['supported'])

    def test_realtime_gpu_selection_routes_to_recognition_and_ignores_unused_voice_assets(self):
        root,cards=self.gpu_fixture()
        config=self.service.configuration();config['catalogue']['runtime_api']=6
        (root/'native/kiara-asr.dll').write_bytes(b'new ASR')
        config['manifest']['native/kiara-asr.dll']={'bytes':7,'sha256':hashlib.sha256(b'new ASR').hexdigest()}
        config['manifest']['tts/model.q8.gguf']={'bytes':99,'sha256':'0'*64}
        (self.service.home/'runtime.json').write_text(json.dumps(config),encoding='utf-8')
        with patch.object(self.service,'unload') as unload:
            self.service.set_gpu(cards[1]['id']);unload.assert_called_once_with('asr')
        self.assertEqual(self.service.native_command('asr')[-2:],['--gpu',cards[1]['id']])
        self.assertNotIn('--gpu',self.service.native_command())
        with self.assertRaises(ValueError):self.service.native_command('tts')

    def test_old_python_custom_voice_also_reports_the_french_update(self):
        self.install_fixture()
        (self.service.home/'runtime.json').write_text(json.dumps({'models':[{'repo':'Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice'}]}),encoding='utf-8')
        self.assertTrue(self.service.status()['update_recommended'])
        self.assertTrue(self.service.status()['available'])

    def test_gpu_selection_cannot_change_during_calls_tests_or_for_unknown_cards(self):
        self.gpu_fixture()
        for value in ('Vulkan0','CPU','c'*24,None,[],{'device':'b'*24}):
            with self.assertRaises(ValueError):self.service.set_gpu(value)
        with patch.object(self.service,'start'):
            self.service.warm('alice','a'*32)
            with self.assertRaises(ValueError):self.service.set_gpu('b'*24)
            self.service.release('alice','a'*32)
        self.service.testing=True
        with self.assertRaises(ValueError):self.service.set_gpu('b'*24)
        self.service.testing=False
        self.assertEqual(self.service.gpu_selection(),'auto')

    def test_gpu_probe_checks_runtime_without_loading_or_reading_model_weights(self):
        root,cards=self.gpu_fixture();(root/'asr/model.onnx').unlink()
        with patch('advanced_voice.subprocess.run') as run:
            run.return_value.returncode=0;run.return_value.stdout=json.dumps({'devices':cards,'recommended':'b'*24})
            status=self.service.detect_devices()
        self.assertTrue(status['gpu']['checked']);self.assertEqual(status['gpu']['recommended'],'b'*24)
        self.assertIn('--probe-gpus',run.call_args.args[0]);self.assertFalse(self.service.processes)
        (root/'native/qwen.dll').write_bytes(b'tampered')
        with patch('advanced_voice.subprocess.run') as run:
            with self.assertRaisesRegex(ValueError,'corrompu'):self.service.detect_devices()
            run.assert_not_called()
        self.assertFalse(self.service.maintenance);self.assertFalse(self.service.probing)

    def test_gpu_probe_rejects_bad_outputs_and_can_be_retried(self):
        _,cards=self.gpu_fixture()
        with patch('advanced_voice.subprocess.run') as run:
            run.return_value.returncode=0;run.return_value.stdout=json.dumps({'devices':[{'id':'b'*24}],'recommended':'b'*24})
            with self.assertRaises(ValueError):self.service.detect_devices()
            self.assertFalse(self.service.status()['gpu']['checked']);self.assertEqual(self.service.status()['gpu']['cards'],[])
            run.return_value.stdout=json.dumps({'devices':cards,'recommended':'b'*24})
            self.assertFalse(self.service.detect_devices()['gpu']['error'])
        self.assertFalse(self.service.maintenance)

    def test_only_missing_installation_blocks_use_benchmarks_are_advisory(self):
        self.assertFalse(self.service.status()['available'])
        self.install_fixture(False);self.assertTrue(self.service.status()['available'])
        self.assertEqual(self.service.status()['performance'],'limited')
        self.install_fixture();self.assertTrue(self.service.status()['available'])
        self.service.paths()[1].write_text('changed');self.assertTrue(self.service.status()['available'])
        self.assertEqual(self.service.status()['performance'],'unmeasured')
        self.service.paths()[0].unlink();self.assertFalse(self.service.status()['available'])

    def test_slow_or_failed_test_allows_explicit_pc_use_and_a_retry(self):
        self.install_fixture(False)
        self.service.error='Le test a échoué'
        self.service.error_code='gpu_unavailable'
        with patch.object(self.service,'start') as start:
            self.service.warm('alice','a'*32)
            self.assertFalse(self.service.error)
            self.assertEqual(start.call_count,2)
        self.service.release('alice','a'*32)
        self.assertEqual(choose_execution(self.service.status(),{'available':True,'latency_ms':10},'pc'),'pc')

    def test_maintenance_cannot_interrupt_or_start_a_call(self):
        self.install_fixture()
        with patch.object(self.service,'start'):
            self.service.warm('alice','a'*32)
            with self.assertRaises(ValueError):self.service.begin_maintenance()
            self.service.release('alice','a'*32)
        self.service.begin_maintenance()
        self.assertFalse(self.service.status()['available'])
        with self.assertRaises(ValueError):self.service.warm('alice','b'*32)
        with self.assertRaises(ValueError):self.service.test()
        self.service.end_maintenance()
        self.assertTrue(self.service.status()['available'])

    def test_auto_uses_only_measured_available_targets_and_manual_choice_is_respected(self):
        pc={'available':True,'latency_ms':1200};server={'available':True,'latency_ms':600}
        self.assertEqual(choose_execution(pc,server),'server')
        self.assertEqual(choose_execution(pc,server,'pc'),'pc')
        self.assertEqual(choose_execution(pc,{**server,'busy':True}),'pc')
        failed={**pc,'error_code':'gpu_unavailable','latency_ms':1}
        self.assertEqual(choose_execution(failed,server),'server')
        self.assertEqual(choose_execution(failed,server,'pc'),'pc')
        for place in ('auto','pc','server','external'):
            with self.assertRaises(ValueError):choose_execution({}, {}, place)

    def test_pcm_boundary_and_injected_fields(self):
        body={'rate':16000,'pcm':base64.b64encode(b'\0\0'*1600).decode()}
        self.assertEqual(len(audio_request(body)),3200)
        for value in ({**body,'url':'https://example.invalid'},{**body,'rate':24000},{**body,'pcm':'!!!'},
                      {**body,'pcm':base64.b64encode(b'x').decode()},{**body,'request_id':'old'},
                      {**body,'pcm':'A'*1300000},[]):
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaises(ValueError):audio_request(value)

    def test_failed_readiness_cannot_spawn_models_or_consume_audio(self):
        with patch('advanced_voice.subprocess.Popen') as process:
            with self.assertRaises(ValueError):list(self.service.frames('alice','transcribe',{'rate':16000,'pcm':'AAA='}))
            process.assert_not_called()

    def test_an_active_call_reserves_the_runtime_and_prevents_retesting(self):
        self.install_fixture()
        with patch.object(self.service,'start'):
            self.service.warm('alice','a'*32)
            self.assertTrue(self.service.status()['busy'])
            with self.assertRaises(ValueError):self.service.test()
            with self.assertRaises(BlockingIOError):self.service.warm('bob','b'*32)
            self.service.release('bob','a'*32);self.assertTrue(self.service.status()['busy'])
            self.service.release('alice','a'*32);self.assertFalse(self.service.status()['busy'])

    def test_cancellation_cannot_interrupt_another_owner(self):
        job={'owner':'alice','id':'a'*32,'cancel':threading.Event(),'finished':threading.Event()}
        self.service.current={'asr':job}
        with patch.object(self.service,'_write') as write:
            self.service.cancel('bob','a'*32);write.assert_not_called();self.assertFalse(job['cancel'].is_set())
            self.service.cancel('alice','a'*32);write.assert_called_once();self.assertTrue(job['cancel'].is_set())

    def test_asr_and_tts_have_independent_slots_and_revalidate_access(self):
        self.install_fixture()
        for ready in self.service.ready.values():ready.set()
        allowed=[True]
        def send(value,engine):
            job=self.service.current[engine]
            if engine=='asr':job['queue'].put({'id':job['id'],'text':'Bonjour'})
            else:job['queue'].put({'id':job['id'],'rate':24000,'pcm':'AAA='})
            job['queue'].put({'id':job['id'],'done':True});job['finished'].set()
        with patch.object(self.service,'start'),patch.object(self.service,'_write',send):
            speaking=self.service.frames('alice','speak',{'request_id':'a'*32,'text':'Bonjour'},lambda:allowed[0])
            self.assertEqual(next(speaking)['rate'],24000)
            self.assertEqual(self.service.transcribe('alice',{'rate':16000,'pcm':'AAA='})['text'],'Bonjour')
            allowed[0]=False
            with self.assertRaises(PermissionError):next(speaking)
        self.assertFalse(self.service.current)
        self.assertTrue(self.service.slots['asr'].acquire(blocking=False));self.service.slots['asr'].release()

    def test_benchmark_needs_speed_and_intelligible_speech(self):
        self.install_fixture()
        def frames(owner,action,value,valid=lambda:True,testing=False):
            if action=='speak':
                yield {'pcm':base64.b64encode(b'\0\0'*24000).decode()}
                yield {'metrics':{'rtf':.2,'first_audio_ms':400}}
            else:
                yield {'text':'Le projet Orion sera prêt à 15 heures.','metrics':{'rtf':.1,'elapsed_ms':100}}
        with patch.object(self.service,'start'),patch.object(self.service,'frames',frames):
            for ready in self.service.ready.values():ready.set()
            self.service.test();self.service.test_thread.join(3)
        self.assertFalse(self.service.testing);self.assertTrue(self.service.status()['available'],(self.service.status(),(self.service.home/'benchmark.json').read_text()))

    def test_failed_retest_records_advice_and_keeps_max_selectable_after_restart(self):
        self.install_fixture()
        with patch.object(self.service,'start'),patch.object(self.service,'frames',side_effect=ValueError('Test interrompu')):
            for ready in self.service.ready.values():ready.set()
            self.service.test();self.service.test_thread.join(3)
        reopened=AdvancedVoice(self.service.home)
        self.assertTrue(reopened.status()['available'])
        self.assertEqual(reopened.status()['performance'],'inconclusive')
        self.assertIn('non concluant',reopened.status()['message'])
        reopened.close()

    def test_gpu_compatibility_failure_is_explicit_and_does_not_disable_retry(self):
        self.install_fixture(False)
        report={'fingerprint':self.service.fingerprint(),'passed':False,'error_code':'gpu_unavailable',
                'error':'Le moteur Max ne détecte aucune carte AMD ou NVIDIA via Vulkan. Vérifiez le pilote graphique.'}
        self.service.save_report(report)
        status=self.service.status()
        self.assertTrue(status['available']);self.assertEqual(status['performance'],'inconclusive')
        self.assertIn('Vulkan',status['message']);self.assertNotIn('lent',status['message'])

    def test_reader_applies_backpressure_without_truncating_a_long_phrase(self):
        finish=threading.Event()
        class Process:
            def __init__(self):self.stdout=self.lines()
            def lines(self):
                for index in range(100):yield json.dumps({'id':'a'*32,'index':index})+'\n'
                yield json.dumps({'id':'a'*32,'done':True})+'\n'
                finish.wait(3)
        process=Process();job={'owner':'alice','id':'a'*32,'queue':queue.Queue(maxsize=2),
                             'cancel':threading.Event(),'finished':threading.Event()}
        self.service.processes['tts']=process;self.service.current['tts']=job
        thread=threading.Thread(target=self.service._read,args=(process,'tts'));thread.start()
        try:
            time.sleep(.15);self.assertFalse(job['cancel'].is_set())
            frames=[job['queue'].get(timeout=2) for _ in range(101)]
            self.assertEqual([frame['index'] for frame in frames[:-1]],list(range(100)))
            self.assertTrue(frames[-1]['done'])
        finally:
            self.service.processes.clear();self.service.current.clear();finish.set();thread.join(3)


if __name__=='__main__':unittest.main(verbosity=2)
