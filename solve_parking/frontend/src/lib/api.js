const rawBase = import.meta.env.VITE_API_BASE ?? '/api'
export const API_BASE = rawBase.endsWith('/') ? rawBase.slice(0, -1) : rawBase

const SESSION_HEADER = 'X-Session-ID'
const SESSION_STORAGE_KEY = 'solveParkingSessionId'
const SESSION_ID_PATTERN = /^[A-Za-z0-9_-]{16,128}$/

const sessionListeners = new Set()

function generateSessionId() {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
        return crypto.randomUUID().replace(/-/g, '')
    }
    if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') {
        const buffer = new Uint8Array(16)
        crypto.getRandomValues(buffer)
        return Array.from(buffer, (byte) => byte.toString(16).padStart(2, '0')).join('')
    }
    return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 14)}`
}

function readStoredSessionId() {
    if (typeof window === 'undefined') {
        return null
    }
    try {
        const stored = window.sessionStorage?.getItem(SESSION_STORAGE_KEY)
        if (stored && SESSION_ID_PATTERN.test(stored)) {
            return stored
        }
    } catch (error) {
        console.warn('Failed to read stored session id', error)
    }
    return null
}

function persistSessionId(id) {
    if (typeof window === 'undefined') {
        return
    }
    try {
        window.sessionStorage?.setItem(SESSION_STORAGE_KEY, id)
    } catch (error) {
        console.warn('Failed to persist session id', error)
    }
}

function notifySessionChange(id) {
    for (const listener of sessionListeners) {
        try {
            listener(id)
        } catch (error) {
            console.error('Session listener failed', error)
        }
    }
}

let sessionId = readStoredSessionId()
if (!sessionId) {
    sessionId = generateSessionId()
    persistSessionId(sessionId)
}

export function getSessionId() {
    return sessionId
}

export function onSessionChange(callback) {
    if (typeof callback !== 'function') {
        return () => { }
    }
    sessionListeners.add(callback)
    return () => {
        sessionListeners.delete(callback)
    }
}

export function updateSessionId(id) {
    if (!id || !SESSION_ID_PATTERN.test(id) || id === sessionId) {
        return
    }
    sessionId = id
    persistSessionId(id)
    notifySessionChange(id)
}

export function isSessionReady() {
    return Boolean(sessionId)
}

export function onSessionReady(callback) {
    if (typeof callback !== 'function') {
        return () => { }
    }
    if (sessionId) {
        callback()
        return () => { }
    }
    return onSessionChange(callback)
}

async function request(path, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...(options.headers ?? {}),
        [SESSION_HEADER]: getSessionId(),
    }

    const requestInit = {
        ...options,
        headers,
        credentials: options.credentials ?? 'same-origin',
    }

    const response = await fetch(`${API_BASE}${path}`, requestInit)

    const responseSession = response.headers.get(SESSION_HEADER)
    if (responseSession) {
        updateSessionId(responseSession)
    }

    if (response.ok) {
        if (response.status === 204) {
            return null
        }
        return response.json()
    }

    let message = 'Request failed'
    try {
        const data = await response.json()
        if (data?.detail) {
            message = data.detail
        }
    } catch (error) {
        message = response.statusText || message
    }

    throw new Error(message)
}

export async function getPuzzle() {
    return request('/puzzle')
}

export async function postMove(vehicleId, steps) {
    return request('/move', {
        method: 'POST',
        body: JSON.stringify({ vehicle_id: vehicleId, steps }),
    })
}

export async function resetPuzzle() {
    return request('/reset', { method: 'POST' })
}

export async function solvePuzzle() {
    return request('/solve', { method: 'POST' })
}

export async function putPuzzle(state) {
    return request('/puzzle', {
        method: 'PUT',
        body: JSON.stringify(state),
    })
}

export async function savePuzzleConfig(payload) {
    return request('/configs', {
        method: 'POST',
        body: JSON.stringify(payload),
    })
}

export async function updatePuzzleConfig(id, payload) {
    return request(`/configs/${id}`, {
        method: 'PUT',
        body: JSON.stringify(payload),
    })
}

export async function listPuzzleConfigs() {
    return request('/configs')
}

export async function getPuzzleConfig(id) {
    return request(`/configs/${id}`)
}

export async function activatePuzzleConfig(id) {
    return request(`/configs/${id}/activate`, { method: 'POST' })
}

export async function deletePuzzleConfig(id) {
    return request(`/configs/${id}`, { method: 'DELETE' })
}
