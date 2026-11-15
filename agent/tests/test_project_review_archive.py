"""Typed v6 transport: fictional paired stores, preserved publications and audio."""
from copy import deepcopy
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db import Base as BrainBase
from app.db_support import backup_sqlite, configure_sqlite
from app.models import MeetingRecording, Source, SourceArtifact
from backend.app.db import Base
from backend.app.project_identity_schemas import IdentityPatch, PersonPatch
from backend.app.project_review_models import ProjectReview, ReviewPublication
from backend.app.services import project_archive as archive, project_identity as identity
from backend.app.services.migration_guard import capture_baseline, compare_baseline
from backend.app.services.project_planning_migration import install_planning_schema
from backend.app.services.project_deliverable_migration import install_deliverable_schema
from backend.app.services.project_review_migration import install_review_schema
from tests import test_project_review_archive_contract as contract_fixtures
from tests.test_project_reviews import transaction

store = contract_fixtures.store
audio = contract_fixtures.audio
envelope = contract_fixtures.envelope
l3_store = contract_fixtures.l3_store
typed_document = contract_fixtures.typed_document


@pytest.fixture
def transport(envelope, store, audio, tmp_path, monkeypatch):
    import app.db
    import app.config
    import backend.app.db
    # Upgrade only fictional stores and normalize the direct-ORM person fixture
    # using the actual L1 service before exercising reference reconciliation.
    with transaction(store[0]) as db:
        row = db.execute(select(Base.metadata.tables['project_people'])).mappings().one()
        identity.patch_person(db, row['id'], PersonPatch(expected_revision=row['revision'], first_name=row['first_name']))
        identity.patch_identity(db, store[1]['project'], IdentityPatch(expected_revision=0, responsible_id=row['id']))
    for install,name in ((install_planning_schema,'planning'), (install_deliverable_schema,'deliverables')):
        install(store[0].kw['bind'], backup=lambda n=name:backup_sqlite(store[2], tmp_path / ('before-'+n+'.db')))
    # Retain a real accepted historical transcription alongside its recording.
    with transaction(audio[0]) as db:
        recording = db.get(MeetingRecording, audio[1])
        db.add(SourceArtifact(source_id=recording.source_id, kind='transcription', content_text='Transcription originale',
            content_json={'recording_id':recording.id, 'revision':recording.revision,
                          'segments':recording.segments, 'speaker_names':recording.speaker_names}))
    monkeypatch.setattr(app.db, 'SessionLocal', audio[0])
    source_root, target_root = tmp_path / 'source-files', tmp_path / 'target-files'
    monkeypatch.setattr(backend.app.db, 'APP_DIR', source_root)
    monkeypatch.setattr(app.config, 'RAW_DIR', source_root / 'raw')
    raw = b'RIFF fictional original recording bytes'
    digest = hashlib.sha256(raw).hexdigest()
    raw_path = source_root / 'raw' / (digest + '.wav')
    raw_path.parent.mkdir(parents=True)
    raw_path.write_bytes(raw)
    with transaction(audio[0]) as db:
        source = db.query(Source).one()
        source.sha256 = digest
        source.original_uri = str(raw_path)
        source.source_metadata = {'raw_path':str(raw_path)}
    with store[0]() as db:
        data = archive.export_archive(db, store[1]['project'])
    assert data['version']==6
    erp_path, brain_path = tmp_path / 'target-erp.db', tmp_path / 'target-brain.db'
    erp = create_engine(f'sqlite:///{erp_path}')
    brain = create_engine(f'sqlite:///{brain_path}')
    configure_sqlite(erp)
    configure_sqlite(brain)
    Base.metadata.create_all(erp)
    BrainBase.metadata.create_all(brain)
    for install,name in ((install_planning_schema,'planning'), (install_deliverable_schema,'deliverables'), (install_review_schema,'reviews')):
        install(erp, backup=lambda n=name:backup_sqlite(erp_path, tmp_path / ('target-before-'+n+'.db')))
    target = sessionmaker(bind=erp, autoflush=False)
    target_brain = sessionmaker(bind=brain, autoflush=False)
    monkeypatch.setattr(app.db, 'SessionLocal', target_brain)
    monkeypatch.setattr(backend.app.db, 'APP_DIR', target_root)
    monkeypatch.setattr(app.config, 'RAW_DIR', target_root / 'raw')
    yield data, target, target_brain, erp_path, brain_path, target_root
    erp.dispose()
    brain.dispose()


