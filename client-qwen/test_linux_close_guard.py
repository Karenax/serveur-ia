"""Linux close barrier stays compatible with the restrictive application CSP."""
import json
import re
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

import client


class FakeWindow:
    def __init__(self, result):
        self.result = result
        self.scripts = []
        self.identifier = None

    def run_js(self, source):
        self.scripts.append(source)
        if source.startswith('(() =>'):
            self.identifier = json.loads(re.search(r'const id = ("[^"]+");', source).group(1))
            return None
        return json.dumps({'id': self.identifier, 'pending': False, 'result': self.result})


class LinuxCloseGuardTests(unittest.TestCase):
    def test_waits_for_confirmed_save_without_eval(self):
        window = FakeWindow({'saved': True})
        self.assertEqual(client._prepare_close_linux(window), {'saved': True})
        self.assertIn('kiaraPrepareClose', window.scripts[0])
        self.assertNotIn('eval(', '\n'.join(window.scripts))

    def test_failure_is_returned_instead_of_treated_as_saved(self):
        window = FakeWindow({'saved': False, 'message': 'Disque plein'})
        self.assertEqual(client._prepare_close_linux(window), {'saved': False, 'message': 'Disque plein'})

    def test_timeout_never_claims_saved(self):
        window = FakeWindow({'saved': True})
        self.assertFalse(client._prepare_close_linux(window, timeout=0)['saved'])

    def test_failed_save_never_closes_when_user_declines(self):
        class Event:
            def __iadd__(self, callback):
                self.callback = callback
                return self
        class ImmediateThread:
            def __init__(self, *, target, daemon): self.target = target
            def start(self): self.target()
        window = FakeWindow({'saved': False, 'message': 'Disque plein'})
        window.events = SimpleNamespace(closing=Event())
        window.destroy = Mock()
        window.create_confirmation_dialog = Mock(return_value=False)
        with patch.object(client.sys, 'platform', 'linux'), patch.object(client.threading, 'Thread', ImmediateThread):
            state = client.install_close_guard(window)
            self.assertFalse(window.events.closing.callback())
        window.destroy.assert_not_called()
        window.create_confirmation_dialog.assert_called_once()
        self.assertFalse(state['ready'])
        self.assertFalse(state['pending'])


if __name__ == '__main__':
    unittest.main()
