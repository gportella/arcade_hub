<script>
    /** @type {{ id: string; nickname: string; avatar: string; rating: number } | null} */
    export let user = null;
    /** @type {Array<any>} */
    export let games = [];
    export let selectedGameId = null;
    export let showNewGameForm = false;
    export let availableOpponents = [];
    export let newGameOpponentId = "";
    export let newGameColor = "white";
    export let formatTime = (_iso) => "";
    export let gameStatusLabel = (_game) => "";
    export let onOpenGame = (_id) => {};
    export let onToggleNewGameForm = () => {};
    export let onChangeOpponent = (_id) => {};
    export let onChangeColor = (_color) => {};
    export let onLaunchGame = () => {};
    export let onOpenProfile = () => {};
    export let onLogout = () => {};

    const unfinishedCount = () =>
        games.filter((game) => game.status !== "finished").length;
</script>

<main class="hub">
    <header class="hub-header">
        <div class="hub-actions">
            <button class="secondary micro" on:click={onLogout}>Log out</button>
            <button
                class="avatar-button"
                on:click={onOpenProfile}
                aria-label="Edit profile"
            >
                <img src={user.avatar} alt={`Avatar for ${user.nickname}`} />
                <span class="badge">{games.length}</span>
            </button>
        </div>
        <div class="hub-title">
            <h1>Games</h1>
            <p class="hub-subtitle">
                {unfinishedCount()} ongoing · {games.length} total
            </p>
        </div>
    </header>

    <section class="panel glass-panel">
        <div class="panel-header">
            <h2>Your matches</h2>
            <button class="secondary small" on:click={onToggleNewGameForm}>
                {showNewGameForm ? "Close" : "New challenge"}
            </button>
        </div>

        {#if showNewGameForm}
            <form class="new-game" on:submit|preventDefault={onLaunchGame}>
                <label for="opponent">Opponent</label>
                <select
                    id="opponent"
                    bind:value={newGameOpponentId}
                    on:change={(event) =>
                        onChangeOpponent(
                            /** @type {HTMLSelectElement} */ (
                                event.currentTarget
                            ).value,
                        )}
                >
                    {#each availableOpponents as opponent}
                        <option value={opponent.id}>
                            {opponent.nickname} ({opponent.title})
                        </option>
                    {/each}
                </select>
                <label for="color">Play as</label>
                <select
                    id="color"
                    bind:value={newGameColor}
                    on:change={(event) =>
                        onChangeColor(
                            /** @type {HTMLSelectElement} */ (
                                event.currentTarget
                            ).value,
                        )}
                >
                    <option value="white">White</option>
                    <option value="black">Black</option>
                </select>
                <button type="submit">Launch game</button>
            </form>
        {/if}

        {#if games.length}
            <div class="game-list">
                {#each games as game (game.id)}
                    <button
                        type="button"
                        class="game-card"
                        class:active={game.id === selectedGameId}
                        on:click={() => onOpenGame(game.id)}
                        aria-pressed={game.id === selectedGameId}
                    >
                        <div class="game-opponent">
                            <img
                                src={game.opponent.avatar}
                                alt={`Avatar of ${game.opponent.nickname}`}
                            />
                            <div>
                                <p class="name">{game.opponent.nickname}</p>
                                <p class="meta">{game.summary}</p>
                            </div>
                        </div>
                        <div class="game-info">
                            <span class="status">{gameStatusLabel(game)}</span>
                            <span class="timestamp"
                                >{formatTime(game.lastUpdated)}</span
                            >
                        </div>
                    </button>
                {/each}
            </div>
        {:else}
            <p class="empty">No games yet. Start a new challenge to begin.</p>
        {/if}
    </section>
</main>

<style>
    .hub {
        width: min(720px, 100%);
        display: flex;
        flex-direction: column;
        gap: clamp(1.25rem, 3vw, 1.75rem);
        margin: 0 auto;
        padding: 0.75rem clamp(1rem, 4vw, 1.5rem) 2rem;
    }

    .hub-header {
        display: flex;
        flex-direction: column;
        gap: 0.85rem;
    }

    .hub-actions {
        display: flex;
        justify-content: flex-end;
        gap: 0.65rem;
    }

    .hub-title h1 {
        margin: 0;
        font-size: clamp(1.8rem, 4vw, 2.3rem);
        color: #f8fafc;
    }

    .hub-subtitle {
        margin: 0.25rem 0 0;
        color: rgba(226, 232, 240, 0.72);
        font-size: 0.95rem;
    }

    .panel {
        display: flex;
        flex-direction: column;
        gap: 1.25rem;
        padding: clamp(1.35rem, 4vw, 1.75rem);
    }

    .panel-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.75rem;
    }

    .panel-header h2 {
        margin: 0;
        color: #f8fafc;
        font-size: 1.15rem;
    }

    .new-game {
        display: grid;
        gap: 0.75rem;
    }

    .game-list {
        display: flex;
        flex-direction: column;
        gap: 0.85rem;
    }

    .game-card {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.9rem 1.1rem;
        border-radius: 18px;
        border: 1px solid transparent;
        background: rgba(15, 23, 42, 0.55);
        color: inherit;
        text-align: left;
        cursor: pointer;
        transition:
            border-color 0.15s ease,
            transform 0.15s ease,
            background 0.15s ease;
    }

    .game-card:hover {
        border-color: rgba(96, 165, 250, 0.5);
        transform: translateY(-1px);
    }

    .game-card.active {
        border-color: rgba(37, 99, 235, 0.65);
        background: rgba(15, 23, 42, 0.75);
    }

    .game-opponent {
        display: flex;
        gap: 0.85rem;
        align-items: center;
    }

    .game-opponent img {
        width: 42px;
        height: 42px;
        border-radius: 16px;
        object-fit: cover;
        border: 1px solid rgba(148, 163, 184, 0.25);
    }

    .game-opponent .name {
        margin: 0;
        font-weight: 600;
        color: #f8fafc;
    }

    .game-opponent .meta {
        margin: 0;
        color: rgba(226, 232, 240, 0.6);
        font-size: 0.85rem;
    }

    .game-info {
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        gap: 0.25rem;
        color: rgba(226, 232, 240, 0.65);
        font-size: 0.82rem;
    }

    .status {
        font-weight: 600;
        color: #bfdbfe;
    }

    .timestamp {
        font-size: 0.8rem;
        color: rgba(148, 163, 184, 0.75);
    }

    .empty {
        margin: 0;
        color: rgba(226, 232, 240, 0.65);
    }

    .avatar-button {
        position: relative;
        border: none;
        background: rgba(15, 23, 42, 0.6);
        border-radius: 999px;
        padding: 0.35rem 0.75rem 0.35rem 0.35rem;
        display: inline-flex;
        align-items: center;
        gap: 0.6rem;
        cursor: pointer;
        color: inherit;
        transition: background 0.15s ease;
    }

    .avatar-button:hover {
        background: rgba(37, 99, 235, 0.18);
    }

    .avatar-button img {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        object-fit: cover;
        border: 1px solid rgba(148, 163, 184, 0.3);
    }

    .avatar-button .badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 30px;
        padding: 0.15rem 0.55rem;
        border-radius: 999px;
        background: rgba(37, 99, 235, 0.52);
        color: #e0f2fe;
        font-size: 0.78rem;
        font-weight: 600;
    }

    .small {
        padding: 0.55em 1.1em;
        font-size: 0.9rem;
    }

    .micro {
        padding: 0.45em 0.9em;
        font-size: 0.85rem;
    }

    @media (max-width: 640px) {
        .hub {
            padding-inline: 1rem;
        }

        .panel {
            padding: 1.1rem;
            gap: 1rem;
        }

        .panel-header {
            flex-direction: column;
            align-items: stretch;
        }

        .panel-header button {
            width: 100%;
        }

        .hub-actions {
            justify-content: space-between;
        }
    }
</style>
