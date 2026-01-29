"""Add expiration_date and notes columns to renderings table

Revision ID: f7g8h9i0j1k2
Revises: e6f7g8h9i0j1
Create Date: 2025-01-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f7g8h9i0j1k2'
down_revision: Union[str, None] = 'e6f7g8h9i0j1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add expiration_date column to renderings table
    op.add_column('renderings', sa.Column('expiration_date', sa.Date(), nullable=True))

    # Add notes column to renderings table
    op.add_column('renderings', sa.Column('notes', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove notes column from renderings table
    op.drop_column('renderings', 'notes')

    # Remove expiration_date column from renderings table
    op.drop_column('renderings', 'expiration_date')
