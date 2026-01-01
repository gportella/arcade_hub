<script>
  import GameProbabilityBar from "./GameProbabilityBar.svelte";
  import GameProbabilityTimeline from "./GameProbabilityTimeline.svelte";
  export let entry = null;
  export let index = 0;
  export let total = 0;
  export let labels = {
    heading: "",
    played: "",
    evalBefore: "",
    evalAfter: "",
    delta: "",
    best: "",
    variation: "",
    prev: "",
    next: "",
    close: "",
    counter: "",
    sliderAria: "",
    empty: "",
  };
  export let probabilityLabels = {
    heading: "",
    white: "",
    draw: "",
    black: "",
    timeline: "",
    aria: "",
  };
  export let probabilities = null;
  export let probabilityPercents = null;
  export let probabilityTimeline = [];
  export let onPrev = () => {};
  export let onNext = () => {};
  export let onSeek = () => {};
  export let onClose = () => {};

  const hasSteps = () => total > 0;

  function handleRangeInput(event) {
    if (!hasSteps()) return;
    const value = Number(event.currentTarget?.value ?? 0);
    if (Number.isFinite(value)) {
      onSeek(value);
    }
  }

  function handleTimelineSelect(event) {
    const targetIndex = event?.detail?.index;
    if (typeof targetIndex !== "number" || Number.isNaN(targetIndex)) {
      return;
    }
    onSeek(targetIndex);
  }

  $: probabilityTimelineLabels = {
    timeline: probabilityLabels.timeline || probabilityLabels.heading,
    heading: probabilityLabels.heading,
    aria: probabilityLabels.aria,
    white: probabilityLabels.white,
    draw: probabilityLabels.draw,
    black: probabilityLabels.black,
  };
</script>

