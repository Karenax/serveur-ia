# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('F:/Serveur IA/client-qwen/voice', 'voice'), ('F:/Serveur IA/client-qwen/voice.js', '.'), ('F:/Serveur IA/client-qwen/conversation.js', '.'), ('F:/Serveur IA/client-qwen/workspace.html', '.'), ('F:/Serveur IA/client-qwen/ui.css', '.'), ('F:/Serveur IA/client-qwen/ui.js', '.'), ('F:/Serveur IA/client-qwen/attachments.js', '.'), ('F:/Serveur IA/client-qwen/selection.js', '.'), ('F:/Serveur IA/client-qwen/thinking.js', '.'), ('F:/Serveur IA/client-qwen/markdown.js', '.'), ('F:/Serveur IA/client-qwen/corrector.js', '.'), ('F:/Serveur IA/client-qwen/vendor', 'vendor'), ('F:/Serveur IA/client-qwen/chat.html', '.'), ('F:/Serveur IA/client-qwen/LICENSE.txt', '.'), ('F:/Serveur IA/client-qwen/THIRD-PARTY.txt', '.')]
binaries = [('F:/Serveur IA/client-qwen/wireguard-bridge.exe', '.')]
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
    ['F:/Serveur IA/client-qwen/client.py'],
    pathex=['F:/Serveur IA/shared'],
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
    name='Accès serveur Fred',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='F:/Serveur IA/client-qwen/product-version.txt',
    icon=['F:/Serveur IA/client-qwen/fred.ico'],
)
