# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('D:/Serveur IA/client-qwen/voice', 'voice'), ('D:/Serveur IA/client-qwen/voice.js', '.'), ('D:/Serveur IA/client-qwen/conversation.js', '.'), ('D:/Serveur IA/client-qwen/workspace.html', '.'), ('D:/Serveur IA/client-qwen/ui.css', '.'), ('D:/Serveur IA/client-qwen/ui.js', '.'), ('D:/Serveur IA/client-qwen/attachments.js', '.'), ('D:/Serveur IA/client-qwen/selection.js', '.'), ('D:/Serveur IA/client-qwen/thinking.js', '.'), ('D:/Serveur IA/client-qwen/markdown.js', '.'), ('D:/Serveur IA/client-qwen/corrector.js', '.'), ('D:/Serveur IA/client-qwen/vendor', 'vendor'), ('D:/Serveur IA/client-qwen/chat.html', '.'), ('D:/Serveur IA/client-qwen/LICENSE.txt', '.'), ('D:/Serveur IA/client-qwen/THIRD-PARTY.txt', '.')]
binaries = [('D:/Serveur IA/client-qwen/wireguard-bridge.exe', '.')]
hiddenimports = []
tmp_ret = collect_all('webview')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pythonnet')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('clr_loader')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['D:/Serveur IA/client-qwen/client.py'],
    pathex=[],
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
    version='D:/Serveur IA/client-qwen/product-version.txt',
    icon=['D:/Serveur IA/client-qwen/fred.ico'],
)
