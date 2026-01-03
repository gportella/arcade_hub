<script>
    import TrophyDisplay from "./TrophyDisplay.svelte";

    /** @typedef {{
     *   id: string | number,
     *   rank: number,
     *   username: string,
     *   avatar: string,
     *   ratingText: string,
     *   recordText: string,
     *   winRateText: string,
     *   puzzlesText: string,
     *   activityText: string,
     *   trophyWins: number,
     *   trophySummary: string,
     *   hasTrophies: boolean,
     *   highlight: boolean
     * }} LeaderboardRow */

    /** @type {string} */
    export let heading = "";
    /** @type {string} */
    export let subtitle = "";
    /** @type {string} */
    export let rankLabel = "";
    /** @type {string} */
    export let playerLabel = "";
    /** @type {string} */
    export let ratingLabel = "";
    /** @type {string} */
    export let recordLabel = "";
    /** @type {string} */
    export let winRateLabel = "";
    /** @type {string} */
    export let puzzlesLabel = "";
    /** @type {string} */
    export let lastActiveLabel = "";
    /** @type {string} */
    export let trophyLabel = "";
    /** @type {string} */
    export let trophyEmptyLabel = "";
    /** @type {Array<LeaderboardRow>} */
    export let rows = [];
    /** @type {boolean} */
    export let isLoading = false;
    /** @type {string} */
    export let emptyLabel = "";
    /** @type {string} */
    export let loadingLabel = "";
    /** @type {string} */
    export let footnote = "";

    $: showTrophyColumn = Boolean(trophyLabel);
</script>

<section class="hub-leaderboard glass-panel">
    <div class="leaderboard-header">
        <div>
            <h2>{heading}</h2>
            <p>{subtitle}</p>
        </div>
    </div>
    {#if rows.length}
        <div class="leaderboard-table-wrapper">
            <table>
                <colgroup>
                    <col class="col-rank" />
                    <col class="col-player" />
                    <col class="col-rating" />
                    {#if showTrophyColumn}
                        <col class="col-trophies" />
                    {/if}
                    <col class="col-record" />
                    <col class="col-win" />
                    <col class="col-puzzles" />
                    <col class="col-last" />
                </colgroup>
                <thead>
                    <tr>
                        <th scope="col" class="numeric">{rankLabel}</th>
                        <th scope="col">{playerLabel}</th>
                        <th scope="col" class="numeric">{ratingLabel}</th>
                        {#if showTrophyColumn}
                            <th scope="col" class="trophies-header">{trophyLabel}</th>
                        {/if}
                        <th scope="col" class="numeric">{recordLabel}</th>
                        <th scope="col" class="numeric">{winRateLabel}</th>
                        <th scope="col" class="numeric">{puzzlesLabel}</th>
                        <th scope="col">{lastActiveLabel}</th>
                    </tr>
                </thead>
                <tbody>
                    {#each rows as entry (entry.id)}
                        <tr class:highlight={entry.highlight}>
                            <td class="numeric">{entry.rank}</td>
                            <th scope="row">
                                <div class="leaderboard-player">
                                    <img src={entry.avatar} alt={entry.username} loading="lazy" />
                                    <strong>{entry.username}</strong>
                                </div>
                            </th>
                            <td class="numeric">{entry.ratingText}</td>
                            {#if showTrophyColumn}
                                <td class="trophies-cell">
                                    {#if entry.hasTrophies}
                                        <TrophyDisplay
                                            wins={entry.trophyWins}
                                            summary={entry.trophySummary}
                                            title={trophyLabel}
                                            emptyLabel={trophyEmptyLabel}
                                            size={16}
                                            className="trophies-inline"
                                        />
                                    {:else}
                                        <span class="trophies-placeholder" aria-label={entry.trophySummary || trophyEmptyLabel}>—</span>
                                    {/if}
                                </td>
                            {/if}
                            <td class="numeric">{entry.recordText}</td>
                            <td class="numeric">{entry.winRateText}</td>
                            <td class="numeric">{entry.puzzlesText}</td>
                            <td>{entry.activityText}</td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>
        {#if footnote}
            <p class="leaderboard-footnote">{footnote}</p>
        {/if}
    {:else if isLoading}
        <p class="leaderboard-footnote subtle">{loadingLabel}</p>
    {:else}
        <p class="leaderboard-footnote subtle">{emptyLabel}</p>
    {/if}
</section>

<style>
    .hub-leaderboard {
        display: grid;
        gap: 0.9rem;
        padding: 1.2rem 1.35rem;
    }

    .leaderboard-header h2 {
        margin: 0;
        font-size: 1.1rem;
        color: #f8fafc;
    }

    .leaderboard-header p {
        margin: 0.35rem 0 0;
        color: rgba(226, 232, 240, 0.72);
        font-size: 0.9rem;
    }

    .leaderboard-table-wrapper {
        overflow-x: auto;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        min-width: 520px;
    }

    th,
    td {
        padding: 0.5rem 0.7rem;
        border-bottom: 1px solid rgba(148, 163, 184, 0.18);
        color: rgba(226, 232, 240, 0.88);
        font-size: 0.92rem;
        white-space: nowrap;
    }

    thead th {
        text-transform: uppercase;
        font-size: 0.7rem;
        letter-spacing: 0.06em;
        color: rgba(148, 163, 184, 0.78);
        background: rgba(15, 23, 42, 0.55);
    }

    tbody tr:last-child th,
    tbody tr:last-child td {
        border-bottom: none;
    }

    .numeric {
        text-align: right;
        font-size: 0.95rem;
        font-variant-numeric: tabular-nums;
        letter-spacing: 0.01em;
    }

    .leaderboard-player {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
    }

    .leaderboard-player img {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        object-fit: cover;
        border: 1px solid rgba(148, 163, 184, 0.25);
        flex-shrink: 0;
        background: rgba(148, 163, 184, 0.16);
    }

    .trophies-header {
        text-align: center;
    }

    .trophies-cell {
        text-align: center;
    }

    .trophies-placeholder {
        display: inline-block;
        color: rgba(148, 163, 184, 0.65);
    }

    :global(.trophies-inline) {
        --cup-size: 16px;
    }

    .col-trophies {
        width: 7.5rem;
    }

    .leaderboard-footnote {
        margin: 0;
        font-size: 0.82rem;
        color: rgba(226, 232, 240, 0.75);
    }

    .leaderboard-footnote.subtle {
        color: rgba(148, 163, 184, 0.7);
    }

    tr.highlight {
        background: rgba(59, 130, 246, 0.12);
    }

    .col-rank {
        width: 3.5rem;
    }

    .col-player {
        width: 14rem;
    }

    .col-rating,
    .col-record,
    .col-win,
    .col-puzzles {
        width: 6.2rem;
    }

    .col-last {
        width: 9rem;
    }

    @media (max-width: 640px) {
        .hub-leaderboard {
            padding: 1rem;
        }

        table {
            min-width: 480px;
        }

        th,
        td {
            padding: 0.45rem 0.55rem;
        }

        .leaderboard-player {
            gap: 0.45rem;
        }

        .leaderboard-player img {
            width: 22px;
            height: 22px;
        }
    }
</style>
