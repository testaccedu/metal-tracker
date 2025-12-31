import os
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

import models
import schemas
from database import engine, get_db, Base
import price_service

# Datenbank-Tabellen erstellen (fuer lokale Entwicklung)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Metal Tracker API",
    description="API zum Verwalten deines Edelmetall-Portfolios (Gold, Silber, Platin, Palladium)",
    version="1.0.0"
)

# CORS erlauben
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
async def root():
    """API Status und Info"""
    return {
        "name": "Metal Tracker API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health", tags=["Root"])
async def health_check():
    """Health Check Endpunkt"""
    return {"status": "healthy"}


# === PREISE ===

@app.get("/api/prices", response_model=dict, tags=["Preise"])
async def get_current_prices():
    """Aktuelle Edelmetall-Preise abrufen"""
    prices = await price_service.get_all_prices()
    return {
        "prices": prices,
        "currency": "EUR",
        "source": "metals.dev" if os.getenv("METALS_API_KEY") else "fallback"
    }


@app.get("/api/prices/{metal_type}", tags=["Preise"])
async def get_metal_price(metal_type: schemas.MetalType):
    """Preis fuer ein bestimmtes Metall abrufen"""
    prices = await price_service.get_all_prices()
    metal = metal_type.value.lower()

    if metal not in prices:
        raise HTTPException(status_code=404, detail=f"Metall {metal_type} nicht gefunden")

    return prices[metal]


# === POSITIONEN ===

@app.post("/api/positions", response_model=schemas.Position, tags=["Positionen"])
async def create_position(position: schemas.PositionCreate, db: Session = Depends(get_db)):
    """Neue Position hinzufuegen"""
    db_position = models.Position(
        metal_type=position.metal_type.value,
        description=position.description,
        weight_grams=position.weight_grams,
        purchase_price_eur=position.purchase_price_eur,
        purchase_date=position.purchase_date
    )
    db.add(db_position)
    db.commit()
    db.refresh(db_position)

    return await enrich_position(db_position)


@app.get("/api/positions", response_model=list[schemas.Position], tags=["Positionen"])
async def get_positions(
    metal_type: Optional[schemas.MetalType] = Query(None, description="Nach Metallart filtern"),
    db: Session = Depends(get_db)
):
    """Alle Positionen abrufen"""
    query = db.query(models.Position)

    if metal_type:
        query = query.filter(models.Position.metal_type == metal_type.value)

    positions = query.all()
    return [await enrich_position(p) for p in positions]


@app.get("/api/positions/{position_id}", response_model=schemas.Position, tags=["Positionen"])
async def get_position(position_id: int, db: Session = Depends(get_db)):
    """Einzelne Position abrufen"""
    position = db.query(models.Position).filter(models.Position.id == position_id).first()

    if not position:
        raise HTTPException(status_code=404, detail="Position nicht gefunden")

    return await enrich_position(position)


@app.put("/api/positions/{position_id}", response_model=schemas.Position, tags=["Positionen"])
async def update_position(
    position_id: int,
    position_update: schemas.PositionUpdate,
    db: Session = Depends(get_db)
):
    """Position aktualisieren"""
    position = db.query(models.Position).filter(models.Position.id == position_id).first()

    if not position:
        raise HTTPException(status_code=404, detail="Position nicht gefunden")

    update_data = position_update.model_dump(exclude_unset=True)
    if "metal_type" in update_data and update_data["metal_type"]:
        update_data["metal_type"] = update_data["metal_type"].value

    for field, value in update_data.items():
        setattr(position, field, value)

    db.commit()
    db.refresh(position)

    return await enrich_position(position)


@app.delete("/api/positions/{position_id}", tags=["Positionen"])
async def delete_position(position_id: int, db: Session = Depends(get_db)):
    """Position loeschen"""
    position = db.query(models.Position).filter(models.Position.id == position_id).first()

    if not position:
        raise HTTPException(status_code=404, detail="Position nicht gefunden")

    db.delete(position)
    db.commit()

    return {"message": "Position geloescht", "id": position_id}


# === PORTFOLIO SUMMARY ===

@app.get("/api/summary", response_model=schemas.PortfolioSummary, tags=["Portfolio"])
async def get_portfolio_summary(db: Session = Depends(get_db)):
    """Portfolio-Zusammenfassung mit Gesamtwert abrufen"""
    positions = db.query(models.Position).all()

    if not positions:
        return schemas.PortfolioSummary(
            total_purchase_value_eur=0,
            total_current_value_eur=0,
            total_profit_loss_eur=0,
            total_profit_loss_percent=0,
            positions_count=0,
            by_metal={},
            last_updated=datetime.now()
        )

    total_purchase = 0.0
    total_current = 0.0
    by_metal: dict = {}

    for position in positions:
        metal = position.metal_type
        current_value = await price_service.calculate_current_value(
            position.metal_type,
            position.weight_grams
        )

        total_purchase += position.purchase_price_eur
        total_current += current_value

        if metal not in by_metal:
            by_metal[metal] = {
                "purchase_value_eur": 0,
                "current_value_eur": 0,
                "weight_grams": 0,
                "positions_count": 0
            }

        by_metal[metal]["purchase_value_eur"] += position.purchase_price_eur
        by_metal[metal]["current_value_eur"] += current_value
        by_metal[metal]["weight_grams"] += position.weight_grams
        by_metal[metal]["positions_count"] += 1

    # Profit/Loss pro Metall berechnen
    for metal in by_metal:
        purchase = by_metal[metal]["purchase_value_eur"]
        current = by_metal[metal]["current_value_eur"]
        by_metal[metal]["profit_loss_eur"] = round(current - purchase, 2)
        by_metal[metal]["profit_loss_percent"] = round(
            ((current - purchase) / purchase * 100) if purchase > 0 else 0, 2
        )
        by_metal[metal]["purchase_value_eur"] = round(purchase, 2)
        by_metal[metal]["current_value_eur"] = round(current, 2)
        by_metal[metal]["weight_grams"] = round(by_metal[metal]["weight_grams"], 2)

    profit_loss = total_current - total_purchase
    profit_loss_percent = ((profit_loss / total_purchase) * 100) if total_purchase > 0 else 0

    return schemas.PortfolioSummary(
        total_purchase_value_eur=round(total_purchase, 2),
        total_current_value_eur=round(total_current, 2),
        total_profit_loss_eur=round(profit_loss, 2),
        total_profit_loss_percent=round(profit_loss_percent, 2),
        positions_count=len(positions),
        by_metal=by_metal,
        last_updated=datetime.now()
    )


async def enrich_position(position: models.Position) -> dict:
    """Reichert eine Position mit aktuellem Wert und Gewinn/Verlust an"""
    current_value = await price_service.calculate_current_value(
        position.metal_type,
        position.weight_grams
    )
    profit_loss = current_value - position.purchase_price_eur
    profit_loss_percent = (profit_loss / position.purchase_price_eur * 100) if position.purchase_price_eur > 0 else 0

    return {
        "id": position.id,
        "metal_type": position.metal_type,
        "description": position.description,
        "weight_grams": position.weight_grams,
        "purchase_price_eur": position.purchase_price_eur,
        "purchase_date": position.purchase_date,
        "created_at": position.created_at,
        "updated_at": position.updated_at,
        "current_value_eur": round(current_value, 2),
        "profit_loss_eur": round(profit_loss, 2),
        "profit_loss_percent": round(profit_loss_percent, 2)
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
