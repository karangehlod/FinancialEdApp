"""
GDPR compliance API endpoints.

Routes:
  GET    /auth/data-export  → download full data export (ZIP/JSON)
  DELETE /auth/account      → anonymise and delete account
  GET    /legal/privacy     → privacy policy (static text)
  GET    /legal/terms       → terms of service (static text)
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_auth_db, get_data_db
from app.db.models.auth import User
from app.dependencies import get_current_user
from app.services.gdpr_service import GDPRService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["gdpr"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AccountDeleteRequest(BaseModel):
    password: str = Field(..., min_length=1, description="Current password for confirmation")
    confirmation: str = Field(
        ...,
        description='Must be exactly "DELETE MY ACCOUNT" to confirm',
        pattern=r"^DELETE MY ACCOUNT$",
    )


class AccountDeleteResponse(BaseModel):
    message: str
    deleted_at: str
    summary: dict


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get(
    "/auth/data-export",
    summary="Download a ZIP archive of all your personal data (GDPR Article 20)",
    responses={
        200: {
            "content": {"application/zip": {}},
            "description": "ZIP archive containing all user data as JSON",
        }
    },
)
async def export_user_data(
    request: Request,
    current_user: User = Depends(get_current_user),
    auth_db: AsyncSession = Depends(get_auth_db),
    data_db: AsyncSession = Depends(get_data_db),
):
    """
    Export all personal data for the authenticated user.

    Returns a ZIP archive containing:
      - data_export.json (profile, expenses, budgets, goals, loans, notifications)
      - README.txt (explanation of data format and GDPR information)

    Rate limited: 1 export per 24 hours (enforced by middleware).
    """
    gdpr_service = GDPRService(auth_db=auth_db, data_db=data_db)

    try:
        zip_bytes = await gdpr_service.export_user_data(str(current_user.id))
    except Exception as exc:
        logger.error("Data export failed for user %s: %s", current_user.id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate data export. Please try again later.",
        )

    filename = f"financialedapp_export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.zip"

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(zip_bytes)),
            "X-GDPR-Export": "true",
        },
    )


@router.delete(
    "/auth/account",
    response_model=AccountDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Permanently delete your account and all associated data (GDPR Article 17)",
)
async def delete_account(
    payload: AccountDeleteRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    auth_db: AsyncSession = Depends(get_auth_db),
    data_db: AsyncSession = Depends(get_data_db),
):
    """
    Permanently delete (anonymise) the authenticated user's account.

    - Requires password confirmation AND the exact string "DELETE MY ACCOUNT".
    - All PII is replaced with pseudonymous values immediately.
    - All financial data is soft-deleted (deleted_at set to NOW()).
    - All refresh tokens are revoked immediately.
    - The operation is irreversible.
    """
    # Verify password
    password_hasher = getattr(request.app.state, "password_hasher", None)
    if password_hasher is None:
        from app.core.provider_implementations import BcryptPasswordHasher
        password_hasher = BcryptPasswordHasher(rounds=12)

    if not password_hasher.verify(payload.password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password.",
        )

    gdpr_service = GDPRService(auth_db=auth_db, data_db=data_db)

    try:
        summary = await gdpr_service.delete_user_account(str(current_user.id))
    except Exception as exc:
        logger.error("Account deletion failed for user %s: %s", current_user.id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account deletion failed. Please contact support.",
        )

    deleted_at = datetime.now(timezone.utc).isoformat()
    logger.info(
        "Account deletion completed: user=%s email=%s",
        current_user.id,
        current_user.email,
    )

    return AccountDeleteResponse(
        message="Your account and all associated data have been permanently deleted.",
        deleted_at=deleted_at,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Legal pages (static content)
# ---------------------------------------------------------------------------

@router.get("/legal/privacy", summary="Privacy Policy")
async def privacy_policy():
    """Returns the application privacy policy."""
    return JSONResponse({
        "title": "Privacy Policy",
        "last_updated": "2024-01-01",
        "data_controller": "FinancialEdApp",
        "contact": "privacy@financialedu.com",
        "summary": (
            "We collect only the data necessary to provide our financial education service. "
            "You have the right to access, correct, export, and delete your data at any time. "
            "We never sell your personal data."
        ),
        "rights": [
            "Right to access your data (GET /auth/data-export)",
            "Right to data portability (ZIP/JSON export)",
            "Right to erasure (DELETE /auth/account)",
            "Right to rectification (PUT /api/v1/users/me)",
            "Right to object to processing (contact privacy@financialedu.com)",
        ],
        "data_retention": "Account data is retained for 2 years after last login, then anonymised.",
        "cookies": "We use only strictly necessary session cookies. No tracking cookies.",
        "third_parties": "We share no data with third parties for marketing purposes.",
    })


@router.get("/legal/terms", summary="Terms of Service")
async def terms_of_service():
    """Returns the terms of service summary."""
    return JSONResponse({
        "title": "Terms of Service",
        "last_updated": "2024-01-01",
        "service": "FinancialEdApp — Personal Finance Education Platform",
        "summary": (
            "By using FinancialEdApp, you agree to these terms. "
            "The service is provided for educational purposes only. "
            "We are not financial advisors."
        ),
        "disclaimer": (
            "FinancialEdApp is an educational tool and does not constitute financial advice. "
            "Always consult a qualified financial advisor before making investment decisions."
        ),
        "governing_law": "These terms are governed by the laws of the applicable jurisdiction.",
    })
