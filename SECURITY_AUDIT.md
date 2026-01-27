# Security Audit - Metal Tracker

**Datum:** 2026-01-27
**Scope:** Vollstaendiger Code-Review aller Backend- und Frontend-Dateien
**Pruefgegenstand:** auth.py, main.py, models.py, schemas.py, database.py, price_service.py, routers/auth.py, scheduler_snapshots.py, static/*.html, requirements.txt

---

## KRITISCH (Sofort beheben)

### SEC-01: Hardcoded JWT Secret Fallback
- **Datei:** `auth.py:23`
- **Code:** `JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE-ME-IN-PRODUCTION-supersecretkey123")`
- **Risiko:** Wenn die Umgebungsvariable nicht gesetzt ist, wird ein im Quellcode (GitHub) oeffentlich sichtbarer Fallback verwendet. Angreifer koennen damit gueltige JWT-Tokens fuer beliebige User erstellen.
- **Empfehlung:** App beim Start abbrechen, wenn `JWT_SECRET` nicht gesetzt ist. Keinen Fallback verwenden.

### SEC-02: Hardcoded Session Secret Fallback
- **Datei:** `main.py:25`
- **Code:** `SESSION_SECRET = os.getenv("SESSION_SECRET", "change-me-in-production")`
- **Risiko:** Gleiche Problematik wie SEC-01. Kompromittiert die OAuth-Session-Integritaet.
- **Empfehlung:** Kein Fallback. App muss die Variable aus der Umgebung laden oder abbrechen.

### SEC-03: Kein Rate Limiting auf Login/Register
- **Datei:** `routers/auth.py:38-87`
- **Risiko:** Die Endpunkte `/api/auth/login` und `/api/auth/register` haben kein Rate Limiting. Dies ermoeglicht Brute-Force-Angriffe, Credential Stuffing und Account-Enumeration.
- **Empfehlung:** Strenges Rate Limiting anwenden (z.B. 5-10 Requests/Minute).

---

## HOCH (Zeitnah beheben)

### SEC-04: OAuth Token im URL-Parameter
- **Datei:** `routers/auth.py:173`
- **Code:** `return RedirectResponse(url=f"{frontend_url}?token={access_token}")`
- **Risiko:** JWT-Token landet in Browser-History, Server-Logs, Referer-Header und Proxy-Logs.
- **Empfehlung:** Kurzlebigen Einmal-Code (Authorization Code Flow) verwenden oder Token ueber HttpOnly-Cookie setzen.

### SEC-05: Unsichere OAuth Account-Verknuepfung
- **Datei:** `routers/auth.py:155-159`
- **Risiko:** Wenn ein Google-Konto die gleiche Email wie ein existierender Account hat, wird es automatisch verknuepft. Ein Angreifer mit Kontrolle ueber ein Google-Konto mit der Email des Opfers erhaelt vollen Zugriff.
- **Empfehlung:** Passwort-Bestaetigung vor Verknuepfung, oder explizite Verknuepfung aus bestehender Session.

### SEC-06: Fehlende Content-Security-Policy (CSP)
- **Datei:** `main.py:70-78`
- **Risiko:** Ohne CSP-Header koennen injizierte Skripte ungehindert ausgefuehrt werden. Besonders relevant bei CDN-Abhaengigkeiten.
- **Empfehlung:** CSP-Header hinzufuegen: `default-src 'self'; script-src 'self' cdn.tailwindcss.com cdn.jsdelivr.net 'unsafe-inline'; style-src 'self' 'unsafe-inline'`

---

## MITTEL (Geplant beheben)

### SEC-07: Kein Token-Blacklisting/Revocation
- **Datei:** `routers/auth.py:182-188`
- **Risiko:** Logout invalidiert Token nicht server-seitig. Kompromittierte Tokens bleiben 60 Minuten gueltig.
- **Empfehlung:** Redis-basierte Token-Blacklist oder kuerzere Token mit Refresh-Tokens.

### SEC-08: PII in Scheduler-Logs
- **Datei:** `scheduler_snapshots.py:96`
- **Code:** `print(f"  [OK] User {user.id} ({user.email})")`
- **Risiko:** Email-Adressen in Heroku-Logs.
- **Empfehlung:** Nur User-IDs loggen.

### SEC-09: Base.metadata.create_all() im Produktionscode
- **Datei:** `main.py:34-37`
- **Risiko:** Schema-Konflikte mit Alembic-Migrationen. Widerspricht dem Migrations-Workflow in CLAUDE.md.
- **Empfehlung:** Nur im lokalen Development ausfuehren (`if DEBUG`).

### SEC-10: API-Key Hashing mit einfachem SHA256
- **Datei:** `auth.py:44-46`
- **Risiko:** SHA256 ohne Salt oder HMAC. Bei Datenbank-Leak koennte ein Angreifer Keys schneller brute-forcen (obwohl Keys hochentropisch sind).
- **Empfehlung:** HMAC mit Server-Secret verwenden.

### SEC-11: DEBUG-Modus oeffnet CORS komplett
- **Datei:** `main.py:55`
- **Code:** `allow_origins=ALLOWED_ORIGINS if not DEBUG else ["*"]`
- **Risiko:** Versehentliches `DEBUG=true` in Produktion oeffnet CORS fuer alle Origins bei `allow_credentials=True`.
- **Empfehlung:** CORS-Wildcard und credentials nie zusammen erlauben.

### SEC-12: X-API-Key nicht in CORS allow_headers
- **Datei:** `main.py:58`
- **Risiko:** Cross-Origin-Requests mit API-Key-Auth scheitern am CORS-Preflight.
- **Empfehlung:** `X-API-Key` zu `allow_headers` hinzufuegen.

---

## NIEDRIG (Bei Gelegenheit)

### SEC-13: Keine Passwort-Komplexitaetsanforderungen
- **Datei:** `schemas.py:137`
- **Risiko:** Nur Mindestlaenge 8 Zeichen. Schwache Passwoerter moeglich.
- **Empfehlung:** Mindestens eine Ziffer und einen Buchstaben erfordern.

### SEC-14: Kein Account-Lockout
- **Risiko:** Unbegrenzte fehlgeschlagene Login-Versuche moeglich.
- **Empfehlung:** Temporaere Sperre nach 5-10 Fehlversuchen.

### SEC-15: decode_token ValueError-Risiko
- **Datei:** `auth.py:103`
- **Code:** `user_id = int(payload.get("sub"))`
- **Risiko:** `int(None)` wirft `TypeError`, nicht `JWTError`. Moeglicher unkontrollierter 500-Fehler.
- **Empfehlung:** `sub` auf None pruefen vor der Konvertierung.

### SEC-16: CDN ohne Subresource Integrity (SRI)
- **Datei:** `static/index.html:7-8`
- **Risiko:** Kompromittierter CDN koennte Schadcode einschleusen.
- **Empfehlung:** SRI-Hashes hinzufuegen oder Ressourcen lokal hosten.

### SEC-17: Veraltete Dependencies
- **Datei:** `requirements.txt`
- `python-jose==3.3.0` - Bekannte Schwachstellen. PyJWT empfohlen.
- `python-multipart==0.0.6` - Aeltere Version.
- **Empfehlung:** Dependencies aktualisieren.

---

## Positiv (Was gut gemacht ist)

- **SQLAlchemy ORM** durchgehend - kein SQL-Injection-Risiko
- **bcrypt** fuer Passwort-Hashing mit passlib
- **XSS-Schutz** im Frontend: `escapeHtml()` konsequent eingesetzt
- **Multi-Tenant-Isolation**: Alle DB-Queries filtern nach `user_id`
- **Rate Limiting** auf den meisten Endpunkten
- **Security Headers**: HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy
- **API-Keys**: Kryptographisch sicher generiert (`secrets.token_urlsafe`), gehasht gespeichert, nur einmal angezeigt
- **Pydantic-Validierung**: Strikte Input-Validierung mit Constraints
- **Docs in Produktion deaktiviert**: `/docs` und `/redoc` nur im Debug-Modus
- **Tier-Limits**: DB-seitig geprueft, nicht nur im Frontend

---

## Zusammenfassung

| Schweregrad | Anzahl | Wichtigste Findings |
|-------------|--------|---------------------|
| KRITISCH    | 3      | Hardcoded Secrets, fehlendes Rate Limit auf Auth-Endpoints |
| HOCH        | 3      | OAuth Token in URL, unsichere Account-Verknuepfung, kein CSP |
| MITTEL      | 6      | Kein Token-Blacklisting, PII in Logs, SHA256 API-Keys |
| NIEDRIG     | 5      | Passwort-Komplexitaet, CDN-SRI, veraltete Dependencies |

**Gesamtbewertung:** Die grundlegende Architektur ist solide. Die kritischen Punkte (Hardcoded Secrets, fehlendes Rate Limiting auf Auth-Endpunkten) muessen prioritaer behoben werden, da sie aktive Angriffsflaechen darstellen.
