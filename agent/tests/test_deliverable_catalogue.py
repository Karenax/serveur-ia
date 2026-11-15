"""L3 catalogue CAS, scope, explicit applicability and non-destructive selection."""
from concurrent.futures import ThreadPoolExecutor

from fastapi import HTTPException
import pytest

from backend.app.models import Deliverable
from backend.app.project_deliverable_models import DeliverableEvent, DeliverablePlan, DeliverableTypeVersion
from backend.app.project_deliverable_schemas import (
    ChecklistCreate, ChecklistPatch, DeliverableCreate, SelectionApply, SelectionPreview, TypeCreate, TypeDefinition,
    TypePatch, TypePublish, TypologyTypesPatch,
)
from backend.app.project_identity_models import ProjectPerson, ProjectProfile, ProjectReferenceChange
from backend.app.project_identity_schemas import ReferenceCreate
from backend.app.project_planning_models import PlanningChange
from backend.app.services import deliverable_catalogue as catalogue, project_deliverables as service
from backend.app.services.migration_guard import capture_baseline
from backend.app.services.planning_revision import revision
from backend.app.services.project_identity import create_reference
from backend.app.services.project_operator import Operator, operator_context
from tests import test_project_deliverables as fixtures
from tests.test_project_deliverables import transaction

store = fixtures.store


def reference(store, code='af', *, checklist=None, label=None, position=0):
    with transaction(store[0]) as db:
        return service.create_type(db, TypeCreate(code=code, label=label or code.upper(),
            definition=TypeDefinition(checklist=checklist or [], position=position)))


def typology(store, code='conception'):
    factory, ids, *_ = store
    with transaction(factory) as db:
        row = create_reference(db, ReferenceCreate(kind='typology', code=code, label=code.title()))
        db.add(ProjectProfile(project_id=ids['project'], typology_id=row['id']))
    return row['id']


def preview(store, **values):
    factory, ids, *_ = store
    with factory() as db:
        request = SelectionPreview(expected_revision=revision(db, ids['project']), **values)
        return request, catalogue.preview_selection(db, ids['project'], request)


def apply(store, request, result):
    factory, ids, *_ = store
    with transaction(factory) as db:
        return catalogue.apply_selection(db, ids['project'], SelectionApply(
            **request.model_dump(), expected_preview_sha256=result['sha256']))


def test_catalogue_reads_are_paged_literal_accent_insensitive_and_neutral(store):
    factory, ids, path, *_ = store
    for index in range(27):
        reference(store, f'type_{index:02d}', label=f'Études {index:02d}' if index != 12 else 'Valeur 100%_réelle')
    before = capture_baseline(path)
    with operator_context(Operator('reader', 'reader', frozenset([ids['project']]))), factory() as db:
        first = catalogue.list_types(db, search='ETUDES', limit=10)
        second = catalogue.list_types(db, search='études', limit=10, offset=10)
        assert first['total'] == second['total'] == 26
        assert not {item['id'] for item in first['items']} & {item['id'] for item in second['items']}
        assert not first['can_manage'] and len(second['items']) == 10
        assert catalogue.list_types(db, search='%_')['total'] == 1
    assert capture_baseline(path) == before


def test_condition_typology_codes_are_authoritative_scoped_paged_and_read_only(store):
    factory, ids, path, *_ = store
    identity = typology(store, code='ÉTUDE_ß')
    with transaction(factory) as db:
        foreign = create_reference(db, ReferenceCreate(kind='typology', code='Autre', label='Autre typologie'))
        db.add(ProjectProfile(project_id=ids['foreign'], typology_id=foreign['id']))
    before = capture_baseline(path)
    with operator_context(Operator('reader', 'reader', frozenset([ids['project']]))), factory() as db:
        result = catalogue.condition_typologies(db, limit=1)
        assert result['total'] == 1 and result['items'][0]['id'] == identity
        assert result['items'][0]['condition_code'] == 'etude_ss'
        assert catalogue.condition_typologies(db, offset=1, limit=1)['items'] == []
        assert catalogue.condition_typologies(db, search='autre')['total'] == 0
    with factory() as db:
        assert catalogue.condition_typologies(db, limit=1)['total'] == 2
    assert capture_baseline(path) == before


