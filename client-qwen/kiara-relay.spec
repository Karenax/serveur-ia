# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path
import ssl

from PyInstaller.utils.hooks import collect_all

client = Path(SPECPATH).resolve()
root = client.parent
extension = root / 'agent/extensions/thunderbird-agent'
datas = [(str(client / directory), directory) for directory in ('voice', 'vendor')]
datas += [(str(extension / name), 'thunderbird-agent') for name in (
    'manifest.json', 'core.js', 'background.js', 'options.html', 'options.js')]
datas += [(str(client / name), '.') for name in (
    'chat.html', 'kiara-shell.html', 'notification-settings-panel.js', 'device-settings.js', 'device-settings.css',
    'help.html', 'help.css', 'help.mjs',
    'workspace.html', 'ui.css', 'ui.js', 'voice.js', 'conversation.js', 'project-conversation.js',
    'attachments.js', 'selection.js', 'thinking.js', 'markdown.js', 'corrector.js', 'LICENSE.txt', 'THIRD-PARTY.txt',
    'portal_origin_inventory.js', 'portal_origin_recovery.js', 'portal_origin_scan.html', 'portal_origin_scan.js',
    'portal_origin_transfer.html', 'portal_origin_transfer.js', 'portal_origin_sender.js', 'portal_origin_sender_result.js',
    'portal_origin_receiver.js', 'portal_origin_window.js', 'portal_origin_snapshot.js',
    'portal_conflict_archive.js', 'portal_conflict_review.js', 'portal_conflict_review.css', 'portal_conflict_library.js', 'portal_conflict_library.css',
    'portal_audio_conflict_archive.js', 'portal_audio_conflict_review.js', 'portal_audio_conflict_library.js', 'portal_origin_manifest.js')]
datas += [(str(root / 'client-tauri/src/recovery_init.js'), '.')]
rejected_cas = Path(ssl.__file__).with_name('codex-rejected-cas.pem')
if rejected_cas.is_file():
    datas.append((str(rejected_cas), '.'))
binaries = [(os.environ.get('KIARA_BUILD_WIREGUARD', str(client / 'wireguard-bridge.exe')), '.')]
hiddenimports = []
tmp_ret = collect_all('kiara_shared')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('webview')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pythonnet')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('clr_loader')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    [str(client / 'client.py')],
    pathex=[str(root / 'shared')],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='kiara-relay',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=str(client / 'product-version.txt'),
    icon=[str(client / 'fred.ico')],
)
