<script>
    import { onMount } from "svelte";
    import HubLeaderboard from "../components/HubLeaderboard.svelte";
    import { locale, t } from "../i18n";
    import { calculateTrophies } from "../utils/trophies";
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
    export let onOpenPuzzles = () => {};
    export let onOpenAdmin = () => {};
    export let onLogout = () => {};
    export let onRefreshGames = () => {};
    export let showAdminLink = false;
    export let leaderboard = [];
    export let isLeaderboardLoading = false;
    let showActionMenu = false;
    let actionMenuRef;
    let menuToggleRef;

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
    $: puzzlesLabel = $t("hub.actions.puzzles");
    $: adminLabel = $t("hub.actions.admin");
    $: matchesHeading = $t("hub.section.matches");
    $: refreshLabel = $t("hub.actions.refresh");
    $: newLabel = $t("hub.actions.new");
    $: newShortLabel = $t("hub.actions.newShort");
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
    $: ratingValueLabel = $t("label.ratingValue");
    $: toggleNewGameLabel = showNewGameForm
        ? closeLabel
        : newShortLabel || newLabel;
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
    $: timeUntimedLabel = $t("play.clock.unlimited");
    $: archiveHeading = $t("hub.groups.archive");
    $: ongoingHeading = $t("hub.groups.ongoing");
    $: undatedGroupLabel = $t("hub.groups.undated");
    $: expandGroupLabel = $t("hub.groups.expand");
    $: collapseGroupLabel = $t("hub.groups.collapse");
    $: leaderboardHeading = $t("hub.leaderboard.heading");
    $: leaderboardSubtitle = $t("hub.leaderboard.subtitle");
    $: leaderboardRankLabel = $t("hub.leaderboard.rank");
    $: leaderboardPlayerLabel = $t("hub.leaderboard.player");
    $: leaderboardRatingLabel = $t("hub.leaderboard.rating");
    $: leaderboardTrophiesLabel = $t("hub.leaderboard.trophies");
    $: leaderboardRecordLabel = $t("hub.leaderboard.record");
    $: leaderboardWinRateLabel = $t("hub.leaderboard.winRate");
    $: leaderboardPuzzlesLabel = $t("hub.leaderboard.puzzles");
    $: leaderboardLastActiveLabel = $t("hub.leaderboard.lastActive");
    $: leaderboardEmptyLabel = $t("hub.leaderboard.empty");
    $: leaderboardLoadingLabel = $t("hub.leaderboard.loading");
    $: challengeHint = $t("hub.actions.newHint");
    $: puzzlesHint = $t("hub.actions.puzzlesHint");
    $: puzzlesShortLabel = $t("hub.actions.puzzlesShort") || puzzlesLabel;

    $: currentLocale = $locale;

    const parseTimestamp = (value) => {
        if (!value) {
            return null;
        }
        const date = new Date(value);
        return Number.isNaN(date.getTime()) ? null : date;
    };

    const formatArchiveLabel = (date) => {
        if (!(date instanceof Date) || Number.isNaN(date.getTime())) {
            return undatedGroupLabel;
        }
        try {
            return new Intl.DateTimeFormat(currentLocale || undefined, {
                month: "long",
                year: "numeric",
            }).format(date);
        } catch (_error) {
            return new Intl.DateTimeFormat(undefined, {
                month: "long",
                year: "numeric",
            }).format(date);
        }
    };

    const sortByDateDesc = (a, b) => {
        if (!a && !b) {
            return 0;
        }
        if (!a) {
            return 1;
        }
        if (!b) {
            return -1;
        }
        return b.getTime() - a.getTime();
    };

    const sanitizeId = (value) => String(value ?? "").replace(/[^a-zA-Z0-9_-]+/g, "-");

    const archivePanelId = (key) => `archive-${sanitizeId(key)}`;
    const opponentPanelId = (groupKey, opponentKey) =>
        `archive-${sanitizeId(groupKey)}-opponent-${sanitizeId(opponentKey)}`;

    let collapsedArchiveGroups = {};
    let collapsedOpponentGroups = {};

    const archiveGroupCollapsed = (key) => Boolean(collapsedArchiveGroups[key]);
    const opponentGroupCollapsed = (groupKey, opponentKey) =>
        Boolean(collapsedOpponentGroups[`${groupKey}::${opponentKey}`]);

    const toggleArchiveGroup = (key) => {
        collapsedArchiveGroups = {
            ...collapsedArchiveGroups,
            [key]: !collapsedArchiveGroups[key],
        };
    };

    const toggleOpponentGroup = (groupKey, opponentKey) => {
        const compound = `${groupKey}::${opponentKey}`;
        collapsedOpponentGroups = {
            ...collapsedOpponentGroups,
            [compound]: !collapsedOpponentGroups[compound],
        };
    };

    $: {
        const archiveKeys = new Set(archivedGroups.map((group) => group.key));
        let archiveChanged = false;
        const nextArchiveState = { ...collapsedArchiveGroups };
        archiveKeys.forEach((key) => {
            if (!(key in nextArchiveState)) {
                nextArchiveState[key] = false;
                archiveChanged = true;
            }
        });
        Object.keys(nextArchiveState).forEach((key) => {
            if (!archiveKeys.has(key)) {
                delete nextArchiveState[key];
                archiveChanged = true;
            }
        });
        if (archiveChanged) {
            collapsedArchiveGroups = nextArchiveState;
        }

        const opponentKeys = new Set(
            archivedGroups.flatMap((group) =>
                group.opponents.map((opponent) => `${group.key}::${opponent.key}`),
            ),
        );
        let opponentChanged = false;
        const nextOpponentState = { ...collapsedOpponentGroups };
        opponentKeys.forEach((compound) => {
            if (!(compound in nextOpponentState)) {
                nextOpponentState[compound] = false;
                opponentChanged = true;
            }
        });
        Object.keys(nextOpponentState).forEach((compound) => {
            if (!opponentKeys.has(compound)) {
                delete nextOpponentState[compound];
                opponentChanged = true;
            }
        });
        if (opponentChanged) {
            collapsedOpponentGroups = nextOpponentState;
        }
    }

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

    const safeNumber = (value) => (Number.isFinite(value) ? Number(value) : 0);

    const formatWinRate = (wins, games) => {
        if (!games) {
            return "—";
        }
        const ratio = Math.round((wins / games) * 100);
        return `${ratio}%`;
    };

    const formatRecord = (entry) => {
        const wins = safeNumber(entry?.games_won);
        const losses = safeNumber(entry?.games_lost);
        const draws = safeNumber(entry?.games_drawn);
        return `${wins}-${losses}-${draws}`;
    };

    const formatPuzzleSummary = (entry) => {
        const solved = safeNumber(entry?.puzzles_solved);
        const attempted = safeNumber(entry?.puzzles_attempted);
        return attempted ? `${solved}/${attempted}` : `${solved}/0`;
    };

    const formatActivity = (entry) => {
        return formatTime(entry?.last_activity_at || entry?.last_game_at || null);
    };

    $: trophyNoneLabel = $t("profile.trophies.none");

    $: rankedEntries = Array.isArray(leaderboard)
        ? leaderboard.map((entry, index) => ({ ...entry, rank: index + 1 }))
        : [];
    $: userRankEntry = rankedEntries.find((entry) => String(entry.id) === String(user?.id)) ?? null;
    $: hubLeaderboard = rankedEntries.slice(0, 5);
    $: hubLeaderboardRows = hubLeaderboard.map((entry) => {
        const trophyData = calculateTrophies(entry?.games_won, 4);
        const hasTrophies = trophyData.cups.length > 0;
        const trophySummary = hasTrophies
            ? $t("profile.trophies.summary", {
                  gold: trophyData.counts.gold,
                  silver: trophyData.counts.silver,
                  bronze: trophyData.counts.bronze,
                  represented: trophyData.representedWins,
                  wins: trophyData.sourceWins,
              })
            : trophyNoneLabel;
        return {
            id: entry.id,
            rank: entry.rank,
            username: entry.username,
            avatar: entry.avatar_url || "",
            ratingText: ratingDisplay(entry.rating) ?? "—",
            recordText: formatRecord(entry),
            winRateText: formatWinRate(entry.games_won, entry.games_played),
            puzzlesText: formatPuzzleSummary(entry),
            activityText: formatActivity(entry) || "—",
            trophyWins: trophyData.sourceWins,
            trophySummary,
            hasTrophies,
            highlight: String(entry.id) === String(user?.id),
        };
    });
    $: leaderboardFootnote =
        userRankEntry && userRankEntry.rank > hubLeaderboard.length
            ? $t("hub.leaderboard.yourRank", {
                  rank: userRankEntry.rank,
                  rating: ratingDisplay(userRankEntry.rating) ?? "—",
              })
            : "";

    const toRenderGame = (game) => {
        const opponent = game?.opponent ?? null;
        const opponentLabel = opponentNameDisplay(opponent);
        const opponentRating = ratingDisplay(opponent?.rating);
        return {
            id: game.id,
            opponentLabel,
            opponentAvatar: opponent?.avatar ?? "",
            opponentIsEngine: Boolean(opponent?.isEngine),
            opponentRating,
            opponentRatingLabel: ratingValueText(opponent?.rating),
            summary: summaryText(game),
            status: gameStatusLabel(game),
            timestamp: formatTime(game.lastUpdated),
        };
    };

    $: userRatingValue = ratingDisplay(user?.rating);

    const opponentKey = (game) => {
        const rawId = game?.opponent?.id;
        if (rawId !== null && rawId !== undefined) {
            return `id-${rawId}`;
        }
        const label = opponentNameDisplay(game?.opponent ?? null);
        return `name-${label.toLowerCase()}`;
    };

    $: activeGames = games
        .filter((game) => !isFinished(game))
        .map((game) => toRenderGame(game));
    $: archivedGroups = (() => {
        const finished = games.filter(isFinished);
        if (!finished.length) {
            return [];
        }
        const buckets = new Map();
        finished.forEach((game) => {
            const timestamp = parseTimestamp(game.lastUpdated ?? game.startedAt ?? null);
            const key = timestamp
                ? `${timestamp.getFullYear()}-${String(timestamp.getMonth() + 1).padStart(2, "0")}`
                : "undated";
            if (!buckets.has(key)) {
                buckets.set(key, {
                    date: timestamp,
                    opponents: new Map(),
                });
            }
            const entry = buckets.get(key);
            if (timestamp && (!entry.date || timestamp > entry.date)) {
                entry.date = timestamp;
            }
            const opponentId = opponentKey(game);
            if (!entry.opponents.has(opponentId)) {
                entry.opponents.set(opponentId, {
                    label: opponentNameDisplay(game.opponent ?? null),
                    games: [],
                });
            }
            entry.opponents.get(opponentId).games.push(game);
        });
        return Array.from(buckets.entries())
            .map(([key, value]) => {
                const opponentGroups = Array.from(value.opponents.entries())
                    .map(([opponentKeyValue, opponentValue]) => {
                        const sortedGames = opponentValue.games.slice().sort((a, b) => {
                            const aDate = parseTimestamp(a.lastUpdated ?? a.startedAt ?? null);
                            const bDate = parseTimestamp(b.lastUpdated ?? b.startedAt ?? null);
                            return sortByDateDesc(aDate, bDate);
                        });
                        const renderGames = sortedGames.map((game) => toRenderGame(game));
                        return {
                            key: opponentKeyValue,
                            label: opponentValue.label,
                            games: renderGames,
                        };
                    })
                    .sort((a, b) => a.label.localeCompare(b.label, currentLocale || undefined, {
                        sensitivity: "base",
                    }));
                const totalGames = opponentGroups.reduce((total, group) => total + group.games.length, 0);
                return {
                    key,
                    date: value.date,
                    label: value.date ? formatArchiveLabel(value.date) : undatedGroupLabel,
                    opponents: opponentGroups,
                    total: totalGames,
                };
            })
            .sort((a, b) => sortByDateDesc(a.date, b.date));
    })();

    $: archivedTotal = archivedGroups.reduce((total, group) => total + group.total, 0);

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

    const toggleActionMenu = () => {
        showActionMenu = !showActionMenu;
    };

    const closeActionMenu = () => {
        showActionMenu = false;
    };

    const runMenuAction = (callback) => {
        closeActionMenu();
        if (typeof callback === "function") {
            callback();
        }
    };

    const handleMenuKeydown = (event) => {
        if (event.key === "Escape") {
            event.preventDefault();
            closeActionMenu();
        }
    };

    const handleDocumentClick = (event) => {
        if (!showActionMenu) {
            return;
        }
        const target = /** @type {Node} */ (event.target);
        if (actionMenuRef?.contains(target) || menuToggleRef?.contains(target)) {
            return;
        }
        closeActionMenu();
    };

    onMount(() => {
        document.addEventListener("click", handleDocumentClick);
        return () => {
            document.removeEventListener("click", handleDocumentClick);
        };
    });
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
        <div class="hub-actions desktop">
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
            {#if showAdminLink}
                <button type="button" class="micro secondary" on:click={onOpenAdmin}>
                    {adminLabel}
                </button>
            {/if}
            <button type="button" class="micro engage" on:click={onOpenPuzzles}>
                {puzzlesLabel}
            </button>
            <button type="button" class="micro" on:click={onLogout}>
                {logoutLabel}
            </button>
        </div>
        <div class="hub-actions-mobile">
            {#if user}
                <button
                    type="button"
                    class="avatar-button"
                    on:click={() => runMenuAction(onOpenProfile)}
                    aria-label={profileAria}
                >
                    <img src={user?.avatar ?? ""} alt={userAlt} />
                    <span class="sr-only">{profileLabel}</span>
                </button>
            {/if}
            <button
                type="button"
                class="micro secondary menu-toggle"
                aria-expanded={showActionMenu}
                aria-controls="hub-action-menu"
                aria-haspopup="true"
                on:click={toggleActionMenu}
                bind:this={menuToggleRef}
            >
                {showActionMenu ? $t("hub.actions.menuClose") : $t("hub.actions.menu")}
            </button>
            {#if showActionMenu}
                <div
                    class="action-menu"
                    id="hub-action-menu"
                    role="menu"
                    tabindex="-1"
                    on:keydown={handleMenuKeydown}
                    bind:this={actionMenuRef}
                >
                    {#if showAdminLink}
                        <button type="button" role="menuitem" on:click={() => runMenuAction(onOpenAdmin)}>
                            {adminLabel}
                        </button>
                    {/if}
                    <button
                        type="button"
                        class="engage"
                        role="menuitem"
                        on:click={() => runMenuAction(onOpenPuzzles)}
                    >
                        {puzzlesLabel}
                    </button>
                    <button type="button" role="menuitem" on:click={() => runMenuAction(onLogout)}>
                        {logoutLabel}
                    </button>
                </div>
            {/if}
        </div>
    </header>

        <HubLeaderboard
            heading={leaderboardHeading}
            subtitle={leaderboardSubtitle}
            rankLabel={leaderboardRankLabel}
            playerLabel={leaderboardPlayerLabel}
            ratingLabel={leaderboardRatingLabel}
            trophyLabel={leaderboardTrophiesLabel}
            trophyEmptyLabel={trophyNoneLabel}
            recordLabel={leaderboardRecordLabel}
            winRateLabel={leaderboardWinRateLabel}
            puzzlesLabel={leaderboardPuzzlesLabel}
            lastActiveLabel={leaderboardLastActiveLabel}
            rows={hubLeaderboardRows}
            isLoading={isLeaderboardLoading}
            emptyLabel={leaderboardEmptyLabel}
            loadingLabel={leaderboardLoadingLabel}
            footnote={leaderboardFootnote}
        />

        <section class="hub-cta">
            <button
                type="button"
                class="cta-card challenge"
                class:active={showNewGameForm}
                aria-pressed={showNewGameForm}
                title={challengeHint}
                on:click={onToggleNewGameForm}
            >
                <span class="cta-title">{toggleNewGameLabel}</span>
            </button>
            <button
                type="button"
                class="cta-card puzzles"
                title={puzzlesHint}
                on:click={onOpenPuzzles}
            >
                <span class="cta-title">{puzzlesShortLabel}</span>
            </button>
        </section>

        <section class="panel">
        <header class="panel-header">
            <h2>{matchesHeading}</h2>
            <div class="panel-actions">
                <button type="button" class="micro" on:click={onRefreshGames}>
                    {refreshLabel}
                </button>
            </div>
        </header>

        {#if showNewGameForm}
            <form class="new-game" on:submit|preventDefault={onLaunchGame}>
                <div class="new-game-grid">
                    <section class="field-stack">
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
                                <label for="color-choice">{colorLabelText}</label>
                                <select
                                    id="color-choice"
                                    bind:value={newGameColor}
                                    on:change={(event) =>
                                        onChangeColor(
                                            /** @type {HTMLSelectElement} */ (event.currentTarget).value,
                                        )
                                    }
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
                                <div class="mode-toggle" role="radiogroup" aria-label={engineModeLabel}>
                                    <label
                                        class="mode-pill"
                                        class:active={engineModeValue === ENGINE_MODE_TIME}
                                    >
                                        <input
                                            type="radio"
                                            name="engine-mode"
                                            value={ENGINE_MODE_TIME}
                                            checked={engineModeValue === ENGINE_MODE_TIME}
                                            on:change={() => onChangeEngineMode(ENGINE_MODE_TIME)}
                                        />
                                        <span>{engineModeTimeLabel}</span>
                                    </label>
                                    <label
                                        class="mode-pill"
                                        class:active={engineModeValue === ENGINE_MODE_DEPTH}
                                    >
                                        <input
                                            type="radio"
                                            name="engine-mode"
                                            value={ENGINE_MODE_DEPTH}
                                            checked={engineModeValue === ENGINE_MODE_DEPTH}
                                            on:change={() => onChangeEngineMode(ENGINE_MODE_DEPTH)}
                                        />
                                        <span>{engineModeDepthLabel}</span>
                                    </label>
                                </div>
                                {#if engineUsesDepth}
                                    <div class="depth-field">
                                        <label for="engine-depth">{depthLabel}</label>
                                        <input
                                            id="engine-depth"
                                            type="number"
                                            min="1"
                                            max="64"
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
                            </fieldset>
                        {/if}
                        {#if showTimeControls}
                            <fieldset class="time-card">
                                <legend>{timeInitialLabel}</legend>
                                <div class="slider-control">
                                    <label for="initial-time-range">
                                        <span>{timeInitialLabel}</span>
                                        <span class="slider-value">
                                            {#if sliderInitialMinutes !== null}
                                                {sliderInitialMinutes} {timeMinutesSuffix}
                                            {:else}
                                                {timeUntimedLabel}
                                            {/if}
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
                    <button type="submit" class="engage">{launchLabel}</button>
                </footer>
            </form>
        {/if}

        {#if games.length}
            <div class="game-sections">
                {#if activeGames.length}
                    <section class="game-section current">
                        <header class="game-section-header">
                            <h3>{ongoingHeading}</h3>
                            <span class="game-count" aria-hidden="true">{activeGames.length}</span>
                        </header>
                        <div class="game-list">
                            {#each activeGames as game (game.id)}
                                <button
                                    type="button"
                                    class="game-card"
                                    class:active={game.id === selectedGameId}
                                    on:click={() => onOpenGame(game.id)}
                                    aria-pressed={game.id === selectedGameId}
                                >
                                    <div class="game-opponent">
                                        <img
                                            src={game.opponentAvatar}
                                            alt={$t("avatar.label", {
                                                name: game.opponentLabel,
                                            })}
                                        />
                                        <div>
                                            <p class="name">
                                                {game.opponentLabel}
                                                {#if game.opponentIsEngine}
                                                    <span class="engine-badge">
                                                        {engineBadge}
                                                    </span>
                                                {/if}
                                                {#if game.opponentRating !== null}
                                                    <span
                                                        class="rating-badge"
                                                        title={game.opponentRatingLabel}
                                                    >
                                                        {game.opponentRating}
                                                    </span>
                                                {/if}
                                            </p>
                                            <p class="meta">{game.summary}</p>
                                        </div>
                                    </div>
                                    <div class="game-info">
                                        <span class="status">{game.status}</span>
                                        <span class="timestamp">{game.timestamp}</span>
                                    </div>
                                </button>
                            {/each}
                        </div>
                    </section>
                {/if}

                {#if archivedGroups.length}
                    <section class="game-section archive">
                        <header class="game-section-header">
                            <h3>{archiveHeading}</h3>
                            <span class="game-count" aria-hidden="true">{archivedTotal}</span>
                        </header>
                        <div class="archive-groups">
                            {#each archivedGroups as group (group.key)}
                                {@const archiveId = archivePanelId(group.key)}
                                <div class="game-group" data-collapsed={archiveGroupCollapsed(group.key)}>
                                    <div class="game-group-header">
                                        <div class="group-title">
                                            <h4>{group.label}</h4>
                                        </div>
                                        <div class="group-controls">
                                            <span class="game-group-count" aria-hidden="true">{group.total}</span>
                                            <button
                                                type="button"
                                                class="collapse-toggle"
                                                on:click={() => toggleArchiveGroup(group.key)}
                                                aria-expanded={!archiveGroupCollapsed(group.key)}
                                                aria-controls={archiveId}
                                                aria-label={archiveGroupCollapsed(group.key)
                                                    ? expandGroupLabel
                                                    : collapseGroupLabel}
                                            >
                                                <span aria-hidden="true">
                                                    {archiveGroupCollapsed(group.key) ? "+" : "-"}
                                                </span>
                                            </button>
                                        </div>
                                    </div>
                                    <div
                                        class="opponent-groups"
                                        id={archiveId}
                                        class:is-collapsed={archiveGroupCollapsed(group.key)}
                                        aria-hidden={archiveGroupCollapsed(group.key)}
                                    >
                                        {#each group.opponents as opponentGroup (opponentGroup.key)}
                                            {@const opponentId = opponentPanelId(group.key, opponentGroup.key)}
                                            <div
                                                class="opponent-group"
                                                data-collapsed={opponentGroupCollapsed(group.key, opponentGroup.key)}
                                            >
                                                <div class="opponent-header">
                                                    <span class="opponent-name">{opponentGroup.label}</span>
                                                    <div class="opponent-controls">
                                                        <span class="opponent-count" aria-hidden="true">
                                                            {opponentGroup.games.length}
                                                        </span>
                                                        <button
                                                            type="button"
                                                            class="collapse-toggle small"
                                                            on:click={() =>
                                                                toggleOpponentGroup(group.key, opponentGroup.key)
                                                            }
                                                            aria-expanded={!opponentGroupCollapsed(
                                                                group.key,
                                                                opponentGroup.key,
                                                            )}
                                                            aria-controls={opponentId}
                                                            aria-label={opponentGroupCollapsed(
                                                                group.key,
                                                                opponentGroup.key,
                                                            )
                                                                ? expandGroupLabel
                                                                : collapseGroupLabel}
                                                        >
                                                            <span aria-hidden="true">
                                                                {opponentGroupCollapsed(group.key, opponentGroup.key)
                                                                    ? "+"
                                                                    : "-"}
                                                            </span>
                                                        </button>
                                                    </div>
                                                </div>
                                                <div
                                                    class="game-list compact"
                                                    id={opponentId}
                                                    class:is-collapsed={opponentGroupCollapsed(
                                                        group.key,
                                                        opponentGroup.key,
                                                    )}
                                                    aria-hidden={opponentGroupCollapsed(
                                                        group.key,
                                                        opponentGroup.key,
                                                    )}
                                                >
                                                    {#each opponentGroup.games as game (game.id)}
                                                        <button
                                                            type="button"
                                                            class="game-card"
                                                            class:active={game.id === selectedGameId}
                                                            on:click={() => onOpenGame(game.id)}
                                                            aria-pressed={game.id === selectedGameId}
                                                        >
                                                            <div class="game-opponent">
                                                                <img
                                                                    src={game.opponentAvatar}
                                                                    alt={$t("avatar.label", {
                                                                        name: game.opponentLabel,
                                                                    })}
                                                                />
                                                                <div>
                                                                    <p class="name">
                                                                        {game.opponentLabel}
                                                                        {#if game.opponentIsEngine}
                                                                            <span class="engine-badge">
                                                                                {engineBadge}
                                                                            </span>
                                                                        {/if}
                                                                        {#if game.opponentRating !== null}
                                                                            <span
                                                                                class="rating-badge"
                                                                                title={game.opponentRatingLabel}
                                                                            >
                                                                                {game.opponentRating}
                                                                            </span>
                                                                        {/if}
                                                                    </p>
                                                                    <p class="meta">{game.summary}</p>
                                                                </div>
                                                            </div>
                                                            <div class="game-info">
                                                                <span class="status">{game.status}</span>
                                                                <span class="timestamp">{game.timestamp}</span>
                                                            </div>
                                                        </button>
                                                    {/each}
                                                </div>
                                            </div>
                                        {/each}
                                    </div>
                                </div>
                            {/each}
                        </div>
                    </section>
                {/if}
            </div>
        {:else}
            <p class="empty">{emptyLabel}</p>
        {/if}
    </section>
</main>

<style>
    .hub {
        width: 100%;
        max-width: min(100%, 1680px);
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
        margin: 0 auto;
        padding-block: clamp(0.4rem, 1.4vw, 0.7rem) 1.95rem;
        padding-inline: clamp(0.25rem, 2.2vw, 1.2rem);
    }

    .hub-header {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }

    .hub-actions.desktop {
        display: flex;
        justify-content: flex-end;
        gap: 0.75rem;
        align-items: center;
    }

    .hub-actions-mobile {
        display: none;
        align-items: center;
        gap: 0.5rem;
        justify-content: flex-end;
    }

    .menu-toggle {
        min-width: 0;
    }

    .action-menu {
        position: absolute;
        right: 1rem;
        top: calc(100% + 0.5rem);
        display: grid;
        gap: 0.35rem;
        padding: 0.75rem;
        border-radius: 0.85rem;
        background: rgba(12, 20, 45, 0.95);
        border: 1px solid rgba(59, 130, 246, 0.25);
        box-shadow: 0 18px 32px rgba(8, 15, 35, 0.45);
        z-index: 10;
        min-width: 180px;
    }

    .action-menu button {
        width: 100%;
        text-align: left;
        background: transparent;
        border: none;
        color: #e2e8f0;
        font-size: 0.95rem;
        padding: 0.45rem 0.35rem;
        border-radius: 0.6rem;
    }

    .action-menu button:hover,
    .action-menu button:focus {
        background: rgba(59, 130, 246, 0.18);
        outline: none;
    }

    .hub-header {
        position: relative;
    }

    .sr-only {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border: 0;
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

    .hub-cta {
        display: flex;
        justify-content: center;
        align-items: stretch;
        gap: 0.85rem;
        margin: 1.25rem 0 0.85rem;
        flex-wrap: nowrap;
    }

    .cta-card {
        position: relative;
        border: none;
        border-radius: 0.75rem;
        padding: 0.95rem 1.2rem 1.3rem 1.05rem;
        min-height: 3.6rem;
        flex: 1 1 180px;
        max-width: 220px;
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        justify-content: flex-start;
        gap: 0.55rem;
        font-size: 0.92rem;
        font-weight: 700;
        color: #f8fafc;
        background: #0f172a;
        border: 1px solid rgba(30, 41, 59, 0.75);
        box-shadow: 0 6px 12px rgba(7, 10, 20, 0.26);
        cursor: pointer;
        transition: transform 0.16s ease, box-shadow 0.16s ease, filter 0.16s ease;
        overflow: visible;
        isolation: isolate;
    }

    .cta-card .cta-title {
        position: relative;
        z-index: 3;
        text-transform: none;
        letter-spacing: 0.01em;
        font-size: 0.92rem;
        line-height: 1.1;
    }

    .cta-card.challenge {
        border-color: rgba(34, 197, 94, 0.32);
        background: #18281f;
        box-shadow: 0 10px 16px rgba(34, 197, 94, 0.14);
    }

    .cta-card.puzzles {
        border-color: rgba(129, 140, 248, 0.32);
        background: #1b2142;
        box-shadow: 0 10px 16px rgba(129, 140, 248, 0.14);
    }

    .cta-card:hover,
    .cta-card:focus-visible {
        transform: translateY(-2px);
        box-shadow: 0 12px 20px rgba(15, 23, 42, 0.24);
        filter: brightness(1.005);
    }

    .cta-card:focus-visible {
        outline: 2px solid rgba(248, 250, 252, 0.78);
        outline-offset: 3px;
    }

    .cta-card.active {
        box-shadow: 0 24px 44px rgba(30, 64, 175, 0.35);
        filter: brightness(1.03);
    }

    .panel {
        display: flex;
        flex-direction: column;
        gap: 1.2rem;
        padding: clamp(0.95rem, 1vw + 0.65rem, 1.3rem);
        background: rgba(15, 23, 42, 0.45);
        border-radius: 0.9rem;
    }

    @media (max-width: 540px) {
        .panel {
            padding: 1.25rem;
        }
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

    @media (min-width: 660px) {
        .inline-fields {
            grid-template-columns: minmax(0, 7fr) minmax(0, 4fr);
            align-items: start;
        }

        .inline-fields .color-pick select,
        .inline-fields .color-pick {
            min-width: 0;
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
        border: 1px solid rgba(148, 163, 184, 0.32);
        background: rgba(8, 15, 35, 0.6);
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
        padding: 0.85rem 1rem;
        border-radius: 0.85rem;
        border: 1px solid rgba(59, 130, 246, 0.18);
        background: transparent;
        display: grid;
        gap: 0.6rem;
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
        position: relative;
        background: rgba(30, 64, 175, 0.12);
        border: 1px solid rgba(96, 165, 250, 0.12);
        color: #dbeafe;
        border-radius: 999px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        height: 1.55rem;
        padding: 0 0.75rem;
        font-size: 0.78rem;
        cursor: pointer;
        transition:
            background 0.18s ease,
            border-color 0.18s ease,
            transform 0.18s ease;
    }

    .mode-pill input {
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        opacity: 0;
        cursor: pointer;
    }

    .mode-pill span {
        pointer-events: none;
    }

    .mode-pill:hover {
        transform: translateY(-1px);
        border-color: rgba(148, 197, 255, 0.4);
    }

    .mode-pill.active {
        background: rgba(37, 99, 235, 0.85);
        color: #f8fafc;
        border-color: rgba(148, 197, 255, 0.65);
        box-shadow: 0 6px 14px rgba(37, 99, 235, 0.28);
    }

    .mode-pill:focus-visible {
        outline: 2px solid rgba(191, 219, 254, 0.9);
        outline-offset: 2px;
    }

    .time-card {
        margin: 0;
        padding: 0.85rem 1rem;
        border-radius: 0.85rem;
        border: 1px solid rgba(94, 234, 212, 0.18);
        background: transparent;
        display: grid;
        gap: 0.65rem;
        box-shadow: none;
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

    .game-sections {
        display: grid;
        gap: 1.2rem;
    }

    .game-section {
        display: grid;
        gap: 0.75rem;
    }

    .is-collapsed {
        display: none !important;
    }

    .game-section-header {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 0.6rem;
    }

    .game-section-header h3 {
        margin: 0;
        font-size: 1rem;
        color: #f8fafc;
    }

    .game-count {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 2.25rem;
        padding: 0.2rem 0.6rem;
        border-radius: 999px;
        background: rgba(37, 99, 235, 0.18);
        color: #bfdbfe;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.04em;
    }

    .archive-groups {
        display: grid;
        gap: 1rem;
    }

    .game-group {
        display: grid;
        gap: 0.7rem;
        padding: 0.7rem 0.9rem;
        border-radius: 1rem;
        background: rgba(15, 23, 42, 0.32);
        border: 1px solid rgba(96, 165, 250, 0.12);
    }

    .group-title {
        display: flex;
        flex-direction: column;
        gap: 0.2rem;
    }

    .group-controls {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .opponent-groups {
        display: grid;
        gap: 0.8rem;
    }

    .opponent-group {
        display: grid;
        gap: 0.5rem;
        padding: 0.5rem 0.65rem;
        border-radius: 0.85rem;
        background: rgba(15, 23, 42, 0.25);
        border: 1px solid rgba(148, 163, 184, 0.12);
    }

    .opponent-header {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 0.5rem;
    }

    .opponent-name {
        font-size: 0.92rem;
        font-weight: 600;
        color: rgba(226, 232, 240, 0.88);
    }

    .opponent-controls {
        display: flex;
        align-items: center;
        gap: 0.45rem;
    }

    .opponent-count {
        font-size: 0.75rem;
        color: rgba(148, 163, 184, 0.7);
        font-weight: 600;
    }

    .collapse-toggle {
        border: none;
        background: rgba(37, 99, 235, 0.18);
        color: #bfdbfe;
        width: 1.75rem;
        height: 1.75rem;
        border-radius: 999px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 1rem;
        cursor: pointer;
        transition: background 0.15s ease, color 0.15s ease, transform 0.15s ease;
    }

    .collapse-toggle.small {
        width: 1.5rem;
        height: 1.5rem;
        font-size: 0.9rem;
    }

    .collapse-toggle:hover {
        background: rgba(59, 130, 246, 0.32);
        color: #e0f2fe;
        transform: translateY(-1px);
    }

    .collapse-toggle:focus-visible {
        outline: 2px solid rgba(191, 219, 254, 0.9);
        outline-offset: 2px;
    }

    .game-group-header {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 0.6rem;
    }

    .game-group-header h4 {
        margin: 0;
        color: rgba(226, 232, 240, 0.88);
        font-size: 0.95rem;
        font-weight: 600;
    }

    .game-group-count {
        color: rgba(148, 163, 184, 0.75);
        font-size: 0.78rem;
        font-weight: 600;
    }

    .game-list {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }

    .game-list.compact {
        gap: 0.65rem;
    }

    .game-card {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.78rem 0.95rem;
        border-radius: 14px;
        border: 1px solid transparent;
        background: rgba(15, 23, 42, 0.5);
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
        gap: 0.65rem;
        align-items: center;
    }

    .game-opponent img {
        width: 32px;
        height: 32px;
        border-radius: 12px;
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
        padding: 0.25rem 0.6rem 0.25rem 0.25rem;
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        cursor: pointer;
        color: inherit;
        transition: background 0.15s ease;
    }

    .avatar-button:hover {
        background: rgba(37, 99, 235, 0.18);
    }

    .avatar-button img {
        width: 28px;
        height: 28px;
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

    .engage {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 0.35rem;
        background: linear-gradient(135deg, #ff299b 0%, #c084fc 55%, #2563eb 100%);
        color: #fdf4ff;
        border: none;
    }

    .engage:hover {
        background: linear-gradient(135deg, #ff3aa6 0%, #ca8dfc 55%, #3b82f6 100%);
    }

    .engage:focus-visible {
        outline: 3px solid rgba(192, 132, 252, 0.55);
        outline-offset: 4px;
    }

    .engage:disabled {
        opacity: 0.8;
        cursor: not-allowed;
    }

    .action-menu button.engage {
        text-align: center;
    }

    .action-menu button.engage:hover,
    .action-menu button.engage:focus {
        background: linear-gradient(135deg, #ff45af 0%, #d09bff 55%, #4f8df9 100%);
    }

    @media (max-width: 640px) {
        .hub {
            padding-inline: clamp(0.2rem, 4.25vw, 0.55rem);
        }

        .panel {
            padding: 0.5rem 0.56rem 0.72rem;
            gap: 0.72rem;
            border-radius: 0.68rem;
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

        .hub-header {
            flex-direction: column;
        }

        .hub-actions.desktop {
            display: none;
        }

        .hub-actions-mobile {
            display: flex;
            width: 100%;
            justify-content: space-between;
        }

        .game-sections {
            gap: 0.65rem;
        }

        .game-section {
            gap: 0.38rem;
        }

        .game-section-header {
            padding-inline: 0.05rem;
        }

        .game-count {
            min-width: 1.9rem;
            font-size: 0.7rem;
        }

        .game-list {
            gap: 0.42rem;
            margin-inline: -0.2rem;
        }

        .game-card {
            padding: 0.58rem 0.68rem;
            border-radius: 12px;
            background: rgba(15, 23, 42, 0.44);
        }

        .archive-groups {
            gap: 0.42rem;
            margin-inline: -0.22rem;
        }

        .game-group {
            padding: 0.15rem 0.18rem 0.4rem;
            border-radius: 0;
            background: transparent;
            border: none;
            border-bottom: 1px solid rgba(71, 85, 105, 0.28);
        }

        .game-group:last-child {
            border-bottom: none;
        }

        .opponent-groups {
            gap: 0.35rem;
        }

        .opponent-group {
            padding: 0.12rem 0.2rem 0.28rem;
            border-radius: 0;
            background: transparent;
            border: none;
        }
    }
</style>
