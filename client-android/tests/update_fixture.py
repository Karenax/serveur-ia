"""Serve a future test APK through an isolated gateway and WireGuard peer, never production."""
import argparse
import base64
import json
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'lanceur'))
import android_releases
from remote import AccessStore, serve_gateway
from wireguard_access import WireGuardAccess, Engine
from wg_crypto import private_directory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    private_directory(args.output)
    android_releases.DIRECTORY = args.directory.resolve()
    android_releases.status()
    store = AccessStore(args.output / 'server')
    access = store.issue('Fixture mises à jour Android')
    wireguard = WireGuardAccess(store, store.home)
    wireguard.configure({'public_host': '127.0.0.1', 'listen_port': 51820})
    profile = wireguard.new_peer(access)
    profile['client_name'] = 'Fixture mises à jour Android'
    store.configure({'enabled': True, 'url': 'wireguard://10.77.0.1:8766'})
    server = serve_gateway(store, lambda: (0, 'unused', ''), 0)
    engine = Engine({'role': 'server', 'wireguard': {'private_key': wireguard.vault()['private_key']},
                    'listen_port': 0, 'upstream_port': server.server_port, 'peers': wireguard.peers()},
                    executable=ROOT / 'toolchain/releases-staging/android-updates/wireguard-bridge.exe')
    profile['wireguard']['endpoint'] = f'10.0.2.2:{engine.port}'
    (args.output / 'profile.b64').write_text(base64.b64encode(json.dumps(profile).encode()).decode(), encoding='ascii')
    print('Isolated Android update fixture ready', flush=True)
    try:
        server.serve_forever()
    finally:
        engine.close(); wireguard.close(); server.server_close()


if __name__ == '__main__': main()
