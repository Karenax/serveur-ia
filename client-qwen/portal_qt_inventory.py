"""Experimental isolated Qt window for the legacy Linux profile.

The caller must hold the shared desktop profile lock and reserve every port.
The descriptor, including the temporary token, arrives only over stdin.
This helper is not connected to the shipping client.
"""
from pathlib import Path
import json
import re
import stat
import sys
import threading

PORTS = tuple(range(17841, 17851))
MAX_DESCRIPTOR = 4096
ALLOWED_PATHS = frozenset({'/recovery', '/recovery/scan', '/recovery/transfer', '/recovery.js', '/portal_origin_scan.js', '/portal_origin_inventory.js',
                           '/portal_origin_recovery.js', '/portal_origin_transfer.js', '/portal_origin_sender.js',
                           '/portal_origin_sender_result.js', '/portal_origin_snapshot.js', '/portal_origin_window.js',
                           '/portal_origin_receiver.js', '/recovery/inventory',
                           '/recovery/status', '/recovery/complete', '/recovery/stage',
                           '/recovery/read', '/recovery/ack', '/recovery/receipt', '/recovery/result'})


def read_descriptor(stream):
    raw = stream.readline(MAX_DESCRIPTOR + 1)
    if not isinstance(raw, bytes) or not raw.endswith(b'\n') or len(raw) > MAX_DESCRIPTOR:
        raise ValueError('Paramètres de récupération Qt invalides.')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:raise ValueError('Paramètres de récupération Qt invalides.')
            result[key] = value
        return result
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique)
        base={'token', 'ports', 'initial_port', 'storage', 'script'}
        if not isinstance(value, dict) or set(value) not in (base,base|{'page'},base|{'page','mode'}):
            raise ValueError()
        if 'page' in value and value['page'] not in ('scan','transfer'):raise ValueError()
        if 'mode' in value and value['mode'] not in ('transfer','snapshot'):raise ValueError()
        if ('mode' in value) != (value.get('page')=='transfer'):raise ValueError()
        if not isinstance(value['token'], str) or not re.fullmatch(r'[0-9a-f]{64}', value['token']):
            raise ValueError()
        if not isinstance(value['ports'], list) or tuple(value['ports']) != PORTS or any(type(p) is not int for p in value['ports']):
            raise ValueError()
        if type(value['initial_port']) is not int or value['initial_port'] not in PORTS:
            raise ValueError()
        for name in ('storage', 'script'):
            if not isinstance(value[name], str) or not Path(value[name]).is_absolute():raise ValueError()
        storage = Path(value['storage']);script = Path(value['script'])
        if not stat.S_ISDIR(storage.lstat().st_mode) or not stat.S_ISREG(script.lstat().st_mode):
            raise ValueError()
    except (OSError, UnicodeError, TypeError, ValueError, KeyError) as error:
        raise ValueError('Paramètres de récupération Qt invalides.') from error
    return value


def main():
    if not sys.platform.startswith('linux'):
        raise SystemExit('Ce contrôle Qt est réservé à Linux.')
    descriptor = read_descriptor(sys.stdin.buffer)
    from PySide6.QtCore import QObject, QUrl, Signal
    from PySide6.QtWidgets import QApplication
    from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineScript, QWebEngineUrlRequestInterceptor
    from PySide6.QtWebEngineWidgets import QWebEngineView

    def allowed(url, *, navigation=False):
        return (url.scheme() == 'http' and url.host() == '127.0.0.1' and url.port() in PORTS
                and not url.userInfo() and not url.hasQuery() and not url.hasFragment()
                and (url.path() in ('/recovery','/recovery/scan','/recovery/transfer') if navigation else url.path() in ALLOWED_PATHS))

    class Interceptor(QWebEngineUrlRequestInterceptor):
        def interceptRequest(self, info):
            if not allowed(info.requestUrl()):info.block(True)

    class Page(QWebEnginePage):
        def acceptNavigationRequest(self, target, kind, main):return allowed(target, navigation=True)
        def createWindow(self, kind):return None

    class Stopper(QObject):
        stop = Signal()

    app = QApplication([])
    stopper = Stopper();stopper.stop.connect(app.quit)
    def watch_parent():
        try:sys.stdin.buffer.read(1)
        finally:stopper.stop.emit()
    threading.Thread(target=watch_parent, daemon=True).start()
    profile = QWebEngineProfile('pywebview')
    profile.setPersistentStoragePath(descriptor['storage'])
    interceptor = Interceptor(profile);profile.setUrlRequestInterceptor(interceptor)
    script = QWebEngineScript();script.setName('kiara-recovery-guard')
    script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
    script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
    script.setRunsOnSubFrames(False)
    with Path(descriptor['script']).open('r', encoding='utf-8') as stream:
        template = stream.read(65537)
    if len(template) > 65536:raise ValueError('Ressource Qt invalide.')
    code=(template.replace('__TOKEN__', descriptor['token'])
          .replace('__PORTS__', ','.join(map(str, PORTS)))
          .replace('__REQUIRE_NAVIGATION__', 'false'))
    if 'mode' in descriptor:
        code += ("\nObject.defineProperty(window,'__kiaraRecoveryRole',{value:'sender',configurable:false});"
                 "\nObject.defineProperty(window,'__kiaraRecoveryMode',{value:'"+descriptor['mode']+"',configurable:false});")
    script.setSourceCode(code)
    profile.scripts().insert(script)
    view = QWebEngineView();page = Page(profile, view);view.setPage(page)
    view.resize(1100, 650);view.hide()
    suffix='/recovery/'+descriptor['page'] if 'page' in descriptor else '/recovery'
    view.setUrl(QUrl(f"http://127.0.0.1:{descriptor['initial_port']}{suffix}"))
    print('KIARA_QT_INVENTORY_READY', flush=True)
    app.exec()


if __name__ == '__main__':
    main()
