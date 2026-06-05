"""Comprehensive tests for loan calculators and validators."""

import pytest
from decimal import Decimal
from datetime import date, datetime, timedelta
import math

from app.services.loan_calculators import (
    EMICalculator, InterestCalculator, PrepaymentCalculator
)
from app.services.loan_validators import (
    LoanAmountValidator, InterestRateValidator, LoanTermValidator,
    LoanValidator, DateValidator
)
from app.services.loan_domain import (
    Money, InterestRate, LoanTerm, DueDate, PaymentAllocation,
    LoanScheduleItem, LoanStatusEnum, LoanState, LoanPayment,
    EMIImpactAnalysis, PrepaymentAnalysis
)


# ============== EMI CALCULATOR TESTS ==============

class TestEMICalculator:
    """Test EMICalculator."""
    
    def test_calculate_emi_basic(self):
        """Test basic EMI calculation."""
        principal = Decimal("100000")
        annual_rate = Decimal("8.5")
        months = 60
        
        emi = EMICalculator.calculate_emi(principal, annual_rate, months)
        
        assert emi > 0
        assert isinstance(emi, Decimal)
        # EMI should be roughly 2000-3000 for these params
        assert Decimal("1800") < emi < Decimal("3000")
    
    def test_calculate_emi_zero_interest(self):
        """Test EMI with zero interest."""
        principal = Decimal("100000")
        annual_rate = Decimal("0")
        months = 60
        
        emi = EMICalculator.calculate_emi(principal, annual_rate, months)
        
        # With 0% interest, EMI should be principal / months (rounded to 2 decimals)
        expected = Decimal("1666.67")  # 100000 / 60 rounded
        assert emi == expected
    
    def test_calculate_emi_zero_months(self):
        """Test EMI with zero months."""
        principal = Decimal("100000")
        annual_rate = Decimal("8.5")
        months = 0
        
        emi = EMICalculator.calculate_emi(principal, annual_rate, months)
        
        assert emi == Decimal("0")
    
    def test_calculate_emi_high_rate(self):
        """Test EMI with high interest rate."""
        principal = Decimal("50000")
        annual_rate = Decimal("20")
        months = 24
        
        emi = EMICalculator.calculate_emi(principal, annual_rate, months)
        
        assert emi > 0
        assert isinstance(emi, Decimal)
    
    def test_calculate_total_interest(self):
        """Test total interest calculation."""
        principal = Decimal("100000")
        annual_rate = Decimal("8.5")
        months = 60
        
        total_interest = EMICalculator.calculate_total_interest(principal, annual_rate, months)
        
        assert total_interest > 0
        assert isinstance(total_interest, Decimal)
    
    def test_calculate_total_interest_zero_rate(self):
        """Test total interest with zero rate."""
        principal = Decimal("100000")
        annual_rate = Decimal("0")
        months = 60
        
        total_interest = EMICalculator.calculate_total_interest(principal, annual_rate, months)
        
        # With 0% interest, total interest should be very close to 0 (rounding artifact)
        assert total_interest <= Decimal("0.50")  # Allow for rounding artifacts
    
    def test_calculate_tenure_from_emi(self):
        """Test tenure calculation from EMI."""
        principal = Decimal("100000")
        annual_rate = Decimal("8.5")
        current_emi = Decimal("2500")
        
        tenure = EMICalculator.calculate_tenure_from_emi(principal, annual_rate, current_emi)
        
        assert tenure > 0
        assert isinstance(tenure, int)
    
    def test_calculate_tenure_from_emi_zero_interest(self):
        """Test tenure calculation with zero interest."""
        principal = Decimal("100000")
        annual_rate = Decimal("0")
        current_emi = Decimal("2000")
        
        tenure = EMICalculator.calculate_tenure_from_emi(principal, annual_rate, current_emi)
        
        assert tenure == 50
    
    def test_calculate_tenure_from_emi_insufficient_emi(self):
        """Test tenure calculation with EMI too low to cover interest."""
        principal = Decimal("100000")
        annual_rate = Decimal("20")  # Very high rate
        current_emi = Decimal("100")  # Too low
        
        tenure = EMICalculator.calculate_tenure_from_emi(principal, annual_rate, current_emi)
        
        # EMI insufficient to cover interest - should return 0
        assert tenure == 0
    
    def test_calculate_tenure_from_emi_edge_case_exception(self):
        """Test tenure calculation exception handling (very negative case)."""
        # This tests the exception handling in calculate_tenure_from_emi
        # Edge case where computation might fail
        principal = Decimal("1")
        annual_rate = Decimal("0.01")
        current_emi = Decimal("0.001")  # Very small EMI
        
        # This might trigger exception due to math domain issues
        tenure = EMICalculator.calculate_tenure_from_emi(principal, annual_rate, current_emi)
        
        # Should either return valid tenure or 0 if exception occurs
        assert tenure >= 0
    
    def test_calculate_interest_portion(self):
        """Test monthly interest calculation."""
        balance = Decimal("50000")
        annual_rate = Decimal("8.5")
        
        interest = EMICalculator.calculate_interest_portion(balance, annual_rate)
        
        assert interest > 0
        assert isinstance(interest, Decimal)
    
    def test_calculate_principal_portion(self):
        """Test principal portion calculation."""
        emi = Decimal("2500")
        interest = Decimal("400")
        
        principal = EMICalculator.calculate_principal_portion(emi, interest)
        
        assert principal == Decimal("2100")
    
    def test_calculate_principal_portion_negative(self):
        """Test principal portion with interest exceeding EMI."""
        emi = Decimal("1000")
        interest = Decimal("1500")  # Interest > EMI
        
        principal = EMICalculator.calculate_principal_portion(emi, interest)
        
        # Should return 0 (clamped)
        assert principal == Decimal("0")


# ============== INTEREST CALCULATOR TESTS ==============

