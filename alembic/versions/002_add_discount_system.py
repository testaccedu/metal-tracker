"""Add discount system (user_settings table and discount_percent column)

Revision ID: 002
Revises: 001
Create Date: 2026-01-18

Fügt das Discount-System hinzu:
- user_settings Tabelle (Default-Discounts pro Metall)
- discount_percent Spalte in positions (optionaler Override)
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Fügt Discount-System hinzu.
    Idempotent: Tabellen/Spalten werden nur erstellt, wenn sie nicht existieren.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # 1. user_settings Tabelle erstellen
    existing_tables = inspector.get_table_names()
    if 'user_settings' not in existing_tables:
        op.create_table(
            'user_settings',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('default_discount_gold', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('default_discount_silver', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('default_discount_platinum', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('default_discount_palladium', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_user_settings_id'), 'user_settings', ['id'], unique=False)
        op.create_index(op.f('ix_user_settings_user_id'), 'user_settings', ['user_id'], unique=True)

    # 2. discount_percent Spalte zu positions hinzufügen
    positions_columns = [col['name'] for col in inspector.get_columns('positions')]
    if 'discount_percent' not in positions_columns:
        op.add_column('positions', sa.Column('discount_percent', sa.Float(), nullable=True))


def downgrade() -> None:
    """
    Entfernt das Discount-System.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Spalte aus positions entfernen
    positions_columns = [col['name'] for col in inspector.get_columns('positions')]
    if 'discount_percent' in positions_columns:
        op.drop_column('positions', 'discount_percent')

    # user_settings Tabelle löschen
    existing_tables = inspector.get_table_names()
    if 'user_settings' in existing_tables:
        op.drop_index(op.f('ix_user_settings_user_id'), table_name='user_settings')
        op.drop_index(op.f('ix_user_settings_id'), table_name='user_settings')
        op.drop_table('user_settings')
