# Arcade Hub Deployment

This repository bundles multiple mini-projects (Connect4, Solve Parking, and a landing page) into a single Docker Compose stack. Traefik fronts the stack so you can expose a single address via Tailscale while routing traffic to each app.

## Prerequisites

- Podman or Docker installed.
- `podman-compose` (or Docker Compose) available on your PATH.
- Tailscale installed and authenticated on the host.
- Host directories for data persistence:
  - `/home/guillem/container_services/connect_4/data`
  - `/home/guillem/container_services/solve_parking/puzzle_data`

Create the directories if they don't exist:

```sh
sudo mkdir -p /home/guillem/container_services/connect_4/data
sudo mkdir -p /home/guillem/container_services/solve_parking/puzzle_data
sudo chown -R "$(whoami)" /home/guillem/container_services
```

## Build and Run (with Podman)

From the repository root:

```sh
podman compose build
podman compose up -d
```

The `build` step compiles all frontend assets and builds the Python backends. The `up -d` command starts the stack and keeps it running in the background.

If you prefer a single command:

```sh
podman compose up --build -d
```

(Replace `podman compose` with `podman-compose` or `docker compose` if that's what you have installed.)

## Traffic Layout

Traefik terminates on:

- HTTP: `http://<host>:80`
- HTTPS: `https://<host>:443`

Routing rules:

- `/` -> Landing page
- `/connect4` -> Connect4 frontend (proxying its API/WebSocket calls to the Connect4 backend)
- `/solve-parking` -> Solve Parking frontend (proxying API/WebSocket calls to its backend)

Each frontend remains unaware of the path prefix thanks to Traefik strip-prefix middlewares.

## Tailscale Exposure

Use `tailscale serve` (or Tailscale Funnel) to expose the local Traefik entrypoints:

```sh
# Expose HTTP on your tailnet (TLS handled by the client or Traefik)
tailscale serve http 80 http://127.0.0.1:80

# Optional: expose HTTPS with Tailscale-managed TLS
# (requires Tailscale HTTPS support / Funnel)
tailscale serve https 443 https://127.0.0.1:443
```

Tailscale assigns you a stable HTTPS URL matching your tailnet. Users hitting that URL land on the Traefik landing page and can navigate to the apps via the `/connect4` and `/solve-parking` paths.

## Updating the Stack

After code changes, rebuild and restart:

```sh
podman compose up --build -d
```

To stop everything:

```sh
podman compose down
```

Logs for a specific service:

```sh
podman compose logs -f connect4-backend
```

## Notes

- Ensure each frontend is built with the correct base path (e.g. Vite `base` set to `/connect4/` or `/solve-parking/`).
- If you need additional apps, copy the per-app pattern in `docker-compose.yml` (private network + strip-prefix router).
- For TLS termination directly in Traefik, add certificate configuration or enable its automatic cert resolvers.
