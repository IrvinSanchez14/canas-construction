"""Add renderings, rendering_images, and rendering_items tables for visual proposals

Revision ID: e6f7g8h9i0j1
Revises: d5e6f7g8h9i0
Create Date: 2025-12-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e6f7g8h9i0j1'
down_revision: Union[str, None] = 'd5e6f7g8h9i0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()

    # Check if renderingstatus enum already exists
    enum_check = connection.execute(sa.text(
        "SELECT EXISTS(SELECT 1 FROM pg_type WHERE typname = 'renderingstatus')"
    )).scalar()

    # Only create enum if it doesn't exist
    if not enum_check:
        renderingstatus_enum = postgresql.ENUM(
            'draft', 'sent', 'approved', 'rejected',
            name='renderingstatus'
        )
        renderingstatus_enum.create(connection)

    inspector = sa.inspect(connection)

    # Create renderings table
    if not inspector.has_table('renderings'):
        op.create_table('renderings',
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('status', sa.VARCHAR(50), nullable=False),
            sa.Column('total_amount', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
            sa.Column('visit_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('budget_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('sent_at', sa.DateTime(), nullable=True),
            sa.Column('sent_to_email', sa.String(length=255), nullable=True),
            sa.Column('approved_at', sa.DateTime(), nullable=True),
            sa.Column('approved_by_client_name', sa.String(length=255), nullable=True),
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['visit_id'], ['visits.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['budget_id'], ['budgets.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )

        # Create indexes for renderings
        op.create_index(op.f('ix_renderings_id'), 'renderings', ['id'], unique=False)
        op.create_index(op.f('ix_renderings_title'), 'renderings', ['title'], unique=False)
        op.create_index(op.f('ix_renderings_status'), 'renderings', ['status'], unique=False)
        op.create_index(op.f('ix_renderings_visit_id'), 'renderings', ['visit_id'], unique=False)
        op.create_index(op.f('ix_renderings_budget_id'), 'renderings', ['budget_id'], unique=False)

        # Convert status column to use enum type
        op.execute(sa.text("""
            ALTER TABLE renderings
            ALTER COLUMN status TYPE renderingstatus USING status::renderingstatus
        """))

        # Set default value
        op.execute(sa.text("""
            ALTER TABLE renderings
            ALTER COLUMN status SET DEFAULT 'draft'::renderingstatus
        """))

    # Create rendering_images table
    if not inspector.has_table('rendering_images'):
        op.create_table('rendering_images',
            sa.Column('image_url', sa.String(length=500), nullable=False),
            sa.Column('title', sa.String(length=255), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('is_full_page', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('image_type', sa.String(length=50), nullable=False, server_default='project'),
            sa.Column('rendering_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['rendering_id'], ['renderings.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )

        # Create indexes for rendering_images
        op.create_index(op.f('ix_rendering_images_id'), 'rendering_images', ['id'], unique=False)
        op.create_index(op.f('ix_rendering_images_rendering_id'), 'rendering_images', ['rendering_id'], unique=False)

    # Create rendering_items table
    if not inspector.has_table('rendering_items'):
        op.create_table('rendering_items',
            sa.Column('category', sa.String(length=255), nullable=True),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('specifications', postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('image_url', sa.String(length=500), nullable=True),
            sa.Column('quantity', sa.Numeric(precision=10, scale=2), nullable=False, server_default='1'),
            sa.Column('unit', sa.String(length=50), nullable=True),
            sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
            sa.Column('subtotal', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
            sa.Column('total', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
            sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('budget_item_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('rendering_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['budget_item_id'], ['budget_items.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['rendering_id'], ['renderings.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )

        # Create indexes for rendering_items
        op.create_index(op.f('ix_rendering_items_id'), 'rendering_items', ['id'], unique=False)
        op.create_index(op.f('ix_rendering_items_rendering_id'), 'rendering_items', ['rendering_id'], unique=False)
        op.create_index(op.f('ix_rendering_items_budget_item_id'), 'rendering_items', ['budget_item_id'], unique=False)
        op.create_index(op.f('ix_rendering_items_category'), 'rendering_items', ['category'], unique=False)


def downgrade() -> None:
    # Drop indexes for rendering_items
    op.drop_index(op.f('ix_rendering_items_category'), table_name='rendering_items')
    op.drop_index(op.f('ix_rendering_items_budget_item_id'), table_name='rendering_items')
    op.drop_index(op.f('ix_rendering_items_rendering_id'), table_name='rendering_items')
    op.drop_index(op.f('ix_rendering_items_id'), table_name='rendering_items')

    # Drop rendering_items table
    op.drop_table('rendering_items')

    # Drop indexes for rendering_images
    op.drop_index(op.f('ix_rendering_images_rendering_id'), table_name='rendering_images')
    op.drop_index(op.f('ix_rendering_images_id'), table_name='rendering_images')

    # Drop rendering_images table
    op.drop_table('rendering_images')

    # Drop indexes for renderings
    op.drop_index(op.f('ix_renderings_budget_id'), table_name='renderings')
    op.drop_index(op.f('ix_renderings_visit_id'), table_name='renderings')
    op.drop_index(op.f('ix_renderings_status'), table_name='renderings')
    op.drop_index(op.f('ix_renderings_title'), table_name='renderings')
    op.drop_index(op.f('ix_renderings_id'), table_name='renderings')

    # Drop renderings table
    op.drop_table('renderings')

    # Drop enum with IF EXISTS
    connection = op.get_bind()
    connection.execute(sa.text("DROP TYPE IF EXISTS renderingstatus CASCADE"))
