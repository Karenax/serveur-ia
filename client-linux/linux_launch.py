"""Run the unmodified shared UI and loopback API with Linux platform services."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sys


def verify_files(root):
    manifest = json.loads((root/'build-manifest.json').read_text(encoding='utf-8'))
    for name, digest in manifest['files'].items():
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or '\\' in name:
            raise ValueError('Chemin de paquet invalide.')
        path = root/name
        if not path.resolve().is_relative_to(root.resolve()) or path.is_symlink():
            raise ValueError('Lien inattendu dans le paquet Linux.')
        with path.open('rb') as stream:
            if hashlib.file_digest(stream,'sha256').hexdigest() != digest:
                raise ValueError('Paquet Linux incomplet ou altéré : '+name)


def main():
    if not sys.platform.startswith('linux'):
        raise SystemExit('Ce lanceur est réservé à Linux.')
    if os.geteuid() == 0:
        raise SystemExit('Ouvrez Kiara depuis votre session habituelle, sans sudo.')
    root = Path(__file__).resolve().parent
    os.umask(0o077)
    verify_files(root)
    os.environ.setdefault('QT_API','pyside6')
    sys.path[:0] = [str(root/'client'),str(root/'shared'),str(root/'client/voice/conversation-worker')]
    if '--audio-self-test' in sys.argv:
        from linux_audio import audio_self_test
        print(json.dumps(audio_self_test()))
        return
    import client
    client.main()


if __name__ == '__main__':
    main()
