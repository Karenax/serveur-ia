"""Apprentissage multi-critère depuis les seuls classements humains courants."""
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.db_support import configure_sqlite
from app.models import Contact, KnowledgeItem, Project, Proposal, Source, SourceArtifact
from app.services.ingestion import parse_eml
from app.services.mail_learning import addresses, build_learning_context, reply_headers, terms
from app.services.resolution import choose_candidate, merge_ai_hints, resolve_project


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    configure_sqlite(engine)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def projects(db):
    a = Project(code="LEARN-A", name="Dossier alpha")
    b = Project(code="LEARN-B", name="Dossier beta")
    db.add_all([a, b])
    db.commit()
    return [a, b]


def sample(db, project, sender="Alice <alice@atelier.test>", *, status="resolved",
           subject="Conversation technique", body="", participants=None):
    source = Source(source_type="email", status=status, project_id=project.id,
                    author=sender, participants=participants or [], sha256=uuid.uuid4().hex,
                    original_uri="test.eml", source_metadata={"subject": subject,
                    "message_id": f"<{uuid.uuid4()}@atelier.test>"})
    db.add(source)
    db.flush()
    db.add(SourceArtifact(source_id=source.id, kind="body_text", content_text=body))
    db.commit()
    return source


def classify(db, ps, sender="alice@atelier.test", **kwargs):
    return resolve_project({"subject": "Nouveau sujet", "sender": sender, **kwargs}, ps, None,
                           build_learning_context(db, ps))


def test_sender_strength_grows_with_validations(db):
    ps = projects(db)
    scores = []
    for _ in range(3):
        sample(db, ps[0])
        result = classify(db, ps, "ALICE <ALICE@ATELIER.TEST>")
        scores.append(result["candidates"][0]["score"])
        assert result["auto"] is False
    assert scores == [0.42, 0.62, 0.8]
    assert choose_candidate(result["candidates"])["project_id"] == ps[0].id
    assert result["candidates"][0]["evidence"][0]["samples"] == 3


def test_duplicate_copies_do_not_inflate_learning(db):
    ps = projects(db)
    original = sample(db, ps[0])
    for _ in range(2):
        duplicate = sample(db, ps[0])
        duplicate.source_metadata = {**duplicate.source_metadata, "message_id": original.source_metadata["message_id"]}
    db.commit()
    context = build_learning_context(db, ps)
    assert context.samples[ps[0].id] == 1
    assert choose_candidate(classify(db, ps)["candidates"]) is None


def test_shared_sender_needs_other_criteria(db):
    ps = projects(db)
    for p in ps:
        for _ in range(3):
            sample(db, p, body="vérin hydraulique ajustage pression" if p == ps[0]
                   else "plancher plafond peinture composite")
    unknown = classify(db, ps)
    assert choose_candidate(unknown["candidates"]) is None
    selected = choose_candidate(classify(db, ps, body_text="Vérin hydraulique ajustage pression")['candidates'])
    assert selected["project_id"] == ps[0].id
    assert {"learned_sender", "learned_vocabulary"} <= set(selected["reasons"])


def test_uneven_shared_sender_requires_a_discriminant_before_automatic_assignment(db):
    ps = projects(db)
    for _ in range(20):
        sample(db, ps[0], participants=["moi@entreprise.test"])
    sample(db, ps[1], participants=["moi@entreprise.test"])
    result = classify(db, ps, participants=["moi@entreprise.test"])
    assert choose_candidate(result['candidates']) is None
    merge_ai_hints(result, ps, [ps[0].code])
    selected = choose_candidate(result['candidates'])
    assert selected['project_id'] == ps[0].id
    assert selected['score'] >= 0.75
    assert 'ai_hint' in selected['reasons']


