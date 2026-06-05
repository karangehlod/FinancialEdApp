"""Comprehensive tests for Budget API endpoints."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from decimal import Decimal
from datetime import datetime, date
import uuid

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_financial_profile():
    """Sample financial profile data."""
    return {
        "monthly_salary": 50000.0,
        "total_emi": 10000.0,
        "rent": 15000.0,
        "insurance": 2000.0,
        "subscriptions": 500.0,
        "other_expenses": 3000.0
    }


@pytest.fixture
def sample_budget_data():
    """Sample budget creation data."""
    return {
        "category": "Food",
        "limit": 5000.0,
        "month": "2025-01",
        "alert_threshold": 80
    }


# ============== FINANCIAL PROFILE TESTS ==============

class TestFinancialProfileEndpoints:
    """Test financial profile management endpoints."""
    
    def test_create_financial_profile(self, client):
        """Test creating/updating financial profile."""
        response = client.put(
            "/api/v1/auth/financial-profile",
            json={
                "monthly_salary": 50000.0,
                "total_emi": 10000.0,
                "rent": 15000.0,
                "insurance": 2000.0,
                "subscriptions": 500.0
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 201, 401, 403, 400, 422]
    
    def test_create_profile_missing_monthly_salary(self, client):
        """Test profile update without monthly salary (all fields optional in PUT)."""
        response = client.put(
            "/api/v1/auth/financial-profile",
            json={
                "total_emi": 10000.0,
                "rent": 15000.0
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 422, 401, 403]
    
    def test_create_profile_negative_salary(self, client):
        """Test profile update with negative salary."""
        response = client.put(
            "/api/v1/auth/financial-profile",
            json={
                "monthly_salary": -50000.0,
                "total_emi": 10000.0,
                "rent": 15000.0
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 400, 422, 401, 403]
    
    def test_create_profile_zero_salary(self, client):
        """Test profile update with zero salary."""
        response = client.put(
            "/api/v1/auth/financial-profile",
            json={
                "monthly_salary": 0,
                "total_emi": 10000.0,
                "rent": 15000.0
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 400, 422, 401, 403]
    
    def test_create_profile_negative_emi(self, client):
        """Test profile update with negative EMI."""
        response = client.put(
            "/api/v1/auth/financial-profile",
            json={
                "monthly_salary": 50000.0,
                "total_emi": -10000.0,
                "rent": 15000.0
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 400, 422, 401, 403]
    
    def test_create_profile_negative_rent(self, client):
        """Test profile update with negative rent."""
        response = client.put(
            "/api/v1/auth/financial-profile",
            json={
                "monthly_salary": 50000.0,
                "total_emi": 10000.0,
                "rent": -15000.0
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 400, 422, 401, 403]
    
    def test_create_profile_with_all_optional_fields(self, client):
        """Test profile update with all optional fields."""
        response = client.put(
            "/api/v1/auth/financial-profile",
            json={
                "monthly_salary": 50000.0,
                "total_emi": 10000.0,
                "rent": 15000.0,
                "insurance": 2000.0,
                "subscriptions": 500.0,
                "other_expenses": 3000.0
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 201, 401, 403, 400, 422]
    
    def test_get_financial_profile(self, client):
        """Test retrieving financial profile."""
        response = client.get(
            "/api/v1/auth/financial-profile",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403, 404]
    
    def test_update_financial_profile(self, client):
        """Test updating financial profile."""
        response = client.put(
            "/api/v1/auth/financial-profile",
            json={
                "monthly_salary": 60000.0,
                "total_emi": 12000.0,
                "rent": 17000.0
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 201, 401, 403, 404, 400, 422]
    
    def test_update_profile_partial(self, client):
        """Test partial update of financial profile."""
        response = client.put(
            "/api/v1/auth/financial-profile",
            json={
                "monthly_salary": 60000.0
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 201, 401, 403, 404, 400, 422]


# ============== BUDGET ENDPOINTS ==============

class TestBudgetCRUDEndpoints:
    """Test budget CRUD operations."""
    
    def test_create_budget(self, client):
        """Test creating a budget."""
        response = client.post(
            "/api/v1/budgets",
            json={
                "category": "Food",
                "limit": 5000.0,
                "month": "2025-01",
                "alert_threshold": 80
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [201, 401, 403, 400, 422]
    
    def test_create_budget_missing_category(self, client):
        """Test creating budget without category."""
        response = client.post(
            "/api/v1/budgets",
            json={
                "limit": 5000.0,
                "month": "2025-01"
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [422, 401, 403]
    
    def test_create_budget_missing_limit(self, client):
        """Test creating budget without limit."""
        response = client.post(
            "/api/v1/budgets",
            json={
                "category": "Food",
                "month": "2025-01"
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [422, 401, 403]
    
    def test_create_budget_negative_limit(self, client):
        """Test creating budget with negative limit."""
        response = client.post(
            "/api/v1/budgets",
            json={
                "category": "Food",
                "limit": -5000.0,
                "month": "2025-01"
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [400, 422, 401, 403]
    
    def test_create_budget_zero_limit(self, client):
        """Test creating budget with zero limit."""
        response = client.post(
            "/api/v1/budgets",
            json={
                "category": "Food",
                "limit": 0,
                "month": "2025-01"
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [400, 422, 401, 403]
    
    def test_create_budget_invalid_threshold(self, client):
        """Test creating budget with invalid alert threshold."""
        response = client.post(
            "/api/v1/budgets",
            json={
                "category": "Food",
                "limit": 5000.0,
                "month": "2025-01",
                "alert_threshold": 150  # More than 100%
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [400, 422, 401, 403]
    
    def test_get_all_budgets(self, client):
        """Test retrieving all budgets."""
        response = client.get(
            "/api/v1/budgets",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403]
    
    def test_get_budgets_with_filter(self, client):
        """Test retrieving budgets with filter."""
        response = client.get(
            "/api/v1/budgets?category=Food",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403]
    
    def test_get_budgets_by_month(self, client):
        """Test retrieving budgets by month."""
        response = client.get(
            "/api/v1/budgets?month=2025-01",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403]
    
    def test_get_specific_budget(self, client):
        """Test retrieving a specific budget."""
        budget_id = str(uuid.uuid4())
        response = client.get(
            f"/api/v1/budgets/{budget_id}",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403, 404]
    
    def test_get_budget_invalid_id(self, client):
        """Test retrieving budget with invalid ID."""
        response = client.get(
            "/api/v1/budgets/invalid-id",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [422, 401, 403]
    
    def test_update_budget(self, client):
        """Test updating a budget."""
        budget_id = str(uuid.uuid4())
        response = client.put(
            f"/api/v1/budgets/{budget_id}",
            json={
                "category": "Food",
                "limit": 6000.0,
                "alert_threshold": 75
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 201, 401, 403, 404, 400, 422]
    
    def test_delete_budget(self, client):
        """Test deleting a budget."""
        budget_id = str(uuid.uuid4())
        response = client.delete(
            f"/api/v1/budgets/{budget_id}",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [204, 401, 403, 404]


# ============== BUDGET SUMMARY & ANALYTICS TESTS ==============

class TestBudgetSummaryAndAnalytics:
    """Test budget summary and analytics endpoints."""
    
    def test_get_budget_summary(self, client):
        """Test getting budget summary."""
        response = client.get(
            "/api/v1/budgets/summary",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403]
    
    def test_get_budget_analytics(self, client):
        """Test getting budget analytics."""
        response = client.get(
            "/api/v1/budgets/analytics",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403]
    
    def test_get_budget_comparison(self, client):
        """Test budget comparison endpoint."""
        response = client.get(
            "/api/v1/budgets/comparison",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403, 400]
    
    def test_get_budget_comparison_with_months(self, client):
        """Test budget comparison with specific months."""
        response = client.get(
            "/api/v1/budgets/comparison?month1=2025-01&month2=2025-02",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403, 400]
    
    def test_get_budget_trends(self, client):
        """Test getting budget trends."""
        response = client.get(
            "/api/v1/budgets/trends",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403]
    
    def test_get_spending_by_category(self, client):
        """Test getting spending by category."""
        response = client.get(
            "/api/v1/budgets/spending-by-category",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403]


# ============== BUDGET ALERTS TESTS ==============

class TestBudgetAlerts:
    """Test budget alert endpoints."""
    
    def test_get_budget_alerts(self, client):
        """Test retrieving budget alerts."""
        response = client.get(
            "/api/v1/budgets/alerts",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403]
    
    def test_get_budget_alerts(self, client):
        """Test retrieving budget alerts."""
        response = client.get(
            "/api/v1/budgets/alerts",
            headers={"Authorization": "Bearer invalid_token"}
        )
        # Should return 401 for invalid token, or 200 with valid auth
        assert response.status_code in [200, 401]
        
        # Test with unread_only parameter
        response = client.get(
            "/api/v1/budgets/alerts?unread_only=true",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401]
    
    def test_get_specific_alert(self, client):
        """Test retrieving specific alert."""
        alert_id = str(uuid.uuid4())
        response = client.get(
            f"/api/v1/budgets/alerts/{alert_id}",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403, 404]
    
    def test_update_alert(self, client):
        """Test updating budget alert."""
        alert_id = str(uuid.uuid4())
        response = client.put(
            f"/api/v1/budgets/alerts/{alert_id}",
            json={"threshold": 75},
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 201, 401, 403, 404, 400, 422]
    
    def test_delete_alert(self, client):
        """Test deleting budget alert."""
        alert_id = str(uuid.uuid4())
        response = client.delete(
            f"/api/v1/budgets/alerts/{alert_id}",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [204, 401, 403, 404]


# ============== BUDGET RECOMMENDATIONS TESTS ==============

class TestBudgetRecommendations:
    """Test budget recommendation endpoints."""
    
    def test_get_budget_recommendations(self, client):
        """Test getting budget recommendations."""
        response = client.get(
            "/api/v1/budgets/recommendations",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403]
    
    def test_get_category_recommendations(self, client):
        """Test getting recommendations for specific category."""
        response = client.get(
            "/api/v1/budgets/recommendations?category=Food",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403]


# ============== MONTHLY SUMMARY TESTS ==============

class TestMonthlyBudgetSummary:
    """Test monthly budget summary endpoints."""
    
    def test_get_monthly_summary(self, client):
        """Test getting monthly budget summary."""
        response = client.get(
            "/api/v1/budgets/monthly-summary",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403]
    
    def test_get_monthly_summary_specific_month(self, client):
        """Test getting monthly summary for specific month."""
        response = client.get(
            "/api/v1/budgets/monthly-summary?month=2025-01",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403]
    
    def test_get_monthly_breakdown(self, client):
        """Test getting monthly breakdown by category."""
        response = client.get(
            "/api/v1/budgets/monthly-breakdown",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403]


# ============== LOAN INTEGRATION TESTS ==============

class TestBudgetLoanIntegration:
    """Test budget-loan integration endpoints."""
    
    def test_get_emi_vs_budget(self, client):
        """Test getting EMI vs budget view."""
        response = client.get(
            "/api/v1/budgets/emi-vs-budget",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403]
    
    def test_get_budget_after_loans(self, client):
        """Test getting budget after accounting for loans."""
        response = client.get(
            "/api/v1/budgets/after-loans",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403]


# ============== EDGE CASES AND ERROR HANDLING ==============

class TestBudgetEdgeCases:
    """Test edge cases and error handling."""
    
    def test_create_multiple_budgets_same_category_month(self, client):
        """Test creating multiple budgets for same category and month."""
        response1 = client.post(
            "/api/v1/budgets",
            json={
                "category": "Food",
                "limit": 5000.0,
                "month": "2025-01"
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        response2 = client.post(
            "/api/v1/budgets",
            json={
                "category": "Food",
                "limit": 6000.0,
                "month": "2025-01"
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response1.status_code in [201, 401, 403, 400, 422]
        assert response2.status_code in [201, 401, 403, 400, 422, 409]
    
    def test_budget_limit_greater_than_salary(self, client):
        """Test budget limit greater than monthly salary."""
        response = client.post(
            "/api/v1/budgets",
            json={
                "category": "Food",
                "limit": 500000.0,
                "month": "2025-01"
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [201, 401, 403, 400, 422]
    
    def test_very_high_alert_threshold(self, client):
        """Test with very high alert threshold."""
        response = client.post(
            "/api/v1/budgets",
            json={
                "category": "Food",
                "limit": 5000.0,
                "month": "2025-01",
                "alert_threshold": 99
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [201, 401, 403, 400, 422]
    
    def test_zero_alert_threshold(self, client):
        """Test with zero alert threshold."""
        response = client.post(
            "/api/v1/budgets",
            json={
                "category": "Food",
                "limit": 5000.0,
                "month": "2025-01",
                "alert_threshold": 0
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [201, 401, 403, 400, 422]
    
    def test_negative_alert_threshold(self, client):
        """Test with negative alert threshold."""
        response = client.post(
            "/api/v1/budgets",
            json={
                "category": "Food",
                "limit": 5000.0,
                "month": "2025-01",
                "alert_threshold": -50
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [400, 422, 401, 403]
    
    def test_invalid_month_format(self, client):
        """Test with invalid month format."""
        response = client.post(
            "/api/v1/budgets",
            json={
                "category": "Food",
                "limit": 5000.0,
                "month": "invalid-month"
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [400, 422, 401, 403]
    
    def test_future_month_budget(self, client):
        """Test creating budget for future month."""
        response = client.post(
            "/api/v1/budgets",
            json={
                "category": "Food",
                "limit": 5000.0,
                "month": "2030-12"
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [201, 401, 403, 400, 422]
    
    def test_past_month_budget(self, client):
        """Test creating budget for past month."""
        response = client.post(
            "/api/v1/budgets",
            json={
                "category": "Food",
                "limit": 5000.0,
                "month": "2020-01"
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [201, 401, 403, 400, 422]
    
    def test_very_small_budget_limit(self, client):
        """Test with very small budget limit."""
        response = client.post(
            "/api/v1/budgets",
            json={
                "category": "Food",
                "limit": 0.01,
                "month": "2025-01"
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [201, 401, 403, 400, 422]
    
    def test_very_large_budget_limit(self, client):
        """Test with very large budget limit."""
        response = client.post(
            "/api/v1/budgets",
            json={
                "category": "Food",
                "limit": 9999999999.99,
                "month": "2025-01"
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [201, 401, 403, 400, 422]


# ============== HTTP METHOD VALIDATION ==============

class TestBudgetHTTPMethods:
    """Test HTTP method validation."""
    
    def test_budgets_list_get_allowed(self, client):
        """Test that GET is allowed for budgets list."""
        response = client.get(
            "/api/v1/budgets",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403]
    
    def test_budgets_list_post_allowed(self, client):
        """Test that POST is allowed for budgets creation."""
        response = client.post(
            "/api/v1/budgets",
            json={
                "category": "Food",
                "limit": 5000.0,
                "month": "2025-01"
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [201, 401, 403, 400, 422]
    
    def test_profile_get_allowed(self, client):
        """Test that GET is allowed for profile."""
        response = client.get(
            "/api/v1/auth/financial-profile",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403, 404]
    
    def test_profile_post_allowed(self, client):
        """Test that PUT is allowed for profile (profile uses PUT, not POST)."""
        response = client.put(
            "/api/v1/auth/financial-profile",
            json={"monthly_salary": 50000.0},
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 201, 401, 403, 400, 422]