def restore(factory, data, code='COPIE-0205'):
    with factory() as db:
        return archive.import_archive(db, data, code)


def test_populated_catalogue_is_preserved_locally_and_explicitly_outside_legacy_archive(
        transport, store, audio, monkeypatch):
    import app.db
    import app.config
    import backend.app.db
    from uuid import uuid4
    from app.source_library_models import LibraryItem, LibraryVersion, LIBRARY_TABLES
    data, _, _, _, _, _ = transport
    BrainBase.metadata.create_all(audio[0].kw['bind'], tables=list(LIBRARY_TABLES))
    with transaction(audio[0]) as db:
        source = db.query(Source).one()
        item = LibraryItem(project_id=source.project_id, provider='fixture', provider_key='fictitious-original',
            title='Catalogue conservé', current_source_id=source.id, labels=['fictif'])
        db.add(item)
        db.flush()
        db.add(LibraryVersion(id=str(uuid4()), item_id=item.id, source_id=source.id,
            content_sha256=source.sha256, size_bytes=Path(source.original_uri).stat().st_size,
            provenance={'kind': 'fictional-preservation-test'}))
        original_path = Path(source.original_uri)
    monkeypatch.setattr(app.db, 'SessionLocal', audio[0])
    monkeypatch.setattr(app.config, 'RAW_DIR', original_path.parent)
    monkeypatch.setattr(backend.app.db, 'APP_DIR', original_path.parent.parent)
    before = capture_baseline(store[2]), capture_baseline(audio[2])
    with store[0]() as db:
        exported = archive.export_archive(db, store[1]['project'])
    assert exported['version'] == 6
    assert not any(name.startswith('foresight_') for name in exported['brain'])
    assert exported['brain']['sources'] == data['brain']['sources']
    assert exported['brain']['source_artifacts'] == data['brain']['source_artifacts']
    assert exported['files'] == data['files']
    assert any('catalogue' in warning and 'sauvegarde globale coordonnée' in warning for warning in exported['warnings'])
    assert (capture_baseline(store[2]), capture_baseline(audio[2])) == before
    with audio[0]() as db:
        assert db.query(LibraryItem).count() == db.query(LibraryVersion).count() == 1
    with pytest.raises(HTTPException) as caught:
        archive._validate_tables(BrainBase.metadata, {**exported['brain'], 'foresight_library_items': []})
    assert caught.value.status_code == 400 and 'Table inconnue' in caught.value.detail


def test_v6_paired_roundtrip_keeps_frozen_bytes_and_remaps_material_links(transport, store, audio):
    data, target, brain, erp_path, brain_path, _ = transport
    original = deepcopy(data)
    before = capture_baseline(store[2]), capture_baseline(audio[2])
    target_before = capture_baseline(erp_path), capture_baseline(brain_path)
    result = restore(target, data)
    assert result['version']==6 and data==original
    assert (capture_baseline(store[2]), capture_baseline(audio[2]))==before
    with target() as db:
        published = db.query(ReviewPublication).one()
        original_publication = data['tables']['project_review_publications'][0]
        for key in ('snapshot','sha256','pdf_base64','pdf_sha256'):
            assert getattr(published,key)==original_publication[key]
        assert published.bindings['erp'][store[1]['project']]==result['id']
        current = db.get(ProjectReview, published.review_id)
        assert current.content['notes'].startswith(store[1]['project'])
        proof = next(iter(current.provenance.values()))
        assert proof['erp_project_id']==result['id'] and proof['recording_id']!=audio[1]
        second = archive.export_archive(db, result['id'])
        assert second['version']==6
    with brain() as db:
        recording = db.query(MeetingRecording).one()
        artifact = db.query(SourceArtifact).one()
        assert artifact.content_json['recording_id']==recording.id==proof['recording_id']
        assert recording.erp_project_id==result['id']
    assert compare_baseline(target_before[0], capture_baseline(erp_path))['preserved']
    assert compare_baseline(target_before[1], capture_baseline(brain_path))['preserved']
    assert brain_path.is_file()


