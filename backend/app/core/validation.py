from pydantic import EmailStr, validator
from pydantic import BaseModel
from typing import Optional
import re

# Shared validators and helper functions for request data

PASSWORD_REGEX = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,100}$")


def validate_password(value: str) -> str:
    if not PASSWORD_REGEX.match(value):
        raise ValueError("Password must be 8-100 chars, include upper, lower and digit")
    return value


def sanitize_string(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    # Basic trimming and length limit
    v = value.strip()
    if len(v) > 256:
        raise ValueError("Value too long")
    return v


class PasswordSchema(BaseModel):
    new_password: str

    @validator("new_password")
    def check_password(cls, v):
        return validate_password(v)
