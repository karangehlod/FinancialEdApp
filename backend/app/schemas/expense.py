from pydantic import BaseModel, Field, field_validator, ConfigDict, BeforeValidator
from typing import Optional, List, Annotated
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from app.core.sanitization import sanitize_text, sanitize_merchant


def parse_decimal(v):
    """Parse decimal from string, int, or float"""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    try:
        decimal_val = Decimal(str(v))
        if decimal_val <= 0:
            raise ValueError("Amount must be greater than 0")
        return decimal_val
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid decimal amount: {v}") from e


def parse_date(v):
    """Parse date from string or date object"""
    if v is None:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        try:
            # Simple date parsing YYYY-MM-DD
            parts = v.split('-')
            if len(parts) == 3:
                return date(int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError):
            pass
        raise ValueError(f"Invalid date format. Use YYYY-MM-DD: {v}")
    raise ValueError(f"Invalid date type: {type(v)}")


# Type aliases with before validators
RequiredDecimal = Annotated[Decimal, BeforeValidator(parse_decimal)]
RequiredDate = Annotated[date, BeforeValidator(parse_date)]
OptionalDecimal = Annotated[Optional[Decimal], BeforeValidator(parse_decimal)]
OptionalDate = Annotated[Optional[date], BeforeValidator(parse_date)]


class ExpenseBase(BaseModel):
    """Base schema for expense"""
    amount: RequiredDecimal = Field(..., gt=0, decimal_places=2)
    category: str = Field(..., min_length=1, max_length=50)
    subcategory: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    date: RequiredDate
    merchant: Optional[str] = Field(None, max_length=200)
    payment_method: Optional[str] = Field(None, max_length=50)
    is_recurring: bool = False

    # ── P1-9: Input sanitization validators ──────────────────────────────────

    @field_validator("merchant", mode="before")
    @classmethod
    def clean_merchant(cls, v: Optional[str]) -> Optional[str]:
        """Strip HTML and enforce character allowlist for merchant names."""
        return sanitize_merchant(v) if v else v

    @field_validator("description", mode="before")
    @classmethod
    def clean_description(cls, v: Optional[str]) -> Optional[str]:
        """Strip HTML from free-text description."""
        return sanitize_text(v, max_length=500) if v else v

    @field_validator("subcategory", mode="before")
    @classmethod
    def clean_subcategory(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_text(v, max_length=50) if v else v


class ExpenseCreate(ExpenseBase):
    """Schema for creating an expense"""
    pass


class ExpenseUpdate(BaseModel):
    """Schema for updating an expense"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "amount": "10.00",
                "category": "food",
                "date": "2026-01-18",
                "description": "tea"
            }
        }
    )

    amount: OptionalDecimal = None
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    subcategory: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    date: OptionalDate = None
    merchant: Optional[str] = Field(None, max_length=200)
    payment_method: Optional[str] = Field(None, max_length=50)
    is_recurring: Optional[bool] = None

    @field_validator("merchant", mode="before")
    @classmethod
    def clean_merchant(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_merchant(v) if v else v

    @field_validator("description", mode="before")
    @classmethod
    def clean_description(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_text(v, max_length=500) if v else v





class ExpenseResponse(ExpenseBase):
    """Schema for expense response"""
    id: UUID
    user_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class ExpenseListResponse(BaseModel):
    """Schema for list of expenses with pagination"""
    expenses: List[ExpenseResponse]
    total: int
    page: int = 1
    page_size: int = 50
    
    class Config:
        from_attributes = True


class ExpenseFilter(BaseModel):
    """Schema for filtering expenses"""
    category: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    merchant: Optional[str] = None
    payment_method: Optional[str] = None


class ExpenseSummary(BaseModel):
    """Schema for expense summary"""
    total_amount: Decimal
    count: int
    category: Optional[str] = None
    start_date: date
    end_date: date