def test_second_restore_has_flat_original_bindings_and_exact_pdf(transport, tmp_path, monkeypatch):
    import json
    from backend.app.models import NetworkLink

    client_root = tmp_path / 'clients'
    client_root.mkdir()
    monkeypatch.setenv('AGENT_DOCUMENT_PROJECT_ROOT', json.dumps(str(client_root)))
    data, target, _, _, _, _ = transport
    first = restore(target, data)
    with target() as db:
        second_archive = archive.export_archive(db, first['id'])
    second = restore(target, second_archive, 'COPIE-0306')
    with target() as db:
        for result in (first, second):
            folder = client_root / result['id']
            link = db.query(NetworkLink).filter_by(project_id=result['id'], code='dossier_client_kiara').one()
            assert folder.is_dir() and link.chemin == str(folder)
        publications = db.query(ReviewPublication).order_by(ReviewPublication.created_at).all()
        assert len(publications)==2
        assert publications[0].snapshot==publications[1].snapshot and publications[0].pdf_base64==publications[1].pdf_base64
        restored = next(row for row in publications if row.project_id==second['id'])
        assert restored.bindings['erp'][data['project']['id']]==second['id']
        assert all(isinstance(value,str) for space in restored.bindings.values() for value in space.values())


def test_same_store_reuse_clones_transcription_and_later_edit_keeps_old_frozen_proof(transport, store, audio, monkeypatch):
    import app.db
    import app.config
    data, *_ = transport
    monkeypatch.setattr(app.db,'SessionLocal',audio[0])
    monkeypatch.setattr(app.config,'RAW_DIR',Path(data['brain']['sources'][0]['original_uri']).parent)
    before_erp, before_brain = capture_baseline(store[2]), capture_baseline(audio[2])
    result = restore(store[0], data)
    assert compare_baseline(before_erp, capture_baseline(store[2]))['preserved']
    assert compare_baseline(before_brain, capture_baseline(audio[2]))['preserved']
    with transaction(audio[0]) as db:
        recording = db.query(MeetingRecording).filter_by(erp_project_id=result['id']).one()
        artifact = db.query(SourceArtifact).filter(SourceArtifact.content_json['recording_id'].as_string()==recording.id).one()
        assert artifact.content_json['revision']==3
        changed = deepcopy(recording.segments)
        changed[0]['text']='Transcription corrigée ultérieurement'
        recording.segments=changed
        recording.revision=4
    with store[0]() as db:
        second = archive.export_archive(db,result['id'])
    # Export validates the old frozen revision through its cloned artifact.
    assert second['brain']['meeting_recordings'][0]['revision']==4
    assert json.loads(second['tables']['project_review_publications'][0]['snapshot'])==json.loads(data['tables']['project_review_publications'][0]['snapshot'])


@pytest.mark.parametrize('stage',['brain','erp','before_commit'])
def test_failure_after_insertion_rolls_back_both_real_store_files(transport, monkeypatch, stage):
    data, target, brain, erp_path, brain_path, _ = transport
    before = capture_baseline(erp_path), capture_baseline(brain_path)
    original = archive._insert
    def injected(db, metadata, tables, *args, **kwargs):
        original(db,metadata,tables,*args,**kwargs)
        if ((stage=='brain' and metadata is BrainBase.metadata and tables.get('projects'))
                or (stage in {'erp','before_commit'} and metadata is Base.metadata and tables.get('projects'))):
            raise RuntimeError('Injected '+stage)
    monkeypatch.setattr(archive,'_insert',injected)
    with pytest.raises(HTTPException) as error:
        restore(target,data)
    assert error.value.status_code==409
    assert (capture_baseline(erp_path),capture_baseline(brain_path))==before
    from backend.app.services.project_archive_files import inspect_preparation
    directory = next((transport[-1] / 'backups' / 'archive-imports').iterdir())
    with target() as db, brain() as canonical:
        assert inspect_preparation(db,directory,canonical)['sql_state']=='not_committed'
    prepared = json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    assert prepared['files'] and all(Path(item['path']).is_file() for item in prepared['files'])


