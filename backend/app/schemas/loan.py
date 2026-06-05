"""Loan management schemas."""
from pydantic import BaseModel, Field, validator, field_validator
from typing import Optional, List, Dict
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from enum import Enum

from app.core.sanitization import sanitize_name, sanitize_notes


class LoanType(str, Enum):
    """Loan type enumeration."""
    PERSONAL = "Personal"
    HOME = "Home"
    CAR = "Car"
    EDUCATION = "Education"
    BUSINESS = "Business"
    CREDIT_CARD = "Credit Card"
    OTHER = "Other"


class LoanStatus(str, Enum):
    """Loan status enumeration — values must match DB CHECK constraint
    (lowercase: active, closed, defaulted, restructured)."""
    ACTIVE = "active"
    CLOSED = "closed"
    PAID_OFF = "closed"       # Alias for CLOSED
    DEFAULTED = "defaulted"
    PENDING = "active"        # Map Pending → active (DB doesn't have 'pending')
    OVERDUE = "defaulted"     # Map Overdue → defaulted
    RESTRUCTURED = "restructured"


class PaymentStatus(str, Enum):
    """Payment status enumeration."""
    PAID = "Paid"
    PENDING = "Pending"
    OVERDUE = "Overdue"
    PARTIAL = "Partial"


# NEW: Advanced EMI calculation schemas
class EMICalculationRequest(BaseModel):
    """Request schema for EMI calculation scenarios."""
    principal_amount: Decimal = Field(..., gt=0, decimal_places=2)
    interest_rate: Decimal = Field(..., ge=0, le=100, decimal_places=2)
    loan_term_months: int = Field(..., gt=0, le=600)
    current_emi: Optional[Decimal] = Field(None, gt=0, decimal_places=2)


class EMIImpactAnalysis(BaseModel):
    """Schema for EMI impact analysis results."""
    original_emi: Decimal
    new_emi: Decimal
    monthly_emi: Decimal  # Alias for new_emi for backward compatibility
    emi_to_income_ratio: Decimal = Decimal('0')  # Add missing field
    original_tenure_months: int
    new_tenure_months: int
    tenure_reduction_months: int
    original_total_interest: Decimal
    new_total_interest: Decimal
    interest_savings: Decimal
    total_savings_percentage: Decimal
    
    def __init__(self, **data):
        # Set monthly_emi as alias for new_emi
        if 'new_emi' in data and 'monthly_emi' not in data:
            data['monthly_emi'] = data['new_emi']
        elif 'monthly_emi' in data and 'new_emi' not in data:
            data['new_emi'] = data['monthly_emi']
        super().__init__(**data)


class PrepaymentAnalysis(BaseModel):
    """Schema for prepayment analysis."""
    prepayment_amount: Decimal
    new_outstanding_balance: Decimal
    tenure_reduction_months: int
    interest_savings: Decimal
    new_emi: Optional[Decimal] = None  # If EMI is reduced instead of tenure
    savings_percentage: Decimal


class LoanConfiguration(BaseModel):
    """Schema for configurable loan parameters."""
    loan_id: UUID
    new_principal: Optional[Decimal] = Field(None, gt=0)
    new_interest_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    new_emi: Optional[Decimal] = Field(None, gt=0)
    prepayment_amount: Optional[Decimal] = Field(None, gt=0)
    effective_date: Optional[date] = None


class BudgetLoanIntegration(BaseModel):
    """Schema for integrating loans into budget planning."""
    month: str  # YYYY-MM format
    total_emi_budget: Decimal
    loans: List['LoanEMIBudgetItem']
    weekly_breakdown: List['WeeklyEMIBreakdown']
    budget_utilization_percentage: Decimal
    available_for_prepayment: Decimal


class LoanEMIBudgetItem(BaseModel):
    """Individual loan EMI in budget planning."""
    loan_id: UUID
    loan_type: str
    lender_name: str
    monthly_emi: Decimal
    due_date: date
    principal_portion: Decimal
    interest_portion: Decimal
    remaining_balance: Decimal


class WeeklyEMIBreakdown(BaseModel):
    """Weekly breakdown of EMI payments."""
    week_number: int
    week_start_date: date
    week_end_date: date
    emi_due: Decimal
    loans_due: List[str]  # Loan IDs due this week


# NEW: Advanced calculation results
class LoanOptimizationSuggestion(BaseModel):
    """Loan optimization suggestions."""
    loan_id: UUID
    suggestion_type: str  # "increase_emi", "prepay", "refinance"
    current_situation: Dict
    suggested_action: Dict
    potential_savings: Dict
    risk_assessment: str


