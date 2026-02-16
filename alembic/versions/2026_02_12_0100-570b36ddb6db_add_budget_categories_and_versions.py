"""add_budget_categories_and_versions

Restructure budgets: Budget → Categories → Items
Add budget versioning with JSON snapshots.

Revision ID: 570b36ddb6db
Revises: 49115b4ac9f8
Create Date: 2026-02-12 01:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision: str = '570b36ddb6db'
down_revision: Union[str, None] = '49115b4ac9f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create budget_categories table
    op.create_table('budget_categories',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('images', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('subtotal', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
        sa.Column('budget_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['budget_id'], ['budgets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_budget_categories_id'), 'budget_categories', ['id'], unique=False)
    op.create_index(op.f('ix_budget_categories_name'), 'budget_categories', ['name'], unique=False)
    op.create_index(op.f('ix_budget_categories_budget_id'), 'budget_categories', ['budget_id'], unique=False)

    # 2. Create budget_versions table
    op.create_table('budget_versions',
        sa.Column('budget_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('snapshot', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['budget_id'], ['budgets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_budget_versions_id'), 'budget_versions', ['id'], unique=False)
    op.create_index(op.f('ix_budget_versions_budget_id'), 'budget_versions', ['budget_id'], unique=False)
    op.create_index(op.f('ix_budget_versions_created_by_user_id'), 'budget_versions', ['created_by_user_id'], unique=False)

    # 3. Add current_version column to budgets
    op.add_column('budgets', sa.Column('current_version', sa.Integer(), nullable=False, server_default='0'))

    # 4. Add budget_category_id column to budget_items (nullable first for migration)
    op.add_column('budget_items', sa.Column(
        'budget_category_id',
        postgresql.UUID(as_uuid=True),
        nullable=True
    ))

    # 5. Migrate existing data: create a "General" category per budget, move items
    connection = op.get_bind()

    # Get all distinct budget_ids from budget_items
    budgets_with_items = connection.execute(sa.text(
        "SELECT DISTINCT budget_id FROM budget_items"
    )).fetchall()

    now = sa.text("NOW()")

    for (budget_id,) in budgets_with_items:
        category_id = str(uuid.uuid4())

        # Calculate subtotal for this budget's items
        subtotal_result = connection.execute(sa.text(
            "SELECT COALESCE(SUM(subtotal), 0) FROM budget_items WHERE budget_id = :budget_id"
        ), {"budget_id": budget_id}).scalar()

        # Create a "General" category for this budget
        connection.execute(sa.text(
            """
            INSERT INTO budget_categories (id, name, description, order_index, subtotal, budget_id, created_at, updated_at)
            VALUES (:id, :name, NULL, 0, :subtotal, :budget_id, NOW(), NOW())
            """
        ), {
            "id": category_id,
            "name": "General",
            "subtotal": subtotal_result,
            "budget_id": budget_id
        })

        # Move all items from this budget into the new category
        connection.execute(sa.text(
            """
            UPDATE budget_items
            SET budget_category_id = :category_id
            WHERE budget_id = :budget_id
            """
        ), {
            "category_id": category_id,
            "budget_id": budget_id
        })

    # 6. Make budget_category_id NOT NULL and add FK + index
    op.alter_column('budget_items', 'budget_category_id', nullable=False)
    op.create_foreign_key(
        'fk_budget_items_budget_category_id',
        'budget_items', 'budget_categories',
        ['budget_category_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index(op.f('ix_budget_items_budget_category_id'), 'budget_items', ['budget_category_id'], unique=False)

    # 7. Drop old columns from budget_items
    op.drop_index(op.f('ix_budget_items_section_name'), table_name='budget_items')
    op.drop_constraint('budget_items_budget_id_fkey', 'budget_items', type_='foreignkey')
    op.drop_index(op.f('ix_budget_items_budget_id'), table_name='budget_items')
    op.drop_column('budget_items', 'section_name')
    op.drop_column('budget_items', 'budget_id')


def downgrade() -> None:
    # 1. Re-add budget_id and section_name to budget_items
    op.add_column('budget_items', sa.Column('budget_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('budget_items', sa.Column('section_name', sa.String(length=255), nullable=True))

    # 2. Migrate data back: copy budget_id from category, copy category name to section_name
    connection = op.get_bind()
    connection.execute(sa.text(
        """
        UPDATE budget_items bi
        SET budget_id = bc.budget_id,
            section_name = bc.name
        FROM budget_categories bc
        WHERE bi.budget_category_id = bc.id
        """
    ))

    # 3. Make budget_id NOT NULL and add FK/index back
    op.alter_column('budget_items', 'budget_id', nullable=False)
    op.create_foreign_key(
        'budget_items_budget_id_fkey',
        'budget_items', 'budgets',
        ['budget_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index(op.f('ix_budget_items_budget_id'), 'budget_items', ['budget_id'], unique=False)
    op.create_index(op.f('ix_budget_items_section_name'), 'budget_items', ['section_name'], unique=False)

    # 4. Drop budget_category_id from budget_items
    op.drop_index(op.f('ix_budget_items_budget_category_id'), table_name='budget_items')
    op.drop_constraint('fk_budget_items_budget_category_id', 'budget_items', type_='foreignkey')
    op.drop_column('budget_items', 'budget_category_id')

    # 5. Drop current_version from budgets
    op.drop_column('budgets', 'current_version')

    # 6. Drop new tables
    op.drop_index(op.f('ix_budget_versions_created_by_user_id'), table_name='budget_versions')
    op.drop_index(op.f('ix_budget_versions_budget_id'), table_name='budget_versions')
    op.drop_index(op.f('ix_budget_versions_id'), table_name='budget_versions')
    op.drop_table('budget_versions')

    op.drop_index(op.f('ix_budget_categories_budget_id'), table_name='budget_categories')
    op.drop_index(op.f('ix_budget_categories_name'), table_name='budget_categories')
    op.drop_index(op.f('ix_budget_categories_id'), table_name='budget_categories')
    op.drop_table('budget_categories')
