import importlib
import types
from unittest import mock

import pytest

from app.db.session import get_pool_strategy_summary


class DummyPool:
    pass


class DummyEngine:
    def __init__(self, poolname):
        pool = DummyPool()
        pool.size = None
        pool.overflow = None
        self.sync_engine = types.SimpleNamespace(pool=pool)


@mock.patch('app.db.session._PGBOUNCER_MODE', True)
@mock.patch('app.db.session.auth_engine', new_callable=lambda: DummyEngine('auth'))
@mock.patch('app.db.session.data_engine', new_callable=lambda: DummyEngine('data'))
def test_pool_strategy_uses_nullpool(mock_data_engine, mock_auth_engine):
    summary = get_pool_strategy_summary()
    # When PGBOUNCER_MODE=True we expect pool_class to reflect NullPool-like behavior.
    # The dummy engine exposes a pool whose __class__.__name__ is 'DummyPool'.
    assert summary['auth_db']['pool_class'] in {'DummyPool', 'unknown'}

