import asyncio
import pytest
from uuid import uuid4

from app.core.cache_service import CacheService
from app.services.expense_service import ExpenseService


class DummyCache:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ttl):
        self.store[key] = value
        return True

    async def delete(self, key):
        self.store.pop(key, None)
        return True


class DummyRepo:
    def __init__(self):
        self.called = 0

    async def get_by_user(self, user_id, skip, limit, filters):
        self.called += 1
        # return empty list and total
        return [], 0


@pytest.mark.asyncio
async def test_get_user_expenses_uses_cache():
    db = None
    cache = DummyCache()
    repo = DummyRepo()

    service = ExpenseService(db, cache_service=cache)
    service.repository = repo

    user_id = uuid4()

    # First call should hit the repo and return model objects
    repo.get_by_user = asyncio.coroutine(lambda u, s=0, l=50, f=None: ([], 0))

    res1 = await service.get_user_expenses(user_id)
    assert repo.called == 1

    # Second call should use cache and not hit repo
    repo.get_by_user = asyncio.coroutine(lambda u, s=0, l=50, f=None: ([_ for _ in range(1)], 1))

    res2 = await service.get_user_expenses(user_id)
    assert repo.called == 1
    assert res1 == res2
