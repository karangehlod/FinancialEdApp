"""
Tests for input sanitization utilities (P1-9).

Covers:
  - HTML stripping
  - Null byte / control character removal
  - Merchant character allowlist
  - Max length enforcement
  - Unicode normalisation
  - Edge cases: None, empty string, plain text (unchanged)
"""

import pytest
from app.core.sanitization import (
    sanitize_text,
    sanitize_merchant,
    sanitize_name,
    sanitize_notes,
    validate_max_length,
)


# ---------------------------------------------------------------------------
# sanitize_text
# ---------------------------------------------------------------------------

class TestSanitizeText:
    def test_plain_text_unchanged(self):
        assert sanitize_text("hello world") == "hello world"

    def test_strips_html_tags(self):
        result = sanitize_text("<script>alert('xss')</script>buy now!")
        assert "<script>" not in result
        assert "buy now!" in result

    def test_strips_html_anchor(self):
        result = sanitize_text('<a href="http://evil.com">click</a>')
        assert "<a" not in result
        assert "click" in result

    def test_removes_null_bytes(self):
        result = sanitize_text("hello\x00world")
        assert "\x00" not in result
        assert "helloworld" in result

    def test_removes_control_chars(self):
        result = sanitize_text("hello\x01\x02\x1fworld")
        assert "\x01" not in result
        assert "\x1f" not in result
        assert "hello" in result and "world" in result

    def test_truncates_to_max_length(self):
        long_text = "a" * 2000
        result = sanitize_text(long_text, max_length=100)
        assert len(result) == 100

    def test_strips_whitespace(self):
        result = sanitize_text("  hello  ")
        assert result == "hello"

    def test_empty_string(self):
        assert sanitize_text("") == ""

    def test_unicode_normalised(self):
        # NFC normalisation: combining characters → precomposed
        # é (e + combining accent) → é (precomposed)
        combining = "e\u0301"  # e + combining acute
        result = sanitize_text(combining)
        assert result == "\xe9"  # precomposed é

    def test_nested_html(self):
        result = sanitize_text("<div><p><b>text</b></p></div>")
        assert "<" not in result
        assert "text" in result


# ---------------------------------------------------------------------------
# sanitize_merchant
# ---------------------------------------------------------------------------

class TestSanitizeMerchant:
    def test_plain_merchant_unchanged(self):
        assert sanitize_merchant("Starbucks Coffee") == "Starbucks Coffee"

    def test_strips_html(self):
        result = sanitize_merchant("<b>Amazon</b>")
        assert "<b>" not in result
        assert "Amazon" in result

    def test_removes_script_injection(self):
        result = sanitize_merchant("<script>evil()</script>Shop")
        assert "script" not in result.lower()
        assert "Shop" in result

    def test_removes_disallowed_chars(self):
        # Backtick, semicolon are not in the allowlist
        result = sanitize_merchant("Shop`; DROP TABLE")
        assert "`" not in result
        assert ";" not in result

    def test_allows_common_chars(self):
        name = "McDonald's & Co. (Outlet #1)"
        result = sanitize_merchant(name)
        # All these chars should survive
        assert "McDonald" in result
        assert "&" in result
        assert "." in result

    def test_truncates_to_200_chars(self):
        long = "A" * 300
        result = sanitize_merchant(long)
        assert len(result) <= 200

    def test_none_returns_none(self):
        assert sanitize_merchant(None) is None

    def test_empty_string_returns_none(self):
        # Empty after stripping returns None
        result = sanitize_merchant("   ")
        assert result is None


# ---------------------------------------------------------------------------
# sanitize_name
# ---------------------------------------------------------------------------

class TestSanitizeName:
    def test_plain_name_unchanged(self):
        assert sanitize_name("John Doe") == "John Doe"

    def test_strips_html_from_name(self):
        result = sanitize_name("<script>evil</script>Alice")
        assert "<" not in result

    def test_allows_accented_chars(self):
        result = sanitize_name("José García")
        assert "José" in result or "Jos" in result  # depending on normalisation

    def test_none_returns_none(self):
        assert sanitize_name(None) is None


# ---------------------------------------------------------------------------
# sanitize_notes
# ---------------------------------------------------------------------------

class TestSanitizeNotes:
    def test_long_notes_allowed(self):
        notes = "This is a detailed note. " * 50  # 1250 chars
        result = sanitize_notes(notes)
        assert len(result) <= 2000

    def test_strips_html_from_notes(self):
        result = sanitize_notes("<img src=x onerror=alert(1)>normal text")
        assert "<img" not in result
        assert "normal text" in result

    def test_none_returns_none(self):
        assert sanitize_notes(None) is None


# ---------------------------------------------------------------------------
# validate_max_length
# ---------------------------------------------------------------------------

class TestValidateMaxLength:
    def test_within_limit_passes(self):
        result = validate_max_length("hello", 10, "field")
        assert result == "hello"

    def test_exceeds_limit_raises(self):
        with pytest.raises(ValueError, match="must not exceed"):
            validate_max_length("a" * 101, 100, "description")

    def test_none_passes(self):
        assert validate_max_length(None, 50, "field") is None

    def test_exactly_at_limit_passes(self):
        value = "a" * 100
        result = validate_max_length(value, 100, "field")
        assert result == value


# ---------------------------------------------------------------------------
# Integration: ExpenseCreate schema uses sanitization validators
# ---------------------------------------------------------------------------

class TestExpenseSchemaValidation:
    def test_merchant_with_html_is_sanitized(self):
        from app.schemas.expense import ExpenseCreate
        from decimal import Decimal
        from datetime import date

        expense = ExpenseCreate(
            amount=Decimal("10.00"),
            category="food",
            date=date.today(),
            merchant="<b>McDonald's</b>",
        )
        # HTML should be stripped
        assert "<b>" not in (expense.merchant or "")
        assert "McDonald" in (expense.merchant or "")

    def test_description_with_script_is_sanitized(self):
        from app.schemas.expense import ExpenseCreate
        from decimal import Decimal
        from datetime import date

        expense = ExpenseCreate(
            amount=Decimal("5.00"),
            category="food",
            date=date.today(),
            description="<script>alert('xss')</script>Lunch",
        )
        assert "<script>" not in (expense.description or "")
        assert "Lunch" in (expense.description or "")
