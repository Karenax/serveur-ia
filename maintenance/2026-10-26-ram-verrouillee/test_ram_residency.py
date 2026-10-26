import tempfile
from pathlib import Path
import unittest
import os
from unittest.mock import patch

from ram_residency import verify_locked_ram


class ResidencyTests(unittest.TestCase):
    args = ['--resident-experts', '--no-prefill-borrow', '--ple-io', 'ram']
    ple = 'strata generate: PLE table locked in RAM (--ple-io ram) in 20.0 s\n'
    pinned = ('FileExpertSource: mapped pinned cache complement ready: resident 51.57 GiB, '
              'pinned 51.57 GiB in 200 s; page-locked and mapped\n'
              'strata generate: resident RAM mode: 51.57 GiB of experts (page-locked)\n')

    def verify(self, text, offset=0, args=None):
        with tempfile.TemporaryDirectory() as temporary:
            log = Path(temporary) / 'engine.log'
            log.write_text(text, encoding='utf-8')
            return verify_locked_ram(log, offset, self.args if args is None else args)

    def test_complete_gpu_pin(self):
        self.assertEqual(self.verify(self.ple + self.pinned)['experts_gib'], 51.57)

    def test_windows_lock_fallback(self):
        text = self.pinned.replace('pinned 51.57', 'pinned 0.00').replace(
            'page-locked and mapped', 'locked 52808 MiB via working-set minimum + VirtualLock')
        text = text.replace('(page-locked)', '(locked)')
        self.assertGreater(self.verify(self.ple + text)['windows_locked_gib'], 51)

    def test_partial_pin_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'incomplet'):
            self.verify(self.ple + self.pinned.replace('pinned 51.57', 'pinned 20.00'))

    def test_partial_windows_lock_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'incomplet'):
            self.verify(self.ple + self.pinned.replace('page-locked and mapped', 'VirtualLock stopped at 1024 of 52808 MiB'))

    def test_unlocked_ple_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'PLE'):
            self.verify(self.ple.replace('locked in RAM', 'loaded (not locked)') + self.pinned)

    def test_ple_can_stay_on_c_to_preserve_memory_budget(self):
        args = self.args[:-1] + ['direct', '--ple-gguf', 'C:/synthetic.gguf']
        with patch('ram_residency.Path.resolve', return_value=Path('C:/synthetic.gguf')):
            result = self.verify(self.pinned, args=args)
        self.assertFalse(result['ple_locked'])

    def test_direct_ple_resolving_to_d_is_rejected(self):
        args = self.args[:-1] + ['direct', '--ple-gguf', 'C:/synthetic.gguf']
        with patch('ram_residency.Path.resolve', return_value=Path('D:/synthetic.gguf')):
            with self.assertRaisesRegex(ValueError, 'SSD C:'):
                self.verify(self.pinned, args=args)

    def test_disk_fallback_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'disque'):
            self.verify(self.ple + self.pinned + 'WARNING: the whole resident RAM mode does not fit')

    def test_prior_startup_cannot_mask_current_failure(self):
        good = self.ple + self.pinned
        with self.assertRaisesRegex(ValueError, 'PLE'):
            self.verify(good + 'new startup failed', len(good.encode()))

    def test_unsafe_configuration_is_rejected(self):
        for args in [[], self.args[:-1] + ['direct'], ['--resident-experts', '--ple-io', 'ram']]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.verify(self.ple + self.pinned, args=args)

    @unittest.skipUnless(os.name == 'nt', 'Windows physical page locking')
    def test_readonly_tensor_pages_are_physically_locked_and_released(self):
        import ctypes as c
        from ctypes import wintypes as w
        from ram_residency import LockedTensor
        class Page(c.Structure):
            _fields_ = [('address', c.c_void_p), ('attributes', c.c_size_t)]
        api = c.WinDLL('psapi', use_last_error=True)
        api.QueryWorkingSetEx.argtypes = [w.HANDLE, c.c_void_p, w.DWORD]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'synthetic.bin'
            path.write_bytes(b'x' * 65536)
            locked = LockedTensor(path, 64, 32768)
            try:
                pages = (Page * (locked.length // 4096))()
                for index, page in enumerate(pages):
                    page.address = locked.base + index * 4096
                self.assertTrue(api.QueryWorkingSetEx(locked.kernel.GetCurrentProcess(), c.byref(pages), c.sizeof(pages)))
                for page in pages:
                    self.assertTrue(page.attributes & 1)
                    self.assertTrue(page.attributes & (1 << 22))
            finally:
                locked.close()
            self.assertFalse(locked.locked)
            self.assertEqual(path.read_bytes(), b'x' * 65536)


if __name__ == '__main__':
    unittest.main()
