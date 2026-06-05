"""
Input validation and sanitization decorators for endpoints - DRY compliance.

Provides:
- Automatic request validation decorators
- Sanitization decorators for common fields
- Input size limiting
- XSS prevention
- Injection attack prevention

Usage:
    @validate_expense_input
    @sanitize_request_fields(['description', 'merchant'])
    async def create_expense(user_id: UUID, expense_data: ExpenseCreate):
        ...
"""

from functools import wraps
from typing import Callable, List, Type, Optional, Any
import logging
from decimal import Decimal
from datetime import date

from fastapi import HTTPException, status
from pydantic import BaseModel, ValidationError

from app.core.sanitization import (
    sanitize_text,
    sanitize_merchant,
    sanitize_name,
    sanitize_notes
)
from app.core.logging import get_logger
from app.core.exceptions import (
    InvalidInputError,
    InvalidExpenseAmountError,
    InvalidBudgetAmountError,
)

logger = get_logger(__name__)


# ============================================================================
# Field Sanitization Decorator
# ============================================================================

def sanitize_request_fields(fields: List[str], sanitizer_type: str = "text"):
    """
    Decorator to automatically sanitize specified fields in request data.

    Supported sanitizer types:
    - 'text': General HTML/XSS stripping
    - 'merchant': Strict merchant name sanitization
    - 'name': Display name sanitization
    - 'notes': Longer notes/description sanitization

    Args:
        fields: List of field names to sanitize
        sanitizer_type: Type of sanitization to apply

    Usage:
        @sanitize_request_fields(['description', 'merchant'], sanitizer_type='merchant')
        async def create_expense(expense_data: ExpenseCreate):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find the request data object (typically first non-self argument that's a BaseModel)
            data_obj = None
            for arg in args:
                if isinstance(arg, BaseModel):
                    data_obj = arg
                    break

            if not data_obj:
                for kwarg in kwargs.values():
                    if isinstance(kwarg, BaseModel):
                        data_obj = kwarg
                        break

            # Apply sanitization if data object found
            if data_obj:
                sanitizers = {
                    'text': sanitize_text,
                    'merchant': sanitize_merchant,
                    'name': sanitize_name,
                    'notes': sanitize_notes,
                }
                sanitizer = sanitizers.get(sanitizer_type, sanitize_text)

                for field in fields:
                    if hasattr(data_obj, field):
                        value = getattr(data_obj, field)
                        if isinstance(value, str):
                            try:
                                sanitized = sanitizer(value)
                                setattr(data_obj, field, sanitized)
                                logger.debug(f"Sanitized field '{field}'")
                            except Exception as exc:
                                logger.warning(f"Sanitization of field '{field}' failed: {exc}")

            return await func(*args, **kwargs)

        return wrapper
    return decorator


# ============================================================================
# Amount Validation Decorators
# ============================================================================

def validate_expense_input(func: Callable) -> Callable:
    """Decorator to validate expense-specific inputs."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract expense data from kwargs
        expense_data = kwargs.get('expense_data')

        if expense_data and isinstance(expense_data, BaseModel):
            # Validate amount
            if hasattr(expense_data, 'amount'):
                amount = expense_data.amount
                if not isinstance(amount, Decimal):
                    amount = Decimal(str(amount))

                if amount <= 0:
                    raise InvalidExpenseAmountError("Expense amount must be greater than 0")
                if amount > Decimal('999999.99'):
                    raise InvalidExpenseAmountError("Expense amount cannot exceed 999,999.99")

            # Validate date
            if hasattr(expense_data, 'date') and expense_data.date is not None:
                if expense_data.date > date.today():
                    raise InvalidExpenseAmountError("Expense date cannot be in the future")

            # Sanitize description
            if hasattr(expense_data, 'description') and isinstance(expense_data.description, str):
                expense_data.description = sanitize_text(expense_data.description, max_length=500)

        return await func(*args, **kwargs)

    return wrapper


