# Metal Tracker - Projekt-Kontext

## Beschreibung
Edelmetall-Portfolio-Tracker API mit Web-UI. Verwaltet Positionen in Gold, Silber, Platin und Palladium mit Live-Preisen von GOLD.DE.

## Tech Stack
- **Backend:** FastAPI (Python 3.11)
- **Datenbank:** PostgreSQL (Heroku), SQLite (lokal)
- **ORM:** SQLAlchemy
- **Frontend:** Vanilla JS + Tailwind CSS + Chart.js
- **Hosting:** Heroku (EU Region)

## Projektstruktur
```
metal-tracker/
├── main.py           # FastAPI App, Endpoints, Middleware
├── models.py         # SQLAlchemy Models (Position, PortfolioSnapshot)
├── schemas.py        # Pydantic Schemas, Validierung
├── database.py       # DB-Verbindung
├── price_service.py  # GOLD.DE API Integration
├── static/
│   └── index.html    # Web-UI (Single Page)
├── requirements.txt  # Dependencies
├── Procfile          # Heroku Config
└── .env.example      # Environment-Variablen Vorlage
```

## Wichtige Endpoints
| Methode | Endpoint | Auth | Beschreibung |
|---------|----------|------|--------------|
| GET | /api/prices | Nein | Live-Preise von GOLD.DE |
| GET | /api/positions | Ja | Alle Positionen |
| POST | /api/positions | Ja | Position erstellen |
| DELETE | /api/positions/{id} | Ja | Position loeschen |
| GET | /api/summary | Ja | Portfolio-Zusammenfassung |
| GET | /api/history | Ja | Wert-Verlauf (Chart) |

## Security
- **API-Key Auth:** Header `X-API-Key` erforderlich
- **Rate Limiting:** 20-60 req/min (slowapi)
- **CORS:** Nur eigene Domain
- **Security Headers:** HSTS, X-Frame-Options, etc.
- **XSS-Schutz:** escapeHtml() im Frontend

## Environment-Variablen
```
API_KEY=<geheimer-key>     # Auth (Pflicht in Produktion)
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

# Server starten (ohne Auth)
python main.py

# Mit Auth
set API_KEY=test123 && python main.py
```

## Deployment (Heroku)
```bash
# Push zu Heroku
git push heroku master

# App starten/stoppen
heroku ps:scale web=1 --app metal-tracker-tn
heroku ps:scale web=0 --app metal-tracker-tn

# Logs
heroku logs --tail --app metal-tracker-tn

# Config
heroku config:set API_KEY=xxx --app metal-tracker-tn
```

## URLs
- **Produktion:** https://metal-tracker-tn-ffb450a69489.herokuapp.com/
- **GitHub:** https://github.com/testaccedu/metal-tracker

## Bekannte Einschraenkungen
- Keine Multi-User-Unterstuetzung (Single API-Key)
- Historische Preise sind simuliert (backfill_snapshots)
- CDN-Abhaengigkeit fuer Tailwind/Chart.js
