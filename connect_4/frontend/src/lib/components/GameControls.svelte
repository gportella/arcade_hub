<script>
    export let onReset;

    function handleReset() {
        if (typeof onReset === "function") {
            onReset();
        }
    }
</script>

<div class="controls">
    <button type="button" on:click={handleReset}>Reset Board</button>
</div>

<style>
    .controls {
        display: flex;
        justify-content: center;
        margin-top: 1rem;
    }

    button {
        padding: 0.6rem 1.2rem;
        border: none;
        border-radius: 999px;
        background: var(--accent-color);
        color: white;
        font-size: 0.95rem;
        font-weight: 600;
        cursor: pointer;
        transition:
            transform 100ms ease,
            box-shadow 100ms ease;
    }

    button:hover {
        transform: translateY(-1px);
        box-shadow: 0 0.5rem 1rem rgba(40, 60, 120, 0.35);
    }

    button:active {
        transform: translateY(0);
        box-shadow: none;
    }
</style>
