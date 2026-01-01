#!/usr/bin/env python3
"""
Taeglicher Snapshot Job fuer Heroku Scheduler.

Aufruf: python snapshot_job.py

Dieser Job wird taeglich ausgefuehrt und speichert den aktuellen Portfolio-Wert
mit echten Live-Preisen in der Datenbank.
"""
import asyncio
from datetime import date

from database import SessionLocal
import models
import price_service


async def create_daily_snapshot():
    """Erstellt einen taeglichen Portfolio-Snapshot mit echten Live-Preisen"""
    db = SessionLocal()
    today = date.today()

    try:
        # Alle Positionen laden
        positions = db.query(models.Position).all()

        if not positions:
            print(f"[{today}] Keine Positionen vorhanden - kein Snapshot erstellt")
            return

        # Aktuelle Live-Preise holen
        print(f"[{today}] Hole aktuelle Preise von GOLD.DE...")
        prices = await price_service.fetch_live_prices()

        total_purchase = 0.0
        total_current = 0.0
        weights = {"gold": 0.0, "silver": 0.0, "platinum": 0.0, "palladium": 0.0}

        for p in positions:
            total_purchase += p.purchase_price_eur
            price_per_gram = prices.get(p.metal_type, 0)
            current_value = price_per_gram * p.weight_grams
            total_current += current_value
            if p.metal_type in weights:
                weights[p.metal_type] += p.weight_grams

        # Existierenden Snapshot pruefen
        existing = db.query(models.PortfolioSnapshot).filter(
            models.PortfolioSnapshot.date == today
        ).first()

        if existing:
            # Update
            existing.total_purchase_value_eur = total_purchase
            existing.total_current_value_eur = total_current
            existing.total_weight_gold_g = weights["gold"]
            existing.total_weight_silver_g = weights["silver"]
            existing.total_weight_platinum_g = weights["platinum"]
            existing.total_weight_palladium_g = weights["palladium"]
            existing.positions_count = len(positions)
            print(f"[{today}] Snapshot aktualisiert")
        else:
            # Neu erstellen
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
            print(f"[{today}] Neuer Snapshot erstellt")

        db.commit()

        # Zusammenfassung ausgeben
        profit_loss = total_current - total_purchase
        profit_percent = (profit_loss / total_purchase * 100) if total_purchase > 0 else 0

        print(f"  Kaufwert:      {total_purchase:,.2f} EUR")
        print(f"  Aktueller Wert: {total_current:,.2f} EUR")
        print(f"  Gewinn/Verlust: {profit_loss:+,.2f} EUR ({profit_percent:+.2f}%)")
        print(f"  Positionen:     {len(positions)}")

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(create_daily_snapshot())
