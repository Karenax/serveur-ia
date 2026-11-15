"""Read-only, sourced identification values; overrides belong to one document."""
from datetime import date

from fastapi import HTTPException

from ..models import Project
from ..project_identity_models import ProjectMember, ProjectPerson, ProjectProfile, ProjectReference
from .document_template_catalogue import catalogue
from .planning_revision import revision
from .project_identity import _project


def project_values(db, project_id, *, overrides=None):
    _project(db, project_id)
    project = db.get(Project, project_id)
    fields = catalogue()['fields']
    overrides = {} if overrides is None else overrides
    if (not isinstance(overrides, dict) or not set(overrides).issubset(fields)
            or any(fields[key]['edit_scope'] is None for key in overrides)):
        raise HTTPException(422, 'Corrections documentaires non financières autorisées uniquement')
    for value in overrides.values():
        if (not isinstance(value, str) or len(value) > 10_000
                or any(ord(char) < 32 and char not in '\t\n\r' for char in value)
                or any(0xD800 <= ord(char) <= 0xDFFF or ord(char) in {0xFFFE, 0xFFFF} for char in value)):
            raise HTTPException(422, 'Correction documentaire textuelle invalide')
    profile = db.get(ProjectProfile, project_id)
    values = {key: '' for key in fields}
    origins = {key: {'kind': 'missing', 'record_id': None, 'attribute': None} for key in fields}

    def assign(key, value, *, kind, record_id, attribute):
        if value is not None and str(value).strip():
            values[key] = str(value).strip()
            origins[key] = {'kind': kind, 'record_id': record_id, 'attribute': attribute}

    assign('project_code', project.code, kind='project', record_id=project_id, attribute='code')
    assign('offer_number', project.offer_number, kind='project', record_id=project_id, attribute='offer_number')
    assign('description', project.title, kind='project', record_id=project_id, attribute='title')
    assign('client_name', project.client_name, kind='project', record_id=project_id, attribute='client_name')
    warnings = []
    manager = None
    if profile:
        for key, attribute in (('description', 'description'), ('client_reference', 'client_reference'),
                ('equipment_number', 'equipment_number'), ('client_responsible', 'client_contact'),
                ('client_requester', 'client_contact')):
            assign(key, getattr(profile, attribute), kind='project_profile', record_id=project_id, attribute=attribute)
        if profile.client_id:
            client = db.get(ProjectReference, profile.client_id)
            if client and client.kind == 'client':
                assign('client_name', client.label, kind='client', record_id=client.id, attribute='label')
                if not client.active:
                    warnings.append('client_archived')
            else:
                values['client_name'] = ''
                origins['client_name'] = {'kind': 'missing', 'record_id': profile.client_id, 'attribute': 'label'}
                warnings.append('client_reference_missing')
        if profile.responsible_id:
            manager = db.get(ProjectPerson, profile.responsible_id)
            if manager is None:
                warnings.append('responsible_reference_missing')
        if profile.agency_id:
            # L1 has code/label only. Never infer a city/phone from its label.
            warnings.append('agency_contact_details_not_configured')
    if manager is None and not (profile and profile.responsible_id):
        member = db.query(ProjectMember).filter_by(project_id=project_id, role='responsable_projet', active=True).first()
        if member:
            manager = db.get(ProjectPerson, member.person_id)
    if manager:
        for key, attribute in (('project_manager_trigram', 'trigram'), ('project_manager_first_name', 'first_name'),
                ('project_manager_last_name', 'last_name'), ('project_manager_email', 'email'),
                ('project_manager_phone', 'phone')):
            assign(key, getattr(manager, attribute), kind='person', record_id=manager.id, attribute=attribute)
        name = ' '.join(str(value or '').strip() for value in (manager.first_name, manager.last_name)).strip()
        assign('project_manager_full_name', name, kind='person', record_id=manager.id, attribute='first_name+last_name')
        if not manager.active:
            warnings.append('responsible_archived')
    assign('today', date.today().strftime('%d/%m/%Y'), kind='server_date', record_id=None, attribute='local_date')
    for key, value in overrides.items():
        values[key] = value
        origins[key] = {'kind': 'document_override', 'record_id': None, 'attribute': key}
    return {'project_id': project_id, 'identity_revision': profile.revision if profile else 0,
            'planning_revision': revision(db, project_id), 'values': values,
            'origins': origins, 'fields': fields, 'missing_fields': sorted(key for key, value in values.items() if not value.strip()),
            'oversized_fields': sorted(key for key, value in values.items() if len(value) > 10_000),
            'warnings': warnings, 'overrides_scope': 'one_document', 'read_only': True}
