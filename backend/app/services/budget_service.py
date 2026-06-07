"""Refactored BudgetService following SOLID and OOP principles."""

from typing import Optional, List, Any
from uuid import UUID
from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.db.models.data import Budget, UserFinancialProfile, Loan, BudgetAlert
from app.schemas.budget import BudgetCreate, BudgetUpdate, BudgetWithAlert
from app.schemas.financial_profile import FinancialProfileCreate
from app.core.exceptions import ResourceNotFoundError
from app.repositories.budget_repository import BudgetRepository
from app.services.base_service import CRUDService


class BudgetCalculator:
    """Handles budget calculations - Single Responsibility Principle."""
    
    @staticmethod
    def calculate_utilization(spent: Decimal, allocated: Decimal) -> float:
        """Calculate utilization percentage."""
        if allocated <= 0:
            return 0.0
        return float((spent / allocated) * 100)
    
    @staticmethod
    def calculate_remaining(allocated: Decimal, spent: Decimal) -> Decimal:
        """Calculate remaining budget."""
        return allocated - spent
    
    @staticmethod
    def determine_alert_level(utilization: float, threshold: float = 80) -> str:
        """Determine alert level based on utilization."""
        if utilization >= 100:
            return "critical"
        elif utilization >= threshold:
            return "warning"
        return "ok"
    
    @staticmethod
    def get_alert_message(alert_level: str, category: str) -> str:
        """Get human-readable alert message."""
        if alert_level == "critical":
            return f"{category} budget exceeded"
        elif alert_level == "warning":
            return f"{category} budget at warning threshold"
        return f"{category} budget on track"


class FinancialProfileService:
    """Manages financial profile - handles profile-specific operations."""
    
    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db
    
    async def create_or_update(
        self,
        user_id: UUID,
        profile_data: FinancialProfileCreate
    ) -> UserFinancialProfile:
        """Create or update financial profile."""
        # Get existing profile
        result = await self.db.execute(
            select(UserFinancialProfile).where(
                UserFinancialProfile.user_id == user_id
            )
        )
        profile = result.scalar_one_or_none()
        
        # Calculate total EMI from loans
        total_emi = await self._calculate_total_emi(user_id)
        
        # Calculate disposable income
        fixed_expenses = (
            (total_emi or Decimal('0')) +
            (profile_data.rent or Decimal('0')) +
            (profile_data.insurance or Decimal('0')) +
            (profile_data.subscriptions or Decimal('0'))
        )
        
        disposable_income = None
        if profile_data.monthly_salary:
            disposable_income = profile_data.monthly_salary - fixed_expenses
        
        if profile:
            # Update existing
            for field, value in profile_data.model_dump().items():
                setattr(profile, field, value)
            profile.total_emi = total_emi
            profile.disposable_income = disposable_income
        else:
            # Create new - exclude total_emi and disposable_income from model_dump
            profile_dict = profile_data.model_dump(exclude={'total_emi', 'disposable_income'})
            profile = UserFinancialProfile(
                user_id=user_id,
                **profile_dict,
                total_emi=total_emi,
                disposable_income=disposable_income
            )
            self.db.add(profile)
        
        await self.db.commit()
        await self.db.refresh(profile)
        return profile
    
    async def get(self, user_id: UUID) -> Optional[UserFinancialProfile]:
        """Get user's financial profile."""
        result = await self.db.execute(
            select(UserFinancialProfile).where(
                UserFinancialProfile.user_id == user_id
            )
        )
        return result.scalar_one_or_none()
    
    async def _calculate_total_emi(self, user_id: UUID) -> Decimal:
        """Calculate total EMI from active loans."""
        result = await self.db.execute(
            select(func.sum(Loan.emi_amount)).where(
                and_(
                    Loan.user_id == user_id,
                    Loan.status == "active"
                )
            )
        )
        total = result.scalar()
        return total or Decimal('0')

    async def update_from_loans(self, user_id: UUID) -> Optional[UserFinancialProfile]:
        """Update financial profile based on current loans (e.g., total EMI)."""
        from datetime import datetime
        
        # Calculate total EMI from active loans
        total_emi = await self._calculate_total_emi(user_id)
        
        # Get and update financial profile
        result = await self.db.execute(
            select(UserFinancialProfile).where(
                UserFinancialProfile.user_id == user_id
            )
        )
        profile = result.scalar_one_or_none()
        
        if profile:
            profile.total_emi = total_emi
            # Recalculate disposable income
            if profile.monthly_salary:
                fixed_expenses = (
                    (total_emi or Decimal('0')) + 
                    (profile.rent or Decimal('0')) +
                    (profile.insurance or Decimal('0')) + 
                    (profile.subscriptions or Decimal('0'))
                )
                profile.disposable_income = profile.monthly_salary - fixed_expenses
            
            profile.updated_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(profile)
        
        return profile


