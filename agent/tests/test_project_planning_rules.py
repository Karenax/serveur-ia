"""L2 contracts: keep legacy planning, reject cycles, preserve baseline evidence."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import date
import json

import pytest
from pydantic import ValidationError

from backend.app.services.project_planning_rules import (
    MilestoneSpec, PlanningSnapshot, TaskSpec, TemplateDefinition, WorkCalendar,
    capture_snapshot, compare_snapshots, default_template, legacy_mapping_proposals,
    preview_template, validate_parent,
)


def test_default_workflow_is_a_neutral_preview_without_invented_dates():
    definition = default_template()
    view = preview_template(definition, date(2026, 10, 5))
    assert len(view["milestones"]) == 14
    assert [value["code"] for value in view["milestones"]][4:8] == ["kom", "pdr", "cdr", "fdr"]
    assert all(not value[field] for value in view["milestones"]
               for field in ("forecast_date", "contractual_date", "actual_date"))
    assert view["application_required"] is True
    # Every call returns its own version value, without changing the standard.
    definition.milestones[0].title = "Autre réception"
    assert default_template().milestones[0].title == "Réception"


def test_existing_eight_milestones_are_only_mapping_proposals():
    titles = ["Lancement du projet", "Validation du CDC", "Revue de conception",
              "Fin des études", "FAT", "Livraison", "SAT", "Réception définitive"]
    rows = [{"id": str(index), "title": title, "actual_date": "2026-10-02",
             "date_sources": {"actual_date": {"source_id": "mail-conservé"}}}
            for index, title in enumerate(titles)]
    previous = deepcopy(rows)
    proposals = legacy_mapping_proposals(rows)
    assert rows == previous
    assert [value["milestone_id"] for value in proposals] == [value["id"] for value in rows]
    assert proposals[0]["suggested_code"] == "kom"
    assert proposals[5]["suggested_code"] == "livraison"
    assert all(value["human_confirmation_required"] for value in proposals)
    assert all(proposals[index]["suggested_code"] is None for index in (1, 2, 3, 4, 6, 7))


def test_working_dates_skip_weekends_and_explicit_exclusions_only():
    dates = {date(2026, 10, 5)}
    calendar = WorkCalendar(dates)
    dates.clear()
    assert calendar.add_workdays(date(2026, 10, 2), 1) == date(2026, 10, 6)
    assert calendar.add_workdays(date(2026, 10, 6), -1) == date(2026, 10, 2)
    assert calendar.add_workdays(date(2026, 10, 3), 0) == date(2026, 10, 3)
    assert WorkCalendar().add_workdays(date(2026, 10, 2), 1) == date(2026, 10, 5)
    with pytest.raises(ValueError):
        calendar.add_workdays(date(2026, 10, 2), True)


def test_preview_parent_dates_and_hours_derive_without_double_counting():
    definition = TemplateDefinition(name="Études", milestones=[MilestoneSpec(code="cdr", title="CDR", offset_workdays=2)],
        tasks=[TaskSpec(key="lot", title="Lot BE"), TaskSpec(key="sub", title="Sous-lot", parent_key="lot"),
               TaskSpec(key="be", title="Études", parent_key="sub", planned_hours=8, design=True,
                        start_offset_workdays=0, end_offset_workdays=1),
               TaskSpec(key="check", title="Contrôle", parent_key="lot", planned_hours=4,
                        start_offset_workdays=1, end_offset_workdays=2)])
    view = preview_template(definition, date(2026, 10, 2))
    parent = next(value for value in view["tasks"] if value["key"] == "lot")
    assert view["planned_hours"] == parent["planned_hours"] == 12
    assert parent["start_date"] == "2026-10-02" and parent["end_date"] == "2026-10-06"
    assert view["milestones"][0]["forecast_date"] == "2026-10-06"
    assert not view["milestones"][0]["actual_date"] and not view["milestones"][0]["contractual_date"]
    assert definition.tasks[0].planned_hours == 0


def test_missing_child_dates_are_not_hidden_by_parent_aggregation():
    definition = TemplateDefinition(name="Sans échéance", milestones=[MilestoneSpec(code="end", title="Fin")],
        tasks=[TaskSpec(key="p", title="Parent"),
               TaskSpec(key="a", title="A", parent_key="p", start_offset_workdays=1, end_offset_workdays=2),
               TaskSpec(key="b", title="B", parent_key="p", start_offset_workdays=1)])
    parent = preview_template(definition, date(2026, 10, 2))["tasks"][0]
    assert parent["start_date"] == "2026-10-05" and parent["end_date"] == ""
    assert preview_template(definition, None)["tasks"][0]["start_date"] == ""


@pytest.mark.parametrize("patch", [
    {"tasks": [{"key": "a", "title": "A", "parent_key": "a"}]},
    {"tasks": [{"key": "a", "title": "A", "parent_key": "b"}, {"key": "b", "title": "B", "parent_key": "a"}]},
    {"tasks": [{"key": "a", "title": "A", "parent_key": "missing"}]},
    {"tasks": [{"key": "a", "title": "A", "milestone_code": "missing"}]},
    {"tasks": [{"key": "a", "title": "A"}, {"key": "a", "title": "Autre A"}]},
    {"milestones": [{"code": "end", "title": "A"}, {"code": "end", "title": "B"}]},
    {"tasks": [{"key": "p", "title": "Parent", "planned_hours": 8}, {"key": "a", "title": "A", "parent_key": "p"}]},
    {"tasks": [{"key": "p", "title": "Parent", "end_offset_workdays": 0}, {"key": "a", "title": "A", "parent_key": "p"}]},
    {"tasks": [{"key": "a", "title": "A", "start_offset_workdays": 2, "end_offset_workdays": 1}]},
    {"tasks": [{"key": "a", "title": "A", "planned_hours": float("inf")}]},
    {"hourly_rate": 85},
])
def test_invalid_template_graph_dates_or_financial_fields_are_rejected(patch):
    with pytest.raises(ValidationError):
        TemplateDefinition.model_validate({"name": "Modèle", "milestones": [{"code": "end", "title": "Fin"}], **patch})


def test_parent_chain_must_remain_inside_the_project():
    records = {"a": {"id": "a", "project_id": "p", "parent_id": None},
               "b": {"id": "b", "project_id": "q", "parent_id": None}}
    with pytest.raises(ValueError, match="parente absente"):
        validate_parent(records, "p", "a", "b")
    with pytest.raises(ValueError, match="absente du projet"):
        validate_parent(records, "q", "a", None)


def test_mutated_template_is_revalidated_before_preview():
    definition = default_template()
    definition.tasks = [TaskSpec(key="a", title="A", parent_key="a")]
    with pytest.raises(ValidationError):
        preview_template(definition, None)


def test_snapshot_preserves_dates_and_evidence_after_source_mutation():
    milestones = [{"id": "fat", "project_id": "p", "title": "FAT", "status": "todo",
                   "actual_date": "2026-10-02", "contractual_date": "2026-10-01",
                   "date_sources": {"actual_date": {"source_id": "mail", "quote": "FAT le 02/10/2026"}},
                   "hourly_rate": 85}]
    before = capture_snapshot("p", milestones, [])
    milestones[0]["actual_date"] = "2026-10-05"
    milestones[0]["date_sources"]["actual_date"]["quote"] = "Nouvelle preuve"
    frozen = json.loads(before.payload)["milestones"][0]
    assert frozen["actual_date"] == "2026-10-02" and frozen["status"] == "todo"
    assert frozen["date_sources"]["actual_date"]["quote"] == "FAT le 02/10/2026"
    assert "hourly_rate" not in frozen
    diff = compare_snapshots(before, capture_snapshot("p", milestones, []))
    assert {value["field"] for value in diff["changes"]} == {"actual_date", "date_sources"}
    assert next(value for value in diff["changes"] if value["field"] == "actual_date")["severity"] == "high"
    with pytest.raises(FrozenInstanceError):
        before.payload = "modifié"


def test_snapshot_diff_tracks_stable_ids_and_root_hours_without_double_counting():
    tasks = [{"id": "p", "title": "Lot", "parent_id": None, "planned_hours": 12},
             {"id": "a", "title": "A", "parent_id": "p", "planned_hours": 8},
             {"id": "b", "title": "B", "parent_id": "p", "planned_hours": 4}]
    before = capture_snapshot("project", [], tasks)
    assert capture_snapshot("project", [], list(reversed(tasks))) == before
    # A stale parent total is not used to conceal the actual change in leaves.
    tasks[0]["planned_hours"] = 12
    tasks[1]["planned_hours"] = 12
    tasks[1]["title"] = "Études détaillées"
    diff = compare_snapshots(before, capture_snapshot("project", [], tasks))
    assert diff["planned_hours_delta"] == 4
    assert {value["id"] for value in diff["changes"]} == {"a"}


@pytest.mark.parametrize("tasks", [
    [{"id": "a", "parent_id": "missing"}],
    [{"id": "a", "parent_id": "b"}, {"id": "b", "parent_id": "a"}],
    [{"id": "a", "milestone_id": "foreign"}],
])
def test_snapshot_refuses_broken_planning_relations(tasks):
    with pytest.raises(ValueError):
        capture_snapshot("p", [], tasks)


def test_snapshot_foreign_rows_duplicate_ids_and_corrupt_integrity_are_rejected():
    with pytest.raises(ValueError, match="autre projet"):
        capture_snapshot("p", [{"id": "x", "project_id": "q"}], [])
    with pytest.raises(ValueError, match="dupliqué"):
        capture_snapshot("p", [{"id": "x"}, {"id": "x"}], [])
    before = capture_snapshot("p", [], [])
    with pytest.raises(ValueError, match="Empreinte"):
        compare_snapshots(before, PlanningSnapshot(before.payload + " ", before.sha256))
    with pytest.raises(ValueError, match="projets différents"):
        compare_snapshots(before, capture_snapshot("q", [], []))


def test_project_commitments_are_frozen_and_budget_is_separate_from_task_load():
    values = {'start_date': '2026-10-01', 'planned_end_date': '2026-12-01', 'budget_hours': 0}
    tasks = [{'id': 'a', 'planned_hours': 8}]
    frozen = capture_snapshot('p', [], tasks, project=values)
    values.update(start_date='2026-10-02', planned_end_date='2026-12-02', budget_hours=100)
    tasks[0]['planned_hours'] = 12
    stored = json.loads(frozen.payload)
    assert stored['version'] == 2 and stored['project']['budget_hours'] == 0
    diff = compare_snapshots(frozen, capture_snapshot('p', [], tasks, project=values))
    assert diff['project_comparison_available'] is True
    assert diff['project_budget_hours_delta'] == 100 and diff['planned_hours_delta'] == 4
    assert {row['field'] for row in diff['changes'] if row['kind'] == 'project'} == set(values)
    assert all(row['severity'] == 'high' for row in diff['changes'] if row['kind'] == 'project')


def test_legacy_references_do_not_invent_missing_project_commitments():
    frozen = capture_snapshot('p', [], [])
    current = capture_snapshot('p', [], [], project={'start_date': '', 'planned_end_date': '', 'budget_hours': 20})
    diff = compare_snapshots(frozen, current)
    assert json.loads(frozen.payload)['version'] == 1 and 'project' not in json.loads(frozen.payload)
    assert diff['changes'] == [] and diff['project_comparison_available'] is False
    assert diff['project_budget_hours_delta'] is None


@pytest.mark.parametrize('patch', [
    {'budget_hours': True}, {'budget_hours': '8'}, {'budget_hours': -1}, {'budget_hours': float('nan')},
    {'budget_hours': float('inf')}, {'budget_hours': 1000000000001}, {'budget_hours': None},
    {'start_date': '20261001'}, {'start_date': None}, {'planned_end_date': '2026-02-30'},
    {'start_date': '2026-12-02'}, {'hourly_rate': 90},
])
def test_invalid_or_financial_project_snapshot_values_are_rejected(patch):
    with pytest.raises(ValueError):
        capture_snapshot('p', [], [], project={'start_date': '2026-10-01', 'planned_end_date': '2026-12-01', 'budget_hours': 8, **patch})
