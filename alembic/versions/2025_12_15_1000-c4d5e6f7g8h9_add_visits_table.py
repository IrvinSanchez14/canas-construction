"""Add visits table for project visits and information gathering

Revision ID: c4d5e6f7g8h9
Revises: c3d4e5f6a7b8
Create Date: 2025-12-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c4d5e6f7g8h9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if visitstatus enum already exists
    connection = op.get_bind()
    
    # Query to check if enum exists
    enum_check = connection.execute(sa.text(
        "SELECT EXISTS(SELECT 1 FROM pg_type WHERE typname = 'visitstatus')"
    )).scalar()
    
    # Only create enum if it doesn't exist
    if not enum_check:
        visitstatus_enum = postgresql.ENUM(
            'planning', 'in_review', 'approved', 'inspection_required', 'visited',
            name='visitstatus'
        )
        visitstatus_enum.create(connection)
    
    # Check if visits table exists
    inspector = sa.inspect(connection)
    
    if not inspector.has_table('visits'):
        # Create visits table using VARCHAR for status (will be cast to enum after)
        op.create_table('visits',
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('status', sa.VARCHAR(50), nullable=False),  # Use VARCHAR temporarily
            sa.Column('visit_date', sa.Date(), nullable=True),
            sa.Column('inspection_notes', sa.Text(), nullable=True),
            sa.Column('estimated_materials_cost', sa.Numeric(precision=12, scale=2), nullable=True),
            sa.Column('estimated_labor_cost', sa.Numeric(precision=12, scale=2), nullable=True),
            sa.Column('estimated_total_cost', sa.Numeric(precision=12, scale=2), nullable=True),
            sa.Column('images', postgresql.JSON(), nullable=True),
            sa.Column('attachments', postgresql.JSON(), nullable=True),
            sa.Column('visit_items', postgresql.JSON(), nullable=True),
            sa.Column('project_id', sa.UUID(), nullable=False),
            sa.Column('created_by_user_id', sa.UUID(), nullable=True),
            sa.Column('edited_by_user_id', sa.UUID(), nullable=True),
            sa.Column('reviewed_at', sa.DateTime(), nullable=True),
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['edited_by_user_id'], ['users.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Now convert the status column to use the enum type
        op.execute(sa.text("""
            ALTER TABLE visits 
            ALTER COLUMN status TYPE visitstatus USING status::visitstatus
        """))
        
        # Set default value
        op.execute(sa.text("""
            ALTER TABLE visits 
            ALTER COLUMN status SET DEFAULT 'planning'::visitstatus
        """))
        
        # Create indexes for performance
        op.create_index(op.f('ix_visits_id'), 'visits', ['id'], unique=False)
        op.create_index(op.f('ix_visits_title'), 'visits', ['title'], unique=False)
        op.create_index(op.f('ix_visits_status'), 'visits', ['status'], unique=False)
        op.create_index(op.f('ix_visits_project_id'), 'visits', ['project_id'], unique=False)
        op.create_index(op.f('ix_visits_created_by_user_id'), 'visits', ['created_by_user_id'], unique=False)
        op.create_index(op.f('ix_visits_edited_by_user_id'), 'visits', ['edited_by_user_id'], unique=False)


def downgrade() -> None:
    # Check if visits table exists before dropping
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    if inspector.has_table('visits'):
        # Drop indexes
        op.drop_index(op.f('ix_visits_edited_by_user_id'), table_name='visits')
        op.drop_index(op.f('ix_visits_created_by_user_id'), table_name='visits')
        op.drop_index(op.f('ix_visits_project_id'), table_name='visits')
        op.drop_index(op.f('ix_visits_status'), table_name='visits')
        op.drop_index(op.f('ix_visits_title'), table_name='visits')
        op.drop_index(op.f('ix_visits_id'), table_name='visits')
        
        # Drop table
        op.drop_table('visits')
    
    # Drop enum with IF EXISTS to avoid errors
    connection.execute(sa.text("DROP TYPE IF EXISTS visitstatus CASCADE"))
