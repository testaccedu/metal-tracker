from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional
from enum import Enum


class MetalType(str, Enum):
    GOLD = "gold"
    SILVER = "silver"
    PLATINUM = "platinum"
    PALLADIUM = "palladium"


class ProductType(str, Enum):
    COIN = "coin"           # Muenze (Kruegerrand, Maple Leaf, etc.)
    BAR = "bar"             # Barren
    ROUND = "round"         # Medaille / Round
    GRANULATE = "granulate" # Granulat
    JEWELRY = "jewelry"     # Schmuck


class SpreadCategory(str, Enum):
    """Produktkategorien fuer Ankaufsabschlaege (Spread)"""
    COIN_BULLION = "coin_bullion"       # Bullion-Muenzen (Kruegerrand, Maple Leaf, Wiener Phil.)
    COIN_NUMISMATIC = "coin_numismatic" # Sammlermuenzen mit Aufpreis
    BAR_LARGE = "bar_large"             # Grosse Barren >= 100g
    BAR_SMALL = "bar_small"             # Kleine Barren < 100g
    BAR_MINTED = "bar_minted"           # Gepraegte Barren (z.B. Heraeus, PAMP)
    ROUND = "round"                      # Medaillen / Rounds
    GRANULATE = "granulate"             # Granulat / Koerner
    JEWELRY = "jewelry"                  # Schmuck (hoechster Abschlag)


# Markt-Referenzwerte fuer Ankaufsabschlaege (typische Haendler-Spreads)
# Diese dienen als Orientierung und Defaults
REFERENCE_SPREADS: dict[str, dict[str, float]] = {
    "gold": {
        "coin_bullion": 3.0,      # Kruegerrand, Maple Leaf, etc.
        "coin_numismatic": 8.0,   # Sammlermuenzen
        "bar_large": 2.0,         # 100g, 250g, 1kg Barren
        "bar_small": 4.0,         # 1g, 5g, 10g, 20g, 50g Barren
        "bar_minted": 3.5,        # Gepraegte Barren
        "round": 5.0,             # Medaillen
        "granulate": 2.0,         # Granulat (nahe Spot)
        "jewelry": 15.0,          # Schmuck (hoher Abschlag)
    },
    "silver": {
        "coin_bullion": 15.0,     # Maple Leaf, Wiener Phil., etc.
        "coin_numismatic": 20.0,  # Sammlermuenzen
        "bar_large": 12.0,        # 1kg+ Barren
        "bar_small": 18.0,        # Kleine Barren
        "bar_minted": 15.0,       # Gepraegte Barren
        "round": 18.0,            # Medaillen
        "granulate": 12.0,        # Granulat
        "jewelry": 30.0,          # Schmuck
    },
    "platinum": {
        "coin_bullion": 5.0,
        "coin_numismatic": 10.0,
        "bar_large": 4.0,
        "bar_small": 6.0,
        "bar_minted": 5.0,
        "round": 8.0,
        "granulate": 4.0,
        "jewelry": 20.0,
    },
    "palladium": {
        "coin_bullion": 6.0,
        "coin_numismatic": 12.0,
        "bar_large": 5.0,
        "bar_small": 7.0,
        "bar_minted": 6.0,
        "round": 10.0,
        "granulate": 5.0,
        "jewelry": 25.0,
    },
}


def get_default_spread(metal_type: str, spread_category: str) -> float:
    """Holt den Referenz-Spread fuer eine Metall/Kategorie-Kombination"""
    metal = metal_type.lower()
    return REFERENCE_SPREADS.get(metal, {}).get(spread_category, 5.0)


def get_default_spreads_for_metal(metal_type: str) -> dict[str, float]:
    """Holt alle Referenz-Spreads fuer ein Metall"""
    metal = metal_type.lower()
    return REFERENCE_SPREADS.get(metal, REFERENCE_SPREADS["gold"])


class WeightUnit(str, Enum):
    GRAM = "g"              # Gramm
    OUNCE = "oz"            # Feinunze (31.1035g)
    KILOGRAM = "kg"         # Kilogramm


# Umrechnungsfaktoren zu Gramm
WEIGHT_TO_GRAMS = {
    "g": 1.0,
    "oz": 31.1035,
    "kg": 1000.0
}


def convert_to_grams(value: float, unit: str) -> float:
    """Konvertiert einen Gewichtswert zu Gramm"""
    factor = WEIGHT_TO_GRAMS.get(unit, 1.0)
    return value * factor


def convert_from_grams(grams: float, unit: str) -> float:
    """Konvertiert Gramm zu einer anderen Einheit"""
    factor = WEIGHT_TO_GRAMS.get(unit, 1.0)
    return grams / factor


class PositionBase(BaseModel):
    metal_type: MetalType
    product_type: ProductType = ProductType.BAR
    spread_category: SpreadCategory = SpreadCategory.BAR_LARGE  # NEU: Kategorie fuer Ankaufsabschlag
    description: Optional[str] = Field(None, max_length=200, description="Beschreibung (max 200 Zeichen)")
    quantity: int = Field(1, ge=1, le=10000, description="Anzahl/Stueckzahl (1-10000)")
    weight_per_unit: float = Field(..., gt=0, le=100000, description="Gewicht pro Stueck (max 100kg)")
    weight_unit: WeightUnit = WeightUnit.OUNCE
    purchase_price_eur: float = Field(..., gt=0, le=100000000, description="Gesamtkaufpreis in EUR (max 100M)")
    purchase_date: Optional[date] = None
    spread_percent: Optional[float] = Field(None, ge=0, le=100, description="Ankaufsabschlag in Prozent (0-100%). Wenn nicht gesetzt, wird der Default des Users verwendet.")
    # Deprecated: wird durch spread_percent ersetzt, bleibt fuer Abwaertskompatibilitaet
    discount_percent: Optional[float] = Field(None, ge=0, le=100, description="DEPRECATED: Nutze spread_percent")


