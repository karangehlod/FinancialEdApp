"""Value Objects and Domain Models for Loan domain."""
from dataclasses import dataclass
from decimal import Decimal
from datetime import date, timedelta
from enum import Enum
from typing import Optional


class LoanDisplayStatus(str, Enum):
    """Human-readable loan status for display and domain logic.

    These are the rich display values used in domain objects and
    exposed to the frontend via the /enums API.
    Distinct from the DB-storage LoanStatus in schemas/loan.py which
    maps to the database CHECK constraint values (lowercase).

    Note: ``LoanStatusEnum`` is kept as a backward-compat alias below.
    """
    ACTIVE = "Active"
    CLOSED = "Closed"
    PAID_OFF = "Paid Off"
    OVERDUE = "Overdue"
    DEFAULTED = "Defaulted"


# Backward-compatible alias — use LoanDisplayStatus in new code
LoanStatusEnum = LoanDisplayStatus


class PaymentDisplayStatus(str, Enum):
    """Human-readable payment status for display and domain logic.

    Note: ``PaymentStatusEnum`` is kept as a backward-compat alias below.
    """
    PAID = "Paid"
    PENDING = "Pending"
    OVERDUE = "Overdue"
    FAILED = "Failed"


# Backward-compatible alias — use PaymentDisplayStatus in new code
PaymentStatusEnum = PaymentDisplayStatus


@dataclass(frozen=True)
class Money:
    """Value Object for monetary amounts."""
    amount: Decimal
    
    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Money amount cannot be negative")
    
    def __add__(self, other: 'Money') -> 'Money':
        if not isinstance(other, Money):
            raise TypeError("Can only add Money to Money")
        return Money(self.amount + other.amount)
    
    def __sub__(self, other: 'Money') -> 'Money':
        if not isinstance(other, Money):
            raise TypeError("Can only subtract Money from Money")
        result = self.amount - other.amount
        if result < 0:
            raise ValueError("Subtraction would result in negative money")
        return Money(result)
    
    def __mul__(self, factor: float) -> 'Money':
        return Money(Decimal(str(round(float(self.amount) * factor, 2))))
    
    def __eq__(self, other):
        if not isinstance(other, Money):
            return False
        return self.amount == other.amount
    
    def __lt__(self, other):
        if not isinstance(other, Money):
            raise TypeError("Cannot compare Money with non-Money type")
        return self.amount < other.amount
    
    def __le__(self, other):
        return self < other or self == other
    
    def __gt__(self, other):
        if not isinstance(other, Money):
            raise TypeError("Cannot compare Money with non-Money type")
        return self.amount > other.amount
    
    def __ge__(self, other):
        return self > other or self == other


@dataclass(frozen=True)
class InterestRate:
    """Value Object for interest rate."""
    percentage: Decimal
    
    def __post_init__(self):
        if self.percentage < 0 or self.percentage > 100:
            raise ValueError("Interest rate must be between 0 and 100")
    
    @property
    def monthly_decimal(self) -> float:
        """Get monthly rate as decimal (e.g., 8.5% = 0.00708)."""
        return float(self.percentage) / 12 / 100
    
    @property
    def yearly_decimal(self) -> float:
        """Get yearly rate as decimal (e.g., 8.5% = 0.085)."""
        return float(self.percentage) / 100
    
    def __str__(self) -> str:
        return f"{self.percentage}%"


@dataclass(frozen=True)
class LoanTerm:
    """Value Object for loan term."""
    months: int
    
    def __post_init__(self):
        if self.months <= 0:
            raise ValueError("Loan term must be positive")
        if self.months > 360:
            raise ValueError("Loan term cannot exceed 360 months (30 years)")
    
    @property
    def years(self) -> float:
        """Get term in years."""
        return self.months / 12
    
    def __str__(self) -> str:
        return f"{self.months} months"


@dataclass(frozen=True)
class LoanScheduleItem:
    """Value Object for a single loan payment schedule item."""
    payment_number: int
    payment_date: date
    emi_amount: Money
    principal_portion: Money
    interest_portion: Money
    remaining_balance: Money
    is_paid: bool = False
    
    def __post_init__(self):
        # Validate that principal + interest = EMI (with rounding tolerance)
        tolerance = Decimal('0.01')
        total = self.principal_portion.amount + self.interest_portion.amount
        if abs(total - self.emi_amount.amount) > tolerance:
            raise ValueError(
                f"Principal ({self.principal_portion.amount}) + Interest ({self.interest_portion.amount}) "
                f"must equal EMI ({self.emi_amount.amount})"
            )


