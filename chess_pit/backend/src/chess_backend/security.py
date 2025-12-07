"""Security helpers for password hashing and JWT token management."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import ValidationError

from .config import get_settings
from .schemas import TokenData

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    settings = get_settings()
    secret_key = settings.secret_key
    if not secret_key:
        msg = "CHESS_SECRET_KEY must be configured to issue tokens"
        raise RuntimeError(msg)

    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, secret_key, algorithm="HS256")


def parse_token(token: str) -> TokenData:
    settings = get_settings()
    secret_key = settings.secret_key
    if not secret_key:
        msg = "CHESS_SECRET_KEY must be configured to validate tokens"
        raise RuntimeError(msg)

    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        username: Optional[str] = payload.get("sub")
        token_data = TokenData(username=username)
    except (JWTError, ValidationError) as exc:  # pragma: no cover - jose raises JWTError
        msg = "Could not validate credentials"
        raise ValueError(msg) from exc
    if token_data.username is None:
        raise ValueError("Token missing subject")
    return token_data
