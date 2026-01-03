<script>
    import { t } from "../i18n";

    export let users = [];
    export let isLoading = false;
    export let error = "";
    export let onRefresh = () => {};
    export let onBack = () => {};
    export let onLogout = () => {};
    export let formatTime = (_iso) => "";
    export let selectedUserId = null;
    export let onSelectUser = (_id) => {};
    export let userGames = [];
    export let gamesLoading = false;
    export let gamesError = "";
    export let onAnalyzeGame = (_game) => {};

    let sortKey = "activity";
    let sortDirection = "desc";

    const fallbackAvatar = (username = "player") => {
        const slug = encodeURIComponent(username || "player");
        return `https://avatar.vercel.sh/${slug}`;
    };

    const toTimestamp = (iso) => {
        if (!iso) {
            return 0;
        }
        const time = new Date(iso).getTime();
        return Number.isFinite(time) ? time : 0;
    };

    const valueForSort = (user, key) => {
        if (!user) {
            return 0;
        }
        switch (key) {
            case "rating":
                return Number.isFinite(user?.rating) ? user.rating : 0;
            case "games":
                return Number.isFinite(user?.games_played) ? user.games_played : 0;
            case "puzzles":
                return Number.isFinite(user?.puzzles_solved)
                    ? user.puzzles_solved
                    : 0;
            case "name":
                return (user?.username ?? "").toLowerCase();
            case "activity":
            default:
                return toTimestamp(user?.last_activity_at);
        }
    };

    const compareValues = (a, b) => {
        if (typeof a === "number" && typeof b === "number") {
            return a - b;
        }
        const aText = String(a ?? "");
        const bText = String(b ?? "");
        return aText.localeCompare(bText);
    };

    const changeSort = (key) => {
        if (sortKey === key) {
            sortDirection = sortDirection === "desc" ? "asc" : "desc";
        } else {
            sortKey = key;
            sortDirection = key === "name" ? "asc" : "desc";
        }
    };

    const describeTime = (iso, fallback) => {
        if (!iso) {
            return fallback;
        }
        const text = formatTime(iso);
        return text || fallback;
    };

    const describeAbsolute = (iso) => {
        if (!iso) {
            return "";
        }
        const date = new Date(iso);
        if (Number.isNaN(date.getTime())) {
            return iso;
        }
        return date.toLocaleString();
    };

    const resultLabel = (result) => {
        if (result === "white") {
            return $t("admin.games.resultWhite");
        }
        if (result === "black") {
            return $t("admin.games.resultBlack");
        }
        if (result === "draw") {
            return $t("admin.games.resultDraw");
        }
        return "—";
    };

    const statusLabelFor = (status) => {
        switch (status) {
            case "pending":
                return $t("admin.games.status.pending");
            case "active":
                return $t("admin.games.status.active");
            case "completed":
                return $t("admin.games.status.completed");
            case "aborted":
                return $t("admin.games.status.aborted");
            default:
                return status || "";
        }
    };

    const opponentForGame = (game) => {
        if (!game || selectedUserId === null) {
            return null;
        }
        if (game.white_player_id === selectedUserId) {
            return {
                id: game.black_player_id,
                username: game.black_player_username,
                rating: game.black_player_rating,
            };
        }
        return {
            id: game.white_player_id,
            username: game.white_player_username,
            rating: game.white_player_rating,
        };
    };

    const opponentNameFor = (game) => {
        const opponent = opponentForGame(game);
        const name = opponent?.username ?? "";
        return name || $t("label.unknown");
    };

    const opponentRatingFor = (game) => {
        const opponent = opponentForGame(game);
        return Number.isFinite(opponent?.rating) ? opponent.rating : null;
    };

    const opponentAvatarFor = (game) => {
        const opponent = opponentForGame(game);
        return fallbackAvatar(opponent?.username || "player");
    };

    const lastMoveTimeFor = (game) => describeTime(game?.last_move_at, neverLabel);
    const startedTimeFor = (game) => describeTime(game?.started_at, neverLabel);

    const handleRowKeydown = (event, userId) => {
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            selectUser(userId);
        }
    };

    const puzzleRate = (solved, attempted) => {
        if (!attempted) {
            return 0;
        }
        return Math.round((solved / attempted) * 100);
    };

    const puzzlesSummaryText = (user) => {
        const solved = Number.isFinite(user?.puzzles_solved) ? user.puzzles_solved : 0;
        const attempted = Number.isFinite(user?.puzzles_attempted)
            ? user.puzzles_attempted
            : 0;
        const rate = puzzleRate(solved, attempted);
        return puzzlesSummaryTemplate
            .replace("{solved}", solved)
            .replace("{attempted}", attempted)
            .replace("{rate}", rate);
    };

    const recordSummaryText = (user) => {
        const wins = Number.isFinite(user?.games_won) ? user.games_won : 0;
        const losses = Number.isFinite(user?.games_lost) ? user.games_lost : 0;
        const draws = Number.isFinite(user?.games_drawn) ? user.games_drawn : 0;
        return recordSummaryTemplate
            .replace("{wins}", wins)
            .replace("{losses}", losses)
            .replace("{draws}", draws);
    };

    const selectUser = (userId) => {
        if (typeof onSelectUser === "function") {
            onSelectUser(userId);
        }
    };

    $: headerTitle = $t("admin.heading");
    $: headerSubtitle = $t("admin.subheading");
    $: backLabel = $t("admin.back");
    $: refreshLabel = $t("admin.actions.refresh");
    $: logoutLabel = $t("admin.actions.logout");
    $: loadingLabel = $t("admin.loading");
    $: playerHeader = $t("admin.table.player");
    $: ratingHeader = $t("admin.table.rating");
    $: gamesHeader = $t("admin.table.games");
    $: recordHeader = $t("admin.table.record");
    $: activeHeader = $t("admin.table.active");
    $: lastGameHeader = $t("admin.table.lastGame");
    $: puzzlesHeader = $t("admin.table.puzzles");
    $: lastPuzzleHeader = $t("admin.table.lastPuzzle");
    $: lastActiveHeader = $t("admin.table.lastActive");
    $: emptyLabel = $t("admin.empty");
    $: adminBadge = $t("admin.badge.admin");
    $: engineBadge = $t("admin.badge.engine");
    $: joinedTemplate = $t("admin.meta.joined");
    $: neverLabel = $t("admin.activity.never");
    $: recordSummaryTemplate = $t("admin.record.summary");
    $: puzzlesSummaryTemplate = $t("admin.puzzles.summary");
    $: gamesHeading = $t("admin.games.heading");
    $: gamesSubheading = $t("admin.games.subheading");
    $: gamesEmptyLabel = $t("admin.games.empty");
    $: gamesPlaceholder = $t("admin.games.placeholder");
    $: gamesErrorLabel = $t("admin.games.error");
    $: gamesLoadingLabel = $t("admin.games.loading");
    $: gamesOpponentHeader = $t("admin.games.opponent");
    $: gamesStatusHeader = $t("admin.games.status");
    $: gamesResultHeader = $t("admin.games.result");
    $: gamesMovesHeader = $t("admin.games.moves");
    $: gamesStartedHeader = $t("admin.games.started");
    $: gamesLastMoveHeader = $t("admin.games.lastMove");
    $: gamesActionHeader = $t("admin.games.action");
    $: gamesAnalyzeLabel = $t("admin.games.analyze");

    $: sortedUsers = Array.isArray(users)
        ? [...users].sort((a, b) => {
              const left = valueForSort(a, sortKey);
              const right = valueForSort(b, sortKey);
              const comparison = compareValues(left, right);
              return sortDirection === "desc" ? -comparison : comparison;
          })
        : [];

    $: selectedUser = users.find((user) => user.id === selectedUserId) ?? null;
    $: resolvedGames = Array.isArray(userGames) ? userGames : [];
    $: gamesSubtitle = selectedUser
        ? $t("admin.games.selected", { name: selectedUser.username })
        : gamesSubheading;

    const sortState = (key) => {
        if (sortKey !== key) {
            return "none";
        }
        return sortDirection === "desc" ? "descending" : "ascending";
    };

    const sortIndicator = (key) => {
        if (sortKey !== key) {
            return "";
        }
        return sortDirection === "desc" ? "v" : "^";
    };

    const joinedLabel = (iso) => {
        if (!iso) {
            return "";
        }
        const date = new Date(iso);
        if (Number.isNaN(date.getTime())) {
            return joinedTemplate.replace("{date}", iso);
        }
        const formatted = date.toLocaleDateString();
        return joinedTemplate.replace("{date}", formatted);
    };