@dataclass(frozen=True)
class LoanPayment:
    """Value Object for a loan payment."""
    amount: Money
    payment_date: date
    principal_amount: Money
    interest_amount: Money
    remaining_balance: Money
    notes: Optional[str] = None
    
    def __post_init__(self):
        # Validate that principal + interest = amount (with tolerance)
        tolerance = Decimal('0.01')
        total = self.principal_amount.amount + self.interest_amount.amount
        if abs(total - self.amount.amount) > tolerance:
            raise ValueError(
                f"Principal ({self.principal_amount.amount}) + Interest ({self.interest_amount.amount}) "
                f"must equal amount ({self.amount.amount})"
            )


@dataclass(frozen=True)
class EMIImpactAnalysis:
    """Value Object for EMI change impact analysis."""
    original_emi: Money
    new_emi: Money
    original_tenure_months: int
    new_tenure_months: int
    original_total_interest: Money
    new_total_interest: Money
    interest_savings: Money
    savings_percentage: Decimal
    
    @property
    def tenure_reduction_months(self) -> int:
        """Get reduction in tenure."""
        return self.original_tenure_months - self.new_tenure_months
    
    @property
    def is_beneficial(self) -> bool:
        """Check if the change is beneficial (saves interest)."""
        return self.interest_savings.amount > 0


@dataclass(frozen=True)
class PrepaymentAnalysis:
    """Value Object for prepayment impact analysis."""
    prepayment_amount: Money
    new_outstanding_balance: Money
    tenure_reduction_months: int
    interest_savings: Money
    savings_percentage: Decimal
    
    @property
    def is_full_payoff(self) -> bool:
        """Check if prepayment pays off the entire loan."""
        return self.new_outstanding_balance.amount == 0


@dataclass
class LoanState:
    """Domain Entity representing the state of a loan at a point in time."""
    principal: Money
    outstanding_balance: Money
    interest_rate: InterestRate
    emi_amount: Money
    term: LoanTerm
    remaining_months: int
    next_due_date: date
    status: LoanDisplayStatus

    def is_active(self) -> bool:
        return self.status == LoanDisplayStatus.ACTIVE

    def is_paid_off(self) -> bool:
        return self.outstanding_balance.amount == 0

    def is_overdue(self) -> bool:
        return self.status in [LoanDisplayStatus.OVERDUE, LoanDisplayStatus.DEFAULTED]
    
    def days_overdue(self) -> int:
        """Calculate days overdue."""
        if self.next_due_date < date.today():
            return (date.today() - self.next_due_date).days
        return 0


class DueDate:
    """Domain Service for calculating due dates."""
    
    @staticmethod
    def calculate_next_due_date(current_date: date) -> date:
        """Calculate next due date (typically next month same day)."""
        try:
            if current_date.month == 12:
                return current_date.replace(year=current_date.year + 1, month=1)
            else:
                return current_date.replace(month=current_date.month + 1)
        except ValueError:
            # Handle cases where the day doesn't exist in next month (e.g., Jan 31 -> Feb 28)
            if current_date.month == 12:
                next_month = current_date.replace(year=current_date.year + 1, month=1, day=1)
            else:
                next_month = current_date.replace(month=current_date.month + 1, day=1)
            
            # Get last day of the target month
            if next_month.month == 12:
                last_day = (next_month.replace(year=next_month.year + 1, month=1) - timedelta(days=1)).day
            else:
                last_day = (next_month.replace(month=next_month.month + 1) - timedelta(days=1)).day
            
            return next_month.replace(day=min(current_date.day, last_day))
    
    @staticmethod
    def is_overdue(due_date: date) -> bool:
        """Check if due date has passed."""
        return due_date < date.today()
    
    @staticmethod
    def days_until_due(due_date: date) -> int:
        """Get number of days until due date."""
        delta = due_date - date.today()
        return delta.days


@dataclass
class PaymentAllocation:
    """Represents how a payment is allocated between principal and interest."""
    total_payment: Money
    principal: Money
    interest: Money
    
    def __post_init__(self):
        # Validate allocation
        total = self.principal.amount + self.interest.amount
        if abs(total - self.total_payment.amount) > Decimal('0.01'):
            raise ValueError(
                f"Principal + Interest must equal total payment"
            )
    
    @property
    def principal_percentage(self) -> Decimal:
        """Get percentage of payment going to principal."""
        if self.total_payment.amount == 0:
            return Decimal('0')
        return (self.principal.amount / self.total_payment.amount * 100).quantize(Decimal('0.01'))
    
    @property
    def interest_percentage(self) -> Decimal:
        """Get percentage of payment going to interest."""
        if self.total_payment.amount == 0:
            return Decimal('0')
        return (self.interest.amount / self.total_payment.amount * 100).quantize(Decimal('0.01'))
