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
    export let newGameInitialMinutes = "";
    export let newGameIncrementSeconds = "";
    export let newGameEngineMode = "time";
    export let formatTime = (_iso) => "";
    export let gameStatusLabel = (_game) => "";
    export let onOpenGame = (_id) => {};
    export let onToggleNewGameForm = () => {};
    export let onChangeOpponent = (_id) => {};
    export let onChangeColor = (_color) => {};
    export let onChangeDepth = (_value) => {};
    export let onChangeInitialMinutes = (_value) => {};
    export let onChangeIncrementSeconds = (_value) => {};
    export let onChangeEngineMode = (_mode) => {};
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
    $: timeInitialLabel = $t("hub.form.timeInitial");
    $: timeInitialPlaceholder = $t("hub.form.timeInitialPlaceholder");
    $: timeInitialHelp = $t("hub.form.timeInitialHelp");
    $: timeIncrementLabel = $t("hub.form.timeIncrement");
    $: timeIncrementPlaceholder = $t("hub.form.timeIncrementPlaceholder");
    $: timeIncrementHelp = $t("hub.form.timeIncrementHelp");
    $: engineModeLabel = $t("hub.form.engineMode");
    $: engineModeDepthLabel = $t("hub.form.engineModeDepth");
    $: engineModeTimeLabel = $t("hub.form.engineModeTime");
    $: engineModeHelp = $t("hub.form.engineModeHelp");
    $: timeMinutesSuffix = $t("play.clock.minutesSuffix");
    $: timeSecondsSuffix = $t("play.clock.secondsSuffix");

    const ENGINE_MODE_DEPTH = "depth";
    const ENGINE_MODE_TIME = "time";

    const toNonNegative = (value) => {
        const numeric = Number.parseInt(String(value ?? "").trim(), 10);
        if (!Number.isFinite(numeric)) {
            return null;
        }
        return Math.max(0, numeric);
    };

    const sliderProgress = (value, max) => {
        if (!max || max <= 0) {
            return 100;
        }
        const ratio = Math.max(0, Math.min(1, value / max));
        return Math.round(ratio * 100);
    };

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
    $: engineModeValue =
        newGameEngineMode === ENGINE_MODE_DEPTH ? ENGINE_MODE_DEPTH : ENGINE_MODE_TIME;
    $: engineUsesDepth = Boolean(isEngineChallenge && engineModeValue === ENGINE_MODE_DEPTH);
    $: showTimeControls = !isEngineChallenge || engineModeValue === ENGINE_MODE_TIME;
    $: sliderInitialMinutes = toNonNegative(newGameInitialMinutes);
    $: sliderIncrementSeconds = toNonNegative(newGameIncrementSeconds);
    const sliderFallback = (value, fallback = 0) =>
        typeof value === "number" && Number.isFinite(value) ? value : fallback;
    $: timeInitialSliderStyle = `--slider-progress: ${sliderProgress(sliderInitialMinutes, 120)}%;`;
    $: timeIncrementSliderStyle = `--slider-progress: ${sliderProgress(sliderIncrementSeconds, 60)}%;`;

    /** @param {Event} event */
    const handleOpponentChange = (event) => {
        const selectEl = /** @type {HTMLSelectElement | null} */ (event.currentTarget);
        if (!selectEl) {
            return;
        }
        onChangeOpponent(selectEl.value);
    };

    /** @param {Event} event */
    const handleColorChange = (event) => {
        const selectEl = /** @type {HTMLSelectElement | null} */ (event.currentTarget);
        if (!selectEl) {
            return;
        }
        onChangeColor(selectEl.value);
    };
</script>

