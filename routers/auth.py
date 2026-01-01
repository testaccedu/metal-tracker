"""
Auth Router - Endpoints fuer Registrierung, Login, OAuth
"""
import os
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import httpx
from authlib.integrations.starlette_client import OAuth

import models
import schemas
import auth as auth_module
from database import get_db

router = APIRouter(prefix="/api/auth", tags=["Auth"])

# Google OAuth Setup
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "")

oauth = OAuth()
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    oauth.register(
        name='google',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )


# === REGISTRIERUNG ===

@router.post("/register", response_model=schemas.Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Registriert einen neuen User mit Email und Passwort.
    Gibt direkt einen JWT Token zurueck (auto-login nach Registrierung).
    """
    # Pruefen ob Email schon existiert
    existing = auth_module.get_user_by_email(db, user_data.email.lower())
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email ist bereits registriert"
        )

    # User erstellen
    user = auth_module.create_user(
        db=db,
        email=user_data.email.lower(),
        password=user_data.password
    )

    # Token erstellen und zurueckgeben
    access_token = auth_module.create_access_token(user)
    return schemas.Token(
        access_token=access_token,
        expires_in=auth_module.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


# === LOGIN ===

@router.post("/login", response_model=schemas.Token)
async def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    """
    Login mit Email und Passwort.
    Gibt einen JWT Token zurueck.
    """
    user = auth_module.authenticate_user(db, credentials.email.lower(), credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungueltige Email oder Passwort",
            headers={"WWW-Authenticate": "Bearer"}
        )

    access_token = auth_module.create_access_token(user)
    return schemas.Token(
        access_token=access_token,
        expires_in=auth_module.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


# === AKTUELLER USER ===

@router.get("/me", response_model=schemas.UserResponse)
async def get_current_user_info(
    user: models.User = Depends(auth_module.get_current_user),
    db: Session = Depends(get_db)
):
    """Gibt Informationen ueber den aktuell eingeloggten User zurueck"""
    positions_count = db.query(models.Position).filter(models.Position.user_id == user.id).count()

    return schemas.UserResponse(
        id=user.id,
        email=user.email,
        tier=user.tier,
        is_admin=user.is_admin,
        created_at=user.created_at,
        positions_count=positions_count
    )


# === GOOGLE OAUTH ===

@router.get("/google")
async def google_login(request: Request):
    """
    Startet den Google OAuth Flow.
    Leitet den User zu Google weiter.
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth ist nicht konfiguriert"
        )

    redirect_uri = GOOGLE_REDIRECT_URI or str(request.url_for('google_callback'))
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """
    Google OAuth Callback.
    Erstellt User falls nicht vorhanden und gibt JWT zurueck.
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth ist nicht konfiguriert"
        )

    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        if not user_info:
            raise HTTPException(status_code=400, detail="Keine User-Info von Google erhalten")

        google_id = user_info.get('sub')
        email = user_info.get('email', '').lower()

        if not email:
            raise HTTPException(status_code=400, detail="Keine Email von Google erhalten")

        # User suchen oder erstellen
        user = auth_module.get_user_by_google_id(db, google_id)
        if not user:
            # Pruefen ob Email schon existiert (dann verknuepfen)
            user = auth_module.get_user_by_email(db, email)
            if user:
                # Existierenden Account mit Google verknuepfen
                user.google_id = google_id
                db.commit()
            else:
                # Neuen User erstellen
                user = auth_module.create_user(db=db, email=email, google_id=google_id)

        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account ist deaktiviert")

        # JWT Token erstellen
        access_token = auth_module.create_access_token(user)

        # Redirect zum Frontend mit Token als Query-Parameter
        frontend_url = FRONTEND_URL or "/"
        return RedirectResponse(url=f"{frontend_url}?token={access_token}")

    except Exception as e:
        # Bei OAuth-Fehlern zum Login zurueckleiten
        return RedirectResponse(url="/login.html?error=oauth_failed")


# === LOGOUT (Token Invalidierung) ===

@router.post("/logout")
async def logout():
    """
    Logout - Client soll Token lokal loeschen.
    Server-side Token-Blacklist waere fuer Produktion empfohlen.
    """
    return {"message": "Erfolgreich ausgeloggt"}


# === TIER INFO ===

@router.get("/tier-info")
async def get_tier_info(user: models.User = Depends(auth_module.get_current_user), db: Session = Depends(get_db)):
    """Gibt Informationen ueber das aktuelle Tier und Limits zurueck"""
    positions_count = db.query(models.Position).filter(models.Position.user_id == user.id).count()
    remaining = auth_module.get_positions_remaining(db, user)
    limit = auth_module.TIER_LIMITS.get(user.tier, 10)

    return {
        "tier": user.tier,
        "positions_count": positions_count,
        "positions_limit": limit,
        "positions_remaining": remaining,
        "is_at_limit": remaining == 0
    }
