# Metal Tracker - Projekt-Kontext

## Beschreibung
Edelmetall-Portfolio-Tracker als Multi-User SaaS. Verwaltet Positionen in Gold, Silber, Platin und Palladium mit Live-Preisen von GOLD.DE.

## Tech Stack
- **Backend:** FastAPI (Python 3.11)
- **Datenbank:** PostgreSQL (Heroku), SQLite (lokal)
- **ORM:** SQLAlchemy
- **Auth:** JWT + Google OAuth (authlib)
- **Frontend:** Vanilla JS + Tailwind CSS + Chart.js
- **Hosting:** Heroku (EU Region)

## Projektstruktur
```
metal-tracker/
├── main.py              # FastAPI App, Endpoints, Middleware
├── models.py            # SQLAlchemy Models (User, Position, PortfolioSnapshot, ApiKey)
├── schemas.py           # Pydantic Schemas, Validierung
├── auth.py              # JWT-Logik, Password-Hashing, API-Key-Validierung
├── database.py          # DB-Verbindung
├── price_service.py     # GOLD.DE API Integration
├── scheduler_snapshots.py # Heroku Scheduler: Taegliche Snapshots
├── routers/
│   └── auth.py          # Auth-Endpoints (Login, Register, OAuth, API-Keys)
├── static/
│   ├── index.html       # Dashboard (nach Login)
│   ├── login.html       # Login-Seite
│   └── register.html    # Registrierung
├── migrate_to_saas.py   # Migrations-Script
├── reset_db.py          # DB-Reset (VORSICHT!)
├── requirements.txt     # Dependencies
├── .python-version      # Python Version (3.11)
├── Procfile             # Heroku Config
└── .env.example         # Environment-Variablen Vorlage
```

## Auth-System
- **JWT Token:** 60 Minuten Gueltigkeit, fuer Web-UI
- **API-Keys:** Fuer programmatischen Zugriff (Prefix: `mt_`), max 5 pro User
- **Email/Passwort:** bcrypt-Hashing via passlib
- **Google OAuth:** Optional, via authlib
- **Tiers:** Free (max 10 Positionen), Premium (unbegrenzt)
- **Auth-Reihenfolge:** API-Key (X-API-Key Header) > JWT (Authorization: Bearer)

## Discount-System
- **Spot-Preise:** Live-Preise von GOLD.DE (100% Spot, keine fixen Abschlaege mehr)
- **User-Settings:** Jeder User kann Default-Abschlaege pro Metall konfigurieren (0-100%)
  - `default_discount_gold`: Standard-Abschlag fuer Gold-Positionen
  - `default_discount_silver`: Standard-Abschlag fuer Silber-Positionen
  - `default_discount_platinum`: Standard-Abschlag fuer Platin-Positionen
  - `default_discount_palladium`: Standard-Abschlag fuer Palladium-Positionen
- **Position-Discount:** Jede Position kann einen eigenen Discount haben (ueberschreibt User-Default)
- **Berechnung:** `Wert = Spot-Preis × (1 - Discount/100) × Gewicht`
- **Beispiel:** Gold-Position mit 5% Discount → 95% vom Spot-Preis

## Wichtige Endpoints
| Methode | Endpoint | Auth | Beschreibung |
|---------|----------|------|--------------|
| POST | /api/auth/register | Nein | Registrierung |
| POST | /api/auth/login | Nein | Login -> JWT |
| GET | /api/auth/me | Ja | Aktueller User |
| GET | /api/auth/google | Nein | Google OAuth Start |
| POST | /api/auth/api-keys | Ja | API-Key erstellen |
| GET | /api/auth/api-keys | Ja | API-Keys auflisten |
| DELETE | /api/auth/api-keys/{id} | Ja | API-Key loeschen |
| GET | /api/settings | Ja | User-Settings abrufen |
| PUT | /api/settings | Ja | User-Settings aktualisieren |
| GET | /api/prices | Nein | Live-Preise von GOLD.DE (Spot) |
| GET | /api/positions | Ja | Alle Positionen des Users |
| POST | /api/positions | Ja | Position erstellen |
| DELETE | /api/positions/{id} | Ja | Position loeschen |
| GET | /api/summary | Ja | Portfolio-Zusammenfassung |
| GET | /api/history | Ja | Wert-Verlauf (Chart) |

