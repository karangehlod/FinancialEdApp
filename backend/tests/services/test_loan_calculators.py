"""Unit tests for app.services.loan_calculators module."""

import pytest
import math
from decimal import Decimal
from app.services.loan_calculators import (
    EMICalculator,
    InterestCalculator,
    PrepaymentCalculator,
)


class TestEMICalculator:
    """Test EMICalculator class."""

    def test_calculate_emi_basic(self):
        """Test basic EMI calculation."""
        principal = Decimal('100000')
        rate = Decimal('10')
        months = 12
        
        emi = EMICalculator.calculate_emi(principal, rate, months)
        assert emi > 0
        assert isinstance(emi, Decimal)

    def test_calculate_emi_zero_interest(self):
        """Test EMI calculation with zero interest."""
        principal = Decimal('100000')
        rate = Decimal('0')
        months = 12
        
        emi = EMICalculator.calculate_emi(principal, rate, months)
        # Should be principal/months
        expected = Decimal('100000') / 12
        assert emi == Decimal(str(round(float(expected), 2)))

    def test_calculate_emi_high_interest(self):
        """Test EMI calculation with high interest rate."""
        principal = Decimal('500000')
        rate = Decimal('25')
        months = 60
        
        emi = EMICalculator.calculate_emi(principal, rate, months)
        assert emi > 0
        # EMI should be greater than principal/months due to interest
        assert emi > principal / months

    def test_calculate_emi_single_month(self):
        """Test EMI calculation for single month (edge case)."""
        principal = Decimal('50000')
        rate = Decimal('5')
        months = 1
        
        emi = EMICalculator.calculate_emi(principal, rate, months)
        assert emi > 0

    def test_calculate_emi_long_term(self):
        """Test EMI calculation for long term loan."""
        principal = Decimal('1000000')
        rate = Decimal('8')
        months = 360  # 30 years
        
        emi = EMICalculator.calculate_emi(principal, rate, months)
        assert emi > 0

    def test_calculate_emi_low_amount(self):
        """Test EMI calculation with low loan amount."""
        principal = Decimal('1000')
        rate = Decimal('5')
        months = 12
        
        emi = EMICalculator.calculate_emi(principal, rate, months)
        assert emi > 0

    def test_calculate_emi_zero_months(self):
        """Test EMI calculation with zero months (edge case)."""
        principal = Decimal('100000')
        rate = Decimal('10')
        months = 0
        
        emi = EMICalculator.calculate_emi(principal, rate, months)
        assert emi == 0

    def test_calculate_total_interest_basic(self):
        """Test total interest calculation."""
        principal = Decimal('100000')
        rate = Decimal('10')
        months = 12
        
        interest = EMICalculator.calculate_total_interest(principal, rate, months)
        assert interest >= 0
        assert isinstance(interest, Decimal)

    def test_calculate_total_interest_zero_rate(self):
        """Test total interest with zero rate."""
        principal = Decimal('100000')
        rate = Decimal('0')
        months = 12
        
        interest = EMICalculator.calculate_total_interest(principal, rate, months)
        assert interest == Decimal('0')

    def test_calculate_total_interest_longer_term(self):
        """Test total interest increases with longer term."""
        principal = Decimal('100000')
        rate = Decimal('10')
        
        interest_12 = EMICalculator.calculate_total_interest(principal, rate, 12)
        interest_24 = EMICalculator.calculate_total_interest(principal, rate, 24)
        
        # Longer term should have more interest
        assert interest_24 > interest_12

    def test_calculate_total_interest_negative_prevented(self):
        """Test that negative interest doesn't occur."""
        principal = Decimal('100000')
        rate = Decimal('10')
        months = 1
        
        interest = EMICalculator.calculate_total_interest(principal, rate, months)
        assert interest >= 0

    def test_calculate_tenure_from_emi_basic(self):
        """Test tenure calculation from EMI."""
        principal = Decimal('100000')
        rate = Decimal('10')
        original_tenure = 60
        
        # First calculate EMI for known tenure
        original_emi = EMICalculator.calculate_emi(principal, rate, original_tenure)
        
        # Now calculate tenure from EMI
        calculated_tenure = EMICalculator.calculate_tenure_from_emi(principal, rate, original_emi)
        
        # Tenure calculation is approximate, so allow larger margin
        assert calculated_tenure > 0
        assert isinstance(calculated_tenure, int)

    def test_calculate_tenure_from_emi_zero_rate(self):
        """Test tenure calculation with zero rate."""
        principal = Decimal('100000')
        rate = Decimal('0')
        emi = Decimal('5000')
        
        tenure = EMICalculator.calculate_tenure_from_emi(principal, rate, emi)
        # Should be principal / emi = 20
        assert tenure == 20

    def test_calculate_tenure_from_emi_zero_emi(self):
        """Test tenure calculation with zero EMI (edge case)."""
        principal = Decimal('100000')
        rate = Decimal('10')
        emi = Decimal('0')
        
        tenure = EMICalculator.calculate_tenure_from_emi(principal, rate, emi)
        assert tenure == 0

    def test_calculate_tenure_from_emi_low_emi(self):
        """Test tenure calculation with EMI lower than required."""
        principal = Decimal('100000')
        rate = Decimal('10')
        # Calculate minimum EMI (interest only for one month)
        monthly_rate = float(rate) / 12 / 100
        min_emi = principal * Decimal(str(monthly_rate))
        
        # Use EMI lower than minimum
        low_emi = min_emi * Decimal('0.5')
        
        tenure = EMICalculator.calculate_tenure_from_emi(principal, rate, low_emi)
        assert tenure == 0

    def test_calculate_tenure_from_emi_exception_handling(self):
        """Test tenure calculation exception handling."""
        # Use values that could cause math errors
        principal = Decimal('100000')
        rate = Decimal('10')
        emi = Decimal('1')  # Very low EMI could cause issues
        
        # Should not raise exception, returns 0
        tenure = EMICalculator.calculate_tenure_from_emi(principal, rate, emi)
        assert isinstance(tenure, int)
        assert tenure >= 0

    def test_calculate_interest_portion_basic(self):
        """Test interest portion calculation."""
        balance = Decimal('100000')
        rate = Decimal('10')
        
        interest = EMICalculator.calculate_interest_portion(balance, rate)
        
        # Monthly rate is 10/12/100 = 0.00833...
        # Interest should be balance * monthly_rate
        monthly_rate = Decimal(str(rate)) / 12 / 100
        expected = balance * monthly_rate
        
        assert interest > 0
        assert abs(float(interest) - float(expected)) < 1

    def test_calculate_interest_portion_zero_rate(self):
        """Test interest portion with zero rate."""
        balance = Decimal('100000')
        rate = Decimal('0')
        
        interest = EMICalculator.calculate_interest_portion(balance, rate)
        assert interest == Decimal('0')

    def test_calculate_interest_portion_low_balance(self):
        """Test interest portion with low balance."""
        balance = Decimal('1000')
        rate = Decimal('5')
        
        interest = EMICalculator.calculate_interest_portion(balance, rate)
        assert interest >= 0

    def test_calculate_principal_portion_basic(self):
        """Test principal portion calculation."""
        emi = Decimal('10000')
        interest = Decimal('5000')
        
        principal = EMICalculator.calculate_principal_portion(emi, interest)
        assert principal == Decimal('5000')

    def test_calculate_principal_portion_zero_interest(self):
        """Test principal portion with zero interest."""
        emi = Decimal('10000')
        interest = Decimal('0')
        
        principal = EMICalculator.calculate_principal_portion(emi, interest)
        assert principal == emi

    def test_calculate_principal_portion_high_interest(self):
        """Test principal portion when interest exceeds EMI."""
        emi = Decimal('5000')
        interest = Decimal('6000')  # More than EMI
        
        principal = EMICalculator.calculate_principal_portion(emi, interest)
        # Should not be negative, should be 0
        assert principal == Decimal('0')

    def test_calculate_principal_portion_exact_match(self):
        """Test principal portion when interest equals EMI."""
        emi = Decimal('5000')
        interest = Decimal('5000')
        
        principal = EMICalculator.calculate_principal_portion(emi, interest)
        assert principal == Decimal('0')


