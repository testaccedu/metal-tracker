"""Baseline: Current production schema (v21)

Revision ID: 001
Revises:
Create Date: 2026-01-18

Diese Migration spiegelt das AKTUELLE Schema der Produktions-DB wider (v21).
Sie erstellt Tabellen nur falls sie noch nicht existieren (idempotent).
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Erstellt das Produktions-Schema (v21) - OHNE Discount-System.
    Idempotent: Tabellen werden nur erstellt, wenn sie nicht existieren.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # 1. users Tabelle
    if 'users' not in existing_tables:
        op.create_table(
            'users',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('email', sa.String(), nullable=False),
            sa.Column('password_hash', sa.String(), nullable=True),
            sa.Column('google_id', sa.String(), nullable=True),
            sa.Column('tier', sa.String(), server_default='free'),
            sa.Column('is_active', sa.Boolean(), server_default='true'),
            sa.Column('is_admin', sa.Boolean(), server_default='false'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
        op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
        op.create_index(op.f('ix_users_google_id'), 'users', ['google_id'], unique=True)

    # 2. positions Tabelle (OHNE discount_percent)
    if 'positions' not in existing_tables:
        op.create_table(
            'positions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('metal_type', sa.String(), nullable=False),
            sa.Column('product_type', sa.String(), nullable=False, server_default='bar'),
            sa.Column('description', sa.String(), nullable=True),
            sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('weight_per_unit', sa.Float(), nullable=False),
            sa.Column('weight_unit', sa.String(), nullable=False, server_default='g'),
            sa.Column('weight_grams', sa.Float(), nullable=False),
            sa.Column('purchase_price_eur', sa.Float(), nullable=False),
            sa.Column('purchase_date', sa.Date(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_positions_id'), 'positions', ['id'], unique=False)
        op.create_index(op.f('ix_positions_user_id'), 'positions', ['user_id'], unique=False)
        op.create_index(op.f('ix_positions_metal_type'), 'positions', ['metal_type'], unique=False)

    # 3. portfolio_snapshots Tabelle
    if 'portfolio_snapshots' not in existing_tables:
        op.create_table(
            'portfolio_snapshots',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('date', sa.Date(), nullable=False),
            sa.Column('total_purchase_value_eur', sa.Float(), nullable=False),
            sa.Column('total_current_value_eur', sa.Float(), nullable=False),
            sa.Column('total_weight_gold_g', sa.Float(), server_default='0'),
            sa.Column('total_weight_silver_g', sa.Float(), server_default='0'),
            sa.Column('total_weight_platinum_g', sa.Float(), server_default='0'),
            sa.Column('total_weight_palladium_g', sa.Float(), server_default='0'),
            sa.Column('positions_count', sa.Integer(), server_default='0'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_portfolio_snapshots_id'), 'portfolio_snapshots', ['id'], unique=False)
        op.create_index(op.f('ix_portfolio_snapshots_user_id'), 'portfolio_snapshots', ['user_id'], unique=False)
        op.create_index(op.f('ix_portfolio_snapshots_date'), 'portfolio_snapshots', ['date'], unique=False)

    # 4. api_keys Tabelle
    if 'api_keys' not in existing_tables:
        op.create_table(
            'api_keys',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('key_hash', sa.String(), nullable=False),
            sa.Column('key_prefix', sa.String(length=12), nullable=False),
            sa.Column('is_active', sa.Boolean(), server_default='true'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('last_used_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_api_keys_id'), 'api_keys', ['id'], unique=False)
        op.create_index(op.f('ix_api_keys_user_id'), 'api_keys', ['user_id'], unique=False)


def downgrade() -> None:
    """
    Entfernt alle Tabellen. ACHTUNG: DATENVERLUST!
    """
    op.drop_index(op.f('ix_api_keys_user_id'), table_name='api_keys')
    op.drop_index(op.f('ix_api_keys_id'), table_name='api_keys')
    op.drop_table('api_keys')

    op.drop_index(op.f('ix_portfolio_snapshots_date'), table_name='portfolio_snapshots')
    op.drop_index(op.f('ix_portfolio_snapshots_user_id'), table_name='portfolio_snapshots')
    op.drop_index(op.f('ix_portfolio_snapshots_id'), table_name='portfolio_snapshots')
    op.drop_table('portfolio_snapshots')

    op.drop_index(op.f('ix_positions_metal_type'), table_name='positions')
    op.drop_index(op.f('ix_positions_user_id'), table_name='positions')
    op.drop_index(op.f('ix_positions_id'), table_name='positions')
    op.drop_table('positions')

    op.drop_index(op.f('ix_users_google_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
