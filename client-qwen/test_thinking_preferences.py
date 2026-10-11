"""Actual encrypted client preferences for exact, model-specific reasoning."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import client


EFFORTS = ('none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max', 'ultra', 'on')


class ThinkingPreferences(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / 'preferences.dpapi'
        self.profile = {'url': 'https://fixture.invalid', 'token': 'isolated-preferences'}
        self.path_patch = patch('client.settings_path', return_value=self.path)
        self.path_patch.start()
        self.addCleanup(self.path_patch.stop)

    def save(self, value):
        return client.save_preferences(self.profile, value)

    def preferences(self):
        return client.client_settings(self.profile)['preferences']

    def test_all_canonical_levels_survive_real_encrypted_settings(self):
        for effort in EFFORTS:
            with self.subTest(effort=effort):
                self.assertEqual(self.save({'thinking_effort': effort, 'thinking': effort != 'none',
                    'thinking_by_model': {'fred-qwen': effort, 'legacy model': 'max'}}), {'saved': True})
                actual = self.preferences()
                self.assertEqual(actual['thinking_effort'], effort)
                self.assertEqual(actual['thinking_by_model'], {'fred-qwen': effort, 'legacy model': 'max'})
                self.assertNotIn(b'thinking_by_model', self.path.read_bytes())
                self.assertNotIn(b'legacy model', self.path.read_bytes())

    def test_automatic_mode_omission_keeps_old_global_preferences(self):
        self.save({'thinking_effort': 'max', 'thinking': True, 'theme': 'light',
            'thinking_by_model': {'fred-cloud': 'max', 'fred-toggle': 'on'}})
        self.save({'theme': 'dark', 'thinking_by_model': {'fred-cloud': 'max', 'fred-toggle': 'on'}})
        actual = self.preferences()
        self.assertEqual(actual['thinking_effort'], 'max')
        self.assertIs(actual['thinking'], True)
        self.assertEqual(actual['theme'], 'dark')
        self.assertEqual(actual['thinking_by_model']['fred-toggle'], 'on')

    def test_model_map_boundary_accepts_512_and_rejects_invalid_without_writes(self):
        self.save({'thinking_by_model': {'model-' + str(i): 'max' for i in range(512)}})
        before = self.path.read_bytes()
        invalid = [None, [], True, {'model-' + str(i): 'max' for i in range(513)},
                   {'': 'max'}, {' ': 'max'}, {1: 'max'}, {'x' * 513: 'max'},
                   {'control\nmodel': 'high'}, {'model': True}, {'model': []}, {'model': {}},
                   {'model': 'off'}, {'model': 'maximum'}, {'model': 'unknown'}]
        for value in invalid:
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaises(ValueError): self.save({'thinking_by_model': value})
                self.assertEqual(self.path.read_bytes(), before)

    def test_scalar_aliases_and_invalid_types_are_not_silently_normalized(self):
        self.save({'thinking_effort': 'high'})
        before = self.path.read_bytes()
        for value in (None, True, [], {}, 'off', 'maximum', 'MAX', 'unknown'):
            with self.subTest(value=value):
                with self.assertRaises(ValueError): self.save({'thinking_effort': value})
                self.assertEqual(self.path.read_bytes(), before)


if __name__ == '__main__': unittest.main()
