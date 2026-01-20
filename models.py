from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import json


class User(Base):
    """User-Model fuer Multi-Tenant SaaS"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=True)  # Null bei OAuth-only Users

    # OAuth Provider IDs
    google_id = Column(String, unique=True, nullable=True, index=True)

    # Subscription Tier
    tier = Column(String, default="free")  # "free" | "premium"

    # Account Status
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    positions = relationship("Position", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    metal_type = Column(String, nullable=False, index=True)  # gold, silver, platinum, palladium
    product_type = Column(String, nullable=False, default="bar")  # coin, bar, round, granulate, jewelry
    description = Column(String, nullable=True)

    # NEU: Spread-Kategorie fuer Ankaufsabschlag
    # coin_bullion, coin_numismatic, bar_large, bar_small, bar_minted, round, granulate, jewelry
    spread_category = Column(String(50), nullable=True, default="bar_large")

    # Anzahl und Gewicht
    quantity = Column(Integer, nullable=False, default=1)  # Stueckzahl
    weight_per_unit = Column(Float, nullable=False)  # Gewicht pro Stueck in der gewaehlten Einheit
    weight_unit = Column(String, nullable=False, default="g")  # g, oz, kg
    weight_grams = Column(Float, nullable=False)  # Gesamtgewicht in Gramm (berechnet)

    purchase_price_eur = Column(Float, nullable=False)  # Gesamtpreis fuer alle Stuecke
    purchase_date = Column(Date, nullable=True)

    # NEU: Ankaufsabschlag in Prozent (z.B. 5.0 fuer 5% unter Spot)
    # Optional - wenn nicht gesetzt, wird der Default aus UserSettings verwendet
    spread_percent = Column(Float, nullable=True, default=None)

    # DEPRECATED: Wird durch spread_percent ersetzt, bleibt fuer Datenmigration
    discount_percent = Column(Float, nullable=True, default=None)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationship
    user = relationship("User", back_populates="positions")


class PortfolioSnapshot(Base):
    """Taeglicher Snapshot des Portfolio-Werts fuer Verlaufsanzeige"""
    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)  # unique constraint entfernt (pro user unique)
    total_purchase_value_eur = Column(Float, nullable=False)
    total_current_value_eur = Column(Float, nullable=False)
    total_weight_gold_g = Column(Float, default=0)
    total_weight_silver_g = Column(Float, default=0)
    total_weight_platinum_g = Column(Float, default=0)
    total_weight_palladium_g = Column(Float, default=0)
    positions_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())


class ApiKey(Base):
    """API-Keys fuer programmatischen Zugriff"""
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    key_hash = Column(String, nullable=False)
    key_prefix = Column(String(12), nullable=False)  # "mt_" + erste 8 Zeichen

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    last_used_at = Column(DateTime, nullable=True)

    # Relationship
    user = relationship("User", back_populates="api_keys")


class UserSettings(Base):
    """User-spezifische Einstellungen (Default-Ankaufsabschlaege pro Kategorie)"""
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # NEU: Kategorie-basierte Default-Spreads als JSON-String
    # Format: {"coin_bullion": 3.0, "bar_large": 2.0, ...}
    # Wird als Text gespeichert fuer SQLite-Kompatibilitaet
    _default_spreads = Column("default_spreads", Text, nullable=True)

    # DEPRECATED: Alte Metall-basierte Felder bleiben fuer Migration und Abwaertskompatibilitaet
    default_discount_gold = Column(Float, nullable=False, default=0.0)
    default_discount_silver = Column(Float, nullable=False, default=0.0)
    default_discount_platinum = Column(Float, nullable=False, default=0.0)
    default_discount_palladium = Column(Float, nullable=False, default=0.0)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationship
    user = relationship("User", back_populates="settings")

    @property
    def default_spreads(self) -> dict[str, float]:
        """Getter: JSON-String zu Dict"""
        if self._default_spreads:
            try:
                return json.loads(self._default_spreads)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    @default_spreads.setter
    def default_spreads(self, value: dict[str, float]):
        """Setter: Dict zu JSON-String"""
        if value:
            self._default_spreads = json.dumps(value)
        else:
            self._default_spreads = None
