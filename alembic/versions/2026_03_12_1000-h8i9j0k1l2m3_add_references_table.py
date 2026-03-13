"""Add references table for customer references

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-03-12 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'h8i9j0k1l2m3'
down_revision: str = 'g7h8i9j0k1l2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if not inspector.has_table('customer_references'):
        op.create_table('customer_references',
            sa.Column('client_name', sa.String(length=255), nullable=False),
            sa.Column('location', sa.String(length=255), nullable=False),
            sa.Column('project_description', sa.String(length=500), nullable=False),
            sa.Column('project_value', sa.String(length=100), nullable=False),
            sa.Column('phone', sa.String(length=50), nullable=True),
            sa.Column('display_order', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('company_id', sa.UUID(), nullable=False),
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )

        op.create_index(op.f('ix_customer_references_id'), 'customer_references', ['id'], unique=False)
        op.create_index(op.f('ix_customer_references_client_name'), 'customer_references', ['client_name'], unique=False)
        op.create_index(op.f('ix_customer_references_company_id'), 'customer_references', ['company_id'], unique=False)

    # Seed default references using the first company
    result = connection.execute(sa.text("SELECT id FROM companies LIMIT 1"))
    row = result.fetchone()
    if row:
        company_id = str(row[0])
        defaults = [
            ("Josh Mc Michael", "New London NH", "New Construction Home 9500 sf²", "$2.5M", "603-381-2704", 0),
            ("Kayla Esce", "Windham NH", "Full Rehab, Deck and Porch", "$380,000", "603-393-6271", 1),
            ("Kevin Abood", "Windham NH", "Full Rehab Interior and Patio", "$170,000", "603-216-7165", 2),
            ("Amanda Hartford", "Windham NH", "Full Bathroom Renovation", "$70,000", "518-791-4915", 3),
            ("Tammy Davis", "Auburn NH", "Build a ADU and Garage", "$335,000", "603-289-9596", 4),
        ]
        for client_name, location, description, value, phone, order in defaults:
            connection.execute(sa.text(
                """
                INSERT INTO customer_references (id, client_name, location, project_description, project_value, phone, display_order, company_id, created_at, updated_at)
                VALUES (gen_random_uuid(), :client_name, :location, :project_description, :project_value, :phone, :display_order, :company_id, NOW(), NOW())
                """
            ), {
                "client_name": client_name,
                "location": location,
                "project_description": description,
                "project_value": value,
                "phone": phone,
                "display_order": order,
                "company_id": company_id,
            })


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if inspector.has_table('customer_references'):
        op.drop_index(op.f('ix_customer_references_company_id'), table_name='customer_references')
        op.drop_index(op.f('ix_customer_references_client_name'), table_name='customer_references')
        op.drop_index(op.f('ix_customer_references_id'), table_name='customer_references')
        op.drop_table('customer_references')
