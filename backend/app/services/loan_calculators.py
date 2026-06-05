"""Loan calculation components - implements Single Responsibility and Open/Closed principles."""
from decimal import Decimal
from typing import Tuple
import math


class EMICalculator:
    """Responsible for EMI calculations only."""
    
    @staticmethod
    def calculate_emi(principal: Decimal, annual_rate: Decimal, months: int) -> Decimal:
        """Calculate EMI using the standard formula.
        
        Formula: EMI = P * r * (1+r)^n / ((1+r)^n - 1)
        where P = principal, r = monthly rate, n = number of months
        """
        P = float(principal)
        r = float(annual_rate) / 12 / 100  # Monthly interest rate
        n = months
        
        if r > 0 and n > 0:
            emi = P * r * ((1 + r) ** n) / (((1 + r) ** n) - 1)
        elif n > 0:
            # If no interest, simple division
            emi = P / n
        else:
            emi = 0
        
        return Decimal(str(round(emi, 2)))
    
    @staticmethod
    def calculate_total_interest(principal: Decimal, annual_rate: Decimal, months: int) -> Decimal:
        """Calculate total interest payable over the loan term."""
        emi = EMICalculator.calculate_emi(principal, annual_rate, months)
        total_amount = emi * months
        total_interest = total_amount - principal
        return Decimal(str(round(max(0, total_interest), 2)))
    
    @staticmethod
    def calculate_tenure_from_emi(principal: Decimal, annual_rate: Decimal, current_emi: Decimal) -> int:
        """Calculate tenure in months given a target EMI."""
        P = float(principal)
        r = float(annual_rate) / 12 / 100
        emi = float(current_emi)
        
        if r <= 0:
            # No interest case
            return int(P / emi) if emi > 0 else 0
        
        if emi <= (P * r):
            # EMI too low to cover interest
            return 0
        
        # Use logarithm: n = log(1 + (P*r/EMI)) / log(1 + r)
        try:
            n = math.log(1 + (P * r / emi)) / math.log(1 + r)
            return math.ceil(n)
        except (ValueError, ZeroDivisionError):
            return 0
    
    @staticmethod
    def calculate_interest_portion(outstanding_balance: Decimal, annual_rate: Decimal) -> Decimal:
        """Calculate interest portion for one month."""
        monthly_rate = float(annual_rate) / 12 / 100
        interest = float(outstanding_balance) * monthly_rate
        return Decimal(str(round(interest, 2)))
    
    @staticmethod
    def calculate_principal_portion(emi_amount: Decimal, interest_portion: Decimal) -> Decimal:
        """Calculate principal portion from EMI and interest."""
        principal = emi_amount - interest_portion
        return Decimal(str(round(max(0, principal), 2)))


class InterestCalculator:
    """Calculates interest-related metrics."""
    
    @staticmethod
    def calculate_remaining_interest(
        outstanding_balance: Decimal, 
        annual_rate: Decimal, 
        emi_amount: Decimal, 
        remaining_months: int
    ) -> Decimal:
        """Calculate total remaining interest to be paid."""
        total_interest = Decimal('0')
        balance = float(outstanding_balance)
        monthly_rate = float(annual_rate) / 12 / 100
        emi = float(emi_amount)
        
        for _ in range(remaining_months):
            interest = balance * monthly_rate
            principal = min(emi - interest, balance)
            total_interest += Decimal(str(round(interest, 2)))
            balance -= principal
            
            if balance <= 0:
                break
        
        return total_interest
    
    @staticmethod
    def calculate_weighted_average_rate(
        loan_balances: list,
        loan_rates: list
    ) -> Decimal:
        """Calculate weighted average interest rate across multiple loans."""
        total_balance = sum(loan_balances)
        if total_balance == 0:
            return Decimal('0')
        
        weighted_sum = sum(
            float(rate) * float(balance) 
            for rate, balance in zip(loan_rates, loan_balances)
        )
        
        avg_rate = weighted_sum / float(total_balance)
        return Decimal(str(round(avg_rate, 2)))


class PrepaymentCalculator:
    """Calculates prepayment impact and savings."""
    
    @staticmethod
    def calculate_prepayment_impact(
        original_balance: Decimal,
        prepayment_amount: Decimal,
        annual_rate: Decimal,
        emi_amount: Decimal,
        remaining_months: int
    ) -> dict:
        """Calculate the impact of prepayment on loan tenure and interest."""
        new_balance = max(Decimal('0'), original_balance - prepayment_amount)
        
        # Calculate original remaining interest
        original_remaining_interest = InterestCalculator.calculate_remaining_interest(
            original_balance, annual_rate, emi_amount, remaining_months
        )
        
        # Calculate new remaining interest
        if new_balance > 0:
            new_tenure = EMICalculator.calculate_tenure_from_emi(
                new_balance, annual_rate, emi_amount
            )
            new_remaining_interest = InterestCalculator.calculate_remaining_interest(
                new_balance, annual_rate, emi_amount, new_tenure
            )
        else:
            new_remaining_interest = Decimal('0')
            new_tenure = 0
        
        # Calculate savings
        tenure_reduction = remaining_months - new_tenure
        interest_savings = original_remaining_interest - new_remaining_interest
        savings_percentage = (
            (interest_savings / original_remaining_interest * 100)
            if original_remaining_interest > 0
            else Decimal('100') if new_balance == 0 else Decimal('0')
        )
        
        return {
            'prepayment_amount': prepayment_amount,
            'new_outstanding_balance': new_balance,
            'tenure_reduction_months': tenure_reduction,
            'interest_savings': Decimal(str(round(interest_savings, 2))),
            'savings_percentage': Decimal(str(round(savings_percentage, 2))),
            'new_tenure_months': new_tenure
        }
    
    @staticmethod
    def calculate_emi_change_impact(
        principal: Decimal,
        annual_rate: Decimal,
        original_tenure_months: int,
        new_emi: Decimal
    ) -> dict:
        """Calculate impact of changing EMI on loan tenure and total interest."""
        # Original EMI and totals
        original_emi = EMICalculator.calculate_emi(principal, annual_rate, original_tenure_months)
        original_total_interest = EMICalculator.calculate_total_interest(
            principal, annual_rate, original_tenure_months
        )
        
        # New tenure based on new EMI
        new_tenure = EMICalculator.calculate_tenure_from_emi(principal, annual_rate, new_emi)
        new_total_interest = EMICalculator.calculate_total_interest(principal, annual_rate, new_tenure)
        
        # Calculate savings
        tenure_reduction = original_tenure_months - new_tenure
        interest_savings = original_total_interest - new_total_interest
        savings_percentage = (
            (interest_savings / original_total_interest * 100)
            if original_total_interest > 0
            else Decimal('0')
        )
        
        return {
            'original_emi': original_emi,
            'new_emi': new_emi,
            'original_tenure_months': original_tenure_months,
            'new_tenure_months': new_tenure,
            'tenure_reduction_months': tenure_reduction,
            'original_total_interest': original_total_interest,
            'new_total_interest': new_total_interest,
            'interest_savings': Decimal(str(round(interest_savings, 2))),
            'savings_percentage': Decimal(str(round(savings_percentage, 2)))
        }
