"""
Import von Produktionsdaten (Heroku PostgreSQL) in lokale SQLite-DB

Dieses Script:
1. Liest Daten direkt von der Heroku PostgreSQL-DB
2. Schreibt sie in die lokale SQLite-DB
3. Ermoeglicht lokales Testen mit echten Daten

Verwendung:
    python import_production_data.py
"""
import os
import sys
import sqlalchemy as sa
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import models
from database import Base

# Heroku Database URL aus Environment
HEROKU_DATABASE_URL = os.getenv("HEROKU_DATABASE_URL")
if not HEROKU_DATABASE_URL:
    print("❌ FEHLER: HEROKU_DATABASE_URL nicht gesetzt!")
    print("\nBitte setze die Environment-Variable:")
    print("  set HEROKU_DATABASE_URL=<heroku-db-url>")
    print("\nDie URL bekommst du mit:")
    print("  heroku config:get DATABASE_URL --app metal-tracker-tn")
    sys.exit(1)

# PostgreSQL URL Fix
if HEROKU_DATABASE_URL.startswith("postgres://"):
    HEROKU_DATABASE_URL = HEROKU_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Lokale SQLite DB
LOCAL_DB = "sqlite:///./metal_tracker.db"

print("[*] Import von Produktionsdaten...")
print("    Quelle: Heroku PostgreSQL")
print("    Ziel:   Lokale SQLite DB\n")

try:
    # Verbindung zu Heroku PostgreSQL
    print("[*] Verbinde zu Heroku-DB...")
    heroku_engine = create_engine(HEROKU_DATABASE_URL)
    HerokuSession = sessionmaker(bind=heroku_engine)
    heroku_db = HerokuSession()

    # Verbindung zu lokaler SQLite
    print("[*] Verbinde zu lokaler SQLite-DB...")
    local_engine = create_engine(LOCAL_DB)

    # Lokale DB leeren und neu erstellen
    print("[*] Loesche alte lokale Daten...")
    Base.metadata.drop_all(local_engine)
    Base.metadata.create_all(local_engine)

    LocalSession = sessionmaker(bind=local_engine)
    local_db = LocalSession()

    # Tabellen-Reihenfolge wegen Foreign Keys
    tables = [
        ("users", models.User),
        ("api_keys", models.ApiKey),
        ("user_settings", models.UserSettings),
        ("positions", models.Position),
        ("portfolio_snapshots", models.PortfolioSnapshot)
    ]

    total_imported = 0

    for table_name, model_class in tables:
        # Prüfe ob Tabelle in Heroku-DB existiert
        result = heroku_db.execute(text(
            f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table_name}')"
        ))
        table_exists = result.scalar()

        if not table_exists:
            print(f"[!] Tabelle '{table_name}' existiert nicht in Heroku-DB, ueberspringe...")
            continue

        # Existierende Spalten in Heroku-DB prüfen
        inspector = sa.inspect(heroku_db.bind)
        heroku_columns = {col['name'] for col in inspector.get_columns(table_name)}

        # Daten laden mit nur existierenden Spalten
        print(f"[*] Importiere {table_name}...", end=" ")

        # Baue SELECT nur mit existierenden Spalten
        columns_to_select = []
        for column in model_class.__table__.columns:
            if column.name in heroku_columns:
                columns_to_select.append(column)

        if not columns_to_select:
            print("(keine passenden Spalten)")
            continue

        records = heroku_db.query(*columns_to_select).all()

        if not records:
            print("(leer)")
            continue

        # Daten in lokale DB schreiben
        for record in records:
            # Kopiere nur existierende Attribute
            record_dict = {}
            for i, column in enumerate(columns_to_select):
                record_dict[column.name] = record[i]

            local_record = model_class(**record_dict)
            local_db.add(local_record)

        local_db.commit()
        count = len(records)
        total_imported += count
        print(f"[OK] {count} Eintraege")

    heroku_db.close()
    local_db.close()

    print(f"\n[OK] Import abgeschlossen! {total_imported} Eintraege importiert.")
    print("\n[*] Du kannst jetzt lokal mit Produktionsdaten testen:")
    print("    python main.py")

except Exception as e:
    print(f"\n[ERROR] FEHLER beim Import: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