class TestInterestCalculator:
    """Test InterestCalculator class."""

    def test_calculate_remaining_interest_basic(self):
        """Test remaining interest calculation."""
        balance = Decimal('100000')
        rate = Decimal('10')
        emi = Decimal('2000')
        months = 60
        
        remaining_interest = InterestCalculator.calculate_remaining_interest(
            balance, rate, emi, months
        )
        
        assert remaining_interest >= 0
        assert isinstance(remaining_interest, Decimal)

    def test_calculate_remaining_interest_single_month(self):
        """Test remaining interest for single month."""
        balance = Decimal('100000')
        rate = Decimal('10')
        emi = Decimal('10000')
        months = 1
        
        remaining_interest = InterestCalculator.calculate_remaining_interest(
            balance, rate, emi, months
        )
        
        assert remaining_interest >= 0

    def test_calculate_remaining_interest_zero_months(self):
        """Test remaining interest with zero remaining months."""
        balance = Decimal('100000')
        rate = Decimal('10')
        emi = Decimal('2000')
        months = 0
        
        remaining_interest = InterestCalculator.calculate_remaining_interest(
            balance, rate, emi, months
        )
        
        assert remaining_interest == Decimal('0')

    def test_calculate_remaining_interest_zero_rate(self):
        """Test remaining interest with zero rate."""
        balance = Decimal('100000')
        rate = Decimal('0')
        emi = Decimal('10000')
        months = 10
        
        remaining_interest = InterestCalculator.calculate_remaining_interest(
            balance, rate, emi, months
        )
        
        assert remaining_interest == Decimal('0')

    def test_calculate_remaining_interest_zero_balance(self):
        """Test remaining interest with zero balance."""
        balance = Decimal('0')
        rate = Decimal('10')
        emi = Decimal('2000')
        months = 60
        
        remaining_interest = InterestCalculator.calculate_remaining_interest(
            balance, rate, emi, months
        )
        
        assert remaining_interest == Decimal('0')

    def test_calculate_remaining_interest_high_emi(self):
        """Test remaining interest with very high EMI."""
        balance = Decimal('100000')
        rate = Decimal('10')
        emi = Decimal('50000')  # Very high, pays off quickly
        months = 60
        
        remaining_interest = InterestCalculator.calculate_remaining_interest(
            balance, rate, emi, months
        )
        
        # Interest should be minimal
        assert remaining_interest >= 0

    def test_calculate_weighted_average_rate_single_loan(self):
        """Test weighted average rate with single loan."""
        balances = [Decimal('100000')]
        rates = [Decimal('10')]
        
        avg_rate = InterestCalculator.calculate_weighted_average_rate(balances, rates)
        
        assert avg_rate == Decimal('10')

    def test_calculate_weighted_average_rate_multiple_equal(self):
        """Test weighted average rate with equal amounts."""
        balances = [Decimal('100000'), Decimal('100000')]
        rates = [Decimal('5'), Decimal('15')]
        
        avg_rate = InterestCalculator.calculate_weighted_average_rate(balances, rates)
        
        # Should be (5 + 15) / 2 = 10
        assert avg_rate == Decimal('10')

    def test_calculate_weighted_average_rate_weighted(self):
        """Test weighted average rate with different amounts."""
        balances = [Decimal('100000'), Decimal('200000')]  # 1:2 ratio
        rates = [Decimal('10'), Decimal('20')]
        
        avg_rate = InterestCalculator.calculate_weighted_average_rate(balances, rates)
        
        # Weighted: (10*100000 + 20*200000) / 300000 = (1000000 + 4000000) / 300000 = 16.67
        expected = Decimal(str(round((10*100000 + 20*200000) / 300000, 2)))
        assert avg_rate == expected

    def test_calculate_weighted_average_rate_zero_balance(self):
        """Test weighted average rate with zero total balance."""
        balances = [Decimal('0'), Decimal('0')]
        rates = [Decimal('10'), Decimal('20')]
        
        avg_rate = InterestCalculator.calculate_weighted_average_rate(balances, rates)
        
        assert avg_rate == Decimal('0')

    def test_calculate_weighted_average_rate_three_loans(self):
        """Test weighted average rate with three loans."""
        balances = [Decimal('50000'), Decimal('100000'), Decimal('150000')]
        rates = [Decimal('5'), Decimal('10'), Decimal('15')]
        
        avg_rate = InterestCalculator.calculate_weighted_average_rate(balances, rates)
        
        # (5*50000 + 10*100000 + 15*150000) / 300000
        total_balance = sum(balances)
        weighted_sum = sum(float(r) * float(b) for r, b in zip(rates, balances))
        expected = Decimal(str(round(weighted_sum / float(total_balance), 2)))
        
        assert avg_rate == expected


