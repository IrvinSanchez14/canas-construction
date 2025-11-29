"""Add catalog_items table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2025-11-29 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create catalog_items table
    op.create_table('catalog_items',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('unity', sa.Enum('POUND', 'SQUARE_FOOT', 'FOOT', 'CUBIC_YARD', 'EACH', 'HOUR', 'DAY', name='unittype'), nullable=False),
        sa.Column('price_base', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('created_by_user_id', sa.UUID(), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_catalog_items_id'), 'catalog_items', ['id'], unique=False)
    op.create_index(op.f('ix_catalog_items_name'), 'catalog_items', ['name'], unique=False)
    op.create_index(op.f('ix_catalog_items_unity'), 'catalog_items', ['unity'], unique=False)
    op.create_index(op.f('ix_catalog_items_is_active'), 'catalog_items', ['is_active'], unique=False)
    op.create_index(op.f('ix_catalog_items_company_id'), 'catalog_items', ['company_id'], unique=False)
    op.create_index(op.f('ix_catalog_items_created_by_user_id'), 'catalog_items', ['created_by_user_id'], unique=False)


def downgrade() -> None:
    # Drop catalog_items table and indexes
    op.drop_index(op.f('ix_catalog_items_created_by_user_id'), table_name='catalog_items')
    op.drop_index(op.f('ix_catalog_items_company_id'), table_name='catalog_items')
    op.drop_index(op.f('ix_catalog_items_is_active'), table_name='catalog_items')
    op.drop_index(op.f('ix_catalog_items_unity'), table_name='catalog_items')
    op.drop_index(op.f('ix_catalog_items_name'), table_name='catalog_items')
    op.drop_index(op.f('ix_catalog_items_id'), table_name='catalog_items')
    op.drop_table('catalog_items')

    # Drop enum type
    op.execute('DROP TYPE unittype')
