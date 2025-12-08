#!/usr/bin/env python3
"""Seed default users for the Chess Pit backend."""

from __future__ import annotations

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from chess_backend.config import get_settings  # noqa: E402
from chess_backend.crud.users import get_user_by_username  # noqa: E402
from chess_backend.db import init_db, session_context  # noqa: E402
from chess_backend.models import User  # noqa: E402
from chess_backend.security import hash_password, verify_password  # noqa: E402

ADMIN_USERNAME = "Guillem"
ADMIN_PASSWORD_ENV = "CHESS_ADMIN_PASSWORD"
MAX_BCRYPT_BYTES = 72
DEFAULT_USERS: list[dict[str, object]] = [
    {
        "username": "Marc",
        "password_env": "CHESS_MARC_PASSWORD",
        "fallback_password": "marcarroni",
        "is_admin": False,
    },
    {
        "username": "Emma",
        "password_env": "CHESS_EMMA_PASSWORD",
        "fallback_password": "emmapema",
        "is_admin": False,
    },
    {
        "username": "Ferran",
        "password_env": "CHESS_FERRAN_PASSWORD",
        "fallback_password": "nandopando",
        "is_admin": False,
    },
    {
        "username": "Jaume",
        "password_env": "CHESS_JAUME_PASSWORD",
        "fallback_password": "jaumeescacs",
        "is_admin": False,
    },
]


def _validate_password(*, username: str, password: str, source: str) -> str:
    encoded = password.encode("utf-8")
    if len(encoded) > MAX_BCRYPT_BYTES:
        raise ValueError(
            (
                f"Password for '{username}' provided via {source} exceeds "
                f"{MAX_BCRYPT_BYTES} bytes. "
                "Bcrypt only uses the first 72 bytes; please shorten the password and try again."
            )
        )
    return password


def _resolve_password(entry: dict[str, object]) -> str:
    env_key = entry.get("password_env")
    if isinstance(env_key, str):
        value = os.getenv(env_key)
        if value:
            return _validate_password(
                username=str(entry.get("username")),
                password=value,
                source=f"environment variable {env_key}",
            )
    fallback = entry.get("fallback_password")
    if isinstance(fallback, str) and fallback:
        return _validate_password(
            username=str(entry.get("username")),
            password=fallback,
            source="fallback password",
        )
    raise RuntimeError(f"No password available for user {entry.get('username')}")


def ensure_user(username: str, password: str, *, is_admin: bool) -> None:
    with session_context() as session:
        user = get_user_by_username(session, username)
        if user is None:
            new_user = User(
                username=username,
                hashed_password=hash_password(password),
                is_admin=is_admin,
            )
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            print(f"Created user '{username}' (admin={is_admin})")
            return

        needs_update = False
        if not verify_password(password, user.hashed_password):
            user.hashed_password = hash_password(password)
            needs_update = True
        if is_admin and not user.is_admin:
            user.is_admin = True
            needs_update = True
        if needs_update:
            session.add(user)
            session.commit()
            session.refresh(user)
            print(f"Updated user '{username}' (admin={user.is_admin})")
        else:
            print(f"User '{username}' already up to date")


def main() -> None:
    admin_password = os.getenv(ADMIN_PASSWORD_ENV)
    if not admin_password:
        print(
            f"Environment variable {ADMIN_PASSWORD_ENV} must be set before running this script.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        admin_password = _validate_password(
            username=ADMIN_USERNAME,
            password=admin_password,
            source=f"environment variable {ADMIN_PASSWORD_ENV}",
        )
    except ValueError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)

    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    init_db()
    ensure_user(ADMIN_USERNAME, admin_password, is_admin=True)

    for entry in DEFAULT_USERS:
        username = entry.get("username")
        if not isinstance(username, str):
            continue
        try:
            password = _resolve_password(entry)
        except ValueError as exc:
            print(exc, file=sys.stderr)
            sys.exit(1)
        ensure_user(username, password, is_admin=bool(entry.get("is_admin", False)))


if __name__ == "__main__":
    main()