class TestInterestCalculator:
    """Test InterestCalculator."""
    
    def test_calculate_remaining_interest(self):
        """Test remaining interest calculation."""
        balance = Decimal("50000")
        annual_rate = Decimal("8.5")
        emi = Decimal("2000")
        remaining_months = 24
        
        interest = InterestCalculator.calculate_remaining_interest(
            balance, annual_rate, emi, remaining_months
        )
        
        assert interest > 0
        assert isinstance(interest, Decimal)
    
    def test_calculate_remaining_interest_zero_months(self):
        """Test remaining interest with zero months."""
        balance = Decimal("50000")
        annual_rate = Decimal("8.5")
        emi = Decimal("2000")
        remaining_months = 0
        
        interest = InterestCalculator.calculate_remaining_interest(
            balance, annual_rate, emi, remaining_months
        )
        
        assert interest == Decimal("0")
    
    def test_calculate_weighted_average_rate(self):
        """Test weighted average interest rate calculation."""
        balances = [Decimal("50000"), Decimal("100000")]
        rates = [Decimal("8.5"), Decimal("10.5")]
        
        avg_rate = InterestCalculator.calculate_weighted_average_rate(balances, rates)
        
        # Should be weighted towards the 100k loan
        assert avg_rate > Decimal("8.5")
        assert avg_rate < Decimal("10.5")
    
    def test_calculate_weighted_average_rate_empty(self):
        """Test weighted average with no loans."""
        balances = []
        rates = []
        
        avg_rate = InterestCalculator.calculate_weighted_average_rate(balances, rates)
        
        assert avg_rate == Decimal("0")


# ============== PREPAYMENT CALCULATOR TESTS ==============

class TestPrepaymentCalculator:
    """Test PrepaymentCalculator."""
    
    def test_calculate_prepayment_impact_partial(self):
        """Test prepayment impact with partial prepayment."""
        balance = Decimal("50000")
        prepayment = Decimal("10000")
        annual_rate = Decimal("8.5")
        emi = Decimal("2000")
        remaining_months = 24
        
        impact = PrepaymentCalculator.calculate_prepayment_impact(
            balance, prepayment, annual_rate, emi, remaining_months
        )
        
        assert impact['new_outstanding_balance'] == Decimal("40000")
        assert impact['tenure_reduction_months'] >= 0
        assert impact['interest_savings'] >= 0
    
    def test_calculate_prepayment_impact_full(self):
        """Test prepayment that pays off entire loan."""
        balance = Decimal("10000")
        prepayment = Decimal("15000")
        annual_rate = Decimal("8.5")
        emi = Decimal("2000")
        remaining_months = 5
        
        impact = PrepaymentCalculator.calculate_prepayment_impact(
            balance, prepayment, annual_rate, emi, remaining_months
        )
        
        assert impact['new_outstanding_balance'] == Decimal("0")
        assert impact['savings_percentage'] == Decimal("100")
    
    def test_calculate_emi_change_impact(self):
        """Test EMI change impact."""
        principal = Decimal("100000")
        annual_rate = Decimal("8.5")
        original_tenure = 60
        new_emi = Decimal("3000")
        
        impact = PrepaymentCalculator.calculate_emi_change_impact(
            principal, annual_rate, original_tenure, new_emi
        )
        
        assert 'original_emi' in impact
        assert 'new_emi' in impact
        assert 'tenure_reduction_months' in impact
        assert 'interest_savings' in impact


# ============== LOAN AMOUNT VALIDATOR TESTS ==============

class TestLoanAmountValidator:
    """Test LoanAmountValidator."""
    
    def test_validate_valid_amount(self):
        """Test valid loan amount."""
        valid, msg = LoanAmountValidator.validate(Decimal("50000"))
        assert valid is True
        assert msg == ""
    
    def test_validate_minimum_boundary(self):
        """Test minimum boundary."""
        valid, msg = LoanAmountValidator.validate(Decimal("1000"))
        assert valid is True
    
    def test_validate_below_minimum(self):
        """Test below minimum."""
        valid, msg = LoanAmountValidator.validate(Decimal("500"))
        assert valid is False
        assert "at least" in msg
    
    def test_validate_maximum_boundary(self):
        """Test maximum boundary."""
        valid, msg = LoanAmountValidator.validate(Decimal("10000000"))
        assert valid is True
    
    def test_validate_above_maximum(self):
        """Test above maximum."""
        valid, msg = LoanAmountValidator.validate(Decimal("20000000"))
        assert valid is False
        assert "cannot exceed" in msg
    
    def test_is_valid_shortcut(self):
        """Test is_valid method."""
        assert LoanAmountValidator.is_valid(Decimal("50000")) is True
        assert LoanAmountValidator.is_valid(Decimal("500")) is False


# ============== INTEREST RATE VALIDATOR TESTS ==============

class TestInterestRateValidator:
    """Test InterestRateValidator."""
    
    def test_validate_valid_rate(self):
        """Test valid interest rate."""
        valid, msg = InterestRateValidator.validate(Decimal("8.5"))
        assert valid is True
        assert msg == ""
    
    def test_validate_zero_rate(self):
        """Test zero interest rate."""
        valid, msg = InterestRateValidator.validate(Decimal("0"))
        assert valid is True
    
    def test_validate_maximum_rate(self):
        """Test maximum rate."""
        valid, msg = InterestRateValidator.validate(Decimal("30"))
        assert valid is True
    
    def test_validate_negative_rate(self):
        """Test negative rate."""
        valid, msg = InterestRateValidator.validate(Decimal("-1"))
        assert valid is False
        assert "negative" in msg
    
    def test_validate_above_maximum_rate(self):
        """Test above maximum rate."""
        valid, msg = InterestRateValidator.validate(Decimal("35"))
        assert valid is False
        assert "cannot exceed" in msg

# Additional tests for is_valid shortcut methods

class TestInterestRateValidatorIsValid:
    """Test is_valid shortcut methods."""
    
    def test_interest_rate_is_valid_within_bounds(self):
        """Test is_valid for valid interest rate."""
        assert InterestRateValidator.is_valid(Decimal("8.5")) is True
        assert InterestRateValidator.is_valid(Decimal("0")) is True
        assert InterestRateValidator.is_valid(Decimal("30")) is True
    
    def test_interest_rate_is_valid_outside_bounds(self):
        """Test is_valid for invalid interest rate."""
        assert InterestRateValidator.is_valid(Decimal("-1")) is False
        assert InterestRateValidator.is_valid(Decimal("31")) is False


