"""User repository implementation."""

from typing import Optional, Union
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.repositories.interfaces import IUserRepository
from app.db.models.auth import User
from app.schemas.auth import UserCreate
from app.utils.security import get_password_hash


class UserRepository(IUserRepository):
    """Concrete implementation of user repository."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        normalized_email = user_data.email.lower()
        hashed_password = get_password_hash(user_data.password)
        
        new_user = User(
            email=normalized_email,
            password_hash=hashed_password,
            is_active=True,
            is_verified=False
        )
        
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)
        return new_user
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        normalized_email = email.lower()
        result = await self.db.execute(
            select(User).where(User.email == normalized_email)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_id(self, user_id: Union[str, UUID]) -> Optional[User]:
        """Get user by ID."""
        if isinstance(user_id, str):
            try:
                user_id = UUID(user_id)
            except ValueError:
                return None
        
        result = await self.db.execute(
            select(User).filter(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def update_last_login(self, user_id: UUID) -> None:
        """Update user's last login timestamp."""
        result = await self.db.execute(
            select(User).filter(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            user.last_login = datetime.utcnow()
            await self.db.commit()
    
    async def delete_user(self, user_id: UUID) -> bool:
        """Delete a user."""
        result = await self.db.execute(
            select(User).filter(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            await self.db.delete(user)
            await self.db.commit()
            return True
        return False

    async def update_password(self, user_id: UUID, new_password_hash: str) -> bool:
        """Update user password hash."""
        result = await self.db.execute(
            select(User).filter(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            user.password_hash = new_password_hash
            user.updated_at = datetime.utcnow()
            await self.db.commit()
            return True
        return False

    async def create_oauth_user(
        self,
        email: str,
        display_name: Optional[str] = None,
    ) -> User:
        """
        Create a new user account for an OAuth / social login sign-up.

        OAuth users have no local password (password_hash = None).
        Email is pre-verified because the identity provider has already
        verified it on their side.

        P2-6: OAuth / Social Login
        """
        normalized_email = email.lower()
        new_user = User(
            email=normalized_email,
            password_hash=None,   # OAuth-only — no local password
            is_active=True,
            is_verified=True,     # provider has already verified the email
        )
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)
        return new_user