def test_patch_archive_and_publication_keep_older_definitions_and_project_checklist(store):
    factory, ids, *_ = store
    item = reference(store, checklist=[{'code': 'visa', 'label': 'Version 1'}])
    with transaction(factory) as db:
        project_item = service.create_deliverable(db, ids['project'], DeliverableCreate(expected_revision=0,
            title='AF manuelle', type_version_id=item['version_id']))
        original = service.read_deliverable(db, ids['project'], project_item['id'])
        v2 = service.publish_type(db, item['id'], TypePublish(expected_revision=1,
            definition=TypeDefinition(checklist=[{'code': 'visa', 'label': 'Version 2'}])))
        catalogue.patch_type(db, item['id'], TypePatch(expected_revision=2, label='AF renommée', active=False))
        assert service.read_deliverable(db, ids['project'], project_item['id']) == original
        assert catalogue.list_types(db)['total'] == 0
        assert catalogue.list_types(db, include_inactive=True)['total'] == 1
        assert catalogue.versions(db, item['id'], limit=1)['items'][0]['id'] == v2['version_id']
        assert catalogue.version_detail(db, item['id'], item['version_id'])['definition']['checklist'][0]['label'] == 'Version 1'
    with pytest.raises(HTTPException) as error:
        with transaction(factory) as db:
            catalogue.patch_type(db, item['id'], TypePatch(expected_revision=2, label='Conflit'))
    assert error.value.status_code == 409
    other = reference(store, 'ar')
    with pytest.raises(HTTPException) as error:
        with factory() as db:
            catalogue.version_detail(db, other['id'], item['version_id'])
    assert error.value.status_code == 404


def test_typology_configuration_shares_reference_revision_and_preserves_removed_links(store):
    factory, ids, *_ = store
    identity = typology(store)
    first, second = reference(store), reference(store, 'ar')
    with transaction(factory) as db:
        result = catalogue.patch_typology_types(db, identity, TypologyTypesPatch(expected_revision=1,
            type_ids=[first['id'], second['id']]))
        assert result['revision'] == 2
        assert catalogue.list_types(db, typology_id=identity)['total'] == 2
    with pytest.raises(HTTPException):
        with transaction(factory) as db:
            catalogue.patch_typology_types(db, identity, TypologyTypesPatch(expected_revision=1, type_ids=[]))
    with transaction(factory) as db:
        result = catalogue.patch_typology_types(db, identity, TypologyTypesPatch(expected_revision=2,
            type_ids=[second['id']]))
        assert result['type_ids'] == [second['id']]
        from backend.app.project_deliverable_models import DeliverableTypologyType
        assert db.query(DeliverableTypologyType).count() == 2
        assert db.query(ProjectReferenceChange).filter_by(entity_id=identity).count() == 3


def test_global_administration_and_scoped_typology_reads_are_enforced(store):
    factory, ids, *_ = store
    identity = typology(store)
    item = reference(store)
    with operator_context(Operator('reader', 'reader', frozenset([ids['foreign']]))):
        with factory() as db:
            assert catalogue.list_types(db)['total'] == 1
        with pytest.raises(HTTPException) as error:
            with factory() as db:
                catalogue.typology_types(db, identity)
        assert error.value.status_code == 404
        with pytest.raises(HTTPException) as error:
            with transaction(factory) as db:
                catalogue.patch_type(db, item['id'], TypePatch(expected_revision=1, active=False))
        assert error.value.status_code == 403


