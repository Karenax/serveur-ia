from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    'lanceur/web/app.js', 'lanceur/web/workspace.js', 'lanceur/web/interface.js',
    'client-qwen/ui.js', 'client-qwen/markdown.js', 'client-qwen/corrector.js',
    'client-qwen/vendor/markdown-it.min.js',
)


def main():
    for name in ('chat.html', 'workspace.html'):
        path = ROOT / 'client-qwen' / name
        script = re.search(r'<script nonce="__NONCE__">(.*?)</script>', path.read_text(encoding='utf-8'), re.S)
        if script is None:
            raise SystemExit(f'Script intégré introuvable dans {path}')
        subprocess.run(['node', '--check', '-'], input=script[1].replace('__CONFIG__', '{}').encode(), check=True)
    for name in SOURCES:
        subprocess.run(['node', '--check', str(ROOT / name)], check=True)
    subprocess.run(['node', str(ROOT / 'lanceur/test_markdown.js')], check=True)


if __name__ == '__main__':
    main()
