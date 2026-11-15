"""Typed RLP closure and restore bindings; no DB, DDL or filesystem writes.

Published snapshots, PDFs and event payloads stay byte-for-byte unchanged.
Flat, namespaced bindings resolve their captured identities in the restored
project. Live draft content is remapped only at known reference fields.
"""
import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from typing import Annotated, Literal

from fastapi import HTTPException
from pydantic import Field, TypeAdapter, model_validator

from app.services.deliverable_manifest import check_snapshot, freeze
from ..project_identity_schemas import MemberRole
from ..project_review_schemas import ReviewContent
from ..schemas import DomainInput

PROJECT_TABLES = frozenset({'project_reviews', 'project_review_publications', 'project_review_events'})
ACTIONS = frozenset({'review_created', 'review_saved', 'review_revision_created',
                     'review_recording_imported', 'review_published'})
MAX_ROWS = 100000
MAX_SNAPSHOT_BYTES = 100 * 1024 * 1024
MAX_PDF_BYTES = 10 * 1024 * 1024
Identity = Annotated[str, Field(min_length=1, max_length=36)]
Digest = Annotated[str, Field(pattern=r'^[a-f0-9]{64}$')]


def embedded_bytes(tables):
    """Count review JSON plus decoded PDFs against transport's total bound."""
    total = 0
    for name in PROJECT_TABLES:
        for row in tables.get(name, []):
            value = {key:item for key,item in row.items() if key!='pdf_base64'}
            try:
                total += len(json.dumps(value, ensure_ascii=False).encode('utf-8'))
                if 'pdf_base64' in row:
                    encoded = row['pdf_base64']
                    if not isinstance(encoded, str) or len(encoded) > (MAX_PDF_BYTES + 2) // 3 * 4:
                        raise ValueError('PDF encodé trop volumineux')
                    total += len(base64.b64decode(encoded, validate=True))
            except (TypeError, ValueError) as exc:
                invalid(str(exc))
    return total


class Evidence(DomainInput):
    recording_id: Identity
    brain_project_id: Identity
    erp_project_id: Identity
    source_id: Identity
    revision: int = Field(ge=1)
    summary_model: str = Field(max_length=512)
    summary_sha256: Digest
    segment_id: str = Field(min_length=1, max_length=64)
    quote: str = Field(min_length=1, max_length=1500)
    text: str = Field(min_length=1, max_length=10000)
    speaker: str = Field(min_length=1, max_length=120)
    start: float = Field(ge=0, le=7200, allow_inf_nan=False)
    end: float = Field(ge=0, le=7200, allow_inf_nan=False)

    @model_validator(mode='after')
    def literal_quote(self):
        # Same normalization as the audio service, without importing its worker
        # and database runtime during a read-only archive preflight.
        normal = lambda value: ' '.join(value.casefold().split())  # noqa: E731
        if self.end < self.start or not self.quote.strip() or normal(self.quote) not in normal(self.text):
            raise ValueError('Citation ou horodatage différent de la transcription conservée')
        return self


class ReviewValue(DomainInput):
    id: Identity
    number: int = Field(ge=1)
    type_code: Literal['rlp']
    status: Literal['draft', 'published']
    review_revision: int = Field(ge=1)
    previous_review_id: Identity | None
    content: ReviewContent
    provenance: dict[Identity, Evidence] = Field(max_length=10000)

    @model_validator(mode='after')
    def known_evidence(self):
        if any(key not in self.provenance for item in self.content.items for key in item.evidence_ids):
            raise ValueError('Preuve absente du point de revue')
        return self


class FrozenProject(DomainInput):
    id: Identity
    code: str = Field(max_length=64)
    title: str = Field(max_length=256)


class FrozenMember(DomainInput):
    person_id: Identity
    role: MemberRole
    name: str = Field(min_length=1, max_length=241)


class Progress(DomainInput):
    completed: int = Field(ge=0)
    total: int = Field(ge=0)
    percentage: float = Field(ge=0, le=100, allow_inf_nan=False)
    state: str = Field(min_length=1, max_length=32)

    @model_validator(mode='after')
    def counts(self):
        if self.completed > self.total:
            raise ValueError('Compteurs publiés incohérents')
        return self


class Blocker(DomainInput):
    id: Identity
    label: str = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=1, max_length=2000)


