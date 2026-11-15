"""Frozen planning and atomic group publication in the existing batch receipt.

No device/model/schema/worker is created at import. This module is only used
by an explicit admitted batch, after its existing global CPU reservation.
"""
from copy import deepcopy
from io import BytesIO
import hashlib
import json
from pathlib import Path
import time
import wave

from sqlalchemy import select

from ..meeting_session_models import LiveTranscriptSegment, MeetingAudioChunk, MeetingSessionCommand
from . import audio_capture
from .grouped_resident import GroupedResidentWhisper, validate_response
from scripts.grouped_pcm_core import (Group, GroupRefused, Individual, Member,
                                     group_from_manifest, plan_groups, publication_guard)

PLAN_VERSION = 'grouped-batch-plan-v1'


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _member(db, snapshot, root):
    path = audio_capture.stored_path(snapshot, Path(root))
    existing = bool(db.scalar(select(LiveTranscriptSegment.id).where(
        LiveTranscriptSegment.chunk_id == snapshot['id']).limit(1)))
    metadata = {'decoded_frames': 0, 'sample_rate': 0, 'channels': 0, 'sample_width': 0,
                'standalone_pcm_wav': False, 'effective_metadata_verified': False}
    # Only standalone canonical PCM files can join. All other existing codecs,
    # unknown durations and human-bearing chunks retain their individual path.
    if path.stat().st_size <= 25 * 16000 * 2 + 100 * 4096:
        frozen = path.read_bytes()
        if len(frozen) != snapshot['size_bytes'] or hashlib.sha256(frozen).hexdigest() != snapshot['sha256']:
            raise GroupRefused('source_changed_during_plan')
        try:
            with wave.open(BytesIO(frozen), 'rb') as wav:
                if wav.getcomptype() == 'NONE':
                    metadata = {'decoded_frames': wav.getnframes(), 'sample_rate': wav.getframerate(),
                        'channels': wav.getnchannels(), 'sample_width': wav.getsampwidth(),
                        'standalone_pcm_wav': True, 'effective_metadata_verified': True}
        except (wave.Error, EOFError):
            pass
    return Member(snapshot['id'], snapshot['session_id'], snapshot['track'], snapshot['sequence'],
        snapshot['storage_path'], snapshot['sha256'], snapshot['size_bytes'], snapshot['start_ms'],
        snapshot['duration_ms'], existing_segments=existing, **metadata)


def _profile_snapshot():
    from .live_speech import runtime_paths, speech_profile, model_fingerprint
    python, models = runtime_paths()
    config = Path(models) / 'models.json'
    profile = speech_profile(models, device_override='cpu')
    return {'python': str(python.resolve()), 'models': str(models.resolve()),
            'config_sha256': hashlib.sha256(config.read_bytes()).hexdigest(),
            'model_sha256': model_fingerprint(models), 'profile': profile}


def admit_plan(db, packet):
    from scripts.speech_runtime import device
    grouping = enabled(db)
    if not grouping or device() == 'cuda':
        reason = 'grouped_batch_capability_disabled' if not grouping else 'grouped_batch_requires_CPU_profile'
        data = {'version': PLAN_VERSION, 'units': [{'kind': 'individual', 'chunk_id': chunk['id'],
            'reason': reason} for chunk in packet['chunks']], 'runtime': None}
        return {**data, 'plan_sha256': _digest(data)}
    members = tuple(_member(db, snapshot, packet['storage_root']) for snapshot in packet['chunks'])
    units = []
    for decision in plan_groups(members):
        if isinstance(decision, Group):
            units.append({'kind': 'group', 'group_id': decision.id, 'manifest': decision.manifest})
        elif isinstance(decision, Individual):
            units.append({'kind': 'individual', 'chunk_id': decision.member.id, 'reason': decision.reason})
    profile = _profile_snapshot() if any(unit['kind'] == 'group' for unit in units) else None
    data = {'version': PLAN_VERSION, 'units': units, 'runtime': profile}
    return {**data, 'plan_sha256': _digest(data)}


def enabled(db):
    from .meeting_sessions import feature_enabled
    from .settings_service import get_section
    return feature_enabled(db) and get_section(db, 'foresight').get('grouped_batch_transcription_enabled') is True


