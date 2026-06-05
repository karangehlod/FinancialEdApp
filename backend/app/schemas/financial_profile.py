from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal
from uuid import UUID


class FinancialProfileBase(BaseModel):
    """Base schema for financial profile"""
    monthly_salary: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    currency: str = "INR"
    total_emi: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    rent: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    insurance: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    subscriptions: Optional[Decimal] = Field(None, ge=0, decimal_places=2)


class FinancialProfileCreate(FinancialProfileBase):
    """Schema for creating a financial profile"""
    pass


class FinancialProfileUpdate(BaseModel):
    """Schema for updating a financial profile"""
    monthly_salary: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    currency: Optional[str] = None
    total_emi: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    rent: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    insurance: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    subscriptions: Optional[Decimal] = Field(None, ge=0, decimal_places=2)


class FinancialProfileResponse(FinancialProfileBase):
    """Schema for financial profile response"""
    user_id: UUID
    currency: Optional[str] = "INR"
    disposable_income: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
