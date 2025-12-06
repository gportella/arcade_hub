<script>
    import {
        COLOR_LABELS,
        COLORS,
        MODES,
        DIFFICULTY_LABELS,
        DIFFICULTY_DEPTH,
    } from "../../lib/constants.js";

    export let mode = MODES.SOLO;
    export let toPlay = COLORS.YELLOW;
    export let winner = null;
    export let draw = false;
    export let moveCount = 0;
    export let connectionState = "disconnected";
    export let error = null;
    export let difficulty = null;
    export let aiDepth = null;
    export let players = [];
    export let localColor = null;

    $: summary = (() => {
        if (error) {
            return error;
        }
        if (connectionState !== "connected") {
            return "Connecting…";
        }
        if (winner !== null) {
            return `${COLOR_LABELS[winner]} wins after ${moveCount} moves.`;
        }
        if (draw) {
            return `Draw game after ${moveCount} moves.`;
        }
        if (mode === MODES.MULTIPLAYER) {
            const playerCount = Array.isArray(players) ? players.length : 0;
            if (playerCount < 2) {
                return "Waiting for another player…";
            }
            if (typeof localColor === "number") {
                return localColor === toPlay
                    ? "Your move."
                    : "Opponent to play.";
            }
            return `${COLOR_LABELS[toPlay]} to play.`;
        }
        const opponent =
            mode === MODES.SOLO && toPlay === COLORS.RED
                ? "Computer"
                : COLOR_LABELS[toPlay];
        return `${opponent} to play.`;
    })();

    $: detail = (() => {
        if (mode !== MODES.SOLO || !difficulty) {
            return null;
        }
        const label = DIFFICULTY_LABELS[difficulty] ?? "";
        const depthValue =
            aiDepth != null ? aiDepth : (DIFFICULTY_DEPTH[difficulty] ?? null);
        if (!label || depthValue == null) {
            return label || null;
        }
        return `${label} - depth ${depthValue}`;
    })();
</script>

<div class="status" role="status" aria-live="polite">
    <div>{summary}</div>
    {#if detail}
        <div class="status__detail">{detail}</div>
    {/if}
</div>

<style>
    .status {
        padding: 0.75rem 1rem;
        background: rgba(255, 255, 255, 0.08);
        border-radius: 0.75rem;
        font-weight: 600;
        text-align: center;
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }

    .status__detail {
        font-size: 0.85rem;
        font-weight: 500;
        color: rgba(255, 255, 255, 0.75);
    }
</style>