class FrozenDocument(DomainInput):
    id: Identity
    title: str = Field(min_length=1, max_length=500)
    legacy_status: str = Field(max_length=32)
    project_id: Identity
    revision: int = Field(ge=0)
    document_status: Literal['draft', 'to_verify', 'validated', 'to_revise', 'archived']
    active: bool
    comment: str = Field(max_length=20000)
    responsible_id: Identity | None
    verifier_id: Identity | None
    type_version_id: Identity | None
    latest_version_id: Identity | None
    checklist: list[dict] = Field(max_length=MAX_ROWS)
    progress: Progress
    transverse_progress: Progress
    validation_blockers: list[Blocker] = Field(max_length=MAX_ROWS)
    milestone_ids: list[Identity] = Field(max_length=MAX_ROWS)

    @model_validator(mode='after')
    def known_checks(self):
        from .project_deliverable_rules import progress, validation_blockers
        for check in self.checklist:
            check_snapshot(check)
        ids = [item['id'] for item in self.checklist]
        if len(ids) != len(set(ids)) or len(self.milestone_ids) != len(set(self.milestone_ids)):
            raise ValueError('Contrôle ou jalon publié dupliqué')
        if any(blocker.id not in ids for blocker in self.validation_blockers):
            raise ValueError('Blocage sans contrôle publié')
        if (self.progress.model_dump()!=progress(self.checklist)
                or self.transverse_progress.model_dump()!=progress(self.checklist, transverse=True)
                or [row.model_dump() for row in self.validation_blockers]!=validation_blockers(self.checklist, self.latest_version_id)):
            raise ValueError('Compteurs ou visas différents des contrôles capturés')
        return self


class Snapshot(DomainInput):
    format: Literal['agent-project-review']
    version: Literal[1]
    publication_id: Identity
    project: FrozenProject
    review: ReviewValue
    published_by: str = Field(min_length=1, max_length=120)
    published_at: str = Field(min_length=1, max_length=64)
    deliverables: list[FrozenDocument] = Field(min_length=1, max_length=100)
    team: list[FrozenMember] = Field(min_length=1, max_length=MAX_ROWS)

    @model_validator(mode='after')
    def publication_gate(self):
        datetime.fromisoformat(self.published_at)
        content = self.review.content
        sections = {item.section_code for item in content.items}
        if (self.review.status != 'published' or not content.meeting_date or not content.participants
                or not {'vigilance_points', 'expected_functions', 'initial_constraints'}.issubset(sections)
                or any(not item.reviewed for item in content.items)):
            raise ValueError('Publication sans conditions de revue vérifiées')
        ids = [doc.id for doc in self.deliverables]
        if (len(set(ids)) != len(ids) or set(ids) != set(content.deliverable_ids)
                or any(not doc.active or doc.project_id != self.project.id for doc in self.deliverables)):
            raise ValueError('Livrables capturés différents de la revue publiée')
        return self


class Bindings(DomainInput):
    erp: dict[Identity, Identity] = Field(default_factory=dict, max_length=MAX_ROWS)
    brain: dict[Identity, Identity] = Field(default_factory=dict, max_length=MAX_ROWS)


def invalid(message):
    raise HTTPException(400, 'Archive de RLP : ' + message)


def timestamp(value):
    stamp = datetime.fromisoformat(value)
    return (stamp.replace(tzinfo=timezone.utc) if stamp.tzinfo is None else stamp).astimezone(timezone.utc)


def review_value(value):
    parsed = ReviewValue.model_validate(value, strict=True)
    if parsed.model_dump() != value:
        raise ValueError('Champs de contenu ou de preuve absents')
    return parsed


