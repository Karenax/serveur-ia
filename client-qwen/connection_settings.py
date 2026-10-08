"""Portable server address settings for an existing personal client access."""
import json
import re
from wg_bridge import validate_endpoint

FORMAT='acces-serveur-fred-connection'
HTTPS_ENDPOINT='https://ia.karenax.net'

def validate_connection_endpoint(value):
    # The personal token may only leave WireGuard for our explicitly trusted origin.
    if isinstance(value,str) and value.strip().lower().startswith('https://'):
        if value.strip().lower().rstrip('/') != HTTPS_ENDPOINT:
            raise ValueError('L’accès HTTPS autorisé est https://ia.karenax.net.')
        return HTTPS_ENDPOINT
    return validate_endpoint(value)

def protocol(endpoint):
    return 'HTTPS' if validate_connection_endpoint(endpoint)==HTTPS_ENDPOINT else 'UDP'


def parse(value):
    if not isinstance(value,str) or len(value)>2048:
        raise ValueError('Collez une adresse IP-ou-DNS:port ou les paramètres de connexion copiés.')
    value=value.strip()
    if value.startswith('{'):
        try:settings=json.loads(value)
        except ValueError as error:raise ValueError('Paramètres de connexion JSON illisibles.') from error
        if (not isinstance(settings,dict) or set(settings)!={'format','version','protocol','endpoint'}
                or settings.get('format')!=FORMAT or type(settings.get('version')) is not int
                or settings['version']!=1 or settings.get('protocol') not in ('UDP','HTTPS')):
            raise ValueError('Paramètres de connexion incompatibles. Copiez-les depuis Accès serveur Fred.')
        value=settings['endpoint']
        if protocol(value)!=settings['protocol']:
            raise ValueError('Le protocole ne correspond pas à l’adresse.')
    elif value.upper().endswith('/ UDP'):
        value=re.sub(r'\s*/\s*UDP\s*$','',value,flags=re.I).strip()
    return validate_connection_endpoint(value)


def export(endpoint):
    return {'format':FORMAT,'version':1,'protocol':protocol(endpoint),'endpoint':validate_connection_endpoint(endpoint)}
