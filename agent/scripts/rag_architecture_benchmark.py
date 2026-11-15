"""Evaluate grounded EG2 answers against fictional gold facts."""
import re
import unicodedata

def plain(text):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFD', text.lower())
                            if unicodedata.category(c) != 'Mn').split())

def grade(row):
    answer = row.get('response', {})
    text = plain(answer.get('answer', ''))
    missing = [p for p in row['patterns'] if not re.search(p, text)]
    quotes = answer.get('citations', [])
    available = {c['reference']: ' '.join(c['text'].split()) for c in row['context']}
    def exact_quote(c):
        if not isinstance(c, dict):
            return False
        # A known audit annotation is harmless; preserve strict-format compliance separately.
        ref = re.fullmatch(r'(P\d+)(?:\s+\[PREUVE:(?:A\d{2}|N\d{3})\])?', c.get('reference', ''))
        return bool(ref and ref[1] in available and len(c.get('quote', '').strip()) >= 15
                    and ' '.join(c['quote'].split()) in available[ref[1]])
    valid = bool(quotes) and all(exact_quote(c) for c in quotes)
    if row['unknown']:
        success = answer.get('answerable') is False and not row.get('error')
    else:
        success = not missing and answer.get('answerable') is True and valid and not row.get('error')
    return {'success': success, 'missing_concepts': missing, 'quotes_verbatim': valid,
            'concepts_and_quotes': not missing and valid and not row.get('error'),
            'references_strict_format': all(c.get('reference') in available for c in quotes),
            'review_note': 'Concepts et citations exactes automatiques ; relire le sens et les affirmations supplémentaires.'}
