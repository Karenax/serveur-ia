"""Publication, exact previews, application, scope and preserved legacy data."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json

from fastapi import HTTPException
import pytest

from tests import test_project_planning as fixtures
from tests.test_project_planning import transaction
from backend.app.models import Milestone, Task
from backend.app.project_planning_models import MilestonePlan, PlanningTemplateVersion, ProjectPlanningState, TaskPlan
from backend.app.project_planning_schemas import PlanningTemplatePublish
from backend.app.services import planning_templates as templates, project_planning as planning
from backend.app.services.migration_guard import capture_baseline
from backend.app.services.project_planning_rules import TemplateDefinition, capture_snapshot, default_template

api = fixtures.api
store = fixtures.store


def definition():
    value = default_template().model_dump()
    value['milestones'][10]['offset_workdays'] = 1
    value['tasks'] = [
        {'key': 'group', 'title': 'Groupe du modèle'},
        {'key': 'design', 'title': 'Études du modèle', 'parent_key': 'group', 'milestone_code': 'pdr',
         'start_offset_workdays': 0, 'end_offset_workdays': 1, 'planned_hours': 8, 'design': True},
        {'key': 'control', 'title': 'Contrôle du modèle', 'parent_key': 'group', 'milestone_code': 'livraison',
         'start_offset_workdays': 1, 'end_offset_workdays': 2, 'planned_hours': 4, 'manufacturing': True},
    ]
    return value


@pytest.fixture
def template(api):
    client, ids = api
    response = client.post('/api/v1/planning-templates', json={
        'code': 'STANDARD', 'name': 'Cycle standard', 'definition': definition()})
    assert response.status_code == 201, response.text
    return response.json()


def preview(client, ids, version_id, revision=0, **values):
    inputs = {'expected_revision': revision, 'start_date': '2026-10-02', 'excluded_dates': ['2026-10-05'], **values}
    root = f"/api/v1/projects/{ids['projects'][0]}/planning/templates/{version_id}"
    result = client.post(root + '/preview', json=inputs)
    assert result.status_code == 200, result.text
    return root, inputs, result.json()


def apply(client, root, inputs, view):
    return client.post(root + '/apply', json={**inputs, 'expected_preview_sha256': view['preview_sha256']})


def test_publication_freezes_versions_and_never_modifies_existing_planning(api, store, template):
    client, ids = api
    factory = store[0]
    with factory() as db:
        initial = planning.read_planning(db, ids['projects'][0])
    first = client.get(f"/api/v1/planning-templates/{template['id']}/versions/{template['version']['id']}").json()
    changed = definition()
    changed['tasks'][1]['planned_hours'] = 20
    version = client.post(f"/api/v1/planning-templates/{template['id']}/versions", json={
        'expected_revision': 0, 'definition': changed})
    assert version.status_code == 201 and version.json()['number'] == 2
    assert client.get(f"/api/v1/planning-templates/{template['id']}/versions/{first['id']}").json() == first
    with factory() as db:
        assert planning.read_planning(db, ids['projects'][0]) == initial
    assert client.post(f"/api/v1/planning-templates/{template['id']}/versions", json={
        'expected_revision': 0, 'definition': changed}).status_code == 409


def test_template_detail_is_scoped_readonly_and_returns_exact_current_revision(api, store, template, monkeypatch):
    client, ids = api
    path = f"/api/v1/planning-templates/{template['id']}"
    before = capture_baseline(store[2])
    detail = client.get(path).json()
    assert detail['revision'] == 0 and detail['can_manage'] is True
    assert detail['latest_version']['id'] == template['version']['id']
    assert detail['latest_version']['sha256'] == template['version']['sha256']
    assert capture_baseline(store[2]) == before
    assert client.patch(path, json={'expected_revision': 0, 'name': 'Cycle renommé'}).status_code == 200
    assert client.get(path).json()['revision'] == 1
    typology = client.post('/api/v1/project-references', json={'kind': 'typology', 'code': 'SECRET', 'label': 'Autre typologie'}).json()
    private = client.post('/api/v1/planning-templates', json={'code': 'PRIVATE', 'name': 'Autre projet',
                         'typology_id': typology['id'], 'definition': definition()}).json()
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'reader')
    monkeypatch.setenv('AGENT_OPERATOR_PROJECT_IDS', json.dumps([ids['projects'][0]]))
    assert client.get(path).json()['can_manage'] is False
    assert client.get(f"/api/v1/planning-templates/{private['id']}").status_code == 404
    assert client.get('/api/v1/planning-templates/missing').status_code == 404


def test_preview_is_readonly_uses_workdays_and_does_not_guess_name_mapping(api, store, template):
    client, ids = api
    before = capture_baseline(store[2])
    root, inputs, view = preview(client, ids, template['version']['id'])
    assert capture_baseline(store[2]) == before
    delivery = next(row for row in view['milestones'] if row['code'] == 'livraison')
    assert delivery['forecast_date'] == '2026-10-06'
    assert delivery['contractual_date'] == delivery['actual_date'] == ''
    assert len(view['tasks']) == 6 and len(view['milestones']) == 15
    assert view['task_map']['design'].startswith('new-task:')
    proposals = client.get(f"/api/v1/projects/{ids['projects'][0]}/planning/mapping-proposals").json()
    assert proposals['items'][0]['human_confirmation_required'] is True
    assert proposals['items'][0]['suggested_code'] is None


def test_apply_requires_exact_preview_and_stale_commands_roll_back(api, store, template):
    client, ids = api
    root, inputs, view = preview(client, ids, template['version']['id'])
    before = capture_baseline(store[2])
    assert client.post(root + '/apply', json={**inputs, 'expected_preview_sha256': '0' * 64}).status_code == 409
    assert capture_baseline(store[2]) == before
    assert apply(client, root, {**inputs, 'update_tasks': True}, view).status_code == 409
    assert capture_baseline(store[2]) == before
    client.patch(f"/api/v1/projects/{ids['projects'][0]}/tasks/{ids['tasks'][1]}", json={'title': 'Édition après aperçu'})
    after_edit = capture_baseline(store[2])
    assert apply(client, root, inputs, view).status_code == 409
    assert capture_baseline(store[2]) == after_edit


def test_application_matches_preview_exactly_preserves_manual_rows_and_does_not_duplicate(api, store, template):
    client, ids = api
    root, inputs, view = preview(client, ids, template['version']['id'])
    response = apply(client, root, inputs, view)
    assert response.status_code == 200, response.text
    result = response.json()
    mapping = {view['milestone_map'][key]: value for key, value in result['milestone_map'].items()}
    mapping.update({view['task_map'][key]: value for key, value in result['task_map'].items()})
    expected_milestones, expected_tasks = deepcopy(view['milestones']), deepcopy(view['tasks'])
    for row in [*expected_milestones, *expected_tasks]:
        for field in ('id', 'parent_id', 'milestone_id'):
            if field in row:
                row[field] = mapping.get(row[field], row[field])
    with store[0]() as db:
        actual = planning.read_planning(db, ids['projects'][0])
        assert capture_snapshot(ids['projects'][0], expected_milestones, expected_tasks) == capture_snapshot(
            ids['projects'][0], actual['milestones'], actual['tasks'])
        assert actual['revision'] == 1
        assert db.get(ProjectPlanningState, ids['projects'][0]).excluded_dates == ['2026-10-05']
        assert db.get(TaskPlan, result['task_map']['group']).planned_hours == 12
        assert all(db.get(TaskPlan, task_id) is None for task_id in ids['tasks'][:3])
        assert db.get(Milestone, ids['milestones'][0]).contractual_date == '2026-10-02'
    root, inputs, view = preview(client, ids, template['version']['id'], revision=1)
    repeated = apply(client, root, inputs, view).json()
    assert repeated['task_map'] == result['task_map'] and repeated['milestone_map'] == result['milestone_map']
    with store[0]() as db:
        assert db.query(Task).filter_by(project_id=ids['projects'][0]).count() == 6


@pytest.mark.parametrize('policy,expected', [('preserve', '2026-10-06'), ('fill_empty', '2026-10-06'), ('replace', '2026-10-07')])
def test_explicit_mapping_and_forecast_policy_preserve_actual_contract_and_other_evidence(api, store, template, policy, expected):
    client, ids = api
    with transaction(store[0]) as db:
        row = db.get(Milestone, ids['milestones'][0])
        row.actual_date = '2026-10-04'
        row.date_sources = {'contractual_date': {'source_id': 'preuve-contrat'}, 'actual_date': {'source_id': 'preuve-reelle'}}
    # The delivery offset is 1; map instead to the control task's PDR whose
    # forecast is explicitly configured here for this scenario.
    value = definition()
    value['milestones'][5]['offset_workdays'] = 2
    published = client.post(f"/api/v1/planning-templates/{template['id']}/versions", json={
        'expected_revision': 0, 'definition': value}).json()
    root, inputs, view = preview(client, ids, published['id'], milestone_mapping={'pdr': ids['milestones'][0]}, forecast_policy=policy)
    assert apply(client, root, inputs, view).status_code == 200
    with store[0]() as db:
        row = db.get(Milestone, ids['milestones'][0])
        assert row.forecast_date == expected
        assert row.contractual_date == '2026-10-02' and row.actual_date == '2026-10-04'
        assert row.date_sources['contractual_date'] == {'source_id': 'preuve-contrat'}
        assert row.date_sources['actual_date'] == {'source_id': 'preuve-reelle'}
        assert row.title == 'FAT' and db.get(MilestonePlan, row.id).code == 'pdr'


def test_new_version_preserves_existing_tasks_unless_update_is_explicit(api, store, template):
    client, ids = api
    root, inputs, view = preview(client, ids, template['version']['id'])
    applied = apply(client, root, inputs, view).json()
    updated = definition()
    updated['tasks'][1]['planned_hours'] = 20
    updated['tasks'][1]['title'] = 'Études révisées'
    published = client.post(f"/api/v1/planning-templates/{template['id']}/versions", json={
        'expected_revision': 0, 'definition': updated}).json()
    root, inputs, view = preview(client, ids, published['id'], revision=1)
    assert apply(client, root, inputs, view).status_code == 200
    with store[0]() as db:
        assert db.get(TaskPlan, applied['task_map']['design']).planned_hours == 8
    root, inputs, view = preview(client, ids, published['id'], revision=2, update_tasks=True)
    assert apply(client, root, inputs, view).status_code == 200
    with store[0]() as db:
        assert db.get(TaskPlan, applied['task_map']['group']).planned_hours == 24
        assert db.get(Task, applied['task_map']['design']).title == 'Études révisées'


def test_removed_template_tasks_and_manual_children_are_preserved(api, store, template):
    client, ids = api
    root, inputs, view = preview(client, ids, template['version']['id'])
    applied = apply(client, root, inputs, view).json()
    base = f"/api/v1/projects/{ids['projects'][0]}"
    manual = client.post(base + '/tasks', json={'title': 'Enfant manuel'}).json()
    changed = client.patch(base + f"/planning/tasks/{manual['id']}", json={
        'expected_revision': 2, 'parent_task_id': applied['task_map']['group'], 'planned_hours': 5})
    assert changed.status_code == 200
    updated = definition()
    updated['tasks'] = [updated['tasks'][0], updated['tasks'][2]]
    published = client.post(f"/api/v1/planning-templates/{template['id']}/versions", json={
        'expected_revision': 0, 'definition': updated}).json()
    root, inputs, view = preview(client, ids, published['id'], revision=3, update_tasks=True)
    assert apply(client, root, inputs, view).status_code == 200
    with store[0]() as db:
        assert db.get(TaskPlan, applied['task_map']['group']).planned_hours == 17
        assert db.get(Task, applied['task_map']['design']) is not None
        assert db.get(TaskPlan, manual['id']).planned_hours == 5


def test_foreign_or_duplicate_mapping_is_rejected_without_any_write(api, store, template):
    client, ids = api
    url = f"/api/v1/projects/{ids['projects'][0]}/planning/templates/{template['version']['id']}/preview"
    before = capture_baseline(store[2])
    for mapping in ({'pdr': ids['milestones'][1]}, {'pdr': ids['milestones'][0], 'cdr': ids['milestones'][0]},
                    {'absent': ids['milestones'][0]}):
        assert client.post(url, json={'expected_revision': 0, 'milestone_mapping': mapping}).status_code == 422
        assert capture_baseline(store[2]) == before


def test_mapping_does_not_create_two_open_steps_from_independent_legacy_milestones(api, store, template):
    client, ids = api
    base = f"/api/v1/projects/{ids['projects'][0]}"
    second = client.post(base + '/milestones', json={'title': 'Jalon complémentaire'}).json()['id']
    for expected, milestone_id in enumerate([ids['milestones'][0], second], start=1):
        assert client.patch(base + f'/planning/milestones/{milestone_id}', json={
            'expected_revision': expected, 'workflow_status': 'open'}).status_code == 200
    before = capture_baseline(store[2])
    url = base + f"/planning/templates/{template['version']['id']}/preview"
    assert client.post(url, json={'expected_revision': 3,
        'milestone_mapping': {'pdr': ids['milestones'][0], 'cdr': second}}).status_code == 422
    assert capture_baseline(store[2]) == before


def test_reader_can_preview_visible_generic_model_but_cannot_apply_or_publish(api, store, template, monkeypatch):
    client, ids = api
    monkeypatch.setenv('AGENT_OPERATOR_PROJECT_IDS', json.dumps([ids['projects'][0]]))
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'reader')
    before = capture_baseline(store[2])
    root, inputs, view = preview(client, ids, template['version']['id'])
    assert apply(client, root, inputs, view).status_code == 403
    assert client.get('/api/v1/planning-templates').json()['total'] == 1
    assert client.get(f"/api/v1/planning-templates/{template['id']}/versions").status_code == 200
    assert client.post(f"/api/v1/planning-templates/{template['id']}/versions", json={
        'expected_revision': 0, 'definition': definition()}).status_code == 403
    foreign = f"/api/v1/projects/{ids['projects'][1]}/planning/templates/{template['version']['id']}/preview"
    assert client.post(foreign, json=inputs).status_code == 404
    assert capture_baseline(store[2]) == before


def test_catalog_search_is_paged_and_archive_does_not_destroy_published_version(api, template):
    client, ids = api
    assert client.get('/api/v1/planning-templates', params={'search': 'CYCLE', 'limit': 1}).json()['total'] == 1
    assert client.get('/api/v1/planning-templates', params={'search': '%'}).json()['total'] == 0
    assert client.get('/api/v1/planning-templates', params={'limit': 201}).status_code == 422
    assert client.patch(f"/api/v1/planning-templates/{template['id']}", json={'expected_revision': 0, 'active': False}).status_code == 200
    assert client.get('/api/v1/planning-templates').json()['total'] == 0
    assert client.get('/api/v1/planning-templates', params={'include_inactive': True}).json()['total'] == 1
    assert client.get(f"/api/v1/planning-templates/{template['id']}/versions/{template['version']['id']}").status_code == 200
    url = f"/api/v1/projects/{ids['projects'][0]}/planning/templates/{template['version']['id']}/preview"
    assert client.post(url, json={'expected_revision': 0}).status_code == 409


def test_typology_templates_are_limited_to_visible_classifications(api, template, monkeypatch):
    client, ids = api
    reference = client.post('/api/v1/project-references', json={'kind': 'typology', 'code': 'SPEC', 'label': 'Spécial'}).json()
    classified = client.post('/api/v1/planning-templates', json={
        'code': 'SPECIAL', 'name': 'Planning spécial', 'typology_id': reference['id'], 'definition': definition()}).json()
    url = f"/api/v1/projects/{ids['projects'][0]}/planning/templates/{classified['version']['id']}/preview"
    assert client.post(url, json={'expected_revision': 0}).status_code == 422
    monkeypatch.setenv('AGENT_OPERATOR_PROJECT_IDS', json.dumps([ids['projects'][0]]))
    assert client.get('/api/v1/planning-templates').json()['total'] == 1
    assert client.get(f"/api/v1/planning-templates/{classified['id']}/versions").status_code == 404
    monkeypatch.delenv('AGENT_OPERATOR_PROJECT_IDS')
    assert client.patch(f"/api/v1/projects/{ids['projects'][0]}/identity", json={
        'expected_revision': 0, 'typology_id': reference['id']}).status_code == 200
    monkeypatch.setenv('AGENT_OPERATOR_PROJECT_IDS', json.dumps([ids['projects'][0]]))
    assert client.get('/api/v1/planning-templates').json()['total'] == 2
    assert client.post(url, json={'expected_revision': 0}).status_code == 200


def test_two_concurrent_publications_create_only_one_new_immutable_version(store, api, template):
    factory = store[0]

    def publish(_):
        try:
            with transaction(factory) as db:
                templates.publish_version(db, template['id'], PlanningTemplatePublish(
                    expected_revision=0, definition=TemplateDefinition.model_validate(definition())))
            return 201
        except HTTPException as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(publish, [1, 2])) == [201, 409]
    with factory() as db:
        assert [row.number for row in db.query(PlanningTemplateVersion).filter_by(template_id=template['id']).order_by(
            PlanningTemplateVersion.number)] == [1, 2]


def test_workflow_has_one_open_step_and_validation_opens_next_without_inventing_dates(api, store, template):
    client, ids = api
    root, inputs, view = preview(client, ids, template['version']['id'])
    applied = apply(client, root, inputs, view).json()
    first, second = (applied['milestone_map'][key] for key in ('reception', 'remise_offre'))
    base = f"/api/v1/projects/{ids['projects'][0]}/planning"
    assert client.patch(base + f'/milestones/{first}', json={'expected_revision': 1, 'workflow_status': 'open'}).status_code == 200
    before = capture_baseline(store[2])
    assert client.patch(base + f'/milestones/{second}', json={'expected_revision': 2, 'workflow_status': 'open'}).status_code == 409
    assert capture_baseline(store[2]) == before
    result = client.patch(base + f'/milestones/{first}', json={'expected_revision': 2, 'workflow_status': 'validated'}).json()
    assert result['opened_milestone_id'] == second
    assert result['milestone']['actual_date'] == ''
    with store[0]() as db:
        assert db.get(MilestonePlan, second).workflow_status == 'open'
        assert db.get(Milestone, second).actual_date == ''
    event = client.get(base + '/history').json()['items'][0]
    details = client.get(base + '/history/' + event['id']).json()
    status = {row['id']: row['workflow_status'] for row in details['value']['milestones']}
    assert status[first] == 'validated' and status[second] == 'open'
    repeated = client.patch(base + f'/milestones/{first}', json={'expected_revision': 3, 'workflow_status': 'validated'}).json()
    assert repeated['opened_milestone_id'] is None


def test_blocked_next_step_is_not_skipped_and_earlier_validation_keeps_current_open_step(api, store, template):
    client, ids = api
    root, inputs, view = preview(client, ids, template['version']['id'])
    mapping = apply(client, root, inputs, view).json()['milestone_map']
    base = f"/api/v1/projects/{ids['projects'][0]}/planning/milestones/"
    assert client.patch(base + mapping['remise_offre'], json={'expected_revision': 1, 'workflow_status': 'blocked'}).status_code == 200
    result = client.patch(base + mapping['reception'], json={'expected_revision': 2, 'workflow_status': 'validated'}).json()
    assert result['opened_milestone_id'] is None
    with store[0]() as db:
        assert db.get(MilestonePlan, mapping['recp_commande']).workflow_status == 'pending'
    assert client.patch(base + mapping['rlp'], json={'expected_revision': 3, 'workflow_status': 'open'}).status_code == 200
    result = client.patch(base + mapping['recp_commande'], json={'expected_revision': 4, 'workflow_status': 'validated'}).json()
    assert result['opened_milestone_id'] is None
    with store[0]() as db:
        assert db.get(MilestonePlan, mapping['rlp']).workflow_status == 'open'
        assert not any(row.actual_date for row in db.query(Milestone).filter_by(project_id=ids['projects'][0]))


def test_workflow_ignores_archived_and_explicitly_skipped_steps(api, template):
    client, ids = api
    root, inputs, view = preview(client, ids, template['version']['id'])
    mapping = apply(client, root, inputs, view).json()['milestone_map']
    base = f"/api/v1/projects/{ids['projects'][0]}/planning/milestones/"
    assert client.patch(base + mapping['remise_offre'], json={'expected_revision': 1, 'workflow_status': 'skipped'}).status_code == 200
    assert client.patch(base + mapping['recp_commande'], json={'expected_revision': 2, 'active': False}).status_code == 200
    out = client.patch(base + mapping['reception'], json={'expected_revision': 3, 'workflow_status': 'validated'}).json()
    assert out['opened_milestone_id'] == mapping['rlp']


def test_invalid_calendar_group_load_and_version_hash_have_explicit_errors(api, store, template):
    client, ids = api
    root = f"/api/v1/projects/{ids['projects'][0]}/planning/templates/{template['version']['id']}"
    before = capture_baseline(store[2])
    for values in ({'start_date': '9999-12-31'}, {'excluded_dates': ['']}, {'excluded_dates': ['2026-10-05', '2026-10-05']}):
        response = client.post(root + '/preview', json={'expected_revision': 0, **values})
        assert response.status_code == 422
    large = definition()
    large['tasks'][1]['planned_hours'] = large['tasks'][2]['planned_hours'] = 600000
    assert client.post(f"/api/v1/planning-templates/{template['id']}/versions", json={
        'expected_revision': 0, 'definition': large}).status_code == 422
    assert capture_baseline(store[2]) == before
    with transaction(store[0]) as db:
        row = PlanningTemplateVersion(template_id=template['id'], number=2,
                                      definition=json.dumps(definition()), sha256='0' * 64, actor_id='recette')
        db.add(row)
        db.flush()
        invalid_id = row.id
    invalid = f"/api/v1/projects/{ids['projects'][0]}/planning/templates/{invalid_id}/preview"
    assert client.post(invalid, json={'expected_revision': 0}).status_code == 409


def test_adding_first_child_to_previous_leaf_requires_explicit_task_update(api, template):
    client, ids = api
    leaf = definition()
    leaf['tasks'] = [{'key': 'group', 'title': 'Travail initial', 'planned_hours': 40}]
    first = client.post('/api/v1/planning-templates', json={
        'code': 'EVOLUTIF', 'name': 'Modèle évolutif', 'definition': leaf}).json()
    root, inputs, view = preview(client, ids, first['version']['id'])
    assert apply(client, root, inputs, view).status_code == 200
    updated = definition()
    second = client.post(f"/api/v1/planning-templates/{first['id']}/versions", json={
        'expected_revision': 0, 'definition': updated}).json()
    root = f"/api/v1/projects/{ids['projects'][0]}/planning/templates/{second['id']}"
    assert client.post(root + '/preview', json={'expected_revision': 1}).status_code == 422
    root, inputs, view = preview(client, ids, second['id'], revision=1, update_tasks=True)
    assert view['changes']['planned_hours_delta'] == -28
    assert apply(client, root, inputs, view).status_code == 200