</script>

<main class="admin">
    <header class="admin-header">
        <button type="button" class="secondary small" on:click={onBack}>
            {backLabel}
        </button>
        <div class="header-actions">
            <button
                type="button"
                class="secondary small"
                on:click={onRefresh}
                disabled={isLoading}
            >
                {refreshLabel}
            </button>
            <button type="button" class="small" on:click={onLogout}>
                {logoutLabel}
            </button>
        </div>
    </header>

    <section class="admin-card glass-panel">
        <div class="card-header">
            <div>
                <h1>{headerTitle}</h1>
                <p>{headerSubtitle}</p>
            </div>
            {#if isLoading}
                <span class="status-pill">{loadingLabel}</span>
            {/if}
        </div>

        {#if error}
            <p class="error" role="alert">{error}</p>
        {/if}

        {#if sortedUsers.length}
            <div class="table-wrapper">
                <table class="admin-table">
                    <colgroup>
                        <col class="col-player" />
                        <col class="col-rating" />
                        <col class="col-games" />
                        <col class="col-record" />
                        <col class="col-active" />
                        <col class="col-last" />
                        <col class="col-puzzles" />
                        <col class="col-last" />
                        <col class="col-last" />
                    </colgroup>
                    <thead>
                        <tr>
                            <th scope="col" class="col-player" aria-sort={sortState("name")}>
                                <button
                                    type="button"
                                    class="sort-button"
                                    on:click={() => changeSort("name")}
                                >
                                    {playerHeader}
                                    <span class="indicator">{sortIndicator("name")}</span>
                                </button>
                            </th>
                            <th scope="col" class="col-rating numeric" aria-sort={sortState("rating")}>
                                <button
                                    type="button"
                                    class="sort-button"
                                    on:click={() => changeSort("rating")}
                                >
                                    {ratingHeader}
                                    <span class="indicator">{sortIndicator("rating")}</span>
                                </button>
                            </th>
                            <th scope="col" class="col-games numeric" aria-sort={sortState("games")}>
                                <button
                                    type="button"
                                    class="sort-button"
                                    on:click={() => changeSort("games")}
                                >
                                    {gamesHeader}
                                    <span class="indicator">{sortIndicator("games")}</span>
                                </button>
                            </th>
                            <th scope="col" class="col-record numeric">{recordHeader}</th>
                            <th scope="col" class="col-active numeric">{activeHeader}</th>
                            <th scope="col" class="col-last">{lastGameHeader}</th>
                            <th scope="col" class="col-puzzles" aria-sort={sortState("puzzles")}>
                                <button
                                    type="button"
                                    class="sort-button"
                                    on:click={() => changeSort("puzzles")}
                                >
                                    {puzzlesHeader}
                                    <span class="indicator">{sortIndicator("puzzles")}</span>
                                </button>
                            </th>
                            <th scope="col" class="col-last">{lastPuzzleHeader}</th>
                            <th scope="col" class="col-last" aria-sort={sortState("activity")}>
                                <button
                                    type="button"
                                    class="sort-button"
                                    on:click={() => changeSort("activity")}
                                >
                                    {lastActiveHeader}
                                    <span class="indicator">{sortIndicator("activity")}</span>
                                </button>
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each sortedUsers as user}
                            <tr
                                class="selectable"
                                class:selected={user.id === selectedUserId}
                                role="button"
                                tabindex="0"
                                aria-pressed={user.id === selectedUserId}
                                on:click={() => selectUser(user.id)}
                                on:keydown={(event) => handleRowKeydown(event, user.id)}
                            >
                                <th scope="row">
                                    <div class="player">
                                        <img
                                            src={user.avatar_url || fallbackAvatar(user.username)}
                                            alt={user.username}
                                        />
                                        <div>
                                            <strong>{user.username}</strong>
                                            <div class="player-meta">
                                                <span>{joinedLabel(user.created_at)}</span>
                                                <div class="badges">
                                                    {#if user.is_admin}
                                                        <span class="badge admin">{adminBadge}</span>
                                                    {/if}
                                                    {#if user.is_engine}
                                                        <span class="badge engine">{engineBadge}</span>
                                                    {/if}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </th>
                                <td class="numeric">{Number.isFinite(user.rating) ? user.rating : "—"}</td>
                                <td class="numeric">{user.games_played}</td>
                                <td class="record" title={recordSummaryText(user)}>
                                    <span class="wins">{user.games_won}</span>
                                    <span class="divider">/</span>
                                    <span class="losses">{user.games_lost}</span>
                                    <span class="divider">/</span>
                                    <span class="draws">{user.games_drawn}</span>
                                </td>
                                <td class="numeric">{user.active_games}</td>
                                <td class="timestamp" title={describeAbsolute(user.last_game_at)}>
                                    {describeTime(user.last_game_at, neverLabel)}
                                </td>
                                <td class="puzzle-cell" title={puzzlesSummaryText(user)}>
                                    <span class="emphasis">{user.puzzles_solved}</span>
                                    <span class="muted">
                                        / {user.puzzles_attempted}
                                        ({puzzleRate(user.puzzles_solved, user.puzzles_attempted)}%)
                                    </span>
                                </td>
                                <td class="timestamp" title={describeAbsolute(user.last_puzzle_attempt_at)}>
                                    {describeTime(user.last_puzzle_attempt_at, neverLabel)}
                                </td>
                                <td class="timestamp" title={describeAbsolute(user.last_activity_at)}>
                                    {describeTime(user.last_activity_at, neverLabel)}
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        {:else if !isLoading}
            <p class="empty">{emptyLabel}</p>
        {/if}
    </section>

    <section class="admin-card glass-panel admin-games-card">
        <div class="card-header">
            <div>
                <h2>{gamesHeading}</h2>
                <p>{gamesSubtitle}</p>
            </div>
            {#if gamesLoading}
                <span class="status-pill">{gamesLoadingLabel}</span>
            {/if}
        </div>

        {#if gamesError}
            <p class="error" role="alert">{gamesError || gamesErrorLabel}</p>
        {:else if !selectedUser}
            <p class="empty">{gamesPlaceholder}</p>
        {:else}
            <div class="selected-overview">
                <div class="player">
                    <img
                        src={selectedUser.avatar_url || fallbackAvatar(selectedUser.username)}
                        alt={selectedUser.username}
                    />
                    <div>
                        <strong>{selectedUser.username}</strong>
                        <div class="selected-meta">{recordSummaryText(selectedUser)}</div>
                        <div class="selected-meta">{puzzlesSummaryText(selectedUser)}</div>
                    </div>
                </div>
                <dl class="selected-stats">
                    <div>
                        <dt>{ratingHeader}</dt>
                        <dd>{Number.isFinite(selectedUser.rating) ? selectedUser.rating : "—"}</dd>
                    </div>
                    <div>
                        <dt>{gamesHeader}</dt>
                        <dd>{selectedUser.games_played}</dd>
                    </div>
                    <div>
                        <dt>{lastGameHeader}</dt>
                        <dd>{describeTime(selectedUser.last_game_at, neverLabel)}</dd>
                    </div>
                    <div>
                        <dt>{lastActiveHeader}</dt>
                        <dd>{describeTime(selectedUser.last_activity_at, neverLabel)}</dd>
                    </div>
                </dl>
            </div>

            {#if !resolvedGames.length && !gamesLoading}
                <p class="empty">{gamesEmptyLabel}</p>
            {:else if resolvedGames.length}
                <div class="table-wrapper">
                    <table class="admin-table games-table">
                        <colgroup>
                            <col class="col-player" />
                            <col class="col-status" />
                            <col class="col-result" />
                            <col class="col-moves" />
                            <col class="col-timestamp" />
                            <col class="col-timestamp" />
                            <col class="col-action" />
                        </colgroup>
                        <thead>
                            <tr>
                                <th scope="col" class="col-player">{gamesOpponentHeader}</th>
                                <th scope="col" class="col-status">{gamesStatusHeader}</th>
                                <th scope="col" class="col-result">{gamesResultHeader}</th>
                                <th scope="col" class="col-moves numeric">{gamesMovesHeader}</th>
                                <th scope="col" class="col-timestamp">{gamesStartedHeader}</th>
                                <th scope="col" class="col-timestamp">{gamesLastMoveHeader}</th>
                                <th scope="col" class="col-action">{gamesActionHeader}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {#each resolvedGames as game}
                                <tr>
                                    <th scope="row">
                                        <div class="opponent-cell">
                                            <img src={opponentAvatarFor(game)} alt={opponentNameFor(game)} />
                                            <div>
                                                <strong>{opponentNameFor(game)}</strong>
                                                <span class="muted">{opponentRatingFor(game) ?? "—"}</span>
                                            </div>
                                        </div>
                                    </th>
                                    <td>{statusLabelFor(game.status)}</td>
                                    <td>{resultLabel(game.result)}</td>
                                    <td class="numeric">{game.moves_count}</td>
                                    <td class="timestamp">{startedTimeFor(game)}</td>
                                    <td class="timestamp">{lastMoveTimeFor(game)}</td>
                                    <td class="action-cell">
                                        <button
                                            type="button"
                                            class="small"
                                            on:click|stopPropagation={() => onAnalyzeGame(game)}
                                        >
                                            {gamesAnalyzeLabel}
                                        </button>
                                    </td>
                                </tr>
                            {/each}
                        </tbody>
                    </table>
                </div>
            {/if}
        {/if}
    </section>
</main>

<style>
    .admin {
        width: 100%;
        max-width: 1320px;
        margin: 0 auto;
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
        padding: 1rem 2rem 2.75rem;
    }

    .admin-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .header-actions {
        display: flex;
        gap: 0.75rem;
    }

    .small {
        padding: 0.5em 1.1em;
        font-size: 0.9rem;
    }

    .admin-card {
        display: flex;
        flex-direction: column;
        gap: 1.25rem;
        padding: clamp(1.75rem, 4vw, 2.2rem);
    }

    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
    }

    .card-header h1 {
        margin: 0;
        color: #f8fafc;
        font-size: clamp(1.7rem, 5vw, 2rem);
    }

    .card-header p {
        margin: 0.35rem 0 0;
        color: rgba(226, 232, 240, 0.75);
    }

    .status-pill {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0.35rem 0.9rem;
        border-radius: 999px;
        background: rgba(37, 99, 235, 0.18);
        color: #bfdbfe;
        font-size: 0.85rem;
        font-weight: 600;
    }

    .error {
        margin: 0;
        background: rgba(239, 68, 68, 0.12);
        border: 1px solid rgba(239, 68, 68, 0.3);
        color: #fecaca;
        padding: 0.65rem 1rem;
        border-radius: 12px;
        font-size: 0.9rem;
    }

    .table-wrapper {
        overflow-x: auto;
        border-radius: 18px;
        box-shadow: 0 22px 48px rgba(8, 11, 26, 0.45);
    }

    .admin-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        min-width: 960px;
        background: rgba(15, 23, 42, 0.55);
        border: 1px solid rgba(59, 130, 246, 0.18);
        border-radius: 18px;
    }

    .admin-table col.col-player {
        width: 260px;
    }

    .admin-table col.col-rating,
    .admin-table col.col-games,
    .admin-table col.col-record,
    .admin-table col.col-active {
        width: 110px;
    }

    .admin-table col.col-last {
        width: 160px;
    }

    .admin-table col.col-puzzles {
        width: 180px;
    }

    .admin-table thead th {
        padding: 0.65rem 0.9rem;
        color: rgba(226, 232, 240, 0.7);
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        background: linear-gradient(135deg, rgba(30, 64, 175, 0.38), rgba(59, 130, 246, 0.18));
        border-bottom: 1px solid rgba(148, 163, 184, 0.22);
    }

    .admin-table thead th:first-child {
        border-top-left-radius: 17px;
    }

    .admin-table thead th:last-child {
        border-top-right-radius: 17px;
    }

    .admin-table .sort-button {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        background: none;
        border: none;
        padding: 0;
        color: inherit;
        font: inherit;
        cursor: pointer;
    }

    .admin-table .sort-button:disabled {
        cursor: default;
    }

    .indicator {
        font-size: 0.75rem;
        color: rgba(148, 163, 184, 0.7);
    }

    .admin-table tbody th,
    .admin-table tbody td {
        padding: 0.8rem 0.95rem;
        border-bottom: 1px solid rgba(148, 163, 184, 0.12);
        color: rgba(226, 232, 240, 0.9);
        font-size: 0.95rem;
        vertical-align: middle;
        background-clip: padding-box;
    }

    .admin-table tbody tr:last-child th,
    .admin-table tbody tr:last-child td {
        border-bottom: none;
    }

    .admin-table tbody tr:nth-child(odd) {
        background: rgba(15, 23, 42, 0.42);
    }

    .admin-table tbody tr:nth-child(even) {
        background: rgba(15, 23, 42, 0.34);
    }

    .admin-table tbody tr:hover {
        background: rgba(30, 64, 175, 0.28);
    }

    .admin-table tr.selectable {
        cursor: pointer;
        transition: background 0.15s ease, transform 0.15s ease;
    }

    .admin-table tr.selectable:focus {
        outline: 2px solid rgba(59, 130, 246, 0.4);
        outline-offset: -2px;
    }

    .admin-table tr.selected {
        background: rgba(59, 130, 246, 0.18);
    }

    .admin-table .numeric,
    .record,
    .timestamp,
    .puzzle-cell {
        font-variant-numeric: tabular-nums;
    }

    .admin-table .numeric,
    .record {
        text-align: right;
    }

    .admin-table thead th.numeric {
        text-align: right;
    }

    .admin-table thead th.numeric .sort-button {
        justify-content: flex-end;
    }

    .timestamp {
        text-align: right;
        white-space: nowrap;
    }

    .record {
        display: flex;
        justify-content: flex-end;
        align-items: center;
        gap: 0.25rem;
    }

    .record .wins {
        color: #34d399;
    }

    .record .losses {
        color: #fca5a5;
    }

    .record .draws {
        color: #fef08a;
    }

    .record .divider {
        color: rgba(148, 163, 184, 0.6);
    }

    .puzzle-cell {
        display: flex;
        justify-content: flex-end;
        gap: 0.35rem;
    }

    .player {
        display: flex;
        align-items: center;
        gap: 0.85rem;
    }

    .player img {
        width: 48px;
        height: 48px;
        border-radius: 16px;
        object-fit: cover;
        border: 1px solid rgba(148, 163, 184, 0.3);
    }

    .player strong {
        display: block;
        font-size: 1rem;
        color: #f8fafc;
    }

    .player-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 0.35rem 0.75rem;
        color: rgba(148, 163, 184, 0.75);
        font-size: 0.8rem;
    }

    .badges {
        display: inline-flex;
        gap: 0.35rem;
    }

    .badge {
        padding: 0.2rem 0.55rem;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .badge.admin {
        background: rgba(59, 130, 246, 0.35);
        color: #dbeafe;
    }

    .badge.engine {
        background: rgba(16, 185, 129, 0.3);
        color: #bbf7d0;
    }

    .muted {
        color: rgba(148, 163, 184, 0.75);
        font-size: 0.85rem;
    }

    .emphasis {
        font-weight: 600;
        color: #f8fafc;
    }

    .empty {
        margin: 0;
        color: rgba(148, 163, 184, 0.85);
        text-align: center;
        padding: 2.5rem 0;
    }

    .admin-games-card {
        gap: 1.25rem;
    }

    .selected-overview {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        justify-content: space-between;
        gap: 1.25rem;
    }

    .selected-overview .player {
        min-width: 0;
    }

    .selected-meta {
        margin-top: 0.35rem;
        color: rgba(226, 232, 240, 0.75);
        font-size: 0.85rem;
    }

    .selected-stats {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 0.85rem;
    }

    .selected-stats dt {
        margin: 0;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: rgba(148, 163, 184, 0.75);
    }

    .selected-stats dd {
        margin: 0.25rem 0 0;
        font-weight: 600;
        color: #f8fafc;
    }

    .admin-table col.col-status,
    .admin-table col.col-result,
    .admin-table col.col-moves,
    .admin-table col.col-action {
        width: 120px;
    }

    .admin-table col.col-timestamp {
        width: 160px;
    }

    .games-table .opponent-cell {
        display: flex;
        align-items: center;
        gap: 0.65rem;
    }

    .games-table .opponent-cell img {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        flex-shrink: 0;
        border: 1px solid rgba(148, 163, 184, 0.25);
    }

    .games-table .muted {
        display: block;
        font-size: 0.8rem;
        color: rgba(148, 163, 184, 0.75);
    }

    .games-table .action-cell {
        text-align: right;
    }

    @media (max-width: 768px) {
        .admin {
            padding-inline: 1.25rem;
        }

        .admin-card {
            padding: 1.5rem;
        }

        .admin-table thead th,
        .admin-table tbody td,
        .admin-table tbody th {
            padding: 0.65rem 0.75rem;
        }
    }
</style>
