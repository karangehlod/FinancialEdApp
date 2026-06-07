"""Authentication endpoints with Redis caching, rate limiting, and DB refresh tokens."""
from fastapi import APIRouter, Depends, Request, status, HTTPException, BackgroundTasks, Response
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_auth_db, get_data_db
from app.schemas.auth import UserRegister, UserLogin, Token, TokenResponse, UserResponse, PasswordChange
from app.schemas.user_profile import UserProfileUpdate, UserProfileResponse
from app.schemas.financial_profile import FinancialProfileUpdate, FinancialProfileResponse
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.services.verification_token_service import VerificationTokenService
from app.repositories.user_repository import UserRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_profile_repository import UserProfileRepository
from app.core.exceptions import UserAlreadyExistsError, DatabaseError, AuthenticationError
from app.core.logging import get_logger
from app.core.provider_implementations import BcryptPasswordHasher, JWTTokenProvider
from app.config import settings
from app.dependencies import get_current_user, get_redis_cache, get_password_hasher, get_token_provider


# ── Pydantic request bodies for new P1 endpoints ──────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class VerifyEmailRequest(BaseModel):
    token: str

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/auth", tags=["Authentication"])

def get_auth_service(
    request: Request,
    auth_db: AsyncSession = Depends(get_auth_db),
    password_hasher: BcryptPasswordHasher = Depends(get_password_hasher),
    token_provider: JWTTokenProvider = Depends(get_token_provider),
    cache=Depends(get_redis_cache),
) -> AuthService:
    """
    Build an AuthService per request, sharing singleton providers from app.state.
    The RefreshTokenRepository uses the same auth DB session.
    """
    user_repo = UserRepository(auth_db)
    refresh_token_repo = RefreshTokenRepository(auth_db)
    return AuthService(
        user_repository=user_repo,
        password_hasher=password_hasher,
        token_provider=token_provider,
        refresh_token_repository=refresh_token_repo,
        cache=cache,
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "User successfully registered",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "email": "user@example.com",
                        "created_at": "2026-01-14T10:00:00",
                    }
                }
            },
        },
        400: {
            "description": "User already exists or invalid input",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": {
                            "code": "USER_002",
                            "message": "Email already registered",
                            "details": {"email": "user@example.com"},
                        },
                    }
                }
            },
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": {
                            "code": "VAL_001",
                            "message": "Validation failed",
                            "details": {
                                "validation_errors": [
                                    {
                                        "field": "email",
                                        "message": "Invalid email format",
                                        "type": "value_error.email",
                                    }
                                ]
                            },
                        },
                    }
                }
            },
        },
    },
)
async def register(
    user_data: UserRegister,
    auth_db: AsyncSession = Depends(get_auth_db),
    data_db: AsyncSession = Depends(get_data_db),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Register a new user account.

    **Request body:**
    - **email**: Valid email address (must be unique)
    - **password**: Minimum 8 characters with uppercase, lowercase, and number
    - **name**: Optional user display name

    **Errors:**
    - **USER_002**: Email already registered
    - **VAL_001**: Invalid email format or weak password
    - **SRV_001**: Internal server error

    **Example:**
    ```json
    {
        "email": "john@example.com",
        "password": "SecurePass123",
        "name": "John Doe"
    }
    ```
    """
    logger.info(f"User registration attempt", email=user_data.email)

    # Create user in auth database
    try:
        user = await auth_service.register_user(user_data)
        logger.info(f"User registered successfully", user_id=str(user.id), email=user_data.email)
        
        # Create user profile in data database
        from app.repositories.user_profile_repository import UserProfileRepository
        profile_repo = UserProfileRepository(data_db)
        await profile_repo.create_profile(user.id)
        logger.info(f"User profile created", user_id=str(user.id))
    except UserAlreadyExistsError as e:
        logger.warning(f"Registration failed: user already exists", email=user_data.email)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"User registration failed", email=user_data.email, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user",
        )

    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        200: {
            "description": "Login successful",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "user": {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "email": "user@example.com",
                            "is_active": True,
                            "is_verified": True,
                        },
                    }
                }
            },
        },
        401: {
            "description": "Invalid credentials",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": {
                            "code": "AUTH_001",
                            "message": "Incorrect email or password",
                            "details": {},
                        },
                    }
                }
            },
        },
    },
)
async def login(
    credentials: UserLogin,
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Login with email and password to get JWT token.

    **Request body:**
    - **email**: User email address
    - **password**: User password

    **Returns:**
    - **access_token**: JWT token for API authentication
    - **token_type**: Always "bearer"
    - **user**: Authenticated user information

    **Errors:**
    - **AUTH_001**: Invalid email or password
    - **AUTH_003**: Token generation failed

    **Example:**
    ```json
    {
        "email": "john@example.com",
        "password": "SecurePass123"
    }
    ```

    **Usage:**
    ```bash
    curl -X POST http://localhost:8000/api/v1/auth/login \\
      -H "Content-Type: application/json" \\
      -d '{"email": "john@example.com", "password": "SecurePass123"}'
    ```

    Then use the returned token in subsequent requests:
    ```bash
    curl -H "Authorization: Bearer {access_token}" http://localhost:8000/api/v1/budgets/
    ```
    """
    logger.info(f"Login attempt", email=credentials.email)

    try:
        user = await auth_service.authenticate_user(credentials.email, credentials.password)
    except AuthenticationError as exc:
        # Account locked out
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc))

    if not user:
        logger.warning(f"Login failed: invalid credentials", email=credentials.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    logger.info(f"User logged in successfully", user_id=str(user.id), email=credentials.email)

    # Pass User-Agent as device_info for per-device session tracking
    device_info = request.headers.get("user-agent", "")[:500]
    tokens = await auth_service.create_user_token(user, device_info=device_info)

    # Set refresh token as an HttpOnly, Secure cookie to avoid exposing it to JS.
    try:
        refresh_value = tokens.get("refresh_token")
        if refresh_value:
            max_age = int(settings.REFRESH_TOKEN_EXPIRE_DAYS) * 24 * 60 * 60
            response.set_cookie(
                key="finedu_refresh",
                value=refresh_value,
                httponly=True,
                secure=not settings.DEBUG,
                samesite="lax",
                path="/",
                max_age=max_age,
            )
    except Exception:
        logger.warning("Failed to set refresh cookie for user %s", user.id)

    # For backward compatibility we still include refresh_token in the body for now.
    return tokens


@router.get(
    "/me",
    response_model=dict,  # Return dict instead of UserResponse to include profile fields
    responses={
        200: {
            "description": "Current user information",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "email": "user@example.com",
                        "first_name": "John",
                        "last_name": "Doe",
                        "currency": "USD",
                        "created_at": "2026-01-14T10:00:00",
                    }
                }
            },
        },
        401: {
            "description": "Missing or invalid token",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": {
                            "code": "AUTH_004",
                            "message": "Missing authentication token",
                            "details": {},
                        },
                    }
                }
            },
        },
    },
)
async def get_me(
    current_user=Depends(get_current_user),
    data_db: AsyncSession = Depends(get_data_db)
):
    """
    Get current authenticated user profile including profile fields.

    **Authentication:** Required (Bearer token)

    **Returns:** Current user information with profile fields

    **Errors:**
    - **AUTH_004**: Missing authentication token
    - **AUTH_002**: Token expired
    - **AUTH_003**: Invalid token

    **Example:**
    ```bash
    curl -H "Authorization: Bearer {access_token}" http://localhost:8000/api/v1/auth/me
    ```
    """
    logger.debug(f"Getting current user info", user_id=str(current_user.id))
    
    # Fetch user profile to include profile fields
    try:
        from app.repositories.user_profile_repository import UserProfileRepository
        
        profile_repo = UserProfileRepository(data_db)
        profile = await profile_repo.get_profile_by_user_id(current_user.id)
        
        # Build a combined display name from first/last or fall back to
        # the profile.name field so the frontend can use user.name directly.
        first = (profile.first_name or "") if profile else ""
        last = (profile.last_name or "") if profile else ""
        display_name = f"{first} {last}".strip() or (profile.name if profile else None)

        # Return user data plus profile fields
        user_data = {
            "id": str(current_user.id),
            "email": current_user.email,
            "is_active": current_user.is_active,
            "is_verified": current_user.is_verified,
            "created_at": current_user.created_at,
            "first_name": profile.first_name if profile else None,
            "last_name": profile.last_name if profile else None,
            "name": display_name,
            "currency": profile.currency if profile else "USD",
        }
        return user_data
    except Exception as e:
        logger.warning(f"Failed to fetch profile for user {current_user.id}, returning user data only", exc_info=True)
        # Fall back to basic user data if profile fetch fails
        return {
            "id": str(current_user.id),
            "email": current_user.email,
            "is_active": current_user.is_active,
            "is_verified": current_user.is_verified,
            "created_at": current_user.created_at,
            "name": None,
        }


