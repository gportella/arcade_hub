<script>
    import { onMount } from "svelte";
    import {
        fetchPuzzleConfigurations,
        activatePuzzleConfiguration,
        loading,
    } from "../lib/puzzleStore";

    export let disabled = false;

    let options = [];
    let selected = "";
    let error = null;
    let busy = false;

    async function loadOptions() {
        error = null;
        try {
            const records = await fetchPuzzleConfigurations();
            options = Array.isArray(records) ? records : [];
            const active = options.find((item) => item.active);
            selected = active ? String(active.id) : "";
        } catch (err) {
            error =
                err instanceof Error ? err.message : "Failed to load puzzles.";
            options = [];
            selected = "";
        }
    }

    onMount(() => {
        void loadOptions();
    });

    async function handleChange(event) {
        const value = event.currentTarget.value;
        if (!value) {
            return;
        }
        busy = true;
        error = null;
        try {
            await activatePuzzleConfiguration(Number(value));
            await loadOptions();
        } catch (err) {
            error =
                err instanceof Error
                    ? err.message
                    : "Failed to activate puzzle.";
        } finally {
            busy = false;
        }
    }

    async function handleRefresh() {
        busy = true;
        await loadOptions();
        busy = false;
    }

    export function refresh() {
        return loadOptions();
    }
</script>

<div class="config-picker">
    <label class="config-picker__label">
        <span class="config-picker__caption">Active puzzle</span>
        <select
            class="config-picker__select"
            bind:value={selected}
            on:change={handleChange}
            disabled={disabled || busy || $loading || options.length === 0}
        >
            {#if options.length === 0}
                <option value="">No saved puzzles</option>
            {:else}
                {#if !selected}
                    <option value="" disabled>Select puzzle…</option>
                {/if}
                {#each options as option}
                    <option value={option.id}>
                        {option.name}
                    </option>
                {/each}
            {/if}
        </select>
    </label>
    <button
        type="button"
        class="config-picker__refresh"
        on:click={handleRefresh}
        disabled={disabled || busy || $loading}
        aria-label="Refresh puzzle list"
        title="Refresh puzzle list"
    >
        ↺
    </button>
</div>
{#if error}
    <p class="config-picker__error">{error}</p>
{/if}

<style>
    .config-picker {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        font-size: 0.85rem;
    }

    .config-picker__label {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
        flex: 1;
    }

    .config-picker__caption {
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 0.7rem;
        color: rgba(30, 41, 59, 0.6);
    }

    .config-picker__select {
        width: 100%;
        font-size: 0.85rem;
        padding: 0.35rem 0.45rem;
        border-radius: 0.5rem;
        border: 1px solid rgba(148, 163, 184, 0.5);
        background: rgba(255, 255, 255, 0.9);
    }

    .config-picker__refresh {
        border: none;
        background: rgba(15, 23, 42, 0.08);
        color: rgba(15, 23, 42, 0.75);
        border-radius: 0.5rem;
        padding: 0.3rem 0.5rem;
        line-height: 1;
        font-size: 0.85rem;
        transition: background 120ms ease;
    }

    .config-picker__refresh:enabled:hover {
        background: rgba(15, 23, 42, 0.16);
    }

    .config-picker__refresh:disabled {
        opacity: 0.4;
        cursor: default;
    }

    .config-picker__error {
        margin: 0.25rem 0 0;
        font-size: 0.75rem;
        color: #b91c1c;
    }
</style>