class ComprehensiveLoanAnalysis(BaseModel):
    """Comprehensive analysis across all loans."""
    total_loans: int
    total_outstanding: Decimal
    total_monthly_emi: Decimal
    weighted_average_interest_rate: Decimal
    total_remaining_interest: Decimal
    loan_to_income_ratio: Decimal
    monthly_budget_allocation: Decimal
    optimization_opportunities: List[LoanOptimizationSuggestion]
    budget_integration: BudgetLoanIntegration


# Update existing schemas to maintain compatibility
class LoanBase(BaseModel):
    """Base schema for loan."""
    loan_type: LoanType
    lender_name: str = Field(..., min_length=1, max_length=255)
    principal_amount: Decimal = Field(..., gt=0, decimal_places=2)
    interest_rate: Decimal = Field(..., ge=0, le=100, decimal_places=2)  # Annual interest rate
    loan_term_months: int = Field(..., gt=0, le=600)  # Max 50 years
    emi_amount: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    start_date: date
    description: Optional[str] = Field(None, max_length=500)

    @field_validator("lender_name", mode="before")
    @classmethod
    def clean_lender_name(cls, v: Optional[str]) -> Optional[str]:
        """Strip HTML and normalise unicode from lender name."""
        return sanitize_name(v) if v else v

    @field_validator("description", mode="before")
    @classmethod
    def clean_description(cls, v: Optional[str]) -> Optional[str]:
        """Strip HTML from loan description."""
        return sanitize_notes(v) if v else v

    @validator('emi_amount', pre=True, always=True)
    def calculate_emi_if_not_provided(cls, v, values):
        """Calculate EMI if not provided."""
        if v is None and all(k in values for k in ['principal_amount', 'interest_rate', 'loan_term_months']):
            principal = float(values['principal_amount'])
            rate = float(values['interest_rate']) / 12 / 100  # Monthly rate
            months = values['loan_term_months']
            
            if rate > 0:
                # EMI = P * r * (1+r)^n / ((1+r)^n - 1)
                emi = principal * rate * ((1 + rate) ** months) / (((1 + rate) ** months) - 1)
            else:
                # If no interest, simple division
                emi = principal / months
            
            return Decimal(str(round(emi, 2)))
        return v


class LoanCreate(LoanBase):
    """Schema for creating a loan."""
    pass


class LoanUpdate(BaseModel):
    """Schema for updating a loan."""
    loan_type: Optional[LoanType] = None
    lender_name: Optional[str] = Field(None, min_length=1, max_length=255)
    principal_amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    interest_rate: Optional[Decimal] = Field(None, ge=0, le=100, decimal_places=2)
    loan_term_months: Optional[int] = Field(None, gt=0, le=600)
    emi_amount: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    status: Optional[LoanStatus] = None
    description: Optional[str] = Field(None, max_length=500)
    start_date: Optional[date] = None

    @field_validator("lender_name", mode="before")
    @classmethod
    def clean_lender_name(cls, v: Optional[str]) -> Optional[str]:
        """Strip HTML and normalise unicode from lender name."""
        return sanitize_name(v) if v else v

    @field_validator("description", mode="before")
    @classmethod
    def clean_description(cls, v: Optional[str]) -> Optional[str]:
        """Strip HTML from loan description."""
        return sanitize_notes(v) if v else v


class LoanResponse(LoanBase):
    """Schema for loan response."""
    id: UUID
    user_id: UUID
    status: LoanStatus
    remaining_principal: Decimal
    outstanding_balance: Decimal = None  # Alias for remaining_principal
    total_paid: Decimal
    next_payment_date: Optional[date]
    payments_made: int
    payments_remaining: int
    total_interest_paid: Decimal
    created_at: datetime
    updated_at: Optional[datetime]
    
    def __init__(self, **data):
        super().__init__(**data)
        # Set outstanding_balance as alias for remaining_principal
        if hasattr(self, 'remaining_principal'):
            self.outstanding_balance = self.remaining_principal
    
    class Config:
        from_attributes = True


class LoanPaymentBase(BaseModel):
    """Base schema for loan payment."""
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    payment_date: date
    payment_method: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = Field(None, max_length=500)


class LoanPaymentCreate(LoanPaymentBase):
    """Schema for creating a loan payment."""
    pass


class LoanPaymentUpdate(BaseModel):
    """Schema for updating a loan payment."""
    amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    payment_date: Optional[date] = None
    payment_method: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = Field(None, max_length=500)
    status: Optional[PaymentStatus] = None