def test_atomic_selection_creates_one_planning_event_and_does_not_duplicate_or_change_legacy(store):
    factory, ids, path, *_ = store
    first, second = reference(store), reference(store, 'ar')
    before = capture_baseline(path)
    request, result = preview(store, type_version_ids=[first['version_id'], second['version_id']])
    assert result['changes'] == 2 and not result['blockers']
    assert capture_baseline(path) == before
    applied = apply(store, request, result)
    assert applied['revision'] == 1 and len(applied['changed']) == 2
    with factory() as db:
        assert db.query(PlanningChange).count() == 1 and db.query(DeliverableEvent).count() == 2
        assert db.query(PlanningChange).one().value['inputs'] == request.model_dump()
        assert {row.revision for row in db.query(DeliverableEvent)} == {1}
        assert db.get(Deliverable, ids['legacy']).status == 'done'
    request, result = preview(store, type_version_ids=[first['version_id'], second['version_id']])
    assert result['changes'] == 0
    assert apply(store, request, result)['changed'] == []
    with factory() as db:
        assert db.query(Deliverable).count() == 3


@pytest.mark.parametrize('code,expected', [('conception', 1), ('modification', 2)])
def test_conditional_gates_follow_actual_project_typology(store, code, expected):
    factory, ids, *_ = store
    identity = typology(store, code)
    item = reference(store, checklist=[{'code': 'preparation', 'label': 'Préparation', 'milestone_code': 'pdr'},
        {'code': 'visa_mod', 'label': 'Visa modification', 'milestone_code': 'pdr', 'is_gate': True,
         'typology_codes': ['modification']}])
    request, result = preview(store, type_version_ids=[item['version_id']], typology_id=identity,
                               milestone_mapping={'pdr': ids['milestone']})
    assert not result['blockers']
    applied = apply(store, request, result)
    with factory() as db:
        row = service.read_deliverable(db, ids['project'], applied['changed'][0]['deliverable_id'])
        assert len(row['checklist']) == expected
        assert len(row['validation_blockers']) == expected - 1


def test_unknown_conditional_typology_and_missing_mapping_are_explicit_blockers(store):
    item = reference(store, checklist=[{'code': 'visa', 'label': 'Visa', 'milestone_code': 'pdr',
                                       'typology_codes': ['modification'], 'is_gate': True}])
    request, result = preview(store, type_version_ids=[item['version_id']])
    assert result['blockers']
    with pytest.raises(HTTPException):
        apply(store, request, result)
    request, result = preview(store, type_version_ids=[item['version_id']], excluded_milestone_codes=['pdr'])
    assert not result['blockers']
    assert apply(store, request, result)['changed']


def test_no_silent_omission_of_unmapped_milestone(store):
    item = reference(store, checklist=[{'code': 'visa', 'label': 'Visa', 'milestone_code': 'cdr', 'is_gate': True}])
    request, result = preview(store, type_version_ids=[item['version_id']])
    assert result['blockers'][0]['code'] == 'cdr'
    with pytest.raises(HTTPException) as error:
        apply(store, request, result)
    assert error.value.status_code == 409
    with store[0]() as db:
        assert revision(db, store[1]['project']) == 0 and db.query(Deliverable).count() == 1


@pytest.mark.parametrize('change', ['type_label', 'typology_selection', 'project_typology'])
def test_preview_binds_catalogue_and_profile_changes_even_without_planning_revision(store, change):
    factory, ids, path, *_ = store
    identity = typology(store)
    item = reference(store)
    request, result = preview(store, type_version_ids=[item['version_id']], typology_id=identity)
    with transaction(factory) as db:
        if change == 'type_label':
            catalogue.patch_type(db, item['id'], TypePatch(expected_revision=1, label='Nouveau label'))
        elif change == 'typology_selection':
            catalogue.patch_typology_types(db, identity, TypologyTypesPatch(expected_revision=1, type_ids=[item['id']]))
        else:
            db.get(ProjectProfile, ids['project']).typology_id = None
    before = capture_baseline(path)
    with pytest.raises(HTTPException) as error:
        apply(store, request, result)
    assert error.value.status_code == 409 and capture_baseline(path) == before


