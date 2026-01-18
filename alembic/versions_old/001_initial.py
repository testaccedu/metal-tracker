"""Initial migration - create positions and snapshots tables

Revision ID: 001
Revises:
Create Date: 2024-01-01
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Positions Tabelle
    op.create_table(
        'positions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('metal_type', sa.String(), nullable=False),
        sa.Column('product_type', sa.String(), nullable=False, server_default='bar'),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('weight_grams', sa.Float(), nullable=False),
        sa.Column('weight_unit', sa.String(), nullable=False, server_default='g'),
        sa.Column('weight_original', sa.Float(), nullable=False),
        sa.Column('purchase_price_eur', sa.Float(), nullable=False),
        sa.Column('purchase_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_positions_id'), 'positions', ['id'], unique=False)
    op.create_index(op.f('ix_positions_metal_type'), 'positions', ['metal_type'], unique=False)

    # Portfolio Snapshots Tabelle
    op.create_table(
        'portfolio_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('total_purchase_value_eur', sa.Float(), nullable=False),
        sa.Column('total_current_value_eur', sa.Float(), nullable=False),
        sa.Column('total_weight_gold_g', sa.Float(), server_default='0'),
        sa.Column('total_weight_silver_g', sa.Float(), server_default='0'),
        sa.Column('total_weight_platinum_g', sa.Float(), server_default='0'),
        sa.Column('total_weight_palladium_g', sa.Float(), server_default='0'),
        sa.Column('positions_count', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_portfolio_snapshots_id'), 'portfolio_snapshots', ['id'], unique=False)
    op.create_index(op.f('ix_portfolio_snapshots_date'), 'portfolio_snapshots', ['date'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_portfolio_snapshots_date'), table_name='portfolio_snapshots')
    op.drop_index(op.f('ix_portfolio_snapshots_id'), table_name='portfolio_snapshots')
    op.drop_table('portfolio_snapshots')
    op.drop_index(op.f('ix_positions_metal_type'), table_name='positions')
    op.drop_index(op.f('ix_positions_id'), table_name='positions')
    op.drop_table('positions')
