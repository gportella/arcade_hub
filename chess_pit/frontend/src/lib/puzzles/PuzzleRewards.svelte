<script>
  export let celebrating = false;
  export let currentPoints = 0;
  export let timesSolved = 0;

  // Highest matching entry wins so arrays remain sorted desc by minimum.
  const COIN_TABLE = [
    { minimum: 3, src: "/assets/coinGold.png", alt: "Gold coin" },
    { minimum: 2, src: "/assets/coinSilver.png", alt: "Silver coin" },
    { minimum: 1, src: "/assets/coinBronze.png", alt: "Bronze coin" },
  ];

  const TROPHY_TABLE = [
    { minimum: 50, src: "/assets/trophy_03_gold.png", alt: "Gold trophy" },
    { minimum: 25, src: "/assets/trophy_03_silver.png", alt: "Silver trophy" },
    { minimum: 10, src: "/assets/trophy_03_bronze.png", alt: "Bronze trophy" },
    { minimum: 1, src: "/assets/trophy_01.png", alt: "Starter trophy" },
  ];

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
  $: hasReward = Boolean(coinReward || trophyReward);
</script>

{#if hasReward}
  <section class="rewards" data-active={celebrating} aria-live="polite">
    {#if trophyReward}
      <figure class="reward">
        <img src={trophyReward.src} alt={trophyReward.alt} />
        <figcaption>{trophyReward.alt}</figcaption>
      </figure>
    {/if}
    {#if coinReward}
      <figure class="reward reward--coin">
        <img src={coinReward.src} alt={coinReward.alt} />
        <figcaption>{coinReward.alt}</figcaption>
      </figure>
    {/if}
  </section>
{/if}

<style>
  .rewards {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1.25rem;
    padding: 0.75rem 1rem;
    border-radius: 18px;
    background: rgba(15, 23, 42, 0.65);
    border: 1px solid rgba(148, 163, 184, 0.35);
    box-shadow: 0 12px 20px rgba(15, 23, 42, 0.35);
    transition: transform 180ms ease, box-shadow 180ms ease;
  }

  .rewards[data-active="true"] {
    transform: translateY(-4px) scale(1.03);
    box-shadow: 0 18px 28px rgba(250, 204, 21, 0.25);
  }

  .reward {
    display: grid;
    justify-items: center;
    gap: 0.35rem;
    font-family: "Press Start 2P", "IBM Plex Mono", monospace;
    font-size: 0.55rem;
    color: #f1f5f9;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }

  .reward img {
    width: 64px;
    height: 64px;
    image-rendering: pixelated;
    filter: drop-shadow(0 6px 0 rgba(15, 23, 42, 0.6));
    animation: bob 1400ms ease-in-out infinite;
  }

  .rewards[data-active="false"] .reward img {
    animation: none;
    opacity: 0.82;
  }

  .reward--coin img {
    width: 48px;
    height: 48px;
  }

  .reward figcaption {
    min-width: 72px;
    text-align: center;
    background: rgba(30, 41, 59, 0.75);
    padding: 0.3rem 0.4rem;
    border-radius: 6px;
  }

  @keyframes bob {
    0%,
    100% {
      transform: translateY(0);
    }
    50% {
      transform: translateY(-6px);
    }
  }

  @media (max-width: 760px) {
    .rewards {
      gap: 0.75rem;
      padding: 0.6rem 0.8rem;
    }

    .reward img {
      width: 52px;
      height: 52px;
    }

    .reward--coin img {
      width: 40px;
      height: 40px;
    }

    .reward figcaption {
      font-size: 0.5rem;
      min-width: auto;
    }
  }
</style>
