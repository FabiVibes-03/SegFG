import secrets
import hashlib
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import settings
from database import get_db
from models import Device

bearer_scheme = HTTPBearer()


def generate_device_token() -> tuple[str, str]:
    """
    Genera un token único para un dispositivo.
    Retorna (token_plain, token_hash) — guarda solo el hash en DB.
    """
    token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return token, token_hash


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def get_device_from_token(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Device:
    """Dependency — valida el Bearer token del agente y retorna el Device."""
    token_hash = hash_token(credentials.credentials)
    result = await db.execute(select(Device).where(Device.api_token == token_hash))
    device = result.scalars().first()

    if not device:
        raise HTTPException(status_code=401, detail="Token de dispositivo inválido")

    return device


# ──────────────────────────────────────────────
# JWT para el admin del dashboard
# ──────────────────────────────────────────────

def create_admin_token() -> str:
    expire = datetime.utcnow() + timedelta(hours=12)
    return jwt.encode(
        {"sub": "admin", "exp": expire},
        settings.SECRET_KEY,
        algorithm="HS256",
    )


def verify_admin_token(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> bool:
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=["HS256"])
        if payload.get("sub") != "admin":
            raise HTTPException(status_code=401, detail="Token inválido")
        return True
    except JWTError:
        raise HTTPException(status_code=401, detail="Token expirado o inválido")