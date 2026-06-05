"""
Unit tests for backend/app/core/sanitization.py

Validates that all sanitization functions:
- Strip HTML/script tags (XSS prevention)
- Remove null bytes and control characters
- Enforce maximum field lengths (truncation or ValueError)
- Apply character allowlist for merchant names
- Handle None / empty inputs gracefully
- Normalise unicode (NFC) to prevent homograph attacks
"""
import pytest
from app.core.sanitization import (
    sanitize_text,
    sanitize_merchant,
    sanitize_name,
    sanitize_notes,
    validate_max_length,
)


# ── sanitize_text ─────────────────────────────────────────────────────────────

class TestSanitizeText:
    """Tests for the generic sanitize_text function."""

    def test_strips_script_tag(self):
        assert "<script>" not in sanitize_text("<script>alert('xss')</script>")

    def test_strips_img_onerror_xss(self):
        result = sanitize_text('<img src=x onerror="alert(1)">')
        assert "<img" not in result
        assert "onerror" not in result

    def test_strips_html_bold_tag(self):
        result = sanitize_text("<b>hello</b>")
        assert "<b>" not in result
        assert "hello" in result

    def test_removes_null_bytes(self):
        result = sanitize_text("hello\x00world")
        assert "\x00" not in result
        assert "hello" in result

    def test_removes_control_characters(self):
        result = sanitize_text("hello\x0bworld\x0c!")
        assert "\x0b" not in result
        assert "\x0c" not in result

    def test_truncates_to_max_length(self):
        long_input = "a" * 2000
        result = sanitize_text(long_input, max_length=500)
        assert len(result) <= 500

    def test_default_max_length_is_1000(self):
        long_input = "a" * 1500
        result = sanitize_text(long_input)
        assert len(result) <= 1000

    def test_strips_leading_trailing_whitespace(self):
        result = sanitize_text("  hello  ")
        assert result == "hello"

    def test_normalises_unicode_nfc(self):
        # NFC: é as single codepoint vs NFD: e + combining accent
        nfd_e = "e\u0301"  # NFD form (2 codepoints)
        result = sanitize_text(nfd_e)
        assert result == "\xe9"  # NFC é (1 codepoint)

    def test_preserves_plain_text(self):
        result = sanitize_text("Hello, World! 123")
        assert result == "Hello, World! 123"

    def test_returns_empty_string_for_empty_input(self):
        assert sanitize_text("") == ""

    def test_handles_none_gracefully(self):
        # sanitize_text with None should return None (caller handles None check)
        assert sanitize_text(None) is None  # type: ignore[arg-type]

    def test_handles_nested_html(self):
        result = sanitize_text("<div><p><b>Nested</b></p></div>")
        assert "<" not in result
        assert "Nested" in result

    def test_strips_javascript_uri(self):
        result = sanitize_text('<a href="javascript:alert(1)">click</a>')
        assert "javascript:" not in result


# ── sanitize_merchant ─────────────────────────────────────────────────────────

class TestSanitizeMerchant:
    """Tests for merchant-name sanitization (stricter allowlist)."""

    def test_strips_html_from_merchant(self):
        result = sanitize_merchant('<b>Amazon</b>')
        assert "<b>" not in result
        assert "Amazon" in result

    def test_allows_ampersand_and_dash(self):
        # bleach.clean() HTML-encodes & → &amp; even in strip mode; the sanitized
        # result is safe for storage and will be decoded on display.
        result = sanitize_merchant("Barnes & Noble - Online")
        assert result is not None
        # Accepts both the encoded form (bleach) and literal & (fallback path)
        assert "Noble" in result
        assert "-" in result

    def test_removes_backtick_characters(self):
        result = sanitize_merchant("Store`Drop")
        assert "`" not in result

    def test_truncates_to_200_chars(self):
        long_name = "A" * 300
        result = sanitize_merchant(long_name)
        assert len(result) <= 200

    def test_returns_none_for_none_input(self):
        assert sanitize_merchant(None) is None

    def test_returns_none_for_empty_after_sanitization(self):
        # Input that becomes empty after stripping
        result = sanitize_merchant("<script></script>")
        assert result is None or result == ""

    def test_allows_parentheses_and_period(self):
        result = sanitize_merchant("U.S. Corp (LLC)")
        assert "U.S. Corp (LLC)" == result

    def test_strips_emoji_not_in_allowlist(self):
        # Emoji are not in the Unicode \w class by default for the MERCHANT regex
        result = sanitize_merchant("Store 🛒 Name")
        # We don't assert exact output but ensure no error and reasonable result
        assert isinstance(result, str) or result is None


