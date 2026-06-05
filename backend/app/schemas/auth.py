from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.core.validation import sanitize_string, validate_password


class UserRegister(BaseModel):
    """Schema for user registration"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = None

    # validators
    @classmethod
    def __get_validators__(cls):
        yield from super().__get_validators__()

    @staticmethod
    def validate_password_field(v):
        return validate_password(v)

    @classmethod
    def validate(cls, values):
        # pydantic's BaseModel.validate isn't intended for this, but
        # we keep simple: sanitize full_name if present
        if 'full_name' in values and values['full_name'] is not None:
            values['full_name'] = sanitize_string(values['full_name'])
        # validate password pattern
        values['password'] = validate_password(values['password'])
        return values


class UserCreate(BaseModel):
    """Alias for UserRegister"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for user response"""
    id: UUID
    email: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    currency: Optional[str] = None
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema for JWT token response"""
    access_token: str
    token_type: str = "bearer"


class TokenResponse(BaseModel):
    """Schema for complete token response with user info"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class UserUpdate(BaseModel):
    """Schema for updating user"""
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class PasswordChange(BaseModel):
    """Schema for password change"""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)
