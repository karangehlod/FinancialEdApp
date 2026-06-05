"""Unit tests for app.services.loan_validators module."""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from app.services.loan_validators import (
    LoanAmountValidator,
    InterestRateValidator,
    LoanTermValidator,
    LoanValidator,
    DateValidator,
)


class TestLoanAmountValidator:
    """Test LoanAmountValidator class."""

    def test_validate_valid_min_amount(self):
        """Test validation with minimum allowed amount."""
        is_valid, error = LoanAmountValidator.validate(Decimal('1000'))
        assert is_valid is True
        assert error == ""

    def test_validate_valid_max_amount(self):
        """Test validation with maximum allowed amount."""
        is_valid, error = LoanAmountValidator.validate(Decimal('10000000'))
        assert is_valid is True
        assert error == ""

    def test_validate_valid_middle_amount(self):
        """Test validation with amount between min and max."""
        is_valid, error = LoanAmountValidator.validate(Decimal('500000'))
        assert is_valid is True
        assert error == ""

    def test_validate_below_minimum_amount(self):
        """Test validation with amount below minimum."""
        is_valid, error = LoanAmountValidator.validate(Decimal('500'))
        assert is_valid is False
        assert "at least 1000" in error

    def test_validate_above_maximum_amount(self):
        """Test validation with amount above maximum."""
        is_valid, error = LoanAmountValidator.validate(Decimal('10000001'))
        assert is_valid is False
        assert "cannot exceed 10000000" in error

    def test_validate_zero_amount(self):
        """Test validation with zero amount."""
        is_valid, error = LoanAmountValidator.validate(Decimal('0'))
        assert is_valid is False

    def test_validate_negative_amount(self):
        """Test validation with negative amount."""
        is_valid, error = LoanAmountValidator.validate(Decimal('-1000'))
        assert is_valid is False

    def test_is_valid_true(self):
        """Test is_valid method with valid amount."""
        assert LoanAmountValidator.is_valid(Decimal('100000')) is True

    def test_is_valid_false_below_min(self):
        """Test is_valid method with amount below minimum."""
        assert LoanAmountValidator.is_valid(Decimal('500')) is False

    def test_is_valid_false_above_max(self):
        """Test is_valid method with amount above maximum."""
        assert LoanAmountValidator.is_valid(Decimal('10000001')) is False

    def test_validate_boundary_just_below_min(self):
        """Test validation with amount just below minimum."""
        is_valid, error = LoanAmountValidator.validate(Decimal('999.99'))
        assert is_valid is False

    def test_validate_boundary_just_above_max(self):
        """Test validation with amount just above maximum."""
        is_valid, error = LoanAmountValidator.validate(Decimal('10000000.01'))
        assert is_valid is False


class TestInterestRateValidator:
    """Test InterestRateValidator class."""

    def test_validate_valid_zero_rate(self):
        """Test validation with zero interest rate."""
        is_valid, error = InterestRateValidator.validate(Decimal('0'))
        assert is_valid is True
        assert error == ""

    def test_validate_valid_max_rate(self):
        """Test validation with maximum allowed rate."""
        is_valid, error = InterestRateValidator.validate(Decimal('30'))
        assert is_valid is True
        assert error == ""

    def test_validate_valid_middle_rate(self):
        """Test validation with rate between min and max."""
        is_valid, error = InterestRateValidator.validate(Decimal('5.5'))
        assert is_valid is True
        assert error == ""

    def test_validate_negative_rate(self):
        """Test validation with negative interest rate."""
        is_valid, error = InterestRateValidator.validate(Decimal('-0.1'))
        assert is_valid is False
        assert "cannot be negative" in error

    def test_validate_above_maximum_rate(self):
        """Test validation with rate above maximum."""
        is_valid, error = InterestRateValidator.validate(Decimal('30.1'))
        assert is_valid is False
        assert "cannot exceed 30" in error

    def test_validate_high_negative_rate(self):
        """Test validation with very negative rate."""
        is_valid, error = InterestRateValidator.validate(Decimal('-100'))
        assert is_valid is False

    def test_validate_very_high_rate(self):
        """Test validation with very high rate."""
        is_valid, error = InterestRateValidator.validate(Decimal('100'))
        assert is_valid is False

    def test_is_valid_true(self):
        """Test is_valid method with valid rate."""
        assert InterestRateValidator.is_valid(Decimal('12.5')) is True

    def test_is_valid_false_negative(self):
        """Test is_valid method with negative rate."""
        assert InterestRateValidator.is_valid(Decimal('-1')) is False

    def test_is_valid_false_above_max(self):
        """Test is_valid method with rate above maximum."""
        assert InterestRateValidator.is_valid(Decimal('35')) is False

    def test_validate_boundary_just_above_max(self):
        """Test validation with rate just above maximum."""
        is_valid, error = InterestRateValidator.validate(Decimal('30.01'))
        assert is_valid is False

    def test_validate_decimal_precision(self):
        """Test validation with high decimal precision."""
        is_valid, error = InterestRateValidator.validate(Decimal('15.123456'))
        assert is_valid is True


