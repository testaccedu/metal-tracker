"""Add spread-based surcharge system

Revision ID: 003
Revises: 002
Create Date: 2026-01-20

Fuegt das neue Spread-System hinzu:
- spread_category und spread_percent in positions (neben bestehendem discount_percent)
- default_spreads JSON-Feld in user_settings (neben bestehenden Metall-Feldern)
- Migriert bestehende Daten non-destruktiv

WICHTIG: Diese Migration ist ADDITIV - keine bestehenden Daten werden geloescht!
Die alten Felder (discount_percent, default_discount_*) bleiben erhalten.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Mapping von product_type zu spread_category
PRODUCT_TO_SPREAD_CATEGORY = {
    'coin': 'coin_bullion',
    'bar': 'bar_large',
    'round': 'round',
    'granulate': 'granulate',
    'jewelry': 'jewelry'
}


def upgrade() -> None:
    """
    Fuegt Spread-System hinzu (non-destruktiv).
    Bestehende Felder und Daten bleiben erhalten.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # 1. Neue Spalten zu positions hinzufuegen
    positions_columns = [col['name'] for col in inspector.get_columns('positions')]

    if 'spread_category' not in positions_columns:
        op.add_column('positions', sa.Column('spread_category', sa.String(50), nullable=True))

    if 'spread_percent' not in positions_columns:
        op.add_column('positions', sa.Column('spread_percent', sa.Float(), nullable=True))

    # 2. default_spreads zu user_settings hinzufuegen
    settings_columns = [col['name'] for col in inspector.get_columns('user_settings')]

    if 'default_spreads' not in settings_columns:
        # Text statt JSON fuer SQLite-Kompatibilitaet
        op.add_column('user_settings', sa.Column('default_spreads', sa.Text(), nullable=True))

    # 3. Bestehende Positions-Daten migrieren
    # spread_category aus product_type ableiten, spread_percent aus discount_percent kopieren
    conn.execute(sa.text("""
        UPDATE positions
        SET spread_category = CASE product_type
                WHEN 'coin' THEN 'coin_bullion'
                WHEN 'bar' THEN 'bar_large'
                WHEN 'round' THEN 'round'
                WHEN 'granulate' THEN 'granulate'
                WHEN 'jewelry' THEN 'jewelry'
                ELSE 'bar_large'
            END,
            spread_percent = discount_percent
        WHERE spread_category IS NULL
    """))

    # 4. User-Settings migrieren: Alte Metall-Discounts zu Kategorie-Spreads konvertieren
    # Wir erstellen ein JSON-Objekt mit den alten Werten als Basis
    # Da wir nicht wissen welches Metall der User hauptsaechlich hat,
    # nehmen wir Gold-Werte als Basis fuer alle Kategorien
    try:
        # PostgreSQL-Syntax
        conn.execute(sa.text("""
            UPDATE user_settings
            SET default_spreads = json_build_object(
                'coin_bullion', COALESCE(default_discount_gold, 0),
                'coin_numismatic', COALESCE(default_discount_gold, 0) + 5,
                'bar_large', COALESCE(default_discount_gold, 0),
                'bar_small', COALESCE(default_discount_gold, 0) + 2,
                'bar_minted', COALESCE(default_discount_gold, 0) + 1.5,
                'round', COALESCE(default_discount_gold, 0) + 2,
                'granulate', COALESCE(default_discount_gold, 0),
                'jewelry', 15.0
            )::text
            WHERE default_spreads IS NULL
        """))
    except Exception:
        # SQLite-Syntax (JSON als String)
        conn.execute(sa.text("""
            UPDATE user_settings
            SET default_spreads = '{"coin_bullion": ' || COALESCE(default_discount_gold, 0) ||
                ', "coin_numismatic": ' || (COALESCE(default_discount_gold, 0) + 5) ||
                ', "bar_large": ' || COALESCE(default_discount_gold, 0) ||
                ', "bar_small": ' || (COALESCE(default_discount_gold, 0) + 2) ||
                ', "bar_minted": ' || (COALESCE(default_discount_gold, 0) + 1.5) ||
                ', "round": ' || (COALESCE(default_discount_gold, 0) + 2) ||
                ', "granulate": ' || COALESCE(default_discount_gold, 0) ||
                ', "jewelry": 15.0}'
            WHERE default_spreads IS NULL
        """))


def downgrade() -> None:
    """
    Entfernt die neuen Spread-Felder.
    ACHTUNG: Daten in den neuen Feldern gehen verloren!
    Die alten Felder (discount_percent, default_discount_*) bleiben erhalten.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Neue Spalten aus positions entfernen
    positions_columns = [col['name'] for col in inspector.get_columns('positions')]

    if 'spread_percent' in positions_columns:
        op.drop_column('positions', 'spread_percent')

    if 'spread_category' in positions_columns:
        op.drop_column('positions', 'spread_category')

    # default_spreads aus user_settings entfernen
    settings_columns = [col['name'] for col in inspector.get_columns('user_settings')]

    if 'default_spreads' in settings_columns:
        op.drop_column('user_settings', 'default_spreads')
