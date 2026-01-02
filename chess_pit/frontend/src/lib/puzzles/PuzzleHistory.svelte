<script>
  import { t } from "../i18n";

  export let history = [];

  const formatTime = (value, translate) => {
    if (!value) return translate("puzzles.history.justNow");
    const date = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(date.getTime())) {
      return translate("puzzles.history.justNow");
    }
    return new Intl.DateTimeFormat(undefined, {
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  };

  const formatHintUsage = (count, translate) => {
    if (!count) return "";
    if (count === 1) {
      return translate("puzzles.history.hintSingular");
    }
    return translate("puzzles.history.hintPlural", { count });
  };
</script>

<section class="history" aria-labelledby="puzzle-history-heading">
  <header class="history__header">
    <h3 id="puzzle-history-heading">{$t("puzzles.history.title")}</h3>
    <span class="history__badge">{history.length}</span>
  </header>

  {#if history.length === 0}
    <p class="history__empty">{$t("puzzles.history.empty")}</p>
  {:else}
    <ol class="history__list">
      {#each history as attempt (attempt.id)}
        <li class:history__item--success={attempt.solved} class:history__item--fail={!attempt.solved}
          class="history__item">
          <div>
            <p class="history__title">{attempt.coolId}</p>
            <p class="history__subtitle">
              {$t(`puzzles.difficulty.${attempt.difficulty}`)} · {formatTime(attempt.timestamp, $t)}
            </p>
          </div>
          <div class="history__result">
            <span class="history__points">+{attempt.points}</span>
            <span class="history__status">
              {attempt.solved
                ? $t("puzzles.status.shortSolved")
                : $t("puzzles.status.shortFailed")}
            </span>
            {#if attempt.hints > 0}
              <span class="history__hint">{formatHintUsage(attempt.hints, $t)}</span>
            {/if}
          </div>
        </li>
      {/each}
    </ol>
  {/if}
</section>

<style>
  .history {
    background: rgba(15, 23, 42, 0.45);
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 16px;
    padding: 1.25rem;
    color: #e2e8f0;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .history__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.75rem;
  }

  .history__badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 2.25rem;
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    background: rgba(59, 130, 246, 0.2);
    border: 1px solid rgba(56, 189, 248, 0.55);
    font-size: 0.85rem;
    font-weight: 600;
  }

  .history__empty {
    margin: 0;
    font-size: 0.95rem;
    color: rgba(148, 163, 184, 0.85);
  }

  .history__list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.9rem;
  }

  .history__item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.8rem;
    padding: 0.85rem 1rem;
    border-radius: 12px;
    background: rgba(15, 23, 42, 0.65);
    border: 1px solid rgba(148, 163, 184, 0.15);
    transition: transform 120ms ease, border 120ms ease;
  }

  .history__item--success {
    border-color: rgba(34, 197, 94, 0.45);
  }

  .history__item--fail {
    border-color: rgba(248, 113, 113, 0.35);
  }

  .history__title {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
  }

  .history__subtitle {
    margin: 0.2rem 0 0;
    font-size: 0.85rem;
    color: rgba(148, 163, 184, 0.8);
  }

  .history__result {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 0.25rem;
  }

  .history__points {
    font-size: 1.15rem;
    font-weight: 700;
  }

  .history__status {
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: rgba(148, 163, 184, 0.75);
  }

  .history__hint {
    font-size: 0.75rem;
    color: rgba(148, 163, 184, 0.7);
  }

  @media (max-width: 720px) {
    .history__item {
      flex-direction: column;
      align-items: flex-start;
    }

    .history__result {
      align-items: flex-start;
    }
  }
</style>