def decode_snapshot(row):
    try:
        payload = row['snapshot']
        if (not isinstance(payload, str) or len(payload.encode('utf-8')) > MAX_SNAPSHOT_BYTES
                or hashlib.sha256(payload.encode('utf-8')).hexdigest() != row['sha256']):
            raise ValueError('Empreinte ou taille de publication invalide')
        value = json.loads(payload)
        if not isinstance(value, dict) or type(value.get('version')) is not int:
            raise ValueError('Version de publication invalide')
        parsed = Snapshot.model_validate(value, strict=True)
        if parsed.model_dump() != value or freeze(value)[0] != payload:
            raise ValueError('Publication non canonique')
        pdf64 = row['pdf_base64']
        if not isinstance(pdf64, str) or len(pdf64) > (MAX_PDF_BYTES + 2) // 3 * 4:
            raise ValueError('PDF encodé trop volumineux')
        pdf = base64.b64decode(pdf64, validate=True)
        if (len(pdf) > MAX_PDF_BYTES or not pdf.startswith(b'%PDF-') or hashlib.sha256(pdf).hexdigest() != row['pdf_sha256']
                or base64.b64encode(pdf).decode('ascii') != pdf64):
            raise ValueError('PDF différent de la publication')
        return value
    except (ValueError, TypeError, KeyError) as exc:
        invalid(str(exc))


def value_references(value):
    """Collect only material references; point/evidence IDs and text are local."""
    if not value:
        return {'erp': set(), 'brain': set()}
    if set(value) == {'previous_review_id'}:
        TypeAdapter(Identity).validate_python(value['previous_review_id'], strict=True)
        return {'erp': {value['previous_review_id']}, 'brain': set()}
    review_value(value)
    content = value['content']
    erp = {value['id'], *content['deliverable_ids']}
    erp.update(key for key in (value['previous_review_id'], content['milestone_id']) if key)
    erp.update(person['person_id'] for person in content['participants'] if person['person_id'])
    brain = set()
    for proof in value['provenance'].values():
        erp.add(proof['erp_project_id'])
        brain.update(proof[key] for key in ('recording_id', 'brain_project_id', 'source_id'))
    return {'erp': erp, 'brain': brain}


def publication_references(value):
    result = value_references(value['review'])
    erp = result['erp']
    erp.update((value['publication_id'], value['project']['id']))
    erp.update(row['person_id'] for row in value['team'])
    for doc in value['deliverables']:
        erp.update((doc['id'], doc['project_id'], *doc['milestone_ids']))
        erp.update(doc[key] for key in ('responsible_id', 'verifier_id', 'type_version_id', 'latest_version_id') if doc[key])
        for check in doc['checklist']:
            erp.update(check[key] for key in ('id', 'milestone_id', 'completed_version_id') if check[key])
    return result


def frozen_bindings(row, references):
    raw = row.get('bindings', {})
    try:
        if not isinstance(raw, dict):
            raise ValueError('Correspondances invalides')
        bindings = Bindings.model_validate(raw, strict=True).model_dump()
        if raw and (set(raw) != {'erp', 'brain'} or any(set(bindings[space]) != references[space] for space in bindings)):
            raise ValueError('Correspondances absentes, inutilisées ou hors capture')
        return bindings
    except ValueError as exc:
        invalid(str(exc))


def rebind(row, references, erp_mapping, brain_mapping):
    old = frozen_bindings(row, references)
    result = {'erp': {}, 'brain': {}}
    for space, mapping in (('erp', erp_mapping), ('brain', brain_mapping)):
        for captured in references[space]:
            current = old[space].get(captured, captured)
            if current not in mapping:
                invalid('Identité capturée absente du remappage ' + space)
            result[space][captured] = mapping[current]
    return result


def remap_live_value(value, erp_mapping, brain_mapping):
    value = deepcopy(value)
    for key in ('id', 'previous_review_id'):
        if value.get(key):
            value[key] = erp_mapping[value[key]]
    content = value['content']
    if content['milestone_id']:
        content['milestone_id'] = erp_mapping[content['milestone_id']]
    content['deliverable_ids'] = [erp_mapping[key] for key in content['deliverable_ids']]
    for person in content['participants']:
        if person['person_id']:
            person['person_id'] = erp_mapping[person['person_id']]
    for proof in value['provenance'].values():
        proof['erp_project_id'] = erp_mapping[proof['erp_project_id']]
        for key in ('recording_id', 'brain_project_id', 'source_id'):
            proof[key] = brain_mapping[proof[key]]
    return value


