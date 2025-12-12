<script>
    import { onMount, onDestroy } from "svelte";
    import { Chess } from "chess.js";
    import { Chessground } from "svelte5-chessground";
    import "@lichess-org/chessground/assets/chessground.base.css";
    import "@lichess-org/chessground/assets/chessground.brown.css";
    import "@lichess-org/chessground/assets/chessground.cburnett.css";
    import { normalizeFen, fenEquals } from "./fen.js";

    const game = new Chess();
    /** @type {ReadonlyArray<"q" | "r" | "b" | "n">} */
    const PROMOTION_ORDER = ["q", "r", "b", "n"];
    /** @type {Record<"q" | "r" | "b" | "n", string>} */
    const PROMOTION_LABELS = {
        q: "Queen",
        r: "Rook",
        b: "Bishop",
        n: "Knight",
    };

    /**
     * @param {string | undefined} piece
     * @returns {piece is "q" | "r" | "b" | "n"}
     */
    function isPromotionPiece(piece) {
        return piece === "q" || piece === "r" || piece === "b" || piece === "n";
    }

    let boardApi;
    let boardElement;
    let resizeObserver;
    let statusText = "";
    /** @type {import("chessground/types").Key[]} */
    let lastMove = [];
    let hasHistory = false;
    let hasMounted = false;
    let previousStartingFen = null;
    let previousResetToken = null;
    let previousBoardFen = null;
    let currentFen = normalizeFen(game.fen()) ?? game.fen();
    let lastLocalFen = null;
    let pendingLocalFen = null;
    let lastAcknowledgedFen = currentFen;
    /** @type {"white" | "black"} */
    let movableColor = "white";
    /** @type {import("chessground/types").Dests} */
    let movableDests = new Map();
    let isInCheck = false;
    /** @type {false | "white" | "black"} */
    let checkColor = false;
    /** @type {"white" | "black"} */
    let resolvedOrientation = "white";
    let showPromotionDialog = false;
    /** @type {{ from: import("chessground/types").Key; to: import("chessground/types").Key; color: "white" | "black" } | null} */
    let promotionPending = null;
    /** @type {Array<"q" | "r" | "b" | "n">} */
    let promotionOptions = [];
    let updateTimeout;

    /** @type {"white" | "black"} */
    export let orientation = "white";
    export let startingFen = null;
    export let positionFen = null;
    export let resetToken = null;
    export let onMove = (_detail) => {};
    export let onUndo = (_detail) => {};
    export let onReset = (_detail) => {};
    export let showStatus = true;
    export let showControls = true;
    export let interactive = true;

    // New prop: PGN to replay
    /** @type {string | null} */
    export let pgn = null;
    export let finished = false;

    // PGN cache and derived
    let trimmedPgn = "";
    let pgnCacheKey = null;
    let pgnCache = {
        moves: [],
        startFen: null,
        hasResult: false,
    };
    $: trimmedPgn = typeof pgn === "string" ? pgn.trim() : "";
    $: {
        if (!trimmedPgn) {
            pgnCacheKey = null;
            pgnCache = { moves: [], startFen: null, hasResult: false };
        } else if (trimmedPgn !== pgnCacheKey) {
            try {
                const parsed = new Chess();
                parsed.loadPgn(trimmedPgn, { strict: false });
                const headerMap = parsed.header?.() ?? {};
                const resultTag = headerMap.Result;
                const fallbackResult = /(?:^|\s)(1-0|0-1|1\/2-1\/2)\s*$/.test(
                    trimmedPgn,
                );
                pgnCacheKey = trimmedPgn;
                pgnCache = {
                    moves: parsed.history({ verbose: true }),
                    startFen:
                        headerMap.SetUp === "1" && headerMap.FEN
                            ? headerMap.FEN
                            : null,
                    hasResult: Boolean(
                        (resultTag && resultTag !== "*") || fallbackResult,
                    ),
                };
            } catch (error) {
                const fallbackResult = /(?:^|\s)(1-0|0-1|1\/2-1\/2)\s*$/.test(
                    trimmedPgn,
                );
                pgnCacheKey = trimmedPgn;
                pgnCache = {
                    moves: [],
                    startFen: null,
                    hasResult: fallbackResult,
                };
                console.warn("Failed to parse PGN for replay", error);
            }
        }
    }
    $: gameFinished = Boolean(
        finished || game.isGameOver() || pgnCache.hasResult,
    );
    $: replayReady = Boolean(trimmedPgn && gameFinished);
    $: allowInteraction = interactive && !gameFinished && !replayActive;

    // Replay state
    let replayActive = false;
    let replayChess = null;
    let replayMoves = [];
    let replayIdx = 0;
    let replayTimer = null;
    let replaySpeedMs = 700; // autoplay step speed

    // Helper: pick current engine (live vs replay)
    function currentEngine() {
        return replayActive && replayChess ? replayChess : game;
    }

    function initialiseGame() {
        const sourceFen = startingFen || positionFen;
        if (sourceFen) {
            try {
                game.load(sourceFen);
            } catch (error) {
                console.warn(
                    "Invalid FEN supplied, falling back to default start position.",
                    error,
                );
                game.reset();
            }
        } else {
            game.reset();
        }
        lastMove = [];
        previousStartingFen = startingFen;
        previousResetToken = resetToken;
        previousBoardFen = null;
        lastLocalFen = null;
        pendingLocalFen = null;
        lastAcknowledgedFen = normalizeFen(game.fen()) ?? game.fen();
        updateState();
    }

    function applyExternalFen(fen) {
        const normalizedFen = normalizeFen(fen);
        if (!normalizedFen) {
            return;
        }

        const currentNormalized = normalizeFen(game.fen());
        const pendingNormalized = pendingLocalFen
            ? normalizeFen(pendingLocalFen)
            : null;
        const acknowledgedNormalized = lastAcknowledgedFen
            ? normalizeFen(lastAcknowledgedFen)
            : null;

        if (
            pendingNormalized &&
            acknowledgedNormalized &&
            fenEquals(normalizedFen, acknowledgedNormalized)
        ) {
            return;
        }

        if (pendingNormalized && fenEquals(normalizedFen, pendingNormalized)) {
            pendingLocalFen = null;
            lastAcknowledgedFen = normalizedFen;
            lastLocalFen = null;
            return;
        }

        if (fenEquals(normalizedFen, currentNormalized)) {
            lastAcknowledgedFen = normalizedFen;
            lastLocalFen = null;
            pendingLocalFen = null;
            return;
        }

        if (lastLocalFen && fenEquals(normalizedFen, lastLocalFen)) {
            lastLocalFen = null;
            pendingLocalFen = null;
            lastAcknowledgedFen = normalizedFen;
            return;
        }

        try {
            game.load(normalizedFen);
        } catch (error) {
            console.warn("Invalid external FEN supplied", error);
            return;
        }

        // Clear last move for external updates to avoid incorrect highlighting
        lastMove = [];
        previousBoardFen = null;
        lastLocalFen = null;
        pendingLocalFen = null;
        lastAcknowledgedFen = normalizedFen;

        // Use requestAnimationFrame for smooth transition
        requestAnimationFrame(() => {
            updateState();
        });
    }

    onMount(() => {
        hasMounted = true;
        initialiseGame();
        if (typeof ResizeObserver !== "undefined" && boardElement) {
            resizeObserver = new ResizeObserver(() => {
                boardApi?.redrawAll();
            });
            resizeObserver.observe(boardElement);
        }
    });

    onDestroy(() => {
        clearTimeout(updateTimeout);
        resizeObserver?.disconnect();
        if (replayTimer) {
            clearInterval(replayTimer);
            replayTimer = null;
        }
    });

    $: resolvedOrientation = orientation === "black" ? "black" : "white";

    $: if (hasMounted) {
        clearTimeout(updateTimeout);

        if (resetToken !== previousResetToken) {
            initialiseGame();
        } else if (startingFen !== previousStartingFen) {
            initialiseGame();
        } else if (positionFen) {
            const normalizedPositionFen = normalizeFen(positionFen);
            const normalizedCurrentFen = normalizeFen(currentFen);
            const pendingNormalized = pendingLocalFen
                ? normalizeFen(pendingLocalFen)
                : null;
            const acknowledgedNormalized = lastAcknowledgedFen
                ? normalizeFen(lastAcknowledgedFen)
                : null;

            if (normalizedPositionFen) {
                const matchesCurrent = fenEquals(
                    normalizedPositionFen,
                    normalizedCurrentFen,
                );
                const matchesPending =
                    pendingNormalized &&
                    fenEquals(normalizedPositionFen, pendingNormalized);
                const matchesAcknowledged =
                    acknowledgedNormalized &&
                    fenEquals(normalizedPositionFen, acknowledgedNormalized);

                if (matchesPending) {
                    pendingLocalFen = null;
                    lastAcknowledgedFen = normalizedPositionFen;
                    lastLocalFen = null;
                } else if (matchesCurrent) {
                    lastAcknowledgedFen = normalizedPositionFen;
                    if (pendingLocalFen) {
                        pendingLocalFen = null;
                        lastLocalFen = null;
                    }
                } else if (matchesAcknowledged) {
                    lastAcknowledgedFen = normalizedPositionFen;
                    if (pendingLocalFen) {
                        pendingLocalFen = null;
                    }
                    if (lastLocalFen) {
                        lastLocalFen = null;
                    }
                } else {
                    // Debounce external FEN updates
                    updateTimeout = setTimeout(() => {
                        applyExternalFen(positionFen);
                    }, 10);
                }
            }
        }
    }

    // Watch for boardApi becoming available - only run once
    let boardApiInitialized = false;
    $: if (boardApi && hasMounted && !boardApiInitialized) {
        boardApiInitialized = true;
        updateState();
    }

    /** @param {Chess} ch */
    function computeDestinations(ch) {
        const destinations = new Map();
        for (const move of ch.moves({ verbose: true })) {
            const squares = destinations.get(move.from) ?? [];
            squares.push(move.to);
            destinations.set(move.from, squares);
        }
        return destinations;
    }

    /** @param {Chess} ch @returns {"white" | "black"} */
    function playerTurnColor(ch) {
        return ch.turn() === "w" ? "white" : "black";
    }

    /** @param {Chess} ch */
    function computeStatus(ch) {
        if (ch.isCheckmate()) {
            const winner = ch.turn() === "w" ? "Black" : "White";
            return `${winner} wins by checkmate`;
        }
        if (ch.isStalemate()) {
            return "Draw by stalemate";
        }
        if (ch.isDraw()) {
            return "Draw";
        }
        const player = playerTurnColor(ch) === "white" ? "White" : "Black";
        const suffix = ch.inCheck() ? " (check)" : "";
        return `${player} to move${suffix}`;
    }

    // ===== Captured bars and material delta (canonical baseline) =====
    const canonicalCounts = {
        w: { p: 8, n: 2, b: 2, r: 2, q: 1, k: 1 },
        b: { p: 8, n: 2, b: 2, r: 2, q: 1, k: 1 },
    };
    const pieceOrder = ["p", "n", "b", "r", "q"]; // display order
    const values = { p: 1, n: 3, b: 3, r: 5, q: 9, k: 0 };
    let capturedByWhite = []; // black pieces captured by white (types)
    let capturedByBlack = []; // white pieces captured by black (types)
    let materialDelta = 0; // positive => White ahead

    /** @param {Chess} ch */
    function countPieces(ch) {
        const counts = {
            w: { p: 0, n: 0, b: 0, r: 0, q: 0, k: 0 },
            b: { p: 0, n: 0, b: 0, r: 0, q: 0, k: 0 },
        };
        const grid = ch.board();
        for (let r = 0; r < 8; r++) {
            for (let f = 0; f < 8; f++) {
                const sq = grid[r][f];
                if (!sq) continue;
                counts[sq.color][sq.type]++;
            }
        }
        return counts;
    }

    /** @param {'p'|'n'|'b'|'r'|'q'|'k'} t */
    function roleClass(t) {
        switch (t) {
            case "p":
                return "pawn";
            case "n":
                return "knight";
            case "b":
                return "bishop";
            case "r":
                return "rook";
            case "q":
                return "queen";
            case "k":
                return "king";
        }
    }

    /** @param {Chess} ch */
    function updateCapturedAndMaterial(ch) {
        const current = countPieces(ch);

        // Captured sets relative to canonical (ignore kings in the UI)
        capturedByWhite = [];
        capturedByBlack = [];
        for (const t of pieceOrder) {
            const wCap = Math.max(0, canonicalCounts.b[t] - current.b[t]); // black missing => captured by white
            const bCap = Math.max(0, canonicalCounts.w[t] - current.w[t]); // white missing => captured by black
            for (let i = 0; i < wCap; i++) capturedByWhite.push(t);
            for (let i = 0; i < bCap; i++) capturedByBlack.push(t);
        }

        // Material delta from current counts (promotions included)
        const whiteMat = pieceOrder.reduce(
            (s, t) => s + values[t] * current.w[t],
            0,
        );
        const blackMat = pieceOrder.reduce(
            (s, t) => s + values[t] * current.b[t],
            0,
        );
        materialDelta = whiteMat - blackMat;
    }

    $: topCaptured =
        resolvedOrientation === "white" ? capturedByBlack : capturedByWhite;
    $: bottomCaptured =
        resolvedOrientation === "white" ? capturedByWhite : capturedByBlack;
    $: topPieceLabel = resolvedOrientation === "white" ? "White" : "Black";
    $: bottomPieceLabel = resolvedOrientation === "white" ? "Black" : "White";
    $: topColorClass = "white";
    $: bottomColorClass = "white";
    $: topAdvantage =
        resolvedOrientation === "white"
            ? materialDelta < 0
                ? `+${-materialDelta}`
                : ""
            : materialDelta > 0
              ? `+${materialDelta}`
              : "";
    $: bottomAdvantage =
        resolvedOrientation === "white"
            ? materialDelta > 0
                ? `+${materialDelta}`
                : ""
            : materialDelta < 0
              ? `+${-materialDelta}`
              : "";
    $: topHasContent = Boolean(topCaptured.length || topAdvantage);
    $: bottomHasContent = Boolean(bottomCaptured.length || bottomAdvantage);

    function capturedMargin(idx, list) {
        if (idx === 0) {
            return "0px";
        }
        return list[idx - 1] === list[idx] ? "-10px" : "2px";
    }

    function updateState() {
        const ch = currentEngine();
        statusText = computeStatus(ch);
        const newFen = normalizeFen(ch.fen()) ?? ch.fen();
        movableColor = playerTurnColor(ch);
        movableDests = computeDestinations(ch);
        isInCheck = ch.inCheck();
        checkColor = isInCheck ? movableColor : false;
        hasHistory = game.history().length > 0;

        // Update captured bars + material
        updateCapturedAndMaterial(ch);

        const boardReady = Boolean(boardApi);
        if (!boardReady) {
            currentFen = newFen;
            previousBoardFen = null;
            return;
        }

        const fenChanged = newFen !== previousBoardFen;

        currentFen = newFen;
        const lastMovePayload = lastMove.length ? lastMove : undefined;

        const config = {
            turnColor: movableColor,
            orientation: resolvedOrientation,
            lastMove: lastMovePayload,
            check: checkColor,
            movable: {
                free: false,
                // Disable interaction in replay mode / when finished
                color: allowInteraction ? movableColor : undefined,
                dests: allowInteraction ? movableDests : new Map(),
                showDests: allowInteraction,
            },
            draggable: {
                enabled: allowInteraction,
            },
            highlight: {
                lastMove: true,
                check: true,
            },
        };

        if (fenChanged) {
            config.fen = currentFen;
            previousBoardFen = currentFen;
        }

        boardApi.set(config);
    }

    function promotionLabel(piece) {
        return PROMOTION_LABELS[piece] ?? piece.toUpperCase();
    }

    /**
     * @param {import("chessground/types").Key} from
     * @param {import("chessground/types").Key} to
     * @param {Set<string>} promotions
     */
    function beginPromotionSelection(from, to, promotions) {
        promotionOptions = PROMOTION_ORDER.filter((piece) =>
            promotions.has(piece),
        );
        promotionPending = {
            from,
            to,
            color: playerTurnColor(game),
        };
        showPromotionDialog = true;
    }

    function applyMove(from, to, promotion) {
        showPromotionDialog = false;
        promotionOptions = [];
        promotionPending = null;

        const payload = { from, to };
        if (promotion) {
            payload.promotion = promotion;
        }

        const executed = game.move(payload);
        if (!executed) {
            updateState();
            return;
        }

        lastMove = [executed.from, executed.to];
        const outboundFen = normalizeFen(game.fen()) ?? game.fen();
        lastLocalFen = outboundFen;
        pendingLocalFen = outboundFen;
        updateState();
        onMove({ move: executed, fen: outboundFen });
    }

    function choosePromotion(piece) {
        if (!promotionPending) return;
        if (!promotionOptions.includes(piece)) return;
        const { from, to } = promotionPending;
        applyMove(from, to, piece);
    }

    function cancelPromotion() {
        showPromotionDialog = false;
        promotionPending = null;
        promotionOptions = [];
        updateState();
    }

    function handleMove(from, to, metadata = {}) {
        if (!allowInteraction) {
            updateState();
            return;
        }

        const legalMoves = game.moves({ verbose: true });
        const candidateMoves = legalMoves.filter(
            (move) => move.from === from && move.to === to,
        );

        if (!candidateMoves.length) {
            updateState();
            return;
        }

        const promotionMoves = candidateMoves.filter((move) => move.promotion);
        const promotionPieces = new Set(
            promotionMoves
                .map((move) => move.promotion)
                .filter(isPromotionPiece),
        );

        if (promotionPieces.size > 1 && !metadata.promotion) {
            beginPromotionSelection(from, to, promotionPieces);
            updateState();
            return;
        }

        const desiredPromotion =
            metadata.promotion ||
            (promotionPieces.has("q") ? "q" : undefined) ||
            promotionMoves[0]?.promotion;

        applyMove(from, to, desiredPromotion);
    }

    function undo() {
        const undone = game.undo();
        if (!undone) return;
        showPromotionDialog = false;
        promotionPending = null;
        promotionOptions = [];
        const history = game.history({ verbose: true });
        lastMove = history.length
            ? [history[history.length - 1].from, history[history.length - 1].to]
            : [];
        lastLocalFen = null;
        pendingLocalFen = null;
        lastAcknowledgedFen = normalizeFen(game.fen()) ?? game.fen();
        updateState();
        onUndo({ move: undone, fen: normalizeFen(game.fen()) ?? game.fen() });
    }

    function reset() {
        game.reset();
        lastMove = [];
        showPromotionDialog = false;
        promotionPending = null;
        promotionOptions = [];
        lastLocalFen = null;
        pendingLocalFen = null;
        lastAcknowledgedFen = normalizeFen(game.fen()) ?? game.fen();
        updateState();
        onReset({ fen: normalizeFen(game.fen()) ?? game.fen() });
    }

    export function undoMove() {
        if (!interactive) return;
        undo();
    }

    export function resetPosition() {
        reset();
    }

    // ===== Replay controls (finalized) =====
    function prepareReplay() {
        if (!trimmedPgn) return;

        let moves = pgnCache.moves;
        let startFen = pgnCache.startFen;

        if (!moves.length) {
            const tmp = new Chess();
            try {
                tmp.loadPgn(trimmedPgn, { strict: false });
                moves = tmp.history({ verbose: true });
                const headerMap = tmp.header?.() ?? {};
                if (!startFen && headerMap.SetUp === "1" && headerMap.FEN) {
                    startFen = headerMap.FEN;
                }
            } catch (error) {
                console.warn("Invalid PGN for replay", error);
                return;
            }
        }

        if (!moves.length) {
            console.warn("No moves available for replay.");
            return;
        }

        replayMoves = moves;

        // Create the viewer engine and set the starting position
        replayChess = new Chess();
        try {
            if (startingFen) {
                replayChess.load(startingFen);
            } else if (startFen) {
                replayChess.load(startFen);
            } else {
                replayChess.reset();
            }
        } catch (error) {
            console.warn(
                "Failed to set replay starting position, using default start",
                error,
            );
            replayChess.reset();
        }

        replayIdx = 0;
        lastMove = [];
        // Disable dragging while replaying
        showPromotionDialog = false;
        promotionPending = null;
        promotionOptions = [];

        // Render the starting position for replay
        replayActive = true;
        updateState();
    }

    function exitReplay() {
        pauseReplay();
        replayActive = false;
        lastMove = [];
        updateState();
    }

    function nextReplay() {
        if (!replayActive || replayIdx >= replayMoves.length) return;
        const m = replayMoves[replayIdx++];
        replayChess.move({
            from: m.from,
            to: m.to,
            promotion: m.promotion?.toLowerCase(),
        });
        lastMove = [m.from, m.to];
        updateState();
    }

    function prevReplay() {
        if (!replayActive || replayIdx <= 0) return;
        replayChess.undo();
        replayIdx--;
        const history = replayChess.history({ verbose: true });
        lastMove = history.length
            ? [history[history.length - 1].from, history[history.length - 1].to]
            : [];
        updateState();
    }

    function resetReplay() {
        if (!replayActive) return;
        try {
            if (startingFen) {
                replayChess.load(startingFen);
            } else if (pgnCache.startFen) {
                replayChess.load(pgnCache.startFen);
            } else if (trimmedPgn) {
                const tmp = new Chess();
                tmp.loadPgn(trimmedPgn, { strict: false });
                const headerMap = tmp.header?.() ?? {};
                if (headerMap.SetUp === "1" && headerMap.FEN) {
                    replayChess.load(headerMap.FEN);
                } else {
                    replayChess.reset();
                }
            } else {
                replayChess.reset();
            }
        } catch {
            replayChess.reset();
        }
        replayIdx = 0;
        lastMove = [];
        updateState();
    }

    function playReplay() {
        if (!replayActive || replayTimer) return;
        replayTimer = setInterval(() => {
            if (replayIdx >= replayMoves.length) {
                pauseReplay();
                return;
            }
            nextReplay();
        }, replaySpeedMs);
    }

    function pauseReplay() {
        if (!replayTimer) return;
        clearInterval(replayTimer);
        replayTimer = null;
    }
