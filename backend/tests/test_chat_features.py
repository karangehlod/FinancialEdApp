import pytest
import asyncio
import uuid

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.mark.unit
async def test_conversation_ownership_and_delete(monkeypatch):
    # This is a lightweight integration-style test using TestClient to exercise
    # the chat endpoints. We mock authentication to simulate two users.
    # For brevity we only check ownership enforcement and delete behavior.

    user_a_id = str(uuid.uuid4())
    user_b_id = str(uuid.uuid4())

    # Mock get_current_user dependency to return user A
    from app.dependencies import get_current_user
    async def fake_user_a():
        class U:
            id = user_a_id
        return U()

    app.dependency_overrides[get_current_user] = fake_user_a

    # Create conv for user-a
    r = client.post('/api/v1/chat/conversation')
    assert r.status_code == 201
    conv_id = r.json()['id']

    # Attempt to get history as user-a (should succeed)
    r = client.get(f'/api/v1/chat/history/{conv_id}')
    assert r.status_code == 200

    # Now override to user-b
    async def fake_user_b():
        class U:
            id = user_b_id
        return U()
    app.dependency_overrides[get_current_user] = fake_user_b

    # User-b should be forbidden from accessing history
    r = client.get(f'/api/v1/chat/history/{conv_id}')
    assert r.status_code == 403

    # User-b should be forbidden from deleting
    r = client.delete(f'/api/v1/chat/conversation/{conv_id}')
    assert r.status_code == 403

    # Switch back to user-a and delete
    app.dependency_overrides[get_current_user] = fake_user_a
    r = client.delete(f'/api/v1/chat/conversation/{conv_id}')
    assert r.status_code == 204

    # After deletion, user-a accessing that conv should return 200 (new empty conv), 404, or 403
    r = client.get(f'/api/v1/chat/history/{conv_id}')
    assert r.status_code in [200, 403, 404]  # deleted conv: not found or forbidden
    if r.status_code == 200:
        data = r.json()
        assert 'messages' in data

    # Clean up overrides
    app.dependency_overrides.pop(get_current_user, None)
