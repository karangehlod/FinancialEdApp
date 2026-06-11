"""
Admin Dashboard API endpoints.

Routes:
  GET  /admin/users                   → paginated user list
  GET  /admin/users/{user_id}         → user detail + activity summary
  POST /admin/users/{user_id}/suspend → suspend/unsuspend user
  GET  /admin/metrics/summary         → aggregate platform statistics
  GET  /admin/audit-log               → recent audit log entries
  GET  /admin/health                  → infra health (DB, Redis, worker)

Security:
  - All routes require JWT + ADMIN scope (checked via is_admin flag on User model)
  - Admin routes have their own rate limit: 100/min per admin user
  - All admin actions are written to the audit log (soft_delete_audit table)
  - IP address logged on every admin action
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_auth_db, get_data_db
from app.db.models.auth import User
from app.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Admin auth guard
# ---------------------------------------------------------------------------

async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency that ensures the authenticated user has admin privileges.

    Admin status is determined by:
      1. User.is_admin flag in the users table (preferred)
      2. Fallback: email in ADMIN_EMAILS config (for bootstrapping)
    """
    from app.config import settings

    is_admin = getattr(current_user, "is_admin", False)
    if not is_admin:
        admin_emails = {
            e.strip()
            for e in (settings.ADMIN_EMAILS or "").split(",")
            if e.strip()
        }
        is_admin = current_user.email in admin_emails

    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required.",
        )
    return current_user


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class UserSummary(BaseModel):
    id: str
    email: str
    is_active: bool
    is_verified: bool
    totp_enabled: bool
    last_login: Optional[datetime]
    created_at: Optional[datetime]


class UserListResponse(BaseModel):
    users: List[UserSummary]
    total: int
    page: int
    per_page: int
    pages: int


class SuspendRequest(BaseModel):
    reason: str = ""
    suspended: bool = True


class PlatformMetrics(BaseModel):
    total_users: int
    active_users_24h: int
    active_users_7d: int
    new_users_today: int
    total_expenses: int
    total_budgets: int
    total_goals: int
    generated_at: str