<div class="analysis-viewer">
  <div class="viewer-top">
    <div class="titles">
      {#if labels.heading}
        <p class="heading">{labels.heading}</p>
      {/if}
      {#if entry?.title}
        <h3>{entry.title}</h3>
      {/if}
    </div>
    <button type="button" class="ghost" on:click={onClose}>
      {labels.close}
    </button>
  </div>

  <div class="viewer-nav">
    <button type="button" on:click={onPrev} disabled={index <= 0}>
      {labels.prev}
    </button>
    <div class="viewer-progress">
      <input
        type="range"
        min="0"
        max={Math.max(total - 1, 0)}
        value={Math.min(Math.max(index, 0), Math.max(total - 1, 0))}
        disabled={!hasSteps() || total <= 1}
        aria-label={labels.sliderAria}
        on:input={handleRangeInput}
      />
      {#if labels.counter}
        <span>{labels.counter}</span>
      {/if}
    </div>
    <button
      type="button"
      on:click={onNext}
      disabled={!hasSteps() || index >= total - 1}
    >
      {labels.next}
    </button>
  </div>

  {#if entry}
    <dl class="viewer-grid" class:match={entry.isBestMatch} class:missed={!entry.isBestMatch && entry.hasBest}>
      <div>
        <dt>{labels.played}</dt>
        <dd>
          <span class="played-move">{entry.played}</span>
          {#if entry.annotation}
            <span
              class="annotation"
              aria-label={entry.annotationLabel || entry.annotation}
              title={entry.annotationLabel || entry.annotation}
            >
              {entry.annotation}
            </span>
          {/if}
          {#if entry.annotationLabel}
            <span class="annotation-text">{entry.annotationLabel}</span>
          {/if}
        </dd>
      </div>
      <div>
        <dt>{labels.evalBefore}</dt>
        <dd>{entry.evalBefore}</dd>
      </div>
      <div>
        <dt>{labels.evalAfter}</dt>
        <dd>{entry.evalAfter}</dd>
      </div>
      <div>
        <dt>{labels.delta}</dt>
        <dd>{entry.delta}</dd>
      </div>
      <div>
        <dt>{labels.best}</dt>
        <dd>{entry.best}</dd>
      </div>
      <div class="variation">
        <dt>{labels.variation}</dt>
        <dd>{entry.variation}</dd>
      </div>
    </dl>
    {#if probabilityTimeline?.length}
      <GameProbabilityTimeline
        steps={probabilityTimeline}
        currentIndex={index}
        labels={probabilityTimelineLabels}
        on:select={handleTimelineSelect}
      />
    {/if}
    {#if probabilities}
      <GameProbabilityBar
        values={probabilities}
        percents={probabilityPercents}
        labels={probabilityLabels}
      />
    {/if}
  {:else}
    <p class="placeholder">{labels.empty}</p>
  {/if}
</div>

<style>
  .analysis-viewer {
    display: grid;
    gap: 0.75rem;
    padding: 0.75rem;
    border-radius: 14px;
    background: rgba(9, 16, 33, 0.4);
    border: 1px solid rgba(148, 163, 184, 0.18);
    min-height: 300px;
  }

  .viewer-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.75rem;
  }

  .viewer-top .heading {
    margin: 0;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 0.72rem;
    color: rgba(148, 163, 184, 0.75);
  }

  .viewer-top h3 {
    margin: 0.15rem 0 0;
    font-size: 1.05rem;
    color: #f8fafc;
  }

  .ghost {
    border: none;
    background: transparent;
    color: rgba(148, 163, 184, 0.92);
    font-size: 0.85rem;
    cursor: pointer;
  }

  .ghost:hover {
    color: #e2e8f0;
  }

  .viewer-nav {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-wrap: wrap;
  }

  .viewer-nav button {
    border: none;
    padding: 0.4rem 0.8rem;
    border-radius: 999px;
    background: rgba(59, 130, 246, 0.18);
    color: #cbd5f5;
    font-weight: 600;
    cursor: pointer;
  }

  .viewer-nav button:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .viewer-nav button:not(:disabled):hover {
    background: rgba(59, 130, 246, 0.35);
  }

  .viewer-progress {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    flex: 1;
    min-width: 180px;
  }

  .viewer-progress input[type="range"] {
    flex: 1;
  }

  .viewer-progress span {
    font-size: 0.82rem;
    color: rgba(203, 213, 225, 0.85);
  }

  .viewer-grid {
    display: grid;
    gap: 0.6rem 1rem;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  }

  .viewer-grid.match {
    border-left: 3px solid rgba(34, 197, 94, 0.6);
    padding-left: 0.6rem;
  }

  .viewer-grid.missed {
    border-left: 3px solid rgba(239, 68, 68, 0.6);
    padding-left: 0.6rem;
  }

  .viewer-grid dt {
    text-transform: uppercase;
    letter-spacing: 0.04em;
    font-size: 0.72rem;
    color: rgba(148, 163, 184, 0.68);
  }

  .viewer-grid dd {
    margin: 0;
    font-size: 0.95rem;
    color: rgba(226, 232, 240, 0.92);
    font-family: "JetBrains Mono", "Fira Code", monospace;
    word-break: break-word;
  }

  .played-move {
    margin-right: 0.4rem;
  }

  .annotation {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.15rem 0.4rem;
    border-radius: 999px;
    margin-right: 0.35rem;
    font-family: "JetBrains Mono", "Fira Code", monospace;
    font-size: 0.82rem;
    background: rgba(59, 130, 246, 0.2);
    color: #bfdbfe;
  }

  .annotation-text {
    display: block;
    margin-top: 0.3rem;
    font-size: 0.78rem;
    font-family: inherit;
    color: rgba(148, 163, 184, 0.78);
  }

  .variation {
    grid-column: 1 / -1;
  }

  .variation dd {
    height: 5.8rem;
    overflow-y: auto;
    padding-right: 0.35rem;
    line-height: 1.4;
  }

  .variation dd::-webkit-scrollbar {
    width: 5px;
  }

  .variation dd::-webkit-scrollbar-thumb {
    background: rgba(148, 163, 184, 0.35);
    border-radius: 999px;
  }

  .placeholder {
    margin: 0;
    font-size: 0.9rem;
    color: rgba(148, 163, 184, 0.8);
  }
</style>
