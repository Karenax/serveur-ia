"""Signed update migration retains the existing format while accepting format 4."""
import base64
import json
import unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
import updater
from wg_bridge import validate_profile


class HermesDistributionTests(unittest.TestCase):
    def test_previous_and_new_signed_manifests_are_accepted(self):
        key=Ed25519PrivateKey.generate()
        pinned=base64.b64encode(key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)).decode()
        for protocol in (3,4,5):
            release={'version':'3.5.22','protocol':protocol,'bytes':8,'sha256':'0'*64}
            raw=json.dumps(release,sort_keys=True,separators=(',',':')).encode()
            release['signature']=base64.b64encode(key.sign(raw)).decode()
            if protocol in (3,4):self.assertIs(updater.verify(release,pinned),release)
            else:
                with self.assertRaisesRegex(ValueError,'incompatible'):updater.verify(release,pinned)
            altered={**release,'sha256':'1'*64}
            with self.assertRaises(ValueError):updater.verify(altered,pinned)

    def test_existing_profile_and_future_format_have_same_access_identity(self):
        encoded=base64.b64encode(bytes(range(32))).decode()
        profile={'url':'wireguard://10.77.0.1:8766','transport':'wireguard','token':'qwen_'+'a'*16+'_'+'b'*43,
                 'wireguard':{'private_key':encoded,'server_public_key':encoded,'preshared_key':encoded,'address':'10.77.0.2/32','endpoint':'example.test:51820'}}
        for protocol in (3,4):
            validated=validate_profile({**profile,'protocol':protocol})
            self.assertEqual(validated['token'],profile['token']);self.assertEqual(validated['wireguard'],profile['wireguard'])
        with self.assertRaises(ValueError):validate_profile({**profile,'protocol':5})


if __name__=='__main__':unittest.main()
