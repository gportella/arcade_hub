import { writable } from 'svelte/store';

import {
    COLOR_LABELS,
    COLORS,
    MODES,
    DEFAULT_DIFFICULTY,
    DIFFICULTY_DEPTH,
} from '../constants.js';
import {
    createEmptyBoard,
    describeTurn,
    describeVictory,
    dropPiece,
    isBoardFull,
    isWinningMove,
    listPlayableColumns,
    otherColor,
} from './logic.js';

const DEFAULT_BASE_URL = 'http://127.0.0.1:8000';

function resolveBackendBase() {
    const configured = import.meta.env.VITE_BACKEND_URL;
    if (!configured) {
        return DEFAULT_BASE_URL;
    }

    try {
        const sanitized = configured.trim();
        if (sanitized.startsWith('/')) {
            const origin =
                typeof window !== 'undefined' && window.location
                    ? window.location.origin
                    : DEFAULT_BASE_URL;
            return new URL(sanitized, origin).toString().replace(/\/$/, '');
        }
        return new URL(sanitized).toString().replace(/\/$/, '');
    } catch (error) {
        console.warn('Invalid VITE_BACKEND_URL; falling back to default', {
            configured,
            error,
        });
        return DEFAULT_BASE_URL;
    }
}

const BACKEND_BASE_URL = resolveBackendBase();

const CONNECTION_STATES = {
    DISCONNECTED: 'disconnected',
    CONNECTING: 'connecting',
    CONNECTED: 'connected',
    CLOSED: 'closed',
};

/**
 * @typedef {ReturnType<typeof createInitialState>} GameState
 */

function createInitialState(mode = MODES.SOLO, difficulty = DEFAULT_DIFFICULTY) {
    const board = createEmptyBoard();
    const playableColumns = listPlayableColumns(board);
    const resolvedDifficulty = difficulty ?? DEFAULT_DIFFICULTY;
    const aiDepth = mode === MODES.SOLO ? DIFFICULTY_DEPTH[resolvedDifficulty] : null;
    return {
        mode,
        board,
        playableColumns,
        toPlay: COLORS.YELLOW,
        lastMove: null,
        winner: null,
        draw: false,
        moveCount: 0,
        message: describeTurn(COLORS.YELLOW),
        gameId: null,
        playerId: null,
        connectionState: CONNECTION_STATES.DISCONNECTED,
        error: null,
        players: [],
        difficulty: resolvedDifficulty,
        aiDepth,
    };
}

function buildWsUrl(gameId, playerId, mode) {
    const base = new URL(BACKEND_BASE_URL);
    base.protocol = base.protocol === 'https:' ? 'wss:' : 'ws:';

    const normalizedPath = base.pathname.replace(/\/+/g, '/').replace(/\/+$/u, '')
    const prefix = normalizedPath.endsWith('/api')
        ? normalizedPath.slice(0, -4)
        : normalizedPath

    const wsPath = `${prefix}/ws/${gameId}/${playerId}`.replace(/\/+/g, '/')
    base.pathname = wsPath
    base.search = ''
    if (mode === MODES.SOLO) {
        base.searchParams.set('mode', 'solo');
    }
    return base.toString();
}

function applyRemoteMove(state, payload) {
    const column = payload.column;
    if (typeof column !== 'number') {
        return state;
    }

    const color = typeof payload.color === 'number' ? payload.color : state.toPlay;
    const result = dropPiece(state.board, column, color);
    if (!result) {
        console.warn('applyRemoteMove:drop-failed', { column, color, payload });
        return state;
    }

    const { board, row } = result;

    const winner =
        payload.winner !== undefined
            ? payload.winner
            : isWinningMove(board, row, column, color)
                ? color
                : null;
    const moveCount = payload.turnIndex ?? state.moveCount + 1;
    const playableColumns = listPlayableColumns(board);
    const draw =
        typeof payload.draw === 'boolean'
            ? payload.draw
            : !winner && isBoardFull(board);

    let message = state.message;
    let toPlay = state.toPlay;
    if (winner !== null) {
        message = describeVictory(winner);
        toPlay = color;
    } else if (draw) {
        message = 'Draw game';
        toPlay = color;
    } else {
        toPlay = otherColor(color);
        message = describeTurn(toPlay);
    }

    const nextState = {
        ...state,
        board,
        playableColumns,
        moveCount,
        lastMove: { row, column, color },
        winner,
        draw,
        toPlay,
        message,
    };

    console.debug('applyRemoteMove:state', {
        column,
        color,
        row,
        winner,
        draw,
        toPlay,
        moveCount,
        board,
    });

    return nextState;
}

function applyJoinEvent(state, payload) {
    const players = Array.from(new Set([...state.players, payload.playerId]));
    return {
        ...state,
        players,
    };
}

function applyLeaveEvent(state, payload) {
    const players = state.players.filter((id) => id !== payload.playerId);
    return {
        ...state,
        players,
    };
}

