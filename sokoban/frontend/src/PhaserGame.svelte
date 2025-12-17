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

    onMount(() => {
        phaserRef.game = StartGame("game-container");

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
    });

    onDestroy(() => {
        EventBus.removeAllListeners("current-scene-ready");

        phaserRef.game?.destroy(true);

        phaserRef.game = null;
        phaserRef.scene = null;
    });
</script>

<div id="game-container"></div>
