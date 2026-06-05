"""Custom exceptions for the application with error codes and details."""

from typing import Optional, Dict, Any
from enum import Enum


class ErrorCode(str, Enum):
    """Standard error codes for API responses."""

    # Authentication errors (AUTH_*)
    AUTH_INVALID_CREDENTIALS = "AUTH_001"
    AUTH_TOKEN_EXPIRED = "AUTH_002"
    AUTH_TOKEN_INVALID = "AUTH_003"
    AUTH_MISSING_TOKEN = "AUTH_004"
    AUTH_INSUFFICIENT_PERMISSIONS = "AUTH_005"

    # User errors (USER_*)
    USER_NOT_FOUND = "USER_001"
    USER_ALREADY_EXISTS = "USER_002"
    USER_INACTIVE = "USER_003"
    USER_EMAIL_TAKEN = "USER_004"
    USER_INVALID_PASSWORD = "USER_005"

    # Validation errors (VAL_*)
    VAL_INVALID_INPUT = "VAL_001"
    VAL_MISSING_FIELD = "VAL_002"
    VAL_INVALID_FORMAT = "VAL_003"
    VAL_INVALID_RANGE = "VAL_004"
    VAL_CONSTRAINT_VIOLATION = "VAL_005"

    # Budget errors (BDG_*)
    BDG_NOT_FOUND = "BDG_001"
    BDG_DUPLICATE_CATEGORY = "BDG_002"
    BDG_INVALID_AMOUNT = "BDG_003"
    BDG_MONTH_MISMATCH = "BDG_004"

    # Expense errors (EXP_*)
    EXP_NOT_FOUND = "EXP_001"
    EXP_INVALID_AMOUNT = "EXP_002"
    EXP_INVALID_DATE = "EXP_003"
    EXP_PERMISSION_DENIED = "EXP_004"

    # Loan errors (LN_*)
    LN_NOT_FOUND = "LN_001"
    LN_INVALID_TERM = "LN_002"
    LN_INVALID_RATE = "LN_003"
    LN_PAYMENT_FAILED = "LN_004"
    LN_ALREADY_CLOSED = "LN_005"

    # Database errors (DB_*)
    DB_CONNECTION_ERROR = "DB_001"
    DB_QUERY_ERROR = "DB_002"
    DB_TRANSACTION_ERROR = "DB_003"
    DB_INTEGRITY_ERROR = "DB_004"

    # Server errors (SRV_*)
    SRV_INTERNAL_ERROR = "SRV_001"
    SRV_EXTERNAL_SERVICE_ERROR = "SRV_002"
    SRV_RATE_LIMIT_EXCEEDED = "SRV_003"


class AppException(Exception):
    """
    Base application exception with error code and details.

    Attributes:
        error_code: Unique error code for the exception
        message: User-friendly error message
        status_code: HTTP status code
        details: Additional error details
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: ErrorCode = ErrorCode.SRV_INTERNAL_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response."""
        return {
            "error_code": self.error_code.value,
            "message": self.message,
            "details": self.details,
        }


class AuthenticationError(AppException):
    """Authentication related errors."""

    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: ErrorCode = ErrorCode.AUTH_INVALID_CREDENTIALS,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message, status_code=401, error_code=error_code, details=details
        )


class AuthorizationError(AppException):
    """Authorization related errors."""

    def __init__(
        self,
        message: str = "Access denied",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message,
            status_code=403,
            error_code=ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS,
            details=details,
        )


class UserAlreadyExistsError(AppException):
    """User already exists error."""

    def __init__(
        self,
        message: str = "User already exists",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message,
            status_code=400,
            error_code=ErrorCode.USER_ALREADY_EXISTS,
            details=details,
        )


class UserNotFoundError(AppException):
    """User not found error."""

    def __init__(
        self,
        message: str = "User not found",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message,
            status_code=404,
            error_code=ErrorCode.USER_NOT_FOUND,
            details=details,
        )


class ValidationError(AppException):
    """Validation error."""

    def __init__(
        self,
        message: str = "Validation failed",
        error_code: ErrorCode = ErrorCode.VAL_INVALID_INPUT,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message, status_code=422, error_code=error_code, details=details
        )


class DatabaseError(AppException):
    """Database related errors."""

    def __init__(
        self,
        message: str = "Database error occurred",
        error_code: ErrorCode = ErrorCode.DB_QUERY_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message, status_code=500, error_code=error_code, details=details
        )


class BusinessLogicError(AppException):
    """Business logic related errors."""

    def __init__(
        self,
        message: str = "Business logic error",
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, status_code=status_code, details=details)


