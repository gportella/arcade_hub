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
const COLOR_NAME_TO_VALUE = {
    yellow: COLORS.YELLOW,
    red: COLORS.RED,
};

function updateGameQueryParam(gameId) {
    if (typeof window === 'undefined') {
        return null;
    }
    const url = new URL(window.location.href);
    if (gameId) {
        url.searchParams.set('game', gameId);
    } else {
        url.searchParams.delete('game');
    }
    window.history.replaceState({}, '', url.toString());
    return url.toString();
}

function buildShareUrl(gameId) {
    if (typeof window === 'undefined') {
        return '';
    }
    const url = new URL(window.location.href);
    if (gameId) {
        url.searchParams.set('game', gameId);
    } else {
        url.searchParams.delete('game');
    }
    return url.toString();
}

function getGameIdFromUrl() {
    if (typeof window === 'undefined') {
        return null;
    }
    const url = new URL(window.location.href);
    const value = url.searchParams.get('game');
    if (!value) {
        return null;
    }
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
}

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
    const initialMessage =
        mode === MODES.MULTIPLAYER
            ? 'Waiting for another player…'
            : describeTurn(COLORS.YELLOW);
    return {
        mode,
        board,
        playableColumns,
        toPlay: COLORS.YELLOW,
        lastMove: null,
        winner: null,
        draw: false,
        moveCount: 0,
        message: initialMessage,
        gameId: null,
        playerId: null,
        connectionState: CONNECTION_STATES.DISCONNECTED,
        error: null,
        players: [],
        playerColors: {},
        localColor: null,
        localColorValue: null,
        shareUrl: null,
        difficulty: resolvedDifficulty,
        aiDepth,
        lobbyGames: [],
        lobbyLoading: false,
        lobbyError: null,
        sessionReady: false,
        hadOpponent: false,
        opponentDisconnected: false,
        rematchPending: false,
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
    const playerColors = { ...state.playerColors };
    const colorName =
        typeof payload.color === 'string' && payload.color.length > 0
            ? payload.color
            : null;
    if (colorName) {
        playerColors[payload.playerId] = colorName;
    }
    const localColor =
        payload.playerId === state.playerId && colorName ? colorName : state.localColor;
    const localColorValue =
        payload.playerId === state.playerId && colorName
            ? COLOR_NAME_TO_VALUE[colorName.toLowerCase()] ?? state.localColorValue
            : state.localColorValue;
    const hadOpponent = state.hadOpponent || players.length >= 2;
    const opponentDisconnected = players.length >= 2 ? false : state.opponentDisconnected;
    return {
        ...state,
        players,
        playerColors,
        localColor,
        localColorValue,
        hadOpponent,
        opponentDisconnected,
    };
}

function applyLeaveEvent(state, payload) {
    const players = state.players.filter((id) => id !== payload.playerId);
    const playerColors = { ...state.playerColors };
    delete playerColors[payload.playerId];
    const localColor =
        payload.playerId === state.playerId ? null : state.localColor;
    const localColorValue =
        payload.playerId === state.playerId ? null : state.localColorValue;
    const previouslyHadOpponent = state.hadOpponent || state.players.length >= 2;
    const hadOpponent = state.hadOpponent || previouslyHadOpponent;
    const opponentDisconnected =
        hadOpponent && payload.playerId !== state.playerId && players.length < 2;
    return {
        ...state,
        players,
        playerColors,
        localColor,
        localColorValue,
        hadOpponent,
        opponentDisconnected,
    };
}

