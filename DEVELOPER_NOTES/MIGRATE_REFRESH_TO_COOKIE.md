Migration plan: Move refresh token to httpOnly Secure cookie

Goal
- Store the refresh token in an httpOnly, Secure cookie (SameSite=Lax or Strict) set by the backend on login. Keep access token as short-lived JWT in memory (or localStorage if strictly needed) and use the cookie for refresh.

Rationale
- httpOnly cookies mitigate XSS-based token theft (refresh token can't be read from JS).
- Server-side rotation of refresh tokens improves security and allows revocation.

High-level steps (backend)
1. Add a new auth endpoint behavior on login (POST /api/v1/auth/login):
   - After validating credentials, generate access_token and refresh_token as before.
   - Set cookie:
     - Name: `finedu_refresh` (or `refresh_token`)
     - Value: refresh_token
     - Flags: HttpOnly, Secure, SameSite=Lax (or None if cross-site), Path=/, Max-Age matching refresh expiry
     - Optionally set Domain if multi-subdomain
   - Return `access_token` in JSON, but do NOT return refresh_token in body.
2. Modify refresh endpoint (POST /api/v1/auth/refresh):
   - Read refresh token from the cookie (server-side cookie parsing).
   - Validate and rotate the refresh token if using rotation.
   - Issue new access_token (and rotated refresh token cookie if rotation enabled).
   - Return access_token in response.
3. Modify logout endpoint (POST /api/v1/auth/logout):
   - Revoke refresh token server-side and clear cookie: set cookie with empty value and Max-Age=0.
4. WebSocket auth:
   - During upgrade, validate cookies on the handshake (server must parse cookies and validate session).
5. CSRF considerations:
   - When using cookies for authentication and state-changing POST requests, protect endpoints with CSRF tokens or use same-site cookies + strict CORS + double-submit token.

High-level steps (frontend)
1. Login flow:
   - Call POST /auth/login to get access_token in response body.
   - Do not store refresh_token in localStorage; backend sets the cookie instead.
   - Store access_token in tokenManager (in-memory or localStorage if necessary).
2. Refresh flow:
   - When needing to refresh, call POST /auth/refresh without a body. The browser will include the cookie automatically.
   - Update access_token from response and store via tokenManager.
3. Logout:
   - Call POST /auth/logout; server clears cookie and revokes tokens.
   - Client clears access token and redirects to /login.
4. WebSocket:
   - Create WebSocket to ws://... without query string auth; browser sends cookie during upgrade.

Testing
- Unit tests for server refresh endpoint accepting cookie.
- Integration tests: login -> cookie set, refresh via cookie returns new access token, logout clears cookie.
- E2E test that WebSocket connection succeeds after login when cookie present.

Rollout plan
- Deploy backend changes behind a feature flag to support both cookie and token-based refresh.
- Update frontend to call new endpoints.
- Monitor error rates and report any auth failures.

Fallback
- If users still have refresh tokens in localStorage, invalidate them server-side on first login/refresh and issue new cookie-based refresh tokens. Notify users or force logout.

Security notes
- Use Secure and HttpOnly flags.
- Consider setting cookie SameSite to Lax/Strict to reduce CSRF risk.
- Implement token rotation with single-use refresh tokens stored as hashes server-side.
- Add monitoring and alerting for refresh token misuse.