# ============== LOAN TERM VALIDATOR TESTS ==============

class TestLoanTermValidator:
    """Test LoanTermValidator."""
    
    def test_validate_valid_term(self):
        """Test valid loan term."""
        valid, msg = LoanTermValidator.validate(60)
        assert valid is True
        assert msg == ""
    
    def test_validate_minimum_term(self):
        """Test minimum term."""
        valid, msg = LoanTermValidator.validate(6)
        assert valid is True
    
    def test_validate_below_minimum_term(self):
        """Test below minimum term."""
        valid, msg = LoanTermValidator.validate(3)
        assert valid is False
        assert "at least" in msg
    
    def test_validate_maximum_term(self):
        """Test maximum term (30 years)."""
        valid, msg = LoanTermValidator.validate(360)
        assert valid is True
    
    def test_validate_above_maximum_term(self):
        """Test above maximum term."""
        valid, msg = LoanTermValidator.validate(400)
        assert valid is False
        assert "cannot exceed" in msg

class TestLoanTermValidatorIsValid:
    """Test LoanTermValidator is_valid."""
    
    def test_loan_term_is_valid_within_bounds(self):
        """Test is_valid for valid loan term."""
        assert LoanTermValidator.is_valid(6) is True
        assert LoanTermValidator.is_valid(180) is True
        assert LoanTermValidator.is_valid(360) is True
    
    def test_loan_term_is_valid_outside_bounds(self):
        """Test is_valid for invalid loan term."""
        assert LoanTermValidator.is_valid(5) is False
        assert LoanTermValidator.is_valid(361) is False


# ============== COMPOSITE LOAN VALIDATOR TESTS ==============

class TestLoanValidator:
    """Test composite LoanValidator."""
    
    def test_validate_all_valid(self):
        """Test validation of all valid parameters."""
        valid, errors = LoanValidator.validate_all(
            principal=Decimal("100000"),
            interest_rate=Decimal("8.5"),
            term_months=60
        )
        
        assert valid is True
        assert len(errors) == 0
    
    def test_validate_all_invalid_amount(self):
        """Test validation with invalid amount."""
        valid, errors = LoanValidator.validate_all(
            principal=Decimal("500"),  # Too low
            interest_rate=Decimal("8.5"),
            term_months=60
        )
        
        assert valid is False
        assert len(errors) > 0
    
    def test_validate_all_multiple_errors(self):
        """Test validation with multiple errors."""
        valid, errors = LoanValidator.validate_all(
            principal=Decimal("500"),  # Too low
            interest_rate=Decimal("35"),  # Too high
            term_months=3  # Too low
        )
        
        assert valid is False
        assert len(errors) == 3


# ============== DATE VALIDATOR TESTS ==============

class TestDateValidator:
    """Test DateValidator."""
    
    def test_validate_start_date_today(self):
        """Test start date as today."""
        valid, msg = DateValidator.validate_start_date(date.today())
        assert valid is True
    
    def test_validate_start_date_future(self):
        """Test start date in future."""
        future_date = date.today() + timedelta(days=1)
        valid, msg = DateValidator.validate_start_date(future_date)
        assert valid is False
        assert "future" in msg
    
    def test_validate_payment_date_valid(self):
        """Test valid payment date."""
        start_date = date(2023, 1, 1)
        payment_date = date(2023, 6, 1)
        
        valid, msg = DateValidator.validate_payment_date(start_date, payment_date)
        assert valid is True
    
    def test_validate_payment_date_before_start(self):
        """Test payment date before start date."""
        start_date = date(2023, 6, 1)
        payment_date = date(2023, 1, 1)
        
        valid, msg = DateValidator.validate_payment_date(start_date, payment_date)
        assert valid is False
    
    def test_validate_due_date_future(self):
        """Test valid due date in future."""
        future_date = date.today() + timedelta(days=5)
        valid, msg = DateValidator.validate_due_date(future_date)
        assert valid is True
    
    def test_validate_due_date_past(self):
        """Test due date in the past."""
        past_date = date.today() - timedelta(days=1)
        valid, msg = DateValidator.validate_due_date(past_date)
        assert valid is False
        assert "past" in msg


# ============== VALUE OBJECTS TESTS ==============

class TestMoney:
    """Test Money value object."""
    
    def test_create_money_valid(self):
        """Test creating valid Money."""
        money = Money(Decimal("100.50"))
        assert money.amount == Decimal("100.50")
    
    def test_create_money_negative(self):
        """Test creating Money with negative amount."""
        with pytest.raises(ValueError):
            Money(Decimal("-50"))
    
    def test_money_addition(self):
        """Test Money addition."""
        m1 = Money(Decimal("100"))
        m2 = Money(Decimal("50"))
        
        result = m1 + m2
        
        assert result.amount == Decimal("150")
    
    def test_money_subtraction(self):
        """Test Money subtraction."""
        m1 = Money(Decimal("100"))
        m2 = Money(Decimal("30"))
        
        result = m1 - m2
        
        assert result.amount == Decimal("70")
    
    def test_money_subtraction_negative_result(self):
        """Test Money subtraction resulting in negative."""
        m1 = Money(Decimal("30"))
        m2 = Money(Decimal("50"))
        
        with pytest.raises(ValueError):
            m1 - m2
    
    def test_money_multiplication(self):
        """Test Money multiplication."""
        money = Money(Decimal("100"))
        result = money * 1.5
        
        assert result.amount == Decimal("150")
    
    def test_money_equality(self):
        """Test Money equality."""
        m1 = Money(Decimal("100"))
        m2 = Money(Decimal("100"))
        
        assert m1 == m2
    
    def test_money_comparison(self):
        """Test Money comparison."""
        m1 = Money(Decimal("100"))
        m2 = Money(Decimal("50"))
        
        assert m1 > m2
        assert m1 >= m2
        assert m2 < m1
        assert m2 <= m1
    
    def test_money_comparison_type_error_add(self):
        """Test Money addition with non-Money type."""
        money = Money(Decimal("100"))
        
        with pytest.raises(TypeError):
            money + 50
    
    def test_money_subtraction_type_error(self):
        """Test Money subtraction with non-Money type."""
        money = Money(Decimal("100"))
        
        with pytest.raises(TypeError):
            money - 50
    
    def test_money_less_than_type_error(self):
        """Test Money < comparison with non-Money type."""
        money = Money(Decimal("100"))
        
        with pytest.raises(TypeError):
            money < 50
    
    def test_money_greater_than_type_error(self):
        """Test Money > comparison with non-Money type."""
        money = Money(Decimal("100"))
        
        with pytest.raises(TypeError):
            money > 50
    
    def test_money_equal_non_money(self):
        """Test Money equality with non-Money type."""
        money = Money(Decimal("100"))
        
        # Should return False, not raise
        assert (money == 100) is False
        assert (money == "100") is False


