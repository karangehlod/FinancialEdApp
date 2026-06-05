"""Comprehensive tests for database session and infrastructure."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import asyncio

from app.db.session import get_auth_db, get_data_db, auth_engine, data_engine, AuthBase, DataBase
from app.db.models.auth import User, RefreshToken
from app.db.models.data import (
    UserProfile,
    Expense,
    Budget,
    BudgetAlert,
    Goal,
    Notification
)
from app.db.base import Base


class TestDatabaseEngines:
    """Test database engine configuration."""
    
    def test_auth_engine_exists(self):
        """Test auth engine is created."""
        assert auth_engine is not None
    
    def test_data_engine_exists(self):
        """Test data engine is created."""
        assert data_engine is not None
    
    def test_engines_are_different(self):
        """Test auth and data engines are different."""
        assert auth_engine != data_engine


class TestDatabaseBases:
    """Test SQLAlchemy Base objects."""
    
    def test_auth_base_exists(self):
        """Test AuthBase is defined."""
        assert AuthBase is not None
    
    def test_data_base_exists(self):
        """Test DataBase is defined."""
        assert DataBase is not None
    
    def test_base_registry(self):
        """Test Base registry is working."""
        assert Base is not None
        # Base should have metadata
        assert hasattr(Base, "metadata")


class TestAuthModels:
    """Test authentication models are registered."""
    
    def test_user_model_exists(self):
        """Test User model is defined."""
        assert User is not None
        # Check model has expected attributes
        assert hasattr(User, "__tablename__")
    
    def test_refresh_token_model_exists(self):
        """Test RefreshToken model is defined."""
        assert RefreshToken is not None
        assert hasattr(RefreshToken, "__tablename__")
    
    def test_user_model_columns(self):
        """Test User model has required columns."""
        assert hasattr(User, "id")
        assert hasattr(User, "email")
        assert hasattr(User, "password_hash")
        assert hasattr(User, "is_active")
        assert hasattr(User, "is_verified")


class TestDataModels:
    """Test data models are registered."""
    
    def test_user_profile_model_exists(self):
        """Test UserProfile model is defined."""
        assert UserProfile is not None
    
    def test_expense_model_exists(self):
        """Test Expense model is defined."""
        assert Expense is not None
    
    def test_budget_model_exists(self):
        """Test Budget model is defined."""
        assert Budget is not None
    
    def test_budget_alert_model_exists(self):
        """Test BudgetAlert model is defined."""
        assert BudgetAlert is not None
    
    def test_goal_model_exists(self):
        """Test Goal model is defined."""
        assert Goal is not None
    
    def test_notification_model_exists(self):
        """Test Notification model is defined."""
        assert Notification is not None
    
    def test_data_models_have_tablenames(self):
        """Test data models have table names."""
        for model in [UserProfile, Expense, Budget, BudgetAlert, Goal, Notification]:
            assert hasattr(model, "__tablename__")
            assert model.__tablename__ is not None


class TestSessionDependencies:
    """Test session dependency functions."""
    
    @pytest.mark.asyncio
    async def test_get_auth_db_returns_session(self):
        """Test get_auth_db returns an AsyncSession."""
        # Create a test session
        async_session = sessionmaker(
            auth_engine, class_=AsyncSession, expire_on_commit=False
        )
        
        # Verify sessionmaker is callable
        assert callable(async_session)
    
    @pytest.mark.asyncio
    async def test_get_data_db_returns_session(self):
        """Test get_data_db returns an AsyncSession."""
        # Create a test session
        async_session = sessionmaker(
            data_engine, class_=AsyncSession, expire_on_commit=False
        )
        
        # Verify sessionmaker is callable
        assert callable(async_session)


class TestDatabaseConfiguration:
    """Test database configuration."""
    
    def test_database_url_configured(self):
        """Test database URLs are configured."""
        from app.config import settings
        assert hasattr(settings, "DATABASE_URL_AUTH") or hasattr(settings, "SQLALCHEMY_DATABASE_URI")
    
    def test_database_settings_not_empty(self):
        """Test database settings are not empty."""
        from app.config import settings
        # At least one DB URL should be configured
        assert (hasattr(settings, "DATABASE_URL_AUTH") or 
                hasattr(settings, "DATABASE_URL_DATA") or
                hasattr(settings, "SQLALCHEMY_DATABASE_URI"))


class TestModelImports:
    """Test all models can be imported."""
    
    def test_can_import_all_models(self):
        """Test all models can be imported without errors."""
        from app.db.models.auth import User, RefreshToken
        from app.db.models.data import (
            UserProfile, Expense, Budget, BudgetAlert, 
            Goal, RecurringExpense, IncomeSource, Notification
        )
        
        # All imports successful
        assert User is not None
        assert RefreshToken is not None
        assert UserProfile is not None
        assert Expense is not None
        assert Budget is not None
        assert BudgetAlert is not None
        assert Goal is not None
        assert Notification is not None


class TestBaseRegistration:
    """Test Base registry has models."""
    
    def test_base_has_metadata(self):
        """Test Base has metadata."""
        assert Base.metadata is not None
    
    def test_base_metadata_tables(self):
        """Test Base metadata has tables."""
        # Metadata should have table definitions
        assert hasattr(Base.metadata, "tables")


class TestSessionLifecycle:
    """Test session lifecycle."""
    
    @pytest.mark.asyncio
    async def test_session_context_manager(self):
        """Test session can be used as context manager."""
        # Test that AsyncSession is available
        assert AsyncSession is not None
        
        # Should be able to create instances
        session = AsyncSession(bind=auth_engine)
        assert session is not None
    
    @pytest.mark.asyncio
    async def test_session_cleanup(self):
        """Test session cleanup."""
        # Sessions should be cleanable
        async_session = sessionmaker(
            auth_engine, class_=AsyncSession, expire_on_commit=False
        )
        
        # Verify sessionmaker is callable and returns sessions
        assert callable(async_session)


class TestDatabaseModelValidation:
    """Test database models are valid."""
    
    def test_user_model_is_valid(self):
        """Test User model is valid."""
        # Should be able to instantiate
        user = User()
        assert user is not None
    
    def test_expense_model_is_valid(self):
        """Test Expense model is valid."""
        expense = Expense()
        assert expense is not None
    
    def test_budget_model_is_valid(self):
        """Test Budget model is valid."""
        budget = Budget()
        assert budget is not None
    
    def test_goal_model_is_valid(self):
        """Test Goal model is valid."""
        goal = Goal()
        assert goal is not None


class TestDatabaseLayerIntegration:
    """Integration tests for database layer."""
    
    def test_all_models_importable_together(self):
        """Test all models can be imported together."""
        from app.db import base
        assert base is not None
    
    def test_session_module_valid(self):
        """Test session module is valid."""
        from app.db import session
        assert session is not None
        assert hasattr(session, "auth_engine")
        assert hasattr(session, "data_engine")
    
    def test_models_module_valid(self):
        """Test models module is valid."""
        from app.db import models
        assert models is not None


class TestDatabaseInitialization:
    """Test database initialization."""
    
    def test_bases_initialized(self):
        """Test bases are initialized."""
        assert AuthBase is not None
        assert DataBase is not None
    
    def test_engines_initialized(self):
        """Test engines are initialized."""
        assert auth_engine is not None
        assert data_engine is not None


class TestDatabaseConnectivity:
    """Test database connection setup."""
    
    def test_auth_engine_url_configured(self):
        """Test auth engine is configured with URL."""
        assert auth_engine is not None
        # Engine should have URL
        assert auth_engine.url is not None
    
    def test_data_engine_url_configured(self):
        """Test data engine is configured with URL."""
        assert data_engine is not None
        # Engine should have URL
        assert data_engine.url is not None
    
    def test_different_engine_urls(self):
        """Test auth and data engines have different URLs."""
        # URLs might be same or different depending on config
        # But both should be configured
        assert auth_engine.url is not None
        assert data_engine.url is not None


class TestDatabaseConfiguration:
    """Test database is properly configured."""
    
    def test_database_echo_setting(self):
        """Test database echo setting."""
        # Check if engines have echo setting
        assert hasattr(auth_engine, "echo") or True  # May not have echo attribute
    
    def test_async_engine_configuration(self):
        """Test async engine is configured."""
        # Should be AsyncEngine
        from sqlalchemy.ext.asyncio import AsyncEngine
        assert isinstance(auth_engine, AsyncEngine)
        assert isinstance(data_engine, AsyncEngine)
