"""Install into the extracted directory; register a per-user desktop shortcut."""
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import venv


def desktop_quote(value):
    # Desktop Entry Exec has its own quoting rules (including field codes).
    return '"'+str(value).replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$').replace('%','%%')+'"'


def write_shortcut(path: Path, entry: str) -> None:
    # Keep the existing shortcut usable until the new contents are complete.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.kiara-', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(entry)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    if not sys.platform.startswith('linux') or not (3,12) <= sys.version_info[:2] <= (3,13):
        raise SystemExit('Installation requise sous Linux avec Python 3.12 ou 3.13.')
    if os.geteuid() == 0:
        raise SystemExit('Lancez cette installation depuis votre session habituelle, sans sudo.')
    root = Path(__file__).resolve().parent
    manifest_path = root/'build-manifest.json'
    if not manifest_path.is_file():
        raise SystemExit(
            'Ce dossier ne contient pas le paquet Kiara complet (build-manifest.json absent).\n'
            'Extrayez l’archive Kiara-linux-amd64-…-tauri.tar.gz, puis lancez\n'
            'python3 installer.py depuis le dossier extrait Kiara-linux-amd64.\n'
            'Copier uniquement le dossier client-linux du dépôt ne suffit pas.')
    if not shutil.which('parec'):
        raise SystemExit('Installez pulseaudio-utils pour le microphone, puis relancez cet installateur.')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('shell')!='tauri' or not all((root/name).is_file() for name in ('kiara','kiara-relay','start-tauri.sh')):
        raise SystemExit('Ce paquet ne contient pas le client Tauri complet. Utilisez une archive Kiara Tauri.')
    expected = {'amd64':('x86_64','amd64'), 'arm64':('aarch64','arm64')}
    if platform.machine().lower() not in expected[manifest['architecture']]:
        raise SystemExit('Ce paquet ne correspond pas au processeur de ce PC.')
    from linux_launch import verify_files
    verify_files(root)
    environment = root/'.venv'
    venv.EnvBuilder(with_pip=True).create(environment)
    try:
        subprocess.run([str(environment/'bin/python'),'-m','pip','install','--require-hashes','--only-binary=:all:',
                        '-r',str(root/'requirements.lock')], check=True)
    except subprocess.CalledProcessError:
        raise SystemExit('L’installation des dépendances a échoué. Consultez l’erreur pip ci-dessus, puis relancez python3 installer.py.') from None
    root.joinpath('start.sh').chmod(0o755)
    root.joinpath('client/wireguard-bridge').chmod(0o755)
    for name in ('kiara', 'kiara-relay', 'start-tauri.sh'):
        root.joinpath(name).chmod(0o755)
    base = Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))
    if not base.is_absolute():
        raise SystemExit('XDG_DATA_HOME doit être un chemin absolu.')
    shortcuts = base/'applications'
    shortcuts.mkdir(parents=True, exist_ok=True)
    entry = ('[Desktop Entry]\nType=Application\nName=Kiara\nComment=Accès à votre assistant Kiara\n'
             'Exec='+desktop_quote(root/'start-tauri.sh')+'\nIcon='+str(root/'client/fred-icon.png')+
             '\nTerminal=false\nCategories=Office;Network;\nStartupNotify=true\n')
    write_shortcut(shortcuts/'kiara.desktop', entry)
    print('Kiara est installé. Ouvrez Kiara depuis le menu des applications.')


if __name__ == '__main__':
    main()
