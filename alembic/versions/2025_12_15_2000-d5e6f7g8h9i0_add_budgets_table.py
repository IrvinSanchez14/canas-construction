"""Add budgets and budget_items tables for project cost breakdowns

Revision ID: d5e6f7g8h9i0
Revises: c4d5e6f7g8h9
Create Date: 2025-12-15 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd5e6f7g8h9i0'
down_revision: Union[str, None] = 'c4d5e6f7g8h9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if budgetstatus enum already exists
    connection = op.get_bind()
    
    # Query to check if enum exists
    enum_check = connection.execute(sa.text(
        "SELECT EXISTS(SELECT 1 FROM pg_type WHERE typname = 'budgetstatus')"
    )).scalar()
    
    # Only create enum if it doesn't exist
    if not enum_check:
        budgetstatus_enum = postgresql.ENUM(
            'draft', 'pending_approval', 'accepted', 'rejected', 'revised',
            name='budgetstatus'
        )
        budgetstatus_enum.create(connection)
    
    # Check if budgets table exists
    inspector = sa.inspect(connection)
    
    if not inspector.has_table('budgets'):
        # Create budgets table
        op.create_table('budgets',
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('status', sa.VARCHAR(50), nullable=False),  # Use VARCHAR temporarily
            sa.Column('total_amount', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
            sa.Column('visit_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('accepted_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('accepted_at', sa.DateTime(), nullable=True),
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['visit_id'], ['visits.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['accepted_by_user_id'], ['users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('visit_id', name='uq_budgets_visit_id')
        )
        
        # Create indexes
        op.create_index(op.f('ix_budgets_id'), 'budgets', ['id'], unique=False)
        op.create_index(op.f('ix_budgets_title'), 'budgets', ['title'], unique=False)
        op.create_index(op.f('ix_budgets_status'), 'budgets', ['status'], unique=False)
        op.create_index(op.f('ix_budgets_visit_id'), 'budgets', ['visit_id'], unique=True)
        op.create_index(op.f('ix_budgets_accepted_by_user_id'), 'budgets', ['accepted_by_user_id'], unique=False)
        
        # Now convert the status column to use the enum type
        op.execute(sa.text("""
            ALTER TABLE budgets 
            ALTER COLUMN status TYPE budgetstatus USING status::budgetstatus
        """))
        
        # Set default value
        op.execute(sa.text("""
            ALTER TABLE budgets 
            ALTER COLUMN status SET DEFAULT 'draft'::budgetstatus
        """))
    
    # Check if budget_items table exists
    if not inspector.has_table('budget_items'):
        # Create budget_items table
        op.create_table('budget_items',
            sa.Column('section_name', sa.String(length=255), nullable=True),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('unit', sa.String(length=50), nullable=True),
            sa.Column('quantity', sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=False),
            sa.Column('subtotal', sa.Numeric(precision=12, scale=2), nullable=False),
            sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('catalog_item_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('budget_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['budget_id'], ['budgets.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['catalog_item_id'], ['catalog_items.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Create indexes
        op.create_index(op.f('ix_budget_items_id'), 'budget_items', ['id'], unique=False)
        op.create_index(op.f('ix_budget_items_budget_id'), 'budget_items', ['budget_id'], unique=False)
        op.create_index(op.f('ix_budget_items_catalog_item_id'), 'budget_items', ['catalog_item_id'], unique=False)
        op.create_index(op.f('ix_budget_items_section_name'), 'budget_items', ['section_name'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_budget_items_section_name'), table_name='budget_items')
    op.drop_index(op.f('ix_budget_items_catalog_item_id'), table_name='budget_items')
    op.drop_index(op.f('ix_budget_items_budget_id'), table_name='budget_items')
    op.drop_index(op.f('ix_budget_items_id'), table_name='budget_items')
    
    # Drop budget_items table
    op.drop_table('budget_items')
    
    # Drop indexes for budgets
    op.drop_index(op.f('ix_budgets_accepted_by_user_id'), table_name='budgets')
    op.drop_index(op.f('ix_budgets_visit_id'), table_name='budgets')
    op.drop_index(op.f('ix_budgets_status'), table_name='budgets')
    op.drop_index(op.f('ix_budgets_title'), table_name='budgets')
    op.drop_index(op.f('ix_budgets_id'), table_name='budgets')
    
    # Drop budgets table
    op.drop_table('budgets')
    
    # Drop enum with IF EXISTS to avoid errors
    connection = op.get_bind()
    connection.execute(sa.text("DROP TYPE IF EXISTS budgetstatus CASCADE"))
