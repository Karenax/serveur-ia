"""Download only the licensed, pinned French checkpoint; no production changes."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'lanceur'))
from phonon_model import MODEL, SPEC, verify


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--download', action='store_true')
    args = parser.parse_args()
    if args.download:
        from huggingface_hub import hf_hub_download
        from huggingface_hub.errors import GatedRepoError
        try:
            for name,entry in SPEC['files'].items():
                if 'repository' in entry:
                    source=hf_hub_download(entry['repository'],entry['filename'],revision=entry['revision'])
                    target=MODEL/name;target.parent.mkdir(parents=True,exist_ok=True)
                    staged=target.with_suffix('.tmp');shutil.copyfile(source,staged);staged.replace(target)
                else:hf_hub_download(SPEC['repository'], name, revision=SPEC['revision'], local_dir=MODEL)
        except GatedRepoError:
            print('Accès au modèle français requis : accepter les conditions sur ' +
                  'https://huggingface.co/' + SPEC['repository'] + ', puis lancer hf auth login.', file=sys.stderr)
            return 2
    verify()
    result = {'passed': True, 'repository': SPEC['repository'], 'revision': SPEC['revision'],
              'files': {name: hashlib.sha256((MODEL / name).read_bytes()).hexdigest() for name in SPEC['files']}}
    (OUT / 'checkpoint.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('Modèle français vérifié, fichiers locaux prêts. Production inchangée.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