def require_active_plan(db, packet):
    if any(unit['kind'] == 'group' for unit in units(packet)) and not enabled(db):
        raise InterruptedError('Consolidation groupée désactivée ; audio et corrections conservés')


def units(packet):
    plan = packet.get('grouping_plan')
    if plan is None:
        # Old admission receipts stay deterministic and individually processed.
        return [{'kind': 'individual', 'chunk_id': chunk['id'], 'reason': 'historical_individual_receipt'}
                for chunk in packet['chunks']]
    if not isinstance(plan, dict) or set(plan) != {'version', 'units', 'runtime', 'plan_sha256'}:
        raise GroupRefused('invalid_durable_group_plan')
    data = {key: value for key, value in plan.items() if key != 'plan_sha256'}
    if plan['version'] != PLAN_VERSION or plan['plan_sha256'] != _digest(data) or not isinstance(plan['units'], list):
        raise GroupRefused('durable_group_plan_changed')
    selected, observed = {chunk['id']: chunk for chunk in packet['chunks']}, []
    for unit in plan['units']:
        if unit.get('kind') == 'group' and set(unit) == {'kind', 'group_id', 'manifest'}:
            group = group_from_manifest(unit['manifest'])
            if group.id != unit['group_id'] or plan['runtime'] is None:
                raise GroupRefused('group_or_runtime_identity_changed')
            for member in group.members:
                snapshot = selected.get(member.id)
                if snapshot is None or any(getattr(member, target) != snapshot[source] for target, source in (
                    ('session_id', 'session_id'), ('track', 'track'), ('sequence', 'sequence'),
                    ('path', 'storage_path'), ('sha256', 'sha256'), ('size_bytes', 'size_bytes'),
                    ('start_ms', 'start_ms'), ('duration_ms', 'duration_ms'))):
                    raise GroupRefused('group_source_differs_from_admission')
                observed.append(member.id)
        elif unit.get('kind') == 'individual' and set(unit) == {'kind', 'chunk_id', 'reason'}:
            if unit['chunk_id'] not in selected or not isinstance(unit['reason'], str):
                raise GroupRefused('individual_source_differs_from_admission')
            observed.append(unit['chunk_id'])
        else:
            raise GroupRefused('invalid_work_unit')
    if observed != [chunk['id'] for chunk in packet['chunks']]:
        raise GroupRefused('selected_source_order_or_completeness_changed')
    return deepcopy(plan['units'])


def resident(packet):
    if any(unit['kind'] == 'group' for unit in units(packet)):
        expected = packet['grouping_plan']['runtime']
        if _profile_snapshot() != expected:
            raise GroupRefused('runtime_changed_before_group_loading')
        return GroupedResidentWhisper(Path(packet['storage_root']), python=expected['python'], models=expected['models'], device_override='cpu')
    return None


def _check_loaded_profile(packet, response):
    expected = packet['grouping_plan']['runtime']['profile']
    actual = response.get('loaded_model_profile', {})
    if (actual.get('model') != expected['model']
            or str(Path(actual.get('model_path', '')).resolve()) != expected['model_directory']
            or type(actual.get('cpu_threads')) is not int or actual['cpu_threads'] != expected['cpu_threads']
            or actual.get('runtime_version') != expected['runtime_version']):
        raise GroupRefused('loaded_profile_differs_from_admitted_profile')


