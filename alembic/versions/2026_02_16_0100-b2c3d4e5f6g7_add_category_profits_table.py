"""add_category_profits_table

Internal cost breakdown table for budget categories.
Tracks provider price, delivery cost, profit percentage, and calculated total price.

Revision ID: b2c3d4e5f6g7
Revises: 570b36ddb6db
Create Date: 2026-02-16 01:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, None] = '570b36ddb6db'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('category_profits',
        sa.Column('budget_category_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('provider_price', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
        sa.Column('delivery_cost', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
        sa.Column('profit_percentage', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0'),
        sa.Column('total_price', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['budget_category_id'], ['budget_categories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_category_profits_id'), 'category_profits', ['id'], unique=False)
    op.create_index(op.f('ix_category_profits_budget_category_id'), 'category_profits', ['budget_category_id'], unique=True)
    op.create_index(op.f('ix_category_profits_created_by_user_id'), 'category_profits', ['created_by_user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_category_profits_created_by_user_id'), table_name='category_profits')
    op.drop_index(op.f('ix_category_profits_budget_category_id'), table_name='category_profits')
    op.drop_index(op.f('ix_category_profits_id'), table_name='category_profits')
    op.drop_table('category_profits')
