<script>
    import { onMount, onDestroy } from "svelte";
    import { get } from "svelte/store";
    import { Chess } from "chess.js";
    import ChessBoard from "../ChessBoard.svelte";
    import { createMiniEngine } from "../engine/miniEngine.js";
    import {
        detectInitialLocale,
        locale,
        setLocale,
        supportedLocales,
        t,
    } from "../i18n";

    export let showcaseFen = "";
    export let onPlay = (_credentials) => {};
    export let onAdminLogin = (_credentials) => {};
    export let error = "";
    export let isLoading = false;
    export let leaderboard = [];
    export let leaderboardError = "";
    export let isLeaderboardLoading = false;
    export let formatTime = (_iso) => "";

    let username = "";
    let password = "";

    const localeLabels = {
        en: "locale.english",
        ca: "locale.catalan",
    };
    const languageOptions = supportedLocales
        .map((code) => ({
            code,
            labelKey: localeLabels[code] ?? null,
        }))
        .filter((option) => option.labelKey);
    const detectedLocale = detectInitialLocale();
    let gameStatusKey = "";
    let gameStatusParams = {};
    let isGameOver = false;

    $: translatedLanguageOptions = languageOptions.map((option) => ({
        ...option,
        label: $t(option.labelKey),
    }));

    $: localeNote =
        $locale === detectedLocale
            ? $t("notice.language.detected")
            : $t("notice.language.manual");

    $: leaderboardTitle = $t("landing.leaderboard.title");
    $: leaderboardPlayerHeader = $t("landing.leaderboard.player");
    $: leaderboardRankHeader = $t("landing.leaderboard.rank");
    $: leaderboardRatingHeader = $t("landing.leaderboard.rating");
    $: leaderboardGamesHeader = $t("landing.leaderboard.games");
    $: leaderboardWinRateHeader = $t("landing.leaderboard.winRate");
    $: leaderboardLastPlayedHeader = $t("landing.leaderboard.lastPlayed");
    $: leaderboardRecordHeader = $t("landing.leaderboard.record");
    $: leaderboardPuzzlesHeader = $t("landing.leaderboard.puzzles");
    $: leaderboardPuzzleRateHeader = $t("landing.leaderboard.puzzleRate");
    $: leaderboardLastPuzzleHeader = $t("landing.leaderboard.lastPuzzle");
    $: leaderboardEmptyLabel = $t("landing.leaderboard.empty");
    $: leaderboardErrorLabel = $t("landing.leaderboard.error");
    $: leaderboardLoadingLabel = $t("landing.leaderboard.loading");
    $: leaderboardNeverLabel = $t("landing.leaderboard.never");
    $: resolvedLeaderboard = Array.isArray(leaderboard)
        ? [...leaderboard].sort((a, b) => (b?.rating ?? 0) - (a?.rating ?? 0))
        : [];

    const safeNumber = (value) => {
        return Number.isFinite(value) ? Number(value) : 0;
    };

    const formatPercentage = (value, { showDashWhenZero = false } = {}) => {
        if (typeof value !== "number" || !Number.isFinite(value)) {
            return showDashWhenZero ? "—" : "0%";
        }
        const percentage = Math.round(value * 100);
        if (percentage === 0 && showDashWhenZero) {
            return "—";
        }
        return `${percentage}%`;
    };

    const formatWinRate = (value, gamesPlayed = 0) => {
        if (!gamesPlayed) {
            return "—";
        }
        return formatPercentage(value, { showDashWhenZero: true });
    };

    const formatRecord = (entry) => {
        const wins = safeNumber(entry?.games_won);
        const losses = safeNumber(entry?.games_lost);
        const draws = safeNumber(entry?.games_drawn);
        return `${wins}-${losses}-${draws}`;
    };

    const recordLabelFor = (entry) => {
        const translator = get(t);
        const wins = safeNumber(entry?.games_won);
        const losses = safeNumber(entry?.games_lost);
        const draws = safeNumber(entry?.games_drawn);
        const total = safeNumber(entry?.games_played);
        return translator("landing.leaderboard.recordLabel", {
            wins,
            losses,
            draws,
            total,
        });
    };

    const formatPuzzleSummary = (entry) => {
        const solved = safeNumber(entry?.puzzles_solved);
        const attempted = safeNumber(entry?.puzzles_attempted);
        return `${solved}/${attempted || 0}`;
    };

    const puzzlesLabelFor = (entry) => {
        const translator = get(t);
        const solved = safeNumber(entry?.puzzles_solved);
        const attempted = safeNumber(entry?.puzzles_attempted);
        return translator("landing.leaderboard.puzzlesLabel", {
            solved,
            attempted,
        });
    };

    const formatPuzzleRate = (entry) => {
        const solved = safeNumber(entry?.puzzles_solved);
        const attempted = safeNumber(entry?.puzzles_attempted);
        if (!attempted) {
            return "—";
        }
        return formatPercentage(solved / attempted, { showDashWhenZero: true });
    };

    const puzzleRateLabelFor = (entry) => {
        const translator = get(t);
        const solved = safeNumber(entry?.puzzles_solved);
        const attempted = safeNumber(entry?.puzzles_attempted);
        const rate = attempted ? Math.round((solved / attempted) * 100) : 0;
        return translator("landing.leaderboard.puzzleRateLabel", {
            rate,
        });
    };

    const describeLeaderboardTime = (iso) => {
        if (!iso) {
            return leaderboardNeverLabel;
        }
        const text = formatTime(iso);
        return text || leaderboardNeverLabel;
    };

    const loginGame = new Chess();
    let miniEngine = null;
    let boardPosition = showcaseFen;
    let isThinking = false;
    let previousShowcase = null;
    let isActive = true;
    const fallbackAvatar = (username = "player") => {
        const slug = encodeURIComponent(username || "player");
        return `https://avatar.vercel.sh/${slug}`;
    };

    function handleLocaleSelect(code) {
        if (!code) {
            return;
        }
        const current = get(locale);
        if (code === current) {
            return;
        }
        setLocale(code);
    }

    function describeSide(color) {
        const translator = get(t);
        return color === "w"
            ? translator("color.white")
            : translator("color.black");
    }

    function setGameStatus(key = "", params = {}) {
        gameStatusKey = key;
        gameStatusParams = params;
    }

    function evaluateGameOutcome() {
        if (loginGame.isCheckmate()) {
            const winner =
                loginGame.turn() === "w"
                    ? describeSide("b")
                    : describeSide("w");
            setGameStatus("landing.status.checkmate", { winner });
            isGameOver = true;
            return;
        }

        if (loginGame.isStalemate()) {
            setGameStatus("landing.status.stalemate");
            isGameOver = true;
            return;
        }

        if (loginGame.isThreefoldRepetition()) {
            setGameStatus("landing.status.repetition");
            isGameOver = true;
            return;
        }

        if (loginGame.isInsufficientMaterial()) {
            setGameStatus("landing.status.insufficient");
            isGameOver = true;
            return;
        }

        if (loginGame.isDraw()) {
            setGameStatus("landing.status.draw");
            isGameOver = true;
            return;
        }

        setGameStatus();
        isGameOver = false;
    }

    $: if ($locale) {
        evaluateGameOutcome();
    }

    function initialiseMiniGame() {
        miniEngine = createMiniEngine();
        miniEngine.reset();
        try {
            if (showcaseFen) {
                loginGame.load(showcaseFen);
            } else {
                loginGame.reset();
            }
        } catch (_error) {
            loginGame.reset();
        }
        boardPosition = loginGame.fen();
        previousShowcase = showcaseFen;
        setGameStatus();
        isGameOver = false;
        evaluateGameOutcome();
    }

    onMount(() => {
        initialiseMiniGame();
    });

    onDestroy(() => {
        isActive = false;
    });

    $: if (miniEngine && showcaseFen !== previousShowcase) {
        initialiseMiniGame();
    }

    const toUci = (move) => `${move.from}${move.to}${move.promotion ?? ""}`;

    async function handleBoardMove(event) {
        if (!miniEngine || isThinking || isGameOver) {
            return;
        }

        const { move } = event;
        if (!move) {
            return;
        }

        const playerMoveUci = toUci(move);
        const executed = loginGame.move(move);
        if (!executed) {
            return;
        }

        try {
            miniEngine.applyMove(playerMoveUci);
        } catch (_error) {
            loginGame.undo();
            boardPosition = loginGame.fen();
            evaluateGameOutcome();
            return;
        }

        boardPosition = loginGame.fen();
        evaluateGameOutcome();
        if (isGameOver || !isActive) {
            return;
        }

        isThinking = true;
        try {
            const reply = await miniEngine.think();
            if (!reply || !isActive) {
                evaluateGameOutcome();
                return;
            }

            const replyMove = {
                from: reply.slice(0, 2),
                to: reply.slice(2, 4),
            };
            if (reply.length > 4) {
                replyMove.promotion = reply[4];
            }

            const executed = loginGame.move(replyMove);
            if (executed) {
                boardPosition = loginGame.fen();
                evaluateGameOutcome();
            } else {
                try {
                    loginGame.load(boardPosition);
                } catch (_error) {
                    loginGame.reset();
                    boardPosition = loginGame.fen();
                }
                evaluateGameOutcome();
            }
        } finally {
            if (isActive) {
                isThinking = false;
            }
        }
    }

    const submit = () => {
        onPlay({ username, password });
    };

    const submitAdmin = () => {
        onAdminLogin({ username, password });
    };
