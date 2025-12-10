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

    /** @returns {import("chessground/types").Dests} */
    function computeDestinations() {
        const destinations = new Map();
        for (const move of game.moves({ verbose: true })) {
            const squares = destinations.get(move.from) ?? [];
            squares.push(move.to);
            destinations.set(move.from, squares);
        }
        return destinations;
    }

    /** @returns {"white" | "black"} */
    function playerTurnColor() {
        return game.turn() === "w" ? "white" : "black";
    }

    function computeStatus() {
        if (game.isCheckmate()) {
            const winner = game.turn() === "w" ? "Black" : "White";
            return `${winner} wins by checkmate`;
        }
        if (game.isStalemate()) {
            return "Draw by stalemate";
        }
        if (game.isDraw()) {
            return "Draw";
        }
        const player = playerTurnColor() === "white" ? "White" : "Black";
        const suffix = game.inCheck() ? " (check)" : "";
        return `${player} to move${suffix}`;
    }

    function updateState() {
        statusText = computeStatus();
        const newFen = normalizeFen(game.fen()) ?? game.fen();
        movableColor = playerTurnColor();
        movableDests = computeDestinations();
        isInCheck = game.inCheck();
        checkColor = isInCheck ? movableColor : false;
        hasHistory = game.history().length > 0;

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
                color: interactive ? movableColor : undefined,
                dests: interactive ? movableDests : new Map(),
                showDests: interactive,
            },
            draggable: {
                enabled: interactive,
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
            color: playerTurnColor(),
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
        if (!promotionPending) {
            return;
        }
        if (!promotionOptions.includes(piece)) {
            return;
        }
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
        if (!interactive) {
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
        if (!undone) {
            return;
        }
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
        if (!interactive) {
            return;
        }
        undo();
    }

    export function resetPosition() {
        reset();
    }
</script>

<section class="chess-widget" class:compact={!showStatus && !showControls}>
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