def test_specific_recipient_is_preferred_over_frequent_internal_recipient(db):
    ps = projects(db)
    for _ in range(3):
        sample(db, ps[0], participants=["moi@entreprise.test", "specialiste@client.test"])
        sample(db, ps[1], participants=["moi@entreprise.test"])
    result = classify(db, ps, "new@unknown.test",
                      participants=["moi@entreprise.test", "specialiste@client.test"])
    evidence = next(c for c in result['candidates'] if c['project_id'] == ps[0].id)['evidence']
    recipient = next(e for e in evidence if e['key'] == 'learned_participants')
    assert "specialiste@client.test" in recipient['label']


def test_internal_recipient_and_domain_cannot_decide_alone(db):
    ps = projects(db)
    for p in ps:
        for _ in range(4):
            sample(db, p, participants=["moi@entreprise.test"])
    result = classify(db, ps, "inconnu@atelier.test", participants=["moi@entreprise.test"])
    assert choose_candidate(result["candidates"]) is None
    assert all(c["score"] < 0.3 for c in result["candidates"])


def test_reply_headers_connect_to_validated_thread(db):
    ps = projects(db)
    source = sample(db, ps[1])
    selected = choose_candidate(classify(db, ps, "new@other.test",
        in_reply_to=source.source_metadata["message_id"])["candidates"])
    assert selected["project_id"] == ps[1].id
    assert "learned_thread" in selected["reasons"]
    other = sample(db, ps[0])
    conflict = classify(db, ps, "new@other.test", references=" ".join([
        source.source_metadata["message_id"], other.source_metadata["message_id"]]))
    assert choose_candidate(conflict["candidates"]) is None


def test_reclassification_moves_learning_and_exclusion_removes_it(db):
    ps = projects(db)
    sources = [sample(db, ps[0]) for _ in range(3)]
    assert choose_candidate(classify(db, ps)["candidates"])["project_id"] == ps[0].id
    sources[0].project_id = ps[1].id
    db.commit()
    context = build_learning_context(db, ps)
    assert context.senders["alice@atelier.test"] == {ps[0].id: 2, ps[1].id: 1}
    assert choose_candidate(classify(db, ps)["candidates"]) is None
    sources[0].status = "discarded"
    db.commit()
    assert ps[1].id not in build_learning_context(db, ps).senders["alice@atelier.test"]


def test_unvalidated_suggestions_and_divers_do_not_feed_learning(db):
    ps = projects(db)
    pending = sample(db, ps[0], status="resolution_pending", body="secret hydraulique ajustage")
    db.add(Proposal(source_id=pending.id, project_id=ps[0].id, kind="project_attach",
                    subject="Suggestion", value="{}", status="accepted"))
    divers = Project(code="DIVERS", name="Divers")
    db.add(divers)
    db.commit()
    sample(db, divers)
    context = build_learning_context(db, ps + [divers])
    assert not context.samples and not context.senders and not context.vocabulary


def test_excluding_source_prevents_learning_from_itself(db):
    ps = projects(db)
    source = sample(db, ps[0])
    context = build_learning_context(db, ps, exclude_source_id=source.id)
    assert not context.samples and not context.vocabulary


def test_declared_contact_and_project_title_combine(db):
    ps = projects(db)
    ps[0].name = "Ajustage hydraulique"
    db.add(Contact(name="Alice", emails=["alice@atelier.test"], roles={ps[0].id: "client"}))
    db.commit()
    selected = choose_candidate(classify(db, ps, body_text="Ajustage hydraulique")['candidates'])
    assert selected["project_id"] == ps[0].id
    assert {"project_contact", "project_title"} <= set(selected["reasons"])


def test_validated_knowledge_enriches_vocabulary(db):
    ps = projects(db)
    db.add(Contact(name="Alice", emails=["alice@atelier.test"], roles={ps[0].id: "client"}))
    item = KnowledgeItem(project_id=ps[0].id, kind="requirement", subject="Vérin hydraulique",
                         value="Ajustage pression", status="validated")
    db.add(item)
    db.commit()
    assert choose_candidate(classify(db, ps, body_text="Vérin hydraulique ajustage pression")['candidates'])["project_id"] == ps[0].id
    item.status = "invalidated"
    db.commit()
    assert choose_candidate(classify(db, ps, body_text="Vérin hydraulique ajustage pression")['candidates']) is None