def validate_budget_input(func: Callable) -> Callable:
    """Decorator to validate budget-specific inputs."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract budget data from kwargs
        budget_data = kwargs.get('budget_data')

        if budget_data and isinstance(budget_data, BaseModel):
            # Validate allocated amount
            if hasattr(budget_data, 'allocated_amount'):
                amount = budget_data.allocated_amount
                if not isinstance(amount, Decimal):
                    amount = Decimal(str(amount))

                if amount <= 0:
                    raise InvalidBudgetAmountError("Budget amount must be greater than 0")
                if amount > Decimal('999999.99'):
                    raise InvalidBudgetAmountError("Budget amount cannot exceed 999,999.99")

            # Sanitize description
            if hasattr(budget_data, 'description') and isinstance(budget_data.description, str):
                budget_data.description = sanitize_text(budget_data.description, max_length=500)

        return await func(*args, **kwargs)

    return wrapper


def validate_loan_input(func: Callable) -> Callable:
    """Decorator to validate loan-specific inputs."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract loan data from kwargs
        loan_data = kwargs.get('loan_data')

        if loan_data and isinstance(loan_data, BaseModel):
            from app.services.loan_validators import (
                LoanAmountValidator,
                InterestRateValidator,
                LoanTermValidator,
            )

            # Validate principal amount
            if hasattr(loan_data, 'principal_amount'):
                is_valid, msg = LoanAmountValidator.validate(loan_data.principal_amount)
                if not is_valid:
                    raise InvalidInputError(msg)

            # Validate interest rate
            if hasattr(loan_data, 'interest_rate'):
                is_valid, msg = InterestRateValidator.validate(loan_data.interest_rate)
                if not is_valid:
                    raise InvalidInputError(msg)

            # Validate loan term
            if hasattr(loan_data, 'loan_term_months'):
                is_valid, msg = LoanTermValidator.validate(loan_data.loan_term_months)
                if not is_valid:
                    raise InvalidInputError(msg)

            # Sanitize description
            if hasattr(loan_data, 'description') and isinstance(loan_data.description, str):
                loan_data.description = sanitize_text(loan_data.description, max_length=500)

        return await func(*args, **kwargs)

    return wrapper


def validate_goal_input(func: Callable) -> Callable:
    """Decorator to validate goal-specific inputs."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract goal data from kwargs
        goal_data = kwargs.get('goal_data')

        if goal_data and isinstance(goal_data, BaseModel):
            # Validate target amount
            if hasattr(goal_data, 'target_amount'):
                amount = goal_data.target_amount
                if not isinstance(amount, Decimal):
                    amount = Decimal(str(amount))

                if amount <= 0:
                    raise InvalidInputError("Goal target amount must be greater than 0")
                if amount > Decimal('999999.99'):
                    raise InvalidInputError("Goal target amount cannot exceed 999,999.99")

            # Sanitize goal name and description
            if hasattr(goal_data, 'goal_name') and isinstance(goal_data.goal_name, str):
                goal_data.goal_name = sanitize_name(goal_data.goal_name)

            if hasattr(goal_data, 'description') and isinstance(goal_data.description, str):
                goal_data.description = sanitize_text(goal_data.description, max_length=500)

        return await func(*args, **kwargs)

    return wrapper


# ============================================================================
# Pydantic Validator Helpers (for use in schema definitions)
# ============================================================================

def validate_decimal_range(
    value: Any,
    min_val: Decimal = Decimal('0'),
    max_val: Decimal = Decimal('999999.99'),
    field_name: str = "value"
) -> Decimal:
    """Helper to validate decimal field in Pydantic validators."""
    if not isinstance(value, Decimal):
        try:
            value = Decimal(str(value))
        except Exception:
            raise ValueError(f"{field_name} must be a valid decimal number")

    if value < min_val:
        raise ValueError(f"{field_name} must be at least {min_val}")
    if value > max_val:
        raise ValueError(f"{field_name} cannot exceed {max_val}")

    return value


def validate_string_length(
    value: Optional[str],
    min_length: int = 1,
    max_length: int = 256,
    field_name: str = "value",
    allow_empty: bool = False
) -> Optional[str]:
    """Helper to validate string field length in Pydantic validators."""
    if value is None or value == "":
        if allow_empty:
            return value
        raise ValueError(f"{field_name} is required")

    if len(value) < min_length:
        raise ValueError(f"{field_name} must be at least {min_length} characters")
    if len(value) > max_length:
        raise ValueError(f"{field_name} cannot exceed {max_length} characters")

    return value


# ============================================================================
# Composition Decorator
# ============================================================================

def validate_and_sanitize(
    *validators: Callable,
    sanitize_fields: Optional[dict] = None
) -> Callable:
    """
    Composite decorator that applies multiple validators and sanitization.

    Args:
        validators: Variable number of validation decorator functions
        sanitize_fields: Dict mapping field names to sanitizer types

    Usage:
        @validate_and_sanitize(
            validate_expense_input,
            validate_amount_range,
            sanitize_fields={'description': 'text', 'merchant': 'merchant'}
        )
        async def create_expense(expense_data: ExpenseCreate):
            ...
    """
    def decorator(func: Callable) -> Callable:
        # Apply validators in order
        decorated_func = func
        for validator in validators:
            decorated_func = validator(decorated_func)

        # Apply sanitization if specified
        if sanitize_fields:
            for field, sanitizer_type in sanitize_fields.items():
                decorated_func = sanitize_request_fields(
                    [field],
                    sanitizer_type=sanitizer_type
                )(decorated_func)

        return decorated_func

    return decorator