@pytest.mark.parametrize('kind',['pdf','source','historical_person','event','envelope'])
def test_invalid_archive_rejected_without_target_changes(transport, kind):
    data, target, _, erp_path, brain_path, _ = transport
    data=deepcopy(data)
    if kind=='pdf':
        data['tables']['project_review_publications'][0]['pdf_sha256']='0'*64
    elif kind=='source':
        data['brain']['sources']=[]
    elif kind=='historical_person':
        data['references']['project_people']=[]
    elif kind=='event':
        data['tables']['project_review_events']=data['tables']['project_review_events'][1:]
    else:
        data['invented']=True
    before=capture_baseline(erp_path),capture_baseline(brain_path)
    with pytest.raises(HTTPException) as error:
        restore(target,data)
    assert error.value.status_code==400
    assert (capture_baseline(erp_path),capture_baseline(brain_path))==before


@pytest.mark.parametrize('kind',['missing','content','source_hash'])
def test_raw_media_binding_rejects_missing_or_changed_bytes(transport, kind):
    data,target,_,erp_path,brain_path,_=transport
    data=deepcopy(data)
    entry=next(row for row in data['files'] if row['area']=='raw')
    if kind=='missing':
        data['files']=[]
    elif kind=='content':
        entry['data']=base64.b64encode(b'changed media').decode('ascii')
        entry['sha256']=hashlib.sha256(b'changed media').hexdigest()
    else:
        data['brain']['sources'][0]['sha256']='f'*64
    before=capture_baseline(erp_path),capture_baseline(brain_path)
    with pytest.raises(HTTPException) as error:
        restore(target,data)
    assert error.value.status_code==400
    assert (capture_baseline(erp_path),capture_baseline(brain_path))==before


def test_export_refuses_missing_or_changed_declared_media(transport, store, audio, monkeypatch):
    import app.db
    import app.config
    from pathlib import Path
    data,*_=transport
    monkeypatch.setattr(app.db,'SessionLocal',audio[0])
    source=data['brain']['sources'][0]
    path=Path(source['original_uri'])
    monkeypatch.setattr(app.config,'RAW_DIR',path.parent)
    path.write_bytes(b'changed')
    with store[0]() as db, pytest.raises(HTTPException) as error:
        archive.export_archive(db,store[1]['project'])
    assert error.value.status_code==409
    # Rename our own fictional media, preserving all bytes for the missing case.
    path.rename(path.with_suffix('.kept'))
    with store[0]() as db, pytest.raises(HTTPException) as error:
        archive.export_archive(db,store[1]['project'])
    assert error.value.status_code==409


@pytest.mark.parametrize('method',['export','import'])
def test_embedded_pdf_and_json_count_toward_total_bound(transport, store, audio, monkeypatch, method):
    import app.db
    from backend.app.services.project_review_archive import embedded_bytes
    data,target,_,erp_path,brain_path,_=transport
    monkeypatch.setattr(archive,'MAX_ARCHIVE_BYTES',embedded_bytes(data['tables'])-1)
    before=capture_baseline(erp_path),capture_baseline(brain_path)
    if method=='export':
        monkeypatch.setattr(app.db,'SessionLocal',audio[0])
        with store[0]() as db, pytest.raises(HTTPException) as error:
            archive.export_archive(db,store[1]['project'])
    else:
        with pytest.raises(HTTPException) as error:
            restore(target,data)
    assert error.value.status_code==413
    assert (capture_baseline(erp_path),capture_baseline(brain_path))==before