class BudgetService(CRUDService[Budget]):
    """
    Main budget service — orchestrates all budget-related operations.

    Follows SOLID principles by delegating to specialized classes.
    Supports cache invalidation on all mutating operations (P0-9).
    """

    def __init__(
        self,
        db: AsyncSession,
        repository: Optional[BudgetRepository] = None,
        calculator: Optional[BudgetCalculator] = None,
        financial_profile_service: Optional[FinancialProfileService] = None,
        cache_service=None,
    ):
        super().__init__()
        self.db = db
        self.repository = repository or BudgetRepository(db)
        self.calculator = calculator or BudgetCalculator()
        self.financial_profile_service = (
            financial_profile_service or FinancialProfileService(db)
        )
        self._cache = cache_service
    
    async def validate_dependencies(self) -> bool:
        """Validate service dependencies."""
        if self.db is None or self.repository is None:
            raise ValueError("BudgetService requires database session and repository")
        return True
    
    # CRUD abstract methods implementation
    async def create(self, data: Any) -> Budget:
        """Create a new resource - delegates to create_budget."""
        if not isinstance(data, dict) or 'user_id' not in data or 'budget_data' not in data:
            raise ValueError("Invalid data for create operation")
        return await self.create_budget(data['user_id'], data['budget_data'])
    
    async def read(self, resource_id: Any) -> Optional[Budget]:
        """Read a resource by ID - delegates to get_budget."""
        if not isinstance(resource_id, dict) or 'budget_id' not in resource_id or 'user_id' not in resource_id:
            raise ValueError("Invalid ID for read operation")
        return await self.get_budget(resource_id['budget_id'], resource_id['user_id'])
    
    async def update(self, resource_id: Any, data: Any) -> Optional[Budget]:
        """Update a resource - delegates to update_budget."""
        if not isinstance(resource_id, dict) or 'budget_id' not in resource_id or 'user_id' not in resource_id:
            raise ValueError("Invalid ID for update operation")
        if not isinstance(data, BudgetUpdate):
            raise ValueError("Invalid data for update operation")
        return await self.update_budget(resource_id['budget_id'], resource_id['user_id'], data)
    
    async def delete(self, resource_id: Any) -> bool:
        """Delete a resource - delegates to delete_budget."""
        if not isinstance(resource_id, dict) or 'budget_id' not in resource_id or 'user_id' not in resource_id:
            raise ValueError("Invalid ID for delete operation")
        return await self.delete_budget(resource_id['budget_id'], resource_id['user_id'])
    
    async def list(
        self,
        skip: int = 0,
        limit: int = 10,
        filters: Optional[dict] = None
    ) -> List[Budget]:
        """List resources with pagination and filtering."""
        if not filters or 'user_id' not in filters:
            raise ValueError("user_id filter is required")
        
        user_id = filters['user_id']
        start_date = filters.get('start_date')
        end_date = filters.get('end_date')
        
        return await self.get_user_budgets(user_id, start_date, end_date)
    
    # Domain-specific business methods
    async def create_budget(self, user_id: UUID, budget_data: BudgetCreate) -> Budget:
        """Create a new budget and invalidate the budget cache."""
        result = await self.repository.create(user_id, budget_data)
        await self._invalidate_budget_cache(user_id)
        return result

    async def get_budget(self, budget_id: UUID, user_id: UUID) -> Optional[Budget]:
        """Get a specific budget."""
        return await self.repository.get_by_id(budget_id, user_id)

    async def get_user_budgets(
        self,
        user_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Budget]:
        """Get all budgets for a user."""
        return await self.repository.get_by_user(user_id, start_date, end_date)

    async def update_budget(
        self, budget_id: UUID, user_id: UUID, budget_data: BudgetUpdate
    ) -> Budget:
        """Update a budget and invalidate the budget cache."""
        result = await self.repository.update(budget_id, user_id, budget_data)
        await self._invalidate_budget_cache(user_id)
        return result

    async def delete_budget(self, budget_id: UUID, user_id: UUID) -> bool:
        """Delete a budget and invalidate the budget cache."""
        result = await self.repository.delete(budget_id, user_id)
        await self._invalidate_budget_cache(user_id)
        return result

    # ============== CACHE HELPERS ==============

    async def _invalidate_budget_cache(self, user_id: UUID) -> None:
        """Invalidate all cached budget data for this user."""
        if self._cache is None:
            return
        try:
            await self._cache.invalidate_user_budgets(str(user_id))
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Budget cache invalidation failed (non-fatal): %s", exc)
    
    async def create_or_update_financial_profile(
        self,
        user_id: UUID,
        profile_data: FinancialProfileCreate
    ) -> UserFinancialProfile:
        """Create or update financial profile."""
        return await self.financial_profile_service.create_or_update(user_id, profile_data)
    
    async def get_financial_profile(
        self,
        user_id: UUID
    ) -> Optional[UserFinancialProfile]:
        """Get financial profile."""
        return await self.financial_profile_service.get(user_id)
    
    def calculate_budget_utilization(
        self,
        spent: Decimal,
        allocated: Decimal
    ) -> float:
        """Calculate budget utilization percentage."""
        return self.calculator.calculate_utilization(spent, allocated)
    
    def calculate_remaining_budget(
        self,
        allocated: Decimal,
        spent: Decimal
    ) -> Decimal:
        """Calculate remaining budget."""
        return self.calculator.calculate_remaining(allocated, spent)

    async def get_user_alerts(
        self,
        user_id: UUID,
        unread_only: bool = False
    ) -> List:
        """Get user's budget alerts."""
        from sqlalchemy import select, desc
        query = select(BudgetAlert).where(BudgetAlert.user_id == user_id)
        
        if unread_only:
            query = query.where(BudgetAlert.is_read == False)
        
        query = query.order_by(desc(BudgetAlert.created_at))
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def mark_alert_as_read(
        self,
        alert_id: UUID,
        user_id: UUID
    ) -> bool:
        """Mark a budget alert as read."""
        result = await self.db.execute(
            select(BudgetAlert).where(
                and_(
                    BudgetAlert.id == alert_id,
                    BudgetAlert.user_id == user_id
                )
            )
        )
        alert = result.scalar_one_or_none()
        
        if not alert:
            return False
        
        alert.is_read = True
        await self.db.commit()
        return True
    
    async def get_budget_analytics(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date
    ) -> dict:
        """Get comprehensive budget analytics for a period."""
        budgets = await self.get_user_budgets(user_id, start_date, end_date)
        
        if not budgets:
            return {
                "total_allocated": Decimal("0"),
                "total_spent": Decimal("0"),
                "total_remaining": Decimal("0"),
                "total_budgets": 0,
                "overall_utilization": Decimal("0"),
                "categories": [],
                "alerts_count": 0,
                "over_budget_categories": []
            }
        
        # Calculate totals
        total_allocated = sum(b.allocated_amount for b in budgets)
        total_spent = sum(b.spent_amount for b in budgets)
        total_remaining = total_allocated - total_spent
        overall_utilization = (total_spent / total_allocated * 100) if total_allocated > Decimal("0") else Decimal("0")
        
        # Get alerts count
        alerts = await self.get_user_alerts(user_id)
        alerts_count = len(alerts)
        
        # Find over-budget categories
        over_budget = [b.category for b in budgets if b.spent_amount > b.allocated_amount]
        
        return {
            "total_allocated": total_allocated,
            "total_spent": total_spent,
            "total_remaining": total_remaining,
            "total_budgets": len(budgets),
            "overall_utilization": overall_utilization,
            "categories": [
                {
                    "category": b.category,
                    "allocated": b.allocated_amount,
                    "spent": b.spent_amount,
                    "remaining": b.allocated_amount - b.spent_amount,
                    "percentage": float((b.spent_amount / b.allocated_amount * 100)) if b.allocated_amount > 0 else 0.0
                }
                for b in budgets
            ],
            "alerts_count": alerts_count,
            "over_budget_categories": over_budget
        }
