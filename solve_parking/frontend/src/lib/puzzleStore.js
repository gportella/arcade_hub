import { get, writable } from 'svelte/store'
import {
    API_BASE,
    activatePuzzleConfig as activatePuzzleConfigApi,
    deletePuzzleConfig as deletePuzzleConfigApi,
    getSessionId,
    getPuzzle,
    getPuzzleConfig as getPuzzleConfigApi,
    isSessionReady,
    listPuzzleConfigs,
    onSessionChange,
    onSessionReady,
    postMove,
    putPuzzle as putPuzzleApi,
    resetPuzzle as resetPuzzleApi,
    savePuzzleConfig as savePuzzleConfigApi,
    solvePuzzle as solvePuzzleApi,
    updatePuzzleConfig as updatePuzzleConfigApi,
} from './api'
import { clonePuzzle } from './defaultPuzzle'
import { applyMove as applyMoveLocally, isSolved as isPuzzleSolved } from './puzzleLogic'

const defaultState = clonePuzzle()

export const puzzle = writable(defaultState)
export const completed = writable(false)
export const loading = writable(false)
export const lastError = writable(null)
export const notice = writable(null)
export const offlineMode = writable(true)
export const backendEnabled = writable(true)
export const realtimeConnected = writable(false)

let realtimeSocket = null
let reconnectTimer = null

const SOCKET_RECONNECT_DELAY = 3000
const SOLUTION_FRAME_DELAY_MS = 550

if (typeof window !== 'undefined') {
    onSessionReady(() => {
        if (get(backendEnabled)) {
            refreshRealtimeConnection()
        }
    })

    onSessionChange(() => {
        if (get(backendEnabled)) {
            refreshRealtimeConnection()
        }
    })
}

function markBackendHealthy() {
    realtimeConnected.set(true)
    offlineMode.set(false)
    if (get(notice) === 'Connection lost. Retrying…') {
        notice.set(null)
    }
}

function enterOfflineMode() {
    if (get(backendEnabled)) {
        backendEnabled.set(false)
    }
    offlineMode.set(true)
    realtimeConnected.set(false)
    closeRealtime()
}

export const solutionPath = writable([])
export const solutionStep = writable(0)
export const solutionAnimating = writable(false)

export function clearSolutionPath() {
    solutionPath.set([])
    solutionStep.set(0)
    solutionAnimating.set(false)
}

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms))
}

function statesEqual(left, right) {
    if (!left || !right) {
        return false
    }
    return JSON.stringify(left) === JSON.stringify(right)
}

function formatElapsedTime(ms) {
    if (typeof ms !== 'number' || Number.isNaN(ms) || !Number.isFinite(ms) || ms < 0) {
        return null
    }
    if (ms >= 1000) {
        const seconds = ms / 1000
        const precision = seconds >= 10 ? 0 : 1
        return `${seconds.toFixed(precision)} s`
    }
    return `${Math.round(ms)} ms`
}

async function playSolutionPath(path) {
    if (!Array.isArray(path) || path.length === 0) {
        clearSolutionPath()
        return get(puzzle)
    }

    const current = get(puzzle)
    const frames = path.slice()

    if (frames.length === 0 || !statesEqual(frames[0], current)) {
        frames.unshift(JSON.parse(JSON.stringify(current)))
    }

    solutionPath.set(frames)
    solutionStep.set(0)
    solutionAnimating.set(true)

    let startIndex = frames.length > 0 && statesEqual(frames[0], current) ? 1 : 0

    let lastState = current
    for (let index = startIndex; index < frames.length; index += 1) {
        if (!get(solutionAnimating)) {
            break
        }
        const frame = frames[index]
        puzzle.set(frame)
        completed.set(isPuzzleSolved(frame))
        lastState = frame
        solutionStep.set(index)

        const isLast = index === frames.length - 1
        if (!isLast) {
            await sleep(SOLUTION_FRAME_DELAY_MS)
            if (!get(solutionAnimating)) {
                break
            }
        }
    }

    solutionAnimating.set(false)
    return lastState
}

