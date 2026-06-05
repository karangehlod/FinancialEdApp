"""User profile repository implementation."""

from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.repositories.interfaces import IUserProfileRepository
from app.db.models.data import UserProfile
from app.schemas.user_profile import UserProfileCreate, UserProfileUpdate


class UserProfileRepository(IUserProfileRepository):
    """Concrete implementation of user profile repository."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_profile(self, user_id: UUID, profile_data: Optional[UserProfileCreate] = None) -> UserProfile:
        """Create a user profile."""
        new_profile = UserProfile(
            user_id=user_id,
            name=profile_data.name if profile_data else None,
            country=profile_data.country if profile_data else 'IN',
            currency=profile_data.currency if profile_data else 'INR',
            knowledge_level=profile_data.knowledge_level if profile_data else None,
            risk_tolerance=profile_data.risk_tolerance if profile_data else None,
            consent_given=profile_data.consent_given if profile_data else False,
            consent_timestamp=datetime.now(timezone.utc) if profile_data and profile_data.consent_given else None
        )
        
        self.db.add(new_profile)
        await self.db.commit()
        await self.db.refresh(new_profile)
        return new_profile
    
    async def get_profile_by_user_id(self, user_id: UUID) -> Optional[UserProfile]:
        """Get user profile by user ID."""
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def update_profile(self, user_id: UUID, profile_data: UserProfileUpdate) -> Optional[UserProfile]:
        """Update user profile."""
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        
        if not profile:
            return None
        
        # Update fields
        for field, value in profile_data.model_dump(exclude_unset=True).items():
            if hasattr(profile, field):
                setattr(profile, field, value)
        
        await self.db.commit()
        await self.db.refresh(profile)
        return profile
    
    async def delete_profile(self, user_id: UUID) -> bool:
        """Delete user profile."""
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        
        if profile:
            await self.db.delete(profile)  # ✅ Add await
            await self.db.flush()          # ✅ Add flush
            await self.db.commit()
            return True
        return False