class TestLoanTermValidator:
    """Test LoanTermValidator class."""

    def test_validate_valid_min_term(self):
        """Test validation with minimum allowed term."""
        is_valid, error = LoanTermValidator.validate(6)
        assert is_valid is True
        assert error == ""

    def test_validate_valid_max_term(self):
        """Test validation with maximum allowed term."""
        is_valid, error = LoanTermValidator.validate(360)
        assert is_valid is True
        assert error == ""

    def test_validate_valid_middle_term(self):
        """Test validation with term between min and max."""
        is_valid, error = LoanTermValidator.validate(180)
        assert is_valid is True
        assert error == ""

    def test_validate_below_minimum_term(self):
        """Test validation with term below minimum."""
        is_valid, error = LoanTermValidator.validate(3)
        assert is_valid is False
        assert "at least 6 months" in error

    def test_validate_above_maximum_term(self):
        """Test validation with term above maximum."""
        is_valid, error = LoanTermValidator.validate(361)
        assert is_valid is False
        assert "cannot exceed 360 months" in error

    def test_validate_zero_term(self):
        """Test validation with zero term."""
        is_valid, error = LoanTermValidator.validate(0)
        assert is_valid is False

    def test_validate_negative_term(self):
        """Test validation with negative term."""
        is_valid, error = LoanTermValidator.validate(-12)
        assert is_valid is False

    def test_is_valid_true(self):
        """Test is_valid method with valid term."""
        assert LoanTermValidator.is_valid(24) is True

    def test_is_valid_false_below_min(self):
        """Test is_valid method with term below minimum."""
        assert LoanTermValidator.is_valid(3) is False

    def test_is_valid_false_above_max(self):
        """Test is_valid method with term above maximum."""
        assert LoanTermValidator.is_valid(361) is False

    def test_validate_boundary_just_below_min(self):
        """Test validation with term just below minimum."""
        is_valid, error = LoanTermValidator.validate(5)
        assert is_valid is False

    def test_validate_boundary_just_above_max(self):
        """Test validation with term just above maximum."""
        is_valid, error = LoanTermValidator.validate(361)
        assert is_valid is False


class TestLoanValidator:
    """Test composite LoanValidator class."""

    def test_validate_all_valid(self):
        """Test validation with all valid parameters."""
        is_valid, errors = LoanValidator.validate_all(
            Decimal('100000'),
            Decimal('5.5'),
            60
        )
        assert is_valid is True
        assert errors == []

    def test_validate_all_minimum_values(self):
        """Test validation with minimum allowed values."""
        is_valid, errors = LoanValidator.validate_all(
            Decimal('1000'),
            Decimal('0'),
            6
        )
        assert is_valid is True
        assert errors == []

    def test_validate_all_maximum_values(self):
        """Test validation with maximum allowed values."""
        is_valid, errors = LoanValidator.validate_all(
            Decimal('10000000'),
            Decimal('30'),
            360
        )
        assert is_valid is True
        assert errors == []

    def test_validate_all_invalid_amount(self):
        """Test validation with invalid amount."""
        is_valid, errors = LoanValidator.validate_all(
            Decimal('500'),  # Below minimum
            Decimal('5'),
            60
        )
        assert is_valid is False
        assert len(errors) == 1
        assert "amount" in errors[0].lower()

    def test_validate_all_invalid_rate(self):
        """Test validation with invalid rate."""
        is_valid, errors = LoanValidator.validate_all(
            Decimal('100000'),
            Decimal('35'),  # Above maximum
            60
        )
        assert is_valid is False
        assert len(errors) == 1
        assert "rate" in errors[0].lower()

    def test_validate_all_invalid_term(self):
        """Test validation with invalid term."""
        is_valid, errors = LoanValidator.validate_all(
            Decimal('100000'),
            Decimal('5'),
            400  # Above maximum
        )
        assert is_valid is False
        assert len(errors) == 1
        assert "term" in errors[0].lower()

    def test_validate_all_multiple_invalid(self):
        """Test validation with multiple invalid parameters."""
        is_valid, errors = LoanValidator.validate_all(
            Decimal('500'),  # Invalid
            Decimal('35'),  # Invalid
            400  # Invalid
        )
        assert is_valid is False
        assert len(errors) == 3

    def test_validate_all_amount_and_rate_invalid(self):
        """Test validation with invalid amount and rate."""
        is_valid, errors = LoanValidator.validate_all(
            Decimal('-1000'),
            Decimal('-5'),
            60
        )
        assert is_valid is False
        assert len(errors) == 2

    def test_validate_all_amount_and_term_invalid(self):
        """Test validation with invalid amount and term."""
        is_valid, errors = LoanValidator.validate_all(
            Decimal('10000001'),
            Decimal('5'),
            -12
        )
        assert is_valid is False
        assert len(errors) == 2

    def test_validate_all_rate_and_term_invalid(self):
        """Test validation with invalid rate and term."""
        is_valid, errors = LoanValidator.validate_all(
            Decimal('100000'),
            Decimal('40'),
            500
        )
        assert is_valid is False
        assert len(errors) == 2

    def test_validate_all_errors_list_order(self):
        """Test that errors are collected in consistent order."""
        is_valid, errors = LoanValidator.validate_all(
            Decimal('500'),  # Amount error
            Decimal('35'),   # Rate error
            400              # Term error
        )
        assert is_valid is False
        assert len(errors) == 3
        # Errors should be collected in order: amount, rate, term


