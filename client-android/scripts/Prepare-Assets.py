#!/usr/bin/env python3
"""Package the shared Fred UI for Android without changing the desktop sources.

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
          "corrector.js", "attachments.js", "thinking.js", "selection.js", "voice.js",
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


def prepare(source: Path) -> str:
    chat = read(source / "chat.html")
    chat = replace_once(chat, "width=device-width,initial-scale=1", "width=device-width,initial-scale=1,viewport-fit=cover,interactive-widget=resizes-content", "viewport")
    chat = replace_once(chat, "<body>", "<body>" + read(MOBILE / "onboarding.html"), "onboarding")
    for name in ("updates",):
        chat = sub_once(chat, rf'<button class="nav-button" data-view-button="{name}">.*?</button>', "", f"{name} navigation")
        chat = sub_once(chat, rf'<section class="settings-view" data-view="{name}" hidden>.*?</section>', "", f"{name} pane")
    for name in ("access", "connection"):
        chat = sub_once(chat, rf'<section class="settings-view" data-view="{name}" hidden>.*?</section>', read(MOBILE / f"{name}.html"), f"{name} pane")
    chat = sub_once(chat, r'<section class="settings-view" data-view="api" hidden>.*?</section>', read(MOBILE / 'api.html'), 'Android local API pane')
    chat = chat.replace("EXE personnel · connexion automatique", "Accès personnel · Android")
    chat = sub_once(chat, r'<details class="composer-options"><summary>Options</summary>.*?</details>',
                    '<button id="retry-without-thinking" type="button" class="secondary" hidden>Réessayer sans réflexion</button>',
                    "Android response retry menu")
    chat = replace_once(chat, "$('retry').onclick=()=>{", "function retryLastResponse(){", "Android conditional retry action")
    chat = replace_once(chat, ",'retry']", "]", "Android response retry button state")
    chat = replace_once(chat, "if(value?.code==='thinking_without_answer')$('retry-without-thinking').closest('details').open=true;", "", "Android retry popover")
    chat = replace_once(chat, "$('retry').click();", "retryLastResponse();", "Android retry without thinking")
    chat = sub_once(chat, r"async function clientState\(\)\{.*?(?=\n\s*\$\('endpoint'\)\.oninput)", read(MOBILE / "client-state.js").rstrip(), "Android state")
    chat = sub_once(chat, r"\s*\$\('endpoint'\)\.oninput=.*?(?=\n\s*async function bootstrap)", "", "desktop endpoint/update events")
    chat = sub_once(chat, r"\s*\$\('toggle-api-key'\)\.onclick=.*?(?=\n)", "", "desktop local API event")
    chat = replace_once(chat, "setInterval(()=>{if(loggedIn&&!busy)api('/client/update/check',{}).catch(()=>{});},600000);", "", "desktop updater timer")
    chat = chat.replace("['/v1/models','/client/integrations/apply'].includes(path)", "path==='/v1/models'")
    chat = replace_once(chat, "if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing)", "if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)&&!e.isComposing)", "mobile multiline composer")
    chat = replace_once(chat, "buttons();$('prompt').focus();models();", "buttons();if(matchMedia('(pointer:fine)').matches)$('prompt').focus();models();", "finish keyboard focus")
    chat = chat.replace("Entrée pour envoyer · Maj + Entrée pour une nouvelle ligne", "Touchez la flèche pour envoyer").replace("Envoyer · Entrée", "Envoyer le message")
    chat = chat.replace("Les changements des deux postes", "Les changements de vos appareils")
    chat = chat.replace("if(busy||!loggedIn||$('connection-choice').open)", "if(busy||!loggedIn||$('connection-choice').open||$('android-onboarding').open)")
    chat = replace_once(chat, "setInterval(models,15000);setInterval(clientState,2000);", "setInterval(()=>{if(!document.hidden)models();},15000);setInterval(()=>{if(!document.hidden)clientState();},2000);", "mobile background polling")

    workspace = read(source / "workspace.html")
    workspace = workspace.replace("['access','connection','updates','api']", "['access','connection','api']")
    workspace = workspace.replace("Glissez une conversation sur un projet pour la déplacer. Clic droit pour déplacer, archiver ou supprimer.", "Touchez ··· pour déplacer, archiver ou supprimer une discussion.")
    workspace = workspace.replace("if(!connected||busy||historySyncPending||conversationActionPending||wsDraggedConversation)", "if(document.hidden||!connected||busy||historySyncPending||conversationActionPending||wsDraggedConversation)")

    ui = read(source / "ui.js")
    ui = ui.replace("Comme Windows", "Comme l’appareil").replace("Moderne · Segoe UI", "Moderne · Android").replace("Appliqué sur ce poste", "Appliqué sur cet appareil")
    ui = ui.replace("if(name==='api')uiRefreshIntegrations();", "")
    ui = sub_once(ui, r"let uiLastConnection=\{\},uiIntegrations=.*?(?=const uiConnectionPhases=)", "let uiLastConnection={};\n", "desktop integration logic")
    ui = ui.replace("uiIntegrationButtons();", "")
    ui = sub_once(ui, r"let uiWireGuardEndpoint=.*?(?=setInterval\(\(\)=>\{if\(busy\)uiConnectionStatus)", "function uiConnectionSettings(state){}\n", "desktop connection transfer controls")
    selection = read(source / "selection.js")
    selection = replace_once(selection, "document.addEventListener('contextmenu',event=>{\n  selectionUpdate();", "document.addEventListener('contextmenu',event=>{\n  if(matchMedia('(pointer:coarse)').matches)return;\n  selectionUpdate();", "native Android selection handles")
    selection = selection.replace("Copier la sélection · Ctrl+C", "Copier la sélection").replace("Réessayez avec Ctrl+C.", "Sélectionnez le texte puis touchez Copier.")

    corrector = read(source / "corrector.js")
    corrector = sub_once(corrector, r"    const reader=response\.body\.getReader\(\),decoder=new TextDecoder\(\);.*?(?=\n    if\(!correctorAnswer\.content\.trim\(\)\))", read(MOBILE / "corrector-response.js").rstrip(), "corrector JSON fallback")
    presentation = script(ui) + script(read(source / "attachments.js")) + script(corrector)
    presentation += script(selection) + script(read(source / "thinking.js")) + script(read(source / "voice.js")) + script(read(MOBILE / "android.js"))
    markdown = script(read(source / "vendor/markdown-it.min.js")) + script(read(source / "markdown.js"))
    css = read(source / "ui.css") + "\n" + read(MOBILE / "android.css")
    chat = replace_once(chat, "</head>", markdown + "</head>", "markdown bootstrap")
    chat = replace_once(chat, "</body>", workspace + presentation + "</body>", "workspace bootstrap")
    chat = replace_once(chat, "__UI_CSS__", css, "style assembly")
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