def test_sql_commit_failure_preserves_both_stores_and_preparation(transport):
    from sqlalchemy import event
    from backend.app.services.project_archive_files import inspect_preparation
    data,target,brain,erp_path,brain_path,root=transport
    before=capture_baseline(erp_path),capture_baseline(brain_path)
    def fail(connection):
        if connection.connection.driver_connection.in_transaction:
            raise RuntimeError('Injected commit failure')
    engine=target.kw['bind']
    event.listen(engine,'commit',fail)
    try:
        with pytest.raises(HTTPException) as error:
            restore(target,data)
        assert error.value.status_code==409 and 'journal' in error.value.detail
    finally:
        event.remove(engine,'commit',fail)
    assert (capture_baseline(erp_path),capture_baseline(brain_path))==before
    directory=next((root/'backups'/'archive-imports').iterdir())
    with target() as db, brain() as canonical:
        assert inspect_preparation(db,directory,canonical)['sql_state']=='not_committed'


def test_commit_can_be_reconciled_without_final_log_marker(transport, monkeypatch):
    from backend.app.services.project_archive_files import PreparedFiles, inspect_preparation
    data,target,brain,_,_,root=transport
    monkeypatch.setattr(PreparedFiles,'outcome',lambda *_:None)
    result=restore(target,data)
    directory=root/'backups'/'archive-imports'/result['id']
    assert 'sql_committed' not in (directory/'events.ndjson').read_text(encoding='utf-8')
    with target() as db, brain() as canonical:
        assert inspect_preparation(db,directory,canonical)['sql_state']=='committed'


def test_v6_private_import_cannot_bypass_coordinated_transaction(transport):
    data,target,*_=transport
    with target() as db, pytest.raises(HTTPException) as error:
        archive._import_archive(db,data)
    assert error.value.status_code==409


def test_reordered_review_chain_and_events_restore(transport):
    data,target,*_=transport
    data=deepcopy(data)
    for name in ('project_reviews','project_review_publications','project_review_events','project_planning_changes'):
        data['tables'][name].reverse()
    result=restore(target,data)
    with target() as db:
        assert archive.export_archive(db,result['id'])['version']==6


def test_same_uuid_in_erp_and_brain_has_independent_namespace(transport):
    data,target,*_=transport
    data=deepcopy(data)
    erp={row['id']:row['id'] for group in ('tables','references','deliverable_references')
         for rows in data[group].values() for row in rows if row.get('id')}
    brain={row['id']:row['id'] for rows in data['brain'].values() for row in rows if row.get('id')}
    brain[data['brain']['projects'][0]['id']]=data['project']['id']
    remapped=contract_fixtures.remap({key:data[key] for key in ('tables','references','deliverable_references','brain')},erp,brain)
    data.update(remapped)
    for link in data['tables']['brain_links']:
        link['brain_project_id']=data['project']['id']
    result=restore(target,data)
    with target() as db:
        again=archive.export_archive(db,result['id'])
        assert again['brain']['projects'][0]['id']!=result['id']
        proof=next(iter(again['tables']['project_reviews'][0]['provenance'].values()))
        assert proof['erp_project_id']==result['id']
        assert proof['brain_project_id']==again['brain']['projects'][0]['id']


def test_changed_reused_historical_artifact_refuses_import_without_more_changes(transport, store, audio, monkeypatch):
    import app.db
    data,*_=transport
    monkeypatch.setattr(app.db,'SessionLocal',audio[0])
    with transaction(audio[0]) as db:
        db.query(SourceArtifact).one().content_text='changed accepted transcription'
    before=capture_baseline(store[2]),capture_baseline(audio[2])
    with pytest.raises(HTTPException) as error:
        restore(store[0],data)
    assert error.value.status_code==409
    assert (capture_baseline(store[2]),capture_baseline(audio[2]))==before


def test_existing_raw_piece_is_never_overwritten(transport):
    data,target,_,erp_path,brain_path,root=transport
    entry=next(row for row in data['files'] if row['area']=='raw')
    path=root/'raw'/(entry['sha256']+'.bin')
    path.parent.mkdir(parents=True)
    path.write_bytes(b'preexisting different bytes')
    before=capture_baseline(erp_path),capture_baseline(brain_path)
    with pytest.raises(HTTPException) as error:
        restore(target,data)
    assert error.value.status_code==409 and path.read_bytes()==b'preexisting different bytes'
    assert (capture_baseline(erp_path),capture_baseline(brain_path))==before