function createGameStore() {
    const initialState = createInitialState();
    const { subscribe, update, set } = writable(initialState);
    let currentState = initialState;

    subscribe((value) => {
        currentState = value;
    });

    /** @type {WebSocket | null} */
    let socket = null;

    async function startNewGame(mode, difficulty) {
        await disconnect();
        const playerId = crypto.randomUUID();
        const desiredDifficulty =
            mode === MODES.SOLO
                ? difficulty ?? currentState.difficulty ?? DEFAULT_DIFFICULTY
                : currentState.difficulty ?? DEFAULT_DIFFICULTY;

        console.debug('gameStore:startNewGame', {
            mode,
            playerId,
            difficulty: desiredDifficulty,
        });
        set({
            ...createInitialState(mode, desiredDifficulty),
            connectionState: CONNECTION_STATES.CONNECTING,
            playerId,
        });

        try {
            const payload = { mode };
            if (mode === MODES.SOLO) {
                payload.difficulty = desiredDifficulty;
            }

            const response = await fetch(`${BACKEND_BASE_URL}/games`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            if (!response.ok) {
                throw new Error(`Failed to create game: ${response.statusText}`);
            }
            const {
                game_id: gameId,
                mode: responseMode,
                difficulty: responseDifficulty,
                ai_depth: responseAiDepth,
            } = await response.json();
            console.debug('gameStore:startNewGame:created', {
                gameId,
                mode: responseMode,
                difficulty: responseDifficulty,
                aiDepth: responseAiDepth,
            });
            const resolvedDifficulty =
                responseMode === MODES.SOLO
                    ? responseDifficulty ?? desiredDifficulty
                    : desiredDifficulty;
            const resolvedAiDepth =
                responseMode === MODES.SOLO
                    ? responseAiDepth ?? DIFFICULTY_DEPTH[resolvedDifficulty]
                    : null;
            update((state) => ({
                ...state,
                mode: responseMode,
                gameId,
                difficulty: resolvedDifficulty,
                aiDepth: resolvedAiDepth,
            }));
            connect(gameId, playerId, responseMode);
        } catch (error) {
            console.error('Failed to create game', error);
            set((state) => ({
                ...state,
                connectionState: CONNECTION_STATES.DISCONNECTED,
                error: error instanceof Error ? error.message : String(error),
            }));
        }
    }

    function connect(gameId, playerId, mode) {
        const wsUrl = buildWsUrl(gameId, playerId, mode);
        socket = new WebSocket(wsUrl);
        console.debug('gameStore:connect', {
            wsUrl,
            gameId,
            playerId,
            mode,
            difficulty: currentState.difficulty,
            aiDepth: currentState.aiDepth,
        });

        socket.addEventListener('open', () => {
            console.debug('gameStore:ws:open', { gameId, playerId });
            update((state) => ({
                ...state,
                connectionState: CONNECTION_STATES.CONNECTED,
                gameId,
                playerId,
                error: null,
            }));
        });

        socket.addEventListener('message', (event) => {
            try {
                const payload = JSON.parse(event.data);
                console.debug('gameStore:ws:message', payload);
                handleServerMessage(payload);
            } catch (error) {
                console.error('Failed to parse server message', error, event.data);
            }
        });

        socket.addEventListener('close', () => {
            socket = null;
            console.debug('gameStore:ws:close', { gameId, playerId });
            update((state) => ({
                ...state,
                connectionState: CONNECTION_STATES.CLOSED,
            }));
        });

        socket.addEventListener('error', (event) => {
            console.error('WebSocket error', event);
            update((state) => ({
                ...state,
                error: 'WebSocket error occurred',
            }));
        });
    }

    function disconnect() {
        if (socket) {
            console.debug('gameStore:disconnect');
            socket.close();
            socket = null;
        }
        return Promise.resolve();
    }

    function handleServerMessage(payload) {
        if (!payload || typeof payload !== 'object') {
            return;
        }

        update((state) => {
            switch (payload.type) {
                case 'player_joined':
                    return applyJoinEvent(state, payload);
                case 'player_left':
                    return applyLeaveEvent(state, payload);
                case 'move':
                case 'ai_move':
                    return applyRemoteMove(state, payload);
                case 'error':
                    return {
                        ...state,
                        error: payload.detail ?? 'Unknown error',
                    };
                default:
                    return state;
            }
        });
    }

    function playColumn(column) {
        if (!socket || socket.readyState !== WebSocket.OPEN) {
            update((state) => ({
                ...state,
                error: 'Not connected to game server',
            }));
            return;
        }

        update((state) => ({
            ...state,
            error: null,
        }));

        console.debug('gameStore:send:move', { column });
        socket.send(
            JSON.stringify({
                type: 'move',
                column,
            }),
        );
    }

    function reset() {
        const mode = currentState.mode;
        const difficulty = currentState.difficulty;
        startNewGame(mode, difficulty).catch((error) => {
            console.error('Failed to reset game', error);
        });
    }

    return {
        subscribe,
        startNewGame,
        playColumn,
        reset,
    };
}

export const gameStore = createGameStore();

// Auto-start a solo game when the store is created.
gameStore.startNewGame(MODES.SOLO).catch((error) => {
    console.error('Failed to initialise game', error);
});

export function formatStatus(state) {
    if (state.error) {
        return state.error;
    }
    if (state.winner !== null) {
        return describeVictory(state.winner);
    }
    if (state.draw) {
        return 'Draw game';
    }
    if (state.connectionState !== CONNECTION_STATES.CONNECTED) {
        return 'Connecting…';
    }
    return describeTurn(state.toPlay);
}

export function currentPlayerName(state) {
    return COLOR_LABELS[state.toPlay];
}
