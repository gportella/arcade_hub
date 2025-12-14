import { Chess } from "chess.js";

const DEFAULT_DEPTH = 2;
const MAX_DEPTH = 4;
const MATE_SCORE = 1e5;
const PIECE_VALUES = {
    p: 100,
    n: 320,
    b: 330,
    r: 500,
    q: 900,
    k: 0,
};

function clampDepth(value) {
    const numeric = Number.isFinite(value) ? Math.floor(value) : DEFAULT_DEPTH;
    return Math.min(MAX_DEPTH, Math.max(1, numeric || DEFAULT_DEPTH));
}

function toUci(move) {
    return `${move.from}${move.to}${move.promotion ?? ""}`;
}

function evaluateMaterial(chess) {
    let score = 0;
    const board = chess.board();
    for (let rank = 0; rank < 8; rank++) {
        for (let file = 0; file < 8; file++) {
            const piece = board[rank][file];
            if (!piece) continue;
            const value = PIECE_VALUES[piece.type] ?? 0;
            score += piece.color === "w" ? value : -value;
        }
    }
    return score;
}

function evaluatePosition(chess, perspective) {
    if (chess.isCheckmate()) {
        return chess.turn() === perspective ? -MATE_SCORE : MATE_SCORE;
    }
    if (
        chess.isDraw() ||
        chess.isStalemate() ||
        chess.isThreefoldRepetition() ||
        chess.isInsufficientMaterial()
    ) {
        return 0;
    }
    const material = evaluateMaterial(chess);
    return perspective === "w" ? material : -material;
}

function search(chess, depth, alpha, beta, perspective) {
    if (depth === 0 || chess.isGameOver()) {
        return evaluatePosition(chess, perspective);
    }

    const moves = chess.moves({ verbose: true });
    if (!moves.length) {
        return evaluatePosition(chess, perspective);
    }

    const maximizing = chess.turn() === perspective;

    if (maximizing) {
        let best = -Infinity;
        for (const move of moves) {
            chess.move(move);
            const score = search(chess, depth - 1, alpha, beta, perspective);
            chess.undo();
            if (score > best) {
                best = score;
            }
            if (score > alpha) {
                alpha = score;
            }
            if (alpha >= beta) {
                break;
            }
        }
        return best;
    }

    let best = Infinity;
    for (const move of moves) {
        chess.move(move);
        const score = search(chess, depth - 1, alpha, beta, perspective);
        chess.undo();
        if (score < best) {
            best = score;
        }
        if (score < beta) {
            beta = score;
        }
        if (alpha >= beta) {
            break;
        }
    }
    return best;
}

export function createMiniEngine(options = {}) {
    const chess = new Chess();
    let depth = clampDepth(options.depth);

    function reset() {
        chess.reset();
    }

    function applyMove(uci) {
        const move = {
            from: uci.slice(0, 2),
            to: uci.slice(2, 4),
        };
        if (uci.length > 4) {
            move.promotion = uci[4];
        }
        chess.move(move);
    }

    async function think({ depth: overrideDepth } = {}) {
        const searchDepth = clampDepth(overrideDepth ?? depth);
        const perspective = chess.turn();
        const moves = chess.moves({ verbose: true });

        if (!moves.length) {
            return null;
        }

        let bestMove = null;
        let bestScore = -Infinity;

        for (const move of moves) {
            chess.move(move);
            const score = search(chess, searchDepth - 1, -Infinity, Infinity, perspective);
            chess.undo();

            if (
                score > bestScore ||
                (score === bestScore && Math.random() < 0.5)
            ) {
                bestScore = score;
                bestMove = move;
            }
        }

        if (!bestMove) {
            return null;
        }

        chess.move(bestMove);
        return toUci(bestMove);
    }

    function loadMoves(moves = []) {
        reset();
        for (const mv of moves) {
            applyMove(mv);
        }
    }

    function setDepth(value) {
        depth = clampDepth(value);
    }

    function getDepth() {
        return depth;
    }

    reset();

    return {
        reset,
        think,
        applyMove,
        loadMoves,
        setDepth,
        getDepth,
        get side() {
            return chess.turn();
        },
    };
}