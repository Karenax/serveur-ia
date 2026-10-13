"""Focused checks of launch configuration, local HTTP boundaries and process ownership."""
import json
from pathlib import Path
import re
import socket
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import urllib.error
import urllib.request
import psutil
from core import ROOT, HOME, BASE_PATH, PYTHON, HIDDEN, read_json, write_json, defaults_from_config, build_config, validate, matching_servers, process_identity, stop_processes
from app import Controller, serve
from runtime import supervise

def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]

class LaunchTests(unittest.TestCase):
    def setUp(self):
        self.base = read_json(BASE_PATH)
        self.settings = defaults_from_config(self.base)

    def test_default_profile_and_unchanged_native_options(self):
        s = validate(self.settings, True)
        self.assertEqual((s['context'], s['workers'], s['history_slots']), (262144, 15, 8))
        self.assertEqual(s['model_name'], 'qwen3.8-flash-next-iq4-xs')
        self.assertTrue(s['mtp_enabled'])
        self.assertTrue(s['history_enabled'])
        cfg = build_config(self.base, s)
        for flag in ['--resident-cpu-experts', '--mmap-experts', '--no-prefill-borrow']:
            self.assertIn(flag, cfg['args'])
        self.assertEqual(cfg['env'], self.base['env'])
        self.assertEqual(cfg['args'][cfg['args'].index('--pack') + 1], self.settings['pack'])
        self.assertNotIn('C:/Strata-cache', json.dumps(cfg))

    def test_network_requires_key_and_rejects_bad_origins(self):
        s = {**self.settings, 'host': '0.0.0.0'}
        with self.assertRaises(ValueError):
            validate(s)
        s['api_key'] = 'TEST-ONLY-' + 'x' * 32
        cfg = build_config(self.base, s)
        self.assertEqual(cfg['host'], '0.0.0.0')
        with self.assertRaises(ValueError):
            validate({**s, 'trusted_origins': 'https://example.org/path'})
        with self.assertRaises(ValueError):
            validate({**s, 'context': 262145})

    def test_mtp_and_history_can_be_disabled_without_changing_sources(self):
        cfg = build_config(self.base, {**self.settings, 'mtp_enabled': False, 'history_enabled': False})
        self.assertNotIn('--mtp', cfg['args'])
        self.assertEqual(cfg['args'][cfg['args'].index('--spec') + 1], '1')
        self.assertEqual(cfg['args'][cfg['args'].index('--prompt-cache') + 1], '0')

    def test_second_start_is_blocked_before_worker_writes_state(self):
        with tempfile.TemporaryDirectory(dir=HOME) as temporary:
            controller = Controller(temporary, include_legacy=False)
            write_json(controller.pointer, {'directory': temporary, 'worker': process_identity(psutil.Process())})
            with self.assertRaisesRegex(ValueError, 'déjà lancé'):
                controller.start(self.settings)
            self.assertFalse((Path(temporary) / 'sessions').exists())

    def test_ram_guard_stops_only_new_loading_process(self):
        originals = [process_identity(p) for p in matching_servers([ROOT / 'strata-q4-p100-hybride.json'])]
        with tempfile.TemporaryDirectory(dir=HOME) as temporary:
            folder = Path(temporary)
            cfg = build_config(self.base, {**self.settings, 'port': free_port()}, folder / 'engine.log')
            marker = folder / 'test-marker.flag'
            cfg['env']['STRATA_P100_DIAGNOSTIC_SYNC_FILE'] = str(marker)
            config_path = folder / 'strata.json'
            write_json(config_path, cfg)
            # Simulate low free RAM; do not allocate memory or load any model.
            with patch('runtime.health', return_value={}), patch('runtime.psutil.virtual_memory', return_value=SimpleNamespace(available=0)):
                state = supervise(config_path, folder, mock=True)
            self.assertEqual(state['status'], 'erreur')
            self.assertIn('Protection RAM', state['error'])
            self.assertFalse(marker.exists())
            self.assertFalse(matching_servers([config_path]))
            for original in originals:
                self.assertAlmostEqual(psutil.Process(original['pid']).create_time(), original['created'], places=2)

    def test_local_control_rejects_foreign_requests_and_persists_settings(self):
        with tempfile.TemporaryDirectory(dir=HOME) as temporary:
            controller = Controller(temporary, include_legacy=False)
            port = free_port()
            server = serve(port, controller)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            base = f'http://127.0.0.1:{port}'
            try:
                html = urllib.request.urlopen(base).read().decode()
                token = re.search('name="launcher-token" content="([^"]+)"', html)[1]
                def post(origin, key=token):
                    return urllib.request.urlopen(urllib.request.Request(base + '/api/save',
                        data=json.dumps(self.settings).encode(), headers={'Content-Type': 'application/json', 'Origin': origin, 'X-Launcher-Token': key}))
                with self.assertRaises(urllib.error.HTTPError) as error:
                    post('https://foreign.example')
                self.assertEqual(error.exception.code, 403)
                with self.assertRaises(urllib.error.HTTPError):
                    post(base, 'wrong-token')
                with post(base) as response:
                    self.assertEqual(json.load(response)['history_slots'], self.settings['history_slots'])
                self.assertEqual(controller.settings()['context'], 262144)
                with self.assertRaises(urllib.error.HTTPError):
                    urllib.request.urlopen(urllib.request.Request(base, headers={'Host': 'foreign.example'}))
            finally:
                server.shutdown()
                server.server_close()

    def test_mock_lifecycle_key_auth_and_stop_does_not_touch_existing_qwen(self):
        originals = [process_identity(p) for p in matching_servers([ROOT / 'strata-q4-p100-hybride.json'])]
        with tempfile.TemporaryDirectory(dir=HOME) as temporary:
            folder = Path(temporary)
            controller = Controller(folder, include_legacy=False)
            port = free_port()
            cfg = build_config(self.base, {**self.settings, 'port': port, 'api_key': 'TEST-ONLY-' + 'a' * 32}, folder / 'engine.log')
            cfg['env']['STRATA_P100_DIAGNOSTIC_SYNC_FILE'] = str(folder / 'test-marker.flag')
            config_path = folder / 'strata.json'
            write_json(config_path, cfg)
            write_json(controller.pointer, {'directory': str(folder)})
            process = subprocess.Popen([str(PYTHON), '-u', str(HOME / 'runtime.py'), '--config', str(config_path),
                        '--run-dir', str(folder), '--mock'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        creationflags=HIDDEN)
            try:
                deadline = time.monotonic() + 45
                state = {}
                while time.monotonic() < deadline:
                    state = read_json(folder / 'state.json', {})
                    if state.get('status') in ('pret', 'erreur'):
                        break
                    time.sleep(.25)
                self.assertEqual(state.get('status'), 'pret', state.get('error'))
                self.assertFalse((folder / 'test-marker.flag').exists())
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(f'http://127.0.0.1:{port}/v1/models')
                self.assertEqual(error.exception.code, 401)
                request = urllib.request.Request(f'http://127.0.0.1:{port}/v1/models', headers={'Authorization': 'Bearer ' + cfg['api_key']})
                self.assertEqual(urllib.request.urlopen(request).status, 200)
                controller.stop()
                process.wait(timeout=15)
                self.assertFalse(controller.processes())
                for original in originals:
                    self.assertAlmostEqual(psutil.Process(original['pid']).create_time(), original['created'], places=2)
            finally:
                if process.poll() is None:
                    stop_processes([psutil.Process(process.pid)])

    def test_another_workspace_profile_is_recognized_without_changing_defaults(self):
        with tempfile.TemporaryDirectory(dir=HOME) as temporary:
            folder=Path(temporary)
            controller=Controller(folder,include_legacy=True)
            config=folder/'strata-other.json'
            write_json(config,{**self.base,'model_name':'another-live-model','args':['--max-context','4096','--pool-workers','7']})
            unrelated=folder/'strata-unrelated.json'
            write_json(unrelated,{**self.base,'port':9999})
            process=SimpleNamespace(cmdline=lambda:['python.exe','-m','serve.server','--config',str(config)],children=lambda recursive=False:[])
            captured=[]
            def matching(paths):
                captured.extend(paths);return [process]
            with patch('app.ROOT',folder),patch('app.matching_servers',side_effect=matching),patch('app.health',return_value={'loaded':True,'model':'another-live-model'}),patch.object(controller,'gpu_stats',return_value=[]):
                self.assertEqual(controller.remote_backend()[:2],(8080,'another-live-model'))
                state=controller.state()
            self.assertIn(config,captured);self.assertNotIn(unrelated,captured)
            self.assertEqual(state['status'],'pret');self.assertTrue(state['running'])
            self.assertEqual(state['active']['context'],4096)
            self.assertEqual(controller.defaults()['model_name'],self.settings['model_name'])
            self.assertEqual(controller.defaults()['context'],262144)

if __name__ == '__main__':
    unittest.main(verbosity=2)