<main class="hub">
    <header class="hub-header">
        <div class="hub-title">
            <h1>{gamesTitle}</h1>
            <p class="hub-subtitle">{subtitle}</p>
            {#if userRatingValue !== null}
                <p class="hub-rating">{ratingValueText(user?.rating)}</p>
            {/if}
        </div>
        <div class="hub-actions">
            {#if user}
                <button
                    type="button"
                    class="avatar-button"
                    on:click={onOpenProfile}
                    aria-label={profileAria}
                >
                    <img src={user?.avatar ?? ""} alt={userAlt} />
                    <div>
                        <strong>{user?.nickname ?? unknownLabel}</strong>
                        <span class="badge">{ratingValueText(user?.rating)}</span>
                    </div>
                </button>
            {/if}
            <button type="button" class="micro" on:click={onLogout}>
                {logoutLabel}
            </button>
        </div>
    </header>

    <section class="panel">
        <header class="panel-header">
            <h2>{matchesHeading}</h2>
            <div class="panel-actions">
                <button type="button" class="micro" on:click={onRefreshGames}>
                    {refreshLabel}
                </button>
                <button type="button" class="micro" on:click={onToggleNewGameForm}>
                    {toggleNewGameLabel}
                </button>
            </div>
        </header>

        {#if showNewGameForm}
            <form class="new-game" on:submit|preventDefault={onLaunchGame}>
                <div class="new-game-grid">
                    <section class="field-stack compact-card">
                        <div class="inline-fields">
                            <div class="field-block fill">
                                <label for="opponent">{opponentLabel}</label>
                                <select
                                    id="opponent"
                                    bind:value={newGameOpponentId}
                                    on:change={handleOpponentChange}
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
                            </div>
                            <div class="field-block color-pick">
                                <label for="color">{colorLabelText}</label>
                                <select
                                    id="color"
                                    bind:value={newGameColor}
                                    on:change={handleColorChange}
                                >
                                    <option value="white">{colorWhite}</option>
                                    <option value="black">{colorBlack}</option>
                                </select>
                            </div>
                        </div>
                        {#if isEngineChallenge}
                            <fieldset class="engine-mode">
                                <legend>{engineModeLabel}</legend>
                                <p class="hint">{engineModeHelp}</p>
                                <div class="mode-toggle" role="group" aria-label={engineModeLabel}>
                                    <button
                                        type="button"
                                        class="mode-pill"
                                        class:active={engineUsesDepth}
                                        on:click={() => onChangeEngineMode(ENGINE_MODE_DEPTH)}
                                        aria-pressed={engineUsesDepth}
                                    >
                                        {engineModeDepthLabel}
                                    </button>
                                    <button
                                        type="button"
                                        class="mode-pill"
                                        class:active={!engineUsesDepth}
                                        on:click={() => onChangeEngineMode(ENGINE_MODE_TIME)}
                                        aria-pressed={!engineUsesDepth}
                                    >
                                        {engineModeTimeLabel}
                                    </button>
                                </div>
                            </fieldset>
                        {/if}
                    </section>
                    <section class="field-stack emphasis">
                        {#if engineUsesDepth}
                            <div class="depth-field">
                                <label for="engine-depth">{depthLabel}</label>
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
                        {#if showTimeControls}
                            <fieldset class="time-card">
                                <legend>{timeInitialLabel}</legend>
                                <div class="slider-control">
                                    <label for="initial-time-range">
                                        <span>{timeInitialLabel}</span>
                                        <span class="slider-value">
                                            {sliderInitialMinutes ?? 0} {timeMinutesSuffix}
                                        </span>
                                    </label>
                                    <input
                                        id="initial-time-range"
                                        type="range"
                                        min="0"
                                        max="120"
                                        step="1"
                                        value={sliderFallback(sliderInitialMinutes)}
                                        on:input={(event) =>
                                            onChangeInitialMinutes(
                                                /** @type {HTMLInputElement} */ (
                                                    event.currentTarget
                                                ).value,
                                            )
                                        }
                                    />
                                    <div class="number-group">
                                        <input
                                            type="number"
                                            min="0"
                                            max="1440"
                                            step="1"
                                            value={newGameInitialMinutes}
                                            placeholder={timeInitialPlaceholder}
                                            on:input={(event) =>
                                                onChangeInitialMinutes(
                                                    /** @type {HTMLInputElement} */ (
                                                        event.currentTarget
                                                    ).value,
                                                )
                                            }
                                        />
                                        <span class="unit-badge">{timeMinutesSuffix}</span>
                                    </div>
                                    <p class="hint">{timeInitialHelp}</p>
                                </div>
                            </fieldset>
                            <fieldset class="time-card">
                                <legend>{timeIncrementLabel}</legend>
                                <div class="slider-control">
                                    <label for="increment-time-range">
                                        <span>{timeIncrementLabel}</span>
                                        <span class="slider-value">
                                            {sliderIncrementSeconds ?? 0} {timeSecondsSuffix}
                                        </span>
                                    </label>
                                    <input
                                        id="increment-time-range"
                                        type="range"
                                        min="0"
                                        max="60"
                                        step="1"
                                        value={sliderFallback(sliderIncrementSeconds)}
                                        on:input={(event) =>
                                            onChangeIncrementSeconds(
                                                /** @type {HTMLInputElement} */ (
                                                    event.currentTarget
                                                ).value,
                                            )
                                        }
                                    />
                                    <div class="number-group">
                                        <input
                                            type="number"
                                            min="0"
                                            max="600"
                                            step="1"
                                            value={newGameIncrementSeconds}
                                            placeholder={timeIncrementPlaceholder}
                                            on:input={(event) =>
                                                onChangeIncrementSeconds(
                                                    /** @type {HTMLInputElement} */ (
                                                        event.currentTarget
                                                    ).value,
                                                )
                                            }
                                        />
                                        <span class="unit-badge">{timeSecondsSuffix}</span>
                                    </div>
                                    <p class="hint">{timeIncrementHelp}</p>
                                </div>
                            </fieldset>
                        {/if}
                    </section>
                </div>
                <footer class="new-game-actions">
                    <button type="submit">{launchLabel}</button>
                </footer>
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
                            <span class="timestamp">
                                {formatTime(game.lastUpdated)}
                            </span>
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
        width: 100%;
        max-width: 880px;
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
        margin: 0 auto;
        padding: 1rem 1.5rem 2rem;
    }

    @media (min-width: 1200px) {
        .hub {
            max-width: 1020px;
            padding-inline: 2rem;
        }
    }

    .hub-header {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }

    .hub-actions {
        display: flex;
        justify-content: flex-end;
        gap: 0.75rem;
    }

    .hub-title h1 {
        margin: 0;
        font-size: 2.1rem;
        color: #f8fafc;
    }

    .hub-subtitle {
        margin: 0;
        color: rgba(226, 232, 240, 0.72);
        font-size: 0.95rem;
    }

    .hub-rating {
        margin: 0.25rem 0 0;
        color: rgba(148, 163, 184, 0.9);
        font-size: 0.88rem;
    }

    .panel {
        display: flex;
        flex-direction: column;
        gap: 1.25rem;
        padding: 1.5rem;
        background: rgba(15, 23, 42, 0.45);
        border-radius: 1rem;
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
        display: flex;
        flex-direction: column;
        gap: 1.25rem;
    }

    .new-game-grid {
        display: grid;
        gap: 1.25rem;
    }

    .field-stack {
        display: grid;
        gap: 1rem;
    }

    .field-stack.compact-card {
        background: rgba(12, 18, 35, 0.65);
        border: 1px solid rgba(59, 130, 246, 0.18);
        border-radius: 1rem;
        padding: 1.1rem;
        box-shadow: 0 12px 24px rgba(8, 23, 48, 0.35);
    }

    .field-stack.emphasis {
        background: linear-gradient(160deg, rgba(22, 30, 51, 0.85), rgba(30, 64, 175, 0.25));
        border: 1px solid rgba(94, 234, 212, 0.08);
        border-radius: 1.1rem;
        padding: 1.25rem;
        box-shadow: 0 18px 36px rgba(15, 23, 42, 0.4);
    }

    .field-block,
    .depth-field {
        display: grid;
        gap: 0.5rem;
    }

    .inline-fields {
        display: grid;
        gap: 0.75rem;
    }

    .inline-fields .field-block {
        gap: 0.4rem;
    }

    @media (min-width: 620px) {
        .inline-fields {
            grid-template-columns: minmax(0, 1fr) minmax(0, 160px);
            align-items: start;
        }

        .inline-fields .color-pick select {
            min-width: 140px;
        }
    }

    .field-block label,
    .depth-field label,
    .slider-control label span:first-child {
        font-weight: 600;
        color: #dbeafe;
        letter-spacing: 0.01em;
    }

    .field-block select,
    .field-stack input,
    .depth-field input {
        width: 100%;
        border-radius: 0.75rem;
        border: 1px solid rgba(148, 163, 184, 0.35);
        background: rgba(8, 15, 35, 0.75);
        color: #e2e8f0;
        padding: 0.45rem 0.65rem;
        font-size: 0.9rem;
        line-height: 1.2;
        transition: border-color 0.18s ease, box-shadow 0.18s ease;
    }

    .inline-fields .field-block.fill select {
        width: 100%;
    }

    .field-block select {
        appearance: none;
        height: 2.25rem;
        padding-right: 1.9rem;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='8' height='5' viewBox='0 0 8 5'%3E%3Cpath fill='%2394a3b8' fill-rule='evenodd' d='M0.47 0.97a.75.75 0 0 1 1.06 0L4 3.44 6.47.97a.75.75 0 1 1 1.06 1.06L4.53 5.03a.75.75 0 0 1-1.06 0L0.47 2.03a.75.75 0 0 1 0-1.06Z'/%3E%3C/svg%3E");
        background-repeat: no-repeat;
        background-position: right 0.75rem center;
        background-size: 10px 6px;
    }

    .field-block select:focus,
    .field-stack input:focus,
    .depth-field input:focus {
        border-color: rgba(59, 130, 246, 0.75);
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.25);
        outline: none;
    }

    .engine-mode {
        margin: 0;
        padding: 0.75rem 1rem;
        border-radius: 1rem;
        border: 1px solid rgba(59, 130, 246, 0.12);
        background: rgba(12, 20, 45, 0.7);
        display: grid;
        gap: 0.5rem;
    }

    .engine-mode legend {
        margin: 0;
        font-weight: 600;
        color: #cbd5f5;
        font-size: 0.95rem;
    }

    .mode-toggle {
        display: flex;
        gap: 0.6rem;
        flex-wrap: wrap;
    }

    .mode-pill {
        background: rgba(30, 64, 175, 0.18);
        border: 1px solid transparent;
        color: #dbeafe;
        border-radius: 999px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        height: 1.55rem;
        padding: 0 0.65rem;
        font-size: 0.78rem;
        cursor: pointer;
        transition:
            background 0.18s ease,
            border-color 0.18s ease,
            transform 0.18s ease;
    }

    .mode-pill:hover {
        transform: translateY(-1px);
        border-color: rgba(148, 197, 255, 0.4);
    }

    .mode-pill.active {
        background: rgba(37, 99, 235, 0.92);
        color: #f8fafc;
        border-color: rgba(148, 197, 255, 0.8);
        box-shadow: 0 8px 18px rgba(37, 99, 235, 0.3);
    }

    .mode-pill:focus-visible {
        outline: 2px solid rgba(191, 219, 254, 0.9);
        outline-offset: 2px;
    }

    .time-card {
        margin: 0;
        padding: 1rem 1.15rem;
        border-radius: 1rem;
        border: 1px solid rgba(94, 234, 212, 0.14);
        background: linear-gradient(160deg, rgba(10, 19, 41, 0.9), rgba(15, 118, 110, 0.26));
        display: grid;
        gap: 0.75rem;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03), 0 16px 32px rgba(8, 35, 68, 0.35);
    }

    .time-card legend {
        margin: 0;
        font-weight: 600;
        font-size: 0.95rem;
        color: #a7f3d0;
    }

    .slider-control {
        display: grid;
        gap: 0.55rem;
    }

    .slider-control label {
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 0.9rem;
        color: rgba(226, 232, 240, 0.9);
    }

    .slider-value {
        font-variant-numeric: tabular-nums;
        color: #a7f3d0;
        font-weight: 600;
    }

    .slider-control input[type="range"] {
        -webkit-appearance: none;
        appearance: none;
        width: 100%;
        height: 8px;
        border-radius: 999px;
        background: linear-gradient(90deg, rgba(20, 184, 166, 0.85), rgba(37, 99, 235, 0.75));
        outline: none;
        box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.6);
    }

    .slider-control input[type="range"]::-moz-range-track {
        height: 8px;
        border-radius: 999px;
        background: linear-gradient(90deg, rgba(20, 184, 166, 0.85), rgba(37, 99, 235, 0.75));
    }

    .slider-control input[type="range"]::-webkit-slider-thumb {
        -webkit-appearance: none;
        appearance: none;
        width: 18px;
        height: 18px;
        border-radius: 50%;
        background: #f0fdfa;
        border: 2px solid rgba(20, 184, 166, 0.9);
        cursor: pointer;
        box-shadow: 0 0 0 4px rgba(45, 212, 191, 0.22);
    }

    .slider-control input[type="range"]::-moz-range-thumb {
        width: 18px;
        height: 18px;
        border-radius: 50%;
        background: #f0fdfa;
        border: 2px solid rgba(20, 184, 166, 0.9);
        cursor: pointer;
        box-shadow: 0 0 0 4px rgba(45, 212, 191, 0.22);
    }

    .number-group {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .number-group input {
        flex: 1;
        min-width: 0;
        border-radius: 0.75rem;
        border: 1px solid rgba(148, 163, 184, 0.35);
        background: rgba(8, 15, 35, 0.78);
        color: #e2e8f0;
        padding: 0.55rem 0.65rem;
        font-size: 0.9rem;
    }

    .unit-badge {
        padding: 0.35rem 0.65rem;
        border-radius: 999px;
        background: rgba(20, 184, 166, 0.16);
        color: #a7f3d0;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.02em;
        text-transform: uppercase;
    }

    .new-game-actions {
        display: flex;
        justify-content: flex-end;
    }

    .new-game-actions button {
        min-width: 9rem;
        border-radius: 999px;
        font-weight: 600;
        letter-spacing: 0.02em;
        box-shadow: 0 16px 28px rgba(37, 99, 235, 0.35);
    }

    @media (min-width: 880px) {
        .new-game-grid {
            grid-template-columns: minmax(0, 1.15fr) minmax(0, 0.85fr);
            align-items: stretch;
        }
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
