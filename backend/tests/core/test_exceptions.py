"""Unit tests for app.core.exceptions module."""

import pytest
from app.core.exceptions import (
    ErrorCode,
    AppException,
    AuthenticationError,
    AuthorizationError,
    UserAlreadyExistsError,
    UserNotFoundError,
    ValidationError,
    DatabaseError,
    BusinessLogicError,
    ResourceNotFoundError,
    InvalidInputError,
    BudgetNotFoundError,
    DuplicateBudgetError,
    InvalidBudgetAmountError,
    ExpenseNotFoundError,
    InvalidExpenseAmountError,
    InvalidExpenseDateError,
    ExpenseAccessDeniedError,
    LoanNotFoundError,
    InvalidLoanTermError,
    InvalidLoanRateError,
    LoanPaymentFailedError,
    LoanAlreadyClosedError,
    GoalNotFoundError,
    InvalidGoalAmountError,
    InvalidGoalDateError,
)


class TestErrorCode:
    """Test ErrorCode enum."""

    def test_auth_error_codes_exist(self):
        assert ErrorCode.AUTH_INVALID_CREDENTIALS.value == "AUTH_001"
        assert ErrorCode.AUTH_TOKEN_EXPIRED.value == "AUTH_002"
        assert ErrorCode.AUTH_TOKEN_INVALID.value == "AUTH_003"
        assert ErrorCode.AUTH_MISSING_TOKEN.value == "AUTH_004"
        assert ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS.value == "AUTH_005"

    def test_user_error_codes_exist(self):
        assert ErrorCode.USER_NOT_FOUND.value == "USER_001"
        assert ErrorCode.USER_ALREADY_EXISTS.value == "USER_002"
        assert ErrorCode.USER_INACTIVE.value == "USER_003"
        assert ErrorCode.USER_EMAIL_TAKEN.value == "USER_004"
        assert ErrorCode.USER_INVALID_PASSWORD.value == "USER_005"

    def test_validation_error_codes_exist(self):
        assert ErrorCode.VAL_INVALID_INPUT.value == "VAL_001"
        assert ErrorCode.VAL_MISSING_FIELD.value == "VAL_002"
        assert ErrorCode.VAL_INVALID_FORMAT.value == "VAL_003"
        assert ErrorCode.VAL_INVALID_RANGE.value == "VAL_004"
        assert ErrorCode.VAL_CONSTRAINT_VIOLATION.value == "VAL_005"

    def test_budget_error_codes_exist(self):
        assert ErrorCode.BDG_NOT_FOUND.value == "BDG_001"
        assert ErrorCode.BDG_DUPLICATE_CATEGORY.value == "BDG_002"
        assert ErrorCode.BDG_INVALID_AMOUNT.value == "BDG_003"
        assert ErrorCode.BDG_MONTH_MISMATCH.value == "BDG_004"

    def test_expense_error_codes_exist(self):
        assert ErrorCode.EXP_NOT_FOUND.value == "EXP_001"
        assert ErrorCode.EXP_INVALID_AMOUNT.value == "EXP_002"
        assert ErrorCode.EXP_INVALID_DATE.value == "EXP_003"
        assert ErrorCode.EXP_PERMISSION_DENIED.value == "EXP_004"

    def test_loan_error_codes_exist(self):
        assert ErrorCode.LN_NOT_FOUND.value == "LN_001"
        assert ErrorCode.LN_INVALID_TERM.value == "LN_002"
        assert ErrorCode.LN_INVALID_RATE.value == "LN_003"
        assert ErrorCode.LN_PAYMENT_FAILED.value == "LN_004"
        assert ErrorCode.LN_ALREADY_CLOSED.value == "LN_005"

    def test_database_error_codes_exist(self):
        assert ErrorCode.DB_CONNECTION_ERROR.value == "DB_001"
        assert ErrorCode.DB_QUERY_ERROR.value == "DB_002"
        assert ErrorCode.DB_TRANSACTION_ERROR.value == "DB_003"
        assert ErrorCode.DB_INTEGRITY_ERROR.value == "DB_004"

    def test_server_error_codes_exist(self):
        assert ErrorCode.SRV_INTERNAL_ERROR.value == "SRV_001"
        assert ErrorCode.SRV_EXTERNAL_SERVICE_ERROR.value == "SRV_002"
        assert ErrorCode.SRV_RATE_LIMIT_EXCEEDED.value == "SRV_003"


