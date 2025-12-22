<script>
    import { onMount } from "svelte";
    import PhaserGame from "../PhaserGame.svelte";
    import { EventBus } from "../game/EventBus";

    let phaserRef = { game: null, scene: null };
    let levelInfo = { id: "", name: "", index: 0, total: 0, hasNext: false, hasPrev: false, nextId: null, prevId: null };
    let statusMessage = "";
    let isLandscape = false;

    const handleRestart = (event) => {
        if (event && typeof event.preventDefault === "function") {
            event.preventDefault();
        }
        EventBus.emit("request-restart");
    };

    const handlePrev = (event) => {
        if (event && typeof event.preventDefault === "function") {
            event.preventDefault();
        }
        if (levelInfo?.prevId) {
            EventBus.emit("request-load-level", levelInfo.prevId);
        }
    };

    const handleNext = (event) => {
        if (event && typeof event.preventDefault === "function") {
            event.preventDefault();
        }
        if (levelInfo?.nextId) {
            EventBus.emit("request-load-level", levelInfo.nextId);
        }
    };

    onMount(() => {
        const updateOrientation = () => {
            if (typeof window === "undefined") {
                isLandscape = false;
                return;
            }
            const width = window.innerWidth || 0;
            const height = window.innerHeight || 0;
            isLandscape = width > height;
        };

        updateOrientation();
        window.addEventListener("resize", updateOrientation, { passive: true });

        const onLevelChanged = (info) => {
            levelInfo = info;
            statusMessage = "";
        };

        const onLevelComplete = (info) => {
            statusMessage = info?.nextId ? "Advancing to the next puzzle..." : "All puzzles solved!";
        };

        EventBus.on("level-changed", onLevelChanged);
        EventBus.on("level-complete", onLevelComplete);

        return () => {
            window.removeEventListener("resize", updateOrientation);
            EventBus.off("level-changed", onLevelChanged);
            EventBus.off("level-complete", onLevelComplete);
        };
    });
</script>

<div id="app">
    <div class={`hud ${isLandscape ? "hud--compact" : ""}`}>
        <div class="hud-info">
            <span class="hud-title">{levelInfo.name || "Loading puzzle..."}</span>
            {#if levelInfo.total > 0}
                <span class="hud-progress">Level {levelInfo.index + 1} / {levelInfo.total}</span>
            {/if}
        </div>
        <div class="hud-actions">
            <button
                class="button"
                type="button"
                on:click={handlePrev}
                on:touchend|preventDefault={handlePrev}
                disabled={!levelInfo.prevId}
            >
                Previous
            </button>
            <button
                class="button"
                type="button"
                on:click={handleRestart}
                on:touchend|preventDefault={handleRestart}
                disabled={!levelInfo.id}
            >
                Restart
            </button>
            <button
                class="button"
                type="button"
                on:click={handleNext}
                on:touchend|preventDefault={handleNext}
                disabled={!levelInfo.nextId}
            >
                Next
            </button>
        </div>
    </div>

    {#if statusMessage}
        <div class={`hud-status ${isLandscape ? "hud-status--compact" : ""}`}>{statusMessage}</div>
    {/if}

    <div class="game-shell">
        <PhaserGame {phaserRef} />
    </div>
</div>

<style>
    #app {
        width: 100%;
        height: 100vh;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: flex-start;
        gap: 12px;
        padding: 16px 12px;
        box-sizing: border-box;
        background: #1f2125;
    }

    .hud {
        width: min(960px, 100%);
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 16px;
        background: rgba(0, 0, 0, 0.6);
        border-radius: 6px;
        color: #ffffff;
        font-family: "Arial", sans-serif;
        gap: 8px;
        flex-wrap: wrap;
    }

    .hud-info {
        display: flex;
        flex-direction: column;
        gap: 2px;
    }

    .hud-title {
        font-size: 1rem;
        font-weight: 600;
    }

    .hud-progress {
        font-size: 0.85rem;
        opacity: 0.8;
    }

    .hud-actions {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        justify-content: flex-end;
    }

    .button {
        min-width: 120px;
        padding: 8px 14px;
        background-color: #20252d;
        color: #f5f5f5;
        border: 1px solid rgba(255, 255, 255, 0.6);
        cursor: pointer;
        transition: all 0.2s ease;
        font-size: 0.85rem;
        border-radius: 4px;
    }

    .button:hover:not(:disabled) {
        border-color: #0ec3c9;
        color: #0ec3c9;
    }

    .button:active:not(:disabled) {
        background-color: #0ec3c9;
        color: #101417;
    }

    .button:disabled {
        cursor: not-allowed;
        border-color: rgba(255, 255, 255, 0.25);
        color: rgba(255, 255, 255, 0.3);
    }

    .hud-status {
        width: min(960px, 100%);
        padding: 6px 12px;
        background: rgba(14, 195, 201, 0.25);
        color: #0ec3c9;
        border: 1px solid rgba(14, 195, 201, 0.5);
        border-radius: 4px;
        font-size: 0.85rem;
        text-align: center;
    }

    .game-shell {
        flex: 1;
        width: 100%;
        display: flex;
        justify-content: center;
        align-items: center;
        overflow: visible;
    }

    .hud.hud--compact {
        background: rgba(0, 0, 0, 0.45);
        padding: 4px 10px;
        font-size: 0.8rem;
    }

    .hud--compact .hud-info {
        flex: 1 1 auto;
        gap: 0;
    }

    .hud--compact .hud-title {
        font-size: 0.85rem;
        font-weight: 600;
    }

    .hud--compact .hud-progress {
        font-size: 0.75rem;
    }

    .hud--compact .hud-actions {
        flex-wrap: nowrap;
        gap: 6px;
    }

    .hud--compact .button {
        padding: 6px 10px;
        min-width: auto;
        font-size: 0.75rem;
    }

    .hud-status.hud-status--compact {
        font-size: 0.75rem;
        padding: 4px 8px;
    }

    @media (max-width: 640px) {
        .hud {
            flex-direction: column;
            align-items: stretch;
        }

        .hud-info {
            width: 100%;
        }

        .hud-actions {
            width: 100%;
            justify-content: space-between;
        }

        .button {
            flex: 1 1 30%;
            min-width: 0;
            text-align: center;
        }
    }
</style>
