from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.utils.sanitize import clean_text


class UserProfileBase(BaseModel):
    """Base schema for user profile"""
    first_name: Optional[str] = None  # ✅ Add first_name
    last_name: Optional[str] = None   # ✅ Add last_name
    name: Optional[str] = None
    country: str = "IN"
    currency: str = "INR"
    knowledge_level: Optional[str] = None
    risk_tolerance: Optional[str] = None
    consent_given: bool = False

    @validator("first_name", "last_name", "name", "knowledge_level", "risk_tolerance", pre=True, always=False)
    def _clean_strings(cls, v):
        return clean_text(v)


class UserProfileCreate(UserProfileBase):
    """Schema for creating a user profile"""
    user_id: UUID


class UserProfileUpdate(BaseModel):
    """Schema for updating a user profile"""
    first_name: Optional[str] = None  # ✅ Add first_name
    last_name: Optional[str] = None   # ✅ Add last_name
    name: Optional[str] = None
    country: Optional[str] = None
    currency: Optional[str] = None
    knowledge_level: Optional[str] = None
    risk_tolerance: Optional[str] = None
    consent_given: Optional[bool] = None

    @validator("first_name", "last_name", "name", "knowledge_level", "risk_tolerance", pre=True, always=False)
    def _clean_strings(cls, v):
        return clean_text(v)


class UserProfileResponse(UserProfileBase):
    """Schema for user profile response"""
    user_id: UUID
    first_name: Optional[str] = None  # ✅ Include in response
    last_name: Optional[str] = None   # ✅ Include in response
    consent_timestamp: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