class TestInterestRateValueObject:
    """Test InterestRate value object."""
    
    def test_create_interest_rate_valid(self):
        """Test creating valid interest rate."""
        rate = InterestRate(Decimal("8.5"))
        assert rate.percentage == Decimal("8.5")
    
    def test_create_interest_rate_invalid(self):
        """Test creating invalid interest rate."""
        with pytest.raises(ValueError):
            InterestRate(Decimal("-1"))
        
        with pytest.raises(ValueError):
            InterestRate(Decimal("150"))
    
    def test_interest_rate_monthly_decimal(self):
        """Test monthly decimal calculation."""
        rate = InterestRate(Decimal("8.5"))
        monthly = rate.monthly_decimal
        
        assert abs(monthly - (8.5 / 12 / 100)) < 0.0001
    
    def test_interest_rate_yearly_decimal(self):
        """Test yearly decimal calculation."""
        rate = InterestRate(Decimal("8.5"))
        yearly = rate.yearly_decimal
        
        assert abs(yearly - 0.085) < 0.0001


class TestLoanTermValueObject:
    """Test LoanTerm value object."""
    
    def test_create_loan_term_valid(self):
        """Test creating valid loan term."""
        term = LoanTerm(60)
        assert term.months == 60
    
    def test_create_loan_term_invalid(self):
        """Test creating invalid loan term."""
        with pytest.raises(ValueError):
            LoanTerm(-12)
        
        with pytest.raises(ValueError):
            LoanTerm(400)
    
    def test_loan_term_years(self):
        """Test years calculation."""
        term = LoanTerm(60)
        assert term.years == 5.0


class TestDueDate:
    """Test DueDate domain service."""
    
    def test_calculate_next_due_date_normal(self):
        """Test normal next due date calculation."""
        current = date(2023, 1, 15)
        next_due = DueDate.calculate_next_due_date(current)
        
        assert next_due == date(2023, 2, 15)
    
    def test_calculate_next_due_date_december(self):
        """Test next due date from December."""
        current = date(2023, 12, 15)
        next_due = DueDate.calculate_next_due_date(current)
        
        assert next_due == date(2024, 1, 15)
    
    def test_calculate_next_due_date_end_of_month(self):
        """Test next due date from end of month."""
        current = date(2023, 1, 31)
        next_due = DueDate.calculate_next_due_date(current)
        
        # February 31 doesn't exist, should be Feb 28
        assert next_due.month == 2
        assert next_due.day <= 28
    
    def test_is_overdue_past_date(self):
        """Test is_overdue with past date."""
        past = date.today() - timedelta(days=5)
        assert DueDate.is_overdue(past) is True
    
    def test_is_overdue_future_date(self):
        """Test is_overdue with future date."""
        future = date.today() + timedelta(days=5)
        assert DueDate.is_overdue(future) is False


class TestPaymentAllocation:
    """Test PaymentAllocation value object."""
    
    def test_create_valid_allocation(self):
        """Test creating valid payment allocation."""
        allocation = PaymentAllocation(
            total_payment=Money(Decimal("2500")),
            principal=Money(Decimal("2000")),
            interest=Money(Decimal("500"))
        )
        
        assert allocation.total_payment.amount == Decimal("2500")
    
    def test_create_invalid_allocation(self):
        """Test creating invalid allocation."""
        with pytest.raises(ValueError):
            PaymentAllocation(
                total_payment=Money(Decimal("2500")),
                principal=Money(Decimal("2000")),
                interest=Money(Decimal("600"))  # Total doesn't match
            )
    
    def test_principal_percentage(self):
        """Test principal percentage calculation."""
        allocation = PaymentAllocation(
            total_payment=Money(Decimal("2500")),
            principal=Money(Decimal("2000")),
            interest=Money(Decimal("500"))
        )
        
        assert allocation.principal_percentage == Decimal("80.00")
    
    def test_interest_percentage(self):
        """Test interest percentage calculation."""
        allocation = PaymentAllocation(
            total_payment=Money(Decimal("2500")),
            principal=Money(Decimal("2000")),
            interest=Money(Decimal("500"))
        )
        
        assert allocation.interest_percentage == Decimal("20.00")


class TestLoanState:
    """Test LoanState domain entity."""
    
    def test_create_loan_state(self):
        """Test creating loan state."""
        state = LoanState(
            principal=Money(Decimal("100000")),
            outstanding_balance=Money(Decimal("80000")),
            interest_rate=InterestRate(Decimal("8.5")),
            emi_amount=Money(Decimal("2500")),
            term=LoanTerm(60),
            remaining_months=28,
            next_due_date=date.today() + timedelta(days=10),
            status=LoanStatusEnum.ACTIVE
        )
        
        assert state.is_active() is True
        assert state.is_paid_off() is False
    
    def test_loan_state_paid_off(self):
        """Test loan state when paid off."""
        state = LoanState(
            principal=Money(Decimal("100000")),
            outstanding_balance=Money(Decimal("0")),
            interest_rate=InterestRate(Decimal("8.5")),
            emi_amount=Money(Decimal("2500")),
            term=LoanTerm(60),
            remaining_months=0,
            next_due_date=date.today(),
            status=LoanStatusEnum.CLOSED
        )
        
        assert state.is_paid_off() is True
    
    def test_loan_state_days_overdue(self):
        """Test days overdue calculation."""
        past_date = date.today() - timedelta(days=5)
        state = LoanState(
            principal=Money(Decimal("100000")),
            outstanding_balance=Money(Decimal("80000")),
            interest_rate=InterestRate(Decimal("8.5")),
            emi_amount=Money(Decimal("2500")),
            term=LoanTerm(60),
            remaining_months=28,
            next_due_date=past_date,
            status=LoanStatusEnum.OVERDUE
        )
        
        assert state.days_overdue() == 5


