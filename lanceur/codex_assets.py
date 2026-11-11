"""Authenticated, signed Codex setup resources, fetched by the desktop client."""
import base64
import hashlib
import io
import json
import zipfile
from core import ROOT, HOME
from signing import public, sign

FILES=('Installer-Codex-Kiara.ps1','Enregistrer-Cle-Codex-Kiara.ps1',
       'Lire-Cle-Codex-Kiara.ps1','qwen-models.json')


def catalogue(context=None):
    value=json.loads((ROOT/'maintenance/codex/qwen-models.json').read_bytes())
    if not isinstance(value,dict) or not isinstance(value.get('models'),list):raise ValueError('Catalogue Qwen invalide.')
    if context is not None:
        model=next((row for row in value['models'] if row.get('slug')=='fred-qwen'),None)
        if model is None:raise ValueError('Qwen absent du catalogue Codex.')
        model['context_window']=context
    return value


def payload(home=HOME, context=None):
    public(home,create=False)  # Never replace a missing production signing identity.
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for name in FILES:
            data=(json.dumps(catalogue(context),ensure_ascii=False).encode('utf-8') if name=='qwen-models.json'
                  else (ROOT/'maintenance/codex'/name).read_bytes())
            archive.writestr(zipfile.ZipInfo(name,date_time=(2026,11,3,0,0,0)),data)
        archive.writestr(zipfile.ZipInfo('manifest.json',date_time=(2026,11,3,0,0,0)),
                         json.dumps({'kind':'kiara-codex-setup','model':'fred-qwen','files':list(FILES)}).encode())
    data=output.getvalue()
    release=sign({'version':'1.0.2','protocol':4,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)},home)
    return {'release':release,'archive':base64.b64encode(data).decode('ascii')}
