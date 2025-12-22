<script lang="js">
    import { onDestroy, onMount } from "svelte";
    import StartGame from "./game/main";
    import { EventBus } from "./game/EventBus";

    /** @type {{ game: import('phaser').Game | null, scene: import('phaser').Scene | null }} */
    export let phaserRef = {
        game: null,
        scene: null,
    };

    /** @type {(scene: import('phaser').Scene) => void} */
    export let currentActiveScene = () => {};

    let resizeHandler;
    /** @type {HTMLElement | null} */
    let containerEl = null;

    const getContainerSize = () => {
        if (containerEl) {
            const rect = containerEl.getBoundingClientRect();
            const width = Math.max(1, Math.floor(rect.width));
            const height = Math.max(1, Math.floor(rect.height));
            return { width, height };
        }
        if (typeof window !== "undefined") {
            return {
                width: Math.max(1, Math.floor(window.innerWidth || 1024)),
                height: Math.max(1, Math.floor(window.innerHeight || 768))
            };
        }
        return { width: 1024, height: 768 };
    };

    onMount(() => {
        const { width, height } = getContainerSize();
        phaserRef.game = StartGame("game-container", width, height);

        EventBus.on(
            "current-scene-ready",
            /** @param {import('phaser').Scene} sceneInstance */ (
                sceneInstance,
            ) => {
                phaserRef.scene = sceneInstance;

                if (currentActiveScene) {
                    currentActiveScene(sceneInstance);
                }
            },
        );

        const applyResize = () => {
            if (typeof window === "undefined") return;
            if (!phaserRef.game) return;
            const { width, height } = getContainerSize();
            const scaleManager = phaserRef.game.scale;
            if (scaleManager) {
                scaleManager.setParentSize(width, height);
                scaleManager.setGameSize(width, height);
                scaleManager.refresh();
            }
        };

        resizeHandler = () => {
            window.requestAnimationFrame(applyResize);
        };

        window.addEventListener("resize", resizeHandler, { passive: true });
        window.addEventListener("orientationchange", resizeHandler, { passive: true });

        applyResize();
    });

    onDestroy(() => {
        EventBus.removeAllListeners("current-scene-ready");

        if (typeof window !== "undefined" && resizeHandler) {
            window.removeEventListener("resize", resizeHandler);
            window.removeEventListener("orientationchange", resizeHandler);
        }

        phaserRef.game?.destroy(true);

        phaserRef.game = null;
        phaserRef.scene = null;
    });
</script>

<div id="game-container" bind:this={containerEl}></div>

<style>
    #game-container {
        width: 100%;
        height: 100%;
        display: flex;
        justify-content: center;
        align-items: center;
    }

    :global(#game-container canvas) {
        max-width: 100%;
        max-height: 100%;
    }
</style>
