"""Add rendering item display and pricing fields

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-02-18 12:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5f6g7h8i9'
down_revision: Union[str, None] = 'c3d4e5f6g7h8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('rendering_items', sa.Column('tax', sa.Numeric(12, 2), nullable=True))
    op.add_column('rendering_items', sa.Column('disclaimer', sa.Text(), nullable=True))
    op.add_column('rendering_items', sa.Column('material_image_url', sa.String(500), nullable=True))
    op.add_column('rendering_items', sa.Column('product_image_url', sa.String(500), nullable=True))
    op.add_column('rendering_items', sa.Column('is_material_sample', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('rendering_items', sa.Column('show_in_materials_page', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('rendering_items', sa.Column('show_in_details_page', sa.Boolean(), nullable=False, server_default='true'))


def downgrade() -> None:
    op.drop_column('rendering_items', 'show_in_details_page')
    op.drop_column('rendering_items', 'show_in_materials_page')
    op.drop_column('rendering_items', 'is_material_sample')
    op.drop_column('rendering_items', 'product_image_url')
    op.drop_column('rendering_items', 'material_image_url')
    op.drop_column('rendering_items', 'disclaimer')
    op.drop_column('rendering_items', 'tax')