def test_explicit_subject_overrides_learned_sender_and_quoted_code(db):
    ps = projects(db)
    for _ in range(3):
        sample(db, ps[0])
    result = classify(db, ps, subject=ps[1].code, body_text="Historique : " + ps[0].code)
    selected = choose_candidate(result["candidates"])
    assert selected["project_id"] == ps[1].id
    ambiguous = classify(db, ps, subject=ps[1].code + " et " + ps[0].code)
    assert choose_candidate(ambiguous["candidates"]) is None


def test_ai_hints_combine_with_context_and_remain_ambiguous_on_ties(db):
    ps = projects(db)
    sample(db, ps[0])
    result = classify(db, ps)
    merge_ai_hints(result, ps, [ps[0].code])
    assert choose_candidate(result['candidates'])["project_id"] == ps[0].id
    merge_ai_hints(result, ps, [ps[1].code])
    assert choose_candidate(result['candidates']) is None


def test_attachment_topics_contribute(db):
    ps = projects(db)
    for _ in range(2):
        sample(db, ps[0], body="Vérin hydraulique ajustage pression")
    result = classify(db, ps, attachments=[{"filename": "verin_hydraulique_ajustage.pdf"}])
    assert "attachment_vocabulary" in result['candidates'][0]["reasons"]
    assert choose_candidate(result['candidates'])["project_id"] == ps[0].id


def test_address_matching_and_quoted_signatures():
    assert addresses('Alice <ALICE@EXAMPLE.COM>') == {"alice@example.com"}
    assert "hydraulique" not in terms("Bonjour\n> Vérin hydraulique\n--\nHydraulique ajustage")
    assert "hydraulique" not in terms("<p>Bonjour</p><blockquote>Vérin hydraulique</blockquote>")


def test_mime_reply_headers_are_preserved():
    raw = b"In-Reply-To: <parent@x>\r\nReferences: <older@x> <parent@x>\r\n\r\nBonjour."
    parsed = parse_eml(raw)
    assert parsed["in_reply_to"] == "<parent@x>"
    assert parsed["references"] == "<older@x> <parent@x>"


def test_reply_headers_can_be_read_from_old_import_without_changing_metadata(tmp_path):
    original = tmp_path / "old.eml"
    original.write_bytes(b"In-Reply-To: <parent@x>\r\nReferences: <parent@x>\r\n\r\nCorps")
    meta = {"subject": "Ancien import"}
    assert reply_headers(meta, str(original))["in_reply_to"] == "<parent@x>"
    assert meta == {"subject": "Ancien import"}
    assert reply_headers({}, str(tmp_path / "missing.eml"))["references"] == ""


def test_llm_receives_learning_profile_and_recipients(monkeypatch):
    from app.services import ai_client
    observed = []

    def post(url, payload, **kwargs):
        observed.append(payload)
        return {"message": {"content": '{"project_hints": ["LEARN-A"], "items": []}'}}

    monkeypatch.setattr(ai_client, "_post_json", post)
    result = ai_client.classify_email(
        {"enabled": True, "provider": "ollama", "base_url": "http://unused", "model": "fake"},
        "Question technique", "Corps", "alice@atelier.test", [{"code": "LEARN-A", "name": "Ajustage",
        "validated_mail_count": 4, "known_senders": ["alice@atelier.test"], "keywords": ["hydraulique"]}],
        participants=["specialiste@client.test"])
    assert result["project_hints"] == ["LEARN-A"]
    user = observed[0]["messages"][1]["content"]
    assert "Destinataires: specialiste@client.test" in user
    assert "mails validés: 4" in user and "thèmes: hydraulique" in user
