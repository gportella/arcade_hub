<script>
    import ChessBoard from "../ChessBoard.svelte";

    /** @type {any} */
    export let game = null;
    export let formatTime = (_iso) => "";
    export let gameStatusLabel = (_game) => "";
    export let colorLabel = (_color) => "";
    export let onMove = (_event) => {};
    export let onUndo = (_event) => {};
    export let onResign = () => {};
    export let onBack = () => {};
    export let onLogout = () => {};

    const isActiveGame = () =>
        game?.status === "active" || game?.status === "pending";
    let boardRef;
    let yourTurn = false;

    const handleUndoClick = () => {
        if (!yourTurn) return;
        boardRef?.undoMove();
    };

    const handleResignClick = () => {
        if (!active) return;
        onResign();
    };

    $: active = isActiveGame();
    $: yourTurn = active && game?.turn === game?.yourColor;
    $: opponentName = game?.opponent?.nickname ?? "";
    $: opponentAvatar = game?.opponent?.avatar ?? "";
    $: lastUpdated = game ? formatTime(game.lastUpdated) : "";
    $: statusLabel = game ? gameStatusLabel(game) : "";
    $: color = game ? colorLabel(game.yourColor) : "";
    $: resultLabel = game?.resultDisplay ?? null;
    $: summary = game?.summary ?? "";
    $: pgn = game?.pgn ?? "";
</script>

{#if game}
    <main class="play">
        <header class="play-header">
            <button class="ghost" on:click={onBack} aria-label="Back to games">
                ← Games
            </button>
            <div class="match-overview">
                <div class="opponent">
                    <img
                        src={opponentAvatar}
                        alt={`Avatar of ${opponentName}`}
                    />
                    <div>
                        <h1>{opponentName}</h1>
                        <p class="meta">
                            You play {color}
                            {#if statusLabel}
                                · {statusLabel}
                            {/if}
                        </p>
                    </div>
                </div>
                <p class="timestamp">Updated {lastUpdated}</p>
            </div>
            <button class="secondary micro" on:click={onLogout}>Log out</button>
        </header>

        <section class="board-section">
            <ChessBoard
                bind:this={boardRef}
                startingFen={game.initialFen}
                positionFen={game.fen}
                resetToken={game.id}
                orientation={game.yourColor}
                {onMove}
                {onUndo}
                showStatus={false}
                showControls={false}
                interactive={yourTurn}
            />
            {#if active}
                <div class="board-controls" aria-label="Board controls">
                    <!--
                    <button
                        class="pill"
                        on:click={handleUndoClick}
                        disabled={!yourTurn}
                    >
                        Undo
                    </button>
                    -->
                    <button class="pill resign" on:click={handleResignClick}>
                        Resign
                    </button>
                </div>
            {/if}
        </section>

        <section class="game-info">
            {#if summary}
                <div class="info-card">
                    <h2>Summary</h2>
                    <p>{summary}</p>
                </div>
            {/if}
            {#if resultLabel}
                <div class="info-card">
                    <h2>Result</h2>
                    <p>{resultLabel}</p>
                </div>
            {/if}
            {#if pgn}
                <div class="info-card">
                    <h2>PGN</h2>
                    <textarea readonly rows="6">{pgn}</textarea>
                </div>
            {/if}
        </section>
    </main>
{:else}
    <main class="play empty">
        <header class="play-header">
            <button class="ghost" on:click={onBack}>← Games</button>
            <span></span>
            <button class="secondary micro" on:click={onLogout}>Log out</button>
        </header>
        <p class="placeholder">No game selected.</p>
    </main>
{/if}

<style>
    .play {
        min-height: 100vh;
        display: flex;
        flex-direction: column;
        gap: clamp(1rem, 3vw, 1.5rem);
        padding: clamp(0.75rem, 3vw, 1.25rem) clamp(1rem, 4vw, 2.25rem) 2.5rem;
    }

    .play.empty {
        align-items: center;
        justify-content: flex-start;
    }

    .play-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
    }

    .match-overview {
        display: flex;
        flex-direction: column;
        gap: 0.6rem;
        align-items: flex-start;
    }

    .opponent {
        display: flex;
        gap: 0.75rem;
        align-items: center;
    }

    .opponent img {
        width: 52px;
        height: 52px;
        border-radius: 20px;
        object-fit: cover;
        border: 1px solid rgba(148, 163, 184, 0.35);
    }

    .match-overview h1 {
        margin: 0;
        font-size: clamp(1.6rem, 4vw, 2.1rem);
        color: #f8fafc;
    }

    .meta {
        margin: 0.25rem 0 0;
        color: rgba(226, 232, 240, 0.72);
        font-size: 0.95rem;
    }

    .timestamp {
        margin: 0;
        color: rgba(148, 163, 184, 0.75);
        font-size: 0.85rem;
    }

    .board-section {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.75rem;
    }

    .board-section :global(.chess-widget) {
        width: 100%;
    }

    .board-controls {
        display: flex;
        gap: 0.65rem;
        justify-content: center;
        flex-wrap: wrap;
    }

    .pill {
        padding: 0.45rem 0.95rem;
        border-radius: 999px;
        border: none;
        font-weight: 600;
        letter-spacing: 0.01em;
        background: rgba(37, 99, 235, 0.85);
        color: #eaf2ff;
        cursor: pointer;
        transition: background 0.15s ease;
    }

    .pill:hover {
        background: rgba(59, 130, 246, 0.95);
    }

    .pill:disabled {
        opacity: 0.5;
        cursor: not-allowed;
        box-shadow: none;
    }

    .pill.resign {
        background: rgba(239, 68, 68, 0.88);
        color: #fee2e2;
    }

    .pill.resign:hover {
        background: rgba(220, 38, 38, 0.95);
    }

    .game-info {
        display: grid;
        gap: 1rem;
        width: min(100%, 720px);
        margin: 0 auto;
    }

    .info-card {
        background: rgba(15, 23, 42, 0.6);
        border-radius: 16px;
        padding: 1rem 1.1rem;
        display: grid;
        gap: 0.5rem;
    }

    .info-card h2 {
        margin: 0;
        color: #f8fafc;
        font-size: 1.05rem;
    }

    .info-card p {
        margin: 0;
        color: rgba(226, 232, 240, 0.72);
        line-height: 1.5;
    }

    textarea {
        width: 100%;
        border-radius: 12px;
        border: 1px solid rgba(148, 163, 184, 0.3);
        background: rgba(2, 6, 23, 0.6);
        color: #e2e8f0;
        padding: 0.75rem;
        font-family: "JetBrains Mono", "Fira Code", monospace;
        resize: none;
        max-height: 240px;
        overflow-y: auto;
        line-height: 1.45;
    }

    .ghost {
        border: none;
        background: transparent;
        color: #bfdbfe;
        font-weight: 600;
        cursor: pointer;
        padding: 0.35rem 0.6rem;
    }

    .ghost:hover {
        color: #e0f2fe;
    }

    .secondary.micro {
        padding: 0.45em 0.9em;
        font-size: 0.85rem;
    }

    .placeholder {
        margin-top: 4rem;
        color: rgba(226, 232, 240, 0.7);
    }

    @media (max-width: 640px) {
        .play {
            padding-inline: 1rem;
            gap: 1rem;
        }

        .play-header {
            flex-wrap: wrap;
            gap: 0.75rem;
        }

        .match-overview {
            width: 100%;
            order: 3;
        }

        .board-section {
            gap: 0.65rem;
        }

        .board-controls {
            width: 100%;
            justify-content: space-between;
        }

        .ghost {
            padding-left: 0;
        }
    }
</style>
