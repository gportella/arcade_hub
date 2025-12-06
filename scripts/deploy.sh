#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$PROJECT_ROOT"

echo "[deploy] Pulling latest changes..."
git pull --ff-only

echo "[deploy] Bringing down current stack..."
sudo podman-compose down || true

echo "[deploy] Building images..."
sudo podman-compose build

echo "[deploy] Disabling Tailscale funnel on port 80..."
sudo tailscale funnel --stop 80 || sudo tailscale funnel off || true

echo "[deploy] Starting stack..."
sudo podman-compose up -d

echo "[deploy] Re-enabling Tailscale funnel..."
sudo tailscale funnel --bg 80

echo "[deploy] Done."