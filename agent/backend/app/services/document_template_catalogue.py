"""Nonfinancial identification mappings; no database, file scan or Office launch."""
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path, PureWindowsPath
import re
from string import Formatter

CATALOGUE = Path(__file__).resolve().parents[1] / 'data/document_templates.json'
DOCUMENT_IDS = frozenset({'offer_lt_simple', 'tdao', 'tdsp', 'manufacturing_specification',
    'user_manual', 'ce_request', 'customer_satisfaction_product', 'customer_satisfaction_fixed_price'})
FIELD_KEYS = frozenset({'project_code', 'offer_number', 'client_name', 'client_reference', 'description',
    'equipment_number', 'client_responsible', 'client_requester', 'project_manager_trigram',
    'project_manager_first_name', 'project_manager_last_name', 'project_manager_email',
    'project_manager_phone', 'project_manager_full_name', 'agency_address', 'agency_postal_code',
    'agency_city', 'agency_phone', 'today'})
DOCUMENT_KEYS = frozenset({'id', 'label', 'format', 'folder_tokens', 'filename_tokens', 'preferred_version',
    'output_name', 'fields', 'sheet_name', 'cells', 'bookmarks', 'excluded_tokens', 'link_code', 'link_order', 'link_aliases'})


def _text(value, maximum=255):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or any(ord(char) < 32 for char in value):
        raise ValueError('Texte de catalogue invalide')
    return value


def _texts(value, maximum=50):
    if not isinstance(value, list) or len(value) > maximum or len(set(map(str, value))) != len(value):
        raise ValueError('Liste de catalogue invalide')
    return [_text(item) for item in value]


def _cell(value):
    match = re.fullmatch(r'([A-Z]{1,3})([1-9][0-9]{0,6})', _text(value, 16))
    if not match:
        raise ValueError('Cellule documentaire invalide')
    column = 0
    for char in match[1]:
        column = column * 26 + ord(char) - ord('A') + 1
    if column > 16384 or int(match[2]) > 1048576:
        raise ValueError('Cellule hors de la feuille Excel')


def validate_catalogue(value):
    """Reject ambiguous targets or unsupported fields before a fill is prepared."""
    if (not isinstance(value, dict) or set(value) != {'format', 'version', 'source', 'financial_calculations', 'fields', 'documents'}
            or value['format'] != 'agent-project-document-templates' or type(value['version']) is not int or value['version'] != 1
            or value['financial_calculations'] is not False):
        raise ValueError('Contrat de catalogue documentaire invalide')
    fields = value['fields']
    source = value['source']
    if (not isinstance(source, dict)
            or set(source) != {'repository', 'commit', 'path', 'sha256', 'extraction'}
            or source['repository'] != 'XPilot'
            or not isinstance(source['commit'], str) or not re.fullmatch(r'[0-9a-f]{40}', source['commit'])
            or not isinstance(source['sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', source['sha256'])
            or source['path'] != 'backend/app/services/document_filling.py'):
        raise ValueError('Provenance du catalogue invalide')
    _text(source['extraction'], 500)
    if not isinstance(fields, dict) or set(fields) != FIELD_KEYS:
        raise ValueError('Champs documentaires non financiers requis')
    for field in fields.values():
        if (not isinstance(field, dict) or set(field) != {'label', 'edit_scope'}
                or field['edit_scope'] is not None and (not isinstance(field['edit_scope'], str)
                    or field['edit_scope'] not in {'project', 'client', 'person', 'agency'})):
            raise ValueError('Description de champ invalide')
        _text(field['label'], 120)
    documents = value['documents']
    if not isinstance(documents, list) or len(documents) != 8:
        raise ValueError('Les huit trames distinctes sont requises')
    ids, links = set(), set()
    for item in documents:
        if not isinstance(item, dict) or set(item) != DOCUMENT_KEYS:
            raise ValueError('Définition documentaire invalide')
        if (not isinstance(item['id'], str) or item['id'] not in DOCUMENT_IDS or item['id'] in ids
                or not isinstance(item['format'], str) or item['format'] not in {'DOCX', 'DOCM', 'XLSX', 'XLSM'}):
            raise ValueError('Type documentaire inconnu ou répété')
        ids.add(item['id'])
        _text(item['label'])
        _text(item['link_code'], 64)
        if item['link_code'] in links or type(item['link_order']) is not int or not 0 <= item['link_order'] <= 10000:
            raise ValueError('Relation documentaire ambiguë')
        links.add(item['link_code'])
        if type(item['preferred_version']) is not int or item['preferred_version'] < 1:
            raise ValueError('Version préférée invalide')
        for key in ('folder_tokens', 'filename_tokens', 'excluded_tokens', 'link_aliases', 'fields'):
            _texts(item[key])
        if not set(item['fields']).issubset(FIELD_KEYS):
            raise ValueError('Champ documentaire interdit')
        if item['sheet_name'] is not None:
            _text(item['sheet_name'], 31)
        output = _text(item['output_name'])
        if PureWindowsPath(output).name != output or any(char in output for char in '<>:"/\\|?*'):
            raise ValueError('Nom de sortie simple requis')
        for _, field, specification, conversion in Formatter().parse(output):
            if field is not None and (field not in FIELD_KEYS or specification or conversion):
                raise ValueError('Substitution de nom de sortie interdite')
        if not output.endswith('.' + item['format'].lower()):
            raise ValueError('Extension de sortie incompatible')
        spreadsheet = item['format'] in {'XLSX', 'XLSM'}
        if item['bookmarks'] and spreadsheet or item['cells'] and not spreadsheet:
            raise ValueError('Cible de remplissage incompatible avec le format')
        for kind in ('cells', 'bookmarks'):
            mappings = item[kind]
            if not isinstance(mappings, list) or len(mappings) > 100:
                raise ValueError('Mappings documentaires invalides')
            targets = set()
            for mapping in mappings:
                if not isinstance(mapping, list) or len(mapping) != 2:
                    raise ValueError('Mapping documentaire invalide')
                target, field = mapping
                _text(target, 120)
                if not isinstance(field, str) or field not in FIELD_KEYS or target in targets:
                    raise ValueError('Cible répétée ou champ interdit')
                targets.add(target)
                if kind == 'cells':
                    _cell(target)
    if ids != DOCUMENT_IDS:
        raise ValueError('Catalogue documentaire incomplet')
    return deepcopy(value)


@lru_cache(maxsize=1)
def _loaded():
    return validate_catalogue(json.loads(CATALOGUE.read_text(encoding='utf-8')))


def catalogue():
    """Return an independent descriptor; a caller cannot mutate cached mappings."""
    return deepcopy(_loaded())


def document_spec(document_id):
    for item in _loaded()['documents']:
        if item['id'] == document_id:
            return deepcopy(item)
    raise ValueError('Trame documentaire inconnue')
