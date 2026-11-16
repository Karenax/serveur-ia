"""Agent child failures revoke its bridge and internal inference credential."""

import threading
import unittest
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from agent_service import AgentService, service_configuration, web_configuration


class AgentServiceTests(unittest.TestCase):
    def test_project_process_never_inherits_testing_bypass(self):
        with TemporaryDirectory() as folder, patch.dict(os.environ, {'AGENT_TESTING': '1'}):
            root = Path(folder)
            service = AgentService(None, root / 'data', root / 'python.exe')
            (root / 'data/logs').mkdir(parents=True)
            with patch.object(service, 'preflight', return_value={}), patch('agent_service.private_directory'), patch(
                'agent_service.subprocess.Popen', side_effect=OSError('fixture intercepts process creation')
            ) as start:
                with self.assertRaisesRegex(OSError, 'fixture intercepts'):
                    service._start()
            self.assertNotIn('AGENT_TESTING', start.call_args.kwargs['env'])

    def test_selecting_a_thunderbird_device_preserves_its_project_grant(self):
        with TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            home = Path(folder)
            settings = {'data': str(home / 'data'), 'python': str(home / 'python.exe')}
            (home / 'agent-service.json').write_text(json.dumps(settings), encoding='utf-8')
            store = SimpleNamespace(home=home, lock=threading.RLock(), agent_bridge=SimpleNamespace())
            service = AgentService(store, **settings)
            device = '0123456789abcdef'
            grant = {'id': device, 'role': 'owner', 'project_ids': ['one-project'], 'person_id': None}
            with patch.object(service.access, 'operator_for', return_value=grant):
                service.set_thunderbird_device(device)
            self.assertEqual(service_configuration(home)['thunderbird_device'], device)
            self.assertEqual(store.agent_bridge.thunderbird_device, device)
            self.assertEqual(grant['project_ids'], ['one-project'])
            service.set_thunderbird_device(None)
            self.assertIsNone(store.agent_bridge.thunderbird_device)
            self.assertIsNone(service_configuration(home)['thunderbird_device'])

    def test_configuration_survives_process_restart_and_accepts_environment_override(self):
        with TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            home = Path(folder)
            self.assertIsNone(service_configuration(home))
            settings = {'data': str(home / 'data'), 'python': str(home / 'python.exe'),
                        'speech_python': str(home / 'speech.exe'), 'speech_models': str(home / 'speech-models'),
                        'start_workers': False, 'thunderbird_device': '0123456789abcdef'}
            path = home / 'agent-service.json'
            path.write_text(json.dumps(settings), encoding='utf-8')
            self.assertEqual(service_configuration(home), settings)
            self.assertEqual(AgentService(None, **service_configuration(home)).thunderbird_device, settings['thunderbird_device'])
            os.environ['KIARA_AGENT_THUNDERBIRD_DEVICE'] = 'fedcba9876543210'
            self.assertEqual(AgentService(None, **service_configuration(home)).thunderbird_device, 'fedcba9876543210')
            with self.assertRaisesRegex(ValueError, 'poste Thunderbird'):
                AgentService(None, '.', '.', thunderbird_device='Poste de bureau')
            os.environ['KIARA_AGENT_START_WORKERS'] = '1'
            self.assertTrue(service_configuration(home)['start_workers'])
            os.environ['KIARA_AGENT_PYTHON'] = str(home / 'override.exe')
            self.assertEqual(service_configuration(home)['python'], os.environ['KIARA_AGENT_PYTHON'])
            path.write_text('null', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'agent-service.json'):
                service_configuration(home)

    def test_project_configuration_takes_precedence_for_reads_and_writes(self):
        with TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            home = Path(folder)
            settings = {'data': str(home / 'data'), 'python': str(home / 'python.exe')}
            legacy = home / 'agent-service.json'
            original = json.dumps({**settings, 'web_origin': 'https://legacy.example.test'})
            legacy.write_text(original, encoding='utf-8')
            current = home / 'project-service.json'
            current.write_text(json.dumps({**settings, 'web_origin': 'https://kiara.example.test'}), encoding='utf-8')
            self.assertEqual(web_configuration(home), ('https://kiara.example.test', 8767))
            service = AgentService(SimpleNamespace(home=home, lock=threading.RLock(), agent_bridge=None), **settings)
            device = '0123456789abcdef'
            with patch.object(service.access, 'operator_for', return_value={'role': 'editor'}):
                service.set_thunderbird_device(device)
            self.assertEqual(service_configuration(home)['thunderbird_device'], device)
            self.assertEqual(legacy.read_text(encoding='utf-8'), original)
            current.write_text('null', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'project-service.json'):
                service_configuration(home)

    def test_project_environment_overrides_also_support_a_legacy_rollback(self):
        with TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            home = Path(folder)
            config = {
                'data': str(home / 'data'), 'python': str(home / 'python.exe'),
                'web_origin': 'https://kiara.example.test', 'start_workers': True,
            }
            original = json.dumps(config)
            (home / 'agent-service.json').write_text(original, encoding='utf-8')
            old = {'PYTHON': str(home / 'old-override.exe'), 'START_WORKERS': '0', 'WEB_PORT': '8878'}
            os.environ.update({f'KIARA_AGENT_{key}': value for key, value in old.items()})
            expected_service = service_configuration(home)
            expected_web = web_configuration(home)

            candidate = home / 'project-service.json'
            candidate.write_text(original, encoding='utf-8')
            os.environ.update({f'KIARA_PROJECT_{key}': value for key, value in old.items()})
            self.assertEqual(service_configuration(home), expected_service)
            self.assertEqual(web_configuration(home), expected_web)
            os.environ['KIARA_PROJECT_START_WORKERS'] = '1'
            os.environ['KIARA_PROJECT_WEB_ORIGIN'] = ''
            self.assertTrue(service_configuration(home)['start_workers'])
            self.assertIsNone(web_configuration(home))

            candidate.unlink()
            for key in (*old, 'WEB_ORIGIN'):
                del os.environ[f'KIARA_PROJECT_{key}']
            self.assertEqual(service_configuration(home), expected_service)
            self.assertEqual(web_configuration(home), expected_web)

    def test_web_listener_settings_persist_and_keep_environment_overrides(self):
        with TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            home = Path(folder)
            self.assertIsNone(web_configuration(home))
            path = home / 'agent-service.json'
            path.write_text(json.dumps({'data': str(home), 'python': str(home / 'python.exe'),
                                        'web_origin': 'https://agent.example.test', 'web_port': 8877}), encoding='utf-8')
            self.assertEqual(web_configuration(home), ('https://agent.example.test', 8877))
            self.assertEqual(service_configuration(home)['data'], str(home))
            os.environ['KIARA_AGENT_WEB_PORT'] = '8878'
            self.assertEqual(web_configuration(home), ('https://agent.example.test', 8878))
            os.environ['KIARA_AGENT_WEB_ORIGIN'] = ''
            self.assertIsNone(web_configuration(home))
            os.environ['KIARA_AGENT_WEB_ORIGIN'] = 'https://agent.example.test/app'
            with self.assertRaisesRegex(ValueError, 'Origine HTTPS'):
                web_configuration(home)

    def test_document_roots_are_explicit_and_can_be_disabled_by_environment(self):
        with TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            home = Path(folder)
            roots = [str(home / 'read')]
            write_roots = [str(home / 'write')]
            mappings = {'P:': str(home / 'share')}
            (home / 'agent-service.json').write_text(json.dumps({
                'data': str(home), 'python': str(home / 'python.exe'),
                'document_roots': roots, 'document_write_roots': write_roots,
                'document_drive_mappings': mappings,
                'document_project_root': str(home / 'clients'),
            }), encoding='utf-8')
            service = AgentService(None, **service_configuration(home))
            self.assertEqual({key: json.loads(value) for key, value in service.document_settings.items()}, {
                'AGENT_DOCUMENT_ROOTS': roots,
                'AGENT_DOCUMENT_WRITE_ROOTS': write_roots,
                'AGENT_DOCUMENT_DRIVE_MAPPINGS': mappings,
                'AGENT_DOCUMENT_PROJECT_ROOT': str(home / 'clients'),
            })
            os.environ['AGENT_DOCUMENT_WRITE_ROOTS'] = '[]'
            self.assertEqual(service_configuration(home)['document_settings']['AGENT_DOCUMENT_WRITE_ROOTS'], '[]')
            os.environ['AGENT_DOCUMENT_ROOTS'] = '{}'
            with self.assertRaisesRegex(ValueError, 'document_roots'):
                service_configuration(home)

    def test_meeting_activation_preserves_existing_options(self):
        store = SimpleNamespace(agent_bridge=object())
        service = AgentService(store, '.', '.')
        current = {'enabled': False, 'live_transcription_enabled': False, 'proactive_enabled': True,
                   'auto_enhancement_enabled': False, 'mode': 'local', 'onboarding_complete': True,
                   'live_speech_device': 'cpu'}
        with patch.object(service, 'running', return_value=True), patch.object(
                service, '_admin_request', side_effect=[current, {'enabled': True}]) as request:
            service.enable_meetings()
        args = request.call_args.args
        self.assertEqual(args[1]['id'], 'kiara-service')
        self.assertEqual(args[3], 'PUT')
        self.assertEqual(args[4], {key: value for key, value in {**current, 'enabled': True}.items()
                                   if key != 'live_speech_device'})

    def test_exit_cleans_only_the_process_that_was_watched(self):
        store = SimpleNamespace(lock=threading.RLock(), agent_bridge=object(), agent_inference_token='token')
        service = AgentService(store, '.', '.')
        process = SimpleNamespace(wait=lambda: 1)
        service.process = process
        service.inference_token = 'token'
        service._watch(process)
        self.assertIsNone(service.process)
        self.assertIsNone(store.agent_bridge)
        self.assertIsNone(store.agent_inference_token)

        newer = SimpleNamespace(wait=lambda: 1)
        bridge = object()
        service.process = newer
        service.inference_token = 'new-token'
        store.agent_bridge = bridge
        store.agent_inference_token = 'new-token'
        service._watch(process)
        self.assertIs(service.process, newer)
        self.assertIs(store.agent_bridge, bridge)
        self.assertEqual(store.agent_inference_token, 'new-token')

    def test_preflight_detects_inaccessible_or_overlapping_client_storage(self):
        with TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            home = Path(directory).resolve()
            for name in ('brain', 'erp', 'storage'):
                (home / name).mkdir()
            for name in ('brain/project_brain.db', 'erp/minipilot.db', 'python.exe'):
                (home / name).touch()
            root = home / 'clients'
            settings = {'AGENT_DOCUMENT_PROJECT_ROOT': json.dumps(str(root))}
            service = AgentService(None, home, home / 'python.exe', document_settings=settings)
            with self.assertRaisesRegex(ValueError, 'dossier client'):
                service.preflight()
            root.mkdir()
            self.assertEqual(service.preflight(), {})
            settings['AGENT_DOCUMENT_ROOTS'] = json.dumps([str(home)])
            with self.assertRaisesRegex(ValueError, 'dossiers distincts'):
                service.preflight()

    def test_worker_groups_can_be_selected_and_reject_unknown_names(self):
        with TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            home = Path(folder)
            path = home / 'agent-service.json'
            config = {'data': str(home), 'python': str(home / 'python.exe'), 'worker_groups': ['documents']}
            path.write_text(json.dumps(config), encoding='utf-8')
            self.assertEqual(AgentService(None, **service_configuration(home)).worker_groups, ('documents',))
            for invalid in ('documents', ['docs'], ['mail', 'mail'], None):
                config['worker_groups'] = invalid
                path.write_text(json.dumps(config), encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'groupes de traitements'):
                    service_configuration(home)


if __name__ == '__main__':
    unittest.main()