def remap_row(raw, table_name, erp_mapping, brain_mapping):
    """Call only after full closure validation and reference reconciliation."""
    row = deepcopy(raw)
    for key in ('id', 'project_id', 'review_id', 'previous_review_id'):
        if row.get(key):
            row[key] = erp_mapping[row[key]]
    if table_name == 'project_reviews':
        value = remap_live_value({'content': raw['content'], 'provenance': raw['provenance']}, erp_mapping, brain_mapping)
        row['content'], row['provenance'] = value['content'], value['provenance']
    elif table_name == 'project_review_publications':
        row['bindings'] = rebind(raw, publication_references(decode_snapshot(raw)), erp_mapping, brain_mapping)
    elif table_name == 'project_review_events':
        refs = value_references(raw['previous'])
        following = value_references(raw['value'])
        for space in refs:
            refs[space].update(following[space])
        row['bindings'] = rebind(raw, refs, erp_mapping, brain_mapping)
    else:
        invalid('Table de revue inconnue')
    return row


def context(tables, references, deliverable_references, brain):
    names = {'projects':'projects','reviews':'project_reviews','publications':'project_review_publications',
             'people':'project_people','milestones':'milestones','deliverables':'deliverables',
             'checks':'project_deliverable_checklist','files':'project_deliverable_file_versions',
             'type_versions':'project_deliverable_type_versions'}
    groups = {**tables, **references, **deliverable_references}
    result = {'erp': {kind:{row['id'] for row in groups.get(name, [])} for kind,name in names.items()},
              'brain':{kind:{row['id']:row for row in (brain or {}).get(name, [])} for kind,name in
                       (('projects','projects'),('recordings','meeting_recordings'),('sources','sources'))},
              'artifacts': (brain or {}).get('source_artifacts', []),
              'check_rows': {row['id']: row for row in groups.get('project_deliverable_checklist', [])},
              'file_rows': {row['id']: row for row in groups.get('project_deliverable_file_versions', [])}}
    return result


def _pointer(ctx, kind, value, bindings, space='erp'):
    if value is None:
        return None
    resolved = bindings.get(space, {}).get(value, value)
    if resolved not in ctx[space][kind]:
        raise ValueError('Référence capturée absente ou étrangère : ' + kind)
    return resolved


def validate_value(value, bindings, ctx, project_id, review_id=None):
    if not value:
        return
    if set(value) == {'previous_review_id'}:
        TypeAdapter(Identity).validate_python(value['previous_review_id'], strict=True)
        _pointer(ctx, 'reviews', value['previous_review_id'], bindings)
        return
    review_value(value)
    if review_id and _pointer(ctx, 'reviews', value['id'], bindings) != review_id:
        raise ValueError('Contenu appartenant à une autre revue')
    _pointer(ctx, 'reviews', value['previous_review_id'], bindings)
    content = value['content']
    _pointer(ctx, 'milestones', content['milestone_id'], bindings)
    for doc in content['deliverable_ids']:
        _pointer(ctx, 'deliverables', doc, bindings)
    for person in content['participants']:
        _pointer(ctx, 'people', person['person_id'], bindings)
    for proof in value['provenance'].values():
        if _pointer(ctx, 'projects', proof['erp_project_id'], bindings) != project_id:
            raise ValueError('Preuve ERP étrangère')
        source = _pointer(ctx, 'sources', proof['source_id'], bindings, 'brain')
        owner = _pointer(ctx, 'projects', proof['brain_project_id'], bindings, 'brain')
        recording = ctx['brain']['recordings'][_pointer(ctx, 'recordings', proof['recording_id'], bindings, 'brain')]
        if (recording['project_id'] != owner or recording['erp_project_id'] != project_id or recording['source_id'] != source):
            raise ValueError('Preuve audio étrangère au projet ou à sa source')
        if ctx['brain']['sources'][source]['project_id'] not in (None, owner):
            raise ValueError('Source audio appartenant à un autre projet')
        # A later transcript never invalidates an already captured old excerpt.
        # At its captured revision, the original must match the actual segment.
        if recording['revision'] == proof['revision']:
            segment = next((row for row in recording['segments'] if row['id'] == proof['segment_id']), None)
            speakers = recording['speaker_names']
        elif recording['revision'] < proof['revision']:
            raise ValueError('Preuve issue d’une transcription future')
        else:
            # Human transcript validation retains an artifact for each accepted
            # revision. A changed live recording cannot authenticate an older
            # excerpt by itself. Require the matching retained revision.
            captures = [row['content_json'] for row in ctx['artifacts']
                        if row['source_id'] == source and row['kind'] == 'transcription'
                        and isinstance(row.get('content_json'), dict)
                        and row['content_json'].get('recording_id') == recording['id']
                        and row['content_json'].get('revision') == proof['revision']]
            if len(captures) != 1:
                raise ValueError('Transcription historique absente ou ambiguë')
            captured = captures[0]
            segment = next((row for row in captured['segments'] if row['id'] == proof['segment_id']), None)
            speakers = captured['speaker_names']
        if (not segment or any(segment[key] != proof[key] for key in ('text','start','end'))
                or speakers.get(segment['speaker'], segment['speaker']) != proof['speaker']):
            raise ValueError('Extrait ou interlocuteur capturé différent de la transcription conservée')


