"""add project_id to renderings

Revision ID: g7h8i9j0k1l2
Revises: f6g7h8i9j0k1
Create Date: 2026-02-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'g7h8i9j0k1l2'
down_revision: str = 'f6g7h8i9j0k1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('renderings', sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_renderings_project_id',
        'renderings', 'projects',
        ['project_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('ix_renderings_project_id', 'renderings', ['project_id'])


def downgrade() -> None:
    op.drop_index('ix_renderings_project_id', table_name='renderings')
    op.drop_constraint('fk_renderings_project_id', 'renderings', type_='foreignkey')
    op.drop_column('renderings', 'project_id')
