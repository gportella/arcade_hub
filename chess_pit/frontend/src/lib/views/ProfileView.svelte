<script>
    import { t } from "../i18n";
    import TrophyDisplay from "../components/TrophyDisplay.svelte";
    import { calculateTrophies } from "../utils/trophies";
    /**
     * @type {{ username: string; avatar_url?: string | null; games_won: number; games_lost: number; games_drawn: number } | null}
     */
    export let user = null;
    /** @type {{ avatarUrl: string; password: string }} */
    export let profileDraft = { avatarUrl: "", password: "" };
    export let gameCount = 0;
    export let onFieldChange = (_field, _value) => {};
    export let onSave = () => {};
    export let onBack = () => {};
    export let onLogout = () => {};
    export let leaderboard = [];
    export let isLeaderboardLoading = false;

    const handleInput = (field, value) => {
        onFieldChange(field, value);
    };

    $: backLabel = $t("profile.back");
    $: logoutLabel = $t("profile.logout");
    $: updateHeading = $t("profile.update");
    $: avatarLabel = $t("profile.form.avatar");
    $: avatarPlaceholder = $t("profile.form.avatarPlaceholder");
    $: passwordLabel = $t("profile.form.password");
    $: passwordPlaceholder = $t("profile.form.passwordPlaceholder");
    $: saveLabel = $t("profile.form.save");
    $: placeholderText = $t("profile.placeholder");
    $: avatarAlt = $t("avatar.label", { name: user?.username ?? "" });
    $: gamesSuffix = gameCount === 1 ? "" : "s";
    $: gamesCountText = $t("profile.gamesCount", {
        count: gameCount,
        suffix: gamesSuffix,
    });
    $: winsLabel = $t("profile.stats.wins", { count: user?.games_won ?? 0 });
    $: lossesLabel = $t("profile.stats.losses", {
        count: user?.games_lost ?? 0,
    });
    $: drawsLabel = $t("profile.stats.draws", { count: user?.games_drawn ?? 0 });
    const ratingValue = (value) =>
        typeof value === "number" && Number.isFinite(value) ? Math.round(value) : null;
    $: ratingLabel = $t("profile.stats.rating", {
        value: ratingValue(user?.rating) ?? "—",
    });

    $: trophiesLabel = $t("profile.trophies.label");
    $: trophiesNoneLabel = $t("profile.trophies.none");
    $: userTrophyData = calculateTrophies(user?.games_won, 4);
    $: userHasTrophies = userTrophyData.cups.length > 0;
    $: userTrophySummary = userHasTrophies
        ? $t("profile.trophies.summary", {
              gold: userTrophyData.counts.gold,
              silver: userTrophyData.counts.silver,
              bronze: userTrophyData.counts.bronze,
              represented: userTrophyData.representedWins,
              wins: userTrophyData.sourceWins,
          })
        : trophiesNoneLabel;

    const safeNumber = (value) => (Number.isFinite(value) ? Number(value) : 0);

    const formatRecord = (entry) => {
        const wins = safeNumber(entry?.games_won);
        const losses = safeNumber(entry?.games_lost);
        const draws = safeNumber(entry?.games_drawn);
        return `${wins}-${losses}-${draws}`;
    };

    const formatWinRate = (entry) => {
        const wins = safeNumber(entry?.games_won);
        const games = safeNumber(entry?.games_played);
        if (!games) {
            return "—";
        }
        return `${Math.round((wins / games) * 100)}%`;
    };

    const formatPuzzleSummary = (entry) => {
        const solved = safeNumber(entry?.puzzles_solved);
        const attempted = safeNumber(entry?.puzzles_attempted);
        return attempted ? `${solved}/${attempted}` : `${solved}/0`;
    };

    $: leaderboardHeading = $t("profile.leaderboard.heading");
    $: leaderboardSubtitle = $t("profile.leaderboard.subtitle");
    $: leaderboardRankLabel = $t("profile.leaderboard.rank");
    $: leaderboardPlayerLabel = $t("profile.leaderboard.player");
    $: leaderboardRatingLabel = $t("profile.leaderboard.rating");
    $: leaderboardTrophiesLabel = $t("profile.leaderboard.trophies");
    $: leaderboardRecordLabel = $t("profile.leaderboard.record");
    $: leaderboardWinRateLabel = $t("profile.leaderboard.winRate");
    $: leaderboardPuzzlesLabel = $t("profile.leaderboard.puzzles");
    $: leaderboardEmptyLabel = $t("profile.leaderboard.empty");
    $: leaderboardLoadingLabel = $t("profile.leaderboard.loading");
    $: leaderboardNotRankedLabel = $t("profile.leaderboard.notRanked");
    $: leaderboardRankNote = (rank) =>
        $t("profile.leaderboard.yourRank", { rank });

    $: rankedEntries = Array.isArray(leaderboard)
        ? leaderboard.map((entry, index) => {
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
                  : trophiesNoneLabel;
              return {
                  ...entry,
                  rank: index + 1,
                  trophyData,
                  trophySummary,
                  hasTrophies,
              };
          })
        : [];
    $: userRankEntry = rankedEntries.find((entry) => String(entry.id) === String(user?.id)) ?? null;
    $: comparisonEntries = (() => {
        if (!rankedEntries.length) {
            return [];
        }
        if (!userRankEntry) {
            return rankedEntries.slice(0, 5);
        }
        const index = userRankEntry.rank - 1;
        const start = Math.max(0, index - 2);
        return rankedEntries.slice(start, start + 5);
    })();
