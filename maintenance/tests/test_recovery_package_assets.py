"""The two Tauri packages must carry the same recovery resources."""
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]


class RecoveryPackageAssetsTests(unittest.TestCase):
    def test_windows_relay_contains_all_linux_recovery_resources(self):
        from maintenance.package_linux_client import ASSETS

        hooks=ModuleType('PyInstaller.utils.hooks')
        hooks.collect_all=lambda _name:([],[],[])
        modules={'PyInstaller':ModuleType('PyInstaller'),'PyInstaller.utils':ModuleType('PyInstaller.utils'),
                 'PyInstaller.utils.hooks':hooks}
        def analysis(_scripts,**options):
            return SimpleNamespace(datas=options['datas'],binaries=options['binaries'],pure=[],scripts=[])
        spec=ROOT/'client-qwen'/'kiara-relay.spec'
        scope={'Analysis':analysis,'PYZ':lambda *_args:None,'EXE':lambda *_args,**_kwargs:None,
               'SPECPATH':str(spec.parent)}
        with patch.dict(sys.modules,modules):
            exec(compile(spec.read_text(encoding='utf-8'),str(spec),'exec'),scope)
        included={Path(source).name for source,destination in scope['a'].datas if destination=='.'}
        expected={name for name in ASSETS if name.startswith('portal_')}
        self.assertFalse(expected-included,f'Ressources absentes du relais Windows : {sorted(expected-included)}')
        self.assertIn('recovery_init.js',included)
        for name in expected:
            self.assertTrue((ROOT/'client-qwen'/name).is_file(),name)


if __name__=='__main__':unittest.main()
