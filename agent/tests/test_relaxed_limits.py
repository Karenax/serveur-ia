"""Long-session and normal-contention regressions; no hardware or model."""
from concurrent.futures import ThreadPoolExecutor
import io
import threading
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.meeting_session_models import MeetingAudioChunk
from app.services import ai_client, ai_routing, inference_scheduler as scheduler
from app.services import live_speech, native_audio
from app.services.settings_service import save_section
from tests.test_meeting_sessions import stores, create, chunk, wav

__all__ = ['stores']


@pytest.fixture(autouse=True)
def no_devices_or_models(monkeypatch):
    monkeypatch.setattr(native_audio, 'status', lambda sid=None: {'session': None})
    monkeypatch.setattr(native_audio, '_captures', {})
    monkeypatch.setattr(live_speech, 'wake_worker', lambda: None)


def test_thirty_real_PCM_fragments_do_not_suspend_direct_after_two_minutes(stores):
    brain = stores[0]
    with brain() as db:
        save_section(db, 'foresight', {'enabled': True, 'live_transcription_enabled': True})
        sid = create(db, kind='meeting')['id']
        raw = wav(80000)
        for seq in range(30):
            result = chunk(db, sid, seq, raw=raw, start_ms=seq*5000, duration_ms=5000)
            assert result['acknowledged']
            assert result['speech_admission']['status'] == 'pending', result['speech_admission']
        saved = list(db.scalars(select(MeetingAudioChunk).where(MeetingAudioChunk.session_id == sid)))
        assert len(saved) == 30 and all(item.speech_status == 'pending' for item in saved)
        assert sum(item.duration_ms for item in saved) == 150000


def test_fragment_after_three_hours_is_saved_with_replay_identity(stores):
    brain = stores[0]
    with brain() as db:
        sid = create(db, kind='meeting')['id']
        command = str(uuid4())
        body = dict(raw=wav(80000), start_ms=3*3600*1000, duration_ms=5000, command_id=command)
        first = chunk(db, sid, **body)
        assert first['acknowledged'] and chunk(db, sid, **body) == first
        assert len(list(db.scalars(select(MeetingAudioChunk).where(MeetingAudioChunk.session_id == sid)))) == 1


def test_configured_one_hour_generation_timeout_is_not_rejected_by_old_five_minute_cap():
    from app.routers.settings import AISettings, MemorySettings
    assert AISettings(timeout_s=3600).timeout_s == 3600
    assert MemorySettings(timeout_s=3600).timeout_s == 3600


@pytest.mark.asyncio
@pytest.mark.parametrize('path,size', [('/api/v1/projects/example/recordings', 120*1024**2),
                                     ('/api/v1/projects/example/cdc/sources', 40*1024**2)])
async def test_request_guard_accepts_raised_upload_sizes_without_allocating_large_bodies(monkeypatch, path, size):
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    from app.security import _local_session_guard
    monkeypatch.setenv('AGENT_TESTING', '1')
    request = Request({'type': 'http', 'method': 'POST', 'scheme': 'http', 'path': path,
        'server': ('127.0.0.1', 8001), 'query_string': b'',
        'headers': [(b'host', b'127.0.0.1:8001'), (b'content-length', str(size).encode())]})
    called = []

    async def next_handler(value):
        called.append(value)
        return JSONResponse({'accepted': True})

    result = await _local_session_guard(request, next_handler)
    assert result.status_code == 200 and called == [request]


@pytest.mark.parametrize('caller', ['scheduler', 'json', 'local'])
def test_waiting_request_survives_old_thirty_second_cutoff(monkeypatch, caller):
    clock = [1000.0]
    monkeypatch.setattr(scheduler, 'time', SimpleNamespace(monotonic=lambda: clock[0]))
    monkeypatch.setattr(ai_routing, 'time', SimpleNamespace(monotonic=lambda: clock[0]))
    monkeypatch.setattr(ai_client, 'time', SimpleNamespace(monotonic=lambda: clock[0]))
    first, second = threading.Event(), threading.Event()

    class ObservedCondition(threading.Condition):
        waits = 0

        def wait(self, timeout=None):
            self.waits += 1
            (second if clock[0] >= 1061 else first).set()
            return super().wait(timeout)

    condition = ObservedCondition(threading.RLock())
    monkeypatch.setattr(scheduler, '_condition', condition)
    monkeypatch.setattr(scheduler, '_engines', {})
    monkeypatch.setattr(ai_routing, 'ensure_local', lambda cfg: None)
    monkeypatch.setattr(ai_client.urllib.request, 'urlopen', lambda *args, **kwargs: io.BytesIO(b'{"ok":true}'))
    url = 'http://local-fixture.invalid:1234'

    def work():
        if caller == 'json':
            return ai_client._post_json(url+'/v1/chat/completions', {}, timeout=60)
        manager = scheduler.lease(scheduler.engine_key(url)) if caller == 'scheduler' else ai_routing.local_generation({'base_url': url}, timeout=60)
        with manager:
            return {'ok': True}

    with ThreadPoolExecutor(max_workers=1) as pool:
        with scheduler.lease(scheduler.engine_key(url)):
            future = pool.submit(work)
            assert first.wait(2)
            clock[0] += 61
            with condition:
                condition.notify_all()
            assert second.wait(2), 'A normal busy engine discarded the waiting request'
            assert not future.done()
        assert future.result(timeout=2) == {'ok': True}
    assert scheduler.status()['active'] == scheduler.status()['waiting'] == 0
