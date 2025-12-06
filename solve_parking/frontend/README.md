# Solve Parking UI

Svelte single-page interface for the Solve Parking puzzle. The UI renders a 6x6 grid, vehicles, and move controls. It can operate in two modes:

- **Offline/local mode** – default when the Python backend is not running. The app seeds a starter puzzle and uses in-browser logic to validate moves.
- **API-backed mode** – when the FastAPI server is reachable via `/api`, all state mutations are delegated to the backend.

## Scripts

```bash
npm install        # install dependencies
npm run dev -- --host
npm run build
npm run preview
```

During development the Vite dev server proxies `/api` requests to `http://127.0.0.1:8000`.

## Local Puzzle Logic

- Initial state lives in `src/lib/defaultPuzzle.js`.
- Move validation mirrors the backend rules (`src/lib/puzzleLogic.js`).
- The Svelte store (`src/lib/puzzleStore.js`) falls back to the local solver when network requests fail, displaying a notice while still allowing play.

## Files of Interest

- `src/App.svelte` — main layout, controls, and status messaging.
- `src/components/Grid.svelte` — grid rendering + selection handling.
- `src/components/Vehicle.svelte` — individual vehicle visuals.
- `src/lib/puzzleStore.js` — state management, API integration, and offline mode.
