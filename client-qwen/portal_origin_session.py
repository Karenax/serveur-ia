"""Profile-exclusive, read-only Tauri origin inventory.

The desktop relay uses this for profiles without a recorded origin. The caller
holds the profile lock until the normal relay takes over. Multiple or unknown
origins stop the startup; transferring them remains a separate prototype.
"""
from pathlib import Path
from math import isfinite
import re
from time import monotonic

from portal_origin_plan import OriginInventoryPlan
from portal_origin_state import FIRST_PORT, LAST_PORT, read_origin, record_origin
from portal_recovery_broker import PortalRecoveryBroker


class OriginSessionError(RuntimeError):
    pass


class OriginNeedsRecovery(OriginSessionError):
    """The scan cannot select one existing origin without migration."""


class OriginInventoryUnavailable(OriginSessionError):
    """At least one origin could not be checked."""


def recovery_offer(identity, token):
    """Encode a bounded private offer for the desktop process, never for logs."""
    if (not isinstance(identity, str) or not re.fullmatch(r'[0-9a-f]{20}', identity)
            or not isinstance(token, str) or not re.fullmatch(r'[0-9a-f]{64}', token)):
        raise ValueError('Offre de récupération invalide.')
    return f'KIARA_RELAY_ORIGIN_SCAN {identity} {token}'


def transfer_offer(identity, token, source, destination, engine, mode='transfer'):
    """Encode an experimental window instruction for the private relay pipe."""
    recovery_offer(identity, token)  # Keep the same bounded profile and token rules.
    if (type(source) is not int or type(destination) is not int
            or not FIRST_PORT <= source <= LAST_PORT or not FIRST_PORT <= destination <= LAST_PORT
            or engine not in ('qt', 'tauri') or mode not in ('transfer','snapshot','manifest')
            or (mode=='manifest' and (engine!='tauri' or source!=destination))
            or (mode!='manifest' and engine == 'tauri' and source == destination)):
        raise ValueError('Offre de transfert invalide.')
    return f'KIARA_RELAY_ORIGIN_TRANSFER {identity} {token} {source} {destination} {engine} {mode}'


class OriginInventorySession:
    """Reserve all origins, then commit only an acknowledged, unambiguous scan."""

    def __init__(self, marker, assets, *, fixed_port=None, broker_factory=PortalRecoveryBroker):
        self.marker = Path(marker)
        self.ports = tuple(range(FIRST_PORT, LAST_PORT + 1))
        self.plan = OriginInventoryPlan(self.ports, default_port=FIRST_PORT, fixed_port=fixed_port)
        self.assets = assets
        self.destination = fixed_port if fixed_port is not None else FIRST_PORT
        self.broker_factory = broker_factory
        self.broker = None
        self.finished = False

    def start(self):
        if self.broker is not None or self.finished:
            raise OriginSessionError('Inventaire déjà démarré ou terminé.')
        if read_origin(self.marker) is not None:
            raise OriginSessionError('Un port local est déjà enregistré.')
        broker = self.broker_factory(self.ports, self.destination, self.assets, inventory_plan=self.plan)
        try:
            broker.start()
        except BaseException:
            broker.close()
            raise
        self.broker = broker
        return {'ports': self.ports, 'token': broker.token}

    def status(self):
        if self.broker is None or self.finished:
            raise OriginSessionError('Inventaire indisponible.')
        return self.plan.status()

    def finish(self, timeout=0):
        """Persist only after the selected origin acknowledged the complete scan."""
        if self.broker is None or self.finished:
            raise OriginSessionError('Inventaire indisponible.')
        state = self.plan.status()['state']
        if state == 'needsRecovery':
            raise OriginNeedsRecovery('Plusieurs emplacements nécessitent une récupération.')
        if state == 'unavailable':
            raise OriginInventoryUnavailable('Une origine locale ne peut pas être vérifiée.')
        selected = self.broker.wait_complete(timeout)
        if selected is None:
            return None
        status = self.plan.status()
        if status.get('state') != 'ready' or status.get('port') != selected:
            raise OriginSessionError('Inventaire incohérent ; aucun port enregistré.')
        # The ports remain reserved while the immutable marker is created.
        result = record_origin(self.marker, selected)
        self.close()
        return result

    def close(self):
        if self.broker is not None:
            broker, self.broker = self.broker, None
            broker.close()
        self.finished = True

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_args):
        self.close()


def resolve_origin(marker, assets, announce, cancelled, *, fixed_port=None,
                   poll_interval=0.25, timeout=None, session_factory=OriginInventorySession):
    """Experimental startup protocol; the caller must keep the profile locked.

    ``announce`` starts the isolated window using the supplied private token;
    cancellation, timeout and errors always close the temporary broker.
    """
    if not callable(announce) or not callable(cancelled):
        raise ValueError('Contrôle de récupération invalide.')
    if not isinstance(poll_interval, (float, int)) or isinstance(poll_interval, bool) or not isfinite(poll_interval) or not 0 < poll_interval <= 5:
        raise ValueError('Délai de vérification invalide.')
    if timeout is not None and (not isinstance(timeout, (float, int)) or isinstance(timeout, bool) or not isfinite(timeout) or timeout <= 0):
        raise ValueError('Délai de vérification invalide.')
    port = read_origin(marker)
    if port is not None:
        if fixed_port is not None and port != fixed_port:
            raise OriginSessionError('Le port enregistré est incompatible avec la liaison existante.')
        return port
    deadline = None if timeout is None else monotonic() + timeout
    session = session_factory(marker, assets, fixed_port=fixed_port)
    try:
        descriptor = session.start()
        announce(descriptor)
        while not cancelled():
            remaining = None if deadline is None else deadline - monotonic()
            if remaining is not None and remaining <= 0:
                raise OriginSessionError('La vérification a expiré ; aucun port choisi.')
            result = session.finish(poll_interval if remaining is None else min(poll_interval, remaining))
            if result is not None:
                return result
        raise OriginSessionError('La vérification a été interrompue ; aucun port choisi.')
    finally:
        session.close()
