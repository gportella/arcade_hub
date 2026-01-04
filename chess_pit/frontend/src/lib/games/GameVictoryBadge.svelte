<script>
  import { resolveAssetPath } from "../utils/assets";

  export let level = "";
  export let title = "";
  export let subtitle = "";
  export let celebrating = false;

  const TROPHY_SOURCES = {
    gold: resolveAssetPath("assets/trophy_03_gold.png"),
    silver: resolveAssetPath("assets/trophy_03_silver.png"),
    bronze: resolveAssetPath("assets/trophy_03_bronze.png"),
  };

  $: iconSource = TROPHY_SOURCES[level] || TROPHY_SOURCES.bronze;
  $: hasReward = Boolean(level && title);
</script>

{#if hasReward}
  <div
    class="info-card reward-card"
    data-level={level}
    data-celebrating={celebrating}
    aria-live="polite"
  >
    <div class="reward-media">
      <img src={iconSource} alt={title} />
    </div>
    <div class="reward-copy">
      <p class="reward-title">{title}</p>
      {#if subtitle}
        <p class="reward-subtitle">{subtitle}</p>
      {/if}
    </div>
  </div>
{/if}

<style>
  .reward-card {
    display: grid;
    grid-template-columns: auto 1fr;
    align-items: center;
    gap: 0.85rem;
    background: rgba(15, 23, 42, 0.7);
    border: 1px solid rgba(59, 130, 246, 0.35);
    box-shadow: 0 16px 28px rgba(15, 23, 42, 0.45);
    transition: transform 180ms ease, box-shadow 180ms ease;
  }

  .reward-card[data-celebrating="true"] {
    transform: translateY(-3px) scale(1.02);
    box-shadow: 0 20px 32px rgba(250, 204, 21, 0.28);
  }

  .reward-media {
    display: grid;
    place-items: center;
    background: rgba(30, 41, 59, 0.7);
    border-radius: 14px;
    padding: 0.65rem;
  }

  .reward-media img {
    width: 64px;
    height: 64px;
    image-rendering: pixelated;
    filter: drop-shadow(0 6px 0 rgba(15, 23, 42, 0.65));
    animation: bob 1400ms ease-in-out infinite;
  }

  .reward-card[data-celebrating="false"] .reward-media img {
    animation: none;
    opacity: 0.88;
  }

  .reward-copy {
    display: grid;
    gap: 0.4rem;
  }

  .reward-title {
    margin: 0;
    font-size: 0.95rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: #f8fafc;
  }

  .reward-subtitle {
    margin: 0;
    font-size: 0.82rem;
    color: rgba(226, 232, 240, 0.78);
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
    .reward-card {
      grid-template-columns: 1fr;
      justify-items: center;
      text-align: center;
    }

    .reward-media {
      width: 100%;
    }

    .reward-media img {
      width: 56px;
      height: 56px;
    }
  }
</style>
