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
    description: Optional[str] = None
    quantity: int = Field(1, ge=1, description="Anzahl/Stueckzahl")
    weight_per_unit: float = Field(..., gt=0, description="Gewicht pro Stueck")
    weight_unit: WeightUnit = WeightUnit.OUNCE
    purchase_price_eur: float = Field(..., gt=0, description="Gesamtkaufpreis in EUR")
    purchase_date: Optional[date] = None


class PositionCreate(PositionBase):
    pass


class PositionUpdate(BaseModel):
    metal_type: Optional[MetalType] = None
    product_type: Optional[ProductType] = None
    description: Optional[str] = None
    quantity: Optional[int] = Field(None, ge=1)
    weight_per_unit: Optional[float] = Field(None, gt=0)
    weight_unit: Optional[WeightUnit] = None
    purchase_price_eur: Optional[float] = Field(None, gt=0)
    purchase_date: Optional[date] = None


class Position(BaseModel):
    id: int
    metal_type: str
    product_type: str
    description: Optional[str] = None
    quantity: int
    weight_per_unit: float
    weight_unit: str
    weight_grams: float  # Gesamtgewicht
    purchase_price_eur: float
    purchase_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime
    # Berechnete Felder
    current_value_eur: Optional[float] = None
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
