import pytest
import asyncio
from uuid import uuid4

from app.core.auth_lock import AuthLock
from app.core.provider_implementations import RedisCache


class DummyCache:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def increment(self, key, ttl=None):
        val = self.store.get(key, 0) + 1
        self.store[key] = val
        return val

    async def delete(self, key):
        return self.store.pop(key, None) is not None


@pytest.mark.asyncio
async def test_auth_lock_record_and_clear():
    cache = DummyCache()
    lock = AuthLock(cache, window=60, max_attempts=3)

    email = "user@example.com"
    assert not await lock.is_locked(email)

    await lock.record_failed_login(email)
    assert not await lock.is_locked(email)

    await lock.record_failed_login(email)
    assert not await lock.is_locked(email)

    await lock.record_failed_login(email)
    assert await lock.is_locked(email)

    await lock.clear_failed_logins(email)
    assert not await lock.is_locked(email)