# ============== ADDITIONAL EDGE CASE TESTS ==============

class TestEMICalculatorEdgeCases:
    """Test EMI Calculator edge cases."""
    
    def test_calculate_emi_very_small_principal(self):
        """Test EMI with very small principal."""
        principal = Decimal("100")
        annual_rate = Decimal("8.5")
        months = 12
        
        emi = EMICalculator.calculate_emi(principal, annual_rate, months)
        assert emi > 0
    
    def test_calculate_emi_very_high_rate(self):
        """Test EMI with extremely high rate."""
        principal = Decimal("100000")
        annual_rate = Decimal("30")  # Max rate
        months = 12
        
        emi = EMICalculator.calculate_emi(principal, annual_rate, months)
        assert emi > 0
    
    def test_calculate_interest_portion_zero_balance(self):
        """Test interest portion with zero balance."""
        interest = EMICalculator.calculate_interest_portion(Decimal("0"), Decimal("8.5"))
        assert interest == Decimal("0")
    
    def test_calculate_tenure_from_emi_very_high_emi(self):
        """Test tenure calculation with very high EMI."""
        principal = Decimal("50000")
        annual_rate = Decimal("8.5")
        current_emi = Decimal("50000")
        
        tenure = EMICalculator.calculate_tenure_from_emi(principal, annual_rate, current_emi)
        assert tenure == 1


class TestInterestCalculatorEdgeCases:
    """Test Interest Calculator edge cases."""
    
    def test_calculate_remaining_interest_very_high_emi(self):
        """Test remaining interest when EMI exceeds balance."""
        balance = Decimal("1000")
        annual_rate = Decimal("8.5")
        emi = Decimal("5000")  # Much higher than balance
        remaining_months = 12
        
        interest = InterestCalculator.calculate_remaining_interest(
            balance, annual_rate, emi, remaining_months
        )
        assert interest >= Decimal("0")
    
    def test_calculate_weighted_average_rate_unequal_weights(self):
        """Test weighted average with very unequal balance distributions."""
        balances = [Decimal("1000"), Decimal("1000000")]
        rates = [Decimal("5"), Decimal("15")]
        
        avg_rate = InterestCalculator.calculate_weighted_average_rate(balances, rates)
        
        # Should heavily favor the 1M loan at 15%
        assert avg_rate > Decimal("14")


class TestPrepaymentCalculatorEdgeCases:
    """Test Prepayment Calculator edge cases."""
    
    def test_calculate_prepayment_impact_zero_remaining_months(self):
        """Test prepayment with zero remaining months."""
        balance = Decimal("10000")
        prepayment = Decimal("5000")
        annual_rate = Decimal("8.5")
        emi = Decimal("2000")
        remaining_months = 0
        
        impact = PrepaymentCalculator.calculate_prepayment_impact(
            balance, prepayment, annual_rate, emi, remaining_months
        )
        
        assert impact['new_outstanding_balance'] == Decimal("5000")
    
    def test_calculate_emi_change_impact_zero_interest(self):
        """Test EMI change impact with zero interest."""
        principal = Decimal("100000")
        annual_rate = Decimal("0")
        original_tenure = 60
        new_emi = Decimal("2000")
        
        impact = PrepaymentCalculator.calculate_emi_change_impact(
            principal, annual_rate, original_tenure, new_emi
        )
        
        # With 0% interest, interest savings should be minimal (rounding artifacts)
        assert impact['interest_savings'] <= Decimal("1")


class TestValidatorEdgeCases:
    """Test validators with edge cases."""
    
    def test_validate_date_same_day_payment(self):
        """Test payment on same day as loan start."""
        start_date = date(2023, 1, 1)
        payment_date = date(2023, 1, 1)
        
        valid, msg = DateValidator.validate_payment_date(start_date, payment_date)
        assert valid is True
    
    def test_loan_amount_validator_boundary_minus_one(self):
        """Test loan amount just below minimum."""
        valid, msg = LoanAmountValidator.validate(Decimal("999.99"))
        assert valid is False
    
    def test_loan_amount_validator_boundary_plus_one(self):
        """Test loan amount just above maximum."""
        valid, msg = LoanAmountValidator.validate(Decimal("10000000.01"))
        assert valid is False
    
    def test_interest_rate_validator_boundary_zero_point_zero(self):
        """Test zero interest rate."""
        valid, msg = InterestRateValidator.validate(Decimal("0.00"))
        assert valid is True
    
    def test_loan_term_validator_boundary_one_month(self):
        """Test loan term below minimum."""
        valid, msg = LoanTermValidator.validate(1)
        assert valid is False
    
    def test_loan_term_validator_large_term(self):
        """Test very large loan term."""
        valid, msg = LoanTermValidator.validate(360)
        assert valid is True


class TestMoneyEdgeCases:
    """Test Money value object edge cases."""
    
    def test_money_zero_amount(self):
        """Test Money with zero amount."""
        money = Money(Decimal("0"))
        assert money.amount == Decimal("0")
    
    def test_money_very_large_amount(self):
        """Test Money with very large amount."""
        money = Money(Decimal("999999999999.99"))
        assert money.amount == Decimal("999999999999.99")
    
    def test_money_multiplication_zero(self):
        """Test Money multiplication by zero."""
        money = Money(Decimal("1000"))
        result = money * 0
        assert result.amount == Decimal("0")
    
    def test_money_multiplication_fractional(self):
        """Test Money multiplication with fractional factor."""
        money = Money(Decimal("1000"))
        result = money * 0.123456
        assert result.amount >= Decimal("0")


class TestInterestRateValueObjectEdgeCases:
    """Test InterestRate value object edge cases."""
    
    def test_interest_rate_max_value(self):
        """Test maximum interest rate."""
        rate = InterestRate(Decimal("100"))
        assert rate.percentage == Decimal("100")
    
    def test_interest_rate_fraction(self):
        """Test fractional interest rate."""
        rate = InterestRate(Decimal("0.5"))
        assert rate.monthly_decimal > 0


