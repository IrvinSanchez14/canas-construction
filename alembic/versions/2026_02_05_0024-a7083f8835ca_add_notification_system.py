"""add_notification_system

Revision ID: a7083f8835ca
Revises: f7g8h9i0j1k2
Create Date: 2026-02-05 00:24:10.612412+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7083f8835ca'
down_revision: Union[str, None] = 'f7g8h9i0j1k2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create notification_settings table
    op.create_table(
        'notification_settings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', name='uq_notification_settings_company_id')
    )
    op.create_index('ix_notification_settings_company_id', 'notification_settings', ['company_id'])
    
    # Create notification_recipients table
    op.create_table(
        'notification_recipients',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('notification_setting_id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['notification_setting_id'], ['notification_settings.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_notification_recipients_setting_id', 'notification_recipients', ['notification_setting_id'])
    op.create_index('ix_notification_recipients_email', 'notification_recipients', ['email'])


def downgrade() -> None:
    op.drop_index('ix_notification_recipients_email', table_name='notification_recipients')
    op.drop_index('ix_notification_recipients_setting_id', table_name='notification_recipients')
    op.drop_table('notification_recipients')
    
    op.drop_index('ix_notification_settings_company_id', table_name='notification_settings')
    op.drop_table('notification_settings')