class LoanPaymentResponse(LoanPaymentBase):
    """Schema for loan payment response."""
    id: UUID
    loan_id: UUID
    user_id: UUID
    status: PaymentStatus
    principal_portion: Decimal
    interest_portion: Decimal
    remaining_balance: Decimal
    amount_paid: Decimal = None  # Alias for amount
    principal_amount: Decimal = None  # Alias for principal_portion
    interest_amount: Decimal = None  # Alias for interest_portion
    created_at: datetime
    
    def __init__(self, **data):
        super().__init__(**data)
        # Set aliases
        if hasattr(self, 'amount'):
            self.amount_paid = self.amount
        if hasattr(self, 'principal_portion'):
            self.principal_amount = self.principal_portion
        if hasattr(self, 'interest_portion'):
            self.interest_amount = self.interest_portion
    
    class Config:
        from_attributes = True


class RepaymentScheduleItem(BaseModel):
    """Schema for repayment schedule item."""
    payment_number: int
    installment_number: int = None  # Alias for payment_number
    payment_date: date
    emi_amount: Decimal
    principal_portion: Decimal
    interest_portion: Decimal
    remaining_balance: Decimal
    is_paid: bool = False
    
    # Aliases for test compatibility
    @property
    def principal_amount(self) -> Decimal:
        return self.principal_portion
    
    @property
    def interest_amount(self) -> Decimal:
        return self.interest_portion
    
    def __init__(self, **data):
        # Set installment_number as alias for payment_number
        if 'payment_number' in data and 'installment_number' not in data:
            data['installment_number'] = data['payment_number']
        elif 'installment_number' in data and 'payment_number' not in data:
            data['payment_number'] = data['installment_number']
        super().__init__(**data)


class LoanAnalytics(BaseModel):
    """Schema for loan analytics."""
    total_loans: int
    active_loans: int
    total_principal_borrowed: Decimal
    total_principal_amount: Decimal  # Alias for total_principal_borrowed for backward compatibility
    total_outstanding: Decimal
    total_outstanding_balance: Decimal  # Alias for total_outstanding
    total_monthly_emi: Decimal
    total_interest_paid: Decimal
    total_interest_remaining: Decimal
    loans_by_type: dict
    average_interest_rate: Decimal
    
    def __init__(self, **data):
        # Set aliases
        if 'total_principal_borrowed' in data and 'total_principal_amount' not in data:
            data['total_principal_amount'] = data['total_principal_borrowed']
        elif 'total_principal_amount' in data and 'total_principal_borrowed' not in data:
            data['total_principal_borrowed'] = data['total_principal_amount']
            
        if 'total_outstanding' in data and 'total_outstanding_balance' not in data:
            data['total_outstanding_balance'] = data['total_outstanding']
        elif 'total_outstanding_balance' in data and 'total_outstanding' not in data:
            data['total_outstanding'] = data['total_outstanding_balance']
            
        super().__init__(**data)


class LoanSummary(BaseModel):
    """Schema for loan summary."""
    loan: LoanResponse
    repayment_schedule: List[RepaymentScheduleItem]
    next_payment: Optional[RepaymentScheduleItem]
    loan_analytics: dict


class MonthlyLoanSummary(BaseModel):
    """Schema for monthly loan summary."""
    month: str
    total_emi_due: Optional[Decimal] = None
    total_paid: Optional[Decimal] = None
    total_emi_paid: Optional[Decimal] = None
    total_principal_paid: Optional[Decimal] = None
    total_interest_paid: Optional[Decimal] = None
    loans: Optional[List[LoanResponse]] = []
    payment_schedule: Optional[List[RepaymentScheduleItem]] = []


class LoanOption(BaseModel):
    """Schema for a loan option in comparison."""
    principal_amount: Decimal = Field(..., gt=0, decimal_places=2)
    interest_rate: Decimal = Field(..., ge=0, le=100, decimal_places=2)
    loan_term_months: int = Field(..., gt=0, le=600)
    loan_type: str
    lender_name: str


class LoanComparisonResult(BaseModel):
    """Schema for individual loan comparison result."""
    lender_name: str
    loan_type: str
    principal_amount: Decimal
    interest_rate: Decimal
    loan_term_months: int
    emi_amount: Decimal
    total_amount_payable: Decimal
    total_interest: Decimal


class LoanComparisonRequest(BaseModel):
    """Schema for loan comparison request."""
    loan_options: List[LoanOption]


class LoanComparisonResponse(BaseModel):
    """Schema for loan comparison response."""
    comparison_results: List[LoanComparisonResult]
    best_option: Optional[LoanComparisonResult] = None
    savings_vs_worst: Optional[Decimal] = None


class PrepaymentAnalysisRequest(BaseModel):
    """Schema for prepayment analysis request."""
    prepayment_amount: Decimal = Field(..., gt=0, decimal_places=2)


class PrepaymentAnalysisResponse(BaseModel):
    """Schema for prepayment analysis response."""
    original_emi: Decimal
    new_emi: Optional[Decimal]
    tenure_reduction_months: int
    new_loan_term_months: int
    interest_savings: Decimal
    total_savings: Decimal
    savings: Decimal  # For compatibility with tests