def test_old_version_is_retained_by_selection_and_no_existing_checks_are_rewritten(store):
    factory, ids, *_ = store
    item = reference(store, checklist=[{'code': 'original', 'label': 'Checklist initiale'}])
    request, result = preview(store, type_version_ids=[item['version_id']])
    original_id = apply(store, request, result)['changed'][0]['deliverable_id']
    with transaction(factory) as db:
        original = service.read_deliverable(db, ids['project'], original_id)
        new = service.publish_type(db, item['id'], TypePublish(expected_revision=1,
            definition=TypeDefinition(checklist=[{'code': 'new', 'label': 'Nouvelle checklist'}])))
    request, result = preview(store, type_version_ids=[new['version_id']])
    assert result['changes'] == 0 and result['warnings'][0]['retained_version_id'] == item['version_id']
    apply(store, request, result)
    with factory() as db:
        current = service.read_deliverable(db, ids['project'], original_id)
        assert current['type_version_id'] == original['type_version_id'] and current['checklist'] == original['checklist']


def test_adoption_is_explicit_preserves_manual_title_status_checks_and_published_file(store):
    factory, ids, *_ = store
    # Existing manually titled deliverable remains unattached until selected.
    original_id, _ = fixtures.create(store)
    fixtures.publish(store, original_id)
    item = reference(store, checklist=[{'code': 'typed', 'label': 'Contrôle de type'}])
    with transaction(factory) as db:
        responsible = ProjectPerson(first_name='Ancien', last_name='Responsable adopté')
        db.add(responsible)
        db.flush()
        responsible_id = responsible.id
    with factory() as db:
        original = service.read_deliverable(db, ids['project'], original_id)
    request, result = preview(store, type_version_ids=[item['version_id']], existing_mapping={item['id']: original_id},
                              responsible_id=responsible_id)
    assert result['operations'][0]['operation'] == 'adopt'
    apply(store, request, result)
    with factory() as db:
        current = service.read_deliverable(db, ids['project'], original_id)
        assert current['title'] == original['title'] and current['latest_version_id'] == original['latest_version_id']
        assert current['checklist'][0] == original['checklist'][0] and len(current['checklist']) == 2
        assert current['verifier_id'] == original['verifier_id']
    from backend.app.project_deliverable_schemas import DeliverablePatch
    with transaction(factory) as db:
        service.patch_deliverable(db, ids['project'], original_id, DeliverablePatch(expected_revision=4,
            responsible_id=None, verifier_id=None))
    with operator_context(Operator('reader', 'reader', frozenset([ids['project']]))), factory() as db:
        from backend.app.services.project_identity import list_people
        assert responsible_id in {person['id'] for person in list_people(db)['items']}


@pytest.mark.parametrize('case', ['ordinary', 'inactive', 'milestone', 'transverse', 'contributes'])
def test_adoption_preview_blocks_manual_control_masking_required_gate_without_writes(store, case):
    factory, ids, path, *_ = store
    original_id, _ = fixtures.create(store, with_gate=False)
    with transaction(factory) as db:
        item = service.create_check(db, ids['project'], original_id, ChecklistCreate(
            expected_revision=revision(db, ids['project']), code='visa', label='Contrôle manuel conservé',
            is_gate=case not in {'ordinary', 'inactive'}, milestone_id=ids['milestone'] if case == 'milestone' else None,
            transverse=case == 'transverse', contributes=case != 'contributes'))
        if case == 'inactive':
            service.patch_check(db, ids['project'], original_id, item['item']['id'],
                ChecklistPatch(expected_revision=revision(db, ids['project']), active=False))
    typed = reference(store, checklist=[{'code': 'visa', 'label': 'Visa obligatoire', 'is_gate': True}])
    baseline = capture_baseline(path)
    request, result = preview(store, type_version_ids=[typed['version_id']], existing_mapping={typed['id']: original_id})
    assert result['blockers'][0]['deliverable_id'] == original_id and result['blockers'][0]['code'] == 'visa'
    assert capture_baseline(path) == baseline
    with pytest.raises(HTTPException) as error:
        apply(store, request, result)
    assert error.value.status_code == 409 and capture_baseline(path) == baseline


