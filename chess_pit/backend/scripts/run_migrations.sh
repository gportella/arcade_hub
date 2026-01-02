#!/usr/bin/env bash
# Run every Alembic migration for the Chess Pit backend.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${BACKEND_ROOT}"

echo "[migrate] Running alembic upgrade head from ${BACKEND_ROOT}" >&2
poetry run alembic upgrade head

echo "[migrate] Database schema is up to date." >&2