</script>

<main class="profile">
    <header class="profile-header">
        <button class="secondary small" on:click={onBack}>{backLabel}</button>
        <div class="header-actions">
            <button class="secondary small" on:click={onLogout}>
                {logoutLabel}
            </button>
        </div>
    </header>

    {#if user}
        <section class="profile-card glass-panel">
            <div class="identity">
                <img
                    src={profileDraft.avatarUrl || user.avatar_url || ""}
                    alt={avatarAlt}
                />
                <div>
                    <h1>{user.username}</h1>
                    <p class="meta">{gamesCountText}</p>
                    <ul class="stats">
                        <li>{winsLabel}</li>
                        <li>{lossesLabel}</li>
                        <li>{drawsLabel}</li>
                        <li>{ratingLabel}</li>
                    </ul>
                    {#if userHasTrophies}
                        <div class="trophies-summary">
                            <span>{trophiesLabel}</span>
                            <TrophyDisplay
                                wins={userTrophyData.sourceWins}
                                summary={userTrophySummary}
                                title={trophiesLabel}
                                emptyLabel={trophiesNoneLabel}
                            />
                        </div>
                    {/if}
                </div>
            </div>
        </section>

        <section class="profile-leaderboard glass-panel">
            <div class="leaderboard-header">
                <h2>{leaderboardHeading}</h2>
                <p>{leaderboardSubtitle}</p>
            </div>
            {#if comparisonEntries.length}
                <div class="leaderboard-table-wrapper">
                    <table>
                        <colgroup>
                            <col class="col-rank" />
                            <col class="col-player" />
                            <col class="col-rating" />
                            <col class="col-trophies" />
                            <col class="col-record" />
                            <col class="col-win" />
                            <col class="col-puzzles" />
                        </colgroup>
                        <thead>
                            <tr>
                                <th scope="col" class="numeric">{leaderboardRankLabel}</th>
                                <th scope="col">{leaderboardPlayerLabel}</th>
                                <th scope="col" class="numeric">{leaderboardRatingLabel}</th>
                                <th scope="col" class="trophies-header">{leaderboardTrophiesLabel}</th>
                                <th scope="col" class="numeric">{leaderboardRecordLabel}</th>
                                <th scope="col" class="numeric">{leaderboardWinRateLabel}</th>
                                <th scope="col" class="numeric">{leaderboardPuzzlesLabel}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {#each comparisonEntries as entry}
                                <tr class:selected={String(entry.id) === String(user?.id)}>
                                    <td class="numeric">{entry.rank}</td>
                                    <th scope="row">{entry.username}</th>
                                    <td class="numeric">{ratingValue(entry.rating) ?? "—"}</td>
                                    <td class="trophies-cell">
                                        {#if entry.hasTrophies}
                                            <TrophyDisplay
                                                wins={entry.trophyData.sourceWins}
                                                summary={entry.trophySummary}
                                                title={trophiesLabel}
                                                emptyLabel={trophiesNoneLabel}
                                                size={16}
                                                className="trophies-inline"
                                            />
                                        {:else}
                                            <span class="trophies-placeholder" aria-label={entry.trophySummary}>—</span>
                                        {/if}
                                    </td>
                                    <td class="numeric">{formatRecord(entry)}</td>
                                    <td class="numeric">{formatWinRate(entry)}</td>
                                    <td class="numeric">{formatPuzzleSummary(entry)}</td>
                                </tr>
                            {/each}
                        </tbody>
                    </table>
                </div>
                {#if userRankEntry}
                    <p class="leaderboard-note">
                        {leaderboardRankNote(userRankEntry.rank)}
                    </p>
                {:else}
                    <p class="leaderboard-note subtle">{leaderboardNotRankedLabel}</p>
                {/if}
            {:else if isLeaderboardLoading}
                <p class="leaderboard-note subtle">{leaderboardLoadingLabel}</p>
            {:else}
                <p class="leaderboard-note subtle">{leaderboardEmptyLabel}</p>
            {/if}
        </section>

        <section class="profile-form glass-panel">
            <h2>{updateHeading}</h2>
            <form on:submit|preventDefault={onSave}>
                <label for="avatar">{avatarLabel}</label>
                <input
                    id="avatar"
                    name="avatar"
                    placeholder={avatarPlaceholder}
                    value={profileDraft.avatarUrl}
                    on:input={(event) =>
                        handleInput(
                            "avatarUrl",
                            /** @type {HTMLInputElement} */ (
                                event.currentTarget
                            ).value,
                        )}
                />

                <label for="password">{passwordLabel}</label>
                <input
                    id="password"
                    name="password"
                    type="password"
                    autocomplete="new-password"
                    placeholder={passwordPlaceholder}
                    value={profileDraft.password}
                    on:input={(event) =>
                        handleInput(
                            "password",
                            /** @type {HTMLInputElement} */ (
                                event.currentTarget
                            ).value,
                        )}
                />

                <div class="form-actions">
                    <button type="submit">{saveLabel}</button>
                </div>
            </form>
        </section>
    {:else}
        <p class="placeholder">{placeholderText}</p>
    {/if}
</main>

<style>
    .profile {
        width: min(640px, 100%);
        display: flex;
        flex-direction: column;
        gap: clamp(1.25rem, 4vw, 1.75rem);
        margin: 0 auto;
    }

    .profile-header {
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

    .profile-card {
        padding: clamp(1.5rem, 4vw, 2rem);
        display: flex;
        flex-direction: column;
        gap: 1.1rem;
    }

    .profile-leaderboard {
        padding: clamp(1.5rem, 4vw, 2rem);
        display: grid;
        gap: 1rem;
    }

    .leaderboard-header h2 {
        margin: 0;
        color: #f8fafc;
        font-size: 1.15rem;
    }

    .leaderboard-header p {
        margin: 0.35rem 0 0;
        color: rgba(226, 232, 240, 0.72);
        font-size: 0.9rem;
    }

    .leaderboard-table-wrapper {
        overflow-x: auto;
    }

    .profile-leaderboard table {
        width: 100%;
        border-collapse: collapse;
        min-width: 600px;
    }

    .profile-leaderboard th,
    .profile-leaderboard td {
        padding: 0.55rem 0.75rem;
        border-bottom: 1px solid rgba(148, 163, 184, 0.18);
        color: rgba(226, 232, 240, 0.85);
        font-size: 0.9rem;
        white-space: nowrap;
    }

    .profile-leaderboard thead th {
        text-transform: uppercase;
        font-size: 0.72rem;
        letter-spacing: 0.06em;
        color: rgba(148, 163, 184, 0.78);
        background: rgba(15, 23, 42, 0.55);
    }

    .profile-leaderboard tbody tr:last-child th,
    .profile-leaderboard tbody tr:last-child td {
        border-bottom: none;
    }

    .profile-leaderboard .numeric {
        text-align: right;
    }

    .profile-leaderboard .col-trophies {
        width: 120px;
    }

    .profile-leaderboard .trophies-header {
        text-align: center;
    }

    .profile-leaderboard .trophies-cell {
        text-align: center;
    }

    .profile-leaderboard .trophies-cell :global(.trophy-display) {
        justify-content: center;
    }

    .profile-leaderboard :global(.trophies-inline) {
        --cup-size: 16px;
    }

    .profile-leaderboard .trophies-placeholder {
        display: inline-block;
        color: rgba(148, 163, 184, 0.65);
    }

    .profile-leaderboard tr.selected {
        background: rgba(59, 130, 246, 0.14);
    }

    .leaderboard-note {
        margin: 0;
        color: rgba(226, 232, 240, 0.75);
        font-size: 0.85rem;
    }

    .leaderboard-note.subtle {
        color: rgba(148, 163, 184, 0.7);
    }

    .identity {
        display: flex;
        gap: 1rem;
        align-items: center;
    }

    .identity img {
        width: 72px;
        height: 72px;
        border-radius: 24px;
        object-fit: cover;
        border: 2px solid rgba(148, 163, 184, 0.35);
    }

    .identity h1 {
        margin: 0;
        font-size: clamp(1.6rem, 4vw, 1.9rem);
        color: #f8fafc;
    }

    .meta {
        margin: 0;
        color: rgba(226, 232, 240, 0.7);
    }

    .stats {
        margin: 0.4rem 0 0;
        padding-left: 1.1rem;
        color: rgba(226, 232, 240, 0.75);
        display: grid;
        gap: 0.2rem;
    }

    .trophies-summary {
        margin-top: 0.6rem;
        display: inline-flex;
        align-items: center;
        gap: 0.65rem;
        color: rgba(226, 232, 240, 0.85);
        font-size: 0.9rem;
    }

    .trophies-summary span {
        font-weight: 600;
        color: rgba(226, 232, 240, 0.78);
    }

    .profile-form {
        padding: clamp(1.5rem, 4vw, 2rem);
        display: flex;
        flex-direction: column;
        gap: 1.25rem;
    }

    .profile-form h2 {
        margin: 0;
        color: #f8fafc;
        font-size: 1.2rem;
    }

    form {
        display: flex;
        flex-direction: column;
        gap: 0.85rem;
    }

    .form-actions {
        display: flex;
        justify-content: flex-end;
    }

    @media (max-width: 640px) {
        .identity {
            align-items: flex-start;
        }

        .identity img {
            width: 64px;
            height: 64px;
        }

        .profile-card,
        .profile-form,
        .profile-leaderboard {
            padding: 1.25rem;
        }

        .profile-leaderboard table {
            min-width: 440px;
        }
    }
</style>
