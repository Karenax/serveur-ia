"""Install into the extracted directory and register a per-user shortcut."""
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
import sys
import tempfile
import venv


def desktop_string(value):
    return str(value).translate(str.maketrans({'\\': r'\\', '\n': r'\n', '\r': r'\r', '\t': r'\t'}))


def desktop_quote(value):
    # Exec quoting and field codes are interpreted after string escaping.
    argument = str(value).translate(str.maketrans({'\\': r'\\', '"': r'\"', '`': r'\`', '$': r'\$', '%': '%%'}))
    return desktop_string('"' + argument + '"')


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


def mark_executable(root, name, expected):
    parts = Path(name).parts
    with ExitStack() as files:
        directory = os.open(root, os.O_DIRECTORY | os.O_NOFOLLOW)
        files.callback(os.close, directory)
        for part in parts[:-1]:
            directory = os.open(part, os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            files.callback(os.close, directory)
        descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(descriptor, 'rb') as stream:
            if (not stat.S_ISREG(os.fstat(stream.fileno()).st_mode)
                    or hashlib.file_digest(stream, 'sha256').hexdigest() != expected):
                raise ValueError('Exécutable Linux modifié pendant l’installation.')
            os.fchmod(stream.fileno(), 0o755)


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
    if verify_files(root) != manifest:
        raise SystemExit('Le manifeste a changé pendant l’installation. Extrayez à nouveau le paquet Kiara.')
    requirements = (root/'requirements.lock').read_bytes()
    if hashlib.sha256(requirements).hexdigest() != manifest['files']['requirements.lock']:
        raise SystemExit('Le verrou des dépendances a changé pendant l’installation.')
    environment = root/'.venv'
    venv.EnvBuilder(with_pip=True).create(environment)
    try:
        with tempfile.TemporaryDirectory(prefix='kiara-lock-') as folder:
            lock = Path(folder)/'requirements.lock'
            lock.write_bytes(requirements)
            subprocess.run([str(environment/'bin/python'),'-m','pip','install','--require-hashes','--only-binary=:all:',
                            '-r',str(lock)], check=True)
    except subprocess.CalledProcessError:
        raise SystemExit('L’installation des dépendances a échoué. Consultez l’erreur pip ci-dessus, puis relancez python3 installer.py.') from None
    for name in ('start.sh', 'client/wireguard-bridge', 'kiara', 'kiara-relay', 'start-tauri.sh'):
        mark_executable(root, name, manifest['files'][name])
    base = Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))
    if not base.is_absolute():
        raise SystemExit('XDG_DATA_HOME doit être un chemin absolu.')
    shortcuts = base/'applications'
    shortcuts.mkdir(parents=True, exist_ok=True)
    entry = ('[Desktop Entry]\nType=Application\nName=Kiara\nComment=Accès à votre assistant Kiara\n'
             'Exec='+desktop_quote(root/'start-tauri.sh')+'\nIcon='+desktop_string(root/'client/fred-icon.png')+
             '\nTerminal=false\nCategories=Office;Network;\nStartupNotify=true\n')
    write_shortcut(shortcuts/'kiara.desktop', entry)
    print('Kiara est installé. Ouvrez Kiara depuis le menu des applications.')


if __name__ == '__main__':
    main()
