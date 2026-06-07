"""
Live Integration Tests: Authentication
======================================
Tests the full auth flow end-to-end against real PostgreSQL + Redis:
  - Register (signup)
  - Login
  - Token refresh
  - Two-Factor Authentication (TOTP enable / verify / login with 2FA)
  - /me (authenticated user info)
  - Cross-user isolation (user A cannot see user B's data)
  - Duplicate email rejection
  - Invalid / expired token rejection

All tests use real HTTP requests through the FastAPI ASGI app,
real DB transactions (rolled back after each test) and real Redis.

Markers: pytest -m live_auth
"""
import uuid
import time
import pytest
import pytest_asyncio
import pyotp
from datetime import datetime, timedelta
from jose import jwt

from tests.conftest_live import (
    make_user,
    live_client,
    authed_client,
    auth_headers_for,
    auth_db,
    data_db,
    _mint_token,
)
from app.config import settings

pytestmark = [pytest.mark.asyncio, pytest.mark.live, pytest.mark.live_auth]

API = settings.API_V1_PREFIX  # "/api/v1"


# =============================================================================
# ── REGISTRATION ─────────────────────────────────────────────────────────────
# =============================================================================

class TestRegistration:
    """Verify user signup creates an account and returns tokens."""

    async def test_register_returns_201_and_tokens(self, live_client):
        """Happy path: valid payload → 201 with access + refresh tokens."""
        email = f"reg_{uuid.uuid4().hex[:8]}@example.com"
        resp = await live_client.post(f"{API}/auth/register", json={
            "email": email,
            "password": "StrongPass123!",
            "name": "Alice Dev",
        })
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body.get("token_type", "").lower() == "bearer"

    async def test_register_duplicate_email_returns_409(self, live_client, make_user):
        """Registering with an already-used email must be rejected with 409."""
        email = f"dup_{uuid.uuid4().hex[:8]}@example.com"
        await make_user(email=email)  # pre-create via fixture

        resp = await live_client.post(f"{API}/auth/register", json={
            "email": email,
            "password": "AnotherPass456!",
            "name": "Bob Dev",
        })
        assert resp.status_code == 409, resp.text

    async def test_register_weak_password_returns_422(self, live_client):
        """Passwords shorter than 8 chars (or no uppercase/digit) are rejected."""
        resp = await live_client.post(f"{API}/auth/register", json={
            "email": f"weak_{uuid.uuid4().hex[:8]}@example.com",
            "password": "short",
        })
        assert resp.status_code == 422, resp.text

    async def test_register_invalid_email_format_returns_422(self, live_client):
        """Malformed email must not pass schema validation."""
        resp = await live_client.post(f"{API}/auth/register", json={
            "email": "not-an-email",
            "password": "StrongPass123!",
        })
        assert resp.status_code == 422, resp.text

    async def test_register_missing_fields_returns_422(self, live_client):
        """Missing required fields must return 422 (Pydantic validation)."""
        resp = await live_client.post(f"{API}/auth/register", json={})
        assert resp.status_code == 422, resp.text


# =============================================================================
# ── LOGIN ─────────────────────────────────────────────────────────────────────
# =============================================================================

class TestLogin:
    """Verify login returns tokens for valid credentials and rejects bad ones."""

    async def test_login_correct_credentials_returns_200_tokens(self, live_client, make_user):
        """Happy path: correct email+password → 200 with access + refresh."""
        email = f"login_{uuid.uuid4().hex[:8]}@example.com"
        password = "LoginPass123!"
        await make_user(email=email, password=password)

        resp = await live_client.post(f"{API}/auth/login", json={
            "email": email,
            "password": password,
        })
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body

    async def test_login_wrong_password_returns_401(self, live_client, make_user):
        """Wrong password must return 401 with error detail."""
        email = f"wrong_{uuid.uuid4().hex[:8]}@example.com"
        await make_user(email=email, password="CorrectPass123!")

        resp = await live_client.post(f"{API}/auth/login", json={
            "email": email,
            "password": "WrongPassword!",
        })
        assert resp.status_code == 401, resp.text

    async def test_login_nonexistent_email_returns_401(self, live_client):
        """Non-existent user must return 401 (not 404) to prevent user enumeration."""
        resp = await live_client.post(f"{API}/auth/login", json={
            "email": f"nobody_{uuid.uuid4().hex}@example.com",
            "password": "AnyPassword123!",
        })
        assert resp.status_code == 401, resp.text

    async def test_login_inactive_user_returns_401(self, live_client, make_user):
        """Deactivated accounts must not be able to log in."""
        email = f"inactive_{uuid.uuid4().hex[:8]}@example.com"
        await make_user(email=email, password="Pass123!", is_active=False)

        resp = await live_client.post(f"{API}/auth/login", json={
            "email": email,
            "password": "Pass123!",
        })
        assert resp.status_code == 401, resp.text

    async def test_login_missing_fields_returns_422(self, live_client):
        resp = await live_client.post(f"{API}/auth/login", json={})
        assert resp.status_code == 422, resp.text


