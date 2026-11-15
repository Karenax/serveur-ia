"""Pure common preferences validation, independent from runtime stores."""
from fastapi import HTTPException
from pydantic import ValidationError
from ..project_document_form_schemas import DocumentSearchSave
from .document_paths import _relative
from .document_search_rules import SearchRule, default_rule
from .document_template_catalogue import DOCUMENT_IDS, catalogue, document_spec


def default_preferences():
    result = []
    for spec in catalogue()['documents']:
        rule = default_rule(spec['id'])
        result.append({'document_id': spec['id'], 'label': spec['label'], 'format': spec['format'],
                       'relative_paths': list(rule.relative_paths), 'filename_patterns': list(rule.filename_patterns),
                       'excluded_tokens': list(rule.excluded_tokens), 'preferred_version': rule.preferred_version,
                       'active': True, 'order': spec['link_order']})
    return result


def _items(values):
    try:
        command = DocumentSearchSave(expected_revision=0, items=values)
    except (ValidationError, TypeError) as exc:
        raise HTTPException(422, 'Préférences documentaires invalides') from exc
    items = [item.model_dump() for item in command.items]
    if {item['document_id'] for item in items} != DOCUMENT_IDS:
        raise HTTPException(422, 'Les huit documents distincts sont requis')
    for item in items:
        if item['format'] != document_spec(item['document_id'])['format']:
            raise HTTPException(422, 'Le format de la trame auditée est immuable')
        for key in ('relative_paths', 'filename_patterns', 'excluded_tokens'):
            if any(not 1 <= len(value) <= 256 or any(ord(char) < 32 for char in value) for value in item[key]):
                raise HTTPException(422, 'Critère documentaire invalide')
        item['relative_paths'] = [_relative(value) or '.' for value in item['relative_paths']]
        try:
            # Inactive preferences may have no criteria. Use placeholders only
            # for validation, never for discovery or in the saved JSON.
            SearchRule(item['document_id'], tuple(item['relative_paths']) or ('.',),
                       tuple(item['filename_patterns']) or ('inactive',), tuple(item['excluded_tokens']),
                       item['preferred_version'])
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        if item['active'] and (not item['relative_paths'] or not item['filename_patterns']):
            raise HTTPException(422, 'Critères requis pour un document actif')
    return sorted(items, key=lambda item: (item['order'], item['document_id']))


