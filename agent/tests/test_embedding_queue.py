import asyncio
import threading

import httpx
import pytest

from app.services.embedding_channel import EmbeddingChannel
from app.services import inference_scheduler as scheduler


def test_channels_share_one_active_request_across_instances(monkeypatch):
    active, maximum = 0, 0

    async def respond(request):
        nonlocal active, maximum
        active += 1
        maximum = max(maximum, active)
        await asyncio.sleep(0.01)
        active -= 1
        return httpx.Response(200, json={'data': [{'index': 0, 'embedding': [1.] * 768}]})

    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(respond), **kw))

    async def run():
        await asyncio.gather(*(EmbeddingChannel('http://queue-test:17841').embed(['test']) for _ in range(3)))

    asyncio.run(run())
    assert maximum == 1
    assert scheduler.status()['active'] == scheduler.status()['waiting'] == 0


def test_async_wait_does_not_block_and_cancellation_releases_ticket():
    entered, release = threading.Event(), threading.Event()
    key = scheduler.engine_key('http://queue-test:17842')

    def sync_request():
        with scheduler.lease(key):
            entered.set()
            release.wait(5)

    thread = threading.Thread(target=sync_request)
    thread.start()
    assert entered.wait(2)

    async def run():
        async def queued():
            async with scheduler.async_lease(key, timeout=1):
                pytest.fail('Synchronous request is still active')

        pending = asyncio.create_task(queued())
        await asyncio.sleep(0.01)
        assert scheduler.status()['waiting'] == 1
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pending
        assert scheduler.status()['waiting'] == 0

    try:
        asyncio.run(run())
    finally:
        release.set()
        thread.join(2)
    assert scheduler.status()['active'] == 0


def test_request_deadline_releases_reservation(monkeypatch):
    async def respond(request):
        await asyncio.sleep(1)
        return httpx.Response(200)

    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(respond), **kw))
    with pytest.raises(TimeoutError):
        asyncio.run(EmbeddingChannel('http://queue-test:17843', timeout_s=0.02).embed(['test']))
    assert scheduler.status()['active'] == scheduler.status()['waiting'] == 0
