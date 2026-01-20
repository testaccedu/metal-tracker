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
from schemas import REFERENCE_SPREADS, get_default_spread


def get_user_settings(db, user: models.User) -> models.UserSettings:
    """Holt oder erstellt die UserSettings fuer einen User"""
    settings = db.query(models.UserSettings).filter(
        models.UserSettings.user_id == user.id
    ).first()

    if not settings:
        settings = models.UserSettings(
            user_id=user.id,
            default_discount_gold=0.0,
            default_discount_silver=0.0,
            default_discount_platinum=0.0,
            default_discount_palladium=0.0
        )
        settings.default_spreads = REFERENCE_SPREADS.get("gold", {})
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return settings


def get_effective_spread(position: models.Position, user_settings: models.UserSettings) -> float:
    """Ermittelt den effektiven Spread fuer eine Position"""
    # 1. Position hat eigenen Spread
    if position.spread_percent is not None:
        return position.spread_percent
    if position.discount_percent is not None:
        return position.discount_percent

    # 2. User-Default fuer Kategorie
    category = position.spread_category or "bar_large"
    if user_settings.default_spreads:
        if category in user_settings.default_spreads:
            return user_settings.default_spreads[category]

    # 3. Fallback: Markt-Referenzwerte
    metal = position.metal_type.lower()
    return get_default_spread(metal, category)


async def create_snapshot_for_user(db, user: models.User) -> bool:
    """Erstellt einen Snapshot fuer einen User. Gibt True zurueck wenn erfolgreich."""
    today = date.today()

    # Alle Positionen des Users laden
    positions = db.query(models.Position).filter(models.Position.user_id == user.id).all()

    if not positions:
        return False

    # User-Settings laden fuer Spread-Berechnung
    user_settings = get_user_settings(db, user)

    total_purchase = 0.0
    total_current = 0.0
    weights = {"gold": 0, "silver": 0, "platinum": 0, "palladium": 0}

    for p in positions:
        # BUG FIX: Effektiven Spread beruecksichtigen!
        effective_spread = get_effective_spread(p, user_settings)
        current_value = await price_service.calculate_current_value(
            p.metal_type,
            p.weight_grams,
            effective_spread
        )
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