function applySessionState(state, payload) {
    const players = Array.isArray(payload.players)
        ? payload.players
        : state.players;
    const colorsPayload = payload.colors ?? {};
    const playerColors = { ...state.playerColors };
    for (const [playerId, colorName] of Object.entries(colorsPayload)) {
        playerColors[playerId] = colorName;
    }
    let localColor = state.localColor;
    if (state.playerId && colorsPayload[state.playerId]) {
        localColor = colorsPayload[state.playerId];
    }
    const localColorValue =
        localColor && typeof localColor === 'string'
            ? COLOR_NAME_TO_VALUE[localColor.toLowerCase()] ?? null
            : state.localColorValue;

    let toPlay = state.toPlay;
    if (typeof payload.currentTurn === 'string') {
        const colorValue = COLOR_NAME_TO_VALUE[payload.currentTurn.toLowerCase()];
        if (colorValue !== undefined) {
            toPlay = colorValue;
        }
    }

    const waitingForOpponent =
        state.mode === MODES.MULTIPLAYER && players.length < 2;
    const hadOpponent = state.hadOpponent || players.length >= 2;
    const opponentDisconnected =
        state.mode === MODES.MULTIPLAYER && hadOpponent && players.length < 2;
    const message = waitingForOpponent ? 'Waiting for another player…' : describeTurn(toPlay);

    return {
        ...state,
        players,
        playerColors,
        localColor,
        localColorValue,
        toPlay,
        message,
        sessionReady: true,
        error: null,
        hadOpponent,
        opponentDisconnected,
        rematchPending: false,
    };
}

