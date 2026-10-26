"""Shared validation of signed client transport profiles."""
import base64
import ipaddress
import re

def validate_endpoint(value):
    if not isinstance(value,str) or len(value)>300:
        raise ValueError('Adresse attendue : IP-ou-DNS:port, par exemple 192.168.1.40:51820.')
    value=value.strip()
    try:
        host,port=value.rsplit(':',1)
        if not port.isdecimal() or not 1<=int(port)<=65535:
            raise ValueError()
        if host.startswith('[') and host.endswith(']'):
            address=ipaddress.ip_address(host[1:-1])
            if address.version!=6:raise ValueError()
        elif not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?',host):
            raise ValueError()
        elif ':' in host:
            raise ValueError()
    except (ValueError,TypeError):
        raise ValueError('Adresse attendue : IP-ou-DNS:port, sans http:// ni chemin /v1.')
    return host+':'+str(int(port))

def validate_profile(profile):
    if not isinstance(profile,dict):raise ValueError('Profil client invalide.')
    if profile.get('url')!='wireguard://10.77.0.1:8766':raise ValueError('Adresse API privée invalide.')
    if profile.get('protocol', 1) not in (1, 2, 3, 4):
        raise ValueError('Ce profil nécessite une version plus récente d’Accès serveur Kiara.')
    if profile.get('transport') != 'wireguard':
        raise ValueError('Cet accès doit utiliser WireGuard.')
    if not isinstance(profile.get('token'),str) or not re.fullmatch(r'qwen_[0-9a-f]{16}_[A-Za-z0-9_-]{43}',profile['token']):
        raise ValueError('Clé API serveur invalide.')
    wg = profile.get('wireguard')
    if not isinstance(wg,dict):
        raise ValueError('Profil WireGuard absent.')
    for field in ('private_key','server_public_key','preshared_key'):
        try:
            value=base64.b64decode(wg[field],validate=True)
            if len(value)!=32: raise ValueError()
        except (KeyError,TypeError,ValueError):
            raise ValueError('Clé WireGuard invalide.')
    try:
        address=ipaddress.ip_interface(wg['address'])
        if address.network.prefixlen!=32 or address.ip not in ipaddress.ip_network('10.77.0.0/24') or int(str(address.ip).split('.')[-1]) not in range(2,255):
            raise ValueError()
        validate_endpoint(wg['endpoint'])
    except (KeyError,TypeError,ValueError):
        raise ValueError('Adresse du tunnel ou du serveur invalide.')
    routes=profile.get('local_routes',[])
    if not isinstance(routes,list) or len(routes)>16:
        raise ValueError('Adresses locales du serveur invalides.')
    try:
        for route in routes:
            endpoint=validate_endpoint(route['endpoint'])
            host,_=endpoint.rsplit(':',1)
            address=ipaddress.ip_address(host)
            network=ipaddress.ip_network(route['network'])
            if address.version!=4 or not address.is_private or address.is_loopback or address not in network:
                raise ValueError()
    except (ValueError,TypeError,KeyError):
        raise ValueError('Adresses locales du serveur invalides.')
    return profile
