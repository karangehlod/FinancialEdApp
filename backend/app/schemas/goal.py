"""Goal schemas for Pydantic validation."""
from pydantic import BaseModel, Field, field_validator, validator
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from app.core.sanitization import sanitize_name, sanitize_notes


class GoalCreate(BaseModel):
    """Schema for creating a goal."""
    goal_name: str = Field(..., min_length=1, max_length=255)
    goal_type: str = Field(..., pattern="^(savings|debt_payoff|investment|emergency_fund|other)$")
    target_amount: Decimal = Field(..., gt=0)
    target_date: date = Field(...)
    description: Optional[str] = Field(None, max_length=2000)
    priority: str = Field(default="medium", pattern="^(high|medium|low)$")

    @field_validator("goal_name", mode="before")
    @classmethod
    def clean_goal_name(cls, v: Optional[str]) -> Optional[str]:
        """Strip HTML and normalise unicode from goal name."""
        return sanitize_name(v) if v else v

    @field_validator("description", mode="before")
    @classmethod
    def clean_description(cls, v: Optional[str]) -> Optional[str]:
        """Strip HTML from goal description."""
        return sanitize_notes(v) if v else v

    @validator("target_date")
    def validate_target_date(cls, v):
        if v <= date.today():
            raise ValueError("Target date must be in the future")
        return v


class GoalUpdate(BaseModel):
    """Schema for updating a goal."""
    goal_name: Optional[str] = Field(None, max_length=255)
    target_amount: Optional[Decimal] = None
    current_amount: Optional[Decimal] = None
    target_date: Optional[date] = None
    description: Optional[str] = Field(None, max_length=2000)
    priority: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|completed|paused|abandoned)$")

    @field_validator("goal_name", mode="before")
    @classmethod
    def clean_goal_name(cls, v: Optional[str]) -> Optional[str]:
        """Strip HTML and normalise unicode from goal name."""
        return sanitize_name(v) if v else v

    @field_validator("description", mode="before")
    @classmethod
    def clean_description(cls, v: Optional[str]) -> Optional[str]:
        """Strip HTML from goal description."""
        return sanitize_notes(v) if v else v


class GoalResponse(BaseModel):
    """Schema for goal response."""
    id: UUID
    user_id: UUID
    goal_name: str
    goal_type: str
    target_amount: Decimal
    current_amount: Decimal
    target_date: date
    description: Optional[str]
    priority: str
    status: str
    progress_percentage: float = Field(description="Calculated as (current_amount / target_amount) * 100")
    days_remaining: int = Field(description="Days until target date")
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class GoalListResponse(BaseModel):
    """Schema for list of goals."""
    success: bool
    data: list[GoalResponse]
    pagination: Optional[dict] = None


class GoalProgressUpdate(BaseModel):
    """Schema for updating goal progress."""
    current_amount: Decimal = Field(..., ge=0)


class GoalMilestoneResponse(BaseModel):
    """Schema for goal milestone achievement."""
    goal_id: UUID
    goal_name: str
    achievement_percentage: float
    message: str
