<script>
    import { calculateTrophies } from "../utils/trophies";

    export let wins = 0;
    export let maxCups = 4;
    export let size = 18;
    export let summary = "";
    export let title = "Trophies";
    export let emptyLabel = "No trophies yet";
    export let className = "";

    $: trophyData = calculateTrophies(wins, maxCups);
    $: cups = trophyData.cups;
    $: hasCups = cups.length > 0;
    $: fallbackSummary = hasCups
        ? `${title}: ${trophyData.representedWins}`
        : emptyLabel;
    $: ariaLabel = summary || fallbackSummary;
</script>

{#if hasCups}
    <div
        class={`trophy-display ${className}`.trim()}
        role="img"
        aria-label={ariaLabel}
        title={ariaLabel}
        style={`--cup-size: ${size}px`}
    >
        {#each cups as cup, index (index)}
            <svg
                class={`cup cup-${cup.type}`}
                viewBox="0 0 24 24"
                aria-hidden="true"
                focusable="false"
            >
                <path
                    d="M7 3h10v2h1.5a2.5 2.5 0 012.5 2.5c0 1.26-.92 2.3-2.12 2.48A6 6 0 0114 13.05V15h2.5a1 1 0 010 2H13v2.5h2.5a1 1 0 010 2h-7a1 1 0 010-2H11V17H7.5a1 1 0 010-2H10v-1.95a6 6 0 01-5.88-5.07A2.5 2.5 0 012 7.5 2.5 2.5 0 014.5 5H6V3zM5 7.5a.5.5 0 00.5.5H7V5H4.5a.5.5 0 00-.5.5.5.5 0 00.5.5H5zm14.5-2H17v3h1.5a.5.5 0 00.5-.5.5.5 0 00-.5-.5H19a.5.5 0 00.5-.5.5.5 0 00-.5-.5z"
                />
            </svg>
        {/each}
    </div>
{/if}

<style>
    .trophy-display {
        --cup-size: 18px;
        display: inline-flex;
        align-items: center;
        gap: calc(var(--cup-size) * 0.25);
    }

    .cup {
        width: var(--cup-size);
        height: var(--cup-size);
        display: block;
        fill: currentColor;
    }

    .cup-gold {
        color: #facc15;
    }

    .cup-silver {
        color: #cbd5f5;
    }

    .cup-bronze {
        color: #f97316;
    }
</style>
