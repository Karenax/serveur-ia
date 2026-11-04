"""Install into the extracted directory; register a per-user desktop shortcut."""
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import venv


def desktop_quote(value):
    # Desktop Entry Exec has its own quoting rules (including field codes).
    return '"'+str(value).replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$').replace('%','%%')+'"'


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
            'Extrayez l’archive Kiara-linux-amd64-…-vocal.tar.gz, puis lancez\n'
            'python3 installer.py depuis le dossier extrait Kiara-linux-amd64.\n'
            'Copier uniquement le dossier client-linux du dépôt ne suffit pas.')
    if not shutil.which('parec'):
        raise SystemExit('Installez pulseaudio-utils pour le microphone, puis relancez cet installateur.')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    expected = {'amd64':('x86_64','amd64'), 'arm64':('aarch64','arm64')}
    if platform.machine().lower() not in expected[manifest['architecture']]:
        raise SystemExit('Ce paquet ne correspond pas au processeur de ce PC.')
    from linux_launch import verify_files
    verify_files(root)
    environment = root/'.venv'
    venv.EnvBuilder(with_pip=True).create(environment)
    try:
        # proxy_tools is pure Python and published only as a source archive.
        subprocess.run([str(environment/'bin/python'),'-m','pip','install','--only-binary=:all:',
                        '--no-binary=proxy_tools','-r',str(root/'requirements.txt')], check=True)
    except subprocess.CalledProcessError:
        raise SystemExit('L’installation des dépendances a échoué. Consultez l’erreur pip ci-dessus, puis relancez python3 installer.py.') from None
    root.joinpath('start.sh').chmod(0o755)
    root.joinpath('client/wireguard-bridge').chmod(0o755)
    base = Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))
    if not base.is_absolute():
        raise SystemExit('XDG_DATA_HOME doit être un chemin absolu.')
    shortcuts = base/'applications'
    shortcuts.mkdir(parents=True, exist_ok=True)
    entry = ('[Desktop Entry]\nType=Application\nName=Kiara\nComment=Accès à votre assistant Kiara\n'
             'Exec='+desktop_quote(root/'start.sh')+'\nIcon='+str(root/'client/fred-icon.png')+
             '\nTerminal=false\nCategories=Office;Network;\nStartupNotify=true\n')
    (shortcuts/'kiara.desktop').write_text(entry,encoding='utf-8')
    print('Kiara est installé. Ouvrez Kiara depuis le menu des applications.')


if __name__ == '__main__':
    main()
