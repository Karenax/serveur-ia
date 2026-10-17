"""Protect unrelated processes when reclaiming a cold Qwen loader."""
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from startup_memory import reclaim_loader


class StartupMemoryTests(unittest.TestCase):
    def setUp(self):
        self.exe = str(Path(__file__).resolve().parent / 'synthetic-engine.exe')
        self.cfg = {'exe': self.exe, 'args': ['--resident-cpu-experts']}
        self.server = Mock(pid=100)
        self.server.create_time.return_value = 10
        self.engine = Mock(pid=200)
        self.engine.exe.return_value = self.exe
        self.engine.create_time.return_value = 11
        self.engine.ppid.return_value = 100
        self.engine.parents.return_value = []
        self.encoder = Mock(pid=300)
        self.encoder.exe.return_value = self.exe + '.vision'
        self.server.children.return_value = [self.encoder, self.engine]

    def run_reclaim(self, process=None):
        with patch('startup_memory.psutil.Process', side_effect=process or [self.server, self.engine]), \
             patch('startup_memory._empty_working_set') as empty:
            result = reclaim_loader(self.cfg, {'pid': 100, 'created': 10})
            return result, empty.call_args_list

    def test_only_owned_text_engine_not_vision_encoder(self):
        result, calls = self.run_reclaim()
        self.assertEqual(result['status'], 'reclaimed')
        self.assertEqual([call.args for call in calls], [(200,)])

    def test_reused_server_pid_is_not_touched(self):
        self.server.create_time.return_value = 20
        result, calls = self.run_reclaim([self.server])
        self.assertEqual(result['status'], 'skipped')
        self.assertEqual(calls, [])

    def test_windows_python_redirector_keeps_engine_owned(self):
        redirector = Mock(pid=150)
        self.engine.ppid.return_value = 150
        self.engine.parents.return_value = [redirector, self.server]
        result, calls = self.run_reclaim()
        self.assertEqual(result['status'], 'reclaimed')
        self.assertEqual([call.args for call in calls], [(200,)])

    def test_redirected_engine_with_reused_ancestor_is_not_touched(self):
        impostor = Mock(pid=100)
        impostor.create_time.return_value = 99
        self.engine.ppid.return_value = 150
        self.engine.parents.return_value = [impostor]
        result, calls = self.run_reclaim([self.server])
        self.assertEqual(result['status'], 'skipped')
        self.assertEqual(calls, [])

    def test_reused_engine_pid_is_not_touched(self):
        replacement = Mock(pid=200)
        replacement.create_time.return_value = 99
        result, calls = self.run_reclaim([self.server, replacement])
        self.assertEqual(result['status'], 'skipped')
        self.assertEqual(calls, [])

    def test_nonresident_model_is_not_touched(self):
        self.cfg['args'] = []
        result, calls = self.run_reclaim([])
        self.assertEqual(result['status'], 'skipped')
        self.assertEqual(calls, [])

    def test_reparented_engine_is_not_touched(self):
        self.engine.ppid.return_value = 999
        result, calls = self.run_reclaim([self.server])
        self.assertEqual(result['status'], 'skipped')
        self.assertEqual(calls, [])

    def test_failure_is_reported_to_guard_without_exception(self):
        with patch('startup_memory.psutil.Process', side_effect=[self.server, self.engine]), \
             patch('startup_memory._empty_working_set', side_effect=OSError('Synthetic failure')):
            result = reclaim_loader(self.cfg, {'pid': 100, 'created': 10})
        self.assertEqual(result['status'], 'failed')


if __name__ == '__main__':
    unittest.main()