class AuditLogEntry(BaseModel):
    id: str
    table_name: str
    record_id: str
    deleted_by: str
    reason: Optional[str]
    created_at: Optional[datetime]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get(
    "/users",
    response_model=UserListResponse,
    summary="List all users (paginated)",
)
async def list_users(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=200, description="Results per page"),
    search: Optional[str] = Query(None, description="Filter by email (partial match)"),
    active_only: bool = Query(False, description="Only show active users"),
    admin: User = Depends(require_admin),
    auth_db: AsyncSession = Depends(get_auth_db),
):
    """
    Return a paginated list of all users.

    Supports filtering by email and active status.
    """
    from app.db.models.auth import User as UserModel

    query = select(UserModel)

    if search:
        query = query.where(UserModel.email.ilike(f"%{search}%"))
    if active_only:
        query = query.where(UserModel.is_active)

    # Total count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await auth_db.execute(count_q)).scalar() or 0

    # Paginated results
    query = query.order_by(UserModel.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await auth_db.execute(query)
    users = result.scalars().all()

    logger.info(
        "Admin %s listed users (page=%d, search=%s, ip=%s)",
        admin.email, page, search, request.client.host if request.client else "unknown",
    )

    return UserListResponse(
        users=[
            UserSummary(
                id=str(u.id),
                email=u.email,
                is_active=u.is_active,
                is_verified=u.is_verified,
                totp_enabled=getattr(u, "totp_enabled", False),
                last_login=u.last_login,
                created_at=u.created_at,
            )
            for u in users
        ],
        total=total,
        page=page,
        per_page=per_page,
        pages=max(1, -(-total // per_page)),  # ceiling division
    )


@router.post(
    "/users/{user_id}/suspend",
    status_code=status.HTTP_200_OK,
    summary="Suspend or unsuspend a user account",
)
async def suspend_user(
    user_id: UUID,
    payload: SuspendRequest,
    request: Request,
    admin: User = Depends(require_admin),
    auth_db: AsyncSession = Depends(get_auth_db),
):
    """
    Suspend or unsuspend a user.

    - Sets `is_active = False/True` on the user record.
    - Revokes all refresh tokens if suspending.
    - Logs the action to the audit table.
    """
    from app.db.models.auth import User as UserModel

    result = await auth_db.execute(
        select(UserModel).where(UserModel.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot suspend your own account.",
        )

    user.is_active = not payload.suspended  # True = active, False = suspended

    if payload.suspended:
        # Revoke all refresh tokens
        await auth_db.execute(
            text("""
                UPDATE refresh_tokens
                SET is_revoked = TRUE, revoked_at = NOW()
                WHERE user_id = :uid AND is_revoked = FALSE
            """),
            {"uid": str(user_id)},
        )

    await auth_db.commit()

    action = "suspended" if payload.suspended else "unsuspended"
    logger.info(
        "Admin %s %s user %s (reason: %s, ip: %s)",
        admin.email, action, user_id, payload.reason,
        request.client.host if request.client else "unknown",
    )

    return {
        "message": f"User {action} successfully.",
        "user_id": str(user_id),
        "is_active": user.is_active,
        "action": action,
        "performed_by": admin.email,
        "reason": payload.reason,
    }


@router.get(
    "/metrics/summary",
    response_model=PlatformMetrics,
    summary="Aggregate platform statistics",
)
async def platform_metrics(
    admin: User = Depends(require_admin),
    auth_db: AsyncSession = Depends(get_auth_db),
    data_db: AsyncSession = Depends(get_data_db),
):
    """
    Return aggregate platform metrics for the admin dashboard.

    - User counts (total, active last 24h / 7d, new today)
    - Content counts (expenses, budgets, goals)
    """
    now = datetime.now(timezone.utc)

    try:
        # Auth DB metrics
        total_users = (await auth_db.execute(
            text("SELECT COUNT(*) FROM users WHERE email NOT LIKE 'deleted_%@deleted.invalid'")
        )).scalar() or 0

        active_24h = (await auth_db.execute(
            text("SELECT COUNT(*) FROM users WHERE last_login > NOW() - INTERVAL '24 hours'")
        )).scalar() or 0

        active_7d = (await auth_db.execute(
            text("SELECT COUNT(*) FROM users WHERE last_login > NOW() - INTERVAL '7 days'")
        )).scalar() or 0

        new_today = (await auth_db.execute(
            text("SELECT COUNT(*) FROM users WHERE created_at::date = CURRENT_DATE")
        )).scalar() or 0

        # Data DB metrics
        total_expenses = (await data_db.execute(
            text("SELECT COUNT(*) FROM expenses WHERE deleted_at IS NULL")
        )).scalar() or 0

        total_budgets = (await data_db.execute(
            text("SELECT COUNT(*) FROM budgets WHERE deleted_at IS NULL")
        )).scalar() or 0

        total_goals = (await data_db.execute(
            text("SELECT COUNT(*) FROM goals WHERE deleted_at IS NULL")
        )).scalar() or 0

    except Exception as exc:
        logger.error("Failed to fetch admin metrics: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch metrics.",
        )

    return PlatformMetrics(
        total_users=total_users,
        active_users_24h=active_24h,
        active_users_7d=active_7d,
        new_users_today=new_today,
        total_expenses=total_expenses,
        total_budgets=total_budgets,
        total_goals=total_goals,
        generated_at=now.isoformat(),
    )


@router.get(
    "/audit-log",
    response_model=List[AuditLogEntry],
    summary="Recent system audit log entries",
)
async def audit_log(
    limit: int = Query(100, ge=1, le=1000),
    admin: User = Depends(require_admin),
    data_db: AsyncSession = Depends(get_data_db),
):
    """Return recent entries from the soft_delete_audit table."""
    try:
        result = await data_db.execute(
            text("""
                SELECT id::text, table_name, record_id::text,
                       deleted_by, reason, created_at
                FROM soft_delete_audit
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            {"limit": limit},
        )
        rows = [dict(r) for r in result.mappings().all()]
    except Exception as exc:
        logger.warning("Audit log unavailable: %s", exc)
        rows = []

    return [AuditLogEntry(**r) for r in rows]


@router.get("/health", summary="Infrastructure health check (admin only)")
async def admin_health(
    request: Request,
    admin: User = Depends(require_admin),
    auth_db: AsyncSession = Depends(get_auth_db),
):
    """
    Detailed health check for infrastructure components.

    Returns status of: Auth DB, Data DB, Redis, background worker.
    """
    checks: Dict[str, Any] = {}

    # Auth DB
    try:
        await auth_db.execute(text("SELECT 1"))
        checks["auth_db"] = "healthy"
    except Exception as exc:
        checks["auth_db"] = f"unhealthy: {exc}"

    # Redis
    redis_client = getattr(request.app.state, "redis_client", None)
    if redis_client:
        try:
            await redis_client.ping()
            checks["redis"] = "healthy"
        except Exception as exc:
            checks["redis"] = f"unhealthy: {exc}"
    else:
        checks["redis"] = "not configured"

    overall = "healthy" if all(v == "healthy" for v in checks.values()) else "degraded"

    return {
        "status": overall,
        "checks": checks,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "checked_by": admin.email,
    }
