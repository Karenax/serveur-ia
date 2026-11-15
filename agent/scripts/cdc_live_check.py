"""Isolated CDC qualification with an explicitly supplied AI configuration."""
import argparse
import json
import os
from pathlib import Path
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ai-settings', type=Path, required=True, help='JSON IA explicitement fourni pour cet essai')
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    if output.exists() or output.is_relative_to(repo):
        parser.error('Dossier neuf et extérieur au dépôt requis')
    configuration = json.loads(args.ai_settings.read_text(encoding='utf-8'))
    if not configuration.get('enabled'):
        parser.error('Le profil de cet essai doit activer explicitement l’IA')
    output.mkdir(parents=True)
    os.environ.update(PB_DATABASE_URL='sqlite:///' + (output / 'brain.db').as_posix(),
                      PB_STORAGE_DIR=str(output / 'storage'), MINIPILOT_HOME=str(output / 'erp'),
                      PB_MEMORY_ENGINE='fake', AGENT_TESTING='1')
    sys.path.insert(0, str(repo))
    from fastapi.testclient import TestClient
    from app.db import init_db, SessionLocal
    from backend.app.db import init_db as init_erp
    from app.main import app
    from app.routers.settings import AISettings
    from app.services.settings_service import save_section
    configuration = AISettings.model_validate(configuration).model_dump()
    init_db()
    init_erp()
    with SessionLocal() as db:
        save_section(db, 'ai', configuration)
        save_section(db, 'mail', {'folder': str(output / 'empty-mail'), 'auto_scan': False})
    client = TestClient(app)
    project = client.post('/api/v1/projects', json={'code':'CDC-LIVE', 'title':'Corpus CDC isolé'}).json()
    fixture = repo / 'tests' / 'fixtures' / 'cdc_demo.txt'
    upload = client.post(f"/api/v1/projects/{project['id']}/cdc/sources/upload",
                         files={'file':(fixture.name,fixture.read_bytes(),'text/plain')})
    upload.raise_for_status()
    started = time.perf_counter()
    response = client.post(f"/api/v1/projects/{project['id']}/cdc/analyze",
                           json={'source_id':upload.json()['source_id'], 'pages_per_batch':2, 'max_tokens':4000})
    items = client.get(f"/api/v1/projects/{project['id']}/cdc/items").json()
    result = {'status_code':response.status_code, 'duration_seconds':time.perf_counter()-started,
              'model':configuration['model'], 'provider':configuration['provider'],
              'analysis':response.json(), 'items':items,
              'passed':response.status_code == 200 and bool(items) and all(i['evidence'] for i in items),
              'scope':'Synthetic CDC only; does not qualify EG2, OCR or production documents'}
    (output / 'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('analysis','items')},indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
