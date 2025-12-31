from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class MetalType(str, Enum):
    GOLD = "gold"
    SILVER = "silver"
    PLATINUM = "platinum"
    PALLADIUM = "palladium"


class PositionBase(BaseModel):
    metal_type: MetalType
    description: Optional[str] = None
    weight_grams: float = Field(..., gt=0, description="Gewicht in Gramm")
    purchase_price_eur: float = Field(..., gt=0, description="Kaufpreis in EUR")
    purchase_date: Optional[datetime] = None


class PositionCreate(PositionBase):
    pass


class PositionUpdate(BaseModel):
    metal_type: Optional[MetalType] = None
    description: Optional[str] = None
    weight_grams: Optional[float] = Field(None, gt=0)
    purchase_price_eur: Optional[float] = Field(None, gt=0)
    purchase_date: Optional[datetime] = None


class Position(PositionBase):
    id: int
    created_at: datetime
    updated_at: datetime
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
