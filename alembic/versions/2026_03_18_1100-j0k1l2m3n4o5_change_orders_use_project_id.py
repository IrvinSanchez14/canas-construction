"""Change orders: replace budget_id with project_id

Revision ID: j0k1l2m3n4o5
Revises: i9j0k1l2m3n4
Create Date: 2026-03-18 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'j0k1l2m3n4o5'
down_revision: Union[str, None] = 'i9j0k1l2m3n4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add project_id column
    op.add_column('change_orders',
        sa.Column('project_id', UUID(as_uuid=True), nullable=True)
    )

    # Drop old budget_id FK and column
    op.drop_constraint('change_orders_budget_id_fkey', 'change_orders', type_='foreignkey')
    op.drop_index('ix_change_orders_budget_id', table_name='change_orders')
    op.drop_column('change_orders', 'budget_id')

    # Make project_id NOT NULL and add FK
    op.alter_column('change_orders', 'project_id', nullable=False)
    op.create_foreign_key(
        'change_orders_project_id_fkey',
        'change_orders', 'projects',
        ['project_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index('ix_change_orders_project_id', 'change_orders', ['project_id'])


def downgrade() -> None:
    # Reverse: drop project_id, add budget_id back
    op.drop_constraint('change_orders_project_id_fkey', 'change_orders', type_='foreignkey')
    op.drop_index('ix_change_orders_project_id', table_name='change_orders')
    op.drop_column('change_orders', 'project_id')

    op.add_column('change_orders',
        sa.Column('budget_id', UUID(as_uuid=True), nullable=False)
    )
    op.create_foreign_key(
        'change_orders_budget_id_fkey',
        'change_orders', 'budgets',
        ['budget_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index('ix_change_orders_budget_id', 'change_orders', ['budget_id'])
