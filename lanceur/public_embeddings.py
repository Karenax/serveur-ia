"""Bounded OpenAI-compatible embeddings; the private EG2 token stays on Fred."""
import base64
import struct

MODEL_ID = 'google/embeddinggemma-2'


def request(value):
    if not isinstance(value, dict) or set(value)-{'model','input','encoding_format','dimensions','user','input_type'}:
        raise ValueError('Paramètres embeddings invalides.')
    if value.get('model') != MODEL_ID:
        raise ValueError('Modèle embeddings attendu : '+MODEL_ID)
    texts=value.get('input')
    if isinstance(texts,str):texts=[texts]
    if not isinstance(texts,list) or not 1<=len(texts)<=8 or any(
            not isinstance(text,str) or not text.strip() or len(text)>4500 for text in texts):
        raise ValueError('Fournir un texte ou un lot de 1 à 8 textes, de 1 à 4500 caractères chacun.')
    encoding=value.get('encoding_format','float')
    if encoding not in ('float','base64') or type(value.get('dimensions',768)) is not int or value.get('dimensions',768)!=768:
        raise ValueError('Encodage float/base64 et dimensions 768 attendus.')
    mode=value.get('input_type','document')
    if mode not in ('document','query') or ('user' in value and (
            not isinstance(value['user'],str) or len(value['user'])>256)):
        raise ValueError('Type document/query ou identifiant utilisateur invalide.')
    return texts,encoding,mode


def catalogue(service):
    if service is None:return []
    status=service.status()
    if not status['enabled']:return []
    return [{'id':MODEL_ID,'object':'model','owned_by':'google','name':'EmbeddingGemma 2',
             'available':status['status']=='pret','capabilities':{'embedding':True,'dimensions':768}}]


def response(service,texts,encoding,mode):
    result=service.encode(texts,mode=mode,timeout=30,include_usage=True)
    vectors=result['vectors'];tokens=result['prompt_tokens']
    return {'object':'list','model':MODEL_ID,'data':[
        {'object':'embedding','index':index,'embedding':vector if encoding=='float' else
            base64.b64encode(struct.pack('<768f',*vector)).decode('ascii')}
        for index,vector in enumerate(vectors)],'usage':{'prompt_tokens':tokens,'total_tokens':tokens}}
