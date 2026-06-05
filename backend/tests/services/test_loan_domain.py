"""Unit tests for app.services.loan_domain module."""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from app.services.loan_domain import (
    LoanStatusEnum,
    PaymentStatusEnum,
    Money,
    InterestRate,
    LoanTerm,
    LoanScheduleItem,
    LoanPayment,
    EMIImpactAnalysis,
    PrepaymentAnalysis,
    LoanState,
    DueDate,
    PaymentAllocation,
)


class TestLoanStatusEnum:
    """Test LoanStatusEnum."""

    def test_active_status_exists(self):
        """Test ACTIVE status value."""
        assert LoanStatusEnum.ACTIVE.value == "Active"

    def test_closed_status_exists(self):
        """Test CLOSED status value."""
        assert LoanStatusEnum.CLOSED.value == "Closed"

    def test_paid_off_status_exists(self):
        """Test PAID_OFF status value."""
        assert LoanStatusEnum.PAID_OFF.value == "Paid Off"

    def test_overdue_status_exists(self):
        """Test OVERDUE status value."""
        assert LoanStatusEnum.OVERDUE.value == "Overdue"

    def test_defaulted_status_exists(self):
        """Test DEFAULTED status value."""
        assert LoanStatusEnum.DEFAULTED.value == "Defaulted"


class TestPaymentStatusEnum:
    """Test PaymentStatusEnum."""

    def test_paid_status_exists(self):
        """Test PAID status value."""
        assert PaymentStatusEnum.PAID.value == "Paid"

    def test_pending_status_exists(self):
        """Test PENDING status value."""
        assert PaymentStatusEnum.PENDING.value == "Pending"

    def test_overdue_status_exists(self):
        """Test OVERDUE status value."""
        assert PaymentStatusEnum.OVERDUE.value == "Overdue"

    def test_failed_status_exists(self):
        """Test FAILED status value."""
        assert PaymentStatusEnum.FAILED.value == "Failed"