def test_file_sync_failure_retains_evidence_and_rolls_back_sql(transport, monkeypatch):
    from backend.app.services import project_archive_files as storage
    data,target,brain,erp_path,brain_path,root=transport
    before=capture_baseline(erp_path),capture_baseline(brain_path)
    original=storage._write_new
    def fail(path,content):
        original(path,content)
        if path.suffix=='.bin':
            raise OSError('Injected media sync failure')
    monkeypatch.setattr(storage,'_write_new',fail)
    with pytest.raises(HTTPException) as error:
        restore(target,data)
    assert error.value.status_code==409 and 'journal' in error.value.detail
    assert (capture_baseline(erp_path),capture_baseline(brain_path))==before
    directory=next((root/'backups'/'archive-imports').iterdir())
    with target() as db,brain() as canonical:
        assert storage.inspect_preparation(db,directory,canonical)['sql_state']=='not_committed'


@pytest.mark.parametrize('stage',['files_ready','both_sql_writes','after_sql_commit'])
def test_process_interruption_during_real_transport_is_reconciled(transport, tmp_path, stage):
    from backend.app.services.project_archive_files import inspect_preparation
    data,target,brain,erp_path,brain_path,root=transport
    before=capture_baseline(erp_path),capture_baseline(brain_path)
    payload=tmp_path/'payload.json'
    payload.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
    script=tmp_path/'interrupt-transport.py'
    script.write_text('''import json, os, sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db_support import configure_sqlite
import app.db, app.config, backend.app.db
from backend.app.services import project_archive as archive
from backend.app.services.project_archive_files import PreparedFiles
erp=create_engine(sys.argv[1]); brain=create_engine(sys.argv[2])
configure_sqlite(erp); configure_sqlite(brain)
app.db.SessionLocal=sessionmaker(bind=brain,autoflush=False)
root=Path(sys.argv[3]); backend.app.db.APP_DIR=root; app.config.RAW_DIR=root/'raw'
stage=sys.argv[5]
if stage=='files_ready':
    original=PreparedFiles.prepare
    def fail(self):
        original(self); os._exit(37)
    PreparedFiles.prepare=fail
elif stage=='both_sql_writes':
    original=archive._insert
    def fail(db,metadata,tables,*args,**kwargs):
        original(db,metadata,tables,*args,**kwargs)
        if metadata is backend.app.db.Base.metadata and tables.get('projects'): os._exit(37)
    archive._insert=fail
else:
    def fail(self,event):
        if event=='sql_committed': os._exit(37)
    PreparedFiles.outcome=fail
with sessionmaker(bind=erp,autoflush=False)() as db:
    archive.import_archive(db,json.loads(Path(sys.argv[4]).read_text(encoding='utf-8')),'CRASH-0205')
''',encoding='utf-8')
    env={**os.environ,'AGENT_TESTING':'1','PYTHONPATH':str(Path(__file__).resolve().parents[1]),
         'MINIPILOT_HOME':str(root),'PB_DATABASE_URL':str(brain.kw['bind'].url),'PB_STORAGE_DIR':str(root/'storage')}
    process=subprocess.run([sys.executable,str(script),str(target.kw['bind'].url),str(brain.kw['bind'].url),str(root),str(payload),stage],
        env=env,capture_output=True,text=True,timeout=30)
    assert process.returncode==37,process.stderr
    after=capture_baseline(erp_path),capture_baseline(brain_path)
    directory=next((root/'backups'/'archive-imports').iterdir())
    with target() as db,brain() as canonical:
        report=inspect_preparation(db,directory,canonical)
        assert report['sql_state']==('committed' if stage=='after_sql_commit' else 'not_committed')
    for item in report['files']:
        assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest()==item['sha256']
    if stage=='after_sql_commit':
        assert compare_baseline(before[0],after[0])['preserved'] and compare_baseline(before[1],after[1])['preserved']
        with target() as db:
            row=db.query(ReviewPublication).one()
            assert row.pdf_base64==data['tables']['project_review_publications'][0]['pdf_base64']
    else:
        assert after==before
        retry=restore(target,data,'RETRY-0205')
        with target() as db:
            assert archive.export_archive(db,retry['id'])['version']==6


