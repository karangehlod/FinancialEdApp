"""Tests for budget_service.py - comprehensive branch and code coverage."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.budget_service import (
    BudgetService,
    BudgetCalculator,
    FinancialProfileService
)
from app.repositories.budget_repository import BudgetRepository
from app.schemas.budget import BudgetCreate, BudgetUpdate
from app.schemas.financial_profile import FinancialProfileCreate
from app.db.models.data import Budget, UserFinancialProfile, BudgetAlert, Loan
from app.core.exceptions import ResourceNotFoundError


# ============== FIXTURES ==============

@pytest.fixture
def mock_db():
    """Create a mock AsyncSession."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_repository():
    """Create a mock BudgetRepository."""
    return AsyncMock(spec=BudgetRepository)


@pytest.fixture
def budget_calculator():
    """Create a BudgetCalculator instance."""
    return BudgetCalculator()


@pytest.fixture
def user_id():
    """Generate a test user ID."""
    return uuid4()


@pytest.fixture
def budget_id():
    """Generate a test budget ID."""
    return uuid4()


@pytest.fixture
def sample_budget(user_id, budget_id):
    """Create a sample Budget object."""
    return Budget(
        id=budget_id,
        user_id=user_id,
        month=date(2024, 1, 1),
        category="Food",
        allocated_amount=Decimal("1000.00"),
        spent_amount=Decimal("500.00"),
        recommended_amount=Decimal("800.00")
    )


@pytest.fixture
def budget_service(mock_db, mock_repository):
    """Create a BudgetService with mocked dependencies."""
    return BudgetService(
        db=mock_db,
        repository=mock_repository,
        calculator=BudgetCalculator(),
        financial_profile_service=None
    )


# ============== TESTS FOR BudgetCalculator ==============

class TestBudgetCalculator:
    """Test BudgetCalculator static methods."""
    
    def test_calculate_utilization_normal_usage(self, budget_calculator):
        """Test utilization calculation with normal spending."""
        result = budget_calculator.calculate_utilization(
            spent=Decimal("500"),
            allocated=Decimal("1000")
        )
        assert result == 50.0
    
    def test_calculate_utilization_full_usage(self, budget_calculator):
        """Test utilization when budget is fully used."""
        result = budget_calculator.calculate_utilization(
            spent=Decimal("1000"),
            allocated=Decimal("1000")
        )
        assert result == 100.0
    
    def test_calculate_utilization_over_budget(self, budget_calculator):
        """Test utilization when spending exceeds budget."""
        result = budget_calculator.calculate_utilization(
            spent=Decimal("1500"),
            allocated=Decimal("1000")
        )
        assert result == 150.0
    
    def test_calculate_utilization_zero_allocated(self, budget_calculator):
        """Test utilization with zero allocated budget."""
        result = budget_calculator.calculate_utilization(
            spent=Decimal("500"),
            allocated=Decimal("0")
        )
        assert result == 0.0
    
    def test_calculate_utilization_negative_allocated(self, budget_calculator):
        """Test utilization with negative allocated budget."""
        result = budget_calculator.calculate_utilization(
            spent=Decimal("500"),
            allocated=Decimal("-100")
        )
        assert result == 0.0
    
    def test_calculate_remaining_normal(self, budget_calculator):
        """Test remaining budget calculation."""
        result = budget_calculator.calculate_remaining(
            allocated=Decimal("1000"),
            spent=Decimal("300")
        )
        assert result == Decimal("700")
    
    def test_calculate_remaining_over_budget(self, budget_calculator):
        """Test remaining when over budget (negative result)."""
        result = budget_calculator.calculate_remaining(
            allocated=Decimal("1000"),
            spent=Decimal("1500")
        )
        assert result == Decimal("-500")
    
    def test_calculate_remaining_exact(self, budget_calculator):
        """Test remaining when exactly at budget."""
        result = budget_calculator.calculate_remaining(
            allocated=Decimal("1000"),
            spent=Decimal("1000")
        )
        assert result == Decimal("0")
    
    def test_determine_alert_level_ok(self, budget_calculator):
        """Test alert level when under threshold."""
        result = budget_calculator.determine_alert_level(
            utilization=75.0,
            threshold=80.0
        )
        assert result == "ok"
    
    def test_determine_alert_level_warning(self, budget_calculator):
        """Test alert level at warning threshold."""
        result = budget_calculator.determine_alert_level(
            utilization=85.0,
            threshold=80.0
        )
        assert result == "warning"
    
    def test_determine_alert_level_critical(self, budget_calculator):
        """Test alert level when critical."""
        result = budget_calculator.determine_alert_level(
            utilization=100.0,
            threshold=80.0
        )
        assert result == "critical"
    
    def test_determine_alert_level_critical_high(self, budget_calculator):
        """Test alert level when significantly over budget."""
        result = budget_calculator.determine_alert_level(
            utilization=150.0,
            threshold=80.0
        )
        assert result == "critical"
    
    def test_get_alert_message_critical(self, budget_calculator):
        """Test alert message for critical level."""
        result = budget_calculator.get_alert_message(
            alert_level="critical",
            category="Food"
        )
        assert result == "Food budget exceeded"
    
    def test_get_alert_message_warning(self, budget_calculator):
        """Test alert message for warning level."""
        result = budget_calculator.get_alert_message(
            alert_level="warning",
            category="Transport"
        )
        assert result == "Transport budget at warning threshold"
    
    def test_get_alert_message_ok(self, budget_calculator):
        """Test alert message for ok level."""
        result = budget_calculator.get_alert_message(
            alert_level="ok",
            category="Entertainment"
        )
        assert result == "Entertainment budget on track"


