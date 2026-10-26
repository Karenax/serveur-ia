"""Platform adapters use named regions, independent of their default formatting."""
import importlib.util
from html.parser import HTMLParser
from pathlib import Path
import json
import re
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('platform_assets',ROOT/'client-android/scripts/Prepare-Assets.py')
assets=importlib.util.module_from_spec(spec);spec.loader.exec_module(assets)


class PlatformContractTests(unittest.TestCase):
    def setUp(self):
        self.adapters=json.loads((ROOT/'client-android/mobile-ui/platform-adapters.json').read_text(encoding='utf-8'))

    def test_default_region_can_be_reformatted_without_breaking_android(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)
            original=(ROOT/'client-qwen/chat.html').read_text(encoding='utf-8')
            changed=original.replace('width=device-width,initial-scale=1','width=device-width, initial-scale=1')
            (source/'chat.html').write_text(changed,encoding='utf-8')
            self.assertEqual(assets.platform_source(source,'chat.html',self.adapters),
                             assets.platform_source(ROOT/'client-qwen','chat.html',self.adapters))

    def test_missing_or_duplicated_slot_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder);path=source/'chat.html'
            original=(ROOT/'client-qwen/chat.html').read_text(encoding='utf-8')
            for value in (original.replace('kiara-slot:viewport-1','kiara-slot:unknown'),
                          original+re.search(r'<!-- kiara-slot:viewport-1 -->.*?<!-- /kiara-slot:viewport-1 -->',original,re.S)[0]):
                path.write_text(value,encoding='utf-8')
                with self.assertRaises(ValueError):assets.platform_source(source,'chat.html',self.adapters)

    def test_windows_markers_never_enter_html_attribute_values(self):
        class Attributes(HTMLParser):
            def handle_starttag(inner,tag,attributes):
                for _,value in attributes:
                    self.assertNotIn('kiara-slot:',value or '')
        Attributes().feed((ROOT/'client-qwen/chat.html').read_text(encoding='utf-8'))


if __name__=='__main__':unittest.main()
