"""
Migration Script: Single-User -> Multi-User SaaS

Dieses Script migriert bestehende Daten zur neuen Multi-User-Struktur:
1. Erstellt einen Admin-User aus Environment-Variablen
2. Weist alle bestehenden Positionen diesem User zu
3. Weist alle bestehenden PortfolioSnapshots diesem User zu

Ausfuehrung:
    python migrate_to_saas.py

WICHTIG: Vor der Migration ein Datenbank-Backup erstellen!
"""
import os
import sys
from datetime import datetime

# Environment laden
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from database import engine, SessionLocal
import models
import auth as auth_module

# Admin-Credentials aus Environment
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@metal-tracker.local")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")


def run_migration():
    """Fuehrt die Migration durch"""
    print("=" * 50)
    print("Metal Tracker - SaaS Migration")
    print("=" * 50)

    if not ADMIN_PASSWORD:
        print("\nFEHLER: ADMIN_PASSWORD muss gesetzt sein!")
        print("Setze die Umgebungsvariable oder .env Datei:")
        print("  ADMIN_EMAIL=admin@example.com")
        print("  ADMIN_PASSWORD=sicherespasswort")
        sys.exit(1)

    print(f"\nAdmin-Email: {ADMIN_EMAIL}")
    print(f"Admin-Password: {'*' * len(ADMIN_PASSWORD)}")

    db = SessionLocal()

    try:
        # 1. Pruefen ob users-Tabelle existiert (neue Struktur)
        print("\n[1/5] Pruefe Datenbankstruktur...")
        try:
            db.execute(text("SELECT 1 FROM users LIMIT 1"))
            print("      Users-Tabelle existiert bereits.")
        except Exception:
            print("      Users-Tabelle existiert nicht - erstelle Tabellen...")
            models.Base.metadata.create_all(bind=engine)
            print("      Tabellen erstellt.")

        # 2. Pruefen ob Admin-User existiert
        print("\n[2/5] Pruefe Admin-User...")
        admin = auth_module.get_user_by_email(db, ADMIN_EMAIL)

        if admin:
            print(f"      Admin-User existiert bereits (ID: {admin.id})")
        else:
            print("      Erstelle Admin-User...")
            admin = models.User(
                email=ADMIN_EMAIL,
                password_hash=auth_module.hash_password(ADMIN_PASSWORD),
                tier="premium",  # Admin bekommt Premium
                is_admin=True,
                is_active=True
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print(f"      Admin-User erstellt (ID: {admin.id})")

        # 3. Pruefen ob es Positionen ohne user_id gibt
        print("\n[3/5] Migriere Positionen...")
        try:
            # Versuche positions ohne user_id zu finden
            result = db.execute(text("SELECT COUNT(*) FROM positions WHERE user_id IS NULL"))
            orphan_positions = result.scalar()

            if orphan_positions > 0:
                print(f"      {orphan_positions} Positionen ohne User gefunden - weise Admin zu...")
                db.execute(
                    text("UPDATE positions SET user_id = :user_id WHERE user_id IS NULL"),
                    {"user_id": admin.id}
                )
                db.commit()
                print(f"      {orphan_positions} Positionen migriert.")
            else:
                print("      Keine verwaisten Positionen gefunden.")
        except Exception as e:
            print(f"      Fehler bei Positions-Migration: {e}")
            # Vielleicht ist user_id noch nicht in der DB
            print("      Versuche Schema-Update...")
            try:
                db.execute(text("ALTER TABLE positions ADD COLUMN user_id INTEGER REFERENCES users(id)"))
                db.commit()
                db.execute(
                    text("UPDATE positions SET user_id = :user_id"),
                    {"user_id": admin.id}
                )
                db.commit()
                print("      Schema aktualisiert und Positionen migriert.")
            except Exception as e2:
                print(f"      Schema-Update nicht moeglich: {e2}")

        # 4. Migriere PortfolioSnapshots
        print("\n[4/5] Migriere PortfolioSnapshots...")
        try:
            result = db.execute(text("SELECT COUNT(*) FROM portfolio_snapshots WHERE user_id IS NULL"))
            orphan_snapshots = result.scalar()

            if orphan_snapshots > 0:
                print(f"      {orphan_snapshots} Snapshots ohne User gefunden - weise Admin zu...")
                db.execute(
                    text("UPDATE portfolio_snapshots SET user_id = :user_id WHERE user_id IS NULL"),
                    {"user_id": admin.id}
                )
                db.commit()
                print(f"      {orphan_snapshots} Snapshots migriert.")
            else:
                print("      Keine verwaisten Snapshots gefunden.")
        except Exception as e:
            print(f"      Fehler bei Snapshot-Migration: {e}")
            try:
                db.execute(text("ALTER TABLE portfolio_snapshots ADD COLUMN user_id INTEGER REFERENCES users(id)"))
                db.commit()
                db.execute(
                    text("UPDATE portfolio_snapshots SET user_id = :user_id"),
                    {"user_id": admin.id}
                )
                db.commit()
                print("      Schema aktualisiert und Snapshots migriert.")
            except Exception as e2:
                print(f"      Schema-Update nicht moeglich: {e2}")

        # 5. Statistiken
        print("\n[5/5] Migration abgeschlossen!")
        print("\n" + "=" * 50)
        print("STATISTIKEN:")
        print("=" * 50)

        user_count = db.query(models.User).count()
        position_count = db.query(models.Position).count()
        snapshot_count = db.query(models.PortfolioSnapshot).count()

        print(f"  Users:     {user_count}")
        print(f"  Positionen: {position_count}")
        print(f"  Snapshots:  {snapshot_count}")

        print("\n" + "=" * 50)
        print("LOGIN-DATEN:")
        print("=" * 50)
        print(f"  Email:    {ADMIN_EMAIL}")
        print(f"  Passwort: {ADMIN_PASSWORD}")
        print("\nBitte aendere das Passwort nach dem ersten Login!")

    except Exception as e:
        print(f"\nFEHLER: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    run_migration()