@router.put(
    "/profile",
    response_model=UserProfileResponse,
)
async def update_profile(
    profile_data: UserProfileUpdate,
    current_user=Depends(get_current_user),
    data_db: AsyncSession = Depends(get_data_db),
):
    """
    Update user profile information (currency, name, preferences).

    **Request body:**
    - **name**: Optional user display name
    - **currency**: Preferred currency code (e.g., USD, EUR, GBP, INR, JPY)
    - **country**: Country code
    - **knowledge_level**: User knowledge level
    - **risk_tolerance**: User risk tolerance
    - **consent_given**: Consent flag

    **Returns:** Updated user profile information

    **Errors:**
    - **USER_004**: User not found
    - **SRV_001**: Internal server error

    **Example:**
    ```bash
    curl -X PUT http://localhost:8000/api/v1/auth/profile \\
      -H "Authorization: Bearer {access_token}" \\
      -H "Content-Type: application/json" \\
      -d '{"currency": "USD", "name": "John Doe"}'
    ```
    """
    logger.info(f"Update profile attempt", user_id=str(current_user.id))

    try:
        from app.repositories.user_profile_repository import UserProfileRepository
        
        profile_repo = UserProfileRepository(data_db)
        updated_profile = await profile_repo.update_profile(current_user.id, profile_data)
        
        if not updated_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found",
            )
        
        logger.info(f"User profile updated", user_id=str(current_user.id))
        return updated_profile
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update profile", user_id=str(current_user.id), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile",
        )