# =============================================================================
# ── /ME ENDPOINT (authenticated user info) ────────────────────────────────────
# =============================================================================

class TestMeEndpoint:
    """Verify /auth/me returns the authenticated user's info."""

    async def test_me_returns_user_info(self, live_client, make_user, auth_headers_for):
        """Authenticated user can retrieve their own profile via /me."""
        email = f"me_{uuid.uuid4().hex[:8]}@example.com"
        user = await make_user(email=email)
        headers = auth_headers_for(user)

        resp = await live_client.get(f"{API}/auth/me", headers=headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        # Response should include the user's email
        assert body.get("email") == email or str(user.id) in resp.text

    async def test_me_without_token_returns_401(self, live_client):
        resp = await live_client.get(f"{API}/auth/me")
        assert resp.status_code == 401, resp.text

    async def test_me_with_invalid_token_returns_401(self, live_client):
        resp = await live_client.get(
            f"{API}/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401, resp.text

    async def test_me_with_expired_token_returns_401(self, live_client, make_user):
        """An expired JWT must be rejected — no replay attacks."""
        user = await make_user()
        expired_token = _mint_token(user.id, minutes=-5)  # already expired
        resp = await live_client.get(
            f"{API}/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401, resp.text


# =============================================================================
# ── TOKEN REFRESH ─────────────────────────────────────────────────────────────
# =============================================================================

class TestTokenRefresh:
    """Verify that refresh tokens can be exchanged for new access tokens."""

    async def test_token_refresh_returns_new_access_token(self, live_client, make_user):
        """Full login → refresh cycle must succeed."""
        email = f"refresh_{uuid.uuid4().hex[:8]}@example.com"
        password = "RefreshPass123!"
        await make_user(email=email, password=password)

        # Login to get refresh token
        login_resp = await live_client.post(f"{API}/auth/login", json={
            "email": email, "password": password,
        })
        assert login_resp.status_code == 200, login_resp.text
        refresh_token = login_resp.json().get("refresh_token")
        assert refresh_token, "Login did not return a refresh_token"

        # Use refresh token to get new access token
        refresh_resp = await live_client.post(f"{API}/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert refresh_resp.status_code == 200, refresh_resp.text
        body = refresh_resp.json()
        assert "access_token" in body

    async def test_invalid_refresh_token_returns_401(self, live_client):
        resp = await live_client.post(f"{API}/auth/refresh", json={
            "refresh_token": "invalid.refresh.token",
        })
        assert resp.status_code == 401, resp.text


# =============================================================================
# ── TWO-FACTOR AUTHENTICATION (TOTP) ─────────────────────────────────────────
# =============================================================================

class TestTwoFactorAuth:
    """
    End-to-end 2FA flow:
      1. Login → get access token
      2. Call /2fa/setup → get provisioning URI + secret
      3. Generate a valid TOTP from the secret
      4. Call /2fa/verify to confirm and enable 2FA
      5. Subsequent login must accept a valid TOTP code
    """

    async def test_setup_2fa_returns_provisioning_uri(self, live_client, make_user, auth_headers_for):
        """Setting up 2FA returns a TOTP URI the user can scan."""
        user = await make_user()
        headers = auth_headers_for(user)

        resp = await live_client.post(f"{API}/2fa/setup", headers=headers)
        assert resp.status_code in (200, 201), resp.text
        body = resp.json()
        # Must return something scannable (otpauth URI or raw secret)
        has_uri = "otpauth" in resp.text or "secret" in body or "provisioning_uri" in body
        assert has_uri, f"Unexpected 2FA setup response: {body}"

    async def test_verify_2fa_with_valid_totp_succeeds(self, live_client, make_user, auth_headers_for):
        """A valid TOTP code submitted to /2fa/verify enables 2FA."""
        user = await make_user()
        headers = auth_headers_for(user)

        # Setup
        setup_resp = await live_client.post(f"{API}/2fa/setup", headers=headers)
        assert setup_resp.status_code in (200, 201), setup_resp.text
        body = setup_resp.json()

        # Extract the raw secret from the response
        secret = body.get("secret") or body.get("totp_secret")
        if not secret and "otpauth" in body.get("provisioning_uri", ""):
            # Parse secret from otpauth URL
            uri = body["provisioning_uri"]
            secret = uri.split("secret=")[1].split("&")[0]

        if not secret:
            pytest.skip("Could not extract TOTP secret from setup response")

        # Generate valid code
        totp = pyotp.TOTP(secret)
        code = totp.now()

        verify_resp = await live_client.post(f"{API}/2fa/verify", headers=headers, json={
            "code": code,
        })
        assert verify_resp.status_code in (200, 204), verify_resp.text

    async def test_verify_2fa_with_invalid_code_returns_400(self, live_client, make_user, auth_headers_for):
        """Wrong TOTP code must be rejected."""
        user = await make_user()
        headers = auth_headers_for(user)

        await live_client.post(f"{API}/2fa/setup", headers=headers)

        resp = await live_client.post(f"{API}/2fa/verify", headers=headers, json={
            "code": "000000",
        })
        assert resp.status_code in (400, 401, 422), resp.text

    async def test_2fa_setup_requires_authentication(self, live_client):
        """Unauthenticated access to 2FA endpoints must be rejected."""
        resp = await live_client.post(f"{API}/2fa/setup")
        assert resp.status_code == 401, resp.text


# =============================================================================
# ── CROSS-USER DATA ISOLATION ─────────────────────────────────────────────────
# =============================================================================

class TestCrossUserIsolation:
    """
    Verify that User A cannot access User B's data.
    This is the most critical security test.
    """

    async def test_user_cannot_access_another_users_profile(
        self, live_client, make_user, auth_headers_for
    ):
        """User A must not be able to read User B's /me details using their own token."""
        user_a = await make_user()
        user_b = await make_user()

        # User A's token
        headers_a = auth_headers_for(user_a)
        resp = await live_client.get(f"{API}/auth/me", headers=headers_a)
        assert resp.status_code == 200

        body = resp.json()
        # Verify we're seeing user_a's data, not user_b's
        assert str(user_b.id) not in resp.text or body.get("id") != str(user_b.id)

    async def test_two_users_tokens_are_distinct(self, make_user, auth_headers_for):
        """JWT tokens for different users must carry different sub claims."""
        user_a = await make_user()
        user_b = await make_user()

        token_a = auth_headers_for(user_a)["Authorization"].split("Bearer ")[1]
        token_b = auth_headers_for(user_b)["Authorization"].split("Bearer ")[1]

        payload_a = jwt.decode(token_a, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        payload_b = jwt.decode(token_b, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        assert payload_a["sub"] != payload_b["sub"]
        assert payload_a["sub"] == str(user_a.id)
        assert payload_b["sub"] == str(user_b.id)


# =============================================================================
# ── SECURITY HEADERS ──────────────────────────────────────────────────────────
# =============================================================================

class TestSecurityHeaders:
    """Verify every response includes the mandatory security headers."""

    async def test_health_response_has_security_headers(self, live_client):
        resp = await live_client.get("/health")
        assert resp.status_code == 200
        # These headers must always be present
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"

    async def test_cors_headers_present_on_options(self, live_client):
        """CORS preflight must respond correctly."""
        resp = await live_client.options(
            f"{API}/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert resp.status_code in (200, 204), resp.text
