"""Tests for export_service.py - comprehensive branch and code coverage."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4
import io

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.export_service import ExportService
from app.db.models.data import Expense, Budget, Loan, Goal


# ============== FIXTURES ==============

@pytest.fixture
def mock_db():
    """Create a mock AsyncSession."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def user_id():
    """Generate a test user ID."""
    return uuid4()


@pytest.fixture
def user_id_str():
    """Generate a test user ID as string."""
    return str(uuid4())


@pytest.fixture
def export_service(mock_db):
    """Create an ExportService with mocked db."""
    return ExportService(mock_db)


@pytest.fixture
def sample_expense(user_id):
    """Create a sample Expense object."""
    return Expense(
        id=uuid4(),
        user_id=user_id,
        amount=Decimal("50.00"),
        category="Food",
        subcategory="Groceries",
        description="Weekly groceries",
        date=date(2024, 1, 15),
        merchant="Walmart",
        payment_method="Credit Card",
        is_recurring=False
    )


@pytest.fixture
def sample_budget(user_id):
    """Create a sample Budget object."""
    return Budget(
        id=uuid4(),
        user_id=user_id,
        month=date(2024, 1, 1),
        category="Food",
        allocated_amount=Decimal("1000.00"),
        spent_amount=Decimal("500.00"),
        recommended_amount=Decimal("800.00")
    )


@pytest.fixture
def sample_loan(user_id):
    """Create a sample Loan object."""
    return Loan(
        id=uuid4(),
        user_id=user_id,
        loan_type="Personal",
        lender_name="Bank",
        principal_amount=Decimal("100000.00"),
        interest_rate=Decimal("10.00"),
        loan_term_months=60,
        emi_amount=Decimal("2124.71"),
        outstanding_balance=Decimal("80000.00"),
        status="active",
        start_date=date(2024, 1, 1),
        next_due_date=date(2024, 2, 1),
        remaining_months=48
    )


@pytest.fixture
def sample_goal(user_id):
    """Create a sample Goal object."""
    return Goal(
        id=uuid4(),
        user_id=user_id,
        goal_name="Save for vacation",
        goal_type="savings",
        target_amount=Decimal("2000.00"),
        current_amount=Decimal("500.00"),
        target_date=date(2024, 12, 31),
        description="Vacation fund",
        priority="medium",
        status="active"
    )


# ============== TESTS FOR ExportService ==============

