"""Readable model identities for Hermes' id-only desktop picker."""
import copy
import hashlib
import re
import unicodedata


def catalogue(source):
    rows=[]
    for row in source.get('data',[]):
        if not isinstance(row,dict) or not row.get('id') or not row.get('available',True):continue
        if (row.get('capabilities') or {}).get('embedding'):continue
        label=row.get('name') or row.get('label') or row['id']
        # Hermes formats the last slash-separated component of the id itself.
        name=unicodedata.normalize('NFKD',label).encode('ascii','ignore').decode()
        slug=re.sub(r'[^a-z0-9.]+','-',name.lower()).strip('-')[:180] or 'modele'
        rows.append((row,slug))
    result=[];mapping={}
    for row,slug in rows:
        # The prefix keeps identities unique and stable even for identical names.
        # Hermes renders only the readable final component.
        alias='fred-'+hashlib.sha256(row['id'].encode()).hexdigest()[:12]+'/'+slug
        entry=copy.deepcopy(row);entry['id']=alias
        result.append(entry);mapping[alias]=row['id']
    default=next((alias for alias,native in mapping.items() if native==source.get('default_model')),None)
    return {'object':'list','data':result,'default_model':default},mapping
