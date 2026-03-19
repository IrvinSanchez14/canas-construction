"""Add change orders table for mid-project modifications

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
Create Date: 2026-03-18 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'i9j0k1l2m3n4'
down_revision: Union[str, None] = 'h8i9j0k1l2m3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Change Orders table
    op.create_table(
        'change_orders',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(255), nullable=False, index=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('observations', sa.JSON(), nullable=True),
        sa.Column('order_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column(
            'status',
            sa.Enum('draft', 'pending_approval', 'accepted', 'rejected', 'applied',
                    name='changeorderstatus'),
            nullable=False,
            server_default='draft',
            index=True
        ),
        sa.Column('total_amount', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('budget_id', UUID(as_uuid=True),
                  sa.ForeignKey('budgets.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('accepted_by_user_id', UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'),
                  nullable=True, index=True),
        sa.Column('accepted_at', sa.DateTime(), nullable=True),
        sa.Column('applied_by_user_id', UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'),
                  nullable=True, index=True),
        sa.Column('applied_at', sa.DateTime(), nullable=True),
        sa.Column('created_by_user_id', UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'),
                  nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )

    # Change Order Items table
    op.create_table(
        'change_order_items',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('item_code', sa.String(20), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('unit', sa.String(50), nullable=True),
        sa.Column('quantity', sa.Numeric(10, 2), nullable=False),
        sa.Column('unit_price', sa.Numeric(12, 2), nullable=False),
        sa.Column('subtotal', sa.Numeric(12, 2), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('change_order_id', UUID(as_uuid=True),
                  sa.ForeignKey('change_orders.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )


def downgrade() -> None:
    op.drop_table('change_order_items')
    op.drop_table('change_orders')
    op.execute("DROP TYPE IF EXISTS changeorderstatus")
