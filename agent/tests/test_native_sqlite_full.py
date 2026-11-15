"""Real SQLite SQLITE_FULL quota, private databases; no fake I/O exception.

The filesystem stays available. This is not qualification of a full volume or
physical capture: only the producer handle is inert, while SQL/files are real.
"""
import io
import json
import errno
import sqlite3
from types import SimpleNamespace
import uuid

from fastapi import HTTPException
import pytest
from sqlalchemy import event, func, select
from sqlalchemy.exc import OperationalError

from app.meeting_session_models import MeetingAudioChunk, MeetingSession, MeetingSessionCommand, MeetingSessionEvent
from app.services import native_audio as native
from tests.test_native_audio_receipt_recovery import (
    capture as capture_fixture, stores as stores_fixture, assert_originals,
)

stores = stores_fixture
capture = capture_fixture


@pytest.mark.parametrize('failure', [
    OSError(errno.ENOSPC, 'private/file.wav'),
    HTTPException(507, 'private storage details'),
    OperationalError('private SQL', {'secret': 'payload'}, OSError(errno.ENOSPC, 'private/path')),
])
def test_audio_capacity_error_detail_is_actionable_and_contains_no_payload(failure):
    detail = native._capture_failure_detail(failure)
    assert 'Stockage audio saturé' in detail and 'libérez' in detail
    assert 'private' not in detail and 'secret' not in detail


@pytest.mark.parametrize('failure', [
    PermissionError(errno.EACCES, 'private/file.wav'),
    sqlite3.OperationalError('database is locked'),
    RuntimeError('database or disk is full'),
    HTTPException(403, 'private permissions'),
])
def test_unrelated_errors_are_not_reported_as_storage_full(failure):
    assert native._capture_failure_detail(failure) == 'Capture interrompue ; fragments natifs conservés et rejouables'


def test_real_sqlite_full_interrupts_without_ack_and_replays_originals_after_capacity_returns(capture):
    value = capture
    value.item.replay()
    first_receipt = value.receipt.read_bytes()
    engine = value.brain.kw['bind']
    with engine.connect() as connection:
        current_pages = connection.exec_driver_sql('PRAGMA page_count').scalar()
        normal_limit = connection.exec_driver_sql('PRAGMA max_page_count').scalar()
    limit = current_pages + 8  # At most32KiB additional database pages; never fills the host volume.
    constrained = [True]
    observed = []

    def capacity(dbapi, _record, _proxy):
        actual = dbapi.execute('PRAGMA max_page_count='+str(limit if constrained[0] else normal_limit)).fetchone()[0]
        assert actual == (limit if constrained[0] else normal_limit)

    def observe(context):
        error = context.original_exception
        if isinstance(error, sqlite3.Error):
            observed.append({'code': getattr(error, 'sqlite_errorcode', None),
                             'name': getattr(error, 'sqlite_errorname', None)})

    event.listen(engine, 'checkout', capacity)
    event.listen(engine, 'handle_error', observe)
    try:
        filled = 0
        # Fill only the private event B-tree. Other tables/files keep real I/O.
        # A database quota, rather than a raised test exception, causes SQLITE_FULL.
        for _ in range(32):
            try:
                with value.brain() as db:
                    db.add(MeetingSessionEvent(session_id=value.item.sid, kind='qualification.page-reservation',
                        revision=1, data={'filler': 'x'*3800}))
                    db.commit()
                    filled += 1
            except Exception as error:
                original = getattr(error, 'orig', error)
                assert isinstance(original, sqlite3.Error) and original.sqlite_errorcode == sqlite3.SQLITE_FULL
                break
        else:
            pytest.fail('Private database quota did not exhaust within its bounded fixture')
        assert filled > 0
        observed.clear()
        path = value.item.directory/'mic-00000001.wav'
        path.write_bytes(value.raw)
        packet = {**value.packet, 'sequence': 1, 'path': str(path), 'start_ms': 5000,
                  'command_id': str(uuid.uuid5(uuid.UUID(value.item.sid), 'mic:1:'+value.packet['sha256']))}
        manifest = path.with_suffix('.json')
        manifest.write_text(json.dumps(packet), encoding='utf-8')
        manifest_before = manifest.read_bytes()
        stopped = []
        value.item.process = SimpleNamespace(
            stdout=io.StringIO(json.dumps(packet)+'\n'+json.dumps({'kind':'state','state':'stopped'})+'\n'),
            poll=lambda: None, terminate=lambda: stopped.append(True))
        try:
            value.item._receive()
        finally:
            value.item.process = None  # There was never a process/device to close.
        assert any(row['code'] == sqlite3.SQLITE_FULL for row in observed), observed
        assert stopped == [True] and value.item.state == 'interrupted' and value.item._reader_done.is_set()
        assert not path.with_suffix('.receipt.json').exists()
        assert value.item.request['sequences'] == {'mic':1} and value.item.request['offset_ms'] == 5000
        assert 'Stockage de la base saturé' in value.item.error
        with value.brain() as db:
            assert db.scalar(select(func.count()).select_from(MeetingAudioChunk)) == 1
            assert db.get(MeetingSessionCommand, packet['command_id']) is None
        with pytest.raises(ValueError):
            value.item.command('stop', target_state='stopped')
        assert path.read_bytes() == value.raw and manifest.read_bytes() == manifest_before
        assert value.receipt.read_bytes() == first_receipt
        assert_originals(value)
        constrained[0] = False
        value.item._record_interruption()
        value.item.replay()
        second_receipt = path.with_suffix('.receipt.json').read_bytes()
        value.item.replay()
        assert second_receipt == path.with_suffix('.receipt.json').read_bytes()
        with value.brain() as db:
            assert db.scalar(select(func.count()).select_from(MeetingAudioChunk)) == 2
            assert db.scalar(select(func.count()).select_from(MeetingSessionCommand).where(MeetingSessionCommand.kind=='chunk')) == 2
            assert db.scalar(select(func.count()).select_from(MeetingSessionEvent).where(MeetingSessionEvent.kind=='chunk.received')) == 2
            assert db.get(MeetingSession,value.item.sid).state == 'interrupted'
            assert db.connection().exec_driver_sql('PRAGMA integrity_check').scalar() == 'ok'
        assert value.item.request['sequences'] == {'mic':2} and value.item.request['offset_ms'] == 10000
        assert path.read_bytes() == value.raw and manifest.read_bytes() == manifest_before
        assert value.receipt.read_bytes() == first_receipt
        assert_originals(value)
    finally:
        event.remove(engine, 'checkout', capacity)
        event.remove(engine, 'handle_error', observe)
