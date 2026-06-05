"""Tests for expense_analytics_service.py - comprehensive coverage."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.expense_analytics_service import ExpenseAnalyticsService
from app.db.models.data import Expense, Budget


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
def analytics_service(mock_db):
    """Create an ExpenseAnalyticsService with mocked database."""
    return ExpenseAnalyticsService(mock_db)


@pytest.fixture
def sample_expense():
    """Create a sample Expense object."""
    expense = MagicMock(spec=Expense)
    expense.id = uuid4()
    expense.user_id = uuid4()
    expense.amount = Decimal("500.00")
    expense.category = "food"
    expense.date = date.today()
    expense.description = "Lunch"
    return expense


@pytest.fixture
def sample_budget():
    """Create a sample Budget object."""
    budget = MagicMock(spec=Budget)
    budget.id = uuid4()
    budget.user_id = uuid4()
    budget.category = "food"
    budget.allocated_amount = Decimal("5000.00")
    budget.spent_amount = Decimal("2500.00")
    budget.month = date(2024, 1, 1)
    return budget


# ============== TESTS FOR ExpenseAnalyticsService ==============

class TestExpenseAnalyticsService:
    """Test ExpenseAnalyticsService methods."""
    
    def test_init(self, mock_db):
        """Test ExpenseAnalyticsService initialization."""
        service = ExpenseAnalyticsService(mock_db)
        
        assert service.db == mock_db

    @pytest.mark.asyncio
    async def test_get_monthly_analytics_single_category(self, analytics_service, user_id):
        """Test getting monthly analytics for a single category."""
        today = date.today()
        year, month = today.year, today.month
        
        budget = MagicMock(spec=Budget)
        budget.category = "food"
        budget.allocated_amount = Decimal("5000.00")
        budget.spent_amount = Decimal("2500.00")
        
        mock_budget_result = MagicMock()
        mock_budget_result.scalars.return_value.all.return_value = [budget]
        
        expense1 = MagicMock(spec=Expense)
        expense1.category = "food"
        expense1.amount = Decimal("1500.00")
        
        expense2 = MagicMock(spec=Expense)
        expense2.category = "food"
        expense2.amount = Decimal("1000.00")
        
        mock_expense_result = MagicMock()
        mock_expense_result.scalars.return_value.all.return_value = [expense1, expense2]
        
        # Setup execute to return different mocks based on select call
        execute_calls = [mock_budget_result, mock_expense_result]
        analytics_service.db.execute = AsyncMock(side_effect=execute_calls)
        
        result = await analytics_service.get_monthly_analytics(user_id, year, month)
        
        assert "summary" in result
        assert "budget_analysis" in result

    @pytest.mark.asyncio
    async def test_get_monthly_analytics_no_budgets(self, analytics_service, user_id):
        """Test getting monthly analytics when there are no budgets."""
        today = date.today()
        year, month = today.year, today.month
        
        mock_budget_result = MagicMock()
        mock_budget_result.scalars.return_value.all.return_value = []
        
        mock_expense_result = MagicMock()
        mock_expense_result.scalars.return_value.all.return_value = []
        
        execute_calls = [mock_budget_result, mock_expense_result]
        analytics_service.db.execute = AsyncMock(side_effect=execute_calls)
        
        result = await analytics_service.get_monthly_analytics(user_id, year, month)
        
        assert "summary" in result
        assert result["summary"]["total_budgeted"] == Decimal("0")
        assert result["summary"]["total_spent"] == Decimal("0")

    @pytest.mark.asyncio
    async def test_calculate_expense_analytics_with_expenses(self, analytics_service, user_id):
        """Test calculating expense analytics with expenses."""
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        expense1 = MagicMock(spec=Expense)
        expense1.amount = Decimal("500.00")
        expense1.category = "food"
        expense1.payment_method = "credit_card"
        
        expense2 = MagicMock(spec=Expense)
        expense2.amount = Decimal("200.00")
        expense2.category = "transport"
        expense2.payment_method = "upi"
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [expense1, expense2]
        
        analytics_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await analytics_service.calculate_expense_analytics(user_id, start_date, end_date)
        
        assert "total_amount" in result
        assert "category_breakdown" in result
        assert result["total_amount"] == Decimal("700.00")

    @pytest.mark.asyncio
    async def test_calculate_expense_analytics_no_expenses(self, analytics_service, user_id):
        """Test calculating expense analytics when there are no expenses."""
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        
        analytics_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await analytics_service.calculate_expense_analytics(user_id, start_date, end_date)
        
        assert result["total_amount"] == Decimal("0")
        assert result["category_breakdown"] == {}

    @pytest.mark.asyncio
    async def test_calculate_monthly_spending_trend_multiple_months(self, analytics_service, user_id):
        """Test calculating monthly spending trends."""
        # Mock the raw query result with month/total rows
        mock_row1 = MagicMock()
        mock_row1.month = datetime(2024, 1, 1).date()
        mock_row1.total = Decimal("1000.00")
        
        mock_row2 = MagicMock()
        mock_row2.month = datetime(2024, 2, 1).date()
        mock_row2.total = Decimal("2000.00")
        
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row1, mock_row2]
        
        analytics_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await analytics_service.calculate_monthly_spending_trend(user_id)
        
        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_detect_spending_anomalies_normal_spending(self, analytics_service, user_id):
        """Test detecting spending anomalies with normal spending patterns."""
        expenses = []
        for i in range(10):
            expense = MagicMock(spec=Expense)
            expense.amount = Decimal("100.00")
            expense.category = "food"
            expense.date = date.today() - timedelta(days=i)
            expenses.append(expense)
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = expenses
        
        analytics_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await analytics_service.detect_spending_anomalies(user_id)
        
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_detect_spending_anomalies_with_spike(self, analytics_service, user_id):
        """Test detecting spending anomalies with spending spikes."""
        expenses = []
        # Normal expenses
        for i in range(10):
            expense = MagicMock(spec=Expense)
            expense.amount = Decimal("100.00")
            expense.category = "food"
            expense.date = date.today() - timedelta(days=i)
            expenses.append(expense)
        
        # Spike
        spike = MagicMock(spec=Expense)
        spike.amount = Decimal("5000.00")
        spike.category = "food"
        spike.date = date.today()
        expenses.append(spike)
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = expenses
        
        analytics_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await analytics_service.detect_spending_anomalies(user_id)
        
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_calculate_category_wise_trends_multiple_months(self, analytics_service, user_id):
        """Test calculating category-wise trends across months."""
        mock_row1 = MagicMock()
        mock_row1.month = datetime(2024, 1, 1).date()
        mock_row1.category = "food"
        mock_row1.total = Decimal("1000.00")
        
        mock_row2 = MagicMock()
        mock_row2.month = datetime(2024, 2, 1).date()
        mock_row2.category = "food"
        mock_row2.total = Decimal("1500.00")
        
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row1, mock_row2]
        
        analytics_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await analytics_service.calculate_category_wise_trends(user_id)
        
        assert isinstance(result, dict)
        assert "food" in result

    @pytest.mark.asyncio
    async def test_generate_spending_insights_high_spending_category(self, analytics_service, user_id):
        """Test generating spending insights for high spending category."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        
        analytics_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await analytics_service.generate_spending_insights(user_id)
        
        assert "insights" in result
        assert isinstance(result["insights"], list)

    @pytest.mark.asyncio
    async def test_generate_spending_insights_no_data(self, analytics_service, user_id):
        """Test generating spending insights when no data exists."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        
        analytics_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await analytics_service.generate_spending_insights(user_id)
        
        assert "insights" in result
        assert isinstance(result["insights"], list)

    @pytest.mark.asyncio
    async def test_calculate_payment_method_analytics_mixed_methods(self, analytics_service, user_id):
        """Test calculating payment method analytics."""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()
        
        expense1 = MagicMock(spec=Expense)
        expense1.amount = Decimal("500.00")
        expense1.payment_method = "credit_card"
        
        expense2 = MagicMock(spec=Expense)
        expense2.amount = Decimal("300.00")
        expense2.payment_method = "upi"
        
        expense3 = MagicMock(spec=Expense)
        expense3.amount = Decimal("200.00")
        expense3.payment_method = "credit_card"
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [expense1, expense2, expense3]
        
        analytics_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await analytics_service.calculate_payment_method_analytics(user_id, start_date, end_date)
        
        assert isinstance(result, dict)
        assert "credit_card" in result
        assert result["credit_card"] == 700.0

    @pytest.mark.asyncio
    async def test_calculate_payment_method_analytics_no_method(self, analytics_service, user_id):
        """Test calculating payment method analytics when none specified."""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()
        
        expense1 = MagicMock(spec=Expense)
        expense1.amount = Decimal("500.00")
        expense1.payment_method = None
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [expense1]
        
        analytics_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await analytics_service.calculate_payment_method_analytics(user_id, start_date, end_date)
        
        assert isinstance(result, dict)
        assert "unknown" in result
        assert result["unknown"] == 500.0

    @pytest.mark.asyncio
    async def test_calculate_weekly_spending_pattern_normal(self, analytics_service, user_id):
        """Test calculating weekly spending pattern."""
        mock_row1 = MagicMock()
        mock_row1.week_start = datetime(2024, 1, 1).date()
        mock_row1.total_amount = Decimal("1000.00")
        mock_row1.transaction_count = 5
        
        mock_row2 = MagicMock()
        mock_row2.week_start = datetime(2024, 1, 8).date()
        mock_row2.total_amount = Decimal("1500.00")
        mock_row2.transaction_count = 7
        
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row1, mock_row2]
        
        analytics_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await analytics_service.calculate_weekly_spending_pattern(user_id)
        
        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_calculate_weekly_spending_pattern_no_expenses(self, analytics_service, user_id):
        """Test calculating weekly spending pattern with no expenses."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        
        analytics_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await analytics_service.calculate_weekly_spending_pattern(user_id)
        
        assert isinstance(result, list)
        assert len(result) == 0


