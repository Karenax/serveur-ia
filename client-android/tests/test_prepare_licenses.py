"""Local license packaging fixtures: no account, profile or private file is read."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'Prepare-Licenses.py'
spec = importlib.util.spec_from_file_location('fred_android_license_package', SCRIPT)
licenses = importlib.util.module_from_spec(spec)
spec.loader.exec_module(licenses)


class PrepareLicensesTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.goroot = self.root / 'go-runtime'
        self.module = self.root / 'module-cache'
        for target, content in {
            'client-qwen/LICENSE.txt': b'Full application MIT license fixture\n',
            'client-qwen/vendor/markdown-it-LICENSE.txt': b'Full Markdown MIT license fixture\n',
            'client-qwen/vendor/README.txt': b'markdown-it 15.0.2 (MIT)\n',
            'go-runtime/LICENSE': b'Full Go BSD license fixture\n',
            'go-runtime/VERSION': b'go1.27.1\n',
            'module-cache/LICENSE': b'Full module license fixture\n',
            'module-cache/subpackage/NOTICE.txt': b'Full module attribution fixture\n',
            'module-cache/secret.fred-android': b'SYNTHETIC_DO_NOT_PACKAGE_THIS',
            'module-cache/main.go': b'package fixture\n',
        }.items():
            path = self.root / target
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        self.modules = [{'name': 'example.org/module', 'version': 'v1.2.3', 'directory': self.module}]

    def tearDown(self):
        self.temporary.cleanup()

    def test_full_licenses_are_copied_without_source_or_profile_files(self):
        package = licenses.prepare(self.root, self.modules, self.goroot)
        self.assertEqual(package['application/LICENSE.txt'], (self.root / 'client-qwen/LICENSE.txt').read_bytes())
        self.assertEqual(package['modules/example.org/module/subpackage/NOTICE.txt'], b'Full module attribution fixture\n')
        self.assertFalse(any('secret' in name or name.endswith('.go') for name in package))
        self.assertFalse(any(b'SYNTHETIC_DO_NOT_PACKAGE_THIS' in content for content in package.values()))
        index = json.loads(package['manifest.json'])
        self.assertEqual(index['components'][-1]['version'], 'v1.2.3')
        self.assertNotIn(str(self.root), package['manifest.json'].decode())

    def test_missing_module_license_blocks_packaging(self):
        self.modules[0]['directory'] = self.root / 'empty-module'
        self.modules[0]['directory'].mkdir()
        with self.assertRaises(ValueError):
            licenses.prepare(self.root, self.modules, self.goroot)

    def test_output_preserves_unrelated_assets_and_check_detects_changes(self):
        package = licenses.prepare(self.root, self.modules, self.goroot)
        output = self.root / 'output'
        output.mkdir()
        unrelated = output / 'unrelated.txt'
        unrelated.write_bytes(b'preserve')
        licenses.write_package(output, package)
        licenses.write_package(output, package, check=True)
        self.assertEqual(unrelated.read_bytes(), b'preserve')
        (output / 'go/LICENSE').write_bytes(b'altered')
        with self.assertRaises(ValueError):
            licenses.write_package(output, package, check=True)

    def test_compiled_module_metadata_requires_consistent_versions(self):
        metadata = '\tdep\texample.org/module\tv1.2.3\th1:fixture\n' * 2
        self.assertEqual(licenses.binary_dependencies(metadata), {'example.org/module': 'v1.2.3'})
        with self.assertRaises(ValueError):
            licenses.binary_dependencies(metadata + '\tdep\texample.org/module\tv1.2.4\th1:changed\n')
        with self.assertRaises(ValueError):
            licenses.binary_dependencies('not a Go binary')


if __name__ == '__main__':
    unittest.main()
