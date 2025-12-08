const DEFAULT_API_BASE = "http://localhost:8000";
const rawApiBase = import.meta.env.VITE_CHESS_API_BASE || DEFAULT_API_BASE;
const API_BASE = rawApiBase.replace(/\/?$/, "");

const rawWsBase = import.meta.env.VITE_CHESS_WS_BASE || API_BASE;
const WS_BASE = rawWsBase.replace(/\/?$/, "");

function buildJsonHeaders(token) {
    const headers = new Headers({ "Content-Type": "application/json" });
    if (token) {
        headers.set("Authorization", `Bearer ${token}`);
    }
    return headers;
}

async function handleResponse(response) {
    const text = await response.text();
    if (!response.ok) {
        let detail = text;
        try {
            const payload = JSON.parse(text);
            detail = payload.detail || payload.message || detail;
        } catch (_error) {
            /* no-op */
        }
        throw new Error(detail || `Request failed with status ${response.status}`);
    }
    if (!text) {
        return null;
    }
    try {
        return JSON.parse(text);
    } catch (_error) {
        return text;
    }
}

export async function login(username, password) {
    const formData = new URLSearchParams();
    formData.set("username", username);
    formData.set("password", password);
    const response = await fetch(`${API_BASE}/auth/token`, {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded",
        },
        body: formData,
    });
    const payload = await handleResponse(response);
    return payload.access_token;
}

export async function fetchHubOverview(token) {
    const response = await fetch(`${API_BASE}/hub`, {
        headers: buildJsonHeaders(token),
    });
    return handleResponse(response);
}

export async function fetchGameDetail(gameId, token) {
    const response = await fetch(`${API_BASE}/games/${gameId}`, {
        headers: buildJsonHeaders(token),
    });
    return handleResponse(response);
}

export async function createGame(payload, token) {
    const response = await fetch(`${API_BASE}/games`, {
        method: "POST",
        headers: buildJsonHeaders(token),
        body: JSON.stringify(payload),
    });
    return handleResponse(response);
}

export async function submitMove(gameId, payload, token) {
    const response = await fetch(`${API_BASE}/games/${gameId}/moves`, {
        method: "POST",
        headers: buildJsonHeaders(token),
        body: JSON.stringify(payload),
    });
    return handleResponse(response);
}

export async function finishGame(gameId, payload, token) {
    const response = await fetch(`${API_BASE}/games/${gameId}/finish`, {
        method: "POST",
        headers: buildJsonHeaders(token),
        body: JSON.stringify(payload),
    });
    return handleResponse(response);
}

export async function resignGame(gameId, token) {
    const response = await fetch(`${API_BASE}/games/${gameId}/resign`, {
        method: "POST",
        headers: buildJsonHeaders(token),
    });
    return handleResponse(response);
}

export async function updateUser(userId, payload, token) {
    const response = await fetch(`${API_BASE}/users/${userId}`, {
        method: "PATCH",
        headers: buildJsonHeaders(token),
        body: JSON.stringify(payload),
    });
    return handleResponse(response);
}

function buildWebSocketUrl(path) {
    const url = new URL(path, WS_BASE);
    if (url.protocol === "http:") {
        url.protocol = "ws:";
    } else if (url.protocol === "https:") {
        url.protocol = "wss:";
    }
    return url.toString();
}

export function connectToGame(gameId) {
    const url = buildWebSocketUrl(`/ws/games/${gameId}`);
    return new WebSocket(url);
}

export { API_BASE, WS_BASE };
