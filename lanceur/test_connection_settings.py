"""Clipboard connection settings validation, independent of real client credentials."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'client-qwen'))
from connection_settings import parse,export,HTTPS_ENDPOINT


class ConnectionSettingsTests(unittest.TestCase):
    def test_https_roundtrip_is_pinned_to_our_origin(self):
        self.assertEqual(parse('HTTPS://IA.KARENAX.NET/'),HTTPS_ENDPOINT)
        self.assertEqual(parse(json.dumps(export(HTTPS_ENDPOINT))),HTTPS_ENDPOINT)
        self.assertEqual(export(HTTPS_ENDPOINT)['protocol'],'HTTPS')
        for value in ('http://ia.karenax.net','https://other.example','https://ia.karenax.net.evil.example',
                      'https://ia.karenax.net@evil.example','https://ia.karenax.net:444',
                      'https://ia.karenax.net/v1','https://ia.karenax.net?token=x',
                      json.dumps({**export(HTTPS_ENDPOINT),'protocol':'UDP'})):
            with self.subTest(value=value),self.assertRaises(ValueError):parse(value)

    def test_plain_address_and_console_address(self):
        self.assertEqual(parse('  serveur.example:51820  '),'serveur.example:51820')
        self.assertEqual(parse('192.168.1.40:51820 / UDP'),'192.168.1.40:51820')
        self.assertEqual(parse('[2001:db8::1]:51820'),'[2001:db8::1]:51820')

    def test_portable_parameters_roundtrip(self):
        params=export('serveur.example:051820')
        self.assertEqual(parse(json.dumps(params,indent=2)),'serveur.example:51820')
        self.assertEqual(set(params),{'format','version','protocol','endpoint'})

    def test_invalid_import_never_produces_an_endpoint(self):
        params=export('serveur.example:51820')
        invalid=['https://serveur.example:51820/v1','serveur.example:0','serveur.example:65536','{"endpoint":"server:51820"}',None,'x'*2049]
        invalid.extend(json.dumps({**params,**change}) for change in ({'protocol':'TCP'},{'version':True},{'version':2},{'token':'private'},{'endpoint':['server:51820']}))
        for value in invalid:
            with self.subTest(value=str(value)[:80]),self.assertRaises(ValueError):parse(value)


if __name__=='__main__':unittest.main()
