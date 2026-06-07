"""Financial profile repository implementation."""

from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.db.models.data import UserFinancialProfile
from app.schemas.financial_profile import FinancialProfileCreate, FinancialProfileUpdate


class FinancialProfileRepository:
    """Repository for managing user financial profiles."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_profile(self, user_id: UUID, profile_data: Optional[FinancialProfileCreate] = None) -> UserFinancialProfile:
        """Create a financial profile."""
        new_profile = UserFinancialProfile(
            user_id=user_id,
            monthly_salary=profile_data.monthly_salary if profile_data else None,
            currency=profile_data.currency if profile_data else 'INR',
            total_emi=profile_data.total_emi if profile_data else None,
            rent=profile_data.rent if profile_data else None,
            insurance=profile_data.insurance if profile_data else None,
            subscriptions=profile_data.subscriptions if profile_data else None,
        )
        
        self.db.add(new_profile)
        await self.db.commit()
        await self.db.refresh(new_profile)
        return new_profile
    
    async def get_profile_by_user_id(self, user_id: UUID) -> Optional[UserFinancialProfile]:
        """Get financial profile by user ID."""
        result = await self.db.execute(
            select(UserFinancialProfile).where(UserFinancialProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def update_profile(self, user_id: UUID, profile_data: FinancialProfileUpdate) -> Optional[UserFinancialProfile]:
        """Update financial profile or create if it doesn't exist."""
        result = await self.db.execute(
            select(UserFinancialProfile).where(UserFinancialProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        
        # If profile doesn't exist, create it
        if not profile:
            profile = UserFinancialProfile(
                user_id=user_id,
                currency='USD',  # Default currency
            )
            self.db.add(profile)
        
        # Update fields
        for field, value in profile_data.model_dump(exclude_unset=True).items():
            if hasattr(profile, field):
                setattr(profile, field, value)
        
        profile.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(profile)
        return profile
    
    async def delete_profile(self, user_id: UUID) -> bool:
        """Delete financial profile."""
        result = await self.db.execute(
            select(UserFinancialProfile).where(UserFinancialProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        
        if profile:
            await self.db.delete(profile)
            await self.db.commit()
            return True
        return False
