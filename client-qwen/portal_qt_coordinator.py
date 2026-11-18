"""Experimental read-only inventory of the old Qt storage under a profile lock.

This does not migrate or delete data, create a marker, or start automatically.
The caller must hold the common Qt/Tauri profile lock for the entire operation.
"""
from pathlib import Path
import subprocess
import sys
from time import monotonic
import json

from portal_origin_plan import OriginInventoryPlan
from portal_origin_state import FIRST_PORT, LAST_PORT
from portal_recovery_broker import PortalRecoveryBroker
from portal_qt_profile_guard import ensure_qt_profile_idle,ensure_qt_profile_owned


class QtInventoryError(RuntimeError):
    pass


def inspect_qt(storage, script, assets, cancelled, *, helper=None, ports=None,
               timeout=120, environment=None, broker_factory=PortalRecoveryBroker, audio_archives=False):
    """Return only port counts; every unverified or ambiguous state stays so."""
    if (not callable(cancelled) or type(audio_archives) is not bool or not isinstance(timeout, (int, float))
            or isinstance(timeout, bool) or not 0 < timeout <= 600):
        raise ValueError('Paramètres de vérification Qt invalides.')
    ports = tuple(range(FIRST_PORT, LAST_PORT + 1)) if ports is None else tuple(ports)
    if len(ports) != 10:
        raise ValueError('Paramètres de vérification Qt invalides.')
    storage, script = Path(storage), Path(script)
    if not storage.is_absolute() or not script.is_absolute():
        raise ValueError('Paramètres de vérification Qt invalides.')
    if sys.platform.startswith('linux'):ensure_qt_profile_idle(storage)
    command = [sys.executable, '-u', str(Path(__file__).with_name('portal_qt_inventory.py'))] if helper is None else list(helper)
    if not command:
        raise ValueError('Contrôle Qt indisponible.')
    plan = OriginInventoryPlan(ports,default_port=ports[0],allow_audio_archives=audio_archives,require_audio_ids=audio_archives)
    deadline = monotonic() + timeout
    with broker_factory(ports, ports[0], assets, inventory_plan=plan) as broker:
        if cancelled():raise QtInventoryError('Vérification Qt interrompue.')
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   env=environment)
        try:
            descriptor={'token':broker.token,'ports':list(ports),'initial_port':ports[0],
                        'storage':str(storage),'script':str(script),'page':'scan'}
            process.stdin.write((json.dumps(descriptor,ensure_ascii=False)+'\n').encode('utf-8'))
            process.stdin.flush()
            while True:
                if cancelled():raise QtInventoryError('Vérification Qt interrompue.')
                if sys.platform.startswith('linux'):ensure_qt_profile_owned(storage,process.pid)
                status = plan.status()
                if status['state'] in ('needsRecovery', 'unavailable'):
                    return {'status':status, 'reports':plan.reports()}
                if broker.wait_complete(.1) is not None:
                    return {'status':plan.status(), 'reports':plan.reports()}
                if process.poll() is not None:
                    raise QtInventoryError('La vérification Qt s’est arrêtée sans confirmation.')
                if monotonic() >= deadline:
                    raise QtInventoryError('La vérification Qt a expiré.')
        finally:
            try:process.stdin.close()
            except OSError:pass
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait()
            if sys.platform.startswith('linux'):ensure_qt_profile_idle(storage)
