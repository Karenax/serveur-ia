#!/usr/bin/env python3
"""Package the shared Kiara UI for Android without changing the desktop sources.

Only __CONFIG__ and __NONCE__ remain for the native loopback server. Credential
material is intentionally absent from this package; the native layer injects a
random local API key, never the server token or the WireGuard private key.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

PROJECT = Path(__file__).resolve().parent.parent
MOBILE = PROJECT / "mobile-ui"
SHARED = ("chat.html", "workspace.html", "ui.css", "ui.js", "markdown.js",
          "corrector.js", "attachments.js", "thinking.js", "selection.js", "voice.js", "conversation.js",
          "vendor/markdown-it.min.js")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def replace_once(text: str, old: str, new: str, name: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"Shared UI changed: expected one {name}, found {text.count(old)}")
    return text.replace(old, new, 1)


def sub_once(text: str, pattern: str, replacement: str, name: str) -> str:
    text, count = re.subn(pattern, lambda _: replacement, text, count=1, flags=re.DOTALL)
    if count != 1:
        raise ValueError(f"Shared UI changed: missing {name}")
    return text


def script(value: str) -> str:
    return '<script nonce="__NONCE__">' + value.replace("</script", "<\\/script") + "</script>"


def platform_source(source: Path, name: str, adapters: dict) -> str:
    value = read(source / name)
    for operation in adapters.get('sources', {}).get(name, []):
        if 'file' in operation:
            replacement = read(MOBILE / operation['file'])
            if operation.get('rstrip'): replacement = replacement.rstrip()
            replacement = operation.get('prefix', '') + replacement + operation.get('suffix', '')
        else:
            replacement = operation['value']
        if 'label' in operation:
            value = value.replace(operation['label'], replacement)
            continue
        identity = re.escape(operation['slot'])
        if operation.get('html'):
            pattern = r'<!-- kiara-slot:' + identity + r' -->(.*?)<!-- /kiara-slot:' + identity + r' -->'
        else:
            pattern = r'/\* kiara-slot:' + identity + r' \*/(.*?)/\* /kiara-slot:' + identity + r' \*/'
        value, count = re.subn(pattern, lambda _: replacement, value, flags=re.S)
        if count != 1:
            raise ValueError('Missing or duplicated platform slot: ' + operation['slot'])
    return value


def prepare(source: Path) -> str:
    adapters = json.loads(read(MOBILE / 'platform-adapters.json'))
    if adapters.get('format') != 1: raise ValueError('Unsupported UI platform contract')
    files = {name: platform_source(source, name, adapters) for name in SHARED}
    presentation = ''.join(script(files[name]) for name in ('ui.js', 'attachments.js', 'corrector.js',
        'selection.js', 'thinking.js', 'voice.js', 'conversation.js')) + script(read(MOBILE / 'android.js'))
    platform = script('window.kiaraPlatform=Object.freeze(' + json.dumps(adapters['capabilities'],ensure_ascii=False) + ');')
    markdown = platform + script(files['vendor/markdown-it.min.js']) + script(files['markdown.js'])
    chat = replace_once(files['chat.html'], '</head>', markdown + '</head>', 'markdown bootstrap')
    chat = replace_once(chat, '</body>', files['workspace.html'] + presentation + '</body>', 'workspace bootstrap')
    chat = replace_once(chat, '__UI_CSS__', files['ui.css'] + '\n' + read(MOBILE / 'android.css'), 'style assembly')
    validate(chat)
    return chat


def validate(html: str) -> None:
    assert html.count("__CONFIG__") == 1
    assert "__UI_CSS__" not in html
    assert "data-view=\"api\"" in html and "data-view=\"updates\"" not in html
    assert "'/client/update/apply" not in html and "'/client/integrations" not in html
    assert "android-update-install" in html and "'/client/update/check'" in html
    assert "EXE" not in html and "Comme Windows" not in html
    assert 'id="retry"' not in html and "$('retry')" not in html
    assert "Réessayer la réponse" not in html
    for item in ("android-onboarding", "AndroidClient", "exportFile", "ws-project-list", "ws-document-editor",
                 "ws-jobs", "corrector-text", "thinking-bar", "chat-file-input", "/v1/chat/completions",
                 "/client/history/sync", "stream:true", "reader.read()"):
        assert item in html, f"Required Android feature missing: {item}"
    for name in ("token", "private_key", "session"):
        assert not re.search(rf"config\.{name}\b", html), f"Remote secret used by UI: {name}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=PROJECT.parent / "client-qwen")
    parser.add_argument("--output", type=Path, default=PROJECT / "app/src/main/assets")
    parser.add_argument("--check", action="store_true", help="Verify the package is up to date without writing it")
    args = parser.parse_args()
    html = prepare(args.source.resolve())
    target = args.output.resolve() / "android-chat.html"
    if args.check:
        if not target.exists() or read(target) != html:
            raise SystemExit("Android assets are missing or stale; run Prepare-Assets.py")
        print("Android UI package verified")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8", newline="\n")
    manifest = {"format": 1, "entrypoint": "android-chat.html", "sha256": hashlib.sha256(html.encode()).hexdigest(),
                "shared_sources": {name: hashlib.sha256((args.source / name).read_bytes()).hexdigest() for name in SHARED},
                "mobile_sources": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(MOBILE.iterdir()) if path.is_file()}}
    (target.parent / "ui-package.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Android UI prepared: {target} ({len(html.encode())} bytes)")


if __name__ == "__main__":
    main()
