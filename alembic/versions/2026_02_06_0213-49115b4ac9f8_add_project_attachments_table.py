"""add_project_attachments_table

Revision ID: 49115b4ac9f8
Revises: d3f8fb70d5cd
Create Date: 2026-02-06 02:13:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '49115b4ac9f8'
down_revision: Union[str, None] = 'd3f8fb70d5cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create project_attachments table
    op.create_table(
        'project_attachments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False, comment='Original filename'),
        sa.Column('file_url', sa.String(length=1000), nullable=False, comment='R2 storage URL'),
        sa.Column('file_type', sa.String(length=50), nullable=False, comment='MIME type (image/jpeg, application/pdf, etc.)'),
        sa.Column('file_size', sa.Integer(), nullable=False, comment='File size in bytes'),
        sa.Column('description', sa.Text(), nullable=True, comment='Optional user description'),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Project this attachment belongs to'),
        sa.Column('uploaded_by_user_id', postgresql.UUID(as_uuid=True), nullable=True, comment='User who uploaded this attachment'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_project_attachments_project_id'), 'project_attachments', ['project_id'], unique=False)
    op.create_index(op.f('ix_project_attachments_uploaded_by_user_id'), 'project_attachments', ['uploaded_by_user_id'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_project_attachments_uploaded_by_user_id'), table_name='project_attachments')
    op.drop_index(op.f('ix_project_attachments_project_id'), table_name='project_attachments')
    
    # Drop table
    op.drop_table('project_attachments')
