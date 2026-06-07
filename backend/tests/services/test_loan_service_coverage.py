"""Additional tests for loan service to improve coverage."""
import pytest
from decimal import Decimal
from datetime import date, datetime
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.loan_service import LoanService
from app.schemas.loan import LoanCreate, LoanUpdate
from app.db.models.data import Loan


class TestLoanServiceEdgeCases:
    """Test edge cases and error conditions in loan service."""

    @pytest.fixture
    def loan_service(self):
        """Create loan service with mocked database."""
        mock_db = AsyncMock()
        return LoanService(mock_db)

    @pytest.fixture
    def sample_loan_create(self):
        """Sample loan creation data."""
        return LoanCreate(
            loan_type="Home",
            lender_name="Test Bank",
            principal_amount=Decimal("500000"),
            interest_rate=Decimal("8.5"),
            loan_term_months=240,
            start_date=date.today(),
            emi_amount=None  # Will be calculated
        )

    @pytest.mark.asyncio
    async def test_create_loan_with_calculated_emi(self, loan_service, sample_loan_create):
        """Test loan creation with EMI calculation."""
        user_id = uuid4()
        # Ensure EMI is not provided so it gets calculated
        sample_loan_create.emi_amount = None
        
        with patch('app.services.loan_calculators.EMICalculator.calculate_emi') as mock_emi_calc, \
             patch('app.services.loan_domain.DueDate.calculate_next_due_date') as mock_due_date, \
             patch.object(loan_service, '_loan_to_response') as mock_response:
            
            mock_emi_calc.return_value = Decimal("4500.00")
            mock_due_date.return_value = date.today()
            
            # Mock the response
            mock_loan_response = MagicMock()
            mock_response.return_value = mock_loan_response
            
            # Mock database operations
            loan_service.db.add = MagicMock()
            loan_service.db.commit = AsyncMock()
            loan_service.db.refresh = AsyncMock()
            
            # Mock financial profile service
            loan_service.financial_profile_service.update_from_loans = AsyncMock()
            
            result = await loan_service.create_loan(user_id, sample_loan_create)
            
            # Verify EMI was calculated
            mock_emi_calc.assert_called_once()
            mock_due_date.assert_called_once()
            assert result == mock_loan_response

    @pytest.mark.asyncio
    async def test_create_loan_with_provided_emi(self, loan_service, sample_loan_create):
        """Test loan creation with provided EMI amount."""
        user_id = uuid4()
        sample_loan_create.emi_amount = Decimal("5000.00")
        
        with patch('app.services.loan_calculators.EMICalculator.calculate_emi') as mock_emi_calc, \
             patch('app.services.loan_domain.DueDate.calculate_next_due_date') as mock_due_date, \
             patch.object(loan_service, '_loan_to_response') as mock_response:
            
            mock_due_date.return_value = date.today()
            
            # Mock the response
            mock_loan_response = MagicMock()
            mock_response.return_value = mock_loan_response
            
            # Mock database operations
            loan_service.db.add = MagicMock()
            loan_service.db.commit = AsyncMock()
            loan_service.db.refresh = AsyncMock()
            
            # Mock financial profile service
            loan_service.financial_profile_service.update_from_loans = AsyncMock()
            
            result = await loan_service.create_loan(user_id, sample_loan_create)
            
            # Verify EMI was not calculated since it was provided
            mock_emi_calc.assert_not_called()
            assert result == mock_loan_response

    @pytest.mark.asyncio
    async def test_financial_profile_service_lazy_import(self, loan_service):
        """Test that financial profile service is lazily imported."""
        # Verify the service was set during initialization
        assert loan_service.financial_profile_service is not None

    @pytest.mark.asyncio
    async def test_database_error_handling(self, loan_service, sample_loan_create):
        """Test handling of database errors during loan creation."""
        user_id = uuid4()
        
        with patch('app.services.loan_calculators.EMICalculator.calculate_emi') as mock_emi_calc, \
             patch('app.services.loan_domain.DueDate.calculate_next_due_date') as mock_due_date:
            
            mock_emi_calc.return_value = Decimal("4500.00")
            mock_due_date.return_value = date.today()
            
            # Mock database error
            loan_service.db.commit = AsyncMock(side_effect=Exception("Database error"))
            
            with pytest.raises(Exception):
                await loan_service.create_loan(user_id, sample_loan_create)

    @pytest.mark.asyncio
    async def test_initialization_with_custom_financial_service(self):
        """Test loan service initialization with custom financial service."""
        mock_db = AsyncMock()
        mock_financial_service = MagicMock()
        
        loan_service = LoanService(mock_db, mock_financial_service)
        
        assert loan_service.financial_profile_service == mock_financial_service

    @pytest.mark.asyncio
    async def test_create_loan_enum_handling(self, loan_service):
        """Test loan creation with enum handling."""
        user_id = uuid4()
        
        # Create loan data with enum value
        from app.schemas.loan import LoanType
        loan_create = LoanCreate(
            loan_type=LoanType.PERSONAL,  # Use enum instead of string
            lender_name="Test Bank",
            principal_amount=Decimal("100000"),
            interest_rate=Decimal("12.0"),
            loan_term_months=60,
            start_date=date.today()
        )
        
        with patch('app.services.loan_calculators.EMICalculator.calculate_emi') as mock_emi_calc, \
             patch('app.services.loan_domain.DueDate.calculate_next_due_date') as mock_due_date, \
             patch.object(loan_service, '_loan_to_response') as mock_response:
            
            mock_emi_calc.return_value = Decimal("2000.00")
            mock_due_date.return_value = date.today()
            
            # Mock the response
            mock_loan_response = MagicMock()
            mock_response.return_value = mock_loan_response
            
            # Mock database operations
            loan_service.db.add = MagicMock()
            loan_service.db.commit = AsyncMock()
            loan_service.db.refresh = AsyncMock()
            
            # Mock financial profile service
            loan_service.financial_profile_service.update_from_loans = AsyncMock()
            
            result = await loan_service.create_loan(user_id, loan_create)
            
            # Verify the loan type was properly converted from enum to string
            call_args = loan_service.db.add.call_args[0][0]
            assert call_args.loan_type == "Personal"
            assert result == mock_loan_response