@router.get(
    "/financial-profile",
    response_model=FinancialProfileResponse,
)
async def get_financial_profile(
    current_user=Depends(get_current_user),
    data_db: AsyncSession = Depends(get_data_db),
):
    """
    Get user financial profile information.

    **Authentication:** Required (Bearer token)

    **Returns:** User financial profile information

    **Errors:**
    - **FIN_002**: Financial profile not found
    - **AUTH_002**: Token expired
    - **AUTH_003**: Invalid token

    **Example:**
    ```bash
    curl -H "Authorization: Bearer {access_token}" http://localhost:8000/api/v1/auth/financial-profile
    ```
    """
    logger.info(f"Get financial profile attempt", user_id=str(current_user.id))

    try:
        from app.repositories.financial_profile_repository import FinancialProfileRepository
        
        financial_repo = FinancialProfileRepository(data_db)
        profile = await financial_repo.get_profile_by_user_id(current_user.id)
        
        if not profile:
            # Auto-create an empty profile so the frontend never gets a 404
            profile = await financial_repo.create_profile(current_user.id)
        
        logger.info(f"Financial profile retrieved", user_id=str(current_user.id))
        return profile
    except Exception as e:
        logger.error(f"Failed to retrieve financial profile", user_id=str(current_user.id), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve financial profile",
        )


@router.put(
    "/financial-profile",
    response_model=FinancialProfileResponse,
)
async def update_financial_profile(
    financial_data: FinancialProfileUpdate,
    current_user=Depends(get_current_user),
    data_db: AsyncSession = Depends(get_data_db),
):
    """
    Update user financial profile (salary, currency, fixed expenses).

    **Request body:**
    - **monthly_salary**: Monthly income in decimal
    - **currency**: Preferred currency code
    - **rent**: Monthly rent amount
    - **insurance**: Monthly insurance amount
    - **subscriptions**: Monthly subscriptions amount

    **Returns:** Updated financial profile information

    **Errors:**
    - **FIN_002**: Financial profile not found
    - **SRV_001**: Internal server error

    **Example:**
    ```bash
    curl -X PUT http://localhost:8000/api/v1/auth/financial-profile \\
      -H "Authorization: Bearer {access_token}" \\
      -H "Content-Type: application/json" \\
      -d '{"monthly_salary": 50000, "currency": "INR", "rent": 15000}'
    ```
    """
    logger.info(f"Update financial profile attempt", user_id=str(current_user.id))

    try:
        from app.repositories.financial_profile_repository import FinancialProfileRepository
        
        financial_repo = FinancialProfileRepository(data_db)
        updated_profile = await financial_repo.update_profile(current_user.id, financial_data)
        
        if not updated_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Financial profile not found",
            )
        
        logger.info(f"User financial profile updated", user_id=str(current_user.id))
        return updated_profile
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update financial profile", user_id=str(current_user.id), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update financial profile",
        )


