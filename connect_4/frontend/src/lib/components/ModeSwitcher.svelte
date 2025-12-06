<script>
    import { MODES } from "../../lib/constants.js";

    export let mode = MODES.SOLO;
    export let onModeChange = undefined;

    function handleChange(event) {
        const value = event.target.value;
        if (typeof onModeChange === "function") {
            onModeChange(value);
        }
    }
</script>

<fieldset class="mode-switcher" aria-label="Game mode">
    <legend>Game Mode</legend>
    <label>
        <input
            type="radio"
            name="mode"
            value={MODES.SOLO}
            checked={mode === MODES.SOLO}
            on:change={handleChange}
        />
        Solo (vs computer)
    </label>
    <label>
        <input
            type="radio"
            name="mode"
            value={MODES.MULTIPLAYER}
            checked={mode === MODES.MULTIPLAYER}
            on:change={handleChange}
        />
        Two Players (local)
    </label>
</fieldset>

<style>
    fieldset {
        border: none;
        padding: 0;
        margin: 0;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    legend {
        font-weight: 600;
        margin-bottom: 0.5rem;
    }

    label {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        cursor: pointer;
    }

    input[type="radio"] {
        accent-color: var(--accent-color);
    }
</style>
