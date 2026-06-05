"""
Input sanitization utilities — P1-9.

Provides HTML stripping and text sanitization for user-supplied free-text
fields (expense description, merchant name, goal name, notes, etc.).

Design:
  - Uses `bleach` for HTML stripping (allows zero HTML tags by default).
  - Enforces maximum field lengths to prevent DB column overflow.
  - Validates characters against an allowlist for high-risk fields (e.g. merchant).
  - All functions are pure (no I/O) and safe for use in Pydantic validators.

Usage in Pydantic schema:
    from app.core.sanitization import sanitize_text, sanitize_merchant

    class ExpenseCreate(BaseModel):
        merchant: Optional[str] = None
        description: Optional[str] = None

        @field_validator("merchant", mode="before")
        @classmethod
        def clean_merchant(cls, v):
            return sanitize_merchant(v) if v else v

        @field_validator("description", mode="before")
        @classmethod
        def clean_description(cls, v):
            return sanitize_text(v, max_length=500) if v else v
"""

import re
import unicodedata
from typing import Optional

# Maximum field lengths (characters)
_MAX_MERCHANT_LEN   = 200
_MAX_TEXT_LEN       = 1000
_MAX_NAME_LEN       = 150
_MAX_NOTES_LEN      = 2000

# Allowed characters for structured fields like merchant names
# Letters (any unicode), digits, spaces, basic punctuation
_MERCHANT_ALLOWED_RE = re.compile(r"[^\w\s\-&'.,()/#@!]", re.UNICODE)

# Characters that should never appear in any user input (control chars, nulls)
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


def sanitize_text(value: str, max_length: int = _MAX_TEXT_LEN) -> str:
    """
    Strip HTML/JavaScript from free-text fields and enforce max length.

    1. Remove null bytes and control characters.
    2. Strip all HTML tags using bleach.
    3. Normalise unicode (NFC) to prevent homograph attacks.
    4. Truncate to max_length.
    5. Strip leading/trailing whitespace.

    Args:
        value:      Raw user input string.
        max_length: Maximum allowed character count (default 1000).

    Returns:
        Sanitized string safe for DB storage and display.
    """
    if not value:
        return value

    # 1. Remove null bytes and dangerous control characters
    value = _CONTROL_CHAR_RE.sub("", value)

    # 2. Strip HTML (bleach strips all tags when allowed_tags=[])
    try:
        import bleach
        value = bleach.clean(value, tags=[], attributes={}, strip=True)
    except ImportError:
        # Fallback: simple regex tag stripper if bleach not installed
        value = re.sub(r"<[^>]+>", "", value)

    # 3. Normalise unicode (prevent lookalike character attacks)
    value = unicodedata.normalize("NFC", value)

    # 4. Truncate
    value = value[:max_length]

    # 5. Strip whitespace
    return value.strip()


def sanitize_merchant(value: Optional[str]) -> Optional[str]:
    """
    Sanitize a merchant name: strip HTML, then enforce character allowlist.

    Merchant names are displayed in reports and analytics, so we apply a
    stricter character allowlist on top of the general HTML stripping.

    Args:
        value: Raw merchant name from user input.

    Returns:
        Sanitized merchant name, or None if input is None/empty.
    """
    if not value:
        return value

    # General HTML stripping + control char removal
    value = sanitize_text(value, max_length=_MAX_MERCHANT_LEN)

    # Remove characters outside the allowlist
    value = _MERCHANT_ALLOWED_RE.sub("", value)

    return value.strip() or None


def sanitize_name(value: Optional[str]) -> Optional[str]:
    """
    Sanitize a display name (user name, goal name, etc.).

    More permissive than merchant: allows apostrophes, hyphens, accents.

    Args:
        value: Raw name string.

    Returns:
        Sanitized name string truncated to _MAX_NAME_LEN.
    """
    if not value:
        return value
    return sanitize_text(value, max_length=_MAX_NAME_LEN)


def sanitize_notes(value: Optional[str]) -> Optional[str]:
    """
    Sanitize longer notes/description fields.

    Strips HTML but allows a wider character set since notes are internal.

    Args:
        value: Raw notes string.

    Returns:
        Sanitized notes truncated to _MAX_NOTES_LEN.
    """
    if not value:
        return value
    return sanitize_text(value, max_length=_MAX_NOTES_LEN)


def validate_max_length(value: Optional[str], max_length: int, field_name: str) -> Optional[str]:
    """
    Raise ValueError if the string exceeds max_length after sanitization.

    Intended for use in Pydantic validators where you want an explicit error
    instead of silent truncation.

    Args:
        value:      The (already sanitized) string value.
        max_length: Maximum allowed length.
        field_name: Human-readable field name for the error message.

    Returns:
        The value unchanged if within limits.

    Raises:
        ValueError: If the value exceeds max_length.
    """
    if value and len(value) > max_length:
        raise ValueError(f"{field_name} must not exceed {max_length} characters")
    return value