class TestLoanTermValueObjectEdgeCases:
    """Test LoanTerm value object edge cases."""
    
    def test_loan_term_one_month(self):
        """Test one month term."""
        with pytest.raises(ValueError):
            LoanTerm(0)
    
    def test_loan_term_360_months(self):
        """Test 360 month (30 year) term."""
        term = LoanTerm(360)
        assert term.years == 30


class TestLoanScheduleItemEdgeCases:
    """Test LoanScheduleItem edge cases."""
    
    def test_schedule_item_zero_interest(self):
        """Test schedule item with zero interest."""
        item = LoanScheduleItem(
            payment_number=1,
            payment_date=date.today(),
            emi_amount=Money(Decimal("1000")),
            principal_portion=Money(Decimal("1000")),
            interest_portion=Money(Decimal("0")),
            remaining_balance=Money(Decimal("50000"))
        )
        assert item.interest_portion.amount == Decimal("0")
    
    def test_schedule_item_final_payment_small_balance(self):
        """Test schedule item as final payment."""
        item = LoanScheduleItem(
            payment_number=60,
            payment_date=date.today(),
            emi_amount=Money(Decimal("100")),
            principal_portion=Money(Decimal("95")),
            interest_portion=Money(Decimal("5")),
            remaining_balance=Money(Decimal("0")),
            is_paid=True
        )
        assert item.is_paid is True


class TestDueDateEdgeCases:
    """Test DueDate domain service edge cases."""
    
    def test_calculate_next_due_date_leap_year(self):
        """Test next due date calculation in leap year."""
        current = date(2024, 1, 31)
        next_due = DueDate.calculate_next_due_date(current)
        
        assert next_due.month == 2
        assert next_due.year == 2024
    
    def test_calculate_next_due_date_from_feb_29(self):
        """Test next due date from February 29 in leap year."""
        current = date(2024, 2, 29)
        next_due = DueDate.calculate_next_due_date(current)
        
        assert next_due.month == 3
    
    def test_days_until_due_today(self):
        """Test days until due when due date is today."""
        days = DueDate.days_until_due(date.today())
        assert days == 0
    
    def test_days_until_due_future(self):
        """Test days until due with future date."""
        future = date.today() + timedelta(days=30)
        days = DueDate.days_until_due(future)
        assert days == 30
    
    def test_calculate_next_due_date_31st_to_april(self):
        """Test next due date from 31st to April (only 30 days)."""
        current = date(2023, 3, 31)
        next_due = DueDate.calculate_next_due_date(current)
        
        assert next_due.month == 4
        assert next_due.day == 30  # April has only 30 days
    
    def test_calculate_next_due_date_31st_to_june(self):
        """Test next due date from 31st to June (only 30 days)."""
        current = date(2023, 5, 31)
        next_due = DueDate.calculate_next_due_date(current)
        
        assert next_due.month == 6
        assert next_due.day == 30  # June has only 30 days
    
    def test_calculate_next_due_date_30th_to_feb(self):
        """Test next due date from 30th to February."""
        current = date(2023, 1, 30)
        next_due = DueDate.calculate_next_due_date(current)
        
        assert next_due.month == 2
        assert next_due.day == 28  # Non-leap year
    
    def test_calculate_next_due_date_dec_31st_to_jan(self):
        """Test next due date from December 31st to January."""
        current = date(2023, 12, 31)
        next_due = DueDate.calculate_next_due_date(current)
        
        assert next_due.month == 1
        assert next_due.year == 2024
        assert next_due.day == 31


class TestPaymentAllocationEdgeCases:
    """Test PaymentAllocation edge cases."""
    
    def test_payment_allocation_all_principal(self):
        """Test allocation with all principal (no interest)."""
        allocation = PaymentAllocation(
            total_payment=Money(Decimal("1000")),
            principal=Money(Decimal("1000")),
            interest=Money(Decimal("0"))
        )
        assert allocation.principal_percentage == Decimal("100.00")
        assert allocation.interest_percentage == Decimal("0.00")
    
    def test_payment_allocation_all_interest(self):
        """Test allocation with all interest (no principal)."""
        allocation = PaymentAllocation(
            total_payment=Money(Decimal("500")),
            principal=Money(Decimal("0")),
            interest=Money(Decimal("500"))
        )
        assert allocation.principal_percentage == Decimal("0.00")
        assert allocation.interest_percentage == Decimal("100.00")
    
    def test_payment_allocation_zero_payment(self):
        """Test allocation with zero payment."""
        allocation = PaymentAllocation(
            total_payment=Money(Decimal("0")),
            principal=Money(Decimal("0")),
            interest=Money(Decimal("0"))
        )
        assert allocation.principal_percentage == Decimal("0")
        assert allocation.interest_percentage == Decimal("0")


class TestLoanStateEdgeCases:
    """Test LoanState entity edge cases."""
    
    def test_loan_state_just_overdue(self):
        """Test loan state just became overdue."""
        past_date = date.today() - timedelta(days=1)
        state = LoanState(
            principal=Money(Decimal("100000")),
            outstanding_balance=Money(Decimal("50000")),
            interest_rate=InterestRate(Decimal("8.5")),
            emi_amount=Money(Decimal("2500")),
            term=LoanTerm(60),
            remaining_months=28,
            next_due_date=past_date,
            status=LoanStatusEnum.OVERDUE
        )
        
        assert state.is_overdue() is True
        assert state.days_overdue() >= 1
    
    def test_loan_state_heavily_overdue(self):
        """Test loan state heavily overdue."""
        past_date = date.today() - timedelta(days=150)
        state = LoanState(
            principal=Money(Decimal("100000")),
            outstanding_balance=Money(Decimal("50000")),
            interest_rate=InterestRate(Decimal("8.5")),
            emi_amount=Money(Decimal("2500")),
            term=LoanTerm(60),
            remaining_months=28,
            next_due_date=past_date,
            status=LoanStatusEnum.DEFAULTED
        )
        
        assert state.is_overdue() is True
        assert state.days_overdue() >= 150


# Additional comprehensive tests for missing coverage

