"""Linux starts through Tauri and locks its desktop profile."""
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

import client
import linux_support


def profile(token='fiction'):
    return {'url':'https://example.test', 'token':token}


class LinuxEntryTests(unittest.TestCase):
    def test_legacy_entry_exits_before_reading_profile_or_opening_relay(self):
        with patch.object(client.sys, 'argv', ['client']), \
             patch.object(client.sys, 'platform', 'linux'), \
             patch.object(client, 'read_profile') as read, \
             patch.object(client, 'open_local_relay') as relay:
            with self.assertRaisesRegex(SystemExit, 'client Tauri'):
                client.main()
        read.assert_not_called()
        relay.assert_not_called()


@unittest.skipUnless(os.name == 'posix', 'Verrou Linux : vérifié dans la distribution de recette.')
class LinuxGuardTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        env = patch.dict(os.environ, {'XDG_DATA_HOME':str(self.root)})
        env.start();self.addCleanup(env.stop)

    def test_same_profile_is_exclusive_other_profile_and_reopen_are_allowed(self):
        first = linux_support.lock_desktop_profile(profile())
        self.addCleanup(first.close)
        lock_path = linux_support.data_home()/('tauri-webview-'+linux_support.settings_path(profile()).stem+'.lock')
        self.assertEqual(lock_path.name, 'tauri-webview-'+linux_support.settings_path(profile()).stem+'.lock')
        self.assertEqual(stat.S_IMODE(lock_path.stat().st_mode), 0o600)
        with self.assertRaises(linux_support.ProfileAlreadyOpen):
            linux_support.lock_desktop_profile(profile())
        other = linux_support.lock_desktop_profile(profile('different'))
        other.close()
        first.close()
        with linux_support.lock_desktop_profile(profile()):pass

    def test_symlink_lock_is_not_followed(self):
        target=self.root/'sentinel';target.write_bytes(b'preserve')
        directory=linux_support.data_home()
        path=directory/('tauri-webview-'+linux_support.settings_path(profile()).stem+'.lock')
        path.symlink_to(target)
        with self.assertRaises(linux_support.ProfileLockError):linux_support.lock_desktop_profile(profile())
        self.assertEqual(target.read_bytes(),b'preserve')
        self.assertTrue(path.is_symlink())

    def test_special_file_cannot_be_used_as_a_profile_lock(self):
        path=linux_support.data_home()/('tauri-webview-'+linux_support.settings_path(profile()).stem+'.lock')
        os.mkfifo(path)
        with self.assertRaises(linux_support.ProfileLockError):linux_support.lock_desktop_profile(profile())
        self.assertTrue(stat.S_ISFIFO(path.stat().st_mode))

if __name__ == '__main__': unittest.main()