function applyRematch(state, payload) {
    const colorName =
        typeof payload.startingColor === 'string'
            ? payload.startingColor.toLowerCase()
            : 'yellow';
    const startingColor = COLOR_NAME_TO_VALUE[colorName] ?? COLORS.YELLOW;
    const board = createEmptyBoard();
    const playableColumns = listPlayableColumns(board);
    const hadOpponent =
        state.hadOpponent ||
        (Array.isArray(state.players) ? state.players.length >= 2 : false);

    return {
        ...state,
        board,
        playableColumns,
        toPlay: startingColor,
        lastMove: null,
        winner: null,
        draw: false,
        moveCount: 0,
        message: describeTurn(startingColor),
        sessionReady: false,
        error: null,
        opponentDisconnected: false,
        hadOpponent,
        rematchPending: false,
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

    async function startNewGame(mode, difficulty, options = {}) {
        const { reuseGameId = false, existingGameId = null, playerIdOverride = null } =
            options;
        await disconnect();
        const playerId = playerIdOverride ?? crypto.randomUUID();
        const desiredDifficulty =
            mode === MODES.SOLO
                ? difficulty ?? currentState.difficulty ?? DEFAULT_DIFFICULTY
                : currentState.difficulty ?? DEFAULT_DIFFICULTY;

        console.debug('gameStore:startNewGame', {
            mode,
            playerId,
            difficulty: desiredDifficulty,
        });
        if (!reuseGameId) {
            set({
                ...createInitialState(mode, desiredDifficulty),
                connectionState: CONNECTION_STATES.CONNECTING,
                playerId,
                lobbyGames: currentState.lobbyGames,
                lobbyLoading: currentState.lobbyLoading,
                lobbyError: currentState.lobbyError,
                rematchPending: false,
            });
        }

        try {
            const payload = { mode };
            if (mode === MODES.SOLO) {
                payload.difficulty = desiredDifficulty;
            }

            let response;
            if (reuseGameId && existingGameId) {
                response = await fetch(`${BACKEND_BASE_URL}/games/${existingGameId}`);
                if (response.status === 404) {
                    // fall back to creating a brand-new game if the session vanished
                    response = null;
                }
            }

            if (!response) {
                response = await fetch(`${BACKEND_BASE_URL}/games`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
            }
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
            const shareUrl =
                responseMode === MODES.MULTIPLAYER
                    ? reuseGameId && existingGameId
                        ? buildShareUrl(existingGameId)
                        : updateGameQueryParam(gameId)
                    : updateGameQueryParam(null);
            update((state) => ({
                ...state,
                mode: responseMode,
                gameId,
                difficulty: resolvedDifficulty,
                aiDepth: resolvedAiDepth,
                shareUrl,
                playerColors: {},
                localColor: null,
                localColorValue: null,
                sessionReady: false,
                hadOpponent: false,
                opponentDisconnected: false,
                rematchPending: false,
            }));
            connect(gameId, playerId, responseMode);
            refreshLobby().catch((refreshError) => {
                console.debug('gameStore:startNewGame:lobby-refresh-failed', refreshError);
            });
        } catch (error) {
            console.error('Failed to create game', error);
            set((state) => ({
                ...state,
                connectionState: CONNECTION_STATES.DISCONNECTED,
                error: error instanceof Error ? error.message : String(error),
                opponentDisconnected: false,
                hadOpponent: false,
                rematchPending: false,
            }));
        }
    }

    async function joinGame(gameId) {
        if (!gameId) {
            return;
        }
        await disconnect();
        const playerId = crypto.randomUUID();
        set({
            ...createInitialState(MODES.MULTIPLAYER, currentState.difficulty),
            connectionState: CONNECTION_STATES.CONNECTING,
            playerId,
            gameId,
            lobbyGames: currentState.lobbyGames,
            lobbyLoading: currentState.lobbyLoading,
            lobbyError: currentState.lobbyError,
        });

        try {
            const response = await fetch(`${BACKEND_BASE_URL}/games/${gameId}`);
            if (!response.ok) {
                throw new Error(
                    response.status === 404
                        ? 'Game not found'
                        : `Failed to join game: ${response.statusText}`,
                );
            }
            const details = await response.json();
            if (details.mode !== MODES.MULTIPLAYER) {
                throw new Error('Requested game is not running in multiplayer mode');
            }

            const shareUrl = updateGameQueryParam(gameId);

            update((state) => ({
                ...state,
                mode: MODES.MULTIPLAYER,
                gameId,
                difficulty: state.difficulty,
                aiDepth: null,
                shareUrl,
                sessionReady: false,
                hadOpponent: state.hadOpponent,
                opponentDisconnected: false,
                rematchPending: false,
            }));

            connect(gameId, playerId, MODES.MULTIPLAYER);
            refreshLobby().catch((refreshError) => {
                console.debug('gameStore:joinGame:lobby-refresh-failed', refreshError);
            });
        } catch (error) {
            console.error('Failed to join game', error);
            set((state) => ({
                ...state,
                connectionState: CONNECTION_STATES.DISCONNECTED,
                error: error instanceof Error ? error.message : String(error),
                shareUrl: buildShareUrl(gameId),
                opponentDisconnected: false,
                rematchPending: false,
            }));
            refreshLobby().catch((refreshError) => {
                console.debug('gameStore:joinGame:lobby-refresh-failed', refreshError);
            });
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
                sessionReady: false,
                opponentDisconnected: false,
                rematchPending: state.rematchPending,
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
                sessionReady: false,
                rematchPending: false,
            }));
        });

        socket.addEventListener('error', (event) => {
            console.error('WebSocket error', event);
            update((state) => ({
                ...state,
                error: 'WebSocket error occurred',
                sessionReady: false,
                rematchPending: false,
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
                case 'rematch':
                    return applyRematch(state, payload);
                case 'session_state':
                    return applySessionState(state, payload);
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

        if (currentState.mode === MODES.MULTIPLAYER) {
            if (!currentState.sessionReady) {
                update((state) => ({
                    ...state,
                    error: 'Waiting for the game to synchronise…',
                }));
                return;
            }

            const localColorValue =
                typeof currentState.localColorValue === 'number'
                    ? currentState.localColorValue
                    : null;
            if (localColorValue === null) {
                update((state) => ({
                    ...state,
                    error: 'Waiting for color assignment…',
                }));
                return;
            }
            if (!Array.isArray(currentState.players) || currentState.players.length < 2) {
                update((state) => ({
                    ...state,
                    error: 'Waiting for another player to join…',
                }));
                return;
            }
            if (localColorValue !== currentState.toPlay) {
                update((state) => ({
                    ...state,
                    error: 'Not your turn yet.',
                }));
                return;
            }
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

    async function refreshLobby() {
        update((state) => ({
            ...state,
            lobbyLoading: true,
            lobbyError: null,
        }));

        try {
            const response = await fetch(`${BACKEND_BASE_URL}/games`);
            if (!response.ok) {
                throw new Error(`Failed to load games: ${response.statusText}`);
            }
            /** @type {Array<{game_id: string, mode: string, players?: string[], capacity?: number}>} */
            const payload = await response.json();
            const joinable = payload
                .filter((game) => game.mode === MODES.MULTIPLAYER)
                .map((game) => ({
                    gameId: game.game_id,
                    players: Array.isArray(game.players) ? game.players : [],
                    capacity: typeof game.capacity === 'number' ? game.capacity : 2,
                }))
                .filter((game) => game.players.length < game.capacity)
                .filter((game) => game.gameId !== currentState.gameId);
            joinable.sort((a, b) => b.players.length - a.players.length);

            update((state) => ({
                ...state,
                lobbyGames: joinable,
                lobbyLoading: false,
                lobbyError: null,
            }));
        } catch (error) {
            update((state) => ({
                ...state,
                lobbyLoading: false,
                lobbyError: error instanceof Error ? error.message : String(error),
            }));
        }
    }

    async function requestRematch() {
        if (currentState.mode !== MODES.MULTIPLAYER || !currentState.gameId) {
            return;
        }
        if (currentState.rematchPending) {
            return;
        }

        update((state) => ({
            ...state,
            rematchPending: true,
            error: null,
        }));

        try {
            const response = await fetch(
                `${BACKEND_BASE_URL}/games/${currentState.gameId}/rematch`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ playerId: currentState.playerId }),
                },
            );
            if (!response.ok) {
                throw new Error(`Failed to request rematch: ${response.statusText}`);
            }
        } catch (error) {
            update((state) => ({
                ...state,
                rematchPending: false,
                error: error instanceof Error ? error.message : String(error),
            }));
            throw error;
        }
    }

    function reset() {
        const mode = currentState.mode;
        const difficulty = currentState.difficulty;
        if (mode === MODES.MULTIPLAYER && currentState.gameId) {
            requestRematch().catch((error) => {
                console.error('Failed to request rematch', error);
            });
            return;
        }
        startNewGame(mode, difficulty).catch((error) => {
            console.error('Failed to reset game', error);
        });
    }

    return {
        subscribe,
        startNewGame,
        joinGame,
        playColumn,
        reset,
        requestRematch,
        refreshLobby,
    };
}

export const gameStore = createGameStore();

if (typeof window !== 'undefined') {
    const existingGameId = getGameIdFromUrl();
    if (existingGameId) {
        gameStore.joinGame(existingGameId).catch((error) => {
            console.error('Failed to join game from URL', error);
        });
    } else {
        gameStore.startNewGame(MODES.SOLO).catch((error) => {
            console.error('Failed to initialise game', error);
        });
    }
    gameStore.refreshLobby().catch((error) => {
        console.error('Failed to refresh lobby', error);
    });
} else {
    gameStore.startNewGame(MODES.SOLO).catch((error) => {
        console.error('Failed to initialise game', error);
    });
}

export function formatStatus(state) {
    if (state.error) {
        return state.error;
    }
    if (state.connectionState !== CONNECTION_STATES.CONNECTED) {
        return 'Connecting…';
    }
    if (state.mode === MODES.MULTIPLAYER && state.rematchPending) {
        return 'Rematch requested…';
    }
    if (state.mode === MODES.MULTIPLAYER && state.opponentDisconnected) {
        return 'Opponent disconnected. Waiting for reconnection…';
    }
    if (
        state.mode === MODES.MULTIPLAYER &&
        (!Array.isArray(state.players) || state.players.length < 2)
    ) {
        return 'Waiting for another player…';
    }
    if (state.winner !== null) {
        return describeVictory(state.winner);
    }
    if (state.draw) {
        return 'Draw game';
    }
    return describeTurn(state.toPlay);
}

export function currentPlayerName(state) {
    return COLOR_LABELS[state.toPlay];
}