def test_actual_typed_document_files_visas_and_captured_type_roundtrip(typed_document, tmp_path, monkeypatch, request):
    import app.db
    import backend.app.db
    from backend.app.project_deliverable_models import DeliverableFileVersion, DeliverableVersionMetadata
    from backend.app.services import project_deliverables as documents
    from backend.app.services.planning_revision import revision
    from backend.app.project_deliverable_schemas import TypeDefinition, TypePublish
    _,source,published,_=typed_document
    erp_path,brain_path=tmp_path/'typed-target-erp.db',tmp_path/'typed-target-brain.db'
    erp,canonical=create_engine(f'sqlite:///{erp_path}'),create_engine(f'sqlite:///{brain_path}')
    request.addfinalizer(erp.dispose)
    request.addfinalizer(canonical.dispose)
    configure_sqlite(erp)
    configure_sqlite(canonical)
    Base.metadata.create_all(erp)
    BrainBase.metadata.create_all(canonical)
    for install,name in ((install_planning_schema,'planning'),(install_deliverable_schema,'deliverables'),(install_review_schema,'reviews')):
        install(erp,backup=lambda n=name:backup_sqlite(erp_path,tmp_path/('typed-before-'+n+'.db')))
    target,brain=sessionmaker(bind=erp,autoflush=False),sessionmaker(bind=canonical,autoflush=False)
    target_root=tmp_path/'typed-target-files'
    factory,ids,path,*_=source
    source_root=path.parent
    with transaction(factory) as db:
        person=db.execute(select(Base.metadata.tables['project_people'])).mappings().one()
        identity.patch_person(db,person['id'],PersonPatch(expected_revision=person['revision'],first_name=person['first_name']))
        identity.patch_identity(db,ids['project'],IdentityPatch(expected_revision=0,responsible_id=person['id']))
        metadata=db.query(DeliverableVersionMetadata).one()
        source_path=db.get(DeliverableFileVersion,published['version_id']).path
        metadata.storage_path=source_path
        head=db.execute(select(Base.metadata.tables['project_deliverable_types'])).mappings().one()
        documents.publish_type(db,head['id'],TypePublish(expected_revision=head['revision'],definition=TypeDefinition(
            checklist=[{'code':'visa','label':'Visa version suivante','is_gate':True}])))
        assert revision(db,ids['project'])>0
    install_planning_schema(factory.kw['bind'],backup=lambda:backup_sqlite(path,source_root/'before-export-planning.db'))
    monkeypatch.setattr(backend.app.db,'APP_DIR',source_root)
    monkeypatch.setattr(app.db,'SessionLocal',brain)
    with factory() as db:
        data=archive.export_archive(db,ids['project'])
    assert data['version']==6 and len(data['deliverable_references']['project_deliverable_type_versions'])==2
    frozen=data['tables']['project_review_publications'][0]
    monkeypatch.setattr(backend.app.db,'APP_DIR',target_root)
    result=restore(target,data,'TYPED-0205')
    with target() as db:
        publication=db.query(ReviewPublication).filter_by(project_id=result['id']).one()
        assert publication.snapshot==frozen['snapshot'] and publication.pdf_base64==frozen['pdf_base64']
        second=archive.export_archive(db,result['id'])
        assert len(second['deliverable_references']['project_deliverable_type_versions'])==2
        captured=json.loads(publication.snapshot)['deliverables'][0]
        document=documents.read_deliverable(db,result['id'],publication.bindings['erp'][captured['id']])
        assert document['checklist'][0]['completed']
        versions=db.query(DeliverableVersionMetadata).filter_by(project_id=result['id']).all()
        assert len(versions)==1 and Path(versions[0].storage_path).read_bytes()==Path(source_path).read_bytes()
