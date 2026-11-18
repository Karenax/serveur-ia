"""The experimental Qt helper accepts only a bounded private descriptor."""
import io
import json
from pathlib import Path
import tempfile
import unittest

from portal_qt_inventory import PORTS, read_descriptor


class QtInventoryDescriptorTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.storage=Path(self.directory.name)/'storage';self.storage.mkdir()
        self.script=Path(self.directory.name)/'init.js';self.script.write_text('fictif')
        self.value={'token':'a'*64,'ports':list(PORTS),'initial_port':PORTS[0],
                    'storage':str(self.storage),'script':str(self.script)}

    def read(self,value):return read_descriptor(io.BytesIO(json.dumps(value).encode()+b'\n'))

    def test_accepts_valid_descriptor(self):
        self.assertEqual(self.read(self.value),self.value)
        self.assertEqual(self.read({**self.value,'page':'scan'})['page'],'scan')
        self.assertEqual(self.read({**self.value,'page':'transfer','mode':'snapshot'})['mode'],'snapshot')

    def test_rejects_untrusted_ports_tokens_and_paths(self):
        for change in ({'token':'a'*63},{'ports':list(reversed(PORTS))},{'initial_port':9},
                       {'storage':'relative'},{'script':str(self.storage)},{'extra':True},{'mode':'snapshot'},
                       {'page':'transfer'},{'page':'scan','mode':'snapshot'},{'page':'transfer','mode':'other'}):
            with self.subTest(change=change),self.assertRaises(ValueError):self.read({**self.value,**change})

    def test_rejects_duplicate_fields_and_incomplete_or_oversized_input(self):
        for raw in (b'{"token":1,"token":2}\n',b'{}',b'x'*4096+b'\n'):
            with self.subTest(length=len(raw)),self.assertRaises(ValueError):read_descriptor(io.BytesIO(raw))

    def test_rejects_symlink_storage_without_following_it(self):
        link=Path(self.directory.name)/'link'
        try:link.symlink_to(self.storage,target_is_directory=True)
        except (OSError,NotImplementedError):self.skipTest('Lien symbolique indisponible.')
        with self.assertRaises(ValueError):self.read({**self.value,'storage':str(link)})


if __name__=='__main__':unittest.main()
