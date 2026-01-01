<script>
    import { t } from "../i18n";
    /** @type {{ id: string; nickname: string; avatar: string; rating?: number | null } | null} */
    export let user = null;
    /** @type {Array<any>} */
    export let games = [];
    export let selectedGameId = null;
    export let showNewGameForm = false;
    export let availableOpponents = [];
    export let availableEngines = [];
    export let newGameOpponentId = "";
    export let newGameColor = "white";
    export let newGameDepth = "";
    export let formatTime = (_iso) => "";
    export let gameStatusLabel = (_game) => "";
    export let onOpenGame = (_id) => {};
    export let onToggleNewGameForm = () => {};
    export let onChangeOpponent = (_id) => {};
    export let onChangeColor = (_color) => {};
    export let onChangeDepth = (_value) => {};
    export let onLaunchGame = () => {};
    export let onOpenProfile = () => {};
    export let onLogout = () => {};
    export let onRefreshGames = () => {};

    const isFinished = (game) =>
        game.status === "completed" || game.status === "aborted";

    const unfinishedCount = () =>
        games.filter((game) => !isFinished(game)).length;

    $: subtitle = $t("hub.header.subtitle", {
        ongoing: unfinishedCount(),
        total: games.length,
    });
    $: logoutLabel = $t("hub.actions.logout");
    $: profileLabel = $t("hub.actions.profile");
    $: profileAria = $t("hub.actions.profileAria");
    $: matchesHeading = $t("hub.section.matches");
    $: refreshLabel = $t("hub.actions.refresh");
    $: newLabel = $t("hub.actions.new");
    $: closeLabel = $t("hub.actions.close");
    $: opponentLabel = $t("hub.form.opponent");
    $: colorLabelText = $t("hub.form.color");
    $: launchLabel = $t("hub.form.launch");
    $: emptyLabel = $t("hub.empty");
    $: colorWhite = $t("color.white");
    $: colorBlack = $t("color.black");
    $: summaryFallback = $t("game.summary.default");
    $: unknownLabel = $t("label.unknown");
    $: engineBadge = $t("label.engine");
    $: ratingLabel = $t("label.rating");
    $: ratingValueLabel = $t("label.ratingValue");
    $: toggleNewGameLabel = showNewGameForm ? closeLabel : newLabel;
    $: userAlt = $t("avatar.label", { name: user?.nickname ?? "" });
    $: gamesTitle = $t("hub.header.title");
    $: depthLabel = $t("hub.form.depth");
    $: depthPlaceholder = $t("hub.form.depthPlaceholder");
    $: depthHelp = $t("hub.form.depthHelp");

    const summaryText = (game) => {
        if (!game) {
            return summaryFallback;
        }
        const value = typeof game.summary === "string" ? game.summary.trim() : "";
        return value || summaryFallback;
    };

    const opponentNameDisplay = (opponent) => {
        if (!opponent) {
            return unknownLabel;
        }
        const value = typeof opponent.nickname === "string" ? opponent.nickname.trim() : "";
        return value || unknownLabel;
    };

    const ratingDisplay = (value) =>
        typeof value === "number" && Number.isFinite(value) ? Math.round(value) : null;

    const ratingValueText = (value) => {
        const display = ratingDisplay(value);
        if (display === null) {
            return "—";
        }
        return ratingValueLabel.replace("{value}", display);
    };

    $: userRatingValue = ratingDisplay(user?.rating);

    $: selectedOpponent = availableOpponents.find(
        (opponent) => String(opponent.id) === String(newGameOpponentId),
    ) ?? null;
    $: selectedEngine = selectedOpponent?.engineKey
        ? availableEngines.find((engine) => engine.key === selectedOpponent.engineKey) ?? null
        : null;
    $: isEngineChallenge = Boolean(selectedOpponent?.isEngine);
    $: depthHint = selectedEngine?.default_depth
        ? $t("hub.form.depthHint", { value: selectedEngine.default_depth })
        : "";
</script>