class TestLoanServiceComplexOperations:
    """Test complex operations that might have low coverage."""

    @pytest.fixture
    def loan_service(self):
        mock_db = AsyncMock()
        return LoanService(mock_db)

    @pytest.mark.asyncio
    async def test_invalid_decimal_handling(self, loan_service):
        """Test handling of valid but small decimal values."""
        user_id = uuid4()
        
        # Create loan with small but valid decimal values
        loan_create = LoanCreate(
            loan_type="Personal",
            lender_name="Test Bank",
            principal_amount=Decimal("100.00"),  # Valid amount
            interest_rate=Decimal("0.01"),       # Valid rate (0.01% = 2 decimal places)
            loan_term_months=12,
            start_date=date.today()
        )
        
        with patch('app.services.loan_calculators.EMICalculator.calculate_emi') as mock_emi_calc:
            # Mock EMI calculation
            mock_emi_calc.return_value = Decimal("8.50")
            
            with patch('app.services.loan_domain.DueDate.calculate_next_due_date') as mock_due_date:
                mock_due_date.return_value = date.today()
                
                loan_service.db.add = MagicMock()
                loan_service.db.commit = AsyncMock()
                loan_service.db.refresh = AsyncMock()
                loan_service.financial_profile_service.update_from_loans = AsyncMock()
                
                with patch.object(loan_service, '_loan_to_response') as mock_response:
                    mock_response.return_value = MagicMock()
                    
                    # Should handle small decimal values without error
                    result = await loan_service.create_loan(user_id, loan_create)
                    
                    # Verify the operation completed
                    loan_service.db.add.assert_called_once()
                    loan_service.db.commit.assert_called_once()

    @pytest.mark.asyncio  
    async def test_date_edge_cases(self, loan_service):
        """Test handling of edge case dates."""
        user_id = uuid4()
        
        # Test with start date far in the future
        future_date = date(2030, 12, 31)
        loan_create = LoanCreate(
            loan_type="Personal",
            lender_name="Test Bank", 
            principal_amount=Decimal("100000"),
            interest_rate=Decimal("10.0"),
            loan_term_months=12,
            start_date=future_date
        )
        
        with patch('app.services.loan_calculators.EMICalculator.calculate_emi') as mock_emi_calc, \
             patch('app.services.loan_domain.DueDate.calculate_next_due_date') as mock_due_date, \
             patch.object(loan_service, '_loan_to_response') as mock_response:
            
            mock_emi_calc.return_value = Decimal("9000.00")
            mock_due_date.return_value = future_date
            mock_response.return_value = MagicMock()
            
            loan_service.db.add = MagicMock()
            loan_service.db.commit = AsyncMock()  
            loan_service.db.refresh = AsyncMock()
            loan_service.financial_profile_service.update_from_loans = AsyncMock()
            
            result = await loan_service.create_loan(user_id, loan_create)
            
            # Verify future date was handled correctly
            mock_due_date.assert_called_once_with(future_date)

    @pytest.mark.asyncio
    async def test_large_number_handling(self, loan_service):
        """Test handling of very large loan amounts."""
        user_id = uuid4()
        
        # Test with very large principal amount
        loan_create = LoanCreate(
            loan_type="Business",
            lender_name="Commercial Bank",
            principal_amount=Decimal("100000000.00"),  # 100 million
            interest_rate=Decimal("15.0"),
            loan_term_months=360,  # 30 years
            start_date=date.today()
        )
        
        with patch('app.services.loan_calculators.EMICalculator.calculate_emi') as mock_emi_calc, \
             patch('app.services.loan_domain.DueDate.calculate_next_due_date') as mock_due_date, \
             patch.object(loan_service, '_loan_to_response') as mock_response:
            
            mock_emi_calc.return_value = Decimal("1234567.89")
            mock_due_date.return_value = date.today()
            mock_response.return_value = MagicMock()
            
            loan_service.db.add = MagicMock()
            loan_service.db.commit = AsyncMock()
            loan_service.db.refresh = AsyncMock()
            loan_service.financial_profile_service.update_from_loans = AsyncMock()
            
            result = await loan_service.create_loan(user_id, loan_create)
            
            # Verify large numbers were handled without precision loss
            loan_service.db.add.assert_called_once()
            added_loan = loan_service.db.add.call_args[0][0]
            assert added_loan.principal_amount == Decimal("100000000.00")


