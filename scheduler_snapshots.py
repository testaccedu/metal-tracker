"""
Scheduler-Script fuer taegliche Portfolio-Snapshots

Wird von Heroku Scheduler taeglich ausgefuehrt.
Erstellt/aktualisiert Snapshots fuer alle User mit Positionen.

Usage:
    python scheduler_snapshots.py
"""
import asyncio
import sys
from datetime import date
from sqlalchemy import func

from database import SessionLocal
import models
import price_service


async def create_snapshot_for_user(db, user: models.User) -> bool:
    """Erstellt einen Snapshot fuer einen User. Gibt True zurueck wenn erfolgreich."""
    today = date.today()

    # Alle Positionen des Users laden
    positions = db.query(models.Position).filter(models.Position.user_id == user.id).all()

    if not positions:
        return False

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
        models.PortfolioSnapshot.user_id == user.id,
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
            user_id=user.id,
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
    return True


async def run_daily_snapshots():
    """Hauptfunktion: Erstellt Snapshots fuer alle aktiven User mit Positionen"""
    print(f"[{date.today()}] Starte taegliche Snapshot-Erstellung...")

    db = SessionLocal()
    try:
        # Finde alle aktiven User die mindestens eine Position haben
        users_with_positions = db.query(models.User).filter(
            models.User.is_active == True,
            models.User.id.in_(
                db.query(models.Position.user_id).distinct()
            )
        ).all()

        print(f"Gefunden: {len(users_with_positions)} User mit Positionen")

        success_count = 0
        error_count = 0

        for user in users_with_positions:
            try:
                if await create_snapshot_for_user(db, user):
                    success_count += 1
                    print(f"  [OK] User {user.id} ({user.email})")
            except Exception as e:
                error_count += 1
                print(f"  [FEHLER] User {user.id}: {e}")

        print(f"\nFertig! Erfolg: {success_count}, Fehler: {error_count}")

        if error_count > 0:
            sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(run_daily_snapshots())
