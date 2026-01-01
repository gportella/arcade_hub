<script>
  export let values = { white: 0, draw: 0, black: 0 };
  export let percents = null;
  export let labels = {
    heading: "",
    white: "",
    draw: "",
    black: "",
  };

  const safePercents = percents
    ? {
        white: Number.isFinite(percents.white) ? percents.white : 0,
        draw: Number.isFinite(percents.draw) ? percents.draw : 0,
        black: Number.isFinite(percents.black) ? percents.black : 0,
      }
    : {
        white: Math.round((values.white ?? 0) * 100),
        draw: Math.round((values.draw ?? 0) * 100),
        black: Math.round((values.black ?? 0) * 100),
      };

  const formatPercent = (value) => {
    if (!Number.isFinite(value)) {
      return "0";
    }

    return Number.isInteger(value) ? `${value}` : value.toFixed(1);
  };

  const segments = [
    { key: "white", label: labels.white, percent: safePercents.white },
    { key: "draw", label: labels.draw, percent: safePercents.draw },
    { key: "black", label: labels.black, percent: safePercents.black },
  ];

  const ariaLabel = `${labels.white || "White"}: ${formatPercent(safePercents.white)}% · ${labels.draw || "Draw"}: ${formatPercent(safePercents.draw)}% · ${labels.black || "Black"}: ${formatPercent(safePercents.black)}%`;
</script>

<div class="probability">
  {#if labels.heading}
    <p class="heading">{labels.heading}</p>
  {/if}
  <div class="bar" role="img" aria-label={ariaLabel}>
    {#each segments as segment (segment.key)}
      <div
        class={`segment ${segment.key}`}
        style={`width: ${Math.max(0, Math.min(segment.percent, 100))}%`}
        aria-hidden="true"
      ></div>
    {/each}
  </div>
  <dl class="legend">
    {#each segments as segment (segment.key)}
      <div>
        <dt>{segment.label}</dt>
        <dd>{formatPercent(segment.percent)}%</dd>
      </div>
    {/each}
  </dl>
</div>

<style>
  .probability {
    display: grid;
    gap: 0.45rem;
  }

  .heading {
    margin: 0;
    font-size: 0.75rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: rgba(148, 163, 184, 0.78);
  }

  .bar {
    display: flex;
    width: 100%;
    height: 0.65rem;
    border-radius: 999px;
    overflow: hidden;
    background: rgba(15, 23, 42, 0.6);
    box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.16);
  }

  .segment {
    height: 100%;
    transition: width 0.2s ease;
  }

  .segment.white {
    background: linear-gradient(90deg, rgba(148, 163, 184, 0.4), rgba(148, 163, 184, 0.1));
  }

  .segment.draw {
    background: rgba(94, 234, 212, 0.45);
  }

  .segment.black {
    background: rgba(59, 130, 246, 0.55);
  }

  .legend {
    margin: 0;
    display: grid;
    gap: 0.35rem;
    grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
  }

  .legend div {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 0.35rem;
  }

  .legend dt {
    margin: 0;
    font-size: 0.78rem;
    color: rgba(148, 163, 184, 0.78);
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }

  .legend dd {
    margin: 0;
    font-size: 0.88rem;
    color: rgba(226, 232, 240, 0.94);
    font-family: "JetBrains Mono", "Fira Code", monospace;
  }
</style>
