import unittest
from unittest.mock import call, patch

from linux_system_audio import _unload_owned


class LinuxSystemAudioOwnershipTests(unittest.TestCase):
    def test_unloads_only_the_matching_remap_source(self):
        with patch('linux_system_audio._pactl', side_effect=[
                '31\tmodule-remap-source\tmaster=output.monitor source_name=kiara_output_token', '']) as pactl:
            _unload_owned('31', 'kiara_output_token')
        self.assertEqual(pactl.call_args_list, [call('list', 'short', 'modules'), call('unload-module', '31')])

    def test_never_unloads_a_reused_module_id(self):
        with patch('linux_system_audio._pactl', return_value='31\tmodule-remap-source\tsource_name=other') as pactl:
            with self.assertRaises(RuntimeError):
                _unload_owned('31', 'kiara_output_token')
        pactl.assert_called_once_with('list', 'short', 'modules')

    def test_missing_module_is_already_closed(self):
        with patch('linux_system_audio._pactl', return_value='32\tmodule-null-sink\tsink_name=other') as pactl:
            _unload_owned('31', 'kiara_output_token')
        pactl.assert_called_once_with('list', 'short', 'modules')


if __name__ == '__main__':
    unittest.main()
