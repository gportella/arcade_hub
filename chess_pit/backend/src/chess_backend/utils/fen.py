"""Helpers for working with chess FEN strings."""

from __future__ import annotations

import hashlib
from typing import Optional

DEFAULT_FEN_FIELDS = 6


def normalize_fen(raw_fen: Optional[str], fallback: str) -> str:
    """Return a cleaned FEN, falling back to *fallback* when necessary."""

    if raw_fen:
        fen = raw_fen.strip()
        if fen:
            parts = fen.split()
            if len(parts) >= 2:
                if len(parts) < DEFAULT_FEN_FIELDS:
                    parts.extend(["-"] * (DEFAULT_FEN_FIELDS - len(parts)))
                return " ".join(parts[:DEFAULT_FEN_FIELDS])
    return fallback


def fen_hash(raw_fen: Optional[str]) -> Optional[str]:
    """Return a stable hash for the given FEN or ``None`` if not available."""

    if not raw_fen:
        return None
    fen = raw_fen.strip()
    if not fen:
        return None
    digest = hashlib.sha256(fen.encode("utf-8")).hexdigest()
    return digest


def active_color(raw_fen: Optional[str], *, default: str = "white") -> str:
    """Return the side to move expressed as ``"white"`` or ``"black"``."""

    if not raw_fen:
        return default
    parts = raw_fen.split()
    if len(parts) < 2:
        return default
    return "black" if parts[1] == "b" else "white"
