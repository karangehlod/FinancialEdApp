# Import all models here to ensure they are registered with SQLAlchemy
from app.db.models.auth import User, RefreshToken
from app.db.models.data import (
    UserProfile, 
    Expense, 
    Budget, 
    UserFinancialProfile as FinancialProfile,
    BudgetAlert
)

from app.db.session import AuthBase, DataBase

# For convenience, we'll use AuthBase as the primary Base for table creation
# since the startup event will create tables on both engines
Base = AuthBase
