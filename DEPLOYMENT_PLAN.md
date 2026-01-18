# Sicherer Deployment-Plan: Discount-System

## Status
- ✅ Lokale DB: Erfolgreich getestet mit Produktionsdaten + Migration 002
- ✅ App läuft: http://localhost:8000
- ⏳ Heroku: Bereit für Deployment

## Was wurde geändert?

### Neue Migrations-Struktur
Alte Migrationen waren veraltet und führten zu Datenverlusten. **Komplett neu aufgebaut:**

**Migration 001 - Baseline (Produktions-Schema v21)**
- Erstellt: users, positions (OHNE discount_percent), portfolio_snapshots, api_keys
- **Idempotent:** Prüft ob Tabellen existieren, erstellt nur fehlende
- Spiegelt AKTUELLES Produktions-Schema wider

**Migration 002 - Discount-System**
- Erstellt: user_settings Tabelle
- Fügt hinzu: discount_percent Spalte zu positions
- **Idempotent:** Prüft ob bereits vorhanden

### Code-Änderungen
- models.py: UserSettings Model, discount_percent in Position
- main.py: /api/settings Endpoints (GET, PUT)
- price_service.py: calculate_current_value() mit Discount-Parameter
- static/index.html: Settings-Modal, Discount-Feld im Position-Form, Mobile-Responsive

---

## Deployment-Schritte (KRITISCH!)

### Schritt 1: Backup erstellen (PFLICHT!)
```bash
heroku pg:backups:capture --app metal-tracker-tn
heroku pg:backups --app metal-tracker-tn  # Verifizieren
```

### Schritt 2: Produktions-DB vorbereiten
```bash
# Alembic muss wissen, dass Migration 001 bereits angewendet ist
heroku run "alembic stamp 001" --app metal-tracker-tn
```

**WICHTIG:** Die Produktions-DB hat bereits das Schema von Migration 001!
Ohne `alembic stamp 001` würde Alembic versuchen, Tabellen neu zu erstellen → FEHLER!

### Schritt 3: Deployen
```bash
git push heroku <branch>:master
```

Die `release` Phase im Procfile führt automatisch aus:
```bash
alembic upgrade head
```

Das wendet **nur** Migration 002 an (Discount-System), weil Migration 001 bereits gestamped ist.

### Schritt 4: Verifizieren
```bash
# Logs prüfen
heroku logs --tail --app metal-tracker-tn

# App testen
curl https://metal-tracker-tn-ffb450a69489.herokuapp.com/api/prices

# Einloggen und Daten prüfen
https://metal-tracker-tn-ffb450a69489.herokuapp.com/login.html
```

---

## Im Notfall: Rollback

### Option 1: Heroku Rollback
```bash
heroku rollback v25 --app metal-tracker-tn
heroku restart --app metal-tracker-tn
```

### Option 2: Backup wiederherstellen
```bash
heroku pg:backups:restore <backup-id> DATABASE_URL --app metal-tracker-tn --confirm metal-tracker-tn
heroku restart --app metal-tracker-tn
```

---

## Warum ging es beim ersten Mal schief?

### Das Problem
Migration 001 war **katastrophal veraltet**:
- Erstellt `positions` OHNE `user_id`, `quantity`, `weight_per_unit`
- Erstellt KEINE `users` Tabelle
- Erstellt KEINE `api_keys` Tabelle

### Was passierte
1. Alembic versuchte Migration 001 auszuführen
2. Konflikt: Tabellen existierten mit **anderem Schema**
3. App konnte Daten nicht mehr finden (kein `user_id` in positions)

### Die Lösung
- **Neue Baseline-Migration 001:** Spiegelt AKTUELLES Produktions-Schema wider
- **Idempotente Migrations:** Prüfen ob Tabellen/Spalten existieren
- **Stamping:** Alembic weiß, dass Baseline bereits angewendet ist

---

## Checkliste vor Deployment

- [ ] Backup erstellt?
- [ ] `heroku run "alembic stamp 001"` ausgeführt?
- [ ] Lokale Tests erfolgreich?
- [ ] Rollback-Plan bereit?
- [ ] Produktions-Daten verifiziert (3 Users, 3 Positionen)?

---

## Nach erfolgreichem Deployment

1. Testen: https://metal-tracker-tn-ffb450a69489.herokuapp.com/login.html
2. Discount-System testen:
   - User-Menu → Einstellungen
   - Default-Discounts setzen (z.B. Gold: 5%)
   - Neue Position erstellen
   - Prüfen ob Discount angewendet wird
3. Backup erstellen (nach erfolgreichem Test)

---

**Erstellt:** 2026-01-18
**Status:** Bereit für Deployment
