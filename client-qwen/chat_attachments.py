"""Bounded chat attachments; image sources never reference host paths or URLs."""
import base64
import re

MAX_FILE = 2 * 1024 * 1024
FILE_TYPES = ['txt', 'md', 'pdf', 'docx']
REASONING_EFFORTS = ['none', 'low', 'medium', 'high']
CANONICAL_REASONING_EFFORTS = ['none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max', 'ultra', 'on']

def normalize_reasoning(value):
    aliases={value:value for value in CANONICAL_REASONING_EFFORTS}
    aliases.update({'off':'none','disabled':'none','false':'none','maximum':'max'})
    if not isinstance(value,str) or value.strip().lower() not in aliases:
        raise ValueError('Niveau de réflexion invalide.')
    return aliases[value.strip().lower()]

def image_data(url):
    if not isinstance(url, str) or len(url) > MAX_FILE * 4 // 3 + 100:
        raise ValueError('Image limitée à 2 Mo.')
    head, separator, encoded = url.partition(',')
    signatures = {'data:image/png;base64': lambda b: b.startswith(b'\x89PNG\r\n\x1a\n'),
                  'data:image/jpeg;base64': lambda b: b.startswith(b'\xff\xd8\xff'),
                  'data:image/webp;base64': lambda b: b.startswith(b'RIFF') and b[8:12] == b'WEBP'}
    if not separator or head not in signatures:
        raise ValueError('Image PNG, JPEG ou WebP intégrée attendue.')
    try: raw = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError): raise ValueError('Image encodée invalide.') from None
    if not raw or len(raw) > MAX_FILE or not signatures[head](raw):
        raise ValueError('Image invalide ou supérieure à 2 Mo.')
    return len(raw)

def validate_parts(content, role):
    if not isinstance(content, list) or not 1 <= len(content) <= 32 or role != 'user':
        raise ValueError('Pièces jointes réservées aux messages utilisateur.')
    for part in content:
        if not isinstance(part, dict): raise ValueError('Contenu invalide.')
        if part.get('type') == 'text' and set(part) == {'type', 'text'} and isinstance(part['text'], str): continue
        if part.get('type') == 'image_url' and set(part) == {'type', 'image_url'}:
            source = part['image_url']
            if isinstance(source, dict) and set(source) <= {'url', 'detail'} and source.get('detail', 'auto') in ('auto', 'low', 'high'):
                image_data(source.get('url')); continue
        raise ValueError('Texte ou image intégrée attendus.')

def validate_message(message):
    if not isinstance(message, dict) or set(message) - {'role', 'content', 'reasoning_content', 'interrupted', 'attachments', 'turn_id'}:
        raise ValueError('Message invalide.')
    if message.get('role') not in ('user', 'assistant') or not isinstance(message.get('content'), str):
        raise ValueError('Message texte attendu.')
    if not isinstance(message.get('reasoning_content', ''), str) or type(message.get('interrupted', False)) is not bool:
        raise ValueError('État du message invalide.')
    if 'turn_id' in message and (not isinstance(message['turn_id'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', message['turn_id'])):
        raise ValueError('Identifiant du tour invalide.')
    items = message.get('attachments', [])
    if not isinstance(items, list) or len(items) > 4 or (items and message['role'] != 'user'):
        raise ValueError('Maximum quatre pièces jointes par message utilisateur.')
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get('name'), str) or not 1 <= len(item['name']) <= 180:
            raise ValueError('Nom de pièce jointe invalide.')
        if item.get('kind') == 'image' and set(item) == {'name', 'kind', 'url'}: image_data(item['url'])
        elif item.get('kind') == 'file' and set(item) == {'name', 'kind', 'text'} and isinstance(item['text'], str) and 1 <= len(item['text']) <= 50000: pass
        else: raise ValueError('Pièce jointe invalide.')
    return message

def capabilities(live):
    return {'images': live.get('images') is True, 'files': FILE_TYPES,
            'thinking': True, 'reasoning_efforts': REASONING_EFFORTS.copy(), 'max_file_bytes': MAX_FILE}
