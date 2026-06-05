from sqlalchemy import Column, String, Boolean, DateTime, UUID, Integer, Numeric, Date, Text, ARRAY, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.db.session import DataBase
import uuid
from datetime import datetime, timezone


# P1-7: Soft delete mixin — allows deletion tracking without losing data
class SoftDeleteMixin:
    """Mixin that adds soft-delete capability to any model."""
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def soft_delete(self):
        """Mark the record as deleted without removing it from the database."""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self):
        """Restore a soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None


class UserProfile(DataBase):
    __tablename__ = "user_profiles"
    
    user_id = Column(UUID(as_uuid=True), primary_key=True)
    first_name = Column(String(255))  # ✅ Add first_name
    last_name = Column(String(255))   # ✅ Add last_name
    name = Column(String(255))
    country = Column(String(2), default='IN')
    currency = Column(String(3), default='INR')
    knowledge_level = Column(String(20))
    risk_tolerance = Column(String(20))
    consent_given = Column(Boolean, default=False)
    consent_timestamp = Column(DateTime(timezone=False))
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now())


class Expense(DataBase):
    __tablename__ = "expenses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user_profiles.user_id', ondelete='CASCADE'), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    category = Column(String(50), nullable=False)
    subcategory = Column(String(50))
    description = Column(Text)
    date = Column(Date, nullable=False)
    merchant = Column(String(255))
    payment_method = Column(String(50))
    is_recurring = Column(Boolean, default=False)
    # P1-7: Soft delete columns
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    
    def soft_delete(self):
        """Mark the expense as deleted without removing it from the database."""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
    
    def restore(self):
        """Restore a soft-deleted expense."""
        self.is_deleted = False
        self.deleted_at = None


class Budget(DataBase):
    __tablename__ = "budgets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user_profiles.user_id', ondelete='CASCADE'), nullable=False)
    month = Column(Date, nullable=False)
    category = Column(String(50), nullable=False)
    allocated_amount = Column(Numeric(15, 2))
    spent_amount = Column(Numeric(15, 2), default=0)
    recommended_amount = Column(Numeric(15, 2))
    # P1-7: Soft delete columns
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    
    def soft_delete(self):
        """Mark the budget as deleted without removing it from the database."""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
    
    def restore(self):
        """Restore a soft-deleted budget."""
        self.is_deleted = False
        self.deleted_at = None


class UserFinancialProfile(DataBase):
    __tablename__ = "user_financial_profiles"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('user_profiles.user_id', ondelete='CASCADE'), primary_key=True)
    monthly_salary = Column(Numeric(15, 2))
    currency = Column(String(3))
    total_emi = Column(Numeric(15, 2))
    rent = Column(Numeric(15, 2))
    insurance = Column(Numeric(15, 2))
    subscriptions = Column(Numeric(15, 2))
    disposable_income = Column(Numeric(15, 2))
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now())


class BudgetAlert(DataBase):
    __tablename__ = "budget_alerts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    budget_id = Column(UUID(as_uuid=True), ForeignKey('budgets.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user_profiles.user_id', ondelete='CASCADE'), nullable=False)
    alert_level = Column(String(20), nullable=False)
    message = Column(String(500), nullable=False)
    utilization_at_alert = Column(Numeric(5, 2), nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=False), server_default=func.now())


class Loan(DataBase):
    __tablename__ = "loans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user_profiles.user_id', ondelete='CASCADE'), nullable=False)
    loan_type = Column(String(50), nullable=False)  # home, car, personal, education, etc.
    lender_name = Column(String(255))
    principal_amount = Column(Numeric(15, 2), nullable=False)
    outstanding_balance = Column(Numeric(15, 2), nullable=False)
    interest_rate = Column(Numeric(5, 3), nullable=False)  # Annual interest rate as percentage
    emi_amount = Column(Numeric(15, 2), nullable=False)
    loan_term_months = Column(Integer, nullable=False)
    remaining_months = Column(Integer, nullable=False)
    start_date = Column(Date, nullable=False)
    next_due_date = Column(Date, nullable=False)
    status = Column(String(20), default='active')  # active, closed, defaulted
    description = Column(Text)
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now())


class LoanPayment(DataBase):
    __tablename__ = "loan_payments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loan_id = Column(UUID(as_uuid=True), ForeignKey('loans.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user_profiles.user_id', ondelete='CASCADE'), nullable=False)
    payment_date = Column(Date, nullable=False)
    amount_paid = Column(Numeric(15, 2), nullable=False)
    principal_amount = Column(Numeric(15, 2), nullable=False)
    interest_amount = Column(Numeric(15, 2), nullable=False)
    outstanding_balance = Column(Numeric(15, 2), nullable=False)
    is_prepayment = Column(Boolean, default=False)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=False), server_default=func.now())


class Goal(DataBase):
    __tablename__ = "goals"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user_profiles.user_id', ondelete='CASCADE'), nullable=False)
    goal_name = Column(String(255), nullable=False)
    goal_type = Column(String(50), nullable=False)  # savings, debt_payoff, investment, emergency_fund, other
    target_amount = Column(Numeric(15, 2), nullable=False)
    current_amount = Column(Numeric(15, 2), default=0)
    target_date = Column(Date, nullable=False)
    description = Column(Text)
    priority = Column(String(20), default='medium')  # high, medium, low
    status = Column(String(20), default='active')  # active, completed, paused, abandoned
    # P1-7: Soft delete columns
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now())
    
    def soft_delete(self):
        """Mark the goal as deleted without removing it from the database."""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
    
    def restore(self):
        """Restore a soft-deleted goal."""
        self.is_deleted = False
        self.deleted_at = None


class RecurringExpense(DataBase):
    __tablename__ = "recurring_expenses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user_profiles.user_id', ondelete='CASCADE'), nullable=False)
    expense_name = Column(String(255), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    category = Column(String(50), nullable=False)
    frequency = Column(String(20), nullable=False)  # daily, weekly, monthly, quarterly, yearly
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)  # NULL if no end date
    is_active = Column(Boolean, default=True)
    last_generated_date = Column(Date)
    description = Column(Text)
    # P1-7: Soft delete columns
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now())
    
    def soft_delete(self):
        """Mark the recurring expense as deleted without removing it from the database."""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
    
    def restore(self):
        """Restore a soft-deleted recurring expense."""
        self.is_deleted = False
        self.deleted_at = None


class IncomeSource(DataBase):
    __tablename__ = "income_sources"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user_profiles.user_id', ondelete='CASCADE'), nullable=False)
    source_name = Column(String(255), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    frequency = Column(String(20), nullable=False)  # one_time, weekly, monthly, quarterly, yearly
    income_type = Column(String(50), nullable=False)  # salary, bonus, freelance, investment, other
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)  # NULL if ongoing
    is_active = Column(Boolean, default=True)
    description = Column(Text)
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now())


class Notification(DataBase):
    __tablename__ = "notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user_profiles.user_id', ondelete='CASCADE'), nullable=False)
    notification_type = Column(String(50), nullable=False)  # budget_alert, loan_reminder, expense_alert, goal_milestone
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    related_resource_id = Column(UUID(as_uuid=True))  # budget_id, loan_id, goal_id, etc.
    related_resource_type = Column(String(50))  # budget, loan, goal, expense, etc.
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now())
