<script>
  import { t } from "../i18n";
  import { resolveAssetPath } from "../utils/assets";

  export let celebrating = false;
  export let currentPoints = 0;
  export let maxPoints = 0;
  export let timesSolved = 0;

  const toAsset = (path) => resolveAssetPath(path);

  // Highest matching entry wins so arrays remain sorted desc by minimum.
  const COIN_TABLE = [
    { minimum: 3, src: toAsset("assets/coinGold.png"), alt: "Gold coin" },
    { minimum: 2, src: toAsset("assets/coinSilver.png"), alt: "Silver coin" },
    { minimum: 1, src: toAsset("assets/coinBronze.png"), alt: "Bronze coin" },
  ];

  const TROPHY_TABLE = [
    { minimum: 50, src: toAsset("assets/trophy_03_gold.png"), alt: "Gold trophy" },
    { minimum: 25, src: toAsset("assets/trophy_03_silver.png"), alt: "Silver trophy" },
    { minimum: 10, src: toAsset("assets/trophy_03_bronze.png"), alt: "Bronze trophy" },
    { minimum: 1, src: toAsset("assets/trophy_01.png"), alt: "Starter trophy" },
  ];

  const fallbackCoin = toAsset("assets/coinBronze.png");
  const fallbackTrophy = toAsset("assets/trophy_01.png");

  const pickReward = (table, value) => {
    for (const entry of table) {
      if (value >= entry.minimum) {
        return entry;
      }
    }
    return null;
  };

  $: coinReward = pickReward(COIN_TABLE, currentPoints);
  $: trophyReward = pickReward(TROPHY_TABLE, timesSolved);
  $: hasSummary = Boolean(maxPoints || timesSolved || coinReward || trophyReward);
  $: coinSentence = $t("puzzles.rewards.coinSentence", {
    current: currentPoints,
    max: maxPoints,
  });
  $: trophySentenceKey = timesSolved === 1
    ? "puzzles.rewards.trophySentenceSingle"
    : "puzzles.rewards.trophySentencePlural";
  $: trophySentence = $t(trophySentenceKey, { count: timesSolved });
</script>

{#if hasSummary}
  <section class="reward-strip" data-celebrating={celebrating} aria-live="polite">
    <div class="reward-strip__item" data-type="coins">
      <img
        class="reward-strip__icon"
        src={coinReward?.src ?? fallbackCoin}
        alt={coinReward?.alt ?? $t("puzzles.rewards.defaultCoin")}
      />
      <p class="reward-strip__text">{coinSentence}</p>
    </div>

    <div class="reward-strip__item" data-type="trophy">
      <img
        class="reward-strip__icon"
        src={trophyReward?.src ?? fallbackTrophy}
        alt={trophyReward?.alt ?? $t("puzzles.rewards.defaultTrophy")}
      />
      <p class="reward-strip__text">{trophySentence}</p>
    </div>
  </section>
{/if}

<style>
  .reward-strip {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 0.45rem;
    padding: 0.4rem 0.55rem;
    border-radius: 12px;
    background: rgba(15, 23, 42, 0.35);
    border: 1px solid rgba(148, 163, 184, 0.25);
    color: #e2e8f0;
    font-family: "Inter", "IBM Plex Sans", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    transition: transform 180ms ease, box-shadow 180ms ease;
  }

  .reward-strip[data-celebrating="true"] {
    transform: translateY(-1px) scale(1.003);
    box-shadow: 0 8px 16px rgba(250, 204, 21, 0.12);
  }

  .reward-strip__item {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.35rem;
    align-items: center;
  }

  .reward-strip__icon {
    width: 28px;
    height: 28px;
    border-radius: 8px;
    background: rgba(30, 41, 59, 0.55);
    padding: 3px;
    image-rendering: pixelated;
  }

  .reward-strip__item[data-type="coins"] .reward-strip__icon {
    box-shadow: 0 2px 6px rgba(250, 204, 21, 0.18);
  }

  .reward-strip__item[data-type="trophy"] .reward-strip__icon {
    box-shadow: 0 2px 6px rgba(96, 165, 250, 0.16);
  }

  .reward-strip__text {
    margin: 0;
    font-size: 0.72rem;
    line-height: 1.35;
    color: rgba(226, 232, 240, 0.9);
  }

  @media (max-width: 820px) {
    .reward-strip {
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 0.4rem;
    }

    .reward-strip__item {
      grid-template-columns: auto 1fr;
    }
  }

  @media (max-width: 520px) {
    .reward-strip {
      grid-template-columns: 1fr;
      padding: 0.35rem 0.5rem;
    }

    .reward-strip__icon {
      width: 26px;
      height: 26px;
    }
  }
</style>
