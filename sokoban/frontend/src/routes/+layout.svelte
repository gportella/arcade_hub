<svelte:head>
    <title>Phaser Svelte Template</title>
</svelte:head>

<div class="layout-root">
    <slot />
</div>

<style>
    .layout-root {
        min-height: 100vh;
    }

    :global(body) {
        margin: 0;
        padding: 0;
        color: rgba(255, 255, 255, 0.87);
        background-color: #000000;
        font-family: Arial, Helvetica, sans-serif;
    }
</style>