# Arcade Hub Landing Page

Lightweight Svelte single-page site that lists internal apps ("Unblock Me" and "Connect 4 Arena") and checks their health endpoints before advertising the links.

## Getting Started

```bash
cd landing
npm install
npm run dev -- --open
```

- The dev server runs on <http://localhost:5173> by default.
- Build static assets with `npm run build`, then preview with `npm run preview` or serve the `dist/` directory from any static host.

## Configuring Service URLs

Two services are pre-configured via environment variables (place them in `landing/.env` or `landing/.env.local`):

```bash
VITE_UNBLOCK_URL=http://localhost:9000
VITE_UNBLOCK_HEALTH=http://localhost:9000/health
VITE_CONNECT4_URL=http://localhost:8180
VITE_CONNECT4_HEALTH=http://localhost:8100/health
```

When the page loads it issues a GET request to each `*_HEALTH` endpoint. A 2xx response marks the app as _Online_; any error or timeout (4 seconds) marks it as _Offline_.

> Heads-up: the landing UI no longer displays these instructions; use this README as the source of truth when wiring up environment variables.

### Custom Service List

Optionally provide `VITE_SERVICES` with a JSON array to override the defaults:

```bash
VITE_SERVICES='[
  {"id":"unblock","name":"Unblock Me","description":"Sliding block puzzle","url":"http://unblock.local","healthUrl":"http://unblock.local/health"},
  {"id":"connect4","name":"Connect 4","description":"Multiplayer and AI modes","url":"http://connect4.local","healthUrl":"http://connect4.local/health"}
]'
```

Each object supports the following fields:

- `id` – unique identifier (string)
- `name` – display name
- `description` – brief blurb
- `url` – link target opened in a new tab
- `healthUrl` – optional health-check URL; omit to always show as online

## Deploying alongside existing containers

The landing site outputs static files, so you can serve `landing/dist` via nginx, Caddy, GitHub Pages, or any CDN.

### Docker image

This directory already includes a multi-stage Dockerfile mirroring the pattern used by the other frontends:

```bash
docker build -t arcade-landing:latest landing
docker run --rm -p 8200:80 arcade-landing:latest
```

### docker-compose service

Add a new service alongside the existing ones:

```yaml
  landing:
    build:
      context: ./landing
      dockerfile: Dockerfile
    image: arcade-landing:latest
    container_name: arcade-landing
    restart: unless-stopped
    ports:
      - "${ARCADE_LANDING_PORT:-8200}:80"
```

Health checks will still reach the backend/frontends through the URLs configured via environment variables, so no extra backend is required.
