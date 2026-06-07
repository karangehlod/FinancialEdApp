from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


class BudgetBase(BaseModel):
    """Base schema for budget"""
    month: date
    category: str = Field(..., min_length=1, max_length=50)
    recommended_amount: Optional[Decimal] = Field(None, ge=0, decimal_places=2)


class BudgetCreate(BudgetBase):
    """Schema for creating a budget"""
    allocated_amount: Decimal = Field(..., ge=0, decimal_places=2)


class BudgetUpdate(BaseModel):
    """Schema for updating a budget"""
    allocated_amount: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    spent_amount: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    recommended_amount: Optional[Decimal] = Field(None, ge=0, decimal_places=2)


class BudgetResponse(BudgetBase):
    """Schema for budget response"""
    id: UUID
    user_id: UUID
    allocated_amount: Decimal = Field(..., ge=0, decimal_places=2)
    spent_amount: Decimal
    created_at: datetime
    
    class Config:
        from_attributes = True


class BudgetAlert(BaseModel):
    """Schema for budget alert"""
    id: UUID
    budget_id: UUID
    user_id: UUID
    alert_level: str
    message: str
    utilization_at_alert: Decimal
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class BudgetWithAlert(BudgetResponse):
    """Schema for budget with alerts"""
    remaining_amount: Decimal  # Computed field
    utilization_percentage: float
    alert_status: str
    alert_message: Optional[str] = None


class CategorySpending(BaseModel):
    """Schema for category spending analysis"""
    category: str
    allocated: Decimal
    spent: Decimal
    remaining: Decimal
    percentage: float


class BudgetAnalytics(BaseModel):
    """Schema for budget analytics"""
    total_allocated: Decimal
    total_spent: Decimal
    total_remaining: Decimal
    total_budgets: int = 0  # Number of budget categories
    overall_utilization: Decimal
    categories: List[CategorySpending]
    alerts_count: int
    over_budget_categories: List[str]


class MonthlyBudgetSummary(BaseModel):
    """Schema for monthly budget summary"""
    month: str
    salary: Optional[Decimal]
    fixed_expenses: Decimal
    disposable_income: Optional[Decimal]
    total_budget: Decimal
    total_spent: Decimal
    savings: Decimal
    category_breakdown: dict

class BudgetAlertResponse(BaseModel):
    """Schema for budget alert response"""
    id: UUID
    budget_id: UUID
    user_id: UUID
    alert_level: str
    message: str
    utilization_at_alert: Decimal
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