def process_group(batch, active, unit, started):
    from .meeting_sessions import append_event
    group = group_from_manifest(unit['manifest'])
    if group.id != unit['group_id']:
        raise GroupRefused('group_identity_changed')
    _cancel(batch, active)
    with active.factory() as db:
        row, command, packet, chunks = _writer_state(batch, active, db, group, 'batch_pending')
        for chunk in chunks:
            chunk.speech_status = 'batch_running'
        packet.update(state='running', running_group_id=group.id,
                      running_chunk_ids=[member.id for member in group.members])
        batch._save_packet(command, packet)
        append_event(db, row, 'transcript.batch.running', {'command_id': command.id, 'group_id': group.id,
                                                       'chunk_ids': packet['running_chunk_ids']})
        _cancel(batch, active)
        db.commit()
    remaining = batch.MAX_JOB_SECONDS - (time.monotonic() - started)
    if remaining <= 0:
        raise TimeoutError()
    response = active.resident.transcribe_group(group, timeout=remaining, cancel=active.cancel)
    validate_response(group, response)
    _check_loaded_profile(packet, response)
    if _profile_snapshot() != packet['grouping_plan']['runtime']:
        raise GroupRefused('runtime_changed_before_group_publication')
    _cancel(batch, active)
    with active.factory() as db:
        row, command, packet, chunks = _writer_state(batch, active, db, group, 'batch_running')
        if (packet.get('running_group_id') != group.id
                or packet.get('running_chunk_ids') != [member.id for member in group.members]):
            raise GroupRefused('running_group_reservation_changed')
        if response['mapping_status'] != 'mapped':
            packet.setdefault('group_results', {})[group.id] = {'state': 'refused', 'response': deepcopy(response)}
            batch._save_packet(command, packet)
            append_event(db, row, 'transcript.batch.group_refused', {'command_id': command.id,
                'group_id': group.id, 'reason': response['mapping_refusal'], 'published_segments': 0})
            _cancel(batch, active)
            db.commit()  # Diagnostic only; no segment/member is marked completed.
            raise GroupRefused(response['mapping_refusal'])
        # Validate the entire set before adding any row. Existing IDs anywhere
        # refuse the group rather than silently discarding a human correction.
        for item in response['segments']:
            if db.get(LiveTranscriptSegment, item['id']) is not None:
                raise GroupRefused('canonical_segment_collision')
        _cancel(batch, active)
        for item in response['segments']:
            db.add(LiveTranscriptSegment(id=item['id'], session_id=row.id, chunk_id=item['chunk_id'],
                track=item['track'], start_ms=item['start_ms'], end_ms=item['end_ms'], speaker=item['speaker'],
                text=item['text'], revision=1, finalized=False))
        for chunk in chunks:
            chunk.speech_status, chunk.speech_error = 'completed', None
            packet['completed_ids'].append(chunk.id)
            append_event(db, row, 'transcript.updated', {'chunk_id': chunk.id,
                'segments': sum(item['chunk_id'] == chunk.id for item in response['segments']),
                'provisional': True, 'mode': 'explicit-batch-group', 'group_id': group.id})
        packet.setdefault('group_results', {})[group.id] = {'state': 'completed', 'response': deepcopy(response)}
        packet.pop('running_group_id', None)
        packet.pop('running_chunk_ids', None)
        batch._save_packet(command, packet)
        _cancel(batch, active)
        db.commit()  # Segments, all members, native proof, events and receipt together.


def _cancel(batch, active):
    if active.cancel.is_set() or batch._shutdown.is_set():
        raise InterruptedError()


def _writer_state(batch, active, db, group, required_chunk_state):
    _cancel(batch, active)
    batch._writer(db)
    command = db.get(MeetingSessionCommand, active.command_id)
    if command is None:
        raise GroupRefused('group_command_missing')
    packet = deepcopy(batch._packet(command))
    row = batch._validate_authority(db, command, packet)
    require_active_plan(db, packet)
    batch._validate_snapshot(db, packet)
    if packet.get('state') not in {'admitted', 'running'}:
        raise InterruptedError()
    admitted = next((unit for unit in units(packet) if unit['kind'] == 'group' and unit['group_id'] == group.id), None)
    if admitted is None or admitted['manifest'] != group.manifest:
        raise GroupRefused('group_not_in_durable_plan')
    originals = {item['id']: item for item in packet['chunks']}
    current = tuple(_member(db, originals[member.id], packet['storage_root']) for member in group.members)
    existing = list(db.scalars(select(LiveTranscriptSegment.id).where(
        LiveTranscriptSegment.chunk_id.in_([member.id for member in group.members]))))
    publication_guard(group, current_members=current, existing_ids=existing,
                      cancel_requested=active.cancel.is_set() or batch._shutdown.is_set())
    chunks = [db.get(MeetingAudioChunk, member.id) for member in group.members]
    if any(chunk.speech_status != required_chunk_state or chunk.id in packet['completed_ids'] for chunk in chunks):
        raise GroupRefused('group_chunk_reservation_changed')
    _cancel(batch, active)
    return row, command, packet, chunks


def confirm_final_profile(packet):
    if any(unit['kind'] == 'group' for unit in units(packet)):
        if _profile_snapshot() != packet['grouping_plan']['runtime']:
            raise GroupRefused('runtime_changed_during_group_batch')