def remap_audio_artifact(raw, brain_mapping):
    """Only the known transcription recording pointer moves; text stays exact."""
    row = deepcopy(raw)
    if row['kind'] == 'transcription' and isinstance(row.get('content_json'), dict):
        identity = row['content_json'].get('recording_id')
        if identity is not None:
            if identity not in brain_mapping:
                invalid('Enregistrement absent de la transcription historique')
            row['content_json']['recording_id'] = brain_mapping[identity]
    return row


def identity_dependencies(tables):
    people = set()
    for row in tables.get('project_reviews', []):
        people.update(person['person_id'] for person in row['content']['participants'] if person['person_id'])
    for row in tables.get('project_review_events', []):
        refs = value_references(row['previous'])
        following = value_references(row['value'])
        for space in refs:
            refs[space].update(following[space])
        bindings = frozen_bindings(row, refs)
        for value in (row['previous'], row['value']):
            if value.get('content'):
                people.update(bindings['erp'].get(person['person_id'],person['person_id']) for person in value['content']['participants'] if person['person_id'])
    for row in tables.get('project_review_publications', []):
        snapshot = decode_snapshot(row)
        bindings = frozen_bindings(row, publication_references(snapshot))
        ids = {person['person_id'] for person in snapshot['review']['content']['participants'] if person['person_id']}
        ids.update(member['person_id'] for member in snapshot['team'])
        ids.update(doc[key] for doc in snapshot['deliverables'] for key in ('responsible_id','verifier_id') if doc[key])
        people.update(bindings['erp'].get(key,key) for key in ids)
    return {}, people


def deliverable_type_dependencies(tables):
    versions = set()
    for row in tables.get('project_review_publications', []):
        snapshot = decode_snapshot(row)
        bindings = frozen_bindings(row, publication_references(snapshot))
        versions.update(bindings['erp'].get(doc['type_version_id'], doc['type_version_id'])
                        for doc in snapshot['deliverables'] if doc['type_version_id'])
    return versions


