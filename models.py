from sqlalchemy import Column, Integer, String, Float, DateTime, Enum
from sqlalchemy.sql import func
import enum
from database import Base


class MetalType(str, enum.Enum):
    GOLD = "gold"
    SILVER = "silver"
    PLATINUM = "platinum"
    PALLADIUM = "palladium"


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    metal_type = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    weight_grams = Column(Float, nullable=False)
    purchase_price_eur = Column(Float, nullable=False)
    purchase_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