class TestAppException:
    """Test base AppException class."""

    def test_app_exception_with_defaults(self):
        exc = AppException("Test error")
        assert exc.message == "Test error"
        assert exc.status_code == 500
        assert exc.error_code == ErrorCode.SRV_INTERNAL_ERROR
        assert exc.details == {}

    def test_app_exception_with_custom_status_code(self):
        exc = AppException("Test error", status_code=404)
        assert exc.status_code == 404

    def test_app_exception_with_custom_error_code(self):
        exc = AppException("Test error", error_code=ErrorCode.USER_NOT_FOUND)
        assert exc.error_code == ErrorCode.USER_NOT_FOUND

    def test_app_exception_with_details(self):
        details = {"field": "email", "reason": "invalid format"}
        exc = AppException("Test error", details=details)
        assert exc.details == details

    def test_app_exception_to_dict(self):
        details = {"field": "email"}
        exc = AppException(
            "Test error",
            status_code=400,
            error_code=ErrorCode.VAL_INVALID_INPUT,
            details=details,
        )
        result = exc.to_dict()
        assert result["error_code"] == "VAL_001"
        assert result["message"] == "Test error"
        assert result["details"] == details

    def test_app_exception_inherits_from_exception(self):
        exc = AppException("Test error")
        assert isinstance(exc, Exception)

    def test_app_exception_preserves_details_none_to_empty_dict(self):
        exc = AppException("Test error", details=None)
        assert exc.details == {}


class TestAuthenticationError:
    """Test AuthenticationError."""

    def test_authentication_error_defaults(self):
        exc = AuthenticationError()
        assert exc.message == "Authentication failed"
        assert exc.status_code == 401
        assert exc.error_code == ErrorCode.AUTH_INVALID_CREDENTIALS

    def test_authentication_error_custom_message(self):
        exc = AuthenticationError("Invalid token")
        assert exc.message == "Invalid token"

    def test_authentication_error_custom_error_code(self):
        exc = AuthenticationError(
            "Token expired", error_code=ErrorCode.AUTH_TOKEN_EXPIRED
        )
        assert exc.error_code == ErrorCode.AUTH_TOKEN_EXPIRED

    def test_authentication_error_with_details(self):
        details = {"token": "expired"}
        exc = AuthenticationError(details=details)
        assert exc.details == details


class TestAuthorizationError:
    """Test AuthorizationError."""

    def test_authorization_error_defaults(self):
        exc = AuthorizationError()
        assert exc.message == "Access denied"
        assert exc.status_code == 403
        assert exc.error_code == ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS

    def test_authorization_error_custom_message(self):
        exc = AuthorizationError("Admin access required")
        assert exc.message == "Admin access required"

    def test_authorization_error_with_details(self):
        details = {"required_role": "admin"}
        exc = AuthorizationError(details=details)
        assert exc.details == details


class TestUserAlreadyExistsError:
    """Test UserAlreadyExistsError."""

    def test_user_already_exists_error_defaults(self):
        exc = UserAlreadyExistsError()
        assert exc.message == "User already exists"
        assert exc.status_code == 400
        assert exc.error_code == ErrorCode.USER_ALREADY_EXISTS

    def test_user_already_exists_error_custom_message(self):
        exc = UserAlreadyExistsError("Email already registered")
        assert exc.message == "Email already registered"

    def test_user_already_exists_error_with_details(self):
        details = {"email": "test@example.com"}
        exc = UserAlreadyExistsError(details=details)
        assert exc.details == details


class TestUserNotFoundError:
    """Test UserNotFoundError."""

    def test_user_not_found_error_defaults(self):
        exc = UserNotFoundError()
        assert exc.message == "User not found"
        assert exc.status_code == 404
        assert exc.error_code == ErrorCode.USER_NOT_FOUND

    def test_user_not_found_error_custom_message(self):
        exc = UserNotFoundError("User with ID 123 not found")
        assert exc.message == "User with ID 123 not found"


class TestValidationError:
    """Test ValidationError."""

    def test_validation_error_defaults(self):
        exc = ValidationError()
        assert exc.message == "Validation failed"
        assert exc.status_code == 422
        assert exc.error_code == ErrorCode.VAL_INVALID_INPUT

    def test_validation_error_custom_message(self):
        exc = ValidationError("Email format invalid")
        assert exc.message == "Email format invalid"

    def test_validation_error_custom_error_code(self):
        exc = ValidationError(
            "Field missing", error_code=ErrorCode.VAL_MISSING_FIELD
        )
        assert exc.error_code == ErrorCode.VAL_MISSING_FIELD