# ============== EDGE CASE TESTS ==============

class TestExpenseAnalyticsEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_get_monthly_analytics_invalid_month(self, analytics_service, user_id):
        """Test getting analytics with invalid month."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        
        analytics_service.db.execute = AsyncMock(return_value=mock_result)
        
        # Invalid month should raise ValueError during date creation
        with pytest.raises(ValueError):
            await analytics_service.get_monthly_analytics(user_id, 2024, 13)

    @pytest.mark.asyncio
    async def test_calculate_expense_analytics_large_numbers(self, analytics_service, user_id):
        """Test expense analytics with large expense amounts."""
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        expense = MagicMock(spec=Expense)
        expense.amount = Decimal("999999.99")
        expense.category = "travel"
        expense.payment_method = "credit_card"
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [expense]
        
        analytics_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await analytics_service.calculate_expense_analytics(user_id, start_date, end_date)
        
        assert result["total_amount"] == Decimal("999999.99")

    @pytest.mark.asyncio
    async def test_calculate_expense_analytics_multiple_same_category(self, analytics_service, user_id):
        """Test expense analytics with multiple expenses in same category."""
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        expenses = []
        for i in range(5):
            expense = MagicMock(spec=Expense)
            expense.amount = Decimal(str(100 * (i + 1)))
            expense.category = "food"
            expense.payment_method = "upi"
            expenses.append(expense)
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = expenses
        
        analytics_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await analytics_service.calculate_expense_analytics(user_id, start_date, end_date)
        
        assert result["total_amount"] == Decimal("1500.00")
        assert "food" in result["category_breakdown"]


# ============== ADDITIONAL COVERAGE TESTS ==============

class TestExpenseAnalyticsAdditionalCoverage:
    """Additional tests to cover remaining branches and edge cases."""
    
    @pytest.mark.asyncio
    async def test_get_monthly_analytics_budget_under_limit(self, analytics_service, user_id):
        """Test monthly analytics with spending under budget."""
        today = date.today()
        year, month = today.year, today.month
        
        budget = MagicMock(spec=Budget)
        budget.category = "food"
        budget.allocated_amount = Decimal("5000.00")
        
        mock_budget_result = MagicMock()
        mock_budget_result.scalars.return_value.all.return_value = [budget]
        
        # Mock row object for expense query
        mock_row = MagicMock()
        mock_row.category = "food"
        mock_row.total_spent = Decimal("2500.00")
        mock_row.expense_count = 5
        
        mock_expense_result = MagicMock()
        mock_expense_result.all.return_value = [mock_row]
        
        execute_calls = [mock_budget_result, mock_expense_result]
        analytics_service.db.execute = AsyncMock(side_effect=execute_calls)
        
        result = await analytics_service.get_monthly_analytics(user_id, year, month)
        
        assert "budget_analysis" in result
        analysis = result["budget_analysis"][0]
        assert analysis["status"] == "UNDER"
        assert analysis["utilization_percent"] == 50.0

    @pytest.mark.asyncio
    async def test_get_monthly_analytics_budget_over_limit(self, analytics_service, user_id):
        """Test monthly analytics with spending over budget."""
        today = date.today()
        year, month = today.year, today.month
        
        budget = MagicMock(spec=Budget)
        budget.category = "food"
        budget.allocated_amount = Decimal("2000.00")
        
        mock_budget_result = MagicMock()
        mock_budget_result.scalars.return_value.all.return_value = [budget]
        
        # Spending over budget
        mock_row = MagicMock()
        mock_row.category = "food"
        mock_row.total_spent = Decimal("3000.00")
        mock_row.expense_count = 10
        
        mock_expense_result = MagicMock()
        mock_expense_result.all.return_value = [mock_row]
        
        execute_calls = [mock_budget_result, mock_expense_result]
        analytics_service.db.execute = AsyncMock(side_effect=execute_calls)
        
        result = await analytics_service.get_monthly_analytics(user_id, year, month)
        
        assert "budget_analysis" in result
        analysis = result["budget_analysis"][0]
        assert analysis["status"] == "OVER"
        assert analysis["utilization_percent"] == 150.0

    @pytest.mark.asyncio
    async def test_get_monthly_analytics_budget_warning_limit(self, analytics_service, user_id):
        """Test monthly analytics with spending at warning level (90-99%)."""
        today = date.today()
        year, month = today.year, today.month
        
        budget = MagicMock(spec=Budget)
        budget.category = "food"
        budget.allocated_amount = Decimal("1000.00")
        
        mock_budget_result = MagicMock()
        mock_budget_result.scalars.return_value.all.return_value = [budget]
        
        # Spending at 95% of budget
        mock_row = MagicMock()
        mock_row.category = "food"
        mock_row.total_spent = Decimal("950.00")
        mock_row.expense_count = 10
        
        mock_expense_result = MagicMock()
        mock_expense_result.all.return_value = [mock_row]
        
        execute_calls = [mock_budget_result, mock_expense_result]
        analytics_service.db.execute = AsyncMock(side_effect=execute_calls)
        
        result = await analytics_service.get_monthly_analytics(user_id, year, month)
        
        assert "budget_analysis" in result
        analysis = result["budget_analysis"][0]
        assert analysis["status"] == "WARNING"
        assert analysis["utilization_percent"] == 95.0

    @pytest.mark.asyncio
    async def test_get_monthly_analytics_with_unbudgeted_expenses(self, analytics_service, user_id):
        """Test monthly analytics with expenses in categories without budget."""
        today = date.today()
        year, month = today.year, today.month
        
        # Budget for food only
        budget = MagicMock(spec=Budget)
        budget.category = "food"
        budget.allocated_amount = Decimal("5000.00")
        
        mock_budget_result = MagicMock()
        mock_budget_result.scalars.return_value.all.return_value = [budget]
        
        # Expenses in food and transport
        mock_food = MagicMock()
        mock_food.category = "food"
        mock_food.total_spent = Decimal("1000.00")
        mock_food.expense_count = 5
        
        mock_transport = MagicMock()
        mock_transport.category = "transport"
        mock_transport.total_spent = Decimal("500.00")
        mock_transport.expense_count = 3
        
        mock_expense_result = MagicMock()
        mock_expense_result.all.return_value = [mock_food, mock_transport]
        
        execute_calls = [mock_budget_result, mock_expense_result]
        analytics_service.db.execute = AsyncMock(side_effect=execute_calls)
        
        result = await analytics_service.get_monthly_analytics(user_id, year, month)
        
        assert "unbudgeted_spending" in result
        assert len(result["unbudgeted_spending"]) == 1
        assert result["unbudgeted_spending"][0]["category"] == "transport"

    @pytest.mark.asyncio
    async def test_get_monthly_analytics_budget_zero_allocated(self, analytics_service, user_id):
        """Test monthly analytics when budget has zero allocation."""
        today = date.today()
        year, month = today.year, today.month
        
        budget = MagicMock(spec=Budget)
        budget.category = "food"
        budget.allocated_amount = Decimal("0")
        
        mock_budget_result = MagicMock()
        mock_budget_result.scalars.return_value.all.return_value = [budget]
        
        mock_row = MagicMock()
        mock_row.category = "food"
        mock_row.total_spent = Decimal("100.00")
        mock_row.expense_count = 2
        
        mock_expense_result = MagicMock()
        mock_expense_result.all.return_value = [mock_row]
        
        execute_calls = [mock_budget_result, mock_expense_result]
        analytics_service.db.execute = AsyncMock(side_effect=execute_calls)
        
        result = await analytics_service.get_monthly_analytics(user_id, year, month)
        
        assert "budget_analysis" in result
        analysis = result["budget_analysis"][0]
        assert analysis["utilization_percent"] == 0

    @pytest.mark.asyncio
    async def test_get_monthly_analytics_budget_none_allocated(self, analytics_service, user_id):
        """Test monthly analytics when budget allocation is None."""
        today = date.today()
        year, month = today.year, today.month
        
        budget = MagicMock(spec=Budget)
        budget.category = "food"
        budget.allocated_amount = None
        
        mock_budget_result = MagicMock()
        mock_budget_result.scalars.return_value.all.return_value = [budget]
        
        mock_row = MagicMock()
        mock_row.category = "food"
        mock_row.total_spent = Decimal("100.00")
        mock_row.expense_count = 2
        
        mock_expense_result = MagicMock()
        mock_expense_result.all.return_value = [mock_row]
        
        execute_calls = [mock_budget_result, mock_expense_result]
        analytics_service.db.execute = AsyncMock(side_effect=execute_calls)
        
        result = await analytics_service.get_monthly_analytics(user_id, year, month)
        
        assert "budget_analysis" in result

    @pytest.mark.asyncio
    async def test_calculate_monthly_spending_trend_with_none_month(self, analytics_service, user_id):
        """Test monthly spending trend when month is None in result."""
        mock_row = MagicMock()
        mock_row.month = None
        mock_row.total = Decimal("1000.00")
        
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        
        analytics_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await analytics_service.calculate_monthly_spending_trend(user_id)
        
        assert result[0]["month"] == "Unknown"

    @pytest.mark.asyncio
    async def test_calculate_monthly_spending_trend_with_none_total(self, analytics_service, user_id):
        """Test monthly spending trend when total is None."""
        mock_row = MagicMock()
        mock_row.month = datetime(2024, 1, 1).date()
        mock_row.total = None
        
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        
        analytics_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await analytics_service.calculate_monthly_spending_trend(user_id)
        
        assert result[0]["total_amount"] == 0

    @pytest.mark.asyncio
    async def test_detect_spending_anomalies_zero_historical_avg(self, analytics_service, user_id):
        """Test anomaly detection when historical average is zero."""
        # Mock first call for average
        mock_avg_result = MagicMock()
        mock_avg_result.scalar.return_value = Decimal("0")
        
        # Mock second call for recent expenses (not called if avg is 0)
        mock_expenses_result = MagicMock()
        mock_expenses_result.scalars.return_value.all.return_value = []
        
        execute_calls = [mock_avg_result]
        analytics_service.db.execute = AsyncMock(side_effect=execute_calls)
        
        result = await analytics_service.detect_spending_anomalies(user_id)
        
        assert result == []

    @pytest.mark.asyncio
    async def test_detect_spending_anomalies_multiple_anomalies(self, analytics_service, user_id):
        """Test detecting multiple spending anomalies."""
        # Mock historical average
        mock_avg_result = MagicMock()
        mock_avg_result.scalar.return_value = Decimal("100.00")
        
        # Create multiple high-spending anomalies
        expenses = []
        for i in range(3):
            expense = MagicMock(spec=Expense)
            expense.amount = Decimal("500.00")  # > 2.5x of 100 = 250
            expense.category = f"cat{i}"
            expense.date = date.today() - timedelta(days=i)
            expense.id = uuid4()
            expenses.append(expense)
        
        # Mock second call for recent expenses
        mock_expenses_result = MagicMock()
        mock_expenses_result.scalars.return_value.all.return_value = expenses
        
        execute_calls = [mock_avg_result, mock_expenses_result]
        analytics_service.db.execute = AsyncMock(side_effect=execute_calls)
        
        result = await analytics_service.detect_spending_anomalies(user_id)
        
        assert len(result) == 3
        for anomaly in result:
            assert anomaly["type"] == "high_spending"

    @pytest.mark.asyncio
    async def test_calculate_category_wise_trends_with_none_month(self, analytics_service, user_id):
        """Test category trends when month is None."""
        mock_row = MagicMock()
        mock_row.month = None
        mock_row.category = "food"
        mock_row.total = Decimal("1000.00")
        
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        
        analytics_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await analytics_service.calculate_category_wise_trends(user_id)
        
        assert "food" in result
        assert result["food"][0]["month"] == "Unknown"

    @pytest.mark.asyncio
    async def test_calculate_category_wise_trends_multiple_categories(self, analytics_service, user_id):
        """Test category trends with multiple categories."""
        mock_rows = []
        for cat in ["food", "transport", "entertainment"]:
            for month in [1, 2]:
                mock_row = MagicMock()
                mock_row.month = datetime(2024, month, 1).date()
                mock_row.category = cat
                mock_row.total = Decimal(f"{1000 + month * 100}.00")
                mock_rows.append(mock_row)
        
        mock_result = MagicMock()
        mock_result.all.return_value = mock_rows
        
        analytics_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await analytics_service.calculate_category_wise_trends(user_id)
        
        assert len(result) == 3
        assert "food" in result
        assert len(result["food"]) == 2

    @pytest.mark.asyncio
    async def test_calculate_category_wise_trends_with_none_total(self, analytics_service, user_id):
        """Test category trends when total is None."""
        mock_row = MagicMock()
        mock_row.month = datetime(2024, 1, 1).date()
        mock_row.category = "food"
        mock_row.total = None
        
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        
        analytics_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await analytics_service.calculate_category_wise_trends(user_id)
        
        assert result["food"][0]["amount"] == 0

    @pytest.mark.asyncio
    async def test_generate_spending_insights_with_overspending(self, analytics_service, user_id):
        """Test generating insights when categories are overspending."""
        # Mock current expenses
        current_expense = MagicMock(spec=Expense)
        current_expense.category = "food"
        current_expense.amount = Decimal("2000.00")
        
        mock_current_result = MagicMock()
        mock_current_result.scalars.return_value.all.return_value = [current_expense]
        
        # Mock historical average (food average was 1000)
        mock_historical = MagicMock()
        mock_historical.mappings.return_value.all.return_value = [
            {"category": "food", "avg_amount": Decimal("1000.00")}
        ]
        
        execute_calls = [mock_current_result, mock_historical]
        analytics_service.db.execute = AsyncMock(side_effect=execute_calls)
        
        result = await analytics_service.generate_spending_insights(user_id)
        
        assert "overspending_categories" in result
        assert len(result["overspending_categories"]) > 0

    @pytest.mark.asyncio
    async def test_generate_spending_insights_with_highest_category(self, analytics_service, user_id):
        """Test insights report includes highest spending category."""
        # Mock current expenses
        expense1 = MagicMock(spec=Expense)
        expense1.category = "food"
        expense1.amount = Decimal("1000.00")
        
        expense2 = MagicMock(spec=Expense)
        expense2.category = "transport"
        expense2.amount = Decimal("500.00")
        
        mock_current_result = MagicMock()
        mock_current_result.scalars.return_value.all.return_value = [expense1, expense2]
        
        # Mock historical (empty)
        mock_historical = MagicMock()
        mock_historical.mappings.return_value.all.return_value = []
        
        execute_calls = [mock_current_result, mock_historical]
        analytics_service.db.execute = AsyncMock(side_effect=execute_calls)
        
        result = await analytics_service.generate_spending_insights(user_id)
        
        assert "insights" in result
        assert len(result["insights"]) > 0
        assert "highest spending category is food" in result["insights"][0]["message"]

    @pytest.mark.asyncio
    async def test_calculate_payment_method_analytics_mixed_none(self, analytics_service, user_id):
        """Test payment method analytics with mixed None and defined methods."""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()
        
        expenses = []
        expense1 = MagicMock(spec=Expense)
        expense1.amount = Decimal("500.00")
        expense1.payment_method = "credit_card"
        expenses.append(expense1)
        
        expense2 = MagicMock(spec=Expense)
        expense2.amount = Decimal("300.00")
        expense2.payment_method = None
        expenses.append(expense2)
        
        expense3 = MagicMock(spec=Expense)
        expense3.amount = Decimal("200.00")
        expense3.payment_method = "credit_card"
        expenses.append(expense3)
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = expenses
        
        analytics_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await analytics_service.calculate_payment_method_analytics(user_id, start_date, end_date)
        
        assert "credit_card" in result
        assert "unknown" in result
        assert result["credit_card"] == 700.0
        assert result["unknown"] == 300.0

    @pytest.mark.asyncio
    async def test_calculate_weekly_spending_with_none_fields(self, analytics_service, user_id):
        """Test weekly spending when fields are None."""
        mock_row1 = MagicMock()
        mock_row1.week_start = None
        mock_row1.total_amount = Decimal("1000.00")
        mock_row1.transaction_count = 5
        
        mock_row2 = MagicMock()
        mock_row2.week_start = datetime(2024, 1, 8).date()
        mock_row2.total_amount = None
        mock_row2.transaction_count = None
        
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row1, mock_row2]
        
        analytics_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await analytics_service.calculate_weekly_spending_pattern(user_id)
        
        assert result[0]["week_start"] is None
        assert result[1]["total_amount"] == 0
        assert result[1]["transaction_count"] == 0

    @pytest.mark.asyncio
    async def test_calculate_expense_analytics_date_handling(self, analytics_service, user_id):
        """Test expense analytics with datetime handling."""
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        expense = MagicMock(spec=Expense)
        expense.amount = Decimal("500.00")
        expense.category = "food"
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [expense]
        
        analytics_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await analytics_service.calculate_expense_analytics(user_id, start_date, end_date)
        
        assert result["total_amount"] == Decimal("500.00")

    @pytest.mark.asyncio
    async def test_get_monthly_analytics_exception(self, analytics_service, user_id):
        """Test get_monthly_analytics when database query raises exception."""
        today = date.today()
        year, month = today.year, today.month
        
        analytics_service.db.execute = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(Exception, match="Database error"):
            await analytics_service.get_monthly_analytics(user_id, year, month)

    @pytest.mark.asyncio
    async def test_calculate_expense_analytics_exception(self, analytics_service, user_id):
        """Test calculate_expense_analytics when database query raises exception."""
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        analytics_service.db.execute = AsyncMock(side_effect=Exception("Query failed"))
        
        with pytest.raises(Exception, match="Query failed"):
            await analytics_service.calculate_expense_analytics(user_id, start_date, end_date)

    @pytest.mark.asyncio
    async def test_calculate_monthly_spending_trend_exception(self, analytics_service, user_id):
        """Test calculate_monthly_spending_trend when database query raises exception."""
        analytics_service.db.execute = AsyncMock(side_effect=Exception("Trend calculation failed"))
        
        with pytest.raises(Exception, match="Trend calculation failed"):
            await analytics_service.calculate_monthly_spending_trend(user_id)

    @pytest.mark.asyncio
    async def test_detect_spending_anomalies_exception(self, analytics_service, user_id):
        """Test detect_spending_anomalies when database query raises exception."""
        analytics_service.db.execute = AsyncMock(side_effect=Exception("Anomaly detection failed"))
        
        with pytest.raises(Exception, match="Anomaly detection failed"):
            await analytics_service.detect_spending_anomalies(user_id)

    @pytest.mark.asyncio
    async def test_generate_spending_insights_exception(self, analytics_service, user_id):
        """Test generate_spending_insights when database query raises exception."""
        analytics_service.db.execute = AsyncMock(side_effect=Exception("Insights generation failed"))
        
        with pytest.raises(Exception, match="Insights generation failed"):
            await analytics_service.generate_spending_insights(user_id)


# ============== MISSING COVERAGE TESTS ==============

class TestExpenseAnalyticsMissingCoverage:
    """Tests for missing coverage branches in ExpenseAnalyticsService."""
    
    @pytest.mark.asyncio
    async def test_calculate_monthly_spending_trend_multiple_nulls(self, analytics_service, user_id):
        """Test monthly spending trend with multiple None values."""
        mock_rows = []
        
        # Row with None month and None total
        mock_row1 = MagicMock()
        mock_row1.month = None
        mock_row1.total = None
        mock_rows.append(mock_row1)
        
        # Row with valid month and None total
        mock_row2 = MagicMock()
        mock_row2.month = datetime(2024, 2, 1).date()
        mock_row2.total = None
        mock_rows.append(mock_row2)
        
        mock_result = MagicMock()
        mock_result.all.return_value = mock_rows
        
        analytics_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await analytics_service.calculate_monthly_spending_trend(user_id)
        
        assert len(result) == 2
        assert result[0]["month"] == "Unknown"
        assert result[0]["total_amount"] == 0
        assert result[1]["total_amount"] == 0

    @pytest.mark.asyncio
    async def test_calculate_payment_method_analytics_all_none(self, analytics_service, user_id):
        """Test payment method analytics when all methods are None."""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()
        
        expenses = []
        for i in range(3):
            expense = MagicMock(spec=Expense)
            expense.amount = Decimal(str(100 * (i + 1)))
            expense.payment_method = None
            expenses.append(expense)
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = expenses
        
        analytics_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await analytics_service.calculate_payment_method_analytics(user_id, start_date, end_date)
        
        assert "unknown" in result
        assert result["unknown"] == 600.0

    @pytest.mark.asyncio
    async def test_get_monthly_analytics_budget_with_no_expenses(self, analytics_service, user_id):
        """Test monthly analytics when budget exists but no expenses."""
        today = date.today()
        year, month = today.year, today.month
        
        budget = MagicMock(spec=Budget)
        budget.category = "food"
        budget.allocated_amount = Decimal("5000.00")
        
        mock_budget_result = MagicMock()
        mock_budget_result.scalars.return_value.all.return_value = [budget]
        
        # No expenses
        mock_expense_result = MagicMock()
        mock_expense_result.all.return_value = []
        
        execute_calls = [mock_budget_result, mock_expense_result]
        analytics_service.db.execute = AsyncMock(side_effect=execute_calls)
        
        result = await analytics_service.get_monthly_analytics(user_id, year, month)
        
        assert "budget_analysis" in result
        analysis = result["budget_analysis"][0]
        assert analysis["status"] == "UNDER"
        assert analysis["utilization_percent"] == 0.0

    @pytest.mark.asyncio
    async def test_get_monthly_analytics_multiple_budgets_mixed_status(self, analytics_service, user_id):
        """Test monthly analytics with multiple budgets having different statuses."""
        today = date.today()
        year, month = today.year, today.month
        
        budget1 = MagicMock(spec=Budget)
        budget1.category = "food"
        budget1.allocated_amount = Decimal("2000.00")
        
        budget2 = MagicMock(spec=Budget)
        budget2.category = "transport"
        budget2.allocated_amount = Decimal("1000.00")
        
        mock_budget_result = MagicMock()
        mock_budget_result.scalars.return_value.all.return_value = [budget1, budget2]
        
        # Expenses: food at 3000 (150%), transport at 500 (50%)
        mock_food = MagicMock()
        mock_food.category = "food"
        mock_food.total_spent = Decimal("3000.00")
        mock_food.expense_count = 10
        
        mock_transport = MagicMock()
        mock_transport.category = "transport"
        mock_transport.total_spent = Decimal("500.00")
        mock_transport.expense_count = 5
        
        mock_expense_result = MagicMock()
        mock_expense_result.all.return_value = [mock_food, mock_transport]
        
        execute_calls = [mock_budget_result, mock_expense_result]
        analytics_service.db.execute = AsyncMock(side_effect=execute_calls)
        
        result = await analytics_service.get_monthly_analytics(user_id, year, month)
        
        analysis_list = result["budget_analysis"]
        assert len(analysis_list) == 2
        
        # Food should be OVER
        food_analysis = [a for a in analysis_list if a["category"] == "food"][0]
        assert food_analysis["status"] == "OVER"
        
        # Transport should be UNDER
        transport_analysis = [a for a in analysis_list if a["category"] == "transport"][0]
        assert transport_analysis["status"] == "UNDER"

    @pytest.mark.asyncio
    async def test_calculate_category_wise_trends_with_null_category(self, analytics_service, user_id):
        """Test category trends when category is None."""
        mock_rows = []
        
        mock_row = MagicMock()
        mock_row.month = datetime(2024, 1, 1).date()
        mock_row.category = None
        mock_row.total = Decimal("1000.00")
        mock_rows.append(mock_row)
        
        mock_result = MagicMock()
        mock_result.all.return_value = mock_rows
        
        analytics_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await analytics_service.calculate_category_wise_trends(user_id)
        
        assert None in result

    @pytest.mark.asyncio
    async def test_detect_spending_anomalies_with_negative_historical_avg(self, analytics_service, user_id):
        """Test anomaly detection handles edge case of negative historical average."""
        # Mock historical average (shouldn't be negative but test defensive coding)
        mock_avg_result = MagicMock()
        mock_avg_result.scalar.return_value = Decimal("-50")
        
        analytics_service.db.execute = AsyncMock(return_value=mock_avg_result)
        
        result = await analytics_service.detect_spending_anomalies(user_id)
        
        # Should return empty list when average is negative/zero
        assert result == []

    @pytest.mark.asyncio
    async def test_generate_spending_insights_empty_historical(self, analytics_service, user_id):
        """Test generating insights when no historical data exists."""
        # Current expenses
        expense1 = MagicMock(spec=Expense)
        expense1.category = "food"
        expense1.amount = Decimal("1000.00")
        
        expense2 = MagicMock(spec=Expense)
        expense2.category = "transport"
        expense2.amount = Decimal("300.00")
        
        mock_current_result = MagicMock()
        mock_current_result.scalars.return_value.all.return_value = [expense1, expense2]
        
        # No historical data
        mock_historical = MagicMock()
        mock_historical.mappings.return_value.all.return_value = []
        
        execute_calls = [mock_current_result, mock_historical]
        analytics_service.db.execute = AsyncMock(side_effect=execute_calls)
        
        result = await analytics_service.generate_spending_insights(user_id)
        
        assert "insights" in result
        assert len(result["insights"]) > 0

    @pytest.mark.asyncio
    async def test_calculate_weekly_spending_pattern_with_zero_transaction_count(self, analytics_service, user_id):
        """Test weekly spending with zero transaction count."""
        mock_row = MagicMock()
        mock_row.week_start = datetime(2024, 1, 1).date()
        mock_row.total_amount = Decimal("1000.00")
        mock_row.transaction_count = 0
        
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        
        analytics_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await analytics_service.calculate_weekly_spending_pattern(user_id)
        
        assert len(result) == 1
        assert result[0]["transaction_count"] == 0

    @pytest.mark.asyncio
    async def test_calculate_weekly_spending_pattern_large_transaction_count(self, analytics_service, user_id):
        """Test weekly spending with very large transaction count."""
        mock_row = MagicMock()
        mock_row.week_start = datetime(2024, 1, 1).date()
        mock_row.total_amount = Decimal("50000.00")
        mock_row.transaction_count = 500
        
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        
        analytics_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await analytics_service.calculate_weekly_spending_pattern(user_id)
        
        assert len(result) == 1
        assert result[0]["transaction_count"] == 500

    @pytest.mark.asyncio
    async def test_calculate_expense_analytics_multiple_categories_same_amount(self, analytics_service, user_id):
        """Test expense analytics with multiple categories having same amount."""
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        expenses = []
        for cat in ["food", "transport", "entertainment"]:
            expense = MagicMock(spec=Expense)
            expense.amount = Decimal("500.00")
            expense.category = cat
            expense.payment_method = "credit_card"
            expenses.append(expense)
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = expenses
        
        analytics_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await analytics_service.calculate_expense_analytics(user_id, start_date, end_date)
        
        assert result["total_amount"] == Decimal("1500.00")
        assert len(result["category_breakdown"]) == 3
        for category in ["food", "transport", "entertainment"]:
            assert category in result["category_breakdown"]

    @pytest.mark.asyncio
    async def test_get_monthly_analytics_budget_exactly_at_limit(self, analytics_service, user_id):
        """Test monthly analytics when spending is exactly at budget limit (100%)."""
        today = date.today()
        year, month = today.year, today.month
        
        budget = MagicMock(spec=Budget)
        budget.category = "food"
        budget.allocated_amount = Decimal("1000.00")
        
        mock_budget_result = MagicMock()
        mock_budget_result.scalars.return_value.all.return_value = [budget]
        
        # Spending exactly at budget
        mock_row = MagicMock()
        mock_row.category = "food"
        mock_row.total_spent = Decimal("1000.00")
        mock_row.expense_count = 5
        
        mock_expense_result = MagicMock()
        mock_expense_result.all.return_value = [mock_row]
        
        execute_calls = [mock_budget_result, mock_expense_result]
        analytics_service.db.execute = AsyncMock(side_effect=execute_calls)
        
        result = await analytics_service.get_monthly_analytics(user_id, year, month)
        
        analysis = result["budget_analysis"][0]
        assert analysis["utilization_percent"] == 100.0
        # At exactly 100%, should still be marked as WARNING or OVER
        assert analysis["status"] in ["WARNING", "OVER"]


class TestExpenseAnalyticsBranchCoverage:
    """Tests for missing branch coverage."""

    @pytest.mark.asyncio
    async def test_detect_spending_anomalies_no_anomalies_all_below_threshold(self, analytics_service, user_id):
        """Test detect_spending_anomalies when no expenses exceed threshold (327->326 branch)."""
        # Create expenses below the threshold
        expense1 = MagicMock(spec=Expense)
        expense1.amount = Decimal("100.00")
        expense1.category = "food"
        expense1.date = date.today()
        expense1.id = uuid4()
        expense1.merchant = "Restaurant"
        expense1.payment_method = "Card"
        expense1.description = "Lunch"

        expense2 = MagicMock(spec=Expense)
        expense2.amount = Decimal("150.00")
        expense2.category = "transport"
        expense2.date = date.today()
        expense2.id = uuid4()
        expense2.merchant = "Uber"
        expense2.payment_method = "Card"
        expense2.description = "Ride"

        # Mock historical average to be high so no expense exceeds threshold
        mock_hist_result = MagicMock()
        mock_hist_result.scalar.return_value = Decimal("1000.00")  # High historical avg
        
        # Mock current expenses
        mock_exp_result = MagicMock()
        mock_exp_result.scalars.return_value.all.return_value = [expense1, expense2]

        execute_calls = [mock_hist_result, mock_exp_result]
        analytics_service.db.execute = AsyncMock(side_effect=execute_calls)

        result = await analytics_service.detect_spending_anomalies(user_id)

        # Should return empty list since no anomalies
        assert result == []

    @pytest.mark.asyncio
    async def test_calculate_category_wise_trends_exception_handling(self, analytics_service, user_id):
        """Test calculate_category_wise_trends exception handling (400-402 branch)."""
        analytics_service.db.execute = AsyncMock(side_effect=Exception("Database error"))

        with pytest.raises(Exception, match="Database error"):
            await analytics_service.calculate_category_wise_trends(user_id)

    @pytest.mark.asyncio
    async def test_generate_spending_insights_no_overspending(self, analytics_service, user_id):
        """Test generate_spending_insights with no overspending categories (460->462 branch)."""
        current_date = datetime.now()
        start_of_month = current_date.replace(day=1).date()
        end_of_month = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        end_of_month = end_of_month.date()

        # Create expense within budget
        current_expense = MagicMock(spec=Expense)
        current_expense.amount = Decimal("100.00")
        current_expense.category = "food"
        current_expense.date = start_of_month

        # Mock historical average higher than current
        mock_hist_result = MagicMock()
        mock_hist_result.all.return_value = [
            {"category": "food", "avg_amount": Decimal("500.00")}
        ]

        # Mock current month expenses
        mock_current_result = MagicMock()
        mock_current_result.scalars.return_value.all.return_value = [current_expense]

        execute_calls = [mock_hist_result, mock_current_result]
        analytics_service.db.execute = AsyncMock(side_effect=execute_calls)

        result = await analytics_service.generate_spending_insights(user_id)

        assert result["overspending_categories"] == []
        assert "insights" in result

    @pytest.mark.asyncio
    async def test_calculate_payment_method_analytics_empty_analytics(self, analytics_service, user_id):
        """Test calculate_payment_method_analytics with empty analytics (537-539 branch)."""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

        # No expenses
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        analytics_service.db.execute = AsyncMock(return_value=mock_result)

        result = await analytics_service.calculate_payment_method_analytics(user_id, start_date, end_date)

        assert result == {}

    @pytest.mark.asyncio
    async def test_calculate_weekly_spending_pattern_no_data_exception(self, analytics_service, user_id):
        """Test calculate_weekly_spending_pattern with exception (587-589 branch)."""
        analytics_service.db.execute = AsyncMock(side_effect=Exception("Query failed"))

        with pytest.raises(Exception, match="Query failed"):
            await analytics_service.calculate_weekly_spending_pattern(user_id)

    @pytest.mark.asyncio
    async def test_detect_spending_anomalies_with_single_expense_below_threshold(self, analytics_service, user_id):
        """Test detect_spending_anomalies with single expense below threshold."""
        expense = MagicMock(spec=Expense)
        expense.amount = Decimal("100.00")
        expense.category = "food"
        expense.date = date.today()
        expense.id = uuid4()

        mock_hist_result = MagicMock()
        mock_hist_result.scalar.return_value = Decimal("500.00")  # High avg
        
        mock_exp_result = MagicMock()
        mock_exp_result.scalars.return_value.all.return_value = [expense]

        execute_calls = [mock_hist_result, mock_exp_result]
        analytics_service.db.execute = AsyncMock(side_effect=execute_calls)

        result = await analytics_service.detect_spending_anomalies(user_id)

        assert result == []

    @pytest.mark.asyncio
    async def test_calculate_payment_method_analytics_with_unknown_method(self, analytics_service, user_id):
        """Test calculate_payment_method_analytics with None payment method (sets to 'unknown')."""
        expense = MagicMock(spec=Expense)
        expense.amount = Decimal("200.00")
        expense.category = "food"
        expense.payment_method = None  # Should be recorded as "unknown"
        expense.date = date.today()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [expense]

        analytics_service.db.execute = AsyncMock(return_value=mock_result)

        result = await analytics_service.calculate_payment_method_analytics(
            user_id, date.today() - timedelta(days=30), date.today()
        )

        assert "unknown" in result
        assert result["unknown"] == 200.0

    @pytest.mark.asyncio
    async def test_generate_spending_insights_with_historical_avg_zero(self, analytics_service, user_id):
        """Test generate_spending_insights when historical average is 0 (460->462 branch)."""
        current_date = datetime.now()
        start_of_month = current_date.replace(day=1).date()

        # Create current expense
        current_expense = MagicMock(spec=Expense)
        current_expense.amount = Decimal("100.00")
        current_expense.category = "food"
        current_expense.date = start_of_month

        # Mock historical average as 0
        mock_hist_result = MagicMock()
        mock_hist_result.all.return_value = [
            {"category": "food", "avg_amount": Decimal("0")}  # Zero historical avg
        ]

        # Mock current month expenses
        mock_current_result = MagicMock()
        mock_current_result.scalars.return_value.all.return_value = [current_expense]

        execute_calls = [mock_hist_result, mock_current_result]
        analytics_service.db.execute = AsyncMock(side_effect=execute_calls)

        result = await analytics_service.generate_spending_insights(user_id)

        # With 0 historical avg, condition "historical_avg > 0" fails, no overspending recorded
        assert result["overspending_categories"] == []
        assert "insights" in result

    @pytest.mark.asyncio
    async def test_calculate_payment_method_analytics_multiple_same_method(self, analytics_service, user_id):
        """Test calculate_payment_method_analytics with multiple expenses of same method (537-539 branch)."""
        expense1 = MagicMock(spec=Expense)
        expense1.amount = Decimal("100.00")
        expense1.payment_method = "Card"

        expense2 = MagicMock(spec=Expense)
        expense2.amount = Decimal("150.00")
        expense2.payment_method = "Card"

        expense3 = MagicMock(spec=Expense)
        expense3.amount = Decimal("75.00")
        expense3.payment_method = "Cash"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [expense1, expense2, expense3]

        analytics_service.db.execute = AsyncMock(return_value=mock_result)

        result = await analytics_service.calculate_payment_method_analytics(
            user_id, date.today() - timedelta(days=30), date.today()
        )

        # Multiple expenses with same method should accumulate
        assert result["Card"] == 250.0
        assert result["Cash"] == 75.0
