"""Repository pattern interfaces for better testability."""

from abc import ABC, abstractmethod
from typing import Optional, List, Union, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import User
from app.db.models.data import UserProfile, Budget, Expense, Loan
from app.schemas.auth import UserCreate
from app.schemas.user_profile import UserProfileCreate, UserProfileUpdate
from app.schemas.budget import BudgetCreate, BudgetUpdate
from app.schemas.expense import ExpenseCreate, ExpenseUpdate
from app.schemas.loan import LoanCreate, LoanUpdate, LoanPaymentCreate


class IUserRepository(ABC):
    """Interface for user repository operations."""
    
    @abstractmethod
    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        pass
    
    @abstractmethod
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        pass
    
    @abstractmethod
    async def get_user_by_id(self, user_id: Union[str, UUID]) -> Optional[User]:
        """Get user by ID."""
        pass
    
    @abstractmethod
    async def update_last_login(self, user_id: UUID) -> None:
        """Update user's last login timestamp."""
        pass
    
    @abstractmethod
    async def delete_user(self, user_id: UUID) -> bool:
        """Delete a user."""
        pass


class IUserProfileRepository(ABC):
    """Interface for user profile repository operations."""
    
    @abstractmethod
    async def create_profile(self, user_id: UUID, profile_data: Optional[UserProfileCreate] = None) -> UserProfile:
        """Create a user profile."""
        pass
    
    @abstractmethod
    async def get_profile_by_user_id(self, user_id: UUID) -> Optional[UserProfile]:
        """Get user profile by user ID."""
        pass
    
    @abstractmethod
    async def update_profile(self, user_id: UUID, profile_data: UserProfileUpdate) -> Optional[UserProfile]:
        """Update user profile."""
        pass
    
    @abstractmethod
    async def delete_profile(self, user_id: UUID) -> bool:
        """Delete user profile."""
        pass


class IBudgetRepository(ABC):
    """Interface for budget repository operations."""
    
    @abstractmethod
    async def create_budget(self, user_id: UUID, budget_data: BudgetCreate) -> Budget:
        """Create a budget."""
        pass
    
    @abstractmethod
    async def get_budgets_by_user_id(self, user_id: UUID) -> List[Budget]:
        """Get all budgets for a user."""
        pass
    
    @abstractmethod
    async def get_budget_by_id(self, budget_id: UUID) -> Optional[Budget]:
        """Get budget by ID."""
        pass
    
    @abstractmethod
    async def update_budget(self, budget_id: UUID, budget_data: BudgetUpdate) -> Optional[Budget]:
        """Update a budget."""
        pass
    
    @abstractmethod
    async def delete_budget(self, budget_id: UUID) -> bool:
        """Delete a budget."""
        pass


class IExpenseRepository(ABC):
    """Interface for expense repository operations."""
    
    @abstractmethod
    async def create_expense(self, user_id: UUID, expense_data: ExpenseCreate) -> Expense:
        """Create an expense."""
        pass
    
    @abstractmethod
    async def get_expenses_by_user_id(self, user_id: UUID) -> List[Expense]:
        """Get all expenses for a user."""
        pass
    
    @abstractmethod
    async def get_expense_by_id(self, expense_id: UUID) -> Optional[Expense]:
        """Get expense by ID."""
        pass
    
    @abstractmethod
    async def update_expense(self, expense_id: UUID, expense_data: ExpenseUpdate) -> Optional[Expense]:
        """Update an expense."""
        pass
    
    @abstractmethod
    async def delete_expense(self, expense_id: UUID) -> bool:
        """Delete an expense."""
        pass


class ILoanRepository(ABC):
    """Interface for loan repository operations."""

    @abstractmethod
    async def create_loan(self, user_id: UUID, loan_data: LoanCreate) -> Loan:
        """Create a loan for a user."""
        pass

    @abstractmethod
    async def get_loan_by_id(self, loan_id: UUID, user_id: UUID) -> Optional[Loan]:
        """Get a loan by ID for a specific user."""
        pass

    @abstractmethod
    async def get_loans_by_user(self, user_id: UUID, status: Optional[str] = None) -> List[Loan]:
        """Get loans for a user, optionally filtered by status."""
        pass

    @abstractmethod
    async def update_loan(self, loan_id: UUID, user_id: UUID, loan_data: LoanUpdate) -> Optional[Loan]:
        """Update a user's loan."""
        pass

    @abstractmethod
    async def delete_loan(self, loan_id: UUID, user_id: UUID) -> bool:
        """Delete a user's loan."""
        pass

    @abstractmethod
    async def get_loan_payments(self, loan_id: UUID) -> List[Any]:
        """Get payment history for a loan."""
        pass

    @abstractmethod
    async def create_payment(
        self,
        loan_id: UUID,
        user_id: UUID,
        payment_data: LoanPaymentCreate,
        principal_amount: float,
        interest_amount: float,
        outstanding_balance: float,
    ) -> Any:
        """Create a payment against a loan."""
        pass

    @abstractmethod
    async def get_loans_due_soon(self, days_ahead: int = 7) -> List[Loan]:
        """Get loans with due dates approaching soon."""
        pass

    @abstractmethod
    async def get_overdue_loans(self) -> List[Loan]:
        """Get overdue loans."""
        pass
