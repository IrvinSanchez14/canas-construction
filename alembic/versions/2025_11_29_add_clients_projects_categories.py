"""Add clients, projects, and categories tables

Revision ID: a1b2c3d4e5f6
Revises: 0e31217333b8
Create Date: 2025-11-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '0e31217333b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create clients table
    op.create_table('clients',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_clients_id'), 'clients', ['id'], unique=False)
    op.create_index(op.f('ix_clients_name'), 'clients', ['name'], unique=False)
    op.create_index(op.f('ix_clients_company_id'), 'clients', ['company_id'], unique=False)

    # Create project_categories table
    op.create_table('project_categories',
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_project_categories_id'), 'project_categories', ['id'], unique=False)
    op.create_index(op.f('ix_project_categories_name'), 'project_categories', ['name'], unique=False)
    op.create_index(op.f('ix_project_categories_company_id'), 'project_categories', ['company_id'], unique=False)

    # Create projects table
    op.create_table('projects',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('LEAD', 'QUOTED', 'APPROVED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'ON_HOLD', name='projectstatus'), nullable=False),
        sa.Column('estimated_budget', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('actual_cost', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('estimated_completion_date', sa.Date(), nullable=True),
        sa.Column('actual_completion_date', sa.Date(), nullable=True),
        sa.Column('address', sa.String(length=500), nullable=True),
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('category_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['project_categories.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_projects_id'), 'projects', ['id'], unique=False)
    op.create_index(op.f('ix_projects_name'), 'projects', ['name'], unique=False)
    op.create_index(op.f('ix_projects_status'), 'projects', ['status'], unique=False)
    op.create_index(op.f('ix_projects_client_id'), 'projects', ['client_id'], unique=False)
    op.create_index(op.f('ix_projects_category_id'), 'projects', ['category_id'], unique=False)


def downgrade() -> None:
    # Drop projects table and indexes
    op.drop_index(op.f('ix_projects_category_id'), table_name='projects')
    op.drop_index(op.f('ix_projects_client_id'), table_name='projects')
    op.drop_index(op.f('ix_projects_status'), table_name='projects')
    op.drop_index(op.f('ix_projects_name'), table_name='projects')
    op.drop_index(op.f('ix_projects_id'), table_name='projects')
    op.drop_table('projects')

    # Drop enum type
    op.execute('DROP TYPE projectstatus')

    # Drop project_categories table and indexes
    op.drop_index(op.f('ix_project_categories_company_id'), table_name='project_categories')
    op.drop_index(op.f('ix_project_categories_name'), table_name='project_categories')
    op.drop_index(op.f('ix_project_categories_id'), table_name='project_categories')
    op.drop_table('project_categories')

    # Drop clients table and indexes
    op.drop_index(op.f('ix_clients_company_id'), table_name='clients')
    op.drop_index(op.f('ix_clients_name'), table_name='clients')
    op.drop_index(op.f('ix_clients_id'), table_name='clients')
    op.drop_table('clients')
