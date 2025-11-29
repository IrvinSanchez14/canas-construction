"""Add created_by_user_id to projects table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2025-11-29 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add created_by_user_id column to projects table
    op.add_column('projects',
        sa.Column('created_by_user_id', sa.UUID(), nullable=True)
    )

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_projects_created_by_user_id',
        'projects',
        'users',
        ['created_by_user_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Add index for performance
    op.create_index(
        op.f('ix_projects_created_by_user_id'),
        'projects',
        ['created_by_user_id'],
        unique=False
    )


def downgrade() -> None:
    # Drop index
    op.drop_index(op.f('ix_projects_created_by_user_id'), table_name='projects')

    # Drop foreign key constraint
    op.drop_constraint('fk_projects_created_by_user_id', 'projects', type_='foreignkey')

    # Drop column
    op.drop_column('projects', 'created_by_user_id')