<main class="hub">
    <header class="hub-header">
        <div class="hub-actions">
            <button class="secondary micro" on:click={onLogout}>
                {logoutLabel}
            </button>
            <button
                class="avatar-button"
                on:click={onOpenProfile}
                aria-label={profileAria}
                title={profileLabel}
            >
                <img src={user.avatar} alt={userAlt} />
                <span class="badge">{games.length}</span>
            </button>
        </div>
        <div class="hub-title">
            <h1>{gamesTitle}</h1>
            <p class="hub-subtitle">{subtitle}</p>
            <p class="hub-rating">{ratingValueText(user?.rating)}</p>
        </div>
    </header>

    <section class="panel glass-panel">
        <div class="panel-header">
            <h2>{matchesHeading}</h2>
            <div class="panel-actions">
                <button class="secondary small" on:click={onRefreshGames}>
                    {refreshLabel}
                </button>
                <button class="secondary small" on:click={onToggleNewGameForm}>
                    {toggleNewGameLabel}
                </button>
            </div>
        </div>

        {#if showNewGameForm}
            <form class="new-game" on:submit|preventDefault={onLaunchGame}>
                <label for="opponent">{opponentLabel}</label>
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
                        <option
                            value={String(opponent.id)}
                            selected={String(opponent.id) === String(newGameOpponentId)}
                        >
                            {opponentNameDisplay(opponent)}
                            {#if opponent.isEngine}
                                ({engineBadge})
                            {/if}
                            {#if ratingDisplay(opponent.rating) !== null}
                                · {ratingDisplay(opponent.rating)}
                            {/if}
                        </option>
                    {/each}
                </select>
                <label for="color">{colorLabelText}</label>
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
                    <option value="white">{colorWhite}</option>
                    <option value="black">{colorBlack}</option>
                </select>
                {#if isEngineChallenge}
                    <label for="engine-depth">{depthLabel}</label>
                    <div class="depth-field">
                        <input
                            id="engine-depth"
                            name="engine-depth"
                            type="number"
                            min="1"
                            max={selectedEngine?.max_depth ?? 64}
                            step="1"
                            value={newGameDepth}
                            placeholder={depthPlaceholder}
                            on:input={(event) =>
                                onChangeDepth(
                                    /** @type {HTMLInputElement} */ (
                                        event.currentTarget
                                    ).value,
                                )
                            }
                        />
                        <p class="hint">{depthHelp}</p>
                        {#if depthHint}
                            <p class="hint muted">{depthHint}</p>
                        {/if}
                    </div>
                {/if}
                <button type="submit">{launchLabel}</button>
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
                                alt={$t("avatar.label", {
                                    name: opponentNameDisplay(game.opponent),
                                })}
                            />
                            <div>
                                <p class="name">
                                    {opponentNameDisplay(game.opponent)}
                                    {#if game.opponent?.isEngine}
                                        <span class="engine-badge">
                                            {engineBadge}
                                        </span>
                                    {/if}
                                    {#if ratingDisplay(game.opponent?.rating) !== null}
                                        <span
                                            class="rating-badge"
                                            title={ratingValueText(game.opponent?.rating)}
                                        >
                                            {ratingDisplay(game.opponent?.rating)}
                                        </span>
                                    {/if}
                                </p>
                                <p class="meta">{summaryText(game)}</p>
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
            <p class="empty">{emptyLabel}</p>
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

    .hub-rating {
        margin: 0.1rem 0 0;
        color: rgba(148, 163, 184, 0.9);
        font-size: 0.88rem;
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
        flex-wrap: wrap;
    }

    .panel-actions {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
        justify-content: flex-end;
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

    .depth-field {
        display: grid;
        gap: 0.35rem;
    }

    .depth-field input {
        width: 100%;
    }

    .hint {
        margin: 0;
        font-size: 0.8rem;
        color: rgba(226, 232, 240, 0.7);
    }

    .hint.muted {
        color: rgba(148, 163, 184, 0.65);
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

    .engine-badge {
        margin-left: 0.4rem;
        font-size: 0.75rem;
        color: rgba(148, 163, 184, 0.75);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .rating-badge {
        margin-left: 0.5rem;
        padding: 0.1rem 0.4rem;
        border-radius: 999px;
        background: rgba(59, 130, 246, 0.18);
        color: rgba(191, 219, 254, 0.95);
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.03em;
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

        .panel-actions {
            width: 100%;
        }

        .hub-actions {
            justify-content: space-between;
        }
    }
</style>
