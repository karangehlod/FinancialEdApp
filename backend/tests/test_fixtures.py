"""Test fixtures to verify integration test infrastructure works."""
import pytest
from sqlalchemy import text
from tests.conftest import test_auth_db, test_data_db, test_user, authenticated_client


class TestFixturesIntegration:
    """Test that all fixtures work together."""
    
    def test_auth_db_fixture_creates_database(self, test_auth_db):
        """Test that auth database fixture creates a working database."""
        assert test_auth_db is not None
        # Query the database to verify it's working
        result = test_auth_db.execute(text("SELECT 1"))
        assert result is not None
    
    def test_data_db_fixture_creates_database(self, test_data_db):
        """Test that data database fixture creates a working database."""
        assert test_data_db is not None
        # Query the database to verify it's working
        result = test_data_db.execute(text("SELECT 1"))
        assert result is not None
    
    def test_test_user_created(self, test_user):
        """Test that test user is created correctly."""
        assert test_user is not None
        assert test_user.email == "test@example.com"
        assert test_user.is_active is True
        assert test_user.is_verified is True
    
    def test_authenticated_client_has_auth_header(self, authenticated_client):
        """Test that authenticated client has authorization header."""
        assert authenticated_client is not None
        assert "Authorization" in authenticated_client.headers
        assert authenticated_client.headers["Authorization"].startswith("Bearer ")
    
    def test_sample_data_fixtures(self, sample_loan_data, sample_budget_data, 
                                   sample_expense_data, sample_goal_data):
        """Test that sample data fixtures generate correct data."""
        assert sample_loan_data["principal_amount"] == 500000.0
        assert sample_budget_data["category"] == "Food"
        assert sample_expense_data["amount"] == 5000.0
        assert sample_goal_data["title"] == "Emergency Fund"
