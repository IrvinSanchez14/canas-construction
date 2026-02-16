"""remove_project_budget_and_completion_fields

Revision ID: d3f8fb70d5cd
Revises: a7083f8835ca
Create Date: 2026-02-05 02:37:42.693438+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3f8fb70d5cd'
down_revision: Union[str, None] = 'a7083f8835ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove budget and completion date columns from projects table
    op.drop_column('projects', 'estimated_budget')
    op.drop_column('projects', 'actual_cost')
    op.drop_column('projects', 'estimated_completion_date')
    op.drop_column('projects', 'actual_completion_date')


def downgrade() -> None:
    # Add back the columns if we need to rollback
    op.add_column('projects', sa.Column('actual_completion_date', sa.Date(), nullable=True))
    op.add_column('projects', sa.Column('estimated_completion_date', sa.Date(), nullable=True))
    op.add_column('projects', sa.Column('actual_cost', sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column('projects', sa.Column('estimated_budget', sa.Numeric(precision=12, scale=2), nullable=True))
