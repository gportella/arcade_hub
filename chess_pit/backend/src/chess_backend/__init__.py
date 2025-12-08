"""Chess Pit backend package."""

from __future__ import annotations

try:  # pragma: no cover - defensive shim for older passlib
    import bcrypt

    if not hasattr(bcrypt, "__about__"):

        class _BcryptAbout:  # pylint: disable=too-few-public-methods
            __version__ = getattr(bcrypt, "__version__", "unknown")

        bcrypt.__about__ = _BcryptAbout()  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001 - best effort compat layer
    pass

__all__ = ["__version__"]

__version__ = "0.1.0"
