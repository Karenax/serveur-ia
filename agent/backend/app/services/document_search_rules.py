"""Pure, bounded word/folder matching rules, without database or network I/O."""
from dataclasses import dataclass
import re
import unicodedata
from .document_paths import _relative
from .document_template_catalogue import document_spec


def fold(value):
    text = ''.join(char for char in unicodedata.normalize('NFKD', value.casefold())
                   if not unicodedata.combining(char))
    return ' '.join(re.findall('[a-z0-9]+', text))


def phrase(value, pattern):
    words = set(fold(value).split())
    expected = fold(pattern).split()
    return bool(expected) and all(word in words for word in expected)


@dataclass(frozen=True)
class SearchRule:
    document_id: str
    relative_paths: tuple[str, ...]
    filename_patterns: tuple[str, ...]
    excluded_tokens: tuple[str, ...] = ()
    preferred_version: int | None = None

    def __post_init__(self):
        document_spec(self.document_id)
        for values in (self.relative_paths, self.filename_patterns, self.excluded_tokens):
            if not isinstance(values, tuple) or len(values) > 16:
                raise ValueError('Au plus 16 critères immuables par liste')
            if any(not isinstance(value, str) or not 1 <= len(value) <= 256
                   or any(ord(char) < 32 for char in value) for value in values):
                raise ValueError('Critère documentaire invalide')
        if not self.relative_paths or not self.filename_patterns:
            raise ValueError('Emplacements et motifs de nom requis')
        for path in self.relative_paths:
            _relative(path)
        if any(not fold(value) for value in (*self.filename_patterns, *self.excluded_tokens)):
            raise ValueError('Au moins un mot ou chiffre par motif')
        if self.preferred_version is not None and (type(self.preferred_version) is not int
                                                  or not 0 <= self.preferred_version <= 999):
            raise ValueError('Indice préféré entre 0 et 999 requis')


def default_rule(document_id):
    spec = document_spec(document_id)
    return SearchRule(document_id, ('/'.join(spec['folder_tokens']),),
                      (' '.join(spec['filename_tokens']),), tuple(spec['excluded_tokens']), spec['preferred_version'])