class TestDatabaseError:
    """Test DatabaseError."""

    def test_database_error_defaults(self):
        exc = DatabaseError()
        assert exc.message == "Database error occurred"
        assert exc.status_code == 500
        assert exc.error_code == ErrorCode.DB_QUERY_ERROR

    def test_database_error_custom_message(self):
        exc = DatabaseError("Connection timeout")
        assert exc.message == "Connection timeout"

    def test_database_error_custom_error_code(self):
        exc = DatabaseError(
            "Connection failed", error_code=ErrorCode.DB_CONNECTION_ERROR
        )
        assert exc.error_code == ErrorCode.DB_CONNECTION_ERROR


class TestBusinessLogicError:
    """Test BusinessLogicError."""

    def test_business_logic_error_defaults(self):
        exc = BusinessLogicError()
        assert exc.message == "Business logic error"
        assert exc.status_code == 400

    def test_business_logic_error_custom_status_code(self):
        exc = BusinessLogicError("Logic error", status_code=409)
        assert exc.status_code == 409

    def test_business_logic_error_with_details(self):
        details = {"conflict": "data"}
        exc = BusinessLogicError("Conflict", details=details)
        assert exc.details == details


class TestResourceNotFoundError:
    """Test ResourceNotFoundError."""

    def test_resource_not_found_error_formats_message(self):
        exc = ResourceNotFoundError("Budget", "123")
        assert exc.message == "Budget with id '123' not found"
        assert exc.status_code == 404
        assert exc.details == {}

    def test_resource_not_found_error_with_details(self):
        details = {"custom": "data"}
        exc = ResourceNotFoundError("Expense", "456", details=details)
        assert exc.details == details


class TestInvalidInputError:
    """Test InvalidInputError."""

    def test_invalid_input_error_formats_message(self):
        exc = InvalidInputError("email", "must be valid email")
        assert exc.message == "Invalid value for 'email': must be valid email"
        assert exc.status_code == 422
        assert exc.error_code == ErrorCode.VAL_INVALID_INPUT

    def test_invalid_input_error_auto_sets_details(self):
        exc = InvalidInputError("amount", "must be positive")
        assert exc.details["field"] == "amount"
        assert exc.details["reason"] == "must be positive"

    def test_invalid_input_error_custom_details_override(self):
        custom_details = {"custom": "value"}
        exc = InvalidInputError("field", "reason", details=custom_details)
        assert exc.details == custom_details


class TestBudgetNotFoundError:
    """Test BudgetNotFoundError."""

    def test_budget_not_found_error_formats_message(self):
        exc = BudgetNotFoundError("budget-123")
        assert exc.message == "Budget with id 'budget-123' not found"
        assert exc.status_code == 404
        assert exc.error_code == ErrorCode.BDG_NOT_FOUND

    def test_budget_not_found_error_auto_sets_details(self):
        exc = BudgetNotFoundError("budget-456")
        assert exc.details == {"budget_id": "budget-456"}

    def test_budget_not_found_error_custom_details(self):
        custom_details = {"extra": "info"}
        exc = BudgetNotFoundError("budget-789", details=custom_details)
        assert exc.details == custom_details


class TestDuplicateBudgetError:
    """Test DuplicateBudgetError."""

    def test_duplicate_budget_error_formats_message(self):
        exc = DuplicateBudgetError("groceries", "2025-01")
        assert exc.message == "Budget for category 'groceries' already exists for 2025-01"
        assert exc.status_code == 400
        assert exc.error_code == ErrorCode.BDG_DUPLICATE_CATEGORY

    def test_duplicate_budget_error_auto_sets_details(self):
        exc = DuplicateBudgetError("utilities", "2025-02")
        assert exc.details == {"category": "utilities", "month": "2025-02"}


class TestInvalidBudgetAmountError:
    """Test InvalidBudgetAmountError."""

    def test_invalid_budget_amount_error_formats_message(self):
        exc = InvalidBudgetAmountError("must be greater than zero")
        assert exc.message == "Invalid budget amount: must be greater than zero"
        assert exc.status_code == 422
        assert exc.error_code == ErrorCode.BDG_INVALID_AMOUNT

    def test_invalid_budget_amount_error_auto_sets_details(self):
        exc = InvalidBudgetAmountError("negative value")
        assert exc.details == {"reason": "negative value"}


class TestExpenseNotFoundError:
    """Test ExpenseNotFoundError."""

    def test_expense_not_found_error_formats_message(self):
        exc = ExpenseNotFoundError("exp-123")
        assert exc.message == "Expense with id 'exp-123' not found"
        assert exc.status_code == 404
        assert exc.error_code == ErrorCode.EXP_NOT_FOUND

    def test_expense_not_found_error_auto_sets_details(self):
        exc = ExpenseNotFoundError("exp-456")
        assert exc.details == {"expense_id": "exp-456"}