class PositionCreate(PositionBase):
    pass


class PositionUpdate(BaseModel):
    metal_type: Optional[MetalType] = None
    product_type: Optional[ProductType] = None
    spread_category: Optional[SpreadCategory] = None
    description: Optional[str] = Field(None, max_length=200)
    quantity: Optional[int] = Field(None, ge=1, le=10000)
    weight_per_unit: Optional[float] = Field(None, gt=0, le=100000)
    weight_unit: Optional[WeightUnit] = None
    purchase_price_eur: Optional[float] = Field(None, gt=0, le=100000000)
    purchase_date: Optional[date] = None
    spread_percent: Optional[float] = Field(None, ge=0, le=100, description="Ankaufsabschlag in %")
    # Deprecated
    discount_percent: Optional[float] = Field(None, ge=0, le=100)


class Position(BaseModel):
    id: int
    metal_type: str
    product_type: str
    spread_category: Optional[str] = None  # NEU
    description: Optional[str] = None
    quantity: int
    weight_per_unit: float
    weight_unit: str
    weight_grams: float  # Gesamtgewicht
    purchase_price_eur: float
    purchase_date: Optional[date] = None
    spread_percent: Optional[float] = None  # NEU: Ankaufsabschlag
    discount_percent: Optional[float] = None  # Deprecated, fuer Abwaertskompatibilitaet
    created_at: datetime
    updated_at: datetime
    # Berechnete Felder - erweitert fuer Spot vs. Ankaufswert
    spot_value_eur: Optional[float] = None      # NEU: 100% Spot-Wert
    current_value_eur: Optional[float] = None   # = Ankaufswert (nach Spread)
    spread_amount_eur: Optional[float] = None   # NEU: Spread in EUR
    effective_spread_percent: Optional[float] = None  # NEU: Tatsaechlich angewandter Spread
    profit_loss_eur: Optional[float] = None
    profit_loss_percent: Optional[float] = None

    class Config:
        from_attributes = True


class PriceInfo(BaseModel):
    metal_type: MetalType
    price_per_gram_eur: float
    price_per_oz_eur: float
    timestamp: datetime


class PortfolioSummary(BaseModel):
    total_purchase_value_eur: float
    total_current_value_eur: float
    total_profit_loss_eur: float
    total_profit_loss_percent: float
    positions_count: int
    by_metal: dict[str, dict]
    last_updated: datetime


class PortfolioSnapshot(BaseModel):
    date: date
    total_purchase_value_eur: float
    total_current_value_eur: float
    profit_loss_eur: float
    profit_loss_percent: float
    positions_count: int

    class Config:
        from_attributes = True


class PortfolioHistory(BaseModel):
    snapshots: list[PortfolioSnapshot]
    period_days: int


# === AUTH SCHEMAS ===

class UserCreate(BaseModel):
    email: str = Field(..., min_length=5, max_length=255, pattern=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
    password: str = Field(..., min_length=8, max_length=100)


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    tier: str
    is_admin: bool
    created_at: datetime
    positions_count: Optional[int] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # Sekunden


class TokenData(BaseModel):
    user_id: int
    email: str
    tier: str


# === API KEY SCHEMAS ===

class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ApiKeyCreated(BaseModel):
    """Wird nur einmal bei Erstellung zurueckgegeben - Key danach nicht mehr abrufbar!"""
    id: int
    name: str
    api_key: str
    created_at: datetime


# === USER SETTINGS SCHEMAS ===

class UserSettingsUpdate(BaseModel):
    """User-Settings Update (nur die Felder die geaendert werden sollen)"""
    # NEU: Kategorie-basierte Spreads als JSON
    default_spreads: Optional[dict[str, float]] = Field(
        None,
        description="Default-Spreads pro Kategorie, z.B. {'coin_bullion': 3.0, 'bar_large': 2.0}"
    )
    # Deprecated: Alte Metall-basierte Felder (fuer Abwaertskompatibilitaet)
    default_discount_gold: Optional[float] = Field(None, ge=0, le=100, description="DEPRECATED")
    default_discount_silver: Optional[float] = Field(None, ge=0, le=100, description="DEPRECATED")
    default_discount_platinum: Optional[float] = Field(None, ge=0, le=100, description="DEPRECATED")
    default_discount_palladium: Optional[float] = Field(None, ge=0, le=100, description="DEPRECATED")


class UserSettingsResponse(BaseModel):
    """User-Settings Response"""
    # NEU: Kategorie-basierte Spreads
    default_spreads: Optional[dict[str, float]] = None
    # Deprecated: Alte Felder bleiben fuer Abwaertskompatibilitaet
    default_discount_gold: float
    default_discount_silver: float
    default_discount_platinum: float
    default_discount_palladium: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
