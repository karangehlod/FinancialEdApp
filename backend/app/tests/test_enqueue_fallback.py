import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
import pytest

from app.core.worker import enqueue


@pytest.mark.asyncio
async def test_enqueue_falls_back_when_arq_missing(monkeypatch):
    # Simulate ImportError inside enqueue by patching arq import
    monkeypatch.setitem('sys.modules', 'arq', None)
    job = await enqueue('send_verification_email_task', user_id='u', user_email='e', verify_url='u')
    assert job is None


@pytest.mark.asyncio
async def test_enqueue_calls_arq_pool(monkeypatch):
    # Create fake pool with enqueue_job
    fake_pool = AsyncMock()
    fake_pool.enqueue_job = AsyncMock(return_value=MagicMock(id='jobid'))
    fake_pool.aclose = AsyncMock()

    class FakeARQ:
        async def create_pool(self, *args, **kwargs):
            return fake_pool

    monkeypatch.setitem('sys.modules', 'arq', FakeARQ())

    # Monkeypatch arq.create_pool used in enqueue
    async def fake_create_pool(redis_settings):
        return fake_pool

    monkeypatch.setattr('app.core.worker.arq.create_pool', fake_create_pool, raising=False)

    job = await enqueue('send_verification_email_task', user_id='u', user_email='e', verify_url='u')
    assert job is not None
    fake_pool.enqueue_job.assert_called_once()
    fake_pool.aclose.assert_called_once()
