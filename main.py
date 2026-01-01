import os
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func

import models
import schemas
from schemas import convert_to_grams
from database import engine, get_db, Base
import price_service

# Pfad zum static Verzeichnis
STATIC_DIR = Path(__file__).parent / "static"

# Datenbank-Tabellen erstellen
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Metal Tracker API",
    description="API zum Verwalten deines Edelmetall-Portfolios (Gold, Silber, Platin, Palladium)",
    version="2.0.0"
)

# CORS erlauben
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"], include_in_schema=False)
async def root():
    """Serve die Web-UI"""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api", tags=["Root"])
async def api_info():
    """API Status und Info"""
    return {
        "name": "Metal Tracker API",
        "version": "2.0.0",
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
    """Aktuelle Edelmetall-Preise abrufen (Quelle: GOLD.DE)"""
    prices = await price_service.get_all_prices()
    source_info = price_service.get_source_info()
    return {
        "prices": prices,
        "currency": "EUR",
        **source_info
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
    # Gesamtgewicht in Gramm berechnen: Anzahl * Gewicht pro Stueck
    weight_per_unit_grams = convert_to_grams(position.weight_per_unit, position.weight_unit.value)
    total_weight_grams = weight_per_unit_grams * position.quantity

    db_position = models.Position(
        metal_type=position.metal_type.value,
        product_type=position.product_type.value,
        description=position.description,
        quantity=position.quantity,
        weight_per_unit=position.weight_per_unit,
        weight_unit=position.weight_unit.value,
        weight_grams=total_weight_grams,
        purchase_price_eur=position.purchase_price_eur,
        purchase_date=position.purchase_date
    )
    db.add(db_position)
    db.commit()
    db.refresh(db_position)

    # Historische Snapshots erstellen wenn Kaufdatum vorhanden
    if db_position.purchase_date:
        await backfill_snapshots(db, db_position)

    # Snapshot aktualisieren
    await update_daily_snapshot(db)

    return await enrich_position(db_position)


@app.get("/api/positions", response_model=list[schemas.Position], tags=["Positionen"])
async def get_positions(
    metal_type: Optional[schemas.MetalType] = Query(None, description="Nach Metallart filtern"),
    product_type: Optional[schemas.ProductType] = Query(None, description="Nach Produktart filtern"),
    db: Session = Depends(get_db)
):
    """Alle Positionen abrufen"""
    query = db.query(models.Position)

    if metal_type:
        query = query.filter(models.Position.metal_type == metal_type.value)
    if product_type:
        query = query.filter(models.Position.product_type == product_type.value)

    positions = query.order_by(models.Position.created_at.desc()).all()
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

    # Enums zu Strings konvertieren
    if "metal_type" in update_data and update_data["metal_type"]:
        update_data["metal_type"] = update_data["metal_type"].value
    if "product_type" in update_data and update_data["product_type"]:
        update_data["product_type"] = update_data["product_type"].value

    # Gewicht neu berechnen wenn geaendert
    if "weight_per_unit" in update_data or "weight_unit" in update_data or "quantity" in update_data:
        weight_per_unit = update_data.get("weight_per_unit", position.weight_per_unit)
        unit = update_data.get("weight_unit", position.weight_unit)
        quantity = update_data.get("quantity", position.quantity)
        if hasattr(unit, "value"):
            unit = unit.value
        weight_per_unit_grams = convert_to_grams(weight_per_unit, unit)
        update_data["weight_grams"] = weight_per_unit_grams * quantity
        update_data["weight_unit"] = unit

    for field, value in update_data.items():
        setattr(position, field, value)

    db.commit()
    db.refresh(position)

    # Snapshot aktualisieren
    await update_daily_snapshot(db)

    return await enrich_position(position)


@app.delete("/api/positions/{position_id}", tags=["Positionen"])
async def delete_position(position_id: int, db: Session = Depends(get_db)):
    """Position loeschen"""
    position = db.query(models.Position).filter(models.Position.id == position_id).first()

    if not position:
        raise HTTPException(status_code=404, detail="Position nicht gefunden")

    db.delete(position)
    db.commit()

    # Snapshot aktualisieren
    await update_daily_snapshot(db)

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


# === PORTFOLIO HISTORY ===

@app.get("/api/history", response_model=schemas.PortfolioHistory, tags=["Portfolio"])
async def get_portfolio_history(
    days: int = Query(30, ge=7, le=365, description="Anzahl Tage"),
    db: Session = Depends(get_db)
):
    """Portfolio-Verlauf abrufen"""
    start_date = date.today() - timedelta(days=days)

    snapshots = db.query(models.PortfolioSnapshot).filter(
        models.PortfolioSnapshot.date >= start_date
    ).order_by(models.PortfolioSnapshot.date.asc()).all()

    result_snapshots = []
    for s in snapshots:
        profit_loss = s.total_current_value_eur - s.total_purchase_value_eur
        profit_percent = (profit_loss / s.total_purchase_value_eur * 100) if s.total_purchase_value_eur > 0 else 0
        result_snapshots.append(schemas.PortfolioSnapshot(
            date=s.date,
            total_purchase_value_eur=round(s.total_purchase_value_eur, 2),
            total_current_value_eur=round(s.total_current_value_eur, 2),
            profit_loss_eur=round(profit_loss, 2),
            profit_loss_percent=round(profit_percent, 2),
            positions_count=s.positions_count
        ))

    return schemas.PortfolioHistory(snapshots=result_snapshots, period_days=days)


@app.post("/api/history/snapshot", tags=["Portfolio"])
async def create_snapshot(db: Session = Depends(get_db)):
    """Manuell einen Snapshot erstellen"""
    await update_daily_snapshot(db)
    return {"message": "Snapshot erstellt", "date": date.today().isoformat()}


# === HELPER FUNCTIONS ===

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
        "product_type": position.product_type,
        "description": position.description,
        "quantity": position.quantity,
        "weight_per_unit": position.weight_per_unit,
        "weight_unit": position.weight_unit,
        "weight_grams": round(position.weight_grams, 4),
        "purchase_price_eur": position.purchase_price_eur,
        "purchase_date": position.purchase_date,
        "created_at": position.created_at,
        "updated_at": position.updated_at,
        "current_value_eur": round(current_value, 2),
        "profit_loss_eur": round(profit_loss, 2),
        "profit_loss_percent": round(profit_loss_percent, 2)
    }


async def update_daily_snapshot(db: Session):
    """Erstellt oder aktualisiert den taeglichen Portfolio-Snapshot"""
    today = date.today()

    # Alle Positionen laden
    positions = db.query(models.Position).all()

    if not positions:
        return

    total_purchase = 0.0
    total_current = 0.0
    weights = {"gold": 0, "silver": 0, "platinum": 0, "palladium": 0}

    for p in positions:
        current_value = await price_service.calculate_current_value(p.metal_type, p.weight_grams)
        total_purchase += p.purchase_price_eur
        total_current += current_value
        if p.metal_type in weights:
            weights[p.metal_type] += p.weight_grams

    # Existierenden Snapshot suchen oder neuen erstellen
    snapshot = db.query(models.PortfolioSnapshot).filter(
        models.PortfolioSnapshot.date == today
    ).first()

    if snapshot:
        snapshot.total_purchase_value_eur = total_purchase
        snapshot.total_current_value_eur = total_current
        snapshot.total_weight_gold_g = weights["gold"]
        snapshot.total_weight_silver_g = weights["silver"]
        snapshot.total_weight_platinum_g = weights["platinum"]
        snapshot.total_weight_palladium_g = weights["palladium"]
        snapshot.positions_count = len(positions)
    else:
        snapshot = models.PortfolioSnapshot(
            date=today,
            total_purchase_value_eur=total_purchase,
            total_current_value_eur=total_current,
            total_weight_gold_g=weights["gold"],
            total_weight_silver_g=weights["silver"],
            total_weight_platinum_g=weights["platinum"],
            total_weight_palladium_g=weights["palladium"],
            positions_count=len(positions)
        )
        db.add(snapshot)

    db.commit()


async def backfill_snapshots(db: Session, position: models.Position):
    """Erstellt rueckwirkend Snapshots ab dem Kaufdatum einer Position"""
    import random

    if not position.purchase_date:
        return

    today = date.today()
    start_date = position.purchase_date

    # Nicht mehr als 365 Tage zurueck
    max_days_back = 365
    if (today - start_date).days > max_days_back:
        start_date = today - timedelta(days=max_days_back)

    # Aktuelle Preise holen
    current_prices = await price_service.fetch_live_prices()

    # Alle Positionen fuer Gesamtberechnung
    all_positions = db.query(models.Position).all()

    # Fuer jeden Tag seit Kaufdatum
    current_date = start_date
    while current_date < today:
        # Pruefen ob Snapshot schon existiert
        existing = db.query(models.PortfolioSnapshot).filter(
            models.PortfolioSnapshot.date == current_date
        ).first()

        if not existing:
            # Simuliere Preisschwankung: +/- 10% ueber die Zeit
            days_ago = (today - current_date).days
            # Je weiter zurueck, desto mehr Schwankung moeglich
            variance = random.uniform(-0.10, 0.05) * (days_ago / 365)

            total_purchase = 0.0
            total_current = 0.0
            weights = {"gold": 0, "silver": 0, "platinum": 0, "palladium": 0}

            for p in all_positions:
                # Nur Positionen die an diesem Datum schon existierten
                if p.purchase_date and p.purchase_date <= current_date:
                    total_purchase += p.purchase_price_eur
                    # Simulierter Preis mit Schwankung
                    price_per_gram = current_prices.get(p.metal_type, 0) * (1 + variance)
                    current_value = price_per_gram * p.weight_grams
                    total_current += current_value
                    if p.metal_type in weights:
                        weights[p.metal_type] += p.weight_grams

            if total_purchase > 0:  # Nur wenn es Positionen gab
                snapshot = models.PortfolioSnapshot(
                    date=current_date,
                    total_purchase_value_eur=total_purchase,
                    total_current_value_eur=total_current,
                    total_weight_gold_g=weights["gold"],
                    total_weight_silver_g=weights["silver"],
                    total_weight_platinum_g=weights["platinum"],
                    total_weight_palladium_g=weights["palladium"],
                    positions_count=sum(1 for p in all_positions if p.purchase_date and p.purchase_date <= current_date)
                )
                db.add(snapshot)

        current_date += timedelta(days=1)

    db.commit()


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