@router.post(
    "/change-password",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
async def change_password(
    password_data: PasswordChange,
    request: Request,
    current_user=Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Change user password.

    **Request body:**
    - **current_password**: Current password
    - **new_password**: New password (minimum 8 characters)

    **Returns:** Success message

    **Errors:**
    - **AUTH_001**: Invalid old password
    - **SRV_001**: Internal server error

    **Example:**
    ```bash
    curl -X POST http://localhost:8000/api/v1/auth/change-password \\
      -H "Authorization: Bearer {access_token}" \\
      -H "Content-Type: application/json" \\
      -d '{"old_password": "current123", "new_password": "newpass123"}'
    ```
    """
    logger.info(f"Change password attempt", user_id=str(current_user.id))

    try:
        success = await auth_service.change_password(
            current_user.id,
            password_data.current_password,
            password_data.new_password,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to change password",
            )

        logger.info(f"Password changed successfully", user_id=str(current_user.id))
        return {"success": True, "message": "Password changed successfully. Please log in again."}
    except AuthenticationError as e:
        logger.warning(f"Password change authentication error", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to change password", user_id=str(current_user.id), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password",
        )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    current_user=Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
    response: Response = None,
):
    """
    Logout the current user.

    Revokes the refresh token from the DB and adds the user to the Redis
    session blacklist so that in-flight access tokens fail immediately.

    **Authentication:** Required (Bearer token)

    **Returns:** Success message
    """
    from fastapi.security import HTTPBearer
    from fastapi import Header
    from typing import Optional as Opt

    # Try to extract the refresh token from the body
    try:
        body = await request.json()
        refresh_token = body.get("refresh_token")
    except Exception:
        refresh_token = None

    # Prefer explicit refresh_token in body, fall back to cookie
    if not refresh_token:
        try:
            refresh_token = request.cookies.get("finedu_refresh")
        except Exception:
            refresh_token = None

    await auth_service.logout_user(current_user.id, refresh_token=refresh_token)
    logger.info("User logged out", user_id=str(current_user.id))

    # Clear the refresh cookie
    try:
        if response is not None:
            response.delete_cookie("finedu_refresh", path="/")
    except Exception:
        logger.warning("Failed to clear refresh cookie for user %s", current_user.id)

    return {"success": True, "message": "Logged out successfully"}


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh_token(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    response: Response = None,
):
    """
    Rotate a refresh token to get a new access + refresh token pair.

    The old refresh token is immediately revoked in the DB.
    If the token has already been used (possible theft), all sessions for the
    user are revoked automatically.

    **Request body:**
    - **refresh_token**: The refresh JWT issued at login or previous refresh.

    **Returns:** New access_token, refresh_token, and user info.

    **Errors:**
    - **401**: Invalid, expired, or revoked refresh token.
    """
    # Accept refresh token in body (legacy) or from httpOnly cookie (preferred)
    try:
        body = await request.json()
        refresh_token_str = body.get("refresh_token")
    except Exception:
        refresh_token_str = None

    if not refresh_token_str:
        # Try cookie
        try:
            refresh_token_str = request.cookies.get("finedu_refresh")
        except Exception:
            refresh_token_str = None

    if not refresh_token_str:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="refresh_token is required (body or cookie)",
        )

    try:
        device_info = request.headers.get("user-agent", "")[:500]
        tokens = await auth_service.refresh_user_token(refresh_token_str, device_info=device_info)

        # Set rotated refresh token cookie
        try:
            new_refresh = tokens.get("refresh_token")
            if new_refresh and response is not None:
                max_age = int(settings.REFRESH_TOKEN_EXPIRE_DAYS) * 24 * 60 * 60
                response.set_cookie(
                    key="finedu_refresh",
                    value=new_refresh,
                    httponly=True,
                    secure=not settings.DEBUG,
                    samesite="lax",
                    path="/",
                    max_age=max_age,
                )
        except Exception:
            logger.warning("Failed to set rotated refresh cookie")

        # Return token response (still includes refresh_token for compatibility)
        return tokens
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))


# ---------------------------------------------------------------------------
# P1-2: Email Verification + Password Reset
# ---------------------------------------------------------------------------

def _get_verification_service(
    request: Request,
    token_provider: JWTTokenProvider = Depends(get_token_provider),
    cache=Depends(get_redis_cache),
) -> VerificationTokenService:
    """Build a VerificationTokenService per request (token_provider is a singleton)."""
    return VerificationTokenService(token_provider=token_provider, cache=cache)


@router.post(
    "/verify-email",
    status_code=status.HTTP_200_OK,
    tags=["Authentication"],
    summary="Verify email address with a one-time token",
)
async def verify_email(
    body: VerifyEmailRequest,
    auth_db: AsyncSession = Depends(get_auth_db),
    verification_service: VerificationTokenService = Depends(_get_verification_service),
):
    """
    Verify a user's email address using the token sent to their inbox.

    The token is single-use and expires in 1 hour.

    **Request body:**
    - **token**: The JWT token from the verification email link.

    **Errors:**
    - **400**: Invalid, expired, or already-used token.
    """
    try:
        user_id = await verification_service.consume_verification_token(body.token)
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    # Mark user as verified in the DB
    user_repo = UserRepository(auth_db)
    user = await user_repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not user.is_verified:
        user.is_verified = True
        await auth_db.commit()
        logger.info("Email verified for user %s", user_id)

    return {"success": True, "message": "Email verified successfully"}


@router.post(
    "/resend-verification",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Authentication"],
    summary="Resend email verification link",
)
async def resend_verification(
    body: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    auth_db: AsyncSession = Depends(get_auth_db),
    verification_service: VerificationTokenService = Depends(_get_verification_service),
):
    """
    Resend the email verification link.

    Rate-limited to 3 requests per email per hour.
    Returns 202 even if the email is not found (prevents user enumeration).
    """
    user_repo = UserRepository(auth_db)
    user = await user_repo.get_user_by_email(body.email)

    if user and not user.is_verified:
        try:
            token = await verification_service.create_verification_token(user.id, user.email)
            # Send email in background — never block the response
            from app.services.email_service import get_email_service
            email_svc = get_email_service()
            verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
            background_tasks.add_task(
                email_svc.send_generic_email,
                to_email=user.email,
                subject="Verify your FinancialEdApp account",
                title="Email Verification",
                message=f"Click the link below to verify your email address.",
                action_url=verify_url,
                action_text="Verify Email",
            )
        except AuthenticationError:
            # Rate limited — still return 202 to prevent enumeration
            pass

    return {"success": True, "message": "If that email exists and is unverified, a link has been sent"}


@router.post(
    "/forgot-password",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Authentication"],
    summary="Request a password reset email",
)
async def forgot_password(
    body: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    auth_db: AsyncSession = Depends(get_auth_db),
    verification_service: VerificationTokenService = Depends(_get_verification_service),
):
    """
    Send a password reset email.

    Rate-limited to 3 requests per email per hour.
    Always returns 202 (even if email not found) to prevent user enumeration.

    **Request body:**
    - **email**: The account email address.
    """
    user_repo = UserRepository(auth_db)
    user = await user_repo.get_user_by_email(body.email)

    if user and user.is_active:
        try:
            token = await verification_service.create_password_reset_token(user.id, user.email)
            from app.services.email_service import get_email_service
            email_svc = get_email_service()
            reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
            background_tasks.add_task(
                email_svc.send_generic_email,
                to_email=user.email,
                subject="Reset your FinancialEdApp password",
                title="Password Reset Request",
                message=(
                    "We received a request to reset your password. "
                    "This link expires in 1 hour. If you did not request this, ignore this email."
                ),
                action_url=reset_url,
                action_text="Reset Password",
            )
            logger.info("Password reset email queued for user %s", user.id)
        except AuthenticationError:
            # Rate limited — log but don't reveal to caller
            logger.warning("Password reset rate limit hit for email %s", body.email)

    return {"success": True, "message": "If that email is registered, a password reset link has been sent"}


@router.post(
    "/reset-password",
    status_code=status.HTTP_200_OK,
    tags=["Authentication"],
    summary="Reset password using a one-time token",
)
async def reset_password(
    body: ResetPasswordRequest,
    auth_db: AsyncSession = Depends(get_auth_db),
    verification_service: VerificationTokenService = Depends(_get_verification_service),
    password_hasher: BcryptPasswordHasher = Depends(get_password_hasher),
):
    """
    Reset a user's password using the token from the reset email.

    The token is single-use and expires in 1 hour.
    All active sessions are revoked after a successful reset.

    **Request body:**
    - **token**: The JWT token from the reset email link.
    - **new_password**: The new password (minimum 8 characters).
    """
    # Validate new password length before touching the DB
    if len(body.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters",
        )

    try:
        user_id = await verification_service.consume_password_reset_token(body.token)
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    user_repo = UserRepository(auth_db)
    user = await user_repo.get_user_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    new_hash = password_hasher.hash_password(body.new_password)
    await user_repo.update_password(user_id, new_hash)

    # Revoke all existing refresh tokens — force re-login everywhere
    from app.repositories.refresh_token_repository import RefreshTokenRepository
    rt_repo = RefreshTokenRepository(auth_db)
    revoked = await rt_repo.revoke_all_for_user(user_id)
    logger.info("Password reset: revoked %d sessions for user %s", revoked, user_id)

    return {"success": True, "message": "Password reset successfully. Please log in with your new password."}
