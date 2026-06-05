"""Loan validation components - implements Single Responsibility principle."""
from decimal import Decimal
from datetime import date


class LoanAmountValidator:
    """Validates loan amount constraints."""
    
    # Configurable limits
    MIN_LOAN_AMOUNT = Decimal('1000')
    MAX_LOAN_AMOUNT = Decimal('10000000')
    
    @classmethod
    def validate(cls, amount: Decimal) -> tuple[bool, str]:
        """Validate loan amount.
        
        Returns:
            (is_valid, error_message)
        """
        if amount < cls.MIN_LOAN_AMOUNT:
            return False, f"Loan amount must be at least {cls.MIN_LOAN_AMOUNT}"
        
        if amount > cls.MAX_LOAN_AMOUNT:
            return False, f"Loan amount cannot exceed {cls.MAX_LOAN_AMOUNT}"
        
        return True, ""
    
    @classmethod
    def is_valid(cls, amount: Decimal) -> bool:
        """Quick validation check."""
        return cls.MIN_LOAN_AMOUNT <= amount <= cls.MAX_LOAN_AMOUNT


class InterestRateValidator:
    """Validates interest rate constraints."""
    
    # Configurable limits
    MIN_RATE = Decimal('0')
    MAX_RATE = Decimal('30')
    
    @classmethod
    def validate(cls, rate: Decimal) -> tuple[bool, str]:
        """Validate interest rate.
        
        Returns:
            (is_valid, error_message)
        """
        if rate < cls.MIN_RATE:
            return False, f"Interest rate cannot be negative"
        
        if rate > cls.MAX_RATE:
            return False, f"Interest rate cannot exceed {cls.MAX_RATE}%"
        
        return True, ""
    
    @classmethod
    def is_valid(cls, rate: Decimal) -> bool:
        """Quick validation check."""
        return cls.MIN_RATE <= rate <= cls.MAX_RATE


class LoanTermValidator:
    """Validates loan term constraints."""
    
    # Configurable limits (in months)
    MIN_TERM_MONTHS = 6  # 6 months
    MAX_TERM_MONTHS = 360  # 30 years
    
    @classmethod
    def validate(cls, months: int) -> tuple[bool, str]:
        """Validate loan term.
        
        Returns:
            (is_valid, error_message)
        """
        if months < cls.MIN_TERM_MONTHS:
            return False, f"Loan term must be at least {cls.MIN_TERM_MONTHS} months"
        
        if months > cls.MAX_TERM_MONTHS:
            return False, f"Loan term cannot exceed {cls.MAX_TERM_MONTHS} months"
        
        return True, ""
    
    @classmethod
    def is_valid(cls, months: int) -> bool:
        """Quick validation check."""
        return cls.MIN_TERM_MONTHS <= months <= cls.MAX_TERM_MONTHS


class LoanValidator:
    """Composite validator for all loan parameters."""
    
    amount_validator = LoanAmountValidator()
    rate_validator = InterestRateValidator()
    term_validator = LoanTermValidator()
    
    @classmethod
    def validate_all(cls, principal: Decimal, interest_rate: Decimal, term_months: int) -> tuple[bool, list[str]]:
        """Validate all loan parameters.
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        amount_valid, amount_error = cls.amount_validator.validate(principal)
        if not amount_valid:
            errors.append(amount_error)
        
        rate_valid, rate_error = cls.rate_validator.validate(interest_rate)
        if not rate_valid:
            errors.append(rate_error)
        
        term_valid, term_error = cls.term_validator.validate(term_months)
        if not term_valid:
            errors.append(term_error)
        
        return len(errors) == 0, errors


class DateValidator:
    """Validates date-related constraints for loans."""
    
    @staticmethod
    def validate_start_date(start_date: date) -> tuple[bool, str]:
        """Validate loan start date."""
        if start_date > date.today():
            return False, "Loan start date cannot be in the future"
        
        return True, ""
    
    @staticmethod
    def validate_payment_date(loan_start_date: date, payment_date: date) -> tuple[bool, str]:
        """Validate payment date relative to loan start date."""
        if payment_date < loan_start_date:
            return False, "Payment date cannot be before loan start date"
        
        return True, ""
    
    @staticmethod
    def validate_due_date(due_date: date) -> tuple[bool, str]:
        """Validate due date."""
        if due_date < date.today():
            return False, "Due date cannot be in the past"
        
        return True, ""