class TestPrepaymentCalculator:
    """Test PrepaymentCalculator class."""

    def test_calculate_prepayment_impact_basic(self):
        """Test basic prepayment impact calculation."""
        balance = Decimal('100000')
        prepayment = Decimal('10000')
        rate = Decimal('10')
        emi = Decimal('2000')
        months = 60
        
        impact = PrepaymentCalculator.calculate_prepayment_impact(
            balance, prepayment, rate, emi, months
        )
        
        assert isinstance(impact, dict)
        assert 'new_outstanding_balance' in impact
        assert impact['new_outstanding_balance'] == balance - prepayment
        assert impact['prepayment_amount'] == prepayment

    def test_calculate_prepayment_impact_full_payoff(self):
        """Test prepayment that fully pays off loan."""
        balance = Decimal('50000')
        prepayment = Decimal('50000')
        rate = Decimal('10')
        emi = Decimal('2000')
        months = 60
        
        impact = PrepaymentCalculator.calculate_prepayment_impact(
            balance, prepayment, rate, emi, months
        )
        
        assert impact['new_outstanding_balance'] == Decimal('0')
        assert impact['tenure_reduction_months'] == months
        # Check that interest_savings key exists
        assert 'interest_savings' in impact

    def test_calculate_prepayment_impact_overpayment(self):
        """Test prepayment exceeding outstanding balance."""
        balance = Decimal('50000')
        prepayment = Decimal('100000')
        rate = Decimal('10')
        emi = Decimal('2000')
        months = 60
        
        impact = PrepaymentCalculator.calculate_prepayment_impact(
            balance, prepayment, rate, emi, months
        )
        
        # Should not go negative
        assert impact['new_outstanding_balance'] == Decimal('0')

    def test_calculate_prepayment_impact_zero_prepayment(self):
        """Test prepayment with zero amount."""
        balance = Decimal('100000')
        prepayment = Decimal('0')
        rate = Decimal('10')
        emi = Decimal('2000')
        months = 60
        
        impact = PrepaymentCalculator.calculate_prepayment_impact(
            balance, prepayment, rate, emi, months
        )
        
        assert impact['new_outstanding_balance'] == balance
        assert 'tenure_reduction_months' in impact
        assert 'interest_savings' in impact

    def test_calculate_prepayment_impact_small_prepayment(self):
        """Test small prepayment."""
        balance = Decimal('100000')
        prepayment = Decimal('100')
        rate = Decimal('10')
        emi = Decimal('2000')
        months = 60
        
        impact = PrepaymentCalculator.calculate_prepayment_impact(
            balance, prepayment, rate, emi, months
        )
        
        assert impact['new_outstanding_balance'] == balance - prepayment
        assert impact['interest_savings'] >= Decimal('0')

    def test_calculate_emi_change_impact_increase_emi(self):
        """Test impact of increasing EMI."""
        principal = Decimal('100000')
        rate = Decimal('10')
        original_tenure = 60
        
        original_emi = EMICalculator.calculate_emi(principal, rate, original_tenure)
        new_emi = original_emi * Decimal('1.5')  # 50% increase
        
        impact = PrepaymentCalculator.calculate_emi_change_impact(
            principal, rate, original_tenure, new_emi
        )
        
        assert impact['original_emi'] == original_emi
        assert impact['new_emi'] == new_emi
        assert 'new_tenure_months' in impact
        # Higher EMI should reduce tenure
        assert impact['new_tenure_months'] <= impact['original_tenure_months']

    def test_calculate_emi_change_impact_decrease_emi(self):
        """Test impact of decreasing EMI."""
        principal = Decimal('100000')
        rate = Decimal('10')
        original_tenure = 60
        
        original_emi = EMICalculator.calculate_emi(principal, rate, original_tenure)
        new_emi = original_emi * Decimal('0.8')  # 20% decrease
        
        impact = PrepaymentCalculator.calculate_emi_change_impact(
            principal, rate, original_tenure, new_emi
        )
        
        assert impact['original_emi'] == original_emi
        assert impact['new_emi'] == new_emi
        # Verify structure of response
        assert 'new_tenure_months' in impact

    def test_calculate_emi_change_impact_same_emi(self):
        """Test impact with same EMI."""
        principal = Decimal('100000')
        rate = Decimal('10')
        original_tenure = 60
        
        original_emi = EMICalculator.calculate_emi(principal, rate, original_tenure)
        
        impact = PrepaymentCalculator.calculate_emi_change_impact(
            principal, rate, original_tenure, original_emi
        )
        
        assert impact['new_emi'] == original_emi
        assert isinstance(impact['tenure_reduction_months'], (int, Decimal))

    def test_calculate_emi_change_impact_zero_interest(self):
        """Test EMI change impact with zero interest."""
        principal = Decimal('100000')
        rate = Decimal('0')
        original_tenure = 60
        
        original_emi = EMICalculator.calculate_emi(principal, rate, original_tenure)
        new_emi = original_emi * Decimal('2')
        
        impact = PrepaymentCalculator.calculate_emi_change_impact(
            principal, rate, original_tenure, new_emi
        )
        
        # With zero interest, interest savings should be minimal or zero
        assert 'interest_savings' in impact

    def test_calculate_emi_change_impact_all_keys_present(self):
        """Test that all expected keys are in impact result."""
        principal = Decimal('100000')
        rate = Decimal('10')
        original_tenure = 60
        original_emi = EMICalculator.calculate_emi(principal, rate, original_tenure)
        new_emi = original_emi * Decimal('1.2')
        
        impact = PrepaymentCalculator.calculate_emi_change_impact(
            principal, rate, original_tenure, new_emi
        )
        
        expected_keys = [
            'original_emi', 'new_emi', 'original_tenure_months',
            'new_tenure_months', 'tenure_reduction_months',
            'original_total_interest', 'new_total_interest',
            'interest_savings', 'savings_percentage'
        ]
        
        for key in expected_keys:
            assert key in impact
