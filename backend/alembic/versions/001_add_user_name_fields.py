"""Add first_name and last_name to user_profiles

Revision ID: 001_add_user_name_fields
Revises: 
Create Date: 2026-01-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_add_user_name_fields'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add first_name and last_name columns to user_profiles table."""
    op.add_column('user_profiles', sa.Column('first_name', sa.String(255), nullable=True))
    op.add_column('user_profiles', sa.Column('last_name', sa.String(255), nullable=True))


def downgrade() -> None:
    """Remove first_name and last_name columns from user_profiles table."""
    op.drop_column('user_profiles', 'last_name')
    op.drop_column('user_profiles', 'first_name')
