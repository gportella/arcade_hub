<script>
  import { t } from "../i18n";

  export let coolId = "";
  export let difficulty = "easy";
  export let currentPoints = 0;
  export let maxPoints = 3;
  export let totalPoints = 0;
  export let timesPresented = 0;
  export let timesSolved = 0;
  export let hintCount = 0;
  export let status = "active"; // active | solved | failed

  const statusKey = {
    active: "puzzles.status.active",
    solved: "puzzles.status.solved",
    failed: "puzzles.status.failed",
  };

  const clampPercent = (value) => {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return 0;
    return Math.min(100, Math.max(0, numeric));
  };

  const formatPercentLabel = (value) => {
    if (!Number.isFinite(value)) return "0";
    return value % 1 === 0 ? String(value) : value.toFixed(1);
  };

  $: translate = $t;
  $: difficultyLabel = translate(`puzzles.difficulty.${difficulty}`);
  $: statusLabel = translate(statusKey[status] || statusKey.active);
  $: pointsPercent = maxPoints > 0 ? clampPercent((currentPoints / maxPoints) * 100) : 0;
  $: solvesPercent = timesPresented > 0 ? clampPercent((timesSolved / timesPresented) * 100) : 0;
  $: solvesPercentLabel = formatPercentLabel(solvesPercent);
</script>

<section class="score-card" aria-labelledby="puzzle-score-heading">
  <header class="score-card__header">
    <div>
      <p class="score-card__badge">{translate("puzzles.card.id", { id: coolId })}</p>
      <h2 id="puzzle-score-heading">{translate("puzzles.card.title")}</h2>
    </div>
    <span class="score-card__difficulty">{difficultyLabel}</span>
  </header>

  <dl class="score-card__grid">
    <div>
      <dt>{translate("puzzles.points.currentLabel")}</dt>
      <dd>
        <strong>{currentPoints}</strong>
        <span>{translate("puzzles.points.of", { current: currentPoints, max: maxPoints })}</span>
      </dd>
      <div class="meter" role="meter" aria-valuemax={maxPoints} aria-valuemin="0" aria-valuenow={currentPoints}>
        <div class="meter__fill" style={`width: ${pointsPercent}%`}></div>
      </div>
    </div>

    <div>
      <dt>{translate("puzzles.points.totalLabel")}</dt>
      <dd><strong>{totalPoints}</strong></dd>
      <p class="score-card__status">{statusLabel}</p>
    </div>

    <div>
      <dt>{translate("puzzles.card.presented")}</dt>
      <dd><strong>{timesPresented}</strong></dd>
      <div class="meter" role="meter" aria-valuemax={timesPresented || 1} aria-valuemin="0" aria-valuenow={timesSolved}>
        <div class="meter__fill meter__fill--accent" style={`width: ${solvesPercent}%`}></div>
      </div>
      <span class="meter__label">{translate("puzzles.card.solvedRate", { value: solvesPercentLabel })}</span>
    </div>

    <div>
      <dt>{translate("puzzles.card.hints")}</dt>
      <dd><strong>{hintCount}</strong></dd>
      <span class="hint-text">{translate("puzzles.card.hintNote")}</span>
    </div>
  </dl>
</section>

<style>
  .score-card {
    background: rgba(15, 23, 42, 0.55);
    border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 18px;
    padding: 1.5rem;
    color: #f8fafc;
    display: flex;
    flex-direction: column;
    gap: 1.2rem;
  }

  .score-card__header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
  }

  .score-card__badge {
    margin: 0;
    font-size: 0.85rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: rgba(148, 163, 184, 0.85);
  }

  .score-card__difficulty {
    align-self: center;
    padding: 0.4rem 0.75rem;
    border-radius: 999px;
    background: linear-gradient(120deg, #22d3ee, #6366f1);
    font-size: 0.75rem;
    font-weight: 600;
  }

  .score-card__grid {
    display: grid;
    gap: 1.25rem;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    margin: 0;
  }

  dt {
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: rgba(148, 163, 184, 0.7);
    margin-bottom: 0.3rem;
  }

  dd {
    margin: 0;
    font-size: 1.6rem;
    font-weight: 700;
  }

  .meter {
    height: 6px;
    border-radius: 999px;
    background: rgba(15, 23, 42, 0.85);
    margin-top: 0.4rem;
    overflow: hidden;
    position: relative;
  }

  .meter__fill {
    position: absolute;
    top: 0;
    left: 0;
    bottom: 0;
    width: 40%;
    background: linear-gradient(120deg, #22d3ee, #38bdf8);
    transition: width 160ms ease;
  }

  .meter__fill--accent {
    background: linear-gradient(120deg, #f59e0b, #ef4444);
  }

  .meter__label {
    display: block;
    margin-top: 0.35rem;
    font-size: 0.75rem;
    color: rgba(148, 163, 184, 0.8);
  }

  .score-card__status {
    margin: 0.5rem 0 0;
    font-size: 0.9rem;
    color: rgba(148, 163, 184, 0.85);
  }

  .hint-text {
    font-size: 0.75rem;
    color: rgba(148, 163, 184, 0.75);
  }

  @media (max-width: 880px) {
    .score-card {
      padding: 1.25rem;
    }
  }

  @media (max-width: 680px) {
    .score-card {
      padding: 1rem;
      gap: 0.9rem;
    }

    .score-card__grid {
      gap: 0.85rem;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    }

    dd {
      font-size: 1.4rem;
    }

    .score-card__difficulty {
      font-size: 0.7rem;
      padding: 0.35rem 0.65rem;
    }
  }
</style>
