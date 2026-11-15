"""Round-trip both domains in independent processes and fresh databases."""
import json
import os
from pathlib import Path
import subprocess
import sys


CHILD = r'''
import json, sys
from pathlib import Path
from fastapi.testclient import TestClient
from app.db import init_db
from backend.app.db import init_db as init_erp
from app.main import app
init_db(); init_erp()
c = TestClient(app)
archive = Path(sys.argv[2])
if sys.argv[1] == 'export':
    b = c.post('/v1/projects', json={'code':'PORTABLE','name':'Portable'}).json()
    e = c.post('/api/v1/projects', json={'code':'PORTABLE','title':'Portable'}).json()
    assert c.put(f"/api/v1/projects/{e['id']}/brain", json={'brain_project_id':b['id']}).status_code == 200
    raw = b'From: audit@example.test\r\nSubject: PORTABLE\r\n\r\nTODO envoyer le rapport.'
    source = c.post('/v1/sources/upload-eml', files={'file':('a.eml', raw)}, data={'candidate_project_id':b['id']}).json()
    props = c.get('/v1/proposals').json()
    for prop in props:
        assert c.post(f"/v1/proposals/{prop['id']}/accept", json={'actor':'portable'}).status_code == 200
    assert c.post(f"/api/v1/projects/{e['id']}/cdc/sources/upload", files={'file':('cdc.txt',b'Preuve portable')}).status_code == 200
    data = c.get(f"/api/v1/projects/{e['id']}/export").json()
    assert data['brain']['knowledge_items'] and data['brain']['provenance_links']
    archive.write_text(json.dumps(data), encoding='utf-8')
else:
    data = json.loads(archive.read_text(encoding='utf-8'))
    result = c.post('/api/v1/projects/import-json', json={'data':data})
    assert result.status_code == 201, result.text
    eid = result.json()['id']
    link = c.get(f'/api/v1/projects/{eid}/brain').json()
    assert link['linked'] and link['brain_project_id'] != data['brain']['projects'][0]['id']
    items = c.get(f'/api/v1/projects/{eid}/brain/knowledge').json()
    assert len(items) == len(data['brain']['knowledge_items'])
    sources = c.get('/v1/sources?status=resolved').json()
    assert c.get(f"/v1/sources/{sources[0]['source_id']}/raw").content.endswith(b'envoyer le rapport.')
    pages_source = c.get(f'/api/v1/projects/{eid}/cdc/sources').json()[0]
    assert pages_source['analyzable']
    assert c.get('/health').status_code == 200
'''


def test_archive_includes_brain_and_restores_in_fresh_databases(tmp_path):
    archive = tmp_path / "project.json"
    for mode in ["export", "import"]:
        root = tmp_path / mode
        root.mkdir()
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith(("PB_", "MINIPILOT_"))}
        environment.update(PB_DATABASE_URL="sqlite:///" + (root / "brain.db").as_posix(),
                           PB_STORAGE_DIR=str(root / "storage"), MINIPILOT_HOME=str(root / "erp"),
                           PB_MEMORY_ENGINE="fake", AGENT_TESTING="1")
        completed = subprocess.run([sys.executable, "-c", CHILD, mode, str(archive)],
                                   cwd=Path(__file__).resolve().parents[1], env=environment,
                                   capture_output=True, text=True, timeout=60)
        assert completed.returncode == 0, completed.stdout + completed.stderr
    data = json.loads(archive.read_text(encoding="utf-8"))
    assert {entry["area"] for entry in data["files"]} == {"cdc", "raw"}
