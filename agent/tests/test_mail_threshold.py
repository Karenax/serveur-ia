import uuid
import json

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import AuditLog, Project, Proposal, Source
from app.services.settings_service import save_section
from app.services.triage import auto_classification_threshold, auto_classify_proposal


def proposal(db, confidence):
    project=Project(code='THRESHOLD-'+uuid.uuid4().hex,name='Test')
    db.add(project)
    db.flush()
    source=Source(source_type='email',status='resolution_pending',sha256=uuid.uuid4().hex,original_uri='')
    db.add(source)
    db.flush()
    item=Proposal(source_id=source.id,project_id=project.id,kind='project_attach',subject='Test',value='{}',confidence=confidence)
    db.add(item)
    db.commit()
    return source,item


@pytest.mark.parametrize('score,classified',[(.7499,False),(.75,True),(.9,True),(1.01,False)])
def test_default_75_boundary_and_audit(score,classified):
    with SessionLocal() as db:
        assert auto_classification_threshold(db)==.75
        source,item=proposal(db,score)
        assert auto_classify_proposal(db,item,{'enabled':True}) is classified
        if classified:
            assert source.status=='resolved'
            audit=db.query(AuditLog).filter_by(event_type='triage.auto_classified.v1',project_id=item.project_id).one()
            assert audit.payload['confidence']==score
            assert audit.payload['threshold']==.75
            assert audit.actor=='auto-confidence-threshold'
        else:
            assert source.status=='resolution_pending'


def test_custom_threshold_applies_immediately_and_preserves_human_classification():
    with SessionLocal() as db:
        source,item=proposal(db,.8)
        save_section(db,'mail',{'auto_classification_threshold':.9})
        assert not auto_classify_proposal(db,item)
        db.rollback()
        save_section(db,'mail',{'auto_classification_threshold':.75})
        assert auto_classify_proposal(db,item,{'enabled':True})
        assert not auto_classify_proposal(db,item)
        assert source.status=='resolved'


def test_setting_roundtrip_both_routes_and_invalid_values():
    client=TestClient(app)
    assert client.get('/api/v1/brain/mail-settings').json()['auto_classification_threshold']==.75
    assert client.put('/api/v1/brain/mail-settings',json={'auto_classification_threshold':.85}).json()['auto_classification_threshold']==.85
    assert client.get('/v1/settings').json()['mail']['auto_classification_threshold']==.85
    assert client.put('/v1/settings/mail',json={'scan_interval_minutes':9}).json()['auto_classification_threshold']==.85
    for bad in [0,-.1,1.01]:
        for path in ['/api/v1/brain/mail-settings','/v1/settings/mail']:
            assert client.put(path,json={'auto_classification_threshold':bad}).status_code==422


@pytest.mark.parametrize('competing,classified',[(.3,True),(.75,False)])
def test_historical_divers_uses_ai_candidate_and_preserves_ties(competing,classified):
    from app.services.triage import ensure_divers_project
    with SessionLocal() as db:
        source,item=proposal(db,.35)
        target_id=item.project_id
        divers=ensure_divers_project(db)
        other=Project(code='OTHER-'+uuid.uuid4().hex,name='Other')
        db.add(other)
        db.flush()
        item.project_id=divers.id
        item.value=json.dumps({'candidates':[
            {'project_id':target_id,'score':.75,'reasons':['learned_sender','ai_hint'],
             'evidence':[{'key':'learned_sender','shared':True},{'key':'ai_hint'}]},
            {'project_id':other.id,'score':competing,'reasons':['ai_hint'],
             'evidence':[{'key':'ai_hint'}]}]})
        db.commit()
        assert auto_classify_proposal(db,item,{'enabled':True}) is classified
        assert source.status==('resolved' if classified else 'resolution_pending')
        assert item.project_id==(target_id if classified else divers.id)
        assert item.confidence==(.75 if classified else .35)


def test_automatic_pass_reconciles_already_analyzed_mail_without_inference(monkeypatch):
    from app.services.auto_scan import run_auto_scan_once
    from app.services.triage import pending_triage_query
    from app.models import ValidationDecision
    from app.workspace_models import MailEnrichmentJob

    monkeypatch.setattr('app.services.triage.triage_pending', lambda *a, **k: {'triaged': 0})
    monkeypatch.setattr('app.services.ai_client.classify_email', lambda *a, **k: pytest.fail('Unexpected inference'))
    with SessionLocal() as db:
        save_section(db, 'mail', {'source': 'thunderbird', 'auto_classification_threshold': .9})
        source, item = proposal(db, .8)
        item.reason = 'triage IA : ai_hint'
        db.commit()
        source_id, proposal_id, project_id = source.id, item.id, item.project_id
        assert not pending_triage_query(db).filter(Source.id == source_id).count()
    # Already analyzed under a higher threshold, then made eligible by settings.
    run_auto_scan_once()
    with SessionLocal() as db:
        assert db.get(Source, source_id).status == 'resolution_pending'
    with SessionLocal() as db:
        save_section(db, 'mail', {'auto_classification_threshold': .75})
    result = run_auto_scan_once()
    assert result['auto_classification']['auto_classified'] >= 1
    assert result['auto_classification']['errors'] == []
    with SessionLocal() as db:
        assert db.get(Source, source_id).status == 'resolved'
        assert db.get(Source, source_id).project_id == project_id
        assert db.get(Proposal, proposal_id).status == 'accepted'
        assert db.query(ValidationDecision).filter_by(proposal_id=proposal_id).one().actor == 'auto-confidence-threshold'
        assert db.query(MailEnrichmentJob).filter_by(source_id=source_id).one().status == 'queued'
    run_auto_scan_once()
    with SessionLocal() as db:
        audits = db.query(AuditLog).filter_by(event_type='triage.auto_classified.v1', project_id=project_id).all()
        assert len([row for row in audits if row.payload['source_id'] == source_id]) == 1


def test_automatic_pass_preserves_low_scores_conflicts_and_human_decisions(monkeypatch):
    from app.services.auto_scan import run_auto_scan_once
    monkeypatch.setattr('app.services.triage.triage_pending', lambda *a, **k: {'triaged': 0})
    with SessionLocal() as db:
        save_section(db, 'mail', {'source': 'thunderbird'})
        low, _ = proposal(db, .7499)
        conflict, item = proposal(db, .9)
        _, other = proposal(db, .8)
        db.add(Proposal(source_id=conflict.id, project_id=other.project_id,
                        kind='project_attach', subject='Conflict', value='{}', confidence=.9))
        human, human_item = proposal(db, 1.0)
        human.status, human.project_id, human_item.status = 'resolved', human_item.project_id, 'accepted'
        discarded, _ = proposal(db, 1.0)
        discarded.status = 'discarded'
        db.commit()
        protected = {s.id: (s.status, s.project_id) for s in [low, conflict, human, discarded]}
        conflict_id = item.id
    run_auto_scan_once()
    with SessionLocal() as db:
        for sid, before in protected.items():
            source = db.get(Source, sid)
            assert (source.status, source.project_id) == before
        assert db.get(Proposal, conflict_id).status == 'pending'