</script>

<main class="landing">
    <section class="landing-card glass-panel">
        {#if translatedLanguageOptions.length > 1}
            <div class="language-switcher">
                <div
                    class="landing-lang"
                    role="group"
                    aria-label={$t("landing.language.label")}
                >
                    {#each translatedLanguageOptions as option}
                        <button
                            type="button"
                            class:active={option.code === $locale}
                            on:click={() => handleLocaleSelect(option.code)}
                            aria-pressed={option.code === $locale}
                            aria-label={$t("landing.language.aria")}
                        >
                            {option.label}
                        </button>
                    {/each}
                </div>
                <p class="language-note">{localeNote}</p>
            </div>
        {/if}
        <div class="landing-header">
            <span class="landing-badge">{$t("landing.badge")}</span>
            <h1>{$t("landing.title")}</h1>
            <p class="landing-copy">{$t("landing.copy")}</p>
        </div>
        <div class="landing-board-shell">
            <ChessBoard
                startingFen={showcaseFen}
                positionFen={boardPosition}
                showStatus={false}
                showControls={false}
                interactive={!isThinking && !isGameOver}
                onMove={handleBoardMove}
            />
            {#if gameStatusKey}
                <p class="landing-status" role="status" aria-live="polite">
                    {$t(gameStatusKey, gameStatusParams)}
                </p>
            {/if}
        </div>
        <form class="landing-form" on:submit|preventDefault={submit}>
            <label for="username">{$t("landing.form.username")}</label>
            <input
                id="username"
                name="username"
                autocomplete="username"
                placeholder={$t("landing.form.usernamePlaceholder")}
                bind:value={username}
                required
            />
            <label for="password">{$t("landing.form.password")}</label>
            <input
                id="password"
                name="password"
                type="password"
                autocomplete="current-password"
                placeholder={$t("landing.form.passwordPlaceholder")}
                bind:value={password}
                required
            />
            {#if error}
                <p class="error" role="alert">{error}</p>
            {/if}
            <div class="landing-actions">
                <button type="submit" disabled={isLoading}>
                    {isLoading
                        ? $t("landing.actions.signingIn")
                        : $t("landing.actions.play")}
                </button>
                <button
                    class="secondary compact"
                    type="button"
                    on:click={submitAdmin}
                    disabled={isLoading}
                >
                    {$t("landing.actions.admin")}
                </button>
            </div>
        </form>
        <section class="leaderboard-card">
            <h2>{leaderboardTitle}</h2>
            {#if leaderboardError}
                <p class="leaderboard-error" role="alert">
                    {leaderboardError ?? leaderboardErrorLabel}
                </p>
            {:else if resolvedLeaderboard.length}
                <div class="leaderboard-table-wrapper">
                    <table class="leaderboard-table">
                        <colgroup>
                            <col class="col-rank" />
                            <col class="col-player" />
                            <col class="col-rating" />
                            <col class="col-games" />
                            <col class="col-record" />
                            <col class="col-win" />
                            <col class="col-puzzles" />
                            <col class="col-puzzle-rate" />
                            <col class="col-last" />
                            <col class="col-last" />
                        </colgroup>
                        <thead>
                            <tr>
                                <th scope="col" class="col-rank">{leaderboardRankHeader}</th>
                                <th scope="col" class="col-player">{leaderboardPlayerHeader}</th>
                                <th scope="col" class="col-rating numeric">{leaderboardRatingHeader}</th>
                                <th scope="col" class="col-games numeric">{leaderboardGamesHeader}</th>
                                <th scope="col" class="col-record numeric">{leaderboardRecordHeader}</th>
                                <th scope="col" class="col-win numeric">{leaderboardWinRateHeader}</th>
                                <th scope="col" class="col-puzzles numeric">{leaderboardPuzzlesHeader}</th>
                                <th scope="col" class="col-puzzle-rate numeric">{leaderboardPuzzleRateHeader}</th>
                                <th scope="col" class="col-last">{leaderboardLastPlayedHeader}</th>
                                <th scope="col" class="col-last">{leaderboardLastPuzzleHeader}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {#each resolvedLeaderboard as entry, index}
                                <tr>
                                    <td class="numeric">{index + 1}</td>
                                    <th scope="row">
                                        <div class="leaderboard-player">
                                            <img
                                                src={entry.avatar_url || fallbackAvatar(entry.username)}
                                                alt={entry.username}
                                            />
                                            <div>
                                                <strong>{entry.username}</strong>
                                            </div>
                                        </div>
                                    </th>
                                    <td class="numeric">
                                        {Number.isFinite(entry.rating) ? entry.rating : "—"}
                                    </td>
                                    <td class="numeric">{safeNumber(entry.games_played)}</td>
                                    <td class="numeric" title={recordLabelFor(entry)}>
                                        {formatRecord(entry)}
                                    </td>
                                    <td class="numeric">{formatWinRate(entry.win_rate, entry.games_played)}</td>
                                    <td class="numeric" title={puzzlesLabelFor(entry)}>
                                        {formatPuzzleSummary(entry)}
                                    </td>
                                    <td class="numeric" title={puzzleRateLabelFor(entry)}>
                                        {formatPuzzleRate(entry)}
                                    </td>
                                    <td class="timestamp">
                                        {describeLeaderboardTime(entry.last_game_at || entry.last_activity_at)}
                                    </td>
                                    <td class="timestamp">
                                        {describeLeaderboardTime(entry.last_puzzle_attempt_at)}
                                    </td>
                                </tr>
                            {/each}
                        </tbody>
                    </table>
                </div>
                {#if isLeaderboardLoading}
                    <p class="leaderboard-info subtle">{leaderboardLoadingLabel}</p>
                {/if}
            {:else if isLeaderboardLoading}
                <p class="leaderboard-info">{leaderboardLoadingLabel}</p>
            {:else}
                <p class="leaderboard-info">{leaderboardEmptyLabel}</p>
            {/if}
        </section>
    </section>
</main>

<style>
    .landing {
        width: min(620px, 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto;
    }

    @media (min-width: 1280px) {
        .landing {
            width: min(720px, 100%);
        }
    }

    .landing-card {
        width: 100%;
        padding: clamp(1.75rem, 5vw, 2.5rem);
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
    }

    .language-switcher {
        align-self: flex-end;
        display: grid;
        gap: 0.35rem;
        text-align: right;
    }

    .landing-lang {
        display: inline-flex;
        gap: 0.35rem;
        padding: 0.25rem;
        border-radius: 999px;
        background: rgba(15, 23, 42, 0.45);
        backdrop-filter: blur(8px);
    }

    .landing-lang button {
        border: none;
        background: transparent;
        color: rgba(226, 232, 240, 0.75);
        font-weight: 600;
        font-size: 0.82rem;
        padding: 0.35rem 0.65rem;
        border-radius: 999px;
        cursor: pointer;
        transition: background 0.15s ease, color 0.15s ease;
    }

    .landing-lang button:hover {
        background: rgba(59, 130, 246, 0.28);
        color: #e0f2fe;
    }

    .landing-lang button.active {
        background: rgba(37, 99, 235, 0.65);
        color: #e0f2fe;
    }

    .language-note {
        margin: 0;
        font-size: 0.75rem;
        color: rgba(148, 163, 184, 0.7);
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
        flex-direction: column;
        justify-content: center;
        align-items: center;
        gap: 0.75rem;
    }

    .landing-card :global(.chess-widget) {
        width: 100%;
    }

    .landing-card :global(.board) {
        width: min(400px, 100%);
        margin-inline: auto;
    }

    .landing-status {
        margin: 0;
        font-size: 0.9rem;
        color: rgba(226, 232, 240, 0.85);
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

    .landing-form {
        display: grid;
        gap: 0.75rem;
    }

    .leaderboard-card {
        display: grid;
        gap: 1rem;
        padding-top: 1.5rem;
        border-top: 1px solid rgba(148, 163, 184, 0.2);
    }

    .leaderboard-table-wrapper {
        overflow-x: auto;
        border-radius: 0.75rem;
        border: 1px solid rgba(148, 163, 184, 0.15);
        background: rgba(15, 23, 42, 0.4);
    }

    .leaderboard-table {
        width: 100%;
        border-collapse: collapse;
        min-width: 760px;
    }

    .leaderboard-table th,
    .leaderboard-table td {
        padding: 0.65rem 0.9rem;
        text-align: left;
        font-size: 0.9rem;
        color: rgba(226, 232, 240, 0.85);
        border-bottom: 1px solid rgba(148, 163, 184, 0.12);
        white-space: nowrap;
    }

    .leaderboard-table tbody tr:last-child th,
    .leaderboard-table tbody tr:last-child td {
        border-bottom: none;
    }

    .leaderboard-table thead th {
        color: rgba(148, 163, 184, 0.85);
        font-weight: 600;
        text-transform: uppercase;
        font-size: 0.78rem;
        letter-spacing: 0.06em;
        background: rgba(15, 23, 42, 0.55);
    }

    .leaderboard-table .numeric {
        text-align: right;
    }

    .leaderboard-table .col-player {
        width: 18rem;
    }

    .leaderboard-table .col-rating,
    .leaderboard-table .col-games,
    .leaderboard-table .col-record,
    .leaderboard-table .col-win,
    .leaderboard-table .col-puzzles,
    .leaderboard-table .col-puzzle-rate {
        width: 6.5rem;
    }

    .leaderboard-player {
        display: flex;
        align-items: center;
        gap: 0.65rem;
    }

    .leaderboard-player img {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        object-fit: cover;
        background: rgba(148, 163, 184, 0.2);
    }

    .leaderboard-info {
        margin: 0;
        color: rgba(148, 163, 184, 0.85);
        font-size: 0.85rem;
    }

    .leaderboard-info.subtle {
        color: rgba(148, 163, 184, 0.65);
        font-style: italic;
    }

    .leaderboard-error {
        margin: 0;
        color: #fda4af;
        font-size: 0.9rem;
        background: rgba(244, 63, 94, 0.12);
        border: 1px solid rgba(244, 63, 94, 0.35);
        padding: 0.75rem;
        border-radius: 0.75rem;
    }

    .leaderboard-table .timestamp {
        color: rgba(226, 232, 240, 0.7);
        font-variant-numeric: tabular-nums;
        white-space: nowrap;
    }

    .error {
        margin: 0;
        color: #f87171;
        font-size: 0.9rem;
    }

    @media (max-width: 640px) {
        .landing-card {
            padding: 1.5rem;
            gap: 1.25rem;
        }

        .language-switcher {
            align-self: center;
            text-align: center;
        }

        .landing-actions {
            flex-direction: column;
            align-items: stretch;
        }

        .landing-actions button {
            width: 100%;
        }

        .leaderboard-card {
            padding-top: 1rem;
        }

        .leaderboard-table {
            min-width: 640px;
        }
    }
</style>
