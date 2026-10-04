"""Conserve les références et modifications des moteurs sans leurs builds ni modèles."""
from pathlib import Path
import json
import subprocess
import shutil

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'dependances'


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], timeout=180)


def main():
    OUT.mkdir(exist_ok=True)
    records = []
    names = ['Strata-src', 'cafe-llama-src', 'llama-p100-src', 'ik-llama-src']
    names.extend(p.relative_to(ROOT).as_posix() for p in (ROOT / 'recherche').glob('*/source-*')
                 if (p / '.git').exists())
    for name in names:
        repo = ROOT / name
        if not (repo / '.git').exists():
            continue
        head = git(repo, 'rev-parse', 'HEAD').decode().strip()
        remote = git(repo, 'remote', 'get-url', 'origin').decode().strip()
        seen = set()
        while Path(remote).is_absolute() and (Path(remote) / '.git').exists() and remote not in seen:
            seen.add(remote)
            remote = git(Path(remote), 'remote', 'get-url', 'origin').decode().strip()
        branch = git(repo, 'branch', '--show-current').decode().strip()
        base = head
        for ref in ('origin/main', 'origin/master', 'origin/HEAD'):
            exists = subprocess.run(['git', '-C', str(repo), 'rev-parse', '--verify', ref],
                                    capture_output=True, timeout=30)
            if exists.returncode == 0:
                base = git(repo, 'merge-base', 'HEAD', ref).decode().strip()
                break
        patch = git(repo, 'diff', '--binary', base, '--')
        snapshot_name = name.replace('/', '__')
        patch_name = snapshot_name + '.patch'
        if patch:
            (OUT / patch_name).write_bytes(patch)
        copied = []
        for raw in git(repo, 'ls-files', '--others', '--exclude-standard', '-z').split(b'\0'):
            if not raw:
                continue
            relative = Path(raw.decode('utf-8'))
            source = repo / relative
            if source.suffix.lower() not in {'.py', '.cjs', '.js', '.cpp', '.hpp', '.h', '.cu', '.cuh'}:
                continue
            if any(part in {'.venv', 'node_modules', '__pycache__'} for part in relative.parts):
                continue
            if source.stat().st_size > 2 * 1024 * 1024:
                continue
            target = OUT / (snapshot_name + '-nouveaux') / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied.append(relative.as_posix())
        records.append(dict(directory=name, remote=remote, branch=branch, head=head,
                            patch_base=base, patch=patch_name if patch else None,
                            additional_directory=snapshot_name + '-nouveaux' if copied else None,
                            additional_files=copied))
        print(f'{name}: patch {len(patch)} octets, {len(copied)} nouveau(x) fichier(s) source')
    (OUT / 'moteurs.json').write_text(json.dumps(records, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (OUT / 'README.md').write_text(
        '# Moteurs tiers\n\n'
        'Pour chaque entrée de `moteurs.json`, cloner `remote` dans `directory`, '
        'extraire le commit `patch_base`, puis appliquer le patch depuis ce dossier '
        'avec `git apply --binary <chemin-du-projet>/dependances/<patch>`. Copier ensuite les éventuels '
        'fichiers indiqués par `additional_directory` dans le moteur.\n\n'
        'Les patchs contiennent les modifications locales, y compris les changements '
        'committés depuis la base. Les outils CUDA, modèles et environnements Python '
        'ne sont pas sauvegardés ici. Relancer `Sauvegarder-Dependances.py` avant un '
        'commit pour actualiser cet instantané.\n', encoding='utf-8')


if __name__ == '__main__':
    main()