class TestMoney:
    """Test Money value object."""

    def test_money_creation_valid(self):
        """Test creating Money with valid amount."""
        money = Money(Decimal('100.50'))
        assert money.amount == Decimal('100.50')

    def test_money_creation_zero(self):
        """Test creating Money with zero amount."""
        money = Money(Decimal('0'))
        assert money.amount == Decimal('0')

    def test_money_creation_negative_raises(self):
        """Test that negative amount raises ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            Money(Decimal('-100'))

    def test_money_is_frozen(self):
        """Test that Money is immutable."""
        money = Money(Decimal('100'))
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            money.amount = Decimal('200')

    def test_money_addition_valid(self):
        """Test adding two Money objects."""
        money1 = Money(Decimal('100'))
        money2 = Money(Decimal('50'))
        result = money1 + money2
        assert result.amount == Decimal('150')

    def test_money_addition_non_money_raises(self):
        """Test that adding non-Money raises TypeError."""
        money = Money(Decimal('100'))
        with pytest.raises(TypeError, match="Can only add Money to Money"):
            money + 50

    def test_money_subtraction_valid(self):
        """Test subtracting Money objects."""
        money1 = Money(Decimal('100'))
        money2 = Money(Decimal('30'))
        result = money1 - money2
        assert result.amount == Decimal('70')

    def test_money_subtraction_non_money_raises(self):
        """Test that subtracting non-Money raises TypeError."""
        money = Money(Decimal('100'))
        with pytest.raises(TypeError, match="Can only subtract Money from Money"):
            money - 30

    def test_money_subtraction_negative_raises(self):
        """Test that subtraction resulting in negative raises ValueError."""
        money1 = Money(Decimal('30'))
        money2 = Money(Decimal('100'))
        with pytest.raises(ValueError, match="negative"):
            money1 - money2

    def test_money_multiplication(self):
        """Test multiplying Money by factor."""
        money = Money(Decimal('100'))
        result = money * 1.5
        assert result.amount == Decimal('150.00')

    def test_money_multiplication_zero(self):
        """Test multiplying Money by zero."""
        money = Money(Decimal('100'))
        result = money * 0
        assert result.amount == Decimal('0.00')

    def test_money_equality_true(self):
        """Test Money equality when equal."""
        money1 = Money(Decimal('100'))
        money2 = Money(Decimal('100'))
        assert money1 == money2

    def test_money_equality_false(self):
        """Test Money equality when not equal."""
        money1 = Money(Decimal('100'))
        money2 = Money(Decimal('50'))
        assert not (money1 == money2)

    def test_money_equality_with_non_money(self):
        """Test Money equality with non-Money object."""
        money = Money(Decimal('100'))
        assert not (money == 100)

    def test_money_less_than(self):
        """Test Money less than comparison."""
        money1 = Money(Decimal('50'))
        money2 = Money(Decimal('100'))
        assert money1 < money2

    def test_money_less_than_false(self):
        """Test Money less than when false."""
        money1 = Money(Decimal('100'))
        money2 = Money(Decimal('50'))
        assert not (money1 < money2)

    def test_money_less_than_non_money_raises(self):
        """Test Money less than with non-Money raises TypeError."""
        money = Money(Decimal('100'))
        with pytest.raises(TypeError, match="Cannot compare"):
            money < 100

    def test_money_less_equal(self):
        """Test Money less than or equal."""
        money1 = Money(Decimal('50'))
        money2 = Money(Decimal('100'))
        assert money1 <= money2

    def test_money_less_equal_equal(self):
        """Test Money less than or equal when equal."""
        money1 = Money(Decimal('100'))
        money2 = Money(Decimal('100'))
        assert money1 <= money2

    def test_money_greater_than(self):
        """Test Money greater than comparison."""
        money1 = Money(Decimal('100'))
        money2 = Money(Decimal('50'))
        assert money1 > money2

    def test_money_greater_than_false(self):
        """Test Money greater than when false."""
        money1 = Money(Decimal('50'))
        money2 = Money(Decimal('100'))
        assert not (money1 > money2)

    def test_money_greater_than_non_money_raises(self):
        """Test Money greater than with non-Money raises TypeError."""
        money = Money(Decimal('100'))
        with pytest.raises(TypeError, match="Cannot compare"):
            money > 100

    def test_money_greater_equal(self):
        """Test Money greater than or equal."""
        money1 = Money(Decimal('100'))
        money2 = Money(Decimal('50'))
        assert money1 >= money2

    def test_money_greater_equal_equal(self):
        """Test Money greater than or equal when equal."""
        money1 = Money(Decimal('100'))
        money2 = Money(Decimal('100'))
        assert money1 >= money2


class TestInterestRate:
    """Test InterestRate value object."""

    def test_interest_rate_creation_valid(self):
        """Test creating InterestRate with valid percentage."""
        rate = InterestRate(Decimal('10.5'))
        assert rate.percentage == Decimal('10.5')

    def test_interest_rate_creation_zero(self):
        """Test creating InterestRate with zero."""
        rate = InterestRate(Decimal('0'))
        assert rate.percentage == Decimal('0')

    def test_interest_rate_creation_max(self):
        """Test creating InterestRate with max value."""
        rate = InterestRate(Decimal('100'))
        assert rate.percentage == Decimal('100')

    def test_interest_rate_negative_raises(self):
        """Test that negative rate raises ValueError."""
        with pytest.raises(ValueError, match="between 0 and 100"):
            InterestRate(Decimal('-5'))

    def test_interest_rate_above_100_raises(self):
        """Test that rate > 100 raises ValueError."""
        with pytest.raises(ValueError, match="between 0 and 100"):
            InterestRate(Decimal('105'))

    def test_interest_rate_monthly_decimal(self):
        """Test monthly decimal calculation."""
        rate = InterestRate(Decimal('12'))
        # 12% / 12 / 100 = 0.01
        assert abs(rate.monthly_decimal - 0.01) < 0.0001

    def test_interest_rate_yearly_decimal(self):
        """Test yearly decimal calculation."""
        rate = InterestRate(Decimal('8'))
        # 8% / 100 = 0.08
        assert abs(rate.yearly_decimal - 0.08) < 0.0001

    def test_interest_rate_string_representation(self):
        """Test string representation."""
        rate = InterestRate(Decimal('10.5'))
        assert str(rate) == "10.5%"

    def test_interest_rate_is_frozen(self):
        """Test that InterestRate is immutable."""
        rate = InterestRate(Decimal('10'))
        with pytest.raises(Exception):
            rate.percentage = Decimal('20')


class TestLoanTerm:
    """Test LoanTerm value object."""

    def test_loan_term_creation_valid(self):
        """Test creating LoanTerm with valid months."""
        term = LoanTerm(60)
        assert term.months == 60

    def test_loan_term_creation_min(self):
        """Test creating LoanTerm with minimum months."""
        term = LoanTerm(1)
        assert term.months == 1

    def test_loan_term_creation_max(self):
        """Test creating LoanTerm with max months."""
        term = LoanTerm(360)
        assert term.months == 360

    def test_loan_term_zero_raises(self):
        """Test that zero months raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            LoanTerm(0)

    def test_loan_term_negative_raises(self):
        """Test that negative months raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            LoanTerm(-12)

    def test_loan_term_exceeds_max_raises(self):
        """Test that months > 360 raises ValueError."""
        with pytest.raises(ValueError, match="cannot exceed 360"):
            LoanTerm(361)

    def test_loan_term_years_calculation(self):
        """Test years calculation."""
        term = LoanTerm(60)
        assert term.years == 5.0

    def test_loan_term_years_partial(self):
        """Test years calculation with partial year."""
        term = LoanTerm(18)
        assert term.years == 1.5

    def test_loan_term_string_representation(self):
        """Test string representation."""
        term = LoanTerm(60)
        assert str(term) == "60 months"

    def test_loan_term_is_frozen(self):
        """Test that LoanTerm is immutable."""
        term = LoanTerm(60)
        with pytest.raises(Exception):
            term.months = 120


class TestLoanScheduleItem:
    """Test LoanScheduleItem value object."""

    def test_loan_schedule_item_creation_valid(self):
        """Test creating valid LoanScheduleItem."""
        item = LoanScheduleItem(
            payment_number=1,
            payment_date=date.today(),
            emi_amount=Money(Decimal('10000')),
            principal_portion=Money(Decimal('6000')),
            interest_portion=Money(Decimal('4000')),
            remaining_balance=Money(Decimal('94000')),
            is_paid=False
        )
        assert item.payment_number == 1

    def test_loan_schedule_item_invalid_sum_raises(self):
        """Test that invalid principal+interest sum raises ValueError."""
        with pytest.raises(ValueError, match="must equal EMI"):
            LoanScheduleItem(
                payment_number=1,
                payment_date=date.today(),
                emi_amount=Money(Decimal('10000')),
                principal_portion=Money(Decimal('5000')),
                interest_portion=Money(Decimal('4000')),
                remaining_balance=Money(Decimal('95000'))
            )

    def test_loan_schedule_item_with_tolerance(self):
        """Test that small rounding differences are allowed."""
        # Difference of 0.01 should be within tolerance
        item = LoanScheduleItem(
            payment_number=1,
            payment_date=date.today(),
            emi_amount=Money(Decimal('10000.00')),
            principal_portion=Money(Decimal('6000.00')),
            interest_portion=Money(Decimal('4000.00')),
            remaining_balance=Money(Decimal('94000'))
        )
        assert item.emi_amount.amount == Decimal('10000.00')


class TestLoanPayment:
    """Test LoanPayment value object."""

    def test_loan_payment_creation_valid(self):
        """Test creating valid LoanPayment."""
        payment = LoanPayment(
            amount=Money(Decimal('10000')),
            payment_date=date.today(),
            principal_amount=Money(Decimal('6000')),
            interest_amount=Money(Decimal('4000')),
            remaining_balance=Money(Decimal('94000'))
        )
        assert payment.amount.amount == Decimal('10000')

    def test_loan_payment_with_notes(self):
        """Test LoanPayment with notes."""
        payment = LoanPayment(
            amount=Money(Decimal('10000')),
            payment_date=date.today(),
            principal_amount=Money(Decimal('6000')),
            interest_amount=Money(Decimal('4000')),
            remaining_balance=Money(Decimal('94000')),
            notes="Monthly payment"
        )
        assert payment.notes == "Monthly payment"

    def test_loan_payment_invalid_sum_raises(self):
        """Test that invalid sum raises ValueError."""
        with pytest.raises(ValueError, match="must equal amount"):
            LoanPayment(
                amount=Money(Decimal('10000')),
                payment_date=date.today(),
                principal_amount=Money(Decimal('5000')),
                interest_amount=Money(Decimal('4000')),
                remaining_balance=Money(Decimal('94000'))
            )


class TestEMIImpactAnalysis:
    """Test EMIImpactAnalysis value object."""

    def test_emi_impact_analysis_creation(self):
        """Test creating EMIImpactAnalysis."""
        analysis = EMIImpactAnalysis(
            original_emi=Money(Decimal('2000')),
            new_emi=Money(Decimal('2500')),
            original_tenure_months=60,
            new_tenure_months=48,
            original_total_interest=Money(Decimal('20000')),
            new_total_interest=Money(Decimal('15000')),
            interest_savings=Money(Decimal('5000')),
            savings_percentage=Decimal('25.00')
        )
        assert analysis.tenure_reduction_months == 12

    def test_emi_impact_analysis_beneficial(self):
        """Test is_beneficial property."""
        analysis = EMIImpactAnalysis(
            original_emi=Money(Decimal('2000')),
            new_emi=Money(Decimal('2500')),
            original_tenure_months=60,
            new_tenure_months=48,
            original_total_interest=Money(Decimal('20000')),
            new_total_interest=Money(Decimal('15000')),
            interest_savings=Money(Decimal('5000')),
            savings_percentage=Decimal('25.00')
        )
        assert analysis.is_beneficial is True

    def test_emi_impact_analysis_not_beneficial(self):
        """Test is_beneficial when not beneficial."""
        analysis = EMIImpactAnalysis(
            original_emi=Money(Decimal('2000')),
            new_emi=Money(Decimal('1500')),
            original_tenure_months=60,
            new_tenure_months=80,
            original_total_interest=Money(Decimal('20000')),
            new_total_interest=Money(Decimal('30000')),
            interest_savings=Money(Decimal('0')),
            savings_percentage=Decimal('0')
        )
        assert analysis.is_beneficial is False


class TestPrepaymentAnalysis:
    """Test PrepaymentAnalysis value object."""

    def test_prepayment_analysis_creation(self):
        """Test creating PrepaymentAnalysis."""
        analysis = PrepaymentAnalysis(
            prepayment_amount=Money(Decimal('50000')),
            new_outstanding_balance=Money(Decimal('50000')),
            tenure_reduction_months=12,
            interest_savings=Money(Decimal('5000')),
            savings_percentage=Decimal('25.00')
        )
        assert analysis.prepayment_amount.amount == Decimal('50000')

    def test_prepayment_analysis_full_payoff(self):
        """Test is_full_payoff property when true."""
        analysis = PrepaymentAnalysis(
            prepayment_amount=Money(Decimal('100000')),
            new_outstanding_balance=Money(Decimal('0')),
            tenure_reduction_months=60,
            interest_savings=Money(Decimal('20000')),
            savings_percentage=Decimal('100.00')
        )
        assert analysis.is_full_payoff is True

    def test_prepayment_analysis_not_full_payoff(self):
        """Test is_full_payoff property when false."""
        analysis = PrepaymentAnalysis(
            prepayment_amount=Money(Decimal('10000')),
            new_outstanding_balance=Money(Decimal('90000')),
            tenure_reduction_months=2,
            interest_savings=Money(Decimal('500')),
            savings_percentage=Decimal('2.50')
        )
        assert analysis.is_full_payoff is False


class TestLoanState:
    """Test LoanState domain entity."""

    def test_loan_state_creation(self):
        """Test creating LoanState."""
        state = LoanState(
            principal=Money(Decimal('100000')),
            outstanding_balance=Money(Decimal('100000')),
            interest_rate=InterestRate(Decimal('10')),
            emi_amount=Money(Decimal('2000')),
            term=LoanTerm(60),
            remaining_months=60,
            next_due_date=date.today() + timedelta(days=30),
            status=LoanStatusEnum.ACTIVE
        )
        assert state.principal.amount == Decimal('100000')

    def test_loan_state_is_active(self):
        """Test is_active method."""
        state = LoanState(
            principal=Money(Decimal('100000')),
            outstanding_balance=Money(Decimal('100000')),
            interest_rate=InterestRate(Decimal('10')),
            emi_amount=Money(Decimal('2000')),
            term=LoanTerm(60),
            remaining_months=60,
            next_due_date=date.today() + timedelta(days=30),
            status=LoanStatusEnum.ACTIVE
        )
        assert state.is_active() is True

    def test_loan_state_is_active_false(self):
        """Test is_active when false."""
        state = LoanState(
            principal=Money(Decimal('100000')),
            outstanding_balance=Money(Decimal('100000')),
            interest_rate=InterestRate(Decimal('10')),
            emi_amount=Money(Decimal('2000')),
            term=LoanTerm(60),
            remaining_months=60,
            next_due_date=date.today() + timedelta(days=30),
            status=LoanStatusEnum.CLOSED
        )
        assert state.is_active() is False

    def test_loan_state_is_paid_off_true(self):
        """Test is_paid_off when true."""
        state = LoanState(
            principal=Money(Decimal('100000')),
            outstanding_balance=Money(Decimal('0')),
            interest_rate=InterestRate(Decimal('10')),
            emi_amount=Money(Decimal('2000')),
            term=LoanTerm(60),
            remaining_months=0,
            next_due_date=date.today(),
            status=LoanStatusEnum.PAID_OFF
        )
        assert state.is_paid_off() is True

    def test_loan_state_is_paid_off_false(self):
        """Test is_paid_off when false."""
        state = LoanState(
            principal=Money(Decimal('100000')),
            outstanding_balance=Money(Decimal('50000')),
            interest_rate=InterestRate(Decimal('10')),
            emi_amount=Money(Decimal('2000')),
            term=LoanTerm(60),
            remaining_months=30,
            next_due_date=date.today() + timedelta(days=30),
            status=LoanStatusEnum.ACTIVE
        )
        assert state.is_paid_off() is False

    def test_loan_state_is_overdue_true(self):
        """Test is_overdue when true."""
        state = LoanState(
            principal=Money(Decimal('100000')),
            outstanding_balance=Money(Decimal('50000')),
            interest_rate=InterestRate(Decimal('10')),
            emi_amount=Money(Decimal('2000')),
            term=LoanTerm(60),
            remaining_months=30,
            next_due_date=date.today(),
            status=LoanStatusEnum.OVERDUE
        )
        assert state.is_overdue() is True

    def test_loan_state_is_overdue_false(self):
        """Test is_overdue when false."""
        state = LoanState(
            principal=Money(Decimal('100000')),
            outstanding_balance=Money(Decimal('50000')),
            interest_rate=InterestRate(Decimal('10')),
            emi_amount=Money(Decimal('2000')),
            term=LoanTerm(60),
            remaining_months=30,
            next_due_date=date.today() + timedelta(days=30),
            status=LoanStatusEnum.ACTIVE
        )
        assert state.is_overdue() is False

    def test_loan_state_days_overdue_positive(self):
        """Test days_overdue calculation."""
        past_date = date.today() - timedelta(days=10)
        state = LoanState(
            principal=Money(Decimal('100000')),
            outstanding_balance=Money(Decimal('50000')),
            interest_rate=InterestRate(Decimal('10')),
            emi_amount=Money(Decimal('2000')),
            term=LoanTerm(60),
            remaining_months=30,
            next_due_date=past_date,
            status=LoanStatusEnum.OVERDUE
        )
        assert state.days_overdue() == 10

    def test_loan_state_days_overdue_zero(self):
        """Test days_overdue when not overdue."""
        state = LoanState(
            principal=Money(Decimal('100000')),
            outstanding_balance=Money(Decimal('50000')),
            interest_rate=InterestRate(Decimal('10')),
            emi_amount=Money(Decimal('2000')),
            term=LoanTerm(60),
            remaining_months=30,
            next_due_date=date.today() + timedelta(days=10),
            status=LoanStatusEnum.ACTIVE
        )
        assert state.days_overdue() == 0


class TestDueDate:
    """Test DueDate domain service."""

    def test_calculate_next_due_date_regular_month(self):
        """Test calculating next due date in regular month."""
        current = date(2025, 1, 15)
        next_date = DueDate.calculate_next_due_date(current)
        assert next_date == date(2025, 2, 15)

    def test_calculate_next_due_date_december(self):
        """Test calculating next due date from December."""
        current = date(2025, 12, 15)
        next_date = DueDate.calculate_next_due_date(current)
        assert next_date == date(2026, 1, 15)

    def test_calculate_next_due_date_month_end_jan31(self):
        """Test calculating next due date from Jan 31."""
        current = date(2025, 1, 31)
        next_date = DueDate.calculate_next_due_date(current)
        # Feb doesn't have 31 days, so should be Feb 28/29
        assert next_date.month == 2
        assert next_date.day <= 29

    def test_calculate_next_due_date_month_end_march31(self):
        """Test calculating next due date from March 31."""
        current = date(2025, 3, 31)
        next_date = DueDate.calculate_next_due_date(current)
        assert next_date.month == 4
        assert next_date.day <= 30

    def test_is_overdue_true(self):
        """Test is_overdue when true."""
        past_date = date.today() - timedelta(days=1)
        assert DueDate.is_overdue(past_date) is True

    def test_is_overdue_false(self):
        """Test is_overdue when false."""
        future_date = date.today() + timedelta(days=1)
        assert DueDate.is_overdue(future_date) is False

    def test_is_overdue_today(self):
        """Test is_overdue for today."""
        today = date.today()
        # Today is not overdue (it's due today)
        assert DueDate.is_overdue(today) is False

    def test_days_until_due_positive(self):
        """Test days_until_due in future."""
        future_date = date.today() + timedelta(days=10)
        days = DueDate.days_until_due(future_date)
        assert days == 10

    def test_days_until_due_zero(self):
        """Test days_until_due for today."""
        today = date.today()
        days = DueDate.days_until_due(today)
        assert days == 0

    def test_days_until_due_negative(self):
        """Test days_until_due in past."""
        past_date = date.today() - timedelta(days=10)
        days = DueDate.days_until_due(past_date)
        assert days == -10


class TestPaymentAllocation:
    """Test PaymentAllocation value object."""

    def test_payment_allocation_creation_valid(self):
        """Test creating valid PaymentAllocation."""
        allocation = PaymentAllocation(
            total_payment=Money(Decimal('10000')),
            principal=Money(Decimal('6000')),
            interest=Money(Decimal('4000'))
        )
        assert allocation.total_payment.amount == Decimal('10000')

    def test_payment_allocation_invalid_sum_raises(self):
        """Test that invalid sum raises ValueError."""
        with pytest.raises(ValueError, match="must equal total"):
            PaymentAllocation(
                total_payment=Money(Decimal('10000')),
                principal=Money(Decimal('5000')),
                interest=Money(Decimal('4000'))
            )

    def test_payment_allocation_principal_percentage(self):
        """Test principal percentage calculation."""
        allocation = PaymentAllocation(
            total_payment=Money(Decimal('10000')),
            principal=Money(Decimal('6000')),
            interest=Money(Decimal('4000'))
        )
        assert allocation.principal_percentage == Decimal('60.00')

    def test_payment_allocation_interest_percentage(self):
        """Test interest percentage calculation."""
        allocation = PaymentAllocation(
            total_payment=Money(Decimal('10000')),
            principal=Money(Decimal('6000')),
            interest=Money(Decimal('4000'))
        )
        assert allocation.interest_percentage == Decimal('40.00')

    def test_payment_allocation_percentage_sum(self):
        """Test that percentages sum to 100."""
        allocation = PaymentAllocation(
            total_payment=Money(Decimal('10000')),
            principal=Money(Decimal('6000')),
            interest=Money(Decimal('4000'))
        )
        total_percentage = allocation.principal_percentage + allocation.interest_percentage
        assert total_percentage == Decimal('100.00')

    def test_payment_allocation_zero_payment(self):
        """Test with zero payment."""
        allocation = PaymentAllocation(
            total_payment=Money(Decimal('0')),
            principal=Money(Decimal('0')),
            interest=Money(Decimal('0'))
        )
        assert allocation.principal_percentage == Decimal('0')
        assert allocation.interest_percentage == Decimal('0')
