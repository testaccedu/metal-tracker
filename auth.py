"""
Auth-Modul fuer Metal Tracker SaaS
- Password Hashing mit bcrypt
- JWT Token Erstellung/Validierung
- Google OAuth Integration
"""
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db

# === KONFIGURATION ===
JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE-ME-IN-PRODUCTION-supersecretkey123")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# Google OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "")

# Position Limits pro Tier
TIER_LIMITS = {
    "free": 10,
    "premium": 999999  # praktisch unbegrenzt
}

# === PASSWORD HASHING ===
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hasht ein Passwort mit bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Prueft ob ein Passwort mit dem Hash uebereinstimmt"""
    return pwd_context.verify(plain_password, hashed_password)


# === JWT TOKEN ===
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def create_access_token(user: models.User) -> str:
    """Erstellt einen JWT Access Token fuer einen User"""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "tier": user.tier,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[schemas.TokenData]:
    """Dekodiert und validiert einen JWT Token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = int(payload.get("sub"))
        email = payload.get("email")
        tier = payload.get("tier", "free")
        if user_id is None or email is None:
            return None
        return schemas.TokenData(user_id=user_id, email=email, tier=tier)
    except JWTError:
        return None


# === USER OPERATIONS ===

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """Findet einen User anhand der Email"""
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_google_id(db: Session, google_id: str) -> Optional[models.User]:
    """Findet einen User anhand der Google ID"""
    return db.query(models.User).filter(models.User.google_id == google_id).first()


def create_user(db: Session, email: str, password: Optional[str] = None, google_id: Optional[str] = None) -> models.User:
    """Erstellt einen neuen User"""
    user = models.User(
        email=email,
        password_hash=hash_password(password) if password else None,
        google_id=google_id,
        tier="free"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> Optional[models.User]:
    """Authentifiziert einen User mit Email und Passwort"""
    user = get_user_by_email(db, email)
    if not user or not user.password_hash:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user


# === DEPENDENCY fuer geschuetzte Endpoints ===

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> models.User:
    """
    FastAPI Dependency: Extrahiert und validiert den User aus dem JWT Token.
    Wirft 401 wenn kein gueltiger Token vorhanden ist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Nicht authentifiziert",
        headers={"WWW-Authenticate": "Bearer"}
    )

    if not token:
        raise credentials_exception

    token_data = decode_token(token)
    if token_data is None:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == token_data.user_id).first()
    if user is None or not user.is_active:
        raise credentials_exception

    return user


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[models.User]:
    """
    Wie get_current_user, aber gibt None zurueck statt 401.
    Fuer Endpoints die optional Auth unterstuetzen.
    """
    if not token:
        return None

    token_data = decode_token(token)
    if token_data is None:
        return None

    user = db.query(models.User).filter(models.User.id == token_data.user_id).first()
    if user is None or not user.is_active:
        return None

    return user


# === TIER LIMITS ===

def check_position_limit(db: Session, user: models.User) -> bool:
    """
    Prueft ob der User sein Positionslimit erreicht hat.
    Returns True wenn noch Platz ist, False wenn Limit erreicht.
    """
    limit = TIER_LIMITS.get(user.tier, TIER_LIMITS["free"])
    count = db.query(models.Position).filter(models.Position.user_id == user.id).count()
    return count < limit


def get_positions_remaining(db: Session, user: models.User) -> int:
    """Gibt die Anzahl verbleibender Positionen zurueck"""
    limit = TIER_LIMITS.get(user.tier, TIER_LIMITS["free"])
    count = db.query(models.Position).filter(models.Position.user_id == user.id).count()
    return max(0, limit - count)