def test_adoption_keeps_compatible_manual_gate_and_its_human_proof(store):
    factory, ids, *_ = store
    original_id, _ = fixtures.create(store, with_gate=False)
    with transaction(factory) as db:
        item = service.create_check(db, ids['project'], original_id, ChecklistCreate(
            expected_revision=revision(db, ids['project']), code='visa', label='Visa manuel', is_gate=True))
    fixtures.publish(store, original_id)
    with transaction(factory) as db:
        service.patch_check(db, ids['project'], original_id, item['item']['id'], ChecklistPatch(
            expected_revision=revision(db, ids['project']), completed=True, proof='Vérification conservée'))
        original = service.read_deliverable(db, ids['project'], original_id)
    typed = reference(store, checklist=[{'code': 'visa', 'label': 'Visa catalogue', 'is_gate': True}])
    request, result = preview(store, type_version_ids=[typed['version_id']], existing_mapping={typed['id']: original_id})
    assert not result['blockers']
    apply(store, request, result)
    with factory() as db:
        current = service.read_deliverable(db, ids['project'], original_id)
        assert current['checklist'] == original['checklist'] and current['latest_version_id'] == original['latest_version_id']


def test_ambiguous_type_targets_require_explicit_mapping_and_foreign_target_is_rejected(store):
    factory, ids, *_ = store
    item = reference(store)
    with transaction(factory) as db:
        one = service.create_deliverable(db, ids['project'], DeliverableCreate(expected_revision=0, title='AF A', type_version_id=item['version_id']))
        service.create_deliverable(db, ids['project'], DeliverableCreate(expected_revision=1, title='AF B', type_version_id=item['version_id']))
    request, result = preview(store, type_version_ids=[item['version_id']], deactivate_missing=True)
    assert len(result['blockers'][0]['candidate_ids']) == 2 and not result['operations']
    with pytest.raises(HTTPException):
        apply(store, request, result)
    request, result = preview(store, type_version_ids=[item['version_id']], existing_mapping={item['id']: one['id']})
    assert not result['blockers'] and result['operations'][0]['operation'] == 'keep'
    with pytest.raises(HTTPException, match='absent de ce projet'):
        preview(store, type_version_ids=[item['version_id']], existing_mapping={item['id']: ids['other']})


def test_reversible_deactivation_preserves_custom_and_legacy_data(store):
    factory, ids, *_ = store
    item = reference(store)
    request, result = preview(store, type_version_ids=[item['version_id']])
    identity = apply(store, request, result)['changed'][0]['deliverable_id']
    request, result = preview(store, type_version_ids=[], deactivate_missing=False)
    assert not result['operations']
    request, result = preview(store, type_version_ids=[], deactivate_missing=True)
    assert result['operations'][0]['operation'] == 'deactivate'
    apply(store, request, result)
    with factory() as db:
        assert not db.get(DeliverablePlan, identity).active
        assert db.get(Deliverable, ids['legacy']).status == 'done'
    request, result = preview(store, type_version_ids=[item['version_id']])
    assert result['operations'][0]['operation'] == 'reactivate'
    apply(store, request, result)
    with factory() as db:
        assert db.get(DeliverablePlan, identity).active and db.query(Deliverable).count() == 2


def test_scoped_verifier_is_visible_through_l3_assignment_without_identity_membership(store):
    factory, ids, *_ = store
    identity, gate = fixtures.create(store)
    fixtures.publish(store, identity)
    from backend.app.project_deliverable_schemas import ChecklistPatch
    with operator_context(Operator('verifier', 'editor', frozenset([ids['project']]), ids['person'])):
        with transaction(factory) as db:
            value = service.patch_check(db, ids['project'], identity, gate, ChecklistPatch(expected_revision=3,
                completed=True, proof='Visa version courante'))
        assert value['item']['completed']


