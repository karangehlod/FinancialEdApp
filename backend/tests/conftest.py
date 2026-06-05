"""Shared pytest configuration and fixtures for integration tests."""
import pytest
import uuid
from datetime import datetime, timedelta, date
from typing import Generator, Optional, AsyncGenerator
from unittest.mock import MagicMock, patch, AsyncMock
from decimal import Decimal
import asyncio
import httpx
import os

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from jose import jwt

from app.main import app
from app.config import settings
from app.db.session import AuthBase, DataBase, get_auth_db, get_data_db
from app.dependencies import get_current_user, get_redis_cache
from app.core.security_compat import hash_password, create_access_token
from app.db.models.auth import User
from app.db.models.data import (
    Loan, Budget, Expense, Goal, Notification, 
    IncomeSource, RecurringExpense
)
from app.core.provider_implementations import RedisCache


# ============== DATABASE FIXTURES ==============

@pytest.fixture(scope="function")
async def async_test_auth_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Create an in-memory async SQLite database for auth tests.
    """
    # Create in-memory SQLite engine (async)
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        pool_pre_ping=True,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(AuthBase.metadata.create_all)
    
    # Create session factory
    TestingSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with TestingSessionLocal() as session:
        yield session
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(AuthBase.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture(scope="function")
async def async_test_data_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Create an in-memory async SQLite database for data tests.
    """
    # Create in-memory SQLite engine (async)
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        pool_pre_ping=True,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(DataBase.metadata.create_all)
    
    # Create session factory
    TestingSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with TestingSessionLocal() as session:
        yield session
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(DataBase.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture(scope="function")
def test_auth_db() -> Generator[Session, None, None]:
    """
    Create an in-memory SQLite database for authentication tests.
    
    This fixture:
    - Creates a fresh database for each test
    - Automatically cleans up after the test
    - Provides an isolated test environment
    """
    # Create in-memory SQLite engine
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Create all tables using AuthBase
    AuthBase.metadata.create_all(engine)
    
    # Create session
    TestingSessionLocal = sessionmaker(
        autocommit=False, 
        autoflush=False, 
        bind=engine
    )
    
    db = TestingSessionLocal()
    
    yield db
    
    # Cleanup
    db.close()
    AuthBase.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def test_data_db() -> Generator[Session, None, None]:
    """
    Create an in-memory SQLite database for data tests.
    
    This fixture:
    - Creates a fresh database for each test
    - Automatically cleans up after the test
    - Provides an isolated test environment
    """
    # Create in-memory SQLite engine
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Create all tables using DataBase
    DataBase.metadata.create_all(engine)
    
    # Create session
    TestingSessionLocal = sessionmaker(
        autocommit=False, 
        autoflush=False, 
        bind=engine
    )
    
    db = TestingSessionLocal()
    
    yield db
    
    # Cleanup
    db.close()
    DataBase.metadata.drop_all(engine)


# ============== USER FIXTURES ==============

@pytest.fixture
def test_user_id() -> uuid.UUID:
    """Generate a test user ID."""
    return uuid.uuid4()


@pytest.fixture
def test_user(test_auth_db: Session, test_user_id: uuid.UUID) -> User:
    """
    Create a test user in the database.
    
    This fixture:
    - Creates a user with known credentials
    - Returns the user object for testing
    - Can be used to set up other test data
    """
    user = User(
        id=test_user_id,
        email="test@example.com",
        password_hash=hash_password("testpassword123"),
        is_active=True,
        is_verified=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    test_auth_db.add(user)
    test_auth_db.commit()
    test_auth_db.refresh(user)
    return user


@pytest.fixture
def another_test_user(test_auth_db: Session) -> User:
    """Create another test user for permission/authorization tests."""
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="another@example.com",
        password_hash=hash_password("anotherpass123"),
        is_active=True,
        is_verified=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    test_auth_db.add(user)
    test_auth_db.commit()
    test_auth_db.refresh(user)
    return user


# ============== AUTHENTICATION FIXTURES ==============

@pytest.fixture
def jwt_token(test_user: User) -> str:
    """
    Generate a valid JWT token for testing.
    
    This fixture:
    - Creates a token for the test user
    - Uses the same secret key and algorithm as the app
    - Token is valid for 1 hour (typical test duration)
    """
    expires = datetime.utcnow() + timedelta(hours=1)
    to_encode = {
        "sub": str(test_user.id),
        "exp": expires,
        "type": "access"
    }
    token = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    return token


@pytest.fixture
def invalid_jwt_token() -> str:
    """Generate an invalid JWT token for testing error handling."""
    return "invalid.token.here"


@pytest.fixture
def expired_jwt_token(test_user: User) -> str:
    """Generate an expired JWT token for testing token expiration."""
    expires = datetime.utcnow() - timedelta(hours=1)  # Expired 1 hour ago
    to_encode = {
        "sub": str(test_user.id),
        "exp": expires,
        "type": "access"
    }
    token = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    return token


# ============== TEST CLIENT FIXTURES ==============

@pytest.fixture
def client(async_test_auth_db: AsyncSession, async_test_data_db: AsyncSession) -> TestClient:
    """
    Create a basic test client without authentication but with database overrides.
    
    Use this for:
    - Testing unauthenticated endpoints
    - Testing auth endpoints (login, register, etc.)
    - Testing error responses (401 Unauthorized)
    """
    # Provide Redis cache for testing: prefer a real Redis when requested
    # Set the environment variable TEST_REAL_REDIS=1 and ensure settings.REDIS_URL
    # points to a running Redis instance to exercise TTL and concurrency behaviors.
    from app.config import settings as _settings

    async def _build_redis_cache():
        # Real Redis path
        if os.getenv("TEST_REAL_REDIS", "0") in ("1", "true", "True") and getattr(_settings, 'REDIS_URL', None):
            from redis import asyncio as aioredis
            client = aioredis.from_url(
                _settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            # Ensure reachable
            try:
                await client.ping()
                # Clean DB to avoid cross-test pollution
                try:
                    await client.flushdb()
                except Exception:
                    pass
                return RedisCache(client)
            except Exception:
                # Fallback to mock if real redis not reachable
                pass

        # Default: lightweight MagicMock cache provider (synchronous methods mimicked)
        mock_redis_cache = MagicMock()
        async def _get(k):
            return None
        async def _set(k, v, ttl=None):
            return True
        async def _delete(k):
            return True
        async def _exists(k):
            return 0
        mock_redis_cache.get = AsyncMock(side_effect=_get)
        mock_redis_cache.set = AsyncMock(side_effect=_set)
        mock_redis_cache.delete = AsyncMock(side_effect=_delete)
        mock_redis_cache.exists = AsyncMock(side_effect=_exists)
        return mock_redis_cache

    # Resolve cache provider (async builder run) — tests expect dependency override to return an object
    # We run the builder synchronously here because TestClient startup is synchronous; use asyncio.run when needed.
    try:
        redis_cache = asyncio.get_event_loop().run_until_complete(_build_redis_cache())
    except RuntimeError:
        # If no running loop (pytest on some setups), create a new event loop
        loop = asyncio.new_event_loop()
        try:
            redis_cache = loop.run_until_complete(_build_redis_cache())
        finally:
            loop.close()

    # Override database dependencies - async generators for async sessions
    async def override_get_auth_db():
        yield async_test_auth_db
    
    async def override_get_data_db():
        yield async_test_data_db
    
    # Override dependencies
    app.dependency_overrides[get_redis_cache] = lambda: redis_cache
    app.dependency_overrides[get_auth_db] = override_get_auth_db
    app.dependency_overrides[get_data_db] = override_get_data_db
    
    try:
        yield TestClient(app)
    finally:
        # Cleanup: clear dependency overrides
        for dep in [get_redis_cache, get_auth_db, get_data_db]:
            if dep in app.dependency_overrides:
                del app.dependency_overrides[dep]


@pytest.fixture
def authenticated_client(
    client: TestClient, 
    test_user: User, 
    jwt_token: str,
    test_auth_db: Session,
    test_data_db: Session
) -> TestClient:
    """
    Create a test client with authentication and database overrides.
    
    This fixture:
    - Injects a valid JWT token into requests
    - Overrides database dependencies with test databases
    - Returns a ready-to-use client for authenticated tests
    
    Use this for:
    - Testing protected endpoints
    - Testing endpoints that require user context
    - Integration tests that need database access
    """
    # Override the get_current_user dependency - must be async
    async def override_get_current_user() -> User:
        return test_user
    
    # Override database dependencies - must be async generators
    async def override_get_auth_db():
        yield test_auth_db
    
    async def override_get_data_db():
        yield test_data_db
    
    # Apply overrides
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_auth_db] = override_get_auth_db
    app.dependency_overrides[get_data_db] = override_get_data_db
    
    # Create client with auth header
    client = TestClient(app)
    client.headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    
    yield client
    
    # Cleanup: clear dependency overrides
    app.dependency_overrides.clear()


@pytest.fixture
def other_user_authenticated_client(
    client: TestClient,
    another_test_user: User,
    test_auth_db: Session,
    test_data_db: Session
) -> TestClient:
    """
    Create a test client authenticated as a different user.
    
    Use this for:
    - Testing authorization (access denied to other users' data)
    - Testing multi-user scenarios
    - Testing permission checks
    """
    # Generate token for the other user
    expires = datetime.utcnow() + timedelta(hours=1)
    to_encode = {
        "sub": str(another_test_user.id),
        "exp": expires,
        "type": "access"
    }
    jwt_token = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    
    # Override the get_current_user dependency
    async def override_get_current_user() -> User:
        return another_test_user
    
    # Override database dependencies
    def override_get_auth_db():
        return test_auth_db
    
    def override_get_data_db():
        return test_data_db
    
    # Apply overrides
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_auth_db] = override_get_auth_db
    app.dependency_overrides[get_data_db] = override_get_data_db
    
    # Create client with auth header
    client = TestClient(app)
    client.headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    
    yield client
    
    # Cleanup
    app.dependency_overrides.clear()


# ============== DATA MODEL FIXTURES ==============

@pytest.fixture
def sample_loan_data() -> dict:
    """Generate sample loan creation data."""
    return {
        "principal_amount": 500000.0,
        "interest_rate": 8.5,
        "tenure_months": 120,
        "start_date": "2025-01-15",
        "loan_type": "Home Loan",
        "lender": "HDFC Bank",
        "notes": "Home loan for house purchase"
    }


@pytest.fixture
def sample_budget_data() -> dict:
    """Generate sample budget creation data."""
    return {
        "month": "2025-01-01",  # First day of month
        "category": "Food",
        "allocated_amount": 50000.0,
        "recommended_amount": 40000.0
    }


@pytest.fixture
def sample_expense_data() -> dict:
    """Generate sample expense creation data."""
    return {
        "amount": 5000.0,
        "category": "Food",
        "description": "Grocery shopping",
        "date": "2025-01-15",
        "payment_method": "Credit Card"
    }


@pytest.fixture
def sample_goal_data() -> dict:
    """Generate sample goal creation data."""
    return {
        "title": "Emergency Fund",
        "description": "Build 6 months emergency fund",
        "target_amount": 500000.0,
        "current_amount": 0.0,
        "deadline": "2025-12-31",
        "category": "Emergency Fund"
    }


@pytest.fixture
def sample_notification_data() -> dict:
    """Generate sample notification creation data."""
    return {
        "title": "Budget Alert",
        "message": "You have exceeded your budget",
        "notification_type": "budget_alert",
        "is_read": False
    }


# ============== MODEL FACTORY FIXTURES ==============

@pytest.fixture
def create_loan(test_data_db: Session, test_user: User):
    """Factory fixture for creating test loans."""
    def _create_loan(
        principal_amount: float = 500000.0,
        interest_rate: float = 8.5,
        tenure_months: int = 120,
        loan_type: str = "Home Loan",
        lender: str = "HDFC Bank",
        is_active: bool = True
    ) -> Loan:
        loan = Loan(
            id=uuid.uuid4(),
            user_id=test_user.id,
            principal_amount=Decimal(str(principal_amount)),
            outstanding_balance=Decimal(str(principal_amount)),
            interest_rate=Decimal(str(interest_rate)),
            loan_term_months=tenure_months,
            emi_amount=Decimal("6050.00"),
            remaining_months=tenure_months,
            start_date=datetime.utcnow().date(),
            next_due_date=datetime.utcnow().date().replace(day=1) + timedelta(days=32),
            status="active" if is_active else "closed",
            loan_type=loan_type,
            lender_name=lender,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        test_data_db.add(loan)
        test_data_db.commit()
        test_data_db.refresh(loan)
        return loan
    
    return _create_loan


@pytest.fixture
def create_expense(test_data_db: Session, test_user: User):
    """Factory fixture for creating test expenses."""
    def _create_expense(
        amount: float = 5000.0,
        category: str = "Food",
        description: str = "Test expense",
        payment_method: str = "Cash"
    ) -> Expense:
        expense = Expense(
            id=uuid.uuid4(),
            user_id=test_user.id,
            amount=Decimal(str(amount)),
            category=category,
            description=description,
            date=datetime.utcnow().date(),
            payment_method=payment_method,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        test_data_db.add(expense)
        test_data_db.commit()
        test_data_db.refresh(expense)
        return expense
    
    return _create_expense


@pytest.fixture
def create_budget(test_data_db: Session, test_user: User):
    """Factory fixture for creating test budgets."""
    def _create_budget(
        category: str = "Food",
        allocated_amount: float = 50000.0,
        month: Optional[date] = None,
        spent_amount: float = 0.0
    ) -> Budget:
        if month is None:
            month = datetime.utcnow().date().replace(day=1)  # First day of current month
        
        budget = Budget(
            id=uuid.uuid4(),
            user_id=test_user.id,
            month=month,
            category=category,
            allocated_amount=Decimal(str(allocated_amount)),
            spent_amount=Decimal(str(spent_amount)),
            recommended_amount=Decimal(str(allocated_amount * 0.8))  # Example recommendation
        )
        test_data_db.add(budget)
        test_data_db.commit()
        test_data_db.refresh(budget)
        return budget
    
    return _create_budget


@pytest.fixture
def create_goal(test_data_db: Session, test_user: User):
    """Factory fixture for creating test goals."""
    def _create_goal(
        title: str = "Test Goal",
        target_amount: float = 500000.0,
        current_amount: float = 0.0,
        category: str = "Emergency Fund"
    ) -> Goal:
        goal = Goal(
            id=uuid.uuid4(),
            user_id=test_user.id,
            title=title,
            description="Test goal description",
            target_amount=Decimal(str(target_amount)),
            current_amount=Decimal(str(current_amount)),
            deadline=(datetime.utcnow() + timedelta(days=365)).date(),
            category=category,
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        test_data_db.add(goal)
        test_data_db.commit()
        test_data_db.refresh(goal)
        return goal
    
    return _create_goal


# ============== PYTEST CONFIGURATION ==============

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "auth: mark test as related to authentication"
    )


@pytest.fixture(autouse=True)
def cleanup_dependency_overrides():
    """
    Automatically cleanup dependency overrides after each test.
    
    This ensures that dependency overrides don't leak between tests.
    """
    yield
    app.dependency_overrides.clear()


# ============== ASYNC INTEGRATION FIXTURES ==============

@pytest.fixture
async def async_data_engine():
    """Create async database engine for testing."""
    from httpx import ASGITransport
    
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        pool_pre_ping=True,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(DataBase.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(DataBase.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def async_session_local(async_data_engine):
    """Create async session factory."""
    TestingSessionLocal = async_sessionmaker(
        async_data_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return TestingSessionLocal


@pytest.fixture
async def db_session(async_session_local):
    """Provide async database session for tests."""
    async with async_session_local() as session:
        yield session


@pytest.fixture
async def test_async_user():
    """Create test user for async tests."""
    return User(
        id=uuid.uuid4(),
        email="async_test@example.com",
        password_hash="hashed_password",
        is_active=True,
        is_verified=True,
    )


@pytest.fixture
async def auth_headers(test_async_user: User) -> dict:
    """Generate authorization headers with valid JWT token."""
    expires = datetime.utcnow() + timedelta(hours=1)
    to_encode = {
        "sub": str(test_async_user.id),
        "exp": expires,
        "type": "access"
    }
    jwt_token = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture
async def async_client(async_session_local, test_async_user, auth_headers):
    """Create async HTTP client with authentication and DB overrides."""
    from httpx import ASGITransport
    
    # Create async session
    async with async_session_local() as session:
        # Override dependencies
        async def override_get_current_user():
            return test_async_user
        
        async def override_get_data_db():
            yield session
        
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_data_db] = override_get_data_db
        
        # Create async HTTP client
        async with httpx.AsyncClient(
            base_url="http://test",
            headers=auth_headers,
            transport=ASGITransport(app=app)
        ) as client:
            yield client
        
        # Cleanup
        app.dependency_overrides.clear()


# ============== ASYNC MODEL FIXTURES ==============

@pytest.fixture
async def test_loan_fixture(db_session: AsyncSession, test_async_user: User):
    """Create a test loan for async tests."""
    from app.db.models.data import Loan
    
    loan = Loan(
        id=uuid.uuid4(),
        user_id=test_async_user.id,
        principal_amount=Decimal("500000.00"),
        outstanding_balance=Decimal("500000.00"),
        interest_rate=Decimal("8.5"),
        loan_term_months=120,
        emi_amount=Decimal("6050.00"),
        remaining_months=120,
        start_date=datetime.utcnow().date(),
        next_due_date=datetime.utcnow().date().replace(day=1) + timedelta(days=32),
        status="active",
        loan_type="Home Loan",
        lender_name="HDFC Bank",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(loan)
    await db_session.commit()
    await db_session.refresh(loan)
    return loan


@pytest.fixture
async def test_expense_fixture(db_session: AsyncSession, test_async_user: User):
    """Create a test expense for async tests."""
    from app.db.models.data import Expense
    
    expense = Expense(
        id=uuid.uuid4(),
        user_id=test_async_user.id,
        amount=Decimal("500.00"),
        category="Food",
        description="Test grocery shopping",
        date=datetime.utcnow().date(),
        payment_method="Cash",
        created_at=datetime.utcnow()
    )
    db_session.add(expense)
    await db_session.commit()
    await db_session.refresh(expense)
    return expense


@pytest.fixture
async def test_budget_fixture(db_session: AsyncSession, test_async_user: User):
    """Create a test budget for async tests."""
    from app.db.models.data import Budget
    
    budget = Budget(
        id=uuid.uuid4(),
        user_id=test_async_user.id,
        month=datetime.utcnow().date().replace(day=1),
        category="Food",
        allocated_amount=Decimal("10000.00"),
        spent_amount=Decimal("0.00"),
        recommended_amount=Decimal("8000.00")
    )
    db_session.add(budget)
    await db_session.commit()
    await db_session.refresh(budget)
    return budget


@pytest.fixture
async def test_goal_fixture(db_session: AsyncSession, test_async_user: User):
    """Create a test goal for async tests."""
    from app.db.models.data import Goal
    
    goal = Goal(
        id=uuid.uuid4(),
        user_id=test_async_user.id,
        goal_name="Test Goal",
        description="Test goal description",
        target_amount=Decimal("50000.00"),
        current_amount=Decimal("0.00"),
        target_date=(datetime.utcnow() + timedelta(days=365)).date(),
        goal_type="savings",
        status="active",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(goal)
    await db_session.commit()
    await db_session.refresh(goal)
    return goal


@pytest.fixture
async def test_notification_fixture(db_session: AsyncSession, test_async_user: User):
    """Create a test notification for async tests."""
    from app.db.models.data import Notification
    
    notification = Notification(
        id=uuid.uuid4(),
        user_id=test_async_user.id,
        title="Test Notification",
        message="This is a test notification",
        notification_type="budget_alert",
        is_read=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(notification)
    await db_session.commit()
    await db_session.refresh(notification)
    return notification


@pytest.fixture
async def test_user_profile_fixture(db_session: AsyncSession, test_async_user: User):
    """Create a test financial profile for async tests."""
    from app.db.models.data import UserFinancialProfile
    
    profile = UserFinancialProfile(
        user_id=test_async_user.id,
        monthly_salary=Decimal("50000.00"),
        total_emi=Decimal("15000.00"),
        rent=Decimal("10000.00"),
        insurance=Decimal("2000.00"),
        subscriptions=Decimal("500.00"),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return profile
