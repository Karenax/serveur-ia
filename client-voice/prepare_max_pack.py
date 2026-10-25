"""Administrative install of the signed optional pack; ordinary clients use Vocal."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'client-qwen'), str(ROOT/'lanceur')]
from advanced_voice import AdvancedVoice
from max_installation import MaxInstallation
from signing import public


class Release:
    def __init__(self, directory, signing_home):
        self.directory = directory
        self.profile = {'update_public_key': public(signing_home, create=False)}

    def open(self, path):
        names = {'/v1/voice/max/package': 'release.json', '/v1/voice/max/package/download': 'runtime.zip'}
        if path not in names:
            raise ValueError('Source du complément Max invalide.')
        return (self.directory/names[path]).open('rb')


def main():
    parser = argparse.ArgumentParser()
    location = parser.add_mutually_exclusive_group()
    location.add_argument('--server', action='store_true')
    location.add_argument('--home', type=Path)
    parser.add_argument('--release', type=Path, default=ROOT/'toolchain/voice-max-release')
    parser.add_argument('--signing-home', type=Path, default=ROOT/'lanceur')
    parser.add_argument('--download', action='store_true')
    args = parser.parse_args()
    home = ROOT/'toolchain/voice-max-server' if args.server else args.home or Path(os.environ.get('LOCALAPPDATA', str(Path.home())))/'QwenClient/voice-max'
    runtime = AdvancedVoice(home)
    installation = MaxInstallation(home, Release(args.release, args.signing_home), runtime, ROOT/'toolchain/asr-models')
    try:
        installation.detect()
        plan = installation.plan()
        print(json.dumps(plan, ensure_ascii=False, indent=2), flush=True)
        if not args.download:
            print('Aucun téléchargement lancé. Ajouter --download pour installer le complément annoncé.')
            return
        installation.install(plan['plan'])
        while installation.thread.is_alive():
            installation.thread.join(5)
            print(json.dumps(installation.status(), ensure_ascii=False), flush=True)
        if installation.status()['phase'] not in ('ready', 'limited'):
            raise ValueError(installation.status()['message'])
    finally:
        installation.close(); runtime.close()


if __name__ == '__main__':main()
