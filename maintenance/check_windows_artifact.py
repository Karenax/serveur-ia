"""Check the frozen package and execute its smoke test without audio or model calls."""
import argparse
from pathlib import Path
import subprocess

from PyInstaller.archive.readers import CArchiveReader
import psutil


REQUIRED_SHARED = {
    'kiara_shared', 'kiara_shared.http', 'kiara_shared.file_lock',
    'kiara_shared.history_store', 'kiara_shared.voice_runtime',
    'kiara_shared.voice_packs', 'kiara_shared.http_download',
    'kiara_shared.profiles', 'kiara_shared.releases', 'kiara_shared.version',
}
ROOT = Path(__file__).resolve().parents[1]
UI_ASSETS = (
    'chat.html', 'workspace.html', 'ui.css', 'ui.js', 'project-conversation.js',
    'conversation.js', 'voice.js', 'corrector.js', 'attachments.js',
    'selection.js', 'thinking.js', 'markdown.js', 'vendor/markdown-it.min.js',
)
THUNDERBIRD_ASSETS = ('manifest.json', 'core.js', 'background.js', 'options.html', 'options.js')


def check(artifact, result):
    artifact = artifact.resolve()
    archive = CArchiveReader(str(artifact))
    modules = archive.open_embedded_archive('PYZ.pyz')
    missing = REQUIRED_SHARED - modules.toc.keys()
    if missing:
        raise ValueError('Frozen client is missing: ' + ', '.join(sorted(missing)))
    expected = {name: ROOT / 'client-qwen' / name for name in UI_ASSETS}
    if artifact.name == 'kiara-relay.exe':
        expected.update({name: ROOT / 'client-qwen' / name for name in ('help.html', 'help.css', 'help.mjs')})
        expected.update({
            'thunderbird-agent/' + name: ROOT / 'agent/extensions/thunderbird-agent' / name
            for name in THUNDERBIRD_ASSETS
        })
    for name, source in expected.items():
        packaged = name.replace('/', '\\')
        if packaged not in archive.toc or archive.extract(packaged) != source.read_bytes():
            raise ValueError('Frozen client resource missing or different from source: ' + name)
    result.parent.mkdir(parents=True, exist_ok=True)
    result.unlink(missing_ok=True)
    process = subprocess.Popen([str(artifact), '--self-test', '--result', str(result.resolve())],
                               creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        code = process.wait(timeout=90)
    except subprocess.TimeoutExpired:
        # Close only this owned test tree, including a bootloader error dialog.
        try:
            parent = psutil.Process(process.pid)
            children = parent.children(recursive=True)
            for child in reversed(children):
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            parent.kill()
        except psutil.NoSuchProcess:
            pass
        process.wait(timeout=10)
        raise RuntimeError('Frozen client smoke test timed out') from None
    if code or not result.is_file() or 'self-test OK' not in result.read_text(encoding='utf-8'):
        raise ValueError('Frozen client smoke test failed: ' + str(code))
    print('Frozen shared package and native smoke test: OK')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--result', type=Path, required=True)
    args = parser.parse_args()
    check(args.artifact, args.result)