# ============== TESTS FOR FinancialProfileService ==============

class TestFinancialProfileService:
    """Test FinancialProfileService methods."""
    
    @pytest.fixture
    def financial_profile_service(self, mock_db):
        """Create a FinancialProfileService with mocked db."""
        return FinancialProfileService(mock_db)
    
    @pytest.mark.asyncio
    async def test_create_new_financial_profile_with_salary(self, mock_db, user_id):
        """Test creating a new financial profile with monthly salary."""
        service = FinancialProfileService(mock_db)
        
        profile_data = FinancialProfileCreate(
            monthly_salary=Decimal("100000"),
            rent=Decimal("20000"),
            insurance=Decimal("5000"),
            subscriptions=Decimal("2000")
        )
        
        # Mock no existing profile
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        
        # Mock EMI calculation (no active loans)
        mock_emi_result = MagicMock()
        mock_emi_result.scalar.return_value = None
        
        # Setup mock_db.execute to return different results
        call_count = [0]
        async def execute_side_effect(query):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_result  # Profile lookup
            return mock_emi_result  # EMI calculation
        
        mock_db.execute = AsyncMock(side_effect=execute_side_effect)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        result = await service.create_or_update(user_id, profile_data)
        
        # Verify profile was created
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        
        # Verify added profile has correct values
        created_profile = mock_db.add.call_args[0][0]
        assert created_profile.user_id == user_id
        assert created_profile.monthly_salary == Decimal("100000")
        # Disposable income = 100000 - (0 + 20000 + 5000 + 2000) = 73000
        assert created_profile.disposable_income == Decimal("73000")

    @pytest.mark.asyncio
    async def test_create_new_financial_profile_without_salary(self, mock_db, user_id):
        """Test creating a new financial profile without monthly salary."""
        service = FinancialProfileService(mock_db)
        
        profile_data = FinancialProfileCreate(
            monthly_salary=None,
            rent=Decimal("20000"),
            insurance=Decimal("5000")
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        
        mock_emi_result = MagicMock()
        mock_emi_result.scalar.return_value = None
        
        call_count = [0]
        async def execute_side_effect(query):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_result
            return mock_emi_result
        
        mock_db.execute = AsyncMock(side_effect=execute_side_effect)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        result = await service.create_or_update(user_id, profile_data)
        
        mock_db.add.assert_called_once()
        
        created_profile = mock_db.add.call_args[0][0]
        # Disposable income should be None if no salary
        assert created_profile.disposable_income is None

    @pytest.mark.asyncio
    async def test_update_existing_financial_profile(self, mock_db, user_id):
        """Test updating an existing financial profile."""
        service = FinancialProfileService(mock_db)
        
        # Existing profile
        existing_profile = MagicMock(spec=UserFinancialProfile)
        existing_profile.monthly_salary = Decimal("80000")
        existing_profile.rent = Decimal("15000")
        existing_profile.insurance = Decimal("3000")
        existing_profile.subscriptions = Decimal("1000")
        
        profile_data = FinancialProfileCreate(
            monthly_salary=Decimal("100000"),
            rent=Decimal("20000"),
            insurance=Decimal("5000"),
            subscriptions=Decimal("2000")
        )
        
        mock_profile_result = MagicMock()
        mock_profile_result.scalar_one_or_none.return_value = existing_profile
        
        mock_emi_result = MagicMock()
        mock_emi_result.scalar.return_value = Decimal("10000")
        
        call_count = [0]
        async def execute_side_effect(query):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_profile_result
            return mock_emi_result
        
        mock_db.execute = AsyncMock(side_effect=execute_side_effect)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        result = await service.create_or_update(user_id, profile_data)
        
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_financial_profile(self, mock_db, user_id):
        """Test retrieving a financial profile."""
        service = FinancialProfileService(mock_db)
        
        mock_profile = MagicMock(spec=UserFinancialProfile)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_profile
        
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await service.get(user_id)
        
        assert result == mock_profile
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_financial_profile_not_found(self, mock_db, user_id):
        """Test retrieving a non-existent financial profile."""
        service = FinancialProfileService(mock_db)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await service.get(user_id)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_calculate_total_emi_with_active_loans(self, mock_db, user_id):
        """Test calculating total EMI from active loans."""
        service = FinancialProfileService(mock_db)
        
        mock_result = MagicMock()
        mock_result.scalar.return_value = Decimal("25000")
        
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await service._calculate_total_emi(user_id)
        
        assert result == Decimal("25000")

    @pytest.mark.asyncio
    async def test_calculate_total_emi_no_loans(self, mock_db, user_id):
        """Test calculating total EMI when no loans exist."""
        service = FinancialProfileService(mock_db)
        
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await service._calculate_total_emi(user_id)
        
        # Should return 0 when no loans
        assert result == Decimal('0')

    @pytest.mark.asyncio
    async def test_update_from_loans_profile_exists(self, mock_db, user_id):
        """Test updating profile from loans when profile exists."""
        service = FinancialProfileService(mock_db)
        
        existing_profile = MagicMock(spec=UserFinancialProfile)
        existing_profile.monthly_salary = Decimal("100000")
        existing_profile.rent = Decimal("20000")
        existing_profile.insurance = Decimal("5000")
        existing_profile.subscriptions = Decimal("2000")
        existing_profile.total_emi = Decimal("0")
        existing_profile.disposable_income = Decimal("73000")
        
        mock_profile_result = MagicMock()
        mock_profile_result.scalar_one_or_none.return_value = existing_profile
        
        mock_emi_result = MagicMock()
        mock_emi_result.scalar.return_value = Decimal("15000")
        
        call_count = [0]
        async def execute_side_effect(query):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_emi_result  # First call for EMI calculation
            return mock_profile_result  # Second call for profile lookup
        
        mock_db.execute = AsyncMock(side_effect=execute_side_effect)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        result = await service.update_from_loans(user_id)
        
        # Verify profile was updated
        assert existing_profile.total_emi == Decimal("15000")
        # Disposable income should be recalculated: 100000 - (15000 + 20000 + 5000 + 2000) = 58000
        assert existing_profile.disposable_income == Decimal("58000")
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_from_loans_profile_not_exists(self, mock_db, user_id):
        """Test updating profile from loans when profile doesn't exist."""
        service = FinancialProfileService(mock_db)
        
        mock_profile_result = MagicMock()
        mock_profile_result.scalar_one_or_none.return_value = None
        
        mock_emi_result = MagicMock()
        mock_emi_result.scalar.return_value = Decimal("15000")
        
        call_count = [0]
        async def execute_side_effect(query):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_emi_result
            return mock_profile_result
        
        mock_db.execute = AsyncMock(side_effect=execute_side_effect)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        result = await service.update_from_loans(user_id)
        
        # Should return None if no profile
        assert result is None
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_from_loans_no_salary(self, mock_db, user_id):
        """Test updating profile from loans when profile has no salary."""
        service = FinancialProfileService(mock_db)
        
        existing_profile = MagicMock(spec=UserFinancialProfile)
        existing_profile.monthly_salary = None
        existing_profile.total_emi = Decimal("0")
        
        mock_profile_result = MagicMock()
        mock_profile_result.scalar_one_or_none.return_value = existing_profile
        
        mock_emi_result = MagicMock()
        mock_emi_result.scalar.return_value = Decimal("5000")
        
        call_count = [0]
        async def execute_side_effect(query):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_emi_result
            return mock_profile_result
        
        mock_db.execute = AsyncMock(side_effect=execute_side_effect)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        result = await service.update_from_loans(user_id)
        
        # Should update EMI but not recalculate disposable income without salary
        assert existing_profile.total_emi == Decimal("5000")
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_profile_with_active_loans(self, mock_db, user_id):
        """Test creating profile when user has active loans."""
        service = FinancialProfileService(mock_db)
        
        profile_data = FinancialProfileCreate(
            monthly_salary=Decimal("100000"),
            rent=Decimal("20000"),
            insurance=Decimal("5000"),
            subscriptions=Decimal("2000")
        )
        
        mock_profile_result = MagicMock()
        mock_profile_result.scalar_one_or_none.return_value = None
        
        mock_emi_result = MagicMock()
        mock_emi_result.scalar.return_value = Decimal("20000")  # Active loans with EMI
        
        call_count = [0]
        async def execute_side_effect(query):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_profile_result
            return mock_emi_result
        
        mock_db.execute = AsyncMock(side_effect=execute_side_effect)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        result = await service.create_or_update(user_id, profile_data)
        
        created_profile = mock_db.add.call_args[0][0]
        assert created_profile.total_emi == Decimal("20000")
        # Disposable income = 100000 - (20000 + 20000 + 5000 + 2000) = 53000
        assert created_profile.disposable_income == Decimal("53000")


# ============== TESTS FOR BudgetService ==============

class TestBudgetService:
    """Test BudgetService methods."""
    
    @pytest.mark.asyncio
    async def test_init_with_default_dependencies(self, mock_db):
        """Test initialization with defaults."""
        with patch('app.services.budget_service.BudgetRepository') as mock_repo_class:
            with patch('app.services.budget_service.FinancialProfileService'):
                mock_repo_class.return_value = AsyncMock()
                service = BudgetService(mock_db)
                
                assert service.db == mock_db
                assert service.repository is not None
                assert service.calculator is not None
                assert service.financial_profile_service is not None
    
    @pytest.mark.asyncio
    async def test_init_with_injected_dependencies(self, mock_db, mock_repository):
        """Test initialization with injected dependencies."""
        mock_calculator = BudgetCalculator()
        mock_fp_service = AsyncMock()
        
        service = BudgetService(
            db=mock_db,
            repository=mock_repository,
            calculator=mock_calculator,
            financial_profile_service=mock_fp_service
        )
        
        assert service.db == mock_db
        assert service.repository == mock_repository
        assert service.calculator == mock_calculator
        assert service.financial_profile_service == mock_fp_service
    
    @pytest.mark.asyncio
    async def test_validate_dependencies_success(self, budget_service):
        """Test successful dependency validation."""
        result = await budget_service.validate_dependencies()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_dependencies_missing_db(self, mock_repository):
        """Test validation fails without database."""
        service = BudgetService(
            db=None,
            repository=mock_repository
        )
        
        with pytest.raises(ValueError):
            await service.validate_dependencies()
    
    @pytest.mark.asyncio
    async def test_validate_dependencies_missing_repository(self, mock_db):
        """Test validation fails without repository."""
        with patch('app.services.budget_service.BudgetRepository') as mock_repo_class:
            with patch('app.services.budget_service.FinancialProfileService'):
                mock_repo_class.return_value = None
                service = BudgetService(db=mock_db, repository=None, calculator=BudgetCalculator())
                
                with pytest.raises(ValueError):
                    await service.validate_dependencies()
    
    @pytest.mark.asyncio
    async def test_create_budget(self, budget_service, user_id, budget_id):
        """Test creating a budget."""
        budget_data = BudgetCreate(
            month=date(2024, 1, 1),
            category="Food",
            allocated_amount=Decimal("1000")
        )
        
        budget = Budget(
            id=budget_id,
            user_id=user_id,
            **budget_data.model_dump()
        )
        
        budget_service.repository.create.return_value = budget
        
        result = await budget_service.create_budget(user_id, budget_data)
        
        assert result == budget
        budget_service.repository.create.assert_called_once_with(user_id, budget_data)
    
    @pytest.mark.asyncio
    async def test_get_budget(self, budget_service, user_id, budget_id, sample_budget):
        """Test retrieving a budget."""
        budget_service.repository.get_by_id.return_value = sample_budget
        
        result = await budget_service.get_budget(budget_id, user_id)
        
        assert result == sample_budget
        budget_service.repository.get_by_id.assert_called_once_with(budget_id, user_id)
    
    @pytest.mark.asyncio
    async def test_get_user_budgets(self, budget_service, user_id, sample_budget):
        """Test retrieving all user budgets."""
        budgets = [sample_budget]
        budget_service.repository.get_by_user.return_value = budgets
        
        result = await budget_service.get_user_budgets(user_id)
        
        assert result == budgets
        budget_service.repository.get_by_user.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_budgets_with_date_range(self, budget_service, user_id, sample_budget):
        """Test retrieving budgets with date filtering."""
        budgets = [sample_budget]
        budget_service.repository.get_by_user.return_value = budgets
        
        start_date = date(2024, 1, 1)
        end_date = date(2024, 12, 31)
        
        result = await budget_service.get_user_budgets(user_id, start_date, end_date)
        
        assert result == budgets
        budget_service.repository.get_by_user.assert_called_once_with(user_id, start_date, end_date)
    
    @pytest.mark.asyncio
    async def test_update_budget(self, budget_service, user_id, budget_id, sample_budget):
        """Test updating a budget."""
        update_data = BudgetUpdate(allocated_amount=Decimal("1500"))
        
        budget_service.repository.update.return_value = sample_budget
        
        result = await budget_service.update_budget(budget_id, user_id, update_data)
        
        assert result == sample_budget
        budget_service.repository.update.assert_called_once_with(budget_id, user_id, update_data)
    
    @pytest.mark.asyncio
    async def test_delete_budget(self, budget_service, user_id, budget_id):
        """Test deleting a budget."""
        budget_service.repository.delete.return_value = True
        
        result = await budget_service.delete_budget(budget_id, user_id)
        
        assert result is True
        budget_service.repository.delete.assert_called_once_with(budget_id, user_id)
    
    @pytest.mark.asyncio
    async def test_create_abstract_method_valid_data(self, budget_service, user_id, budget_id):
        """Test CRUD create abstract method with valid data."""
        budget_data = BudgetCreate(
            month=date(2024, 1, 1),
            category="Food",
            allocated_amount=Decimal("1000")
        )
        
        budget = Budget(id=budget_id, user_id=user_id, **budget_data.model_dump())
        budget_service.repository.create.return_value = budget
        
        data = {'user_id': user_id, 'budget_data': budget_data}
        result = await budget_service.create(data)
        
        assert result == budget
    
    @pytest.mark.asyncio
    async def test_create_abstract_method_invalid_data(self, budget_service):
        """Test CRUD create abstract method with invalid data."""
        with pytest.raises(ValueError):
            await budget_service.create({'invalid': 'data'})
    
    @pytest.mark.asyncio
    async def test_read_abstract_method_valid_id(self, budget_service, user_id, budget_id, sample_budget):
        """Test CRUD read abstract method with valid ID."""
        budget_service.repository.get_by_id.return_value = sample_budget
        
        resource_id = {'budget_id': budget_id, 'user_id': user_id}
        result = await budget_service.read(resource_id)
        
        assert result == sample_budget
    
    @pytest.mark.asyncio
    async def test_read_abstract_method_invalid_id(self, budget_service):
        """Test CRUD read abstract method with invalid ID."""
        with pytest.raises(ValueError):
            await budget_service.read({'invalid': 'id'})
    
    @pytest.mark.asyncio
    async def test_update_abstract_method_valid_data(self, budget_service, user_id, budget_id, sample_budget):
        """Test CRUD update abstract method with valid data."""
        budget_service.repository.update.return_value = sample_budget
        
        resource_id = {'budget_id': budget_id, 'user_id': user_id}
        update_data = BudgetUpdate(allocated_amount=Decimal("1500"))
        
        result = await budget_service.update(resource_id, update_data)
        
        assert result == sample_budget
    
    @pytest.mark.asyncio
    async def test_update_abstract_method_invalid_id(self, budget_service, sample_budget):
        """Test CRUD update abstract method with invalid ID."""
        with pytest.raises(ValueError):
            await budget_service.update({'invalid': 'id'}, sample_budget)
    
    @pytest.mark.asyncio
    async def test_update_abstract_method_invalid_data(self, budget_service, user_id, budget_id):
        """Test CRUD update abstract method with invalid data."""
        resource_id = {'budget_id': budget_id, 'user_id': user_id}
        
        with pytest.raises(ValueError):
            await budget_service.update(resource_id, {'invalid': 'data'})
    
    @pytest.mark.asyncio
    async def test_delete_abstract_method_valid_id(self, budget_service, user_id, budget_id):
        """Test CRUD delete abstract method with valid ID."""
        budget_service.repository.delete.return_value = True
        
        resource_id = {'budget_id': budget_id, 'user_id': user_id}
        result = await budget_service.delete(resource_id)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_delete_abstract_method_invalid_id(self, budget_service):
        """Test CRUD delete abstract method with invalid ID."""
        with pytest.raises(ValueError):
            await budget_service.delete({'invalid': 'id'})
    
    @pytest.mark.asyncio
    async def test_list_with_valid_filters(self, budget_service, user_id, sample_budget):
        """Test list method with valid filters."""
        budget_service.repository.get_by_user.return_value = [sample_budget]
        
        filters = {'user_id': user_id}
        result = await budget_service.list(filters=filters)
        
        assert result == [sample_budget]
    
    @pytest.mark.asyncio
    async def test_list_without_filters(self, budget_service):
        """Test list method without user_id filter."""
        with pytest.raises(ValueError):
            await budget_service.list()
    
    @pytest.mark.asyncio
    async def test_list_with_date_range(self, budget_service, user_id, sample_budget):
        """Test list method with date range in filters."""
        budget_service.repository.get_by_user.return_value = [sample_budget]
        
        filters = {
            'user_id': user_id,
            'start_date': date(2024, 1, 1),
            'end_date': date(2024, 12, 31)
        }
        result = await budget_service.list(filters=filters)
        
        assert result == [sample_budget]
        budget_service.repository.get_by_user.assert_called_once_with(
            user_id, 
            date(2024, 1, 1), 
            date(2024, 12, 31)
        )
    
    def test_calculate_budget_utilization(self, budget_service):
        """Test budget utilization calculation."""
        result = budget_service.calculate_budget_utilization(
            spent=Decimal("500"),
            allocated=Decimal("1000")
        )
        assert result == 50.0
    
    def test_calculate_remaining_budget(self, budget_service):
        """Test remaining budget calculation."""
        result = budget_service.calculate_remaining_budget(
            allocated=Decimal("1000"),
            spent=Decimal("300")
        )
        assert result == Decimal("700")
    
    @pytest.mark.asyncio
    async def test_get_user_alerts_all(self, mock_db, user_id):
        """Test retrieving all user alerts."""
        budget_service = BudgetService(db=mock_db, repository=AsyncMock(spec=BudgetRepository))
        
        alert_id = uuid4()
        alert = MagicMock(spec=BudgetAlert)
        alert.id = alert_id
        alert.user_id = user_id
        alert.is_read = False
        
        # Mock the execute result with proper scalars().all() chain
        mock_scalars_obj = MagicMock()
        mock_scalars_obj.all.return_value = [alert]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars_obj
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await budget_service.get_user_alerts(user_id)
        
        assert len(result) == 1
        assert result[0].id == alert_id
    
    @pytest.mark.asyncio
    async def test_get_user_alerts_unread_only(self, mock_db, user_id):
        """Test retrieving only unread alerts."""
        budget_service = BudgetService(db=mock_db, repository=AsyncMock(spec=BudgetRepository))
        
        alert_id = uuid4()
        alert = MagicMock(spec=BudgetAlert)
        alert.id = alert_id
        alert.is_read = False
        
        mock_scalars_obj = MagicMock()
        mock_scalars_obj.all.return_value = [alert]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars_obj
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await budget_service.get_user_alerts(user_id, unread_only=True)
        
        assert len(result) == 1
    
    @pytest.mark.asyncio
    async def test_mark_alert_as_read_success(self, mock_db, user_id):
        """Test marking an alert as read."""
        budget_service = BudgetService(db=mock_db, repository=AsyncMock(spec=BudgetRepository))
        
        alert_id = uuid4()
        alert = MagicMock(spec=BudgetAlert)
        alert.is_read = False
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = alert
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        
        result = await budget_service.mark_alert_as_read(alert_id, user_id)
        
        assert result is True
        assert alert.is_read is True
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_mark_alert_as_read_not_found(self, mock_db, user_id):
        """Test marking non-existent alert as read."""
        budget_service = BudgetService(db=mock_db, repository=AsyncMock(spec=BudgetRepository))
        
        alert_id = uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await budget_service.mark_alert_as_read(alert_id, user_id)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_budget_analytics_with_budgets(self, mock_db, mock_repository, user_id, sample_budget):
        """Test budget analytics calculation with data."""
        budget_service = BudgetService(db=mock_db, repository=mock_repository)
        
        budgets = [sample_budget]
        mock_repository.get_by_user.return_value = budgets
        
        mock_alert = MagicMock(spec=BudgetAlert)
        mock_scalars_obj = MagicMock()
        mock_scalars_obj.all.return_value = [mock_alert]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars_obj
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await budget_service.get_budget_analytics(
            user_id,
            date(2024, 1, 1),
            date(2024, 12, 31)
        )
        
        assert result['total_allocated'] == Decimal("1000.00")
        assert result['total_spent'] == Decimal("500.00")
        assert result['total_remaining'] == Decimal("500.00")
        assert result['total_budgets'] == 1
        assert len(result['categories']) == 1
        assert result['alerts_count'] == 1
    
    @pytest.mark.asyncio
    async def test_get_budget_analytics_no_budgets(self, budget_service, user_id):
        """Test budget analytics with no budgets."""
        budget_service.repository.get_by_user.return_value = []
        
        result = await budget_service.get_budget_analytics(
            user_id,
            date(2024, 1, 1),
            date(2024, 12, 31)
        )
        
        assert result['total_allocated'] == Decimal("0")
        assert result['total_spent'] == Decimal("0")
        assert result['total_remaining'] == Decimal("0")
        assert result['total_budgets'] == 0
        assert result['overall_utilization'] == Decimal("0")
    
    @pytest.mark.asyncio
    async def test_get_budget_analytics_over_budget(self, mock_db, mock_repository, user_id):
        """Test budget analytics with over-budget category."""
        budget_service = BudgetService(db=mock_db, repository=mock_repository)
        
        over_budget = Budget(
            id=uuid4(),
            user_id=user_id,
            month=date(2024, 1, 1),
            category="Food",
            allocated_amount=Decimal("500"),
            spent_amount=Decimal("750"),
            recommended_amount=None
        )
        
        mock_repository.get_by_user.return_value = [over_budget]
        
        mock_scalars_obj = MagicMock()
        mock_scalars_obj.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars_obj
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await budget_service.get_budget_analytics(
            user_id,
            date(2024, 1, 1),
            date(2024, 12, 31)
        )
        
        assert "Food" in result['over_budget_categories']
    
    @pytest.mark.asyncio
    async def test_create_or_update_financial_profile(self, budget_service, user_id):
        """Test creating/updating financial profile."""
        mock_fp_service = AsyncMock()
        budget_service.financial_profile_service = mock_fp_service
        
        profile_data = FinancialProfileCreate(
            monthly_salary=Decimal("50000"),
            rent=Decimal("10000"),
            insurance=Decimal("2000"),
            subscriptions=Decimal("1000")
        )
        
        mock_profile = MagicMock(spec=UserFinancialProfile)
        mock_fp_service.create_or_update.return_value = mock_profile
        
        result = await budget_service.create_or_update_financial_profile(user_id, profile_data)
        
        assert result == mock_profile
        mock_fp_service.create_or_update.assert_called_once_with(user_id, profile_data)
    
    @pytest.mark.asyncio
    async def test_get_financial_profile(self, budget_service, user_id):
        """Test retrieving financial profile."""
        mock_fp_service = AsyncMock()
        budget_service.financial_profile_service = mock_fp_service
        
        mock_profile = MagicMock(spec=UserFinancialProfile)
        mock_fp_service.get.return_value = mock_profile
        
        result = await budget_service.get_financial_profile(user_id)
        
        assert result == mock_profile
        mock_fp_service.get.assert_called_once_with(user_id)
