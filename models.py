from sqlalchemy import Column, Integer, String, Float, DateTime, Date
from sqlalchemy.sql import func
from database import Base


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    metal_type = Column(String, nullable=False, index=True)  # gold, silver, platinum, palladium
    product_type = Column(String, nullable=False, default="bar")  # coin, bar, round, granulate, jewelry
    description = Column(String, nullable=True)

    # Anzahl und Gewicht
    quantity = Column(Integer, nullable=False, default=1)  # Stueckzahl
    weight_per_unit = Column(Float, nullable=False)  # Gewicht pro Stueck in der gewaehlten Einheit
    weight_unit = Column(String, nullable=False, default="g")  # g, oz, kg
    weight_grams = Column(Float, nullable=False)  # Gesamtgewicht in Gramm (berechnet)

    purchase_price_eur = Column(Float, nullable=False)  # Gesamtpreis fuer alle Stuecke
    purchase_date = Column(Date, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class PortfolioSnapshot(Base):
    """Taeglicher Snapshot des Portfolio-Werts fuer Verlaufsanzeige"""
    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, unique=True, index=True)
    total_purchase_value_eur = Column(Float, nullable=False)
    total_current_value_eur = Column(Float, nullable=False)
    total_weight_gold_g = Column(Float, default=0)
    total_weight_silver_g = Column(Float, default=0)
    total_weight_platinum_g = Column(Float, default=0)
    total_weight_palladium_g = Column(Float, default=0)
    positions_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
