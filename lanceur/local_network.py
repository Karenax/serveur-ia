"""Control the existing, unauthenticated Qwen LAN exposure from the local console."""
import ipaddress
from pathlib import Path
import subprocess
import threading
import time
import uuid

import psutil

from core import HOME, HIDDEN, health, read_json, write_json

ADDRESS = '192.168.1.41'
SUBNET = '192.168.1.0/24'
PORT = 8080
RULE = 'Qwen-API-LAN-TCP-8080'
PROXY_KEY = r'SYSTEM\CurrentControlSet\Services\PortProxy\v4tov4\tcp'
FIREWALL_KEY = r'SYSTEM\CurrentControlSet\Services\SharedAccess\Parameters\FirewallPolicy\FirewallRules'


def registry_value(path, name):
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as key:
            return winreg.QueryValueEx(key, name)[0]
    except FileNotFoundError:
        return ''


def system_state():
    mapping = registry_value(PROXY_KEY, f'{ADDRESS}/{PORT}')
    rule = registry_value(FIREWALL_KEY, RULE)
    fields = {}
    for part in rule.split('|'):
        if '=' in part:
            key, value = part.split('=', 1)
            fields.setdefault(key, []).append(value)
    firewall = all(fields.get(key) == [value] for key, value in {
        'Active': 'TRUE', 'Action': 'Allow', 'Dir': 'In', 'Protocol': '6',
        'LPort': str(PORT), 'LA4': ADDRESS,
    }.items())
    try:
        firewall = firewall and len(fields.get('RA4', [])) == 1 and str(ipaddress.ip_network(fields['RA4'][0])) == SUBNET
    except ValueError:
        firewall = False
    firewall = firewall and not any(fields.get(key) for key in ('RA6', 'LA6', 'Profile', 'App', 'Svc'))
    listening = any(connection.status == psutil.CONN_LISTEN and connection.laddr.ip == ADDRESS
                    and connection.laddr.port == PORT for connection in psutil.net_connections(kind='tcp4'))
    return {'mapping': mapping == f'127.0.0.1/{PORT}', 'conflict': bool(mapping and mapping != f'127.0.0.1/{PORT}'),
            'firewall': bool(firewall), 'listening': listening}


class LocalNetwork:
    def __init__(self, backend, home=HOME):
        self.backend = backend
        self.home = Path(home)
        self.result_path = self.home / 'qwen-lan-action.json'
        self.lock = threading.RLock()
        self.worker = None

    def status(self):
        with self.lock:
            operation = read_json(self.result_path, {})
            pending = operation.get('state') == 'waiting'
            if pending and (self.worker is not None and self.worker.poll() is not None
                            or time.time() - operation.get('started', 0) > 300):
                operation.update(state='failed', message='La modification n’a pas abouti. Réessayez et validez la demande Windows.')
                write_json(self.result_path, operation)
                pending = False
            result = {'base_url': f'http://{ADDRESS}:{PORT}/v1', 'subnet': SUBNET,
                      'model': 'qwen3.8-flash-next-iq4-xs', 'authentication': False,
                      'pending': pending, 'enabled': False, 'available': False, 'state': 'disabled'}
            try:
                actual = system_state()
                result['enabled'] = actual['mapping'] and actual['firewall']
                live = health('127.0.0.1', PORT, timeout=.5)
                if isinstance(live.get('model'), str):
                    result['model'] = live['model']
                result['available'] = bool(result['enabled'] and actual['listening'] and live.get('loaded'))
                if actual['conflict']:
                    result.update(state='conflict', message='Ce port est utilisé par une autre redirection. Consultez les réglages Windows.')
                elif result['enabled']:
                    result.update(state='enabled', message='Accès local activé.' if result['available'] else 'Accès local activé. Qwen est indisponible ; vérifiez le modèle dans Vue d’ensemble.')
                elif actual['mapping'] or actual['firewall']:
                    result.update(state='incomplete', message='Configuration locale incomplète. Activez l’accès pour la réparer ou coupez-le.')
                else:
                    result['message'] = 'Accès local coupé.'
                result['can_disable'] = actual['mapping'] or actual['firewall']
            except (OSError, ImportError, psutil.Error):
                result.update(state='unknown', message='État de l’accès local indisponible. Réessayez.', can_disable=False)
            if pending:
                result['message'] = 'Validation administrateur Windows en attente…'
            elif operation.get('state') == 'failed':
                result['error'] = operation.get('message', 'La modification de l’accès local a échoué. Réessayez.')
            return result

    def configure(self, enabled):
        if type(enabled) is not bool:
            raise ValueError('Choisissez d’activer ou de couper l’accès local.')
        with self.lock:
            state = self.status()
            if state['pending']:
                raise ValueError('Une modification est déjà en attente de validation Windows.')
            if state['state'] in ('unknown', 'conflict'):
                raise ValueError(state['message'])
            if enabled:
                port, model, key = self.backend()
                live = health('127.0.0.1', PORT, timeout=2)
                if port != PORT or key or live.get('service') != 'strata' or live.get('api_key') is not False or 'qwen' not in str(live.get('model', model)).lower():
                    raise ValueError('L’accès sans clé nécessite Qwen disponible sur le port local 8080, sans authentification.')
            if enabled == state['enabled'] and state['state'] in ('enabled', 'disabled'):
                return {'message': state['message']}
            operation = {'state': 'waiting', 'started': time.time(), 'request_id': uuid.uuid4().hex,
                         'target_enabled': enabled}
            write_json(self.result_path, operation)
            try:
                self.worker = subprocess.Popen([
                    'powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                    '-File', str(HOME / 'Configurer-Qwen-LAN.ps1'), '-Action', 'Activer' if enabled else 'Couper',
                    '-RequestId', operation['request_id'],
                ], creationflags=HIDDEN, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except OSError:
                operation.update(state='failed', message='Impossible de lancer la demande Windows. Réessayez.')
                write_json(self.result_path, operation)
                raise ValueError(operation['message']) from None
            return {'message': 'Validez la demande administrateur Windows pour ' + ('activer' if enabled else 'couper') + ' l’accès local.'}
