WebSocket cookie-based auth instructions (server)

1) Purpose
- Use httpOnly cookies to authenticate WebSocket upgrade requests. This avoids exposing tokens in query strings or client-side JS.

2) Server changes (example in Python / FastAPI + Starlette)
- On login, set cookie:
    response.set_cookie(
      key="finedu_refresh",
      value=refresh_token,
      httponly=True,
      secure=True,
      samesite="lax",
      path='/',
      max_age=ref_exp_seconds
    )

- WebSocket endpoint:
    from starlette.websockets import WebSocket

    async def websocket_endpoint(websocket: WebSocket):
        # Accept the handshake only after validating cookie
        cookies = websocket.cookies
        refresh = cookies.get('finedu_refresh')
        if not refresh:
            await websocket.close(code=4401)  # custom unauthorized code
            return
        # Validate refresh or session via your auth service
        user = await auth_service.validate_refresh_cookie(refresh)
        if not user:
            await websocket.close(code=4401)
            return
        await websocket.accept()
        # proceed with WS loop

3) Origin checks
- Verify websocket.headers['origin'] matches allowed origins for security.

4) Cross-origin notes
- If frontend and backend are on different domains, set cookie domain and SameSite=None; ensure TLS and CORS are properly configured.

5) Testing
- Use browser to login, ensure cookie is present in network tab (httpOnly flags hide it from JS)
- Then open WS connection — the cookie should be sent automatically during upgrade

6) Fallback for non-cookie setups
- If cookie-based isn't possible, accept `Sec-WebSocket-Protocol` header value as a bearer token (less preferred); ensure server reads subprotocols parameter.

7) Logging/security
- NEVER log cookie values or token previews in server logs.
- Log only user IDs and event outcomes.