export function showSolutionStep(index) {
    const path = get(solutionPath)
    if (!Array.isArray(path) || path.length === 0) {
        return
    }

    solutionAnimating.set(false)
    const clampedIndex = Math.min(Math.max(index, 0), path.length - 1)
    puzzle.set(path[clampedIndex])
    completed.set(isPuzzleSolved(path[clampedIndex]))
    solutionStep.set(clampedIndex)
}

export function stepSolution(delta) {
    const path = get(solutionPath)
    if (!Array.isArray(path) || path.length === 0) {
        return
    }

    solutionAnimating.set(false)
    const nextIndex = get(solutionStep) + delta
    showSolutionStep(nextIndex)
}

async function withLoading(action) {
    loading.set(true)
    try {
        return await action()
    } finally {
        loading.set(false)
    }
}

function fallbackToDefault(message) {
    const state = clonePuzzle()
    puzzle.set(state)
    completed.set(false)
    offlineMode.set(true)
    clearSolutionPath()
    if (message) {
        notice.set(message)
    }
    return state
}

function resolveWebSocketUrl() {
    if (typeof window === 'undefined') {
        return null
    }

    const socketPath = '/ws/state'
    const sessionId = getSessionId()
    const query = sessionId ? `session=${encodeURIComponent(sessionId)}` : null

    if (API_BASE.startsWith('http')) {
        const url = new URL(API_BASE, window.location.origin)
        url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
        url.pathname = url.pathname.replace(/\/+$/, '')
        if (url.pathname.endsWith('/api')) {
            url.pathname = url.pathname.slice(0, -4)
        }
        url.pathname = `${url.pathname}${socketPath}`.replace(/\/+/g, '/')
        url.search = ''
        if (query) {
            url.search = `?${query}`
        }
        url.hash = ''
        return url.toString()
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    let basePath = API_BASE.replace(/\/+$/, '')
    if (basePath.endsWith('/api')) {
        basePath = basePath.slice(0, -4)
    }
    const path = `${basePath}${socketPath}`.replace(/\/+/g, '/')
    const fullPath = path.startsWith('/') ? path : `/${path}`
    const suffix = query ? `?${query}` : ''
    return `${protocol}//${host}${fullPath}${suffix}`
}

function clearReconnectTimer() {
    if (reconnectTimer) {
        clearTimeout(reconnectTimer)
        reconnectTimer = null
    }
}

function scheduleReconnect() {
    if (reconnectTimer || !get(backendEnabled)) {
        return
    }
    reconnectTimer = setTimeout(() => {
        reconnectTimer = null
        ensureRealtimeConnection()
    }, SOCKET_RECONNECT_DELAY)
}

function closeRealtime() {
    if (realtimeSocket) {
        realtimeSocket.onopen = null
        realtimeSocket.onmessage = null
        realtimeSocket.onerror = null
        realtimeSocket.onclose = null
        try {
            realtimeSocket.close()
        } catch (error) {
            // ignore closing errors
        }
        realtimeSocket = null
    }
    clearReconnectTimer()
}

function handleRealtimeMessage(event) {
    try {
        const payload = JSON.parse(event.data)
        if (payload?.type !== 'state' || !payload.state) {
            return
        }
        puzzle.set(payload.state)
        completed.set(Boolean(payload.completed))
        markBackendHealthy()
        lastError.set(null)
        if (get(notice)) {
            notice.set(null)
        }
    } catch (error) {
        console.error('Failed to parse realtime update', error)
    }
}

function ensureRealtimeConnection() {
    if (typeof window === 'undefined' || realtimeSocket || !get(backendEnabled)) {
        return
    }

    if (!isSessionReady()) {
        return
    }

    const url = resolveWebSocketUrl()
    if (!url) {
        return
    }

    closeRealtime()
    const socket = new WebSocket(url)
    realtimeSocket = socket

    socket.onopen = () => {
        clearReconnectTimer()
        markBackendHealthy()
        lastError.set(null)
        if (get(notice)) {
            notice.set(null)
        }
    }

    socket.onmessage = handleRealtimeMessage

    socket.onerror = () => {
        socket.close()
    }

    socket.onclose = () => {
        realtimeSocket = null
        if (get(backendEnabled)) {
            notice.set('Connection lost. Retrying…')
            scheduleReconnect()
        }
    }
}

export async function loadPuzzle() {
    lastError.set(null)
    notice.set(null)
    return withLoading(async () => {
        if (!get(backendEnabled)) {
            return fallbackToDefault('Backend disabled. Showing default puzzle.')
        }
        ensureRealtimeConnection()
        try {
            const state = await getPuzzle()
            puzzle.set(state)
            completed.set(false)
            markBackendHealthy()
            notice.set(null)
            clearSolutionPath()
            return state
        } catch (error) {
            if (error instanceof TypeError) {
                const fallbackState = fallbackToDefault('Backend unreachable. Showing default puzzle.')
                enterOfflineMode()
                return fallbackState
            }
            const fallbackState = fallbackToDefault(null)
            lastError.set(error instanceof Error ? error.message : 'Failed to load puzzle.')
            scheduleReconnect()
            return fallbackState
        }
    })
}

export async function moveVehicle(vehicleId, steps) {
    return withLoading(async () => {
        if (!get(backendEnabled)) {
            const current = get(puzzle)
            const result = applyMoveLocally(current, { vehicleId, steps })
            puzzle.set(result.state)
            completed.set(result.completed)
            offlineMode.set(true)
            lastError.set(null)
            notice.set('Backend disabled: applying move locally.')
            return result
        }
        ensureRealtimeConnection()
        try {
            const payload = await postMove(vehicleId, steps)
            puzzle.set(payload.state)
            completed.set(payload.completed)
            markBackendHealthy()
            lastError.set(null)
            notice.set(null)
            clearSolutionPath()
            return payload
        } catch (error) {
            const networkFailure = error instanceof TypeError
            if (networkFailure) {
                enterOfflineMode()
            }
            if (networkFailure || !get(backendEnabled)) {
                try {
                    const current = get(puzzle)
                    const result = applyMoveLocally(current, { vehicleId, steps })
                    puzzle.set(result.state)
                    completed.set(result.completed)
                    offlineMode.set(true)
                    lastError.set(null)
                    notice.set('Offline mode: using local puzzle logic.')
                    clearSolutionPath()
                    return result
                } catch (moveError) {
                    lastError.set(moveError instanceof Error ? moveError.message : 'Move failed')
                    throw moveError
                }
            }

            lastError.set(error instanceof Error ? error.message : 'Move failed')
            scheduleReconnect()
            throw error
        }
    })
}

export async function resetPuzzle() {
    lastError.set(null)
    notice.set(null)
    return withLoading(async () => {
        if (!get(backendEnabled)) {
            return fallbackToDefault('Backend disabled. Resetting to default puzzle.')
        }
        ensureRealtimeConnection()
        try {
            const state = await resetPuzzleApi()
            puzzle.set(state)
            completed.set(false)
            markBackendHealthy()
            notice.set(null)
            clearSolutionPath()
            return state
        } catch (error) {
            if (error instanceof TypeError) {
                const fallbackState = fallbackToDefault('Backend unreachable. Resetting to default puzzle.')
                enterOfflineMode()
                return fallbackState
            }
            const fallbackState = fallbackToDefault(null)
            lastError.set(error instanceof Error ? error.message : 'Failed to reset puzzle.')
            scheduleReconnect()
            return fallbackState
        }
    })
}

export async function solvePuzzle() {
    lastError.set(null)
    notice.set(null)
    return withLoading(async () => {
        if (!get(backendEnabled)) {
            notice.set('Backend disabled. Cannot run solver.')
            return get(puzzle)
        }
        ensureRealtimeConnection()
        try {
            solutionAnimating.set(false)
            const payload = await solvePuzzleApi()
            markBackendHealthy()
            let finalState = payload.state
            if (Array.isArray(payload.path) && payload.path.length > 0) {
                finalState = await playSolutionPath(payload.path)
            } else {
                clearSolutionPath()
                puzzle.set(finalState)
                completed.set(payload.completed)
            }

            puzzle.set(finalState)
            const solved = isPuzzleSolved(finalState)
            completed.set(solved)

            const elapsed = formatElapsedTime(payload.elapsed_ms)
            if (solved && typeof payload.moves === 'number') {
                let message = `Solved in ${payload.moves} moves`
                if (elapsed) {
                    message += ` (${elapsed})`
                }
                notice.set(message)
            } else if (solved) {
                notice.set(elapsed ? `Solved (${elapsed})` : 'Solved.')
            } else {
                const message = elapsed
                    ? `Solver did not complete within the limit (ran ${elapsed}).`
                    : 'Solver did not complete within the limit.'
                notice.set(message)
            }

            return finalState
        } catch (error) {
            if (error instanceof TypeError) {
                enterOfflineMode()
                const message = 'Backend unreachable. Cannot run solver.'
                lastError.set(message)
                notice.set(message)
                throw error
            }
            const message = error instanceof Error ? error.message : 'Solver failed'
            lastError.set(message)
            scheduleReconnect()
            throw error
        }
    })
}

export function useDefaultPuzzle() {
    lastError.set(null)
    notice.set(null)
    return fallbackToDefault()
}

export async function replacePuzzleState(state) {
    lastError.set(null)
    return withLoading(async () => {
        if (!get(backendEnabled)) {
            throw new Error('Backend disabled. Cannot replace puzzle state.')
        }
        ensureRealtimeConnection()
        try {
            const payload = await putPuzzleApi(state)
            puzzle.set(payload.state)
            completed.set(payload.completed)
            markBackendHealthy()
            notice.set(null)
            clearSolutionPath()
            return payload.state
        } catch (error) {
            const networkFailure = error instanceof TypeError
            if (networkFailure) {
                enterOfflineMode()
            } else {
                scheduleReconnect()
            }
            lastError.set(error instanceof Error ? error.message : 'Failed to update puzzle.')
            throw error
        }
    })
}

export async function savePuzzleConfiguration({ name, state, activate = true }) {
    lastError.set(null)
    notice.set(null)
    return withLoading(async () => {
        if (!get(backendEnabled)) {
            throw new Error('Backend disabled. Cannot save puzzle configuration.')
        }
        ensureRealtimeConnection()
        try {
            const payload = await savePuzzleConfigApi({ name, state, activate })
            markBackendHealthy()
            if (payload.active) {
                puzzle.set(payload.state)
                completed.set(isPuzzleSolved(payload.state))
                clearSolutionPath()
            }
            const message = activate
                ? `Activated puzzle "${payload.name}"`
                : `Saved puzzle "${payload.name}"`
            notice.set(message)
            return payload
        } catch (error) {
            const networkFailure = error instanceof TypeError
            if (networkFailure) {
                enterOfflineMode()
            } else {
                scheduleReconnect()
            }
            lastError.set(error instanceof Error ? error.message : 'Failed to save puzzle.')
            throw error
        }
    })
}

export async function updatePuzzleConfiguration({ id, name, state, activate = null }) {
    if (!id) {
        throw new Error('Configuration id is required to update a puzzle.')
    }
    lastError.set(null)
    notice.set(null)
    return withLoading(async () => {
        if (!get(backendEnabled)) {
            throw new Error('Backend disabled. Cannot update puzzle configuration.')
        }
        ensureRealtimeConnection()
        try {
            const payload = await updatePuzzleConfigApi(id, { name, state, activate })
            markBackendHealthy()
            if (payload.active) {
                puzzle.set(payload.state)
                completed.set(isPuzzleSolved(payload.state))
                clearSolutionPath()
            }
            let message = `Updated puzzle "${payload.name}"`
            if (activate === true) {
                message = `Updated and activated puzzle "${payload.name}"`
            } else if (activate === false) {
                message = `Updated puzzle "${payload.name}" (not active)`
            }
            notice.set(message)
            return payload
        } catch (error) {
            const networkFailure = error instanceof TypeError
            if (networkFailure) {
                enterOfflineMode()
            } else {
                scheduleReconnect()
            }
            lastError.set(error instanceof Error ? error.message : 'Failed to update puzzle.')
            throw error
        }
    })
}

export async function deletePuzzleConfiguration(id) {
    if (!id) {
        throw new Error('Configuration id is required to delete a puzzle.')
    }
    lastError.set(null)
    notice.set(null)
    return withLoading(async () => {
        if (!get(backendEnabled)) {
            throw new Error('Backend disabled. Cannot delete puzzle configuration.')
        }
        ensureRealtimeConnection()
        try {
            const payload = await deletePuzzleConfigApi(id)
            markBackendHealthy()
            if (payload?.state) {
                puzzle.set(payload.state)
                completed.set(Boolean(payload.completed))
                clearSolutionPath()
            }
            let message = 'Deleted puzzle configuration.'
            if (payload?.removed_name) {
                message = `Deleted puzzle "${payload.removed_name}".`
            }
            if (payload?.activated_name) {
                message = `${message} Active puzzle: "${payload.activated_name}".`
            }
            notice.set(message)
            return payload
        } catch (error) {
            const networkFailure = error instanceof TypeError
            if (networkFailure) {
                enterOfflineMode()
            } else {
                scheduleReconnect()
            }
            lastError.set(
                error instanceof Error ? error.message : 'Failed to delete puzzle.'
            )
            throw error
        }
    })
}

export async function fetchPuzzleConfigurations() {
    if (!get(backendEnabled)) {
        throw new Error('Backend disabled. Cannot load puzzle configurations.')
    }
    ensureRealtimeConnection()
    try {
        const records = await listPuzzleConfigs()
        markBackendHealthy()
        return records
    } catch (error) {
        if (error instanceof TypeError) {
            enterOfflineMode()
        }
        throw error
    }
}

export async function fetchPuzzleConfiguration(id) {
    if (!get(backendEnabled)) {
        throw new Error('Backend disabled. Cannot load puzzle configurations.')
    }
    ensureRealtimeConnection()
    try {
        const record = await getPuzzleConfigApi(id)
        markBackendHealthy()
        return record
    } catch (error) {
        if (error instanceof TypeError) {
            enterOfflineMode()
            throw error
        }
        throw error
    }
}

export async function activatePuzzleConfiguration(id) {
    lastError.set(null)
    notice.set(null)
    return withLoading(async () => {
        if (!get(backendEnabled)) {
            throw new Error('Backend disabled. Cannot activate configuration.')
        }
        ensureRealtimeConnection()
        try {
            const payload = await activatePuzzleConfigApi(id)
            puzzle.set(payload.state)
            completed.set(isPuzzleSolved(payload.state))
            markBackendHealthy()
            clearSolutionPath()
            notice.set(`Activated puzzle "${payload.name}"`)
            return payload
        } catch (error) {
            const networkFailure = error instanceof TypeError
            if (networkFailure) {
                enterOfflineMode()
            } else {
                scheduleReconnect()
            }
            lastError.set(error instanceof Error ? error.message : 'Failed to activate puzzle.')
            throw error
        }
    })
}

export async function setBackendEnabled(value) {
    backendEnabled.set(value)
    if (!value) {
        realtimeConnected.set(false)
        closeRealtime()
        fallbackToDefault('Backend disabled. Showing default puzzle.')
        return
    }
    refreshRealtimeConnection()
    await loadPuzzle()
}

export function refreshRealtimeConnection() {
    closeRealtime()
    ensureRealtimeConnection()
}
