"""Sourced identity fields and document-only overrides on isolated stores."""
from datetime import date

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db import Base
from backend.app.models import Project
from backend.app.project_identity_models import IDENTITY_TABLES, ProjectMember, ProjectPerson, ProjectProfile, ProjectReference
from backend.app.project_planning_models import ProjectPlanningState
from backend.app.services.document_project_values import project_values
from backend.app.services.project_operator import Operator, operator_context


@pytest.fixture
def store(tmp_path):
    engine = create_engine(f'sqlite:///{tmp_path / "values.db"}')
    Base.metadata.create_all(engine, tables=[Project.__table__, *IDENTITY_TABLES, ProjectPlanningState.__table__])
    factory = sessionmaker(bind=engine)
    with factory() as db:
        project = Project(code='AIRB26LTH0205-A', title='LED 2026', client_name='Client historique', offer_number='OFF-0205')
        other = Project(code='OTHER', title='Autre projet')
        db.add_all([project, other])
        db.commit()
        ids = project.id, other.id
    yield factory, ids
    engine.dispose()


def test_legacy_defaults_missing_fields_no_implicit_profile_or_finance(store):
    factory, ids = store
    with factory() as db:
        result = project_values(db, ids[0])
        assert result['values']['project_code'] == 'AIRB26LTH0205-A'
        assert result['values']['offer_number'] == 'OFF-0205'
        assert result['values']['description'] == 'LED 2026'
        assert result['values']['client_name'] == 'Client historique'
        assert result['values']['today'] == date.today().strftime('%d/%m/%Y')
        assert result['identity_revision'] == result['planning_revision'] == 0
        assert result['origins']['client_name']['attribute'] == 'client_name'
        assert 'agency_city' in result['missing_fields']
        assert not {'hourly_rate', 'margin_pct', 'tdao_prix_vente'} & set(result['values'])
        assert db.query(ProjectProfile).count() == db.query(ProjectPlanningState).count() == 0
        assert not db.new and not db.dirty and not db.deleted


def test_profile_reference_person_provenance_and_separate_revisions(store):
    factory, ids = store
    with factory() as db:
        client = ProjectReference(kind='client', code='CLIENT', normalized_code='client', label='Client actuel')
        agency = ProjectReference(kind='agency', code='AG', normalized_code='ag', label='Agence avec libellé')
        person = ProjectPerson(first_name='Élodie', last_name='Durand', trigram='EDU', email='test@example.invalid', phone='010203')
        db.add_all([client, agency, person])
        db.flush()
        profile = ProjectProfile(project_id=ids[0], client_id=client.id, agency_id=agency.id, responsible_id=person.id,
            description='Outillage actuel', client_reference='Commande 123', client_contact='Contact commun', equipment_number='LED-26', revision=5)
        db.add_all([profile, ProjectPlanningState(project_id=ids[0], revision=9, excluded_dates=[])])
        db.commit()
        result = project_values(db, ids[0])
        assert result['values']['client_name'] == 'Client actuel'
        assert result['values']['description'] == 'Outillage actuel'
        assert result['values']['project_manager_full_name'] == 'Élodie Durand'
        assert result['values']['project_manager_trigram'] == 'EDU'
        assert result['values']['client_requester'] == result['values']['client_responsible'] == 'Contact commun'
        assert result['origins']['client_requester'] == result['origins']['client_responsible']
        assert result['origins']['project_manager_full_name']['record_id'] == person.id
        assert result['identity_revision'] == 5 and result['planning_revision'] == 9
        assert result['values']['agency_city'] == ''
        assert 'agency_contact_details_not_configured' in result['warnings']
        assert not db.new and not db.dirty and not db.deleted


def test_responsible_team_fallback_ignores_inactive_members(store):
    factory, ids = store
    with factory() as db:
        former = ProjectPerson(first_name='Ancien', last_name='Responsable')
        current = ProjectPerson(first_name='Actuel', last_name='Responsable')
        db.add_all([former, current])
        db.flush()
        db.add_all([ProjectMember(project_id=ids[0], person_id=former.id, role='responsable_projet', active=False),
                    ProjectMember(project_id=ids[0], person_id=current.id, role='responsable_projet', active=True)])
        db.commit()
        assert project_values(db, ids[0])['values']['project_manager_first_name'] == 'Actuel'


def test_one_document_override_does_not_write_project_or_contact(store):
    factory, ids = store
    with factory() as db:
        result = project_values(db, ids[0], overrides={'client_name': 'Texte propre au document', 'agency_city': 'Nantes'})
        assert result['overrides_scope'] == 'one_document'
        assert result['origins']['client_name']['kind'] == 'document_override'
        assert result['values']['agency_city'] == 'Nantes'
        assert db.get(Project, ids[0]).client_name == 'Client historique'
        assert db.query(ProjectProfile).count() == 0
        assert not db.new and not db.dirty and not db.deleted
        assert project_values(db, ids[0])['values']['agency_city'] == ''


@pytest.mark.parametrize('override', [{'hourly_rate': '42'}, {'project_code': 'FAKE'}, {'today': '1999-01-01'},
                                    {'client_name': 3}, {'description': '\x01'}, {'description': '\ud800'}])
def test_financial_immutable_or_invalid_overrides_refused(store, override):
    factory, ids = store
    with factory() as db, pytest.raises(HTTPException) as error:
        project_values(db, ids[0], overrides=override)
    assert error.value.status_code == 422


def test_reader_scope_and_archived_reference_warning(store):
    factory, ids = store
    with factory() as db:
        client = ProjectReference(kind='client', code='OLD', normalized_code='old', label='Client archivé', active=False)
        db.add(client)
        db.flush()
        db.add(ProjectProfile(project_id=ids[0], client_id=client.id))
        db.commit()
        with operator_context(Operator('reader', 'reader', frozenset({ids[0]}))):
            result = project_values(db, ids[0])
            assert result['values']['client_name'] == 'Client archivé' and 'client_archived' in result['warnings']
            with pytest.raises(HTTPException) as error:
                project_values(db, ids[1])
            assert error.value.status_code == 404


def test_long_project_description_is_reported_without_truncating_or_rewriting_it(store):
    factory, ids = store
    long_description = 'Texte ' * 2500
    with factory() as db:
        db.add(ProjectProfile(project_id=ids[0], description=long_description))
        db.commit()
        result = project_values(db, ids[0])
        assert result['oversized_fields'] == ['description']
        assert result['values']['description'] == long_description.strip()
        assert db.get(ProjectProfile, ids[0]).description == long_description
        corrected = project_values(db, ids[0], overrides={'description': 'Désignation courte pour cette copie'})
        assert corrected['oversized_fields'] == []
        assert db.get(ProjectProfile, ids[0]).description == long_description