class TestDateValidator:
    """Test DateValidator class."""

    def test_validate_start_date_today(self):
        """Test start date validation with today's date."""
        today = date.today()
        is_valid, error = DateValidator.validate_start_date(today)
        assert is_valid is True
        assert error == ""

    def test_validate_start_date_past(self):
        """Test start date validation with past date."""
        past_date = date.today() - timedelta(days=30)
        is_valid, error = DateValidator.validate_start_date(past_date)
        assert is_valid is True
        assert error == ""

    def test_validate_start_date_future(self):
        """Test start date validation with future date."""
        future_date = date.today() + timedelta(days=1)
        is_valid, error = DateValidator.validate_start_date(future_date)
        assert is_valid is False
        assert "cannot be in the future" in error

    def test_validate_start_date_far_future(self):
        """Test start date validation with far future date."""
        far_future = date.today() + timedelta(days=365)
        is_valid, error = DateValidator.validate_start_date(far_future)
        assert is_valid is False

    def test_validate_start_date_distant_past(self):
        """Test start date validation with distant past date."""
        distant_past = date.today() - timedelta(days=365*5)
        is_valid, error = DateValidator.validate_start_date(distant_past)
        assert is_valid is True

    def test_validate_payment_date_same_as_start(self):
        """Test payment date validation when equal to start date."""
        start_date = date.today()
        payment_date = start_date
        is_valid, error = DateValidator.validate_payment_date(start_date, payment_date)
        assert is_valid is True
        assert error == ""

    def test_validate_payment_date_after_start(self):
        """Test payment date validation after start date."""
        start_date = date.today()
        payment_date = date.today() + timedelta(days=30)
        is_valid, error = DateValidator.validate_payment_date(start_date, payment_date)
        assert is_valid is True
        assert error == ""

    def test_validate_payment_date_before_start(self):
        """Test payment date validation before start date."""
        start_date = date.today()
        payment_date = date.today() - timedelta(days=1)
        is_valid, error = DateValidator.validate_payment_date(start_date, payment_date)
        assert is_valid is False
        assert "cannot be before" in error

    def test_validate_payment_date_far_before_start(self):
        """Test payment date validation far before start date."""
        start_date = date(2025, 1, 1)
        payment_date = date(2020, 1, 1)
        is_valid, error = DateValidator.validate_payment_date(start_date, payment_date)
        assert is_valid is False

    def test_validate_payment_date_far_after_start(self):
        """Test payment date validation far after start date."""
        start_date = date.today()
        payment_date = start_date + timedelta(days=365*5)
        is_valid, error = DateValidator.validate_payment_date(start_date, payment_date)
        assert is_valid is True

    def test_validate_due_date_future(self):
        """Test due date validation with future date."""
        future_date = date.today() + timedelta(days=30)
        is_valid, error = DateValidator.validate_due_date(future_date)
        assert is_valid is True
        assert error == ""

    def test_validate_due_date_today(self):
        """Test due date validation with today's date."""
        today = date.today()
        is_valid, error = DateValidator.validate_due_date(today)
        assert is_valid is True
        assert error == ""

    def test_validate_due_date_past(self):
        """Test due date validation with past date."""
        past_date = date.today() - timedelta(days=1)
        is_valid, error = DateValidator.validate_due_date(past_date)
        assert is_valid is False
        assert "cannot be in the past" in error

    def test_validate_due_date_far_past(self):
        """Test due date validation with far past date."""
        far_past = date.today() - timedelta(days=365)
        is_valid, error = DateValidator.validate_due_date(far_past)
        assert is_valid is False

    def test_validate_due_date_far_future(self):
        """Test due date validation with far future date."""
        far_future = date.today() + timedelta(days=365*10)
        is_valid, error = DateValidator.validate_due_date(far_future)
        assert is_valid is True

    def test_validate_payment_date_sequence(self):
        """Test payment date in realistic loan sequence."""
        start_date = date(2025, 1, 1)
        # First payment
        payment_date_1 = date(2025, 2, 1)
        is_valid, error = DateValidator.validate_payment_date(start_date, payment_date_1)
        assert is_valid is True
        
        # Second payment (after first)
        payment_date_2 = date(2025, 3, 1)
        is_valid, error = DateValidator.validate_payment_date(start_date, payment_date_2)
        assert is_valid is True

    def test_validate_due_date_vs_today_boundary(self):
        """Test due date at boundary with today."""
        today = date.today()
        is_valid, error = DateValidator.validate_due_date(today)
        assert is_valid is True
        
        yesterday = today - timedelta(days=1)
        is_valid, error = DateValidator.validate_due_date(yesterday)
        assert is_valid is False
