"""Port selection must never silently leave a pinned browser origin."""
import unittest
from unittest.mock import Mock, patch
import client


class PinnedRelayPortTests(unittest.TestCase):
    def setUp(self):
        self.remote = Mock()
        self.remote_ctor = patch.object(client, 'Remote', return_value=self.remote)
        self.settings = patch.object(client, 'read_settings_for_update', return_value={})
        self.key = patch.object(client, 'local_key', return_value='key-fictive')
        self.serve = patch.object(client, 'serve_local')
        for context in (self.remote_ctor, self.settings, self.key, self.serve):
            context.start(); self.addCleanup(context.stop)

    def test_pinned_port_is_the_only_port_opened(self):
        server = object()
        client.serve_local.return_value = server
        remote, found = client.open_local_relay({}, required_port=17844)
        self.assertIs(remote, self.remote)
        self.assertIs(found, server)
        client.serve_local.assert_called_once_with(self.remote, 'key-fictive', 17844, managed=False)

    def test_occupied_pinned_port_fails_without_trying_another_origin(self):
        client.serve_local.side_effect = OSError('busy')
        with self.assertRaisesRegex(ValueError, '17844.*occupé'):
            client.open_local_relay({}, required_port=17844)
        client.serve_local.assert_called_once_with(self.remote, 'key-fictive', 17844, managed=False)
        self.remote.close.assert_called_once()

    def test_legacy_call_still_tries_the_next_available_port(self):
        server = object()
        client.serve_local.side_effect = [OSError('busy'), server]
        self.assertIs(client.open_local_relay({})[1], server)
        self.assertEqual([call.args[2] for call in client.serve_local.call_args_list], [17841, 17842])

    def test_invalid_and_thunderbird_incompatible_ports_fail_before_binding(self):
        for value in (True, 17840, 17851, '17841'):
            with self.assertRaises(ValueError): client.open_local_relay({}, required_port=value)
        client.serve_local.assert_not_called()
        client.read_settings_for_update.return_value = {'thunderbird_token':'paired'}
        with self.assertRaises(ValueError): client.open_local_relay({}, required_port=17842)
        client.serve_local.assert_not_called()

    def test_invalid_endpoint_does_not_discard_thunderbird_pairing(self):
        client.read_settings_for_update.return_value = {'endpoint':'invalid endpoint','thunderbird_token':'paired'}
        with self.assertRaises(client.LocalOriginIncompatible):client.open_local_relay({},required_port=17842)
        client.Remote.assert_called_once_with({},endpoint=None,connection_required=True)
        client.serve_local.assert_not_called()

if __name__ == '__main__': unittest.main()