class TestInvalidExpenseAmountError:
    """Test InvalidExpenseAmountError."""

    def test_invalid_expense_amount_error_formats_message(self):
        exc = InvalidExpenseAmountError("amount cannot be negative")
        assert exc.message == "Invalid expense amount: amount cannot be negative"
        assert exc.status_code == 422
        assert exc.error_code == ErrorCode.EXP_INVALID_AMOUNT


class TestInvalidExpenseDateError:
    """Test InvalidExpenseDateError."""

    def test_invalid_expense_date_error_formats_message(self):
        exc = InvalidExpenseDateError("date cannot be in future")
        assert exc.message == "Invalid expense date: date cannot be in future"
        assert exc.status_code == 422
        assert exc.error_code == ErrorCode.EXP_INVALID_DATE


class TestExpenseAccessDeniedError:
    """Test ExpenseAccessDeniedError."""

    def test_expense_access_denied_error_formats_message(self):
        exc = ExpenseAccessDeniedError("exp-999")
        assert exc.message == "You don't have permission to access expense 'exp-999'"
        assert exc.status_code == 403
        assert exc.error_code == ErrorCode.EXP_PERMISSION_DENIED

    def test_expense_access_denied_error_auto_sets_details(self):
        exc = ExpenseAccessDeniedError("exp-111")
        assert exc.details == {"expense_id": "exp-111"}


class TestLoanNotFoundError:
    """Test LoanNotFoundError."""

    def test_loan_not_found_error_formats_message(self):
        exc = LoanNotFoundError("loan-123")
        assert exc.message == "Loan with id 'loan-123' not found"
        assert exc.status_code == 404
        assert exc.error_code == ErrorCode.LN_NOT_FOUND


class TestInvalidLoanTermError:
    """Test InvalidLoanTermError."""

    def test_invalid_loan_term_error_formats_message(self):
        exc = InvalidLoanTermError("term must be positive")
        assert exc.message == "Invalid loan term: term must be positive"
        assert exc.status_code == 422
        assert exc.error_code == ErrorCode.LN_INVALID_TERM


class TestInvalidLoanRateError:
    """Test InvalidLoanRateError."""

    def test_invalid_loan_rate_error_formats_message(self):
        exc = InvalidLoanRateError("rate must be between 0 and 100")
        assert exc.message == "Invalid interest rate: rate must be between 0 and 100"
        assert exc.status_code == 422
        assert exc.error_code == ErrorCode.LN_INVALID_RATE


class TestLoanPaymentFailedError:
    """Test LoanPaymentFailedError."""

    def test_loan_payment_failed_error_formats_message(self):
        exc = LoanPaymentFailedError("insufficient funds")
        assert exc.message == "Loan payment failed: insufficient funds"
        assert exc.status_code == 400
        assert exc.error_code == ErrorCode.LN_PAYMENT_FAILED


class TestLoanAlreadyClosedError:
    """Test LoanAlreadyClosedError."""

    def test_loan_already_closed_error_formats_message(self):
        exc = LoanAlreadyClosedError("loan-777")
        assert exc.message == "Loan 'loan-777' is already closed and cannot be modified"
        assert exc.status_code == 400
        assert exc.error_code == ErrorCode.LN_ALREADY_CLOSED

    def test_loan_already_closed_error_auto_sets_details(self):
        exc = LoanAlreadyClosedError("loan-888")
        assert exc.details == {"loan_id": "loan-888"}


class TestGoalNotFoundError:
    """Test GoalNotFoundError."""

    def test_goal_not_found_error_formats_message(self):
        exc = GoalNotFoundError("goal-123")
        assert exc.message == "Goal 'goal-123' not found"
        assert exc.status_code == 404
        assert exc.error_code == "GOAL_001"


class TestInvalidGoalAmountError:
    """Test InvalidGoalAmountError."""

    def test_invalid_goal_amount_error_default_message(self):
        exc = InvalidGoalAmountError()
        assert exc.message == "Invalid goal amount: Amount must be positive"
        assert exc.status_code == 400
        assert exc.error_code == "GOAL_002"

    def test_invalid_goal_amount_error_custom_reason(self):
        exc = InvalidGoalAmountError("amount too high")
        assert exc.message == "Invalid goal amount: amount too high"


class TestInvalidGoalDateError:
    """Test InvalidGoalDateError."""

    def test_invalid_goal_date_error_default_message(self):
        exc = InvalidGoalDateError()
        assert exc.message == "Invalid goal date: Date is invalid"
        assert exc.status_code == 400
        assert exc.error_code == "GOAL_003"

    def test_invalid_goal_date_error_custom_reason(self):
        exc = InvalidGoalDateError("date in past")
        assert exc.message == "Invalid goal date: date in past"