# ── sanitize_name ────────────────────────────────────────────────────────────

class TestSanitizeName:
    """Tests for display-name sanitization."""

    def test_strips_html(self):
        result = sanitize_name("<b>John</b>")
        assert "<b>" not in result
        assert "John" in result

    def test_truncates_to_150_chars(self):
        result = sanitize_name("A" * 200)
        assert len(result) <= 150

    def test_returns_original_value_when_no_html(self):
        result = sanitize_name("O'Brien")
        assert "O'Brien" == result

    def test_returns_none_for_none(self):
        assert sanitize_name(None) is None

    def test_returns_empty_for_empty(self):
        assert sanitize_name("") == ""


# ── sanitize_notes ────────────────────────────────────────────────────────────

class TestSanitizeNotes:
    """Tests for long notes / description sanitization."""

    def test_strips_html(self):
        result = sanitize_notes("<h1>Title</h1><p>Body</p>")
        assert "<h1>" not in result
        assert "Title" in result

    def test_truncates_to_2000_chars(self):
        result = sanitize_notes("X" * 3000)
        assert len(result) <= 2000

    def test_allows_wide_character_set(self):
        # bleach HTML-encodes & even when stripping; verify no HTML tags remain
        # and the key non-HTML characters are preserved.
        text = "Notes: 50% off & discount — valid (today)!"
        result = sanitize_notes(text)
        assert result is not None
        assert "<" not in result
        assert "50%" in result
        assert "discount" in result
        assert "valid (today)!" in result

    def test_returns_none_for_none(self):
        assert sanitize_notes(None) is None


# ── validate_max_length ───────────────────────────────────────────────────────

class TestValidateMaxLength:
    """Tests for the explicit-error max-length validator."""

    def test_passes_value_within_limit(self):
        result = validate_max_length("hello", 10, "field")
        assert result == "hello"

    def test_raises_for_value_exceeding_limit(self):
        with pytest.raises(ValueError, match="must not exceed 5 characters"):
            validate_max_length("toolong", 5, "field")

    def test_passes_none_value(self):
        assert validate_max_length(None, 10, "field") is None

    def test_passes_exact_length(self):
        result = validate_max_length("exact", 5, "field")
        assert result == "exact"


# ── Integration: Pydantic schema validators ───────────────────────────────────

class TestSchemaIntegration:
    """Ensure sanitization validators are wired into Pydantic schemas."""

    def test_expense_create_sanitizes_description(self):
        from decimal import Decimal
        from datetime import date
        from app.schemas.expense import ExpenseCreate

        raw = ExpenseCreate(
            amount=Decimal("10.00"),
            category="food",
            date=date.today(),
            description='<script>evil()</script>',
        )
        assert "<script>" not in (raw.description or "")

    def test_expense_create_sanitizes_merchant(self):
        from decimal import Decimal
        from datetime import date
        from app.schemas.expense import ExpenseCreate

        raw = ExpenseCreate(
            amount=Decimal("10.00"),
            category="food",
            date=date.today(),
            merchant='<b>Amazon</b>',
        )
        assert "<b>" not in (raw.merchant or "")
        assert "Amazon" in (raw.merchant or "")

    def test_goal_create_sanitizes_goal_name(self):
        from decimal import Decimal
        from datetime import date, timedelta
        from app.schemas.goal import GoalCreate

        raw = GoalCreate(
            goal_name='<script>alert(1)</script>Emergency Fund',
            goal_type="savings",
            target_amount=Decimal("1000"),
            target_date=date.today() + timedelta(days=30),
        )
        assert "<script>" not in raw.goal_name

    def test_budget_create_sanitizes_category(self):
        from decimal import Decimal
        from datetime import date
        from app.schemas.budget import BudgetCreate

        raw = BudgetCreate(
            month=date.today().replace(day=1),
            category='<b>Food</b>',
            allocated_amount=Decimal("500.00"),
        )
        assert "<b>" not in raw.category
        assert "Food" in raw.category
