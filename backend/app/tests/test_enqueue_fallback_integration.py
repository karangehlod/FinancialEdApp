import os
import sys
# Ensure the backend folder is on sys.path so `import app` resolves to backend/app
ROOT = os.path.dirname(os.path.dirname(__file__))
BACKEND_APP = os.path.abspath(ROOT)
if BACKEND_APP not in sys.path:
    sys.path.insert(0, BACKEND_APP)

os.environ.setdefault("TESTING", "1")

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
import uuid

from app.main import app


def make_user(email, verified=False, active=True):
    return SimpleNamespace(id=uuid.uuid4(), email=email, is_verified=verified, is_active=active)


def test_resend_verification_fallback(monkeypatch):
    client = TestClient(app)

    # Fake email service whose send_generic_email is an AsyncMock
    fake_email = MagicMock()
    fake_email.send_generic_email = AsyncMock(return_value=True)
    monkeypatch.setattr("app.services.email_service.get_email_service", lambda: fake_email)

    # Simulate enqueue returning None (ARQ missing / queue unavailable)
    async def fake_enqueue(name, **kwargs):
        return None

    monkeypatch.setattr("app.core.worker.enqueue", fake_enqueue)

    # Patch repository to return a user that exists and is unverified
    async def fake_get_user_by_email(self, email):
        return make_user(email, verified=False, active=True)

    from app.repositories.user_repository import UserRepository

    monkeypatch.setattr(UserRepository, "get_user_by_email", fake_get_user_by_email, raising=False)

    resp = client.post("/api/v1/auth/resend-verification", json={"email": "u@example.com"})
    assert resp.status_code == 202

    # BackgroundTasks should have executed the coroutine; ensure send_generic_email was awaited
    assert fake_email.send_generic_email.await_count == 1


def test_forgot_password_fallback(monkeypatch):
    client = TestClient(app)

    fake_email = MagicMock()
    fake_email.send_generic_email = AsyncMock(return_value=True)
    monkeypatch.setattr("app.services.email_service.get_email_service", lambda: fake_email)

    async def fake_enqueue(name, **kwargs):
        return None

    monkeypatch.setattr("app.core.worker.enqueue", fake_enqueue)

    async def fake_get_user_by_email(self, email):
        return make_user(email, verified=True, active=True)

    from app.repositories.user_repository import UserRepository

    monkeypatch.setattr(UserRepository, "get_user_by_email", fake_get_user_by_email, raising=False)

    resp = client.post("/api/v1/auth/forgot-password", json={"email": "u@example.com"})
    assert resp.status_code == 202
    assert fake_email.send_generic_email.await_count == 1