def validate(metadata, tables, references, deliverable_references, brain):
    try:
        pid = tables['projects'][0]['id']
        ctx = context(tables,references,deliverable_references,brain)
        reviews = {row['id']:row for row in tables.get('project_reviews', [])}
        for name in PROJECT_TABLES:
            rows = tables.get(name, [])
            if not isinstance(rows,list) or len(rows)>MAX_ROWS:
                raise ValueError('Liste de revue invalide')
            seen = set()
            for row in rows:
                if not isinstance(row,dict) or set(row)!=set(metadata.tables[name].c.keys()):
                    raise ValueError('Colonnes de revue absentes ou étrangères')
                TypeAdapter(Identity).validate_python(row['id'],strict=True)
                if row['id'] in seen:
                    raise ValueError('Identifiant de revue, publication ou événement dupliqué')
                seen.add(row['id'])
                if row['project_id']!=pid:
                    raise ValueError('Ligne de revue étrangère')
                if not isinstance(row['actor_id'],str) or not 1<=len(row['actor_id'])<=120:
                    raise ValueError('Acteur de revue invalide')
                datetime.fromisoformat(row['created_at'])
        numbers = {}
        for row in reviews.values():
            value = {'id':row['id'],'number':row['number'],'type_code':row['type_code'],'status':row['status'],
                     'review_revision':row['revision'],'previous_review_id':row['previous_review_id'],
                     'content':row['content'],'provenance':row['provenance']}
            validate_value(value,{},ctx,pid,row['id'])
            datetime.fromisoformat(row['updated_at'])
            if row['number'] in numbers:
                raise ValueError('Numéro de revue dupliqué')
            numbers[row['number']]=row
        if numbers and set(numbers)!=set(range(1,len(numbers)+1)):
            raise ValueError('Historique de révisions incomplet')
        for number,row in numbers.items():
            previous = numbers.get(number-1)
            if row['previous_review_id']!=(previous['id'] if previous else None) or previous and previous['status']!='published':
                raise ValueError('Chaîne de révisions invalide')
        publications = {}
        for row in tables.get('project_review_publications', []):
            snapshot = decode_snapshot(row)
            bindings = frozen_bindings(row,publication_references(snapshot))
            owner = _pointer(ctx,'reviews',snapshot['review']['id'],bindings)
            if (row['review_id']!=owner or owner in publications
                    or _pointer(ctx,'publications',snapshot['publication_id'],bindings)!=row['id']
                    or _pointer(ctx,'projects',snapshot['project']['id'],bindings)!=pid
                    or snapshot['published_by']!=row['actor_id'] or timestamp(snapshot['published_at'])!=timestamp(row['created_at'])):
                raise ValueError('Publication étrangère, dupliquée ou métadonnées différentes')
            validate_value(snapshot['review'],bindings,ctx,pid,owner)
            for member in snapshot['team']:
                _pointer(ctx,'people',member['person_id'],bindings)
            for doc in snapshot['deliverables']:
                document_id = _pointer(ctx,'deliverables',doc['id'],bindings)
                if _pointer(ctx,'projects',doc['project_id'],bindings)!=pid:
                    raise ValueError('Livrable capturé étranger')
                for key,kind in (('responsible_id','people'),('verifier_id','people'),('type_version_id','type_versions'),('latest_version_id','files')):
                    identity = _pointer(ctx,kind,doc[key],bindings)
                    if kind=='files' and identity and ctx['file_rows'][identity]['deliverable_id']!=document_id:
                        raise ValueError('Version capturée appartenant à un autre livrable')
                for key in doc['milestone_ids']:
                    _pointer(ctx,'milestones',key,bindings)
                for check in doc['checklist']:
                    for key,kind in (('id','checks'),('milestone_id','milestones'),('completed_version_id','files')):
                        identity = _pointer(ctx,kind,check[key],bindings)
                        if identity and kind in {'checks','files'}:
                            parent = ctx['check_rows' if kind=='checks' else 'file_rows'][identity]
                            if parent['deliverable_id']!=document_id:
                                raise ValueError('Contrôle ou visa capturé appartenant à un autre livrable')
            live = remap_live_value(snapshot['review'], {key:bindings['erp'].get(key,key) for key in publication_references(snapshot)['erp']},
                                    {key:bindings['brain'].get(key,key) for key in publication_references(snapshot)['brain']})
            current = reviews[owner]
            if (current['status']!='published' or current['revision']!=live['review_revision']
                    or current['number']!=live['number'] or current['type_code']!=live['type_code']
                    or current['previous_review_id']!=live['previous_review_id']
                    or current['content']!=live['content'] or current['provenance']!=live['provenance']
                    or timestamp(current['updated_at'])!=timestamp(row['created_at'])):
                raise ValueError('Revue figée différente de sa publication capturée')
            publications[owner]=row
        if set(publications)!={row['id'] for row in reviews.values() if row['status']=='published'}:
            raise ValueError('Publication absente ou associée à un brouillon')
        revisions=set()
        histories={key:[] for key in reviews}
        states=tables.get('project_planning_states',[])
        if reviews and (len(states)!=1 or type(states[0]['revision']) is not int or states[0]['revision']<1):
            raise ValueError('État de planning partagé absent')
        for row in tables.get('project_review_events', []):
            if row['action'] not in ACTIONS or type(row['planning_revision']) is not int or not 1<=row['planning_revision']<=states[0]['revision']:
                raise ValueError('Action ou révision de journal inconnue')
            if row['planning_revision'] in revisions or row['review_id'] not in reviews:
                raise ValueError('Événement dupliqué ou étranger')
            revisions.add(row['planning_revision'])
            refs=value_references(row['previous'])
            after=value_references(row['value'])
            for space in refs:
                refs[space].update(after[space])
            bindings=frozen_bindings(row,refs)
            for value in (row['previous'],row['value']):
                validate_value(value,bindings,ctx,pid,row['review_id'])
            histories[row['review_id']].append(row)
        for rid,events in histories.items():
            if not events:
                raise ValueError('Revue sans historique')
            events.sort(key=lambda row:row['planning_revision'])
            previous=None
            for event in events:
                refs=value_references(event['previous'])
                after=value_references(event['value'])
                for space in refs:
                    refs[space].update(after[space])
                bind=frozen_bindings(event,refs)
                erp={key:bind['erp'].get(key,key) for key in refs['erp']}
                br={key:bind['brain'].get(key,key) for key in refs['brain']}
                value=remap_live_value(event['value'],erp,br)
                if previous is None:
                    if (event['action'] not in {'review_created','review_revision_created'}
                            or value['review_revision']!=1 or value['status']!='draft'
                            or event['actor_id']!=reviews[rid]['actor_id']):
                        raise ValueError('Premier événement de revue invalide')
                    if value['number'] == 1:
                        if event['action']!='review_created' or event['previous']!={} or value['provenance']:
                            raise ValueError('Création initiale de revue invalide')
                    else:
                        predecessor = numbers[value['number']-1]
                        original = event['previous']
                        if (event['action']!='review_revision_created' or set(original)!={'previous_review_id'}
                                or erp[original['previous_review_id']]!=value['previous_review_id']
                                or value['content']!=predecessor['content'] or value['provenance']!=predecessor['provenance']):
                            raise ValueError('Création de révision différente de sa publication précédente')
                elif (event['action'] in {'review_created','review_revision_created'} or value['review_revision']!=previous['review_revision']+1
                      or remap_live_value(event['previous'],erp,br)!=previous or previous['status']!='draft'):
                    raise ValueError('Chaîne de brouillon discontinue ou modification après publication')
                if previous is not None:
                    if any(value[key]!=previous[key] for key in ('id','number','type_code','previous_review_id')):
                        raise ValueError('Identité de revue modifiée dans le journal')
                    if event['action']=='review_published':
                        if (value['status']!='published' or value['content']!=previous['content']
                                or value['provenance']!=previous['provenance']
                                or event['actor_id']!=publications[rid]['actor_id']):
                            raise ValueError('Transition de publication invalide')
                        captured_docs = decode_snapshot(publications[rid])['deliverables']
                        if any(doc['revision']!=event['planning_revision'] for doc in captured_docs):
                            raise ValueError('Livrable capturé à une révision de planning différente')
                    elif value['status']!='draft':
                        raise ValueError('Publication sans événement de publication')
                    elif event['action']=='review_saved' and value['provenance']!=previous['provenance']:
                        raise ValueError('Preuves modifiées par une sauvegarde manuelle')
                    elif event['action']=='review_recording_imported' and (
                            not set(previous['provenance']) < set(value['provenance'])
                            or any(value['provenance'][key]!=proof for key,proof in previous['provenance'].items())):
                        raise ValueError('Import audio sans nouvelles preuves ou anciennes preuves altérées')
                previous=value
            current=reviews[rid]
            if previous!= {'id':rid,'number':current['number'],'type_code':current['type_code'],'status':current['status'],
                           'review_revision':current['revision'],'previous_review_id':current['previous_review_id'],
                           'content':current['content'],'provenance':current['provenance']}:
                raise ValueError('Dernier événement différent de la revue actuelle')
        other = [row['revision'] for row in tables.get('project_planning_changes',[])]
        if revisions.intersection(other):
            raise ValueError('Révision partagée dupliquée entre revue et planning/livrables')
        if reviews:
            if any(type(item) is not int or not 1<=item<=states[0]['revision'] for item in other):
                raise ValueError('Révision de planning invalide')
            if len(set(other))!=len(other) or len(revisions | set(other))!=states[0]['revision']:
                raise ValueError('Journal partagé de planning, livrables et revues incomplet')
            publication_revisions = {rid: next(event['planning_revision'] for event in events
                                               if event['action']=='review_published')
                                     for rid,events in histories.items() if rid in publications}
            for rid,events in histories.items():
                predecessor = reviews[rid]['previous_review_id']
                if predecessor and publication_revisions[predecessor]>=events[0]['planning_revision']:
                    raise ValueError('Révision créée avant la publication précédente')
    except (ValueError, TypeError, KeyError, IndexError, AttributeError) as exc:
        invalid(str(exc))