class TestMoneyStringRepresentation:
    """Test Money string operations."""
    
    def test_money_with_negative_multiplication(self):
        """Test Money multiplication with 0."""
        money = Money(Decimal("100"))
        result = money * 0
        assert result.amount == Decimal("0")
    
    def test_money_with_decimal_multiplication(self):
        """Test Money multiplication with decimals."""
        money = Money(Decimal("100"))
        result = money * 0.5
        assert result.amount == Decimal("50.00")
    
    def test_money_equality_with_same_amount(self):
        """Test Money equality."""
        m1 = Money(Decimal("100.50"))
        m2 = Money(Decimal("100.50"))
        assert m1 == m2
    
    def test_money_inequality(self):
        """Test Money inequality."""
        m1 = Money(Decimal("100"))
        m2 = Money(Decimal("50"))
        assert m1 != m2
    
    def test_money_less_than_or_equal(self):
        """Test Money <= operator."""
        m1 = Money(Decimal("50"))
        m2 = Money(Decimal("100"))
        m3 = Money(Decimal("50"))
        
        assert m1 <= m2
        assert m1 <= m3
        assert not (m2 <= m1)
    
    def test_money_greater_than_or_equal(self):
        """Test Money >= operator."""
        m1 = Money(Decimal("100"))
        m2 = Money(Decimal("50"))
        m3 = Money(Decimal("100"))
        
        assert m1 >= m2
        assert m1 >= m3
        assert not (m2 >= m1)


class TestInterestRateStringAndEdgeCases:
    """Test InterestRate string representation and edge cases."""
    
    def test_interest_rate_string_representation(self):
        """Test interest rate string representation."""
        rate = InterestRate(Decimal("8.5"))
        assert str(rate) == "8.5%"
    
    def test_interest_rate_boundary_0_percent(self):
        """Test interest rate at 0% boundary."""
        rate = InterestRate(Decimal("0"))
        assert rate.monthly_decimal == 0
        assert rate.yearly_decimal == 0
    
    def test_interest_rate_boundary_100_percent(self):
        """Test interest rate at 100% boundary."""
        rate = InterestRate(Decimal("100"))
        assert rate.monthly_decimal == 100 / 12 / 100
        assert rate.yearly_decimal == 1.0


class TestLoanTermStringAndProperties:
    """Test LoanTerm string representation."""
    
    def test_loan_term_string_representation(self):
        """Test loan term string representation."""
        term = LoanTerm(60)
        assert str(term) == "60 months"
    
    def test_loan_term_years_property(self):
        """Test loan term years calculation."""
        term = LoanTerm(60)
        assert term.years == 5.0
        
        term2 = LoanTerm(120)
        assert term2.years == 10.0


class TestLoanScheduleItemValidation:
    """Test LoanScheduleItem validation."""
    
    def test_loan_schedule_item_valid(self):
        """Test creating valid schedule item."""
        item = LoanScheduleItem(
            payment_number=1,
            payment_date=date.today(),
            emi_amount=Money(Decimal("1000")),
            principal_portion=Money(Decimal("600")),
            interest_portion=Money(Decimal("400")),
            remaining_balance=Money(Decimal("99000"))
        )
        assert item.payment_number == 1
    
    def test_loan_schedule_item_invalid_sum(self):
        """Test schedule item with mismatched sums."""
        with pytest.raises(ValueError):
            LoanScheduleItem(
                payment_number=1,
                payment_date=date.today(),
                emi_amount=Money(Decimal("1000")),
                principal_portion=Money(Decimal("700")),
                interest_portion=Money(Decimal("400")),  # Total = 1100, not 1000
                remaining_balance=Money(Decimal("99000"))
            )


class TestLoanPaymentValidation:
    """Test LoanPayment validation."""
    
    def test_loan_payment_valid(self):
        """Test creating valid payment."""
        payment = LoanPayment(
            amount=Money(Decimal("2000")),
            payment_date=date.today(),
            principal_amount=Money(Decimal("1500")),
            interest_amount=Money(Decimal("500")),
            remaining_balance=Money(Decimal("98000")),
            notes="Regular payment"
        )
        assert payment.amount.amount == Decimal("2000")
    
    def test_loan_payment_invalid_sum(self):
        """Test payment with mismatched sums."""
        with pytest.raises(ValueError):
            LoanPayment(
                amount=Money(Decimal("2000")),
                payment_date=date.today(),
                principal_amount=Money(Decimal("1300")),
                interest_amount=Money(Decimal("500")),  # Total = 1800, not 2000
                remaining_balance=Money(Decimal("98000"))
            )


class TestEMIImpactAnalysisProperties:
    """Test EMIImpactAnalysis properties."""
    
    def test_emi_impact_analysis_tenure_reduction(self):
        """Test tenure reduction calculation."""
        analysis = EMIImpactAnalysis(
            original_emi=Money(Decimal("2000")),
            new_emi=Money(Decimal("2500")),
            original_tenure_months=120,
            new_tenure_months=96,
            original_total_interest=Money(Decimal("40000")),
            new_total_interest=Money(Decimal("30000")),
            interest_savings=Money(Decimal("10000")),
            savings_percentage=Decimal("25")
        )
        
        assert analysis.tenure_reduction_months == 24
        assert analysis.is_beneficial is True
    
    def test_emi_impact_analysis_no_savings(self):
        """Test EMI impact with no savings."""
        analysis = EMIImpactAnalysis(
            original_emi=Money(Decimal("2000")),
            new_emi=Money(Decimal("2000")),
            original_tenure_months=120,
            new_tenure_months=120,
            original_total_interest=Money(Decimal("40000")),
            new_total_interest=Money(Decimal("40000")),
            interest_savings=Money(Decimal("0")),
            savings_percentage=Decimal("0")
        )
        
        assert analysis.tenure_reduction_months == 0
        assert analysis.is_beneficial is False


