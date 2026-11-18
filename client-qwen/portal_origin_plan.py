"""Fail-closed planning of a future, profile-exclusive origin inventory.

This state is intentionally ephemeral. A caller must hold the profile lock,
reserve all listed ports and re-scan after interruption before persisting a
choice. No user data or port marker is written by this module.
"""
from __future__ import annotations

from threading import Lock
import re


class InventoryPlanError(ValueError):
    pass


class OriginInventoryPlan:
    def __init__(self, ports, *, default_port, fixed_port=None, allow_audio_archives=False, require_audio_ids=False):
        ports = tuple(ports)
        if (not ports or len(set(ports)) != len(ports)
                or any(type(port) is not int or not 1024 <= port <= 65535 for port in ports)
                or default_port not in ports or (fixed_port is not None and fixed_port not in ports)
                or type(allow_audio_archives) is not bool or type(require_audio_ids) is not bool
                or (require_audio_ids and not allow_audio_archives)):
            raise InventoryPlanError('Ports de récupération invalides.')
        self._ports = ports
        self._default = default_port
        self._fixed = fixed_port
        self._allow_audio_archives = allow_audio_archives
        self._require_audio_ids = require_audio_ids
        self._reports = {}
        self._blocked = False
        self._lock = Lock()

    @property
    def ports(self):
        return self._ports

    @property
    def allows_audio_archives(self):
        return self._allow_audio_archives

    @property
    def requires_audio_ids(self):
        return self._require_audio_ids

    def _validate(self, report):
        if not isinstance(report, dict):
            raise InventoryPlanError('Inventaire invalide.')
        if set(report) == {'unavailable'} and report['unavailable'] is True:
            return {'unavailable': True}
        fields=('localEntries','audioChunks','audioArchives') if self._allow_audio_archives else ('localEntries','audioChunks')
        expected=set(fields)|({'audioArchiveIds'} if self._require_audio_ids else set())
        if set(report) != expected:
            raise InventoryPlanError('Inventaire invalide.')
        if any(type(report[key]) is not int or not 0 <= report[key] <= 9007199254740991
               for key in fields) or (self._allow_audio_archives and report['audioArchives']>3000):
            raise InventoryPlanError('Inventaire invalide.')
        value={key:report[key] for key in fields}
        if self._require_audio_ids:
            ids=report['audioArchiveIds']
            if (not isinstance(ids,list) or len(ids)!=report['audioArchives']
                    or any(not isinstance(item,str) or not re.fullmatch(r'[0-9a-f]{64}',item) for item in ids)
                    or len(set(ids))!=len(ids)):
                raise InventoryPlanError('Empreintes de copies audio invalides.')
            value['audioArchiveIds']=sorted(ids)
        return value

    @staticmethod
    def _copy(report):
        return {**report,**({'audioArchiveIds':list(report['audioArchiveIds'])} if 'audioArchiveIds' in report else {})}

    def submit(self, port, report):
        value = self._validate(report)
        with self._lock:
            if port not in self._ports or type(port) is not int:
                raise InventoryPlanError('Origine de récupération inconnue.')
            previous = self._reports.get(port)
            if previous is not None:
                if previous != value:
                    raise InventoryPlanError('L’inventaire de cette origine a changé ; recommencez.')
                return self._status_locked()
            if self._blocked or port != self._ports[len(self._reports)]:
                raise InventoryPlanError('L’inventaire doit être repris depuis le début.')
            self._reports[port] = value
            if value.get('unavailable'):
                self._blocked = True
            return self._status_locked()

    def status(self):
        with self._lock:
            return self._status_locked()

    def reports(self):
        """Return counts only, as independent copies in checked-port order."""
        with self._lock:
            return [{'port':port, **self._copy(self._reports[port])} for port in self._ports if port in self._reports]

    def _status_locked(self):
        checked = len(self._reports)
        if self._blocked:
            return {'state':'unavailable', 'checked':checked, 'total':len(self._ports)}
        if checked < len(self._ports):
            return {'state':'scanning', 'checked':checked, 'total':len(self._ports), 'nextPort':self._ports[checked]}
        occupied = [port for port in self._ports if any(self._reports[port].values())]
        # A fixed port can be required by an existing Thunderbird pairing.
        if len(occupied) > 1 or (self._fixed is not None and occupied and occupied[0] != self._fixed):
            return {'state':'needsRecovery', 'checked':checked, 'total':len(self._ports),
                    'origins':[{'port':port, **self._copy(self._reports[port])} for port in occupied]}
        selected = self._fixed if self._fixed is not None else (occupied[0] if occupied else self._default)
        return {'state':'ready', 'checked':checked, 'total':len(self._ports), 'port':selected}