class TestLoanServiceLazyLoading:
    """Test lazy loading and dependency injection patterns."""

    def test_default_financial_profile_service_creation(self):
        """Test that financial profile service is created when not provided."""
        mock_db = AsyncMock()
        
        with patch('app.services.budget_service.FinancialProfileService') as mock_service_class:
            mock_service_instance = MagicMock()
            mock_service_class.return_value = mock_service_instance
            
            loan_service = LoanService(mock_db)
            
            # Verify the service was instantiated with the database
            mock_service_class.assert_called_once_with(mock_db)
            assert loan_service.financial_profile_service == mock_service_instance

    def test_custom_financial_profile_service_used(self):
        """Test that custom financial profile service is used when provided."""
        mock_db = AsyncMock()
        custom_service = MagicMock()
        
        loan_service = LoanService(mock_db, custom_service)
        
        assert loan_service.financial_profile_service == custom_service


class TestLoanServiceInitialization:
    """Test loan service initialization scenarios."""

    def test_initialization_with_minimal_parameters(self):
        """Test initialization with only required parameters."""
        mock_db = AsyncMock()
        
        loan_service = LoanService(mock_db)
        
        assert loan_service.db == mock_db
        assert loan_service.financial_profile_service is not None

    def test_initialization_with_all_parameters(self):
        """Test initialization with all parameters."""
        mock_db = AsyncMock()
        mock_financial_service = MagicMock()
        
        loan_service = LoanService(mock_db, mock_financial_service)
        
        assert loan_service.db == mock_db
        assert loan_service.financial_profile_service == mock_financial_service

    @pytest.mark.asyncio
    async def test_service_dependencies_are_available(self):
        """Test that all required dependencies are properly available."""
        mock_db = AsyncMock()
        loan_service = LoanService(mock_db)
        
        # Verify all required attributes are present
        assert hasattr(loan_service, 'db')
        assert hasattr(loan_service, 'financial_profile_service')
        
        # Verify they are not None
        assert loan_service.db is not None
        assert loan_service.financial_profile_service is not None
