<script>
    import ChessBoard from "../ChessBoard.svelte";

    export let showcaseFen = "";
    export let onPlay = () => {};
    export let onAdminLogin = () => {};
</script>

<main class="landing">
    <section class="landing-card glass-panel">
        <div class="landing-header">
            <span class="landing-badge">Arcade Hub · Chess Pit</span>
            <h1>Ready when you are</h1>
            <p class="landing-copy">
                Fire up the board, then tap play to jump straight into your
                matches.
            </p>
        </div>
        <div class="landing-board-shell">
            <ChessBoard
                startingFen={showcaseFen}
                showStatus={false}
                showControls={false}
            />
        </div>
        <div class="landing-actions">
            <button on:click={onPlay}>Play!</button>
            <button class="secondary compact" on:click={onAdminLogin}
                >Admin login</button
            >
        </div>
    </section>
</main>

<style>
    .landing {
        width: min(480px, 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto;
    }

    .landing-card {
        width: 100%;
        padding: clamp(1.75rem, 5vw, 2.5rem);
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
    }

    .landing-header {
        display: grid;
        gap: 0.75rem;
        text-align: center;
    }

    .landing-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.35rem 0.9rem;
        border-radius: 999px;
        background: rgba(37, 99, 235, 0.18);
        color: #93c5fd;
        font-weight: 600;
        font-size: 0.85rem;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }

    h1 {
        font-size: clamp(2rem, 5.8vw, 2.75rem);
        margin: 0;
        color: #f8fafc;
    }

    .landing-copy {
        margin: 0;
        color: rgba(226, 232, 240, 0.76);
        max-width: 30ch;
        justify-self: center;
    }

    .landing-board-shell {
        display: flex;
        justify-content: center;
    }

    .landing-card :global(.chess-widget) {
        width: 100%;
    }

    .landing-card :global(.board) {
        width: min(320px, 78vw);
        margin-inline: auto;
    }

    .landing-actions {
        display: flex;
        gap: 0.75rem;
        flex-wrap: wrap;
        justify-content: center;
    }

    .landing-actions button:not(.compact) {
        flex: 1 1 auto;
        min-width: 0;
    }

    @media (max-width: 640px) {
        .landing-card {
            padding: 1.5rem;
            gap: 1.25rem;
        }

        .landing-actions {
            flex-direction: column;
            align-items: stretch;
        }

        .landing-actions button {
            width: 100%;
        }
    }
</style>