class ResourceNotFoundError(AppException):
    """Resource not found error."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"{resource_type} with id '{resource_id}' not found"
        super().__init__(
            message,
            status_code=404,
            error_code=ErrorCode.SRV_INTERNAL_ERROR,
            details=details,
        )


class InvalidInputError(AppException):
    """Invalid input error."""

    def __init__(
        self,
        field: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"Invalid value for '{field}': {reason}"
        if details is None:
            details = {"field": field, "reason": reason}
        super().__init__(
            message,
            status_code=422,
            error_code=ErrorCode.VAL_INVALID_INPUT,
            details=details,
        )


# ============================================================================
# DOMAIN-SPECIFIC EXCEPTIONS (Budget, Expense, Loan, Goal)
# ============================================================================


class BudgetNotFoundError(AppException):
    """Budget not found error."""

    def __init__(
        self,
        budget_id: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"Budget with id '{budget_id}' not found"
        super().__init__(
            message,
            status_code=404,
            error_code=ErrorCode.BDG_NOT_FOUND,
            details=details or {"budget_id": budget_id},
        )


class DuplicateBudgetError(AppException):
    """Duplicate budget for same category in same month error."""

    def __init__(
        self,
        category: str,
        month: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"Budget for category '{category}' already exists for {month}"
        super().__init__(
            message,
            status_code=400,
            error_code=ErrorCode.BDG_DUPLICATE_CATEGORY,
            details=details or {"category": category, "month": month},
        )


class InvalidBudgetAmountError(AppException):
    """Invalid budget amount error."""

    def __init__(
        self,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"Invalid budget amount: {reason}"
        super().__init__(
            message,
            status_code=422,
            error_code=ErrorCode.BDG_INVALID_AMOUNT,
            details=details or {"reason": reason},
        )


class ExpenseNotFoundError(AppException):
    """Expense not found error."""

    def __init__(
        self,
        expense_id: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"Expense with id '{expense_id}' not found"
        super().__init__(
            message,
            status_code=404,
            error_code=ErrorCode.EXP_NOT_FOUND,
            details=details or {"expense_id": expense_id},
        )


class InvalidExpenseAmountError(AppException):
    """Invalid expense amount error."""

    def __init__(
        self,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"Invalid expense amount: {reason}"
        super().__init__(
            message,
            status_code=422,
            error_code=ErrorCode.EXP_INVALID_AMOUNT,
            details=details or {"reason": reason},
        )


class InvalidExpenseDateError(AppException):
    """Invalid expense date error."""

    def __init__(
        self,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"Invalid expense date: {reason}"
        super().__init__(
            message,
            status_code=422,
            error_code=ErrorCode.EXP_INVALID_DATE,
            details=details or {"reason": reason},
        )


class ExpenseAccessDeniedError(AppException):
    """User doesn't have permission to access/modify the expense."""

    def __init__(
        self,
        expense_id: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"You don't have permission to access expense '{expense_id}'"
        super().__init__(
            message,
            status_code=403,
            error_code=ErrorCode.EXP_PERMISSION_DENIED,
            details=details or {"expense_id": expense_id},
        )


class LoanNotFoundError(AppException):
    """Loan not found error."""

    def __init__(
        self,
        loan_id: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"Loan with id '{loan_id}' not found"
        super().__init__(
            message,
            status_code=404,
            error_code=ErrorCode.LN_NOT_FOUND,
            details=details or {"loan_id": loan_id},
        )


class InvalidLoanTermError(AppException):
    """Invalid loan term error."""

    def __init__(
        self,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"Invalid loan term: {reason}"
        super().__init__(
            message,
            status_code=422,
            error_code=ErrorCode.LN_INVALID_TERM,
            details=details or {"reason": reason},
        )


class InvalidLoanRateError(AppException):
    """Invalid loan interest rate error."""

    def __init__(
        self,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"Invalid interest rate: {reason}"
        super().__init__(
            message,
            status_code=422,
            error_code=ErrorCode.LN_INVALID_RATE,
            details=details or {"reason": reason},
        )


class LoanPaymentFailedError(AppException):
    """Loan payment processing failed error."""

    def __init__(
        self,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"Loan payment failed: {reason}"
        super().__init__(
            message,
            status_code=400,
            error_code=ErrorCode.LN_PAYMENT_FAILED,
            details=details or {"reason": reason},
        )


class LoanAlreadyClosedError(AppException):
    """Loan is already closed error."""

    def __init__(
        self,
        loan_id: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"Loan '{loan_id}' is already closed and cannot be modified"
        super().__init__(
            message,
            status_code=400,
            error_code=ErrorCode.LN_ALREADY_CLOSED,
            details=details or {"loan_id": loan_id},
        )


class GoalNotFoundError(AppException):
    """Goal not found error."""

    def __init__(
        self,
        goal_id: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"Goal '{goal_id}' not found"
        super().__init__(
            message,
            status_code=404,
            error_code="GOAL_001",
            details=details or {"goal_id": goal_id},
        )


class InvalidGoalAmountError(AppException):
    """Invalid goal amount error."""

    def __init__(
        self,
        reason: str = "Amount must be positive",
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"Invalid goal amount: {reason}"
        super().__init__(
            message,
            status_code=400,
            error_code="GOAL_002",
            details=details or {"reason": reason},
        )


class InvalidGoalDateError(AppException):
    """Invalid goal date error."""

    def __init__(
        self,
        reason: str = "Date is invalid",
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"Invalid goal date: {reason}"
        super().__init__(
            message,
            status_code=400,
            error_code="GOAL_003",
            details=details or {"reason": reason},
        )