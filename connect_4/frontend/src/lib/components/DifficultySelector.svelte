<script>
    import {
        DEFAULT_DIFFICULTY,
        DIFFICULTIES,
        DIFFICULTY_DEPTH,
        DIFFICULTY_LABELS,
    } from "../../lib/constants.js";

    export let difficulty = DEFAULT_DIFFICULTY;
    export let onDifficultyChange = undefined;
    export let disabled = false;

    const ORDER = [
        DIFFICULTIES.CASUAL,
        DIFFICULTIES.STANDARD,
        DIFFICULTIES.CHALLENGER,
        DIFFICULTIES.EXPERT,
    ];

    $: activeIndex = Math.max(0, ORDER.indexOf(difficulty));
    $: activeDifficulty = ORDER[activeIndex] ?? DEFAULT_DIFFICULTY;
    $: activeLabel = DIFFICULTY_LABELS[activeDifficulty];
    $: activeDepth = DIFFICULTY_DEPTH[activeDifficulty];

    function updateDifficulty(index) {
        const next = ORDER[index];
        if (!next || next === difficulty) {
            return;
        }
        if (typeof onDifficultyChange === "function") {
            onDifficultyChange(next);
        }
    }

    function handleInput(event) {
        const value = Number(event.target.value);
        updateDifficulty(value);
    }

    function handleClick(index) {
        updateDifficulty(index);
    }
</script>

<div class="difficulty">
    <div class="difficulty__header">
        <label for="difficulty-slider">AI Strength</label>
        <span>{activeLabel} (depth {activeDepth})</span>
    </div>
    <input
        id="difficulty-slider"
        class="difficulty__slider"
        type="range"
        min="0"
        max={ORDER.length - 1}
        step="1"
        value={activeIndex}
        {disabled}
        aria-label="AI difficulty"
        aria-valuemin="0"
        aria-valuemax={ORDER.length - 1}
        aria-valuenow={activeIndex}
        aria-valuetext={`${activeLabel} depth ${activeDepth}`}
        list="difficulty-ticks"
        on:input={handleInput}
    />
    <div class="difficulty__ticks" aria-hidden="true">
        {#each ORDER as value, index}
            <button
                type="button"
                class:active={index === activeIndex}
                on:click={() => handleClick(index)}
                {disabled}
            >
                {DIFFICULTY_LABELS[value]}
            </button>
        {/each}
    </div>
</div>

<datalist id="difficulty-ticks">
    {#each ORDER as value, index}
        <option value={index} label={DIFFICULTY_LABELS[value]}></option>
    {/each}
</datalist>

<style>
    .difficulty {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }

    .difficulty__header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.9rem;
        font-weight: 500;
        color: rgba(255, 255, 255, 0.8);
    }

    .difficulty__header label {
        font-weight: 600;
        color: inherit;
    }

    .difficulty__slider {
        width: 100%;
        accent-color: var(--accent-color);
    }

    .difficulty__ticks {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.5rem;
        text-align: center;
    }

    .difficulty__ticks button {
        background: transparent;
        border: none;
        padding: 0.35rem 0.25rem;
        border-radius: 0.65rem;
        font-size: 0.75rem;
        color: rgba(255, 255, 255, 0.7);
        cursor: pointer;
        transition:
            background 0.2s ease,
            color 0.2s ease;
    }

    .difficulty__ticks button.active {
        background: rgba(255, 255, 255, 0.15);
        color: white;
        font-weight: 600;
    }

    .difficulty__ticks button:disabled {
        cursor: default;
        opacity: 0.5;
    }

    @media (max-width: 640px) {
        .difficulty__ticks {
            gap: 0.35rem;
            font-size: 0.7rem;
        }

        .difficulty__header {
            flex-direction: column;
            align-items: flex-start;
            gap: 0.25rem;
        }
    }
</style>
