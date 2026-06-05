"""
Service interfaces for SOLID compliance and dependency inversion.

Each domain service should implement one of these interfaces to ensure:
- Liskov Substitution Principle compliance
- Clear contracts for implementation
- Easier testing with mocks
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from datetime import date

from app.db.models.data import Expense, Budget, Loan, Goal, RecurringExpense
from app.schemas.expense import ExpenseCreate, ExpenseUpdate, ExpenseFilter
from app.schemas.budget import BudgetCreate, BudgetUpdate, BudgetWithAlert
from app.schemas.loan import LoanCreate, LoanUpdate, LoanResponse, LoanPaymentCreate
from app.schemas.goal import GoalCreate, GoalUpdate
from app.db.models.data import UserProfile


class IExpenseService(ABC):
    """Interface for expense service operations."""
    
    @abstractmethod
    async def create_expense(
        self,
        user_id: UUID,
        expense_data: ExpenseCreate,
    ) -> Expense:
        """Create a new expense and update related budget."""
        pass
    
    @abstractmethod
    async def get_expense(
        self,
        expense_id: UUID,
        user_id: UUID
    ) -> Optional[Expense]:
        """Get a specific expense by ID."""
        pass
    
    @abstractmethod
    async def get_user_expenses(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
        filters: Optional[ExpenseFilter] = None,
    ) -> tuple[List[Expense], int]:
        """Get all user expenses with pagination and filtering."""
        pass
    
    @abstractmethod
    async def update_expense(
        self,
        expense_id: UUID,
        user_id: UUID,
        expense_data: ExpenseUpdate,
    ) -> Expense:
        """Update an expense with validation and cache invalidation."""
        pass
    
    @abstractmethod
    async def delete_expense(
        self,
        expense_id: UUID,
        user_id: UUID
    ) -> bool:
        """Delete an expense (soft or hard delete)."""
        pass
    
    @abstractmethod
    async def get_expense_summary(
        self,
        user_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        """Get summary of expenses for a period."""
        pass


class IBudgetService(ABC):
    """Interface for budget service operations."""
    
    @abstractmethod
    async def create_budget(
        self,
        user_id: UUID,
        budget_data: BudgetCreate
    ) -> Budget:
        """Create a new budget for a user."""
        pass
    
    @abstractmethod
    async def get_budget(
        self,
        budget_id: UUID,
        user_id: UUID
    ) -> Optional[Budget]:
        """Get a specific budget by ID."""
        pass
    
    @abstractmethod
    async def get_user_budgets(
        self,
        user_id: UUID,
        month: Optional[str] = None
    ) -> List[Budget]:
        """Get all budgets for a user, optionally filtered by month."""
        pass
    
    @abstractmethod
    async def update_budget(
        self,
        budget_id: UUID,
        user_id: UUID,
        budget_data: BudgetUpdate
    ) -> Budget:
        """Update a budget."""
        pass
    
    @abstractmethod
    async def delete_budget(
        self,
        budget_id: UUID,
        user_id: UUID
    ) -> bool:
        """Delete a budget."""
        pass
    
    @abstractmethod
    async def get_budget_alerts(
        self,
        budget_id: UUID,
        user_id: UUID
    ) -> List[BudgetWithAlert]:
        """Get alerts for a budget."""
        pass


class ILoanService(ABC):
    """Interface for loan service operations."""
    
    @abstractmethod
    async def create_loan(
        self,
        user_id: UUID,
        loan_data: LoanCreate
    ) -> LoanResponse:
        """Create a new loan."""
        pass
    
    @abstractmethod
    async def get_loan(
        self,
        user_id: UUID,
        loan_id: UUID
    ) -> Optional[LoanResponse]:
        """Get a specific loan by ID."""
        pass
    
    @abstractmethod
    async def get_user_loans(
        self,
        user_id: UUID,
        status: Optional[str] = None
    ) -> List[LoanResponse]:
        """Get all loans for a user."""
        pass
    
    @abstractmethod
    async def update_loan(
        self,
        user_id: UUID,
        loan_id: UUID,
        loan_data: LoanUpdate
    ) -> Optional[LoanResponse]:
        """Update a loan."""
        pass
    
    @abstractmethod
    async def delete_loan(
        self,
        user_id: UUID,
        loan_id: UUID
    ) -> bool:
        """Delete a loan."""
        pass
    
    @abstractmethod
    async def add_payment(
        self,
        user_id: UUID,
        loan_id: UUID,
        payment_data: LoanPaymentCreate
    ) -> LoanResponse:
        """Record a loan payment."""
        pass


class IGoalService(ABC):
    """Interface for goal service operations."""
    
    @abstractmethod
    async def create_goal(
        self,
        user_id: UUID,
        goal_data: GoalCreate
    ) -> Goal:
        """Create a new financial goal."""
        pass
    
    @abstractmethod
    async def get_goal(
        self,
        goal_id: UUID,
        user_id: UUID
    ) -> Optional[Goal]:
        """Get a specific goal by ID."""
        pass
    
    @abstractmethod
    async def get_user_goals(
        self,
        user_id: UUID
    ) -> List[Goal]:
        """Get all goals for a user."""
        pass
    
    @abstractmethod
    async def update_goal(
        self,
        goal_id: UUID,
        user_id: UUID,
        goal_data: GoalUpdate
    ) -> Goal:
        """Update a goal."""
        pass
    
    @abstractmethod
    async def delete_goal(
        self,
        goal_id: UUID,
        user_id: UUID
    ) -> bool:
        """Delete a goal."""
        pass
    
    @abstractmethod
    async def update_goal_progress(
        self,
        goal_id: UUID,
        user_id: UUID,
        current_amount: Decimal
    ) -> Goal:
        """Update goal progress."""
        pass


class IRecurringExpenseService(ABC):
    """Interface for recurring expense service operations."""
    
    @abstractmethod
    async def create_recurring_expense(
        self,
        user_id: UUID,
        data: dict
    ) -> RecurringExpense:
        """Create a recurring expense."""
        pass
    
    @abstractmethod
    async def get_recurring_expenses(
        self,
        user_id: UUID
    ) -> List[RecurringExpense]:
        """Get all recurring expenses for a user."""
        pass
    
    @abstractmethod
    async def process_recurring_expenses(
        self,
        user_id: UUID
    ) -> List[Expense]:
        """Process due recurring expenses and create actual expenses."""
        pass


class IUserProfileService(ABC):
    """Interface for user profile service operations."""
    
    @abstractmethod
    async def create_profile(
        self,
        user_id: UUID,
        profile_data: dict
    ) -> UserProfile:
        """Create a user profile."""
        pass
    
    @abstractmethod
    async def get_profile(
        self,
        user_id: UUID
    ) -> Optional[UserProfile]:
        """Get user profile."""
        pass
    
    @abstractmethod
    async def update_profile(
        self,
        user_id: UUID,
        profile_data: dict
    ) -> UserProfile:
        """Update user profile."""
        pass
    
    @abstractmethod
    async def delete_profile(
        self,
        user_id: UUID
    ) -> bool:
        """Delete user profile."""
        pass


class IFinancialProfileService(ABC):
    """Interface for financial profile service operations."""
    
    @abstractmethod
    async def create_or_update(
        self,
        user_id: UUID,
        profile_data: dict
    ) -> dict:
        """Create or update financial profile."""
        pass
    
    @abstractmethod
    async def get(
        self,
        user_id: UUID
    ) -> Optional[dict]:
        """Get financial profile."""
        pass
    
    @abstractmethod
    async def update_from_loans(
        self,
        user_id: UUID
    ) -> Optional[dict]:
        """Update financial profile based on current loans."""
        pass