## Security
- **JWT Auth:** Bearer Token im Authorization Header
- **API-Key Auth:** X-API-Key Header (SHA256 gehasht gespeichert)
- **Rate Limiting:** 20-60 req/min (slowapi)
- **CORS:** Nur eigene Domain
- **Security Headers:** HSTS, X-Frame-Options, etc.
- **XSS-Schutz:** escapeHtml() im Frontend
- **Multi-Tenant:** Alle Queries gefiltert nach user_id

## Heroku Scheduler
Taegliche Snapshot-Erstellung fuer alle User mit Positionen:
```bash
# Job im Scheduler Dashboard konfigurieren:
# Command: python scheduler_snapshots.py
# Frequency: Daily (z.B. 06:00 UTC)

# Scheduler Dashboard oeffnen:
heroku addons:open scheduler --app metal-tracker-tn
```

## Environment-Variablen
```
# Auth
JWT_SECRET=<geheimer-key>
SESSION_SECRET=<session-key>

# Google OAuth (optional)
GOOGLE_CLIENT_ID=<client-id>
GOOGLE_CLIENT_SECRET=<client-secret>
GOOGLE_REDIRECT_URI=https://.../api/auth/google/callback

# Admin (fuer Migration)
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=<initial-password>

# Sonstiges
DEBUG=false                 # true = API Docs aktiviert
ALLOWED_ORIGINS=https://... # CORS Origins
DATABASE_URL=postgresql://  # Von Heroku gesetzt
```

## Lokale Entwicklung
```bash
# venv aktivieren
.venv\Scripts\activate

# Dependencies installieren
pip install -r requirements.txt

# Server starten
python main.py

# Test-Login: admin@local.dev / testpassword123
```

## Deployment (Heroku)
```bash
# WICHTIG: Vor Schema-Aenderungen IMMER Backup!
heroku pg:backups:capture --app metal-tracker-tn

# Push zu Heroku
git push heroku master

# App starten/stoppen
heroku ps:scale web=1 --app metal-tracker-tn
heroku ps:scale web=0 --app metal-tracker-tn

# Logs
heroku logs --tail --app metal-tracker-tn

# Config setzen
heroku config:set JWT_SECRET=xxx --app metal-tracker-tn
```

## URLs
- **Produktion:** https://metal-tracker-tn-ffb450a69489.herokuapp.com/
- **Login:** https://metal-tracker-tn-ffb450a69489.herokuapp.com/login.html
- **GitHub:** https://github.com/testaccedu/metal-tracker

## KRITISCHE WARNUNGEN

### VOR JEDER DB-MIGRATION:
```bash
# IMMER zuerst Backup erstellen!
heroku pg:backups:capture --app metal-tracker-tn

# Backup-Liste pruefen
heroku pg:backups --app metal-tracker-tn

# Im Notfall wiederherstellen
heroku pg:backups:restore <backup-id> --app metal-tracker-tn
```

### reset_db.py LOESCHT ALLE DATEN!
- Nur fuer lokale Entwicklung verwenden
- NIEMALS auf Produktion ohne vorheriges Backup
- Besser: Alembic Migrations fuer Schema-Aenderungen

## Bekannte Einschraenkungen
- Historische Daten werden ab Positionserstellung gesammelt (keine Backfill-Funktion)
- CDN-Abhaengigkeit fuer Tailwind/Chart.js
- passlib 1.7.4 zeigt Warnung mit bcrypt 4.2.0 (funktioniert aber)
- Spot-Preise von GOLD.DE, Discounts werden per User konfiguriert

## API-Nutzung mit API-Key
```bash
# API-Key im Dashboard erstellen, dann:
curl -X GET "https://metal-tracker-tn-ffb450a69489.herokuapp.com/api/positions" \
  -H "X-API-Key: mt_dein_api_key_hier"

# Oder mit Authorization Header (JWT):
curl -X GET "https://metal-tracker-tn-ffb450a69489.herokuapp.com/api/positions" \
  -H "Authorization: Bearer <jwt_token>"
```