</script>

<section class="chess-widget" class:compact={!showStatus && !showControls}>
    <div class="board-stack">
        <div
            class="captured-slot top"
            class:empty={!topHasContent}
            role="status"
            aria-live="polite"
        >
            <div
                class="captured-list"
                aria-label="Captured pieces for top player"
            >
                {#each topCaptured as t, i}
                    <span
                        class={`mini-piece piece ${topColorClass} ${roleClass(t)}`}
                        aria-hidden="true"
                        title={`${topPieceLabel} ${roleClass(t)} captured`}
                        style={`margin-left: ${capturedMargin(i, topCaptured)}`}
                    ></span>
                {/each}
            </div>
            {#if topAdvantage}
                <span class="adv" aria-label="Material advantage"
                    >{topAdvantage}</span
                >
            {/if}
        </div>

        <div class="board" aria-label="Chess board" bind:this={boardElement}>
            <Chessground
                bind:api={boardApi}
                fen={currentFen}
                orientation={resolvedOrientation}
                animationDuration={200}
                draggableShowGhost={true}
                highlightLastMove={true}
                highlightCheck={Boolean(checkColor)}
                check={checkColor}
                lastMove={lastMove.length ? lastMove : undefined}
                movableFree={false}
                movableShowDests={true}
                {movableColor}
                {movableDests}
                onMove={handleMove}
            />

            {#if showPromotionDialog && promotionPending}
                <div class="promotion-overlay" role="dialog" aria-modal="true">
                    <div class="promotion-card">
                        <p class="promotion-heading">
                            {promotionPending.color === "white"
                                ? "White pawn promotion"
                                : "Black pawn promotion"}
                        </p>
                        <div class="promotion-options">
                            {#each promotionOptions as option}
                                <button
                                    type="button"
                                    class="promotion-choice"
                                    on:click={() => choosePromotion(option)}
                                >
                                    {promotionLabel(option)}
                                </button>
                            {/each}
                        </div>
                        <button
                            type="button"
                            class="promotion-cancel"
                            on:click={cancelPromotion}
                        >
                            Cancel
                        </button>
                    </div>
                </div>
            {/if}
        </div>

        <div
            class="captured-slot bottom"
            class:empty={!bottomHasContent}
            role="status"
            aria-live="polite"
        >
            <div
                class="captured-list"
                aria-label="Captured pieces for bottom player"
            >
                {#each bottomCaptured as t, i}
                    <span
                        class={`mini-piece piece ${bottomColorClass} ${roleClass(t)}`}
                        aria-hidden="true"
                        title={`${bottomPieceLabel} ${roleClass(t)} captured`}
                        style={`margin-left: ${capturedMargin(i, bottomCaptured)}`}
                    ></span>
                {/each}
            </div>
            {#if bottomAdvantage}
                <span class="adv" aria-label="Material advantage"
                    >{bottomAdvantage}</span
                >
            {/if}
        </div>
    </div>

    {#if replayReady}
        <div class="replay-bar" role="region" aria-label="Replay controls">
            {#if !replayActive}
                <button type="button" on:click={prepareReplay}
                    >Watch Replay ▶</button
                >
                <span class="replay-hint">Relive the finished game.</span>
            {:else}
                <div class="replay-controls">
                    <button
                        type="button"
                        on:click={prevReplay}
                        aria-label="Previous move"
                        disabled={replayIdx === 0}>⟨</button
                    >
                    {#if !replayTimer}
                        <button
                            type="button"
                            on:click={playReplay}
                            aria-label="Play replay"
                            disabled={replayIdx >= replayMoves.length}
                            >▶</button
                        >
                    {:else}
                        <button
                            type="button"
                            on:click={pauseReplay}
                            aria-label="Pause replay">⏸</button
                        >
                    {/if}
                    <button
                        type="button"
                        on:click={nextReplay}
                        aria-label="Next move"
                        disabled={replayIdx >= replayMoves.length}>⟩</button
                    >
                    <button
                        type="button"
                        on:click={resetReplay}
                        aria-label="Restart replay">⟲</button
                    >
                    <button
                        type="button"
                        on:click={exitReplay}
                        aria-label="Close replay">✕</button
                    >
                </div>
                <span class="replay-progress">
                    {#if replayMoves.length === 0}
                        Replay ready
                    {:else if replayIdx === 0}
                        Start position
                    {:else}
                        Move {Math.min(replayIdx, replayMoves.length)} of {replayMoves.length}
                    {/if}
                </span>
            {/if}
        </div>
    {/if}

    {#if showStatus || showControls}
        <aside class="panel" aria-live="polite">
            {#if showStatus}
                <p class="status">{statusText}</p>
            {/if}
            {#if showControls}
                <div class="actions">
                    <button
                        type="button"
                        on:click={undo}
                        disabled={!hasHistory}
                    >
                        Undo
                    </button>
                    <button type="button" on:click={reset}> Reset </button>
                </div>
            {/if}
        </aside>
    {/if}
</section>

<style>
    .chess-widget {
        display: grid;
        gap: 1.5rem;
    }

    @media (min-width: 768px) {
        .chess-widget {
            grid-template-columns: minmax(0, 1fr) 220px;
            align-items: start;
        }
    }

    .chess-widget.compact {
        display: block;
    }

    .board-stack {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.35rem;
    }

    .board {
        position: relative;
        width: min(100%, 860px);
        aspect-ratio: 1;
        margin-inline: auto;
        box-shadow: 0 12px 24px rgba(15, 23, 42, 0.2);
        border-radius: 1rem;
        overflow: hidden;
    }

    .board :global(.cg-board) {
        width: 100%;
        height: 100%;
    }

    .captured-slot {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.75rem;
        width: min(100%, 860px);
        min-height: 34px;
        padding: 0 0.75rem;
        pointer-events: none;
        transition: opacity 160ms ease;
    }

    .captured-slot.empty {
        visibility: hidden;
        opacity: 0;
    }

    .captured-slot:not(.empty) {
        background: rgba(15, 23, 42, 0.05);
        border-radius: 0.75rem;
    }

    .captured-list {
        display: flex;
        gap: 0;
        flex-wrap: nowrap;
        justify-content: flex-start;
        flex: 1;
        min-height: 20px;
        overflow: hidden;
    }

    /* Mini piece using cburnett assets via chessground .piece classes */
    .mini-piece.piece {
        position: static; /* override chessground absolute */
        display: inline-block;
        width: 18px;
        height: 18px;
        background-size: contain; /* fit inside the box */
        background-repeat: no-repeat;
        background-position: center;
        filter: drop-shadow(0 1px 1px rgba(84, 82, 82, 0.25));
    }

    /* cburnett sprites for captured minis */
    .mini-piece.piece.white.pawn {
        background-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0NSIgaGVpZ2h0PSI0NSI+PHBhdGggZD0iTTIyLjUgOWMtMi4yMSAwLTQgMS43OS00IDQgMCAuODkuMjkgMS43MS43OCAyLjM4QzE3LjMzIDE2LjUgMTYgMTguNTkgMTYgMjFjMCAyLjAzLjk0IDMuODQgMi40MSA1LjAzLTMgMS4wNi03LjQxIDUuNTUtNy40MSAxMy40N2gyM2MwLTcuOTItNC40MS0xMi40MS03LjQxLTEzLjQ3IDEuNDctMS4xOSAyLjQxLTMgMi40MS01LjAzIDAtMi40MS0xLjMzLTQuNS0zLjI4LTUuNjIuNDktLjY3Ljc4LTEuNDkuNzgtMi4zOCAwLTIuMjEtMS43OS00LTQtNHoiIGZpbGw9IiNmZmYiIHN0cm9rZT0iIzAwMCIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPjwvc3ZnPg==");
    }

    .mini-piece.piece.white.knight {
        background-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0NSIgaGVpZ2h0PSI0NSI+PGcgZmlsbD0ibm9uZSIgZmlsbC1ydWxlPSJldmVub2RkIiBzdHJva2U9IiMwMDAiIHN0cm9rZS13aWR0aD0iMS41IiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwYXRoIGQ9Ik0yMiAxMGMxMC41IDEgMTYuNSA4IDE2IDI5SDE1YzAtOSAxMC02LjUgOC0yMSIgZmlsbD0iI2ZmZiIvPjxwYXRoIGQ9Ik0yNCAxOGMuMzggMi45MS01LjU1IDcuMzctOCA5LTMgMi0yLjgyIDQuMzQtNSA0LTEuMDQyLS45NCAxLjQxLTMuMDQgMC0zLTEgMCAuMTkgMS4yMy0xIDItMSAwLTQuMDAzIDEtNC00IDAtMiA2LTEyIDYtMTJzMS44OS0xLjkgMi0zLjVjLS43My0uOTk0LS41LTItLjUtMyAxLTEgMyAyLjUgMyAyLjVoMnMuNzgtMS45OTIgMi41LTNjMSAwIDEgMyAxIDMiIGZpbGw9IiNmZmYiLz48cGF0aCBkPSJNOS41IDI1LjVhLjUuNSAwIDEgMS0xIDAgLjUuNSAwIDEgMSAxIDB6bTUuNDMzLTkuNzVhLjUgMS41IDMwIDEgMS0uODY2LS41LjUgMS41IDMwIDEgMSAuODY2LjV6IiBmaWxsPSIjMDAwIi8+PC9nPjwvc3ZnPg==");
    }

    .mini-piece.piece.white.bishop {
        background-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0NSIgaGVpZ2h0PSI0NSI+PGcgZmlsbD0ibm9uZSIgZmlsbC1ydWxlPSJldmVub2RkIiBzdHJva2U9IiMwMDAiIHN0cm9rZS13aWR0aD0iMS41IiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxnIGZpbGw9IiNmZmYiIHN0cm9rZS1saW5lY2FwPSJidXR0Ij48cGF0aCBkPSJNOSAzNmMzLjM5LS45NyAxMC4xMS40MyAxMy41LTIgMy4zOSAyLjQzIDEwLjExIDEuMDMgMTMuNSAyIDAgMCAxLjY1LjU0IDMgMi0uNjguOTctMS42NS45OS0zIC41LTMuMzktLjk3LTEwLjExLjQ2LTEzLjUtMS0zLjM5IDEuNDYtMTAuMTEuMDMtMTMuNSAxLTEuMzU0LjQ5LTIuMzIzLjQ3LTMtLjUgMS4zNTQtMS45NCAzLTIgMy0yeiIvPjxwYXRoIGQ9Ik0xNSAzMmMyLjUgMi41IDEyLjUgMi41IDE1IDAgLjUtMS41IDAtMiAwLTIgMC0yLjUtMi41LTQtMi41LTQgNS41LTEuNSA2LTExLjUtNS0xNS41LTExIDQtMTAuNSAxNC01IDE1LjUgMCAwLTIuNSAxLjUtMi41IDQgMCAwLS41LjUgMCAyeiIvPjxwYXRoIGQ9Ik0yNSA4YTIuNSAyLjUgMCAxIDEtNSAwIDIuNSAyLjUgMCAxIDEgNSAweiIvPjwvZz48cGF0aCBkPSJNMTcuNSAyNmgxME0xNSAzMGgxNW0tNy41LTE0LjV2NU0yMCAxOGg1IiBzdHJva2UtbGluZWpvaW49Im1pdGVyIi8+PC9nPjwvc3ZnPg==");
    }

    .mini-piece.piece.white.rook {
        background-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0NSIgaGVpZ2h0PSI0NSI+PGcgZmlsbD0iI2ZmZiIgZmlsbC1ydWxlPSJldmVub2RkIiBzdHJva2U9IiMwMDAiIHN0cm9rZS13aWR0aD0iMS41IiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwYXRoIGQ9Ik05IDM5aDI3di0zSDl2M3ptMy0zdi00aDIxdjRIMTJ6bS0xLTIyVjloNHYyaDVWOWg1djJoNVY5aDR2NSIgc3Ryb2tlLWxpbmVjYXA9ImJ1dHQiLz48cGF0aCBkPSJNMzQgMTRsLTMgM0gxNGwtMy0zIi8+PHBhdGggZD0iTTMxIDE3djEyLjVIMTRWMTciIHN0cm9rZS1saW5lY2FwPSJidXR0IiBzdHJva2UtbGluZWpvaW49Im1pdGVyIi8+PHBhdGggZD0iTTMxIDI5LjVsMS41IDIuNWgtMjBsMS41LTIuNSIvPjxwYXRoIGQ9Ik0xMSAxNGgyMyIgZmlsbD0ibm9uZSIgc3Ryb2tlLWxpbmVqb2luPSJtaXRlciIvPjwvZz48L3N2Zz4=");
    }

    .mini-piece.piece.white.queen {
        background-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0NSIgaGVpZ2h0PSI0NSI+PGcgZmlsbD0iI2ZmZiIgZmlsbC1ydWxlPSJldmVub2RkIiBzdHJva2U9IiMwMDAiIHN0cm9rZS13aWR0aD0iMS41IiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwYXRoIGQ9Ik04IDEyYTIgMiAwIDEgMS00IDAgMiAyIDAgMSAxIDQgMHptMTYuNS00LjVhMiAyIDAgMSAxLTQgMCAyIDIgMCAxIDEgNCAwek00MSAxMmEyIDIgMCAxIDEtNCAwIDIgMiAwIDEgMSA0IDB6TTE2IDguNWEyIDIgMCAxIDEtNCAwIDIgMiAwIDEgMSA0IDB6TTMzIDlhMiAyIDAgMSAxLTQgMCAyIDIgMCAxIDEgNCAweiIvPjxwYXRoIGQ9Ik05IDI2YzguNS0xLjUgMjEtMS41IDI3IDBsMi0xMi03IDExVjExbC01LjUgMTMuNS0zLTE1LTMgMTUtNS41LTE0VjI1TDcgMTRsMiAxMnoiIHN0cm9rZS1saW5lY2FwPSJidXR0Ii8+PHBhdGggZD0iTTkgMjZjMCAyIDEuNSAyIDIuNSA0IDEgMS41IDEgMSAuNSAzLjUtMS41IDEtMS41IDIuNS0xLjUgMi41LTEuNSAxLjUuNSAyLjUuNSAyLjUgNi41IDEgMTYuNSAxIDIzIDAgMCAwIDEuNS0xIDAtMi41IDAgMCAuNS0xLjUtMS0yLjUtLjUtMi41LS41LTIgLjUtMy41IDEtMiAyLjUtMiAyLjUtNC04LjUtMS41LTE4LjUtMS41LTI3IDB6IiBzdHJva2UtbGluZWNhcD0iYnV0dCIvPjxwYXRoIGQ9Ik0xMS41IDMwYzMuNS0xIDE4LjUtMSAyMiAwTTEyIDMzLjVjNi0xIDE1LTEgMjEgMCIgZmlsbD0ibm9uZSIvPjwvZz48L3N2Zz4=");
    }

    .mini-piece.piece.black.pawn {
        background-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0NSIgaGVpZ2h0PSI0NSI+PHBhdGggZD0iTTIyLjUgOWMtMi4yMSAwLTQgMS43OS00IDQgMCAuODkuMjkgMS43MS43OCAyLjM4QzE3LjMzIDE2LjUgMTYgMTguNTkgMTYgMjFjMCAyLjAzLjk0IDMuODQgMi40MSA1LjAzLTMgMS4wNi03LjQxIDUuNTUtNy40MSAxMy40N2gyM2MwLTcuOTItNC40MS0xMi40MS03LjQxLTEzLjQ3IDEuNDctMS4xOSAyLjQxLTMgMi40MS01LjAzIDAtMi40MS0xLjMzLTQuNS0zLjI4LTUuNjIuNDktLjY3Ljc4LTEuNDkuNzgtMi4zOCAwLTIuMjEtMS43OS00LTQtNHoiIHN0cm9rZT0iIzAwMCIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPjwvc3ZnPg==");
    }

    .mini-piece.piece.black.knight {
        background-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0NSIgaGVpZ2h0PSI0NSI+PGcgZmlsbD0ibm9uZSIgZmlsbC1ydWxlPSJldmVub2RkIiBzdHJva2U9IiMwMDAiIHN0cm9rZS13aWR0aD0iMS41IiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwYXRoIGQ9Ik0yMiAxMGMxMC41IDEgMTYuNSA4IDE2IDI5SDE1YzAtOSAxMC02LjUgOC0yMSIgZmlsbD0iIzAwMCIvPjxwYXRoIGQ9Ik0yNCAxOGMuMzggMi45MS01LjU1IDcuMzctOCA5LTMgMi0yLjgyIDQuMzQtNSA0LTEuMDQyLS45NCAxLjQxLTMuMDQgMC0zLTEgMCAuMTkgMS4yMy0xIDItMSAwLTQuMDAzIDEtNC00IDAtMiA2LTEyIDYtMTJzMS44OS0xLjkgMi0zLjVjLS43My0uOTk0LS41LTItLjUtMyAxLTEgMyAyLjUgMyAyLjVoMnMuNzgtMS45OTIgMi41LTNjMSAwIDEgMyAxIDMiIGZpbGw9IiMwMDAiLz48cGF0aCBkPSJNOS41IDI1LjVhLjUuNSAwIDEgMS0xIDAgLjUuNSAwIDEgMSAxIDB6bTUuNDMzLTkuNzVhLjUgMS41IDMwIDEgMS0uODY2LS41LjUgMS41IDMwIDEgMSAuODY2LjV6IiBmaWxsPSIjZWNlY2VjIiBzdHJva2U9IiNlY2VjZWMiLz48cGF0aCBkPSJNMjQuNTUgMTAuNGwtLjQ1IDEuNDUuNS4xNWMzLjE1IDEgNS42NSAyLjQ5IDcuOSA2Ljc1UzM1Ljc1IDI5LjA2IDM1LjI1IDM5bC0uMDUuNWgyLjI1bC4wNS0uNWMuNS0xMC4wNi0uODgtMTYuODUtMy4yNS0yMS4zNC0yLjM3LTQuNDktNS43OS02LjY0LTkuMTktNy4xNmwtLjUxLS4xeiIgZmlsbD0iI2VjZWNlYyIgc3Ryb2tlPSJub25lIi8+PC9nPjwvc3ZnPg==");
    }

    .mini-piece.piece.black.bishop {
        background-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0NSIgaGVpZ2h0PSI0NSI+PGcgZmlsbD0ibm9uZSIgZmlsbC1ydWxlPSJldmVub2RkIiBzdHJva2U9IiMwMDAiIHN0cm9rZS13aWR0aD0iMS41IiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxnIGZpbGw9IiMwMDAiIHN0cm9rZS1saW5lY2FwPSJidXR0Ij48cGF0aCBkPSJNOSAzNmMzLjM5LS45NyAxMC4xMS40MyAxMy41LTIgMy4zOSAyLjQzIDEwLjExIDEuMDMgMTMuNSAyIDAgMCAxLjY1LjU0IDMgMi0uNjguOTctMS42NS45OS0zIC41LTMuMzktLjk3LTEwLjExLjQ2LTEzLjUtMS0zLjM5IDEuNDYtMTAuMTEuMDMtMTMuNSAxLTEuMzU0LjQ5LTIuMzIzLjQ3LTMtLjUgMS4zNTQtMS45NCAzLTIgMy0yeiIvPjxwYXRoIGQ9Ik0xNSAzMmMyLjUgMi41IDEyLjUgMi41IDE1IDAgLjUtMS41IDAtMiAwLTIgMC0yLjUtMi41LTQtMi41LTQgNS41LTEuNSA2LTExLjUtNS0xNS41LTExIDQtMTAuNSAxNC01IDE1LjUgMCAwLTIuNSAxLjUtMi41IDQgMCAwLS41LjUgMCAyeiIvPjxwYXRoIGQ9Ik0yNSA4YTIuNSAyLjUgMCAxIDEtNSAwIDIuNSAyLjUgMCAxIDEgNSAweiIvPjwvZz48cGF0aCBkPSJNMTcuNSAyNmgxME0xNSAzMGgxNW0tNy41LTE0LjV2NU0yMCAxOGg1IiBzdHJva2U9IiNlY2VjZWMiIHN0cm9rZS1saW5lam9pbj0ibWl0ZXIiLz48L2c+PC9zdmc+");
    }

    .mini-piece.piece.black.rook {
        background-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0NSIgaGVpZ2h0PSI0NSI+PGcgZmlsbC1ydWxlPSJldmVub2RkIiBzdHJva2U9IiMwMDAiIHN0cm9rZS13aWR0aD0iMS41IiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwYXRoIGQ9Ik05IDM5aDI3di0zSDl2M3ptMy41LTdsMS41LTIuNWgxN2wxLjUgMi41aC0yMHptLS41IDR2LTRoMjF2NEgxMnoiIHN0cm9rZS1saW5lY2FwPSJidXR0Ii8+PHBhdGggZD0iTTE0IDI5LjV2LTEzaDE3djEzSDE0eiIgc3Ryb2tlLWxpbmVjYXA9ImJ1dHQiIHN0cm9rZS1saW5lam9pbj0ibWl0ZXIiLz48cGF0aCBkPSJNMTQgMTYuNUwxMSAxNGgyM2wtMyAyLjVIMTR6TTExIDE0VjloNHYyaDVWOWg1djJoNVY5aDR2NUgxMXoiIHN0cm9rZS1saW5lY2FwPSJidXR0Ii8+PHBhdGggZD0iTTEyIDM1LjVoMjFtLTIwLTRoMTltLTE4LTJoMTdtLTE3LTEzaDE3TTExIDE0aDIzIiBmaWxsPSJub25lIiBzdHJva2U9IiNlY2VjZWMiIHN0cm9rZS13aWR0aD0iMSIgc3Ryb2tlLWxpbmVqb2luPSJtaXRlciIvPjwvZz48L3N2Zz4=");
    }

    .mini-piece.piece.black.queen {
        background-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0NSIgaGVpZ2h0PSI0NSI+PGcgZmlsbC1ydWxlPSJldmVub2RkIiBzdHJva2U9IiMwMDAiIHN0cm9rZS13aWR0aD0iMS41IiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxnIHN0cm9rZT0ibm9uZSI+PGNpcmNsZSBjeD0iNiIgY3k9IjEyIiByPSIyLjc1Ii8+PGNpcmNsZSBjeD0iMTQiIGN5PSI5IiByPSIyLjc1Ii8+PGNpcmNsZSBjeD0iMjIuNSIgY3k9IjgiIHI9IjIuNzUiLz48Y2lyY2xlIGN4PSIzMSIgY3k9IjkiIHI9IjIuNzUiLz48Y2lyY2xlIGN4PSIzOSIgY3k9IjEyIiByPSIyLjc1Ii8+PC9nPjxwYXRoIGQ9Ik05IDI2YzguNS0xLjUgMjEtMS41IDI3IDBsMi41LTEyLjVMMzEgMjVsLS4zLTE0LjEtNS4yIDEzLjYtMy0xNC41LTMgMTQuNS01LjItMTMuNkwxNCAyNSA2LjUgMTMuNSA5IDI2eiIgc3Ryb2tlLWxpbmVjYXA9ImJ1dHQiLz48cGF0aCBkPSJNOSAyNmMwIDIgMS41IDIgMi41IDQgMSAxLjUgMSAxIC41IDMuNS0xLjUgMS0xLjUgMi41LTEuNSAyLjUtMS41IDEuNS41IDIuNS41IDIuNSA2LjUgMSAxNi41IDEgMjMgMCAwIDAgMS41LTEgMC0yLjUgMCAwIC41LTEuNS0xLTIuNS0uNS0yLjUtLjUtMiAuNS0zLjUgMS0yIDIuNS0yIDIuNS00LTguNS0xLjUtMTguNS0xLjUtMjcgMHoiIHN0cm9rZS1saW5lY2FwPSJidXR0Ii8+PHBhdGggZD0iTTExIDM4LjVhMzUgMzUgMSAwIDAgMjMgMCIgZmlsbD0ibm9uZSIgc3Ryb2tlLWxpbmVjYXA9ImJ1dHQiLz48cGF0aCBkPSJNMTEgMjlhMzUgMzUgMSAwIDEgMjMgMG0tMjEuNSAyLjVoMjBtLTIxIDNhMzUgMzUgMSAwIDAgMjIgMG0tMjMgM2EzNSAzNSAxIDAgMCAyNCAwIiBmaWxsPSJub25lIiBzdHJva2U9IiNlY2VjZWMiLz48L2c+PC9zdmc+");
    }

    .adv {
        font-weight: 700;
        font-size: 0.9rem;
        min-width: 28px;
        text-align: right;
        color: #111827;
        background: rgba(255, 255, 255, 0.75);
        border-radius: 999px;
        padding: 2px 8px;
        pointer-events: none;
        margin-left: auto;
    }

    .panel {
        display: flex;
        flex-direction: column;
        gap: 1rem;
        padding: 1rem;
        background: rgba(15, 23, 42, 0.05);
        border-radius: 1rem;
    }

    .status {
        font-weight: 600;
        font-size: 1.1rem;
    }

    .actions {
        display: flex;
        gap: 0.75rem;
    }

    button {
        padding: 0.6rem 1.2rem;
        border-radius: 999px;
        border: none;
        font-weight: 600;
        letter-spacing: 0.01em;
        background: #1d4ed8;
        color: white;
        cursor: pointer;
        transition:
            transform 120ms ease,
            box-shadow 120ms ease,
            background 120ms ease;
    }

    button:disabled {
        cursor: not-allowed;
        opacity: 0.55;
        box-shadow: none;
    }

    button:not(:disabled):hover {
        transform: translateY(-1px);
        box-shadow: 0 8px 18px rgba(29, 78, 216, 0.3);
        background: #2563eb;
    }

    .replay-bar {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        justify-content: space-between;
        gap: 0.75rem;
        margin: 0.75rem auto 0;
        padding: 0.6rem 1rem;
        width: min(100%, 860px);
        border-radius: 0.9rem;
        background: rgba(15, 23, 42, 0.06);
        box-shadow: 0 10px 20px rgba(15, 23, 42, 0.12);
        grid-column: 1 / -1;
    }

    .replay-controls {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .replay-bar button {
        padding: 0.45rem 0.9rem;
        min-width: 2.25rem;
    }

    .replay-hint {
        font-size: 0.9rem;
        color: #334155;
        font-weight: 600;
    }

    .replay-progress {
        font-size: 0.9rem;
        font-weight: 600;
        color: #1e293b;
    }

    @media (max-width: 640px) {
        .chess-widget {
            gap: 1rem;
        }

        .board-stack {
            width: 100%;
            gap: 0.25rem;
        }

        .board {
            width: 100%;
            margin-inline: 0;
            border-radius: 0.75rem;
            box-shadow: 0 10px 20px rgba(15, 23, 42, 0.18);
        }

        .captured-slot {
            width: 100%;
            padding-inline: 0.4rem;
        }

        .captured-slot:not(.empty) {
            border-radius: 0.6rem;
        }

        .replay-bar {
            width: 100%;
            margin-top: 0.5rem;
            padding-inline: 0.75rem;
        }

        .adv {
            font-size: 0.8rem;
            padding: 2px 6px;
        }
    }

    .promotion-overlay {
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(15, 23, 42, 0.55);
        backdrop-filter: blur(2px);
        z-index: 5;
    }

    .promotion-card {
        display: flex;
        flex-direction: column;
        gap: 1rem;
        padding: 1.25rem;
        width: min(90%, 260px);
        border-radius: 0.75rem;
        background: rgba(15, 23, 42, 0.92);
        color: #f8fafc;
        box-shadow: 0 16px 32px rgba(15, 23, 42, 0.45);
    }

    .promotion-heading {
        font-weight: 600;
        font-size: 1.05rem;
        text-align: center;
    }

    .promotion-options {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.75rem;
    }

    .promotion-choice {
        background: #f1f5f9;
        color: #111827;
        border-radius: 0.75rem;
        padding: 0.75rem 0.5rem;
        font-weight: 600;
        letter-spacing: 0.01em;
    }

    .promotion-choice:hover {
        background: #e2e8f0;
    }

    .promotion-cancel {
        background: transparent;
        border: 1px solid rgba(248, 250, 252, 0.35);
        color: #f8fafc;
    }

    .promotion-cancel:hover {
        background: rgba(248, 250, 252, 0.1);
    }
</style>