def test_two_concurrent_selection_applications_have_one_winner(store):
    item = reference(store)
    request, result = preview(store, type_version_ids=[item['version_id']])
    def mutate(_):
        try:
            apply(store, request, result)
            return 201
        except HTTPException as error:
            return error.status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(mutate, range(2))) == [201, 409]
    with store[0]() as db:
        assert db.query(Deliverable).count() == 2 and db.query(PlanningChange).count() == 1


def test_legacy_type_version_without_applicability_fields_remains_readable(store):
    import json
    from backend.app.services.project_deliverable_rules import frozen_json
    item = reference(store)
    # Insert a historical immutable version rather than mutating a published row.
    with transaction(store[0]) as db:
        definition, sha = frozen_json({'category': 'studies', 'design': True,
            'checklist': [{'code': 'old', 'label': 'Ancien format', 'milestone_code': '', 'is_gate': False,
                          'transverse': False, 'contributes': True, 'active': True}]})
        version = DeliverableTypeVersion(type_id=item['id'], number=2, definition=definition, sha256=sha, actor_id='old')
        db.add(version)
        db.flush()
        identity = version.id
    with store[0]() as db:
        value = catalogue.version_detail(db, item['id'], identity)
        assert value['published_definition'] == json.loads(definition)
        assert value['definition']['checklist'][0]['typology_codes'] == []
    request, result = preview(store, type_version_ids=[identity])
    assert apply(store, request, result)['changed']


def test_catalogue_position_of_latest_version_precedes_pagination(store):
    factory, *_ = store
    last = reference(store, 'a', position=30)
    first = reference(store, 'z', position=10)
    middle = reference(store, 'm', position=20)
    with factory() as db:
        assert [catalogue.list_types(db, limit=1, offset=offset)['items'][0]['id'] for offset in (0, 1, 2)] == [
            first['id'], middle['id'], last['id']]
    with transaction(factory) as db:
        service.publish_type(db, last['id'], TypePublish(expected_revision=1, definition=TypeDefinition(position=5)))
    with factory() as db:
        page = catalogue.list_types(db, limit=1)
        assert page['items'][0]['id'] == last['id'] and page['items'][0]['latest_version']['position'] == 5


def test_selection_cannot_deactivate_validated_or_reopen_archived_document(store):
    factory, ids, *_ = store
    from backend.app.project_deliverable_schemas import DocumentTransition
    item = reference(store)
    request, result = preview(store, type_version_ids=[item['version_id']], verifier_id=ids['person'])
    identity = apply(store, request, result)['changed'][0]['deliverable_id']
    version = fixtures.publish(store, identity)
    with transaction(factory) as db:
        service.transition(db, ids['project'], identity, DocumentTransition(expected_revision=2,
            status='to_verify', version_id=version['version_id']))
        service.transition(db, ids['project'], identity, DocumentTransition(expected_revision=3,
            status='validated', version_id=version['version_id'], comment='Visa humain'))
    request, result = preview(store, type_version_ids=[], deactivate_missing=True)
    assert result['blockers']
    with pytest.raises(HTTPException):
        apply(store, request, result)
    with transaction(factory) as db:
        service.transition(db, ids['project'], identity, DocumentTransition(expected_revision=4,
            status='archived', version_id=version['version_id']))
    request, result = preview(store, type_version_ids=[], deactivate_missing=True)
    assert not result['blockers']
    apply(store, request, result)
    request, result = preview(store, type_version_ids=[item['version_id']])
    assert result['blockers']
    with pytest.raises(HTTPException):
        apply(store, request, result)
    with factory() as db:
        assert db.get(DeliverablePlan, identity).document_status == 'archived'
