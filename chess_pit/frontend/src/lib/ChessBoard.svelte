<script>
    import { onMount } from "svelte";
    import { Chess } from "chess.js";
    import { Chessground } from "svelte5-chessground";
    import "@lichess-org/chessground/assets/chessground.base.css";
    import "@lichess-org/chessground/assets/chessground.brown.css";
    import "@lichess-org/chessground/assets/chessground.cburnett.css";

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
    let statusText = "";
    /** @type {import("chessground/types").Key[]} */
    let lastMove = [];
    let hasHistory = false;
    let hasMounted = false;
    let lastAppliedFen = null;
    let previousStartingFen = null;
    let currentFen = game.fen();
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

    /** @type {"white" | "black"} */
    export let orientation = "white";
    export let startingFen = null;
    export let onMove = (_detail) => {};
    export let onUndo = (_detail) => {};
    export let onReset = (_detail) => {};
    export let showStatus = true;
    export let showControls = true;

    function initialiseGame() {
        if (startingFen) {
            try {
                game.load(startingFen);
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
        lastAppliedFen = game.fen();
        previousStartingFen = startingFen;
        updateState();
    }

    onMount(() => {
        hasMounted = true;
        initialiseGame();
    });

    $: resolvedOrientation = orientation === "black" ? "black" : "white";

    $: if (hasMounted) {
        if (startingFen && startingFen !== lastAppliedFen) {
            initialiseGame();
        } else if (startingFen === null && previousStartingFen !== null) {
            initialiseGame();
        }
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
        currentFen = game.fen();
        movableColor = playerTurnColor();
        movableDests = computeDestinations();
        isInCheck = game.inCheck();
        checkColor = isInCheck ? movableColor : false;
        hasHistory = game.history().length > 0;
        boardApi?.set({
            fen: currentFen,
            turnColor: movableColor,
            orientation: resolvedOrientation,
            lastMove,
            check: checkColor,
            movable: {
                free: false,
                color: movableColor,
                dests: movableDests,
                showDests: true,
            },
            highlight: {
                lastMove,
                check: Boolean(checkColor),
            },
        });
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
        updateState();
        onMove({ move: executed, fen: game.fen() });
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
        updateState();
        onUndo({ move: undone, fen: game.fen() });
    }

    function reset() {
        game.reset();
        lastMove = [];
        showPromotionDialog = false;
        promotionPending = null;
        promotionOptions = [];
        updateState();
        onReset({ fen: game.fen() });
    }
</script>

<section class="chess-widget" class:compact={!showStatus && !showControls}>
    <div class="board" aria-label="Chess board">
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
        width: min(100%, 720px);
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