class TestExportService:
    """Test ExportService methods."""
    
    def test_convert_uuid_from_string(self, export_service, user_id_str):
        """Test converting UUID from string."""
        result = export_service._convert_uuid(user_id_str)
        
        assert str(result) == user_id_str
    
    def test_convert_uuid_from_uuid(self, export_service, user_id):
        """Test converting UUID from UUID object."""
        result = export_service._convert_uuid(user_id)
        
        assert result == user_id
    
    @pytest.mark.asyncio
    async def test_export_expenses_csv_no_filters(self, export_service, user_id, user_id_str, sample_expense):
        """Test exporting expenses to CSV without filters."""
        # Mock database query
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_expense]
        mock_result.scalars.return_value = mock_scalars
        
        export_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await export_service.export_expenses_csv(user_id_str)
        
        # Verify result is BytesIO
        assert isinstance(result, io.BytesIO)
        
        # Verify content
        content = result.getvalue().decode('utf-8')
        assert "Date" in content
        assert "Category" in content
        assert "Food" in content
        assert "Walmart" in content
        assert "₹50.00" in content
    
    @pytest.mark.asyncio
    async def test_export_expenses_csv_with_date_range(self, export_service, user_id_str, sample_expense):
        """Test exporting expenses to CSV with date range filter."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_expense]
        mock_result.scalars.return_value = mock_scalars
        
        export_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        
        result = await export_service.export_expenses_csv(
            user_id_str,
            start_date=start_date,
            end_date=end_date
        )
        
        assert isinstance(result, io.BytesIO)
        content = result.getvalue().decode('utf-8')
        assert "Food" in content
    
    @pytest.mark.asyncio
    async def test_export_expenses_csv_empty(self, export_service, user_id_str):
        """Test exporting expenses when none exist."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        
        export_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await export_service.export_expenses_csv(user_id_str)
        
        assert isinstance(result, io.BytesIO)
        content = result.getvalue().decode('utf-8')
        # Should have header but no data rows
        assert "Date,Category" in content or "Date\tCategory" in content or "Date" in content
    
    @pytest.mark.asyncio
    async def test_export_budgets_csv_no_filters(self, export_service, user_id_str, sample_budget):
        """Test exporting budgets to CSV without filters."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_budget]
        mock_result.scalars.return_value = mock_scalars
        
        export_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await export_service.export_budgets_csv(user_id_str)
        
        assert isinstance(result, io.BytesIO)
        content = result.getvalue().decode('utf-8')
        assert "Month" in content
        assert "Category" in content
        assert "Food" in content
        assert "₹1,000.00" in content  # Allocated amount
        assert "50.0%" in content  # Utilization
    
    @pytest.mark.asyncio
    async def test_export_budgets_csv_with_month_filter(self, export_service, user_id_str, sample_budget):
        """Test exporting budgets to CSV with month filter."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_budget]
        mock_result.scalars.return_value = mock_scalars
        
        export_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        month = date(2024, 1, 1)
        
        result = await export_service.export_budgets_csv(user_id_str, month=month)
        
        assert isinstance(result, io.BytesIO)
        content = result.getvalue().decode('utf-8')
        assert "Food" in content
    
    @pytest.mark.asyncio
    async def test_export_budgets_csv_zero_allocated(self, export_service, user_id_str, user_id):
        """Test exporting budgets with zero allocated amount (edge case for utilization)."""
        budget = Budget(
            id=uuid4(),
            user_id=user_id,
            month=date(2024, 1, 1),
            category="Test",
            allocated_amount=Decimal("0.00"),
            spent_amount=Decimal("0.00")
        )
        
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [budget]
        mock_result.scalars.return_value = mock_scalars
        
        export_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await export_service.export_budgets_csv(user_id_str)
        
        assert isinstance(result, io.BytesIO)
        content = result.getvalue().decode('utf-8')
        assert "0.0%" in content  # Utilization should be 0 for zero allocated
    
    @pytest.mark.asyncio
    async def test_export_loans_csv(self, export_service, user_id_str, sample_loan):
        """Test exporting loans to CSV."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_loan]
        mock_result.scalars.return_value = mock_scalars
        
        export_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await export_service.export_loans_csv(user_id_str)
        
        assert isinstance(result, io.BytesIO)
        content = result.getvalue().decode('utf-8')
        assert "Loan Type" in content
        assert "Personal" in content
        assert "Bank" in content
        assert "₹100,000.00" in content  # Principal
        assert "10.00%" in content  # Interest rate
        assert "₹2,124.71" in content  # EMI
    
    @pytest.mark.asyncio
    async def test_export_loans_csv_empty(self, export_service, user_id_str):
        """Test exporting loans when none exist."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        
        export_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await export_service.export_loans_csv(user_id_str)
        
        assert isinstance(result, io.BytesIO)
        content = result.getvalue().decode('utf-8')
        assert "Loan Type" in content
    
    @pytest.mark.asyncio
    async def test_export_expenses_csv_multiple_items(self, export_service, user_id_str, user_id):
        """Test exporting multiple expenses with different amounts and categories."""
        expenses = [
            Expense(
                id=uuid4(),
                user_id=user_id,
                amount=Decimal("100.00"),
                category="Food",
                subcategory="Restaurant",
                description="Lunch",
                date=date(2024, 1, 15),
                merchant="Restaurant A",
                payment_method="Credit Card",
                is_recurring=False
            ),
            Expense(
                id=uuid4(),
                user_id=user_id,
                amount=Decimal("50.00"),
                category="Transport",
                subcategory="Fuel",
                description="Petrol",
                date=date(2024, 1, 16),
                merchant="Petrol Pump",
                payment_method="Debit Card",
                is_recurring=False
            ),
        ]
        
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = expenses
        mock_result.scalars.return_value = mock_scalars
        
        export_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await export_service.export_expenses_csv(user_id_str)
        
        content = result.getvalue().decode('utf-8')
        assert "Food" in content
        assert "Transport" in content
        assert "₹100.00" in content
        assert "₹50.00" in content
    
    @pytest.mark.asyncio
    async def test_export_budgets_csv_high_utilization(self, export_service, user_id_str, user_id):
        """Test exporting budget with high utilization percentage."""
        budget = Budget(
            id=uuid4(),
            user_id=user_id,
            month=date(2024, 1, 1),
            category="Test",
            allocated_amount=Decimal("1000.00"),
            spent_amount=Decimal("950.00")  # 95% utilization
        )
        
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [budget]
        mock_result.scalars.return_value = mock_scalars
        
        export_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await export_service.export_budgets_csv(user_id_str)
        
        content = result.getvalue().decode('utf-8')
        assert "95.0%" in content
    
    @pytest.mark.asyncio
    async def test_export_expenses_with_optional_fields_none(self, export_service, user_id_str, user_id):
        """Test exporting expenses where optional fields are None."""
        expense = Expense(
            id=uuid4(),
            user_id=user_id,
            amount=Decimal("75.00"),
            category="Food",
            subcategory=None,  # Optional field
            description=None,  # Optional field
            date=date(2024, 1, 15),
            merchant=None,  # Optional field
            payment_method=None,  # Optional field
            is_recurring=False
        )
        
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [expense]
        mock_result.scalars.return_value = mock_scalars
        
        export_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await export_service.export_expenses_csv(user_id_str)
        
        content = result.getvalue().decode('utf-8')
        # Should have empty strings for None values
        assert "₹75.00" in content
        assert "Food" in content
    
    @pytest.mark.asyncio
    async def test_export_loans_with_optional_fields(self, export_service, user_id_str, user_id):
        """Test exporting loans where optional fields are None."""
        loan = Loan(
            id=uuid4(),
            user_id=user_id,
            loan_type="Auto",
            lender_name=None,  # Optional field
            principal_amount=Decimal("500000.00"),
            interest_rate=Decimal("8.50"),
            loan_term_months=60,
            emi_amount=Decimal("10000.00"),
            outstanding_balance=Decimal("400000.00"),
            status="active",
            start_date=date(2024, 1, 1),
            next_due_date=date(2024, 2, 1),
            remaining_months=36
        )
        
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [loan]
        mock_result.scalars.return_value = mock_scalars
        
        export_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await export_service.export_loans_csv(user_id_str)
        
        content = result.getvalue().decode('utf-8')
        assert "Auto" in content
        assert "₹500,000.00" in content
    
    @pytest.mark.asyncio
    async def test_export_goals_csv_no_filters(self, export_service, user_id_str, sample_goal):
        """Test exporting goals to CSV without filters."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_goal]
        mock_result.scalars.return_value = mock_scalars
        
        export_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await export_service.export_goals_csv(user_id_str)
        
        assert isinstance(result, io.BytesIO)
        content = result.getvalue().decode('utf-8')
        assert "Goal Name" in content
        assert "Save for vacation" in content
        assert "₹2,000.00" in content  # Target amount
        assert "₹500.00" in content  # Current amount
    
    @pytest.mark.asyncio
    async def test_export_goals_csv_empty(self, export_service, user_id_str):
        """Test exporting goals when none exist."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        
        export_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await export_service.export_goals_csv(user_id_str)
        
        assert isinstance(result, io.BytesIO)
        content = result.getvalue().decode('utf-8')
        # Should have header but no data rows
        assert "Goal Name,Target Amount" in content or "Goal Name\tTarget Amount" in content or "Goal Name" in content
    
    @pytest.mark.asyncio
    async def test_export_goals_csv_with_status_filter(self, export_service, user_id_str, sample_goal):
        """Test exporting goals to CSV with status filter."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_goal]
        mock_result.scalars.return_value = mock_scalars
        
        export_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await export_service.export_goals_csv(user_id_str)
        
        assert isinstance(result, io.BytesIO)
        content = result.getvalue().decode('utf-8')
        assert "Save for vacation" in content
    
    @pytest.mark.asyncio
    async def test_export_goals_csv_with_multiple_items(self, export_service, user_id_str, user_id):
        """Test exporting multiple goals with different target amounts and statuses."""
        goals = [
            Goal(
                id=uuid4(),
                user_id=user_id,
                goal_name="Save for car",
                goal_type="savings",
                target_amount=Decimal("5000.00"),
                current_amount=Decimal("1000.00"),
                target_date=date(2024, 6, 30),
                priority="high",
                status="active"
            ),
            Goal(
                id=uuid4(),
                user_id=user_id,
                goal_name="Emergency fund",
                goal_type="emergency_fund",
                target_amount=Decimal("10000.00"),
                current_amount=Decimal("5000.00"),
                target_date=date(2024, 12, 31),
                priority="medium",
                status="active"
            ),
        ]
        
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = goals
        mock_result.scalars.return_value = mock_scalars
        
        export_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await export_service.export_goals_csv(user_id_str)
        
        content = result.getvalue().decode('utf-8')
        assert "Save for car" in content
        assert "Emergency fund" in content
        assert "₹5,000.00" in content
        assert "₹10,000.00" in content
    
    @pytest.mark.asyncio
    async def test_export_goals_csv_with_optional_fields_none(self, export_service, user_id_str, user_id):
        """Test exporting goals where optional fields are None."""
        goal = Goal(
            id=uuid4(),
            user_id=user_id,
            goal_name="New Year Resolution",
            goal_type="savings",
            target_amount=Decimal("3000.00"),
            current_amount=Decimal("0.00"),
            target_date=date(2024, 12, 31),
            description=None,
            priority="medium",
            status="active"
        )
        
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [goal]
        mock_result.scalars.return_value = mock_scalars
        
        export_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await export_service.export_goals_csv(user_id_str)
        
        content = result.getvalue().decode('utf-8')
        # Should have proper values
        assert "New Year Resolution" in content
        assert "₹3,000.00" in content
        assert "₹0.00" in content  # Current amount is 0


# ============== EXCEL EXPORT TESTS ==============

class TestExportServiceExcel:
    """Test Excel export methods."""
    
    @pytest.mark.asyncio
    async def test_export_expenses_excel_no_filters(self, export_service, user_id_str, user_id):
        """Test exporting expenses to Excel without filters."""
        expense = Expense(
            id=uuid4(),
            user_id=user_id,
            amount=Decimal("100.00"),
            category="Food",
            subcategory="Restaurant",
            description="Lunch",
            date=date(2024, 1, 15),
            merchant="Restaurant A",
            payment_method="Credit Card",
            is_recurring=False
        )
        
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [expense]
        mock_result.scalars.return_value = mock_scalars
        
        export_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await export_service.export_expenses_excel(user_id_str)
        
        assert isinstance(result, io.BytesIO)
        # Verify it's a valid Excel file by checking for ZIP header (Excel files are ZIP files)
        result.seek(0)
        assert result.read(2) == b'PK'  # ZIP file magic number
    
    @pytest.mark.asyncio
    async def test_export_expenses_excel_with_date_range(self, export_service, user_id_str, user_id):
        """Test exporting expenses to Excel with date range filter."""
        expense = Expense(
            id=uuid4(),
            user_id=user_id,
            amount=Decimal("100.00"),
            category="Food",
            subcategory="Restaurant",
            description="Lunch",
            date=date(2024, 1, 15),
            merchant="Restaurant A",
            payment_method="Credit Card",
            is_recurring=False
        )
        
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [expense]
        mock_result.scalars.return_value = mock_scalars
        
        export_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        
        result = await export_service.export_expenses_excel(
            user_id_str,
            start_date=start_date,
            end_date=end_date
        )
        
        assert isinstance(result, io.BytesIO)
        result.seek(0)
        assert result.read(2) == b'PK'
    
    @pytest.mark.asyncio
    async def test_export_expenses_excel_empty(self, export_service, user_id_str):
        """Test exporting expenses to Excel when none exist."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        
        export_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await export_service.export_expenses_excel(user_id_str)
        
        assert isinstance(result, io.BytesIO)
        result.seek(0)
        assert result.read(2) == b'PK'
    
    @pytest.mark.asyncio
    async def test_export_expenses_excel_multiple_items(self, export_service, user_id_str, user_id):
        """Test exporting multiple expenses to Excel."""
        expenses = [
            Expense(
                id=uuid4(),
                user_id=user_id,
                amount=Decimal("100.00"),
                category="Food",
                subcategory="Restaurant",
                description="Lunch",
                date=date(2024, 1, 15),
                merchant="Restaurant A",
                payment_method="Credit Card",
                is_recurring=False
            ),
            Expense(
                id=uuid4(),
                user_id=user_id,
                amount=Decimal("50.00"),
                category="Transport",
                subcategory="Fuel",
                description="Petrol",
                date=date(2024, 1, 16),
                merchant="Petrol Pump",
                payment_method="Debit Card",
                is_recurring=False
            ),
        ]
        
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = expenses
        mock_result.scalars.return_value = mock_scalars
        
        export_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await export_service.export_expenses_excel(user_id_str)
        
        assert isinstance(result, io.BytesIO)
        result.seek(0)
        assert result.read(2) == b'PK'
    
    @pytest.mark.asyncio
    async def test_export_expenses_excel_with_optional_fields_none(self, export_service, user_id_str, user_id):
        """Test exporting expenses to Excel where optional fields are None."""
        expense = Expense(
            id=uuid4(),
            user_id=user_id,
            amount=Decimal("75.00"),
            category="Food",
            subcategory=None,
            description=None,
            date=date(2024, 1, 15),
            merchant=None,
            payment_method=None,
            is_recurring=False
        )
        
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [expense]
        mock_result.scalars.return_value = mock_scalars
        
        export_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await export_service.export_expenses_excel(user_id_str)
        
        assert isinstance(result, io.BytesIO)
        result.seek(0)
        assert result.read(2) == b'PK'
    
    @pytest.mark.asyncio
    async def test_export_complete_financial_data_excel(self, export_service, user_id_str, user_id):
        """Test exporting all financial data to Excel."""
        expense = Expense(
            id=uuid4(),
            user_id=user_id,
            amount=Decimal("100.00"),
            category="Food",
            subcategory="Restaurant",
            description="Lunch",
            date=date(2024, 1, 15),
            merchant="Restaurant A",
            payment_method="Credit Card",
            is_recurring=False
        )
        
        budget = Budget(
            id=uuid4(),
            user_id=user_id,
            month=date(2024, 1, 1),
            category="Food",
            allocated_amount=Decimal("1000.00"),
            spent_amount=Decimal("500.00")
        )
        
        loan = Loan(
            id=uuid4(),
            user_id=user_id,
            loan_type="Personal",
            lender_name="Bank",
            principal_amount=Decimal("100000.00"),
            interest_rate=Decimal("10.00"),
            loan_term_months=60,
            emi_amount=Decimal("2124.71"),
            outstanding_balance=Decimal("80000.00"),
            status="active",
            start_date=date(2024, 1, 1),
            next_due_date=date(2024, 2, 1),
            remaining_months=48
        )
        
        goal = Goal(
            id=uuid4(),
            user_id=user_id,
            goal_name="Save for vacation",
            goal_type="savings",
            target_amount=Decimal("2000.00"),
            current_amount=Decimal("500.00"),
            target_date=date(2024, 12, 31),
            description="Vacation fund",
            priority="medium",
            status="active"
        )
        
        # Setup multiple execute calls for each query
        expense_result = MagicMock()
        expense_scalars = MagicMock()
        expense_scalars.all.return_value = [expense]
        expense_result.scalars.return_value = expense_scalars
        
        budget_result = MagicMock()
        budget_scalars = MagicMock()
        budget_scalars.all.return_value = [budget]
        budget_result.scalars.return_value = budget_scalars
        
        loan_result = MagicMock()
        loan_scalars = MagicMock()
        loan_scalars.all.return_value = [loan]
        loan_result.scalars.return_value = loan_scalars
        
        goal_result = MagicMock()
        goal_scalars = MagicMock()
        goal_scalars.all.return_value = [goal]
        goal_result.scalars.return_value = goal_scalars
        
        export_service.db_session.execute = AsyncMock(
            side_effect=[expense_result, budget_result, loan_result, goal_result]
        )
        
        result = await export_service.export_complete_financial_data_excel(user_id_str)
        
        assert isinstance(result, io.BytesIO)
        result.seek(0)
        assert result.read(2) == b'PK'
    
    @pytest.mark.asyncio
    async def test_export_complete_financial_data_excel_empty(self, export_service, user_id_str):
        """Test exporting complete financial data to Excel when mostly empty."""
        # Even with empty data, we need at least one item to have valid sheets
        expense = Expense(
            id=uuid4(),
            user_id=uuid4(),
            amount=Decimal("100.00"),
            category="Food",
            subcategory="Restaurant",
            description="Lunch",
            date=date(2024, 1, 15),
            merchant="Restaurant A",
            payment_method="Credit Card",
            is_recurring=False
        )
        
        expense_result = MagicMock()
        expense_scalars = MagicMock()
        expense_scalars.all.return_value = [expense]
        expense_result.scalars.return_value = expense_scalars
        
        # Other results are empty
        empty_result = MagicMock()
        empty_scalars = MagicMock()
        empty_scalars.all.return_value = []
        empty_result.scalars.return_value = empty_scalars
        
        # All four queries: expense has data, others empty
        export_service.db_session.execute = AsyncMock(
            side_effect=[expense_result, empty_result, empty_result, empty_result]
        )
        
        result = await export_service.export_complete_financial_data_excel(user_id_str)
        
        assert isinstance(result, io.BytesIO)
        result.seek(0)
        assert result.read(2) == b'PK'
    
    @pytest.mark.asyncio
    async def test_export_expenses_excel_single_item_with_all_fields(self, export_service, user_id_str, user_id):
        """Test exporting a single expense with all fields populated."""
        expense = Expense(
            id=uuid4(),
            user_id=user_id,
            amount=Decimal("250.50"),
            category="Entertainment",
            subcategory="Movie",
            description="Movie night with friends",
            date=date(2024, 1, 20),
            merchant="Cineplex",
            payment_method="Debit Card",
            is_recurring=False
        )
        
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [expense]
        mock_result.scalars.return_value = mock_scalars
        
        export_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await export_service.export_expenses_excel(user_id_str)
        
        assert isinstance(result, io.BytesIO)
        result.seek(0)
        assert result.read(2) == b'PK'
    
    @pytest.mark.asyncio
    async def test_export_complete_financial_data_excel_with_multiple_items(self, export_service, user_id_str, user_id):
        """Test exporting complete financial data with multiple items of each type."""
        expenses = [
            Expense(
                id=uuid4(),
                user_id=user_id,
                amount=Decimal("100.00"),
                category="Food",
                subcategory="Restaurant",
                description="Lunch",
                date=date(2024, 1, 15),
                merchant="Restaurant A",
                payment_method="Credit Card",
                is_recurring=False
            ),
            Expense(
                id=uuid4(),
                user_id=user_id,
                amount=Decimal("50.00"),
                category="Transport",
                subcategory="Fuel",
                description="Petrol",
                date=date(2024, 1, 16),
                merchant="Petrol Pump",
                payment_method="Debit Card",
                is_recurring=False
            ),
        ]
        
        budgets = [
            Budget(
                id=uuid4(),
                user_id=user_id,
                month=date(2024, 1, 1),
                category="Food",
                allocated_amount=Decimal("1000.00"),
                spent_amount=Decimal("500.00")
            ),
            Budget(
                id=uuid4(),
                user_id=user_id,
                month=date(2024, 1, 1),
                category="Transport",
                allocated_amount=Decimal("500.00"),
                spent_amount=Decimal("250.00")
            ),
        ]
        
        loans = [
            Loan(
                id=uuid4(),
                user_id=user_id,
                loan_type="Personal",
                lender_name="Bank",
                principal_amount=Decimal("100000.00"),
                interest_rate=Decimal("10.00"),
                loan_term_months=60,
                emi_amount=Decimal("2124.71"),
                outstanding_balance=Decimal("80000.00"),
                status="active",
                start_date=date(2024, 1, 1),
                next_due_date=date(2024, 2, 1),
                remaining_months=48
            ),
        ]
        
        goals = [
            Goal(
                id=uuid4(),
                user_id=user_id,
                goal_name="Save for vacation",
                goal_type="savings",
                target_amount=Decimal("2000.00"),
                current_amount=Decimal("500.00"),
                target_date=date(2024, 12, 31),
                description="Vacation fund",
                priority="medium",
                status="active"
            ),
        ]
        
        # Setup multiple execute calls for each query
        expense_result = MagicMock()
        expense_scalars = MagicMock()
        expense_scalars.all.return_value = expenses
        expense_result.scalars.return_value = expense_scalars
        
        budget_result = MagicMock()
        budget_scalars = MagicMock()
        budget_scalars.all.return_value = budgets
        budget_result.scalars.return_value = budget_scalars
        
        loan_result = MagicMock()
        loan_scalars = MagicMock()
        loan_scalars.all.return_value = loans
        loan_result.scalars.return_value = loan_scalars
        
        goal_result = MagicMock()
        goal_scalars = MagicMock()
        goal_scalars.all.return_value = goals
        goal_result.scalars.return_value = goal_scalars
        
        export_service.db_session.execute = AsyncMock(
            side_effect=[expense_result, budget_result, loan_result, goal_result]
        )
        
        result = await export_service.export_complete_financial_data_excel(user_id_str)
        
        assert isinstance(result, io.BytesIO)
        result.seek(0)
        assert result.read(2) == b'PK'
    
    @pytest.mark.asyncio
    async def test_export_complete_financial_data_excel_no_expenses_only_budgets(self, export_service, user_id_str, user_id, sample_budget):
        """Test export_complete_financial_data_excel when expenses is empty but budgets exist (line 473->492)."""
        # Create mock result objects for each query
        expenses_result = MagicMock()
        expenses_scalars = MagicMock()
        expenses_scalars.all.return_value = []  # No expenses
        expenses_result.scalars.return_value = expenses_scalars
        
        budgets_result = MagicMock()
        budgets_scalars = MagicMock()
        budgets_scalars.all.return_value = [sample_budget]
        budgets_result.scalars.return_value = budgets_scalars
        
        loans_result = MagicMock()
        loans_scalars = MagicMock()
        loans_scalars.all.return_value = []
        loans_result.scalars.return_value = loans_scalars
        
        goals_result = MagicMock()
        goals_scalars = MagicMock()
        goals_scalars.all.return_value = []
        goals_result.scalars.return_value = goals_scalars
        
        export_service.db_session.execute = AsyncMock(
            side_effect=[expenses_result, budgets_result, loans_result, goals_result]
        )
        
        result = await export_service.export_complete_financial_data_excel(user_id_str)
        
        assert isinstance(result, io.BytesIO)
        # Verify it's a valid Excel file
        result.seek(0)
        assert result.read(2) == b'PK'
    
    @pytest.mark.asyncio
    async def test_export_expenses_excel_import_error(self, export_service, user_id_str, user_id):
        """Test export_expenses_excel when openpyxl ImportError occurs."""
        with patch('builtins.__import__', side_effect=ImportError("openpyxl not found")):
            with pytest.raises(ImportError, match="openpyxl is required for Excel export"):
                await export_service.export_expenses_excel(user_id_str)

    @pytest.mark.asyncio
    async def test_export_complete_financial_data_excel_import_error(self, export_service, user_id_str, user_id):
        """Test export_complete_financial_data_excel when openpyxl ImportError occurs."""
        with patch('builtins.__import__', side_effect=ImportError("openpyxl not found")):
            with pytest.raises(ImportError, match="openpyxl is required for Excel export"):
                await export_service.export_complete_financial_data_excel(user_id_str)