class TestPrepaymentAnalysisProperties:
    """Test PrepaymentAnalysis properties."""
    
    def test_prepayment_analysis_full_payoff(self):
        """Test prepayment analysis for full payoff."""
        analysis = PrepaymentAnalysis(
            prepayment_amount=Money(Decimal("50000")),
            new_outstanding_balance=Money(Decimal("0")),
            tenure_reduction_months=60,
            interest_savings=Money(Decimal("15000")),
            savings_percentage=Decimal("30")
        )
        
        assert analysis.is_full_payoff is True
    
    def test_prepayment_analysis_partial(self):
        """Test prepayment analysis for partial prepayment."""
        analysis = PrepaymentAnalysis(
            prepayment_amount=Money(Decimal("20000")),
            new_outstanding_balance=Money(Decimal("30000")),
            tenure_reduction_months=10,
            interest_savings=Money(Decimal("2000")),
            savings_percentage=Decimal("10")
        )
        
        assert analysis.is_full_payoff is False


class TestDueDateDomainService:
    """Test DueDate domain service."""
    
    def test_is_overdue_past_date(self):
        """Test is_overdue with past date."""
        past_date = date.today() - timedelta(days=5)
        assert DueDate.is_overdue(past_date) is True
    
    def test_is_overdue_future_date(self):
        """Test is_overdue with future date."""
        future_date = date.today() + timedelta(days=5)
        assert DueDate.is_overdue(future_date) is False
    
    def test_calculate_next_due_date_regular_month(self):
        """Test next due date calculation for regular months."""
        current = date(2023, 6, 15)
        next_due = DueDate.calculate_next_due_date(current)
        
        assert next_due.month == 7
        assert next_due.day == 15
    
    def test_calculate_next_due_date_year_end(self):
        """Test next due date calculation at year end."""
        current = date(2023, 12, 15)
        next_due = DueDate.calculate_next_due_date(current)
        
        assert next_due.month == 1
        assert next_due.year == 2024
        assert next_due.day == 15
    
    def test_calculate_next_due_date_31st_to_feb(self):
        """Test next due date from 31st to February."""
        current = date(2023, 1, 31)
        next_due = DueDate.calculate_next_due_date(current)
        
        assert next_due.month == 2
        # February should adjust day to last day of month
        assert next_due.day <= 29
    
    def test_calculate_next_due_date_31st_to_april(self):
        """Test next due date from 31st to April (only 30 days)."""
        current = date(2023, 3, 31)
        next_due = DueDate.calculate_next_due_date(current)
        
        assert next_due.month == 4
        assert next_due.day == 30  # April has only 30 days
    
    def test_calculate_next_due_date_31st_to_june(self):
        """Test next due date from 31st to June (only 30 days)."""
        current = date(2023, 5, 31)
        next_due = DueDate.calculate_next_due_date(current)
        
        assert next_due.month == 6
        assert next_due.day == 30  # June has only 30 days
    
    def test_calculate_next_due_date_30th_to_feb(self):
        """Test next due date from 30th to February."""
        current = date(2023, 1, 30)
        next_due = DueDate.calculate_next_due_date(current)
        
        assert next_due.month == 2
        assert next_due.day == 28  # Non-leap year
    
    def test_calculate_next_due_date_dec_31st_to_jan(self):
        """Test next due date from December 31st to January."""
        current = date(2023, 12, 31)
        next_due = DueDate.calculate_next_due_date(current)
        
        assert next_due.month == 1
        assert next_due.year == 2024
        assert next_due.day == 31


class TestPaymentAllocationPercentages:
    """Test PaymentAllocation percentage calculations."""
    
    def test_payment_allocation_equal_split(self):
        """Test allocation with equal principal and interest."""
        allocation = PaymentAllocation(
            total_payment=Money(Decimal("1000")),
            principal=Money(Decimal("500")),
            interest=Money(Decimal("500"))
        )
        
        assert allocation.principal_percentage == Decimal("50.00")
        assert allocation.interest_percentage == Decimal("50.00")
    
    def test_payment_allocation_mostly_principal(self):
        """Test allocation with mostly principal."""
        allocation = PaymentAllocation(
            total_payment=Money(Decimal("1000")),
            principal=Money(Decimal("900")),
            interest=Money(Decimal("100"))
        )
        
        assert allocation.principal_percentage == Decimal("90.00")
        assert allocation.interest_percentage == Decimal("10.00")
    
    def test_payment_allocation_zero_payment(self):
        """Test allocation with zero total payment."""
        allocation = PaymentAllocation(
            total_payment=Money(Decimal("0")),
            principal=Money(Decimal("0")),
            interest=Money(Decimal("0"))
        )
        
        assert allocation.principal_percentage == Decimal("0")
        assert allocation.interest_percentage == Decimal("0")


class TestLoanStateComprehensive:
    """Comprehensive tests for LoanState."""
    
    def test_loan_state_active(self):
        """Test active loan state."""
        state = LoanState(
            principal=Money(Decimal("100000")),
            outstanding_balance=Money(Decimal("50000")),
            interest_rate=InterestRate(Decimal("8.5")),
            emi_amount=Money(Decimal("2500")),
            term=LoanTerm(60),
            remaining_months=30,
            next_due_date=date.today() + timedelta(days=10),
            status=LoanStatusEnum.ACTIVE
        )
        
        assert state.is_active() is True
        assert state.is_paid_off() is False
        assert state.is_overdue() is False
    
    def test_loan_state_paid_off(self):
        """Test paid off loan state."""
        state = LoanState(
            principal=Money(Decimal("100000")),
            outstanding_balance=Money(Decimal("0")),
            interest_rate=InterestRate(Decimal("8.5")),
            emi_amount=Money(Decimal("2500")),
            term=LoanTerm(60),
            remaining_months=0,
            next_due_date=date.today(),
            status=LoanStatusEnum.PAID_OFF
        )
        
        assert state.is_paid_off() is True
        assert state.is_active() is False
    
    def test_loan_state_no_overdue_days(self):
        """Test loan with no overdue days."""
        future_date = date.today() + timedelta(days=30)
        state = LoanState(
            principal=Money(Decimal("100000")),
            outstanding_balance=Money(Decimal("50000")),
            interest_rate=InterestRate(Decimal("8.5")),
            emi_amount=Money(Decimal("2500")),
            term=LoanTerm(60),
            remaining_months=30,
            next_due_date=future_date,
            status=LoanStatusEnum.ACTIVE
        )
        
        assert state.days_overdue() == 0
