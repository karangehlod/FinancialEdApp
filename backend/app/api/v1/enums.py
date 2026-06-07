"""API endpoints for providing enum values to frontend."""
from fastapi import APIRouter
from typing import Dict, List
from enum import Enum

from app.schemas.loan import LoanType, LoanStatus, PaymentStatus
from app.services.loan_domain import LoanStatusEnum, PaymentStatusEnum
from app.core.authorization import Permission, Role
from app.core.exceptions import ErrorCode
from app.api.v1.health import HealthStatus

router = APIRouter(prefix="/enums", tags=["enums"])


def enum_to_dict(enum_class: Enum) -> Dict[str, str]:
    """Convert an enum class to a dictionary of name->value mappings."""
    return {member.name: member.value for member in enum_class}


def enum_to_list(enum_class: Enum) -> List[Dict[str, str]]:
    """Convert an enum class to a list of dictionaries with name and value."""
    return [{"name": member.name, "value": member.value} for member in enum_class]


@router.get("/loan-types")
async def get_loan_types():
    """Get all available loan types."""
    return {
        "enum_name": "LoanType",
        "values": enum_to_dict(LoanType),
        "values_list": enum_to_list(LoanType)
    }


@router.get("/loan-statuses")
async def get_loan_statuses():
    """Get all available loan statuses."""
    return {
        "enum_name": "LoanStatus",
        "values": enum_to_dict(LoanStatus),
        "values_list": enum_to_list(LoanStatus)
    }


@router.get("/loan-statuses-domain")
async def get_loan_statuses_domain():
    """Get all available loan statuses from domain model."""
    return {
        "enum_name": "LoanStatusEnum",
        "values": enum_to_dict(LoanStatusEnum),
        "values_list": enum_to_list(LoanStatusEnum)
    }


@router.get("/payment-statuses")
async def get_payment_statuses():
    """Get all available payment statuses."""
    return {
        "enum_name": "PaymentStatus",
        "values": enum_to_dict(PaymentStatus),
        "values_list": enum_to_list(PaymentStatus)
    }


@router.get("/payment-statuses-domain")
async def get_payment_statuses_domain():
    """Get all available payment statuses from domain model."""
    return {
        "enum_name": "PaymentStatusEnum",
        "values": enum_to_dict(PaymentStatusEnum),
        "values_list": enum_to_list(PaymentStatusEnum)
    }


@router.get("/goal-types")
async def get_goal_types():
    """Get all available goal types."""
    return {
        "enum_name": "GoalType",
        "values": {
            "SAVINGS": "savings",
            "DEBT_PAYOFF": "debt_payoff",
            "INVESTMENT": "investment",
            "EMERGENCY_FUND": "emergency_fund",
            "OTHER": "other"
        },
        "values_list": [
            {"name": "SAVINGS", "value": "savings"},
            {"name": "DEBT_PAYOFF", "value": "debt_payoff"},
            {"name": "INVESTMENT", "value": "investment"},
            {"name": "EMERGENCY_FUND", "value": "emergency_fund"},
            {"name": "OTHER", "value": "other"}
        ]
    }


@router.get("/goal-priorities")
async def get_goal_priorities():
    """Get all available goal priorities."""
    return {
        "enum_name": "GoalPriority",
        "values": {
            "HIGH": "high",
            "MEDIUM": "medium",
            "LOW": "low"
        },
        "values_list": [
            {"name": "HIGH", "value": "high"},
            {"name": "MEDIUM", "value": "medium"},
            {"name": "LOW", "value": "low"}
        ]
    }


@router.get("/goal-statuses")
async def get_goal_statuses():
    """Get all available goal statuses."""
    return {
        "enum_name": "GoalStatus",
        "values": {
            "ACTIVE": "active",
            "COMPLETED": "completed",
            "PAUSED": "paused",
            "ABANDONED": "abandoned"
        },
        "values_list": [
            {"name": "ACTIVE", "value": "active"},
            {"name": "COMPLETED", "value": "completed"},
            {"name": "PAUSED", "value": "paused"},
            {"name": "ABANDONED", "value": "abandoned"}
        ]
    }


@router.get("/permissions")
async def get_permissions():
    """Get all available permissions."""
    return {
        "enum_name": "Permission",
        "values": enum_to_dict(Permission),
        "values_list": enum_to_list(Permission)
    }


@router.get("/roles")
async def get_roles():
    """Get all available user roles."""
    return {
        "enum_name": "Role",
        "values": enum_to_dict(Role),
        "values_list": enum_to_list(Role)
    }


@router.get("/error-codes")
async def get_error_codes():
    """Get all available error codes."""
    return {
        "enum_name": "ErrorCode",
        "values": enum_to_dict(ErrorCode),
        "values_list": enum_to_list(ErrorCode)
    }


@router.get("/health-statuses")
async def get_health_statuses():
    """Get all available health statuses."""
    return {
        "enum_name": "HealthStatus",
        "values": enum_to_dict(HealthStatus),
        "values_list": enum_to_list(HealthStatus)
    }


@router.get("/all")
async def get_all_enums():
    """Get all enums in a single response."""
    return {
        "loan_types": enum_to_dict(LoanType),
        "loan_statuses": enum_to_dict(LoanStatus),
        "loan_statuses_domain": enum_to_dict(LoanStatusEnum),
        "payment_statuses": enum_to_dict(PaymentStatus),
        "payment_statuses_domain": enum_to_dict(PaymentStatusEnum),
        "goal_types": {
            "SAVINGS": "savings",
            "DEBT_PAYOFF": "debt_payoff",
            "INVESTMENT": "investment",
            "EMERGENCY_FUND": "emergency_fund",
            "OTHER": "other"
        },
        "goal_priorities": {
            "HIGH": "high",
            "MEDIUM": "medium",
            "LOW": "low"
        },
        "goal_statuses": {
            "ACTIVE": "active",
            "COMPLETED": "completed",
            "PAUSED": "paused",
            "ABANDONED": "abandoned"
        },
        "permissions": enum_to_dict(Permission),
        "roles": enum_to_dict(Role),
        "error_codes": enum_to_dict(ErrorCode),
        "health_statuses": enum_to_dict(HealthStatus)
    }
