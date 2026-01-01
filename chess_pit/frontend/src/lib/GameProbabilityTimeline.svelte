<script>
  import { createEventDispatcher } from "svelte";

  export let steps = [];
  export let currentIndex = 0;
  export let labels = {
    timeline: "",
    heading: "",
    aria: "",
    white: "",
    draw: "",
    black: "",
  };

  const chartWidth = 100;
  const chartHeight = 16;
  const markerRadius = 1.1;

  const dispatch = createEventDispatcher();
  let svgRef;
  let pointerActive = false;

  const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

  const normaliseShare = (value) => {
    if (!Number.isFinite(value) || value <= 0) {
      return 0;
    }
    return clamp(value, 0, 1);
  };

  const formatPercent = (value) => {
    if (!Number.isFinite(value)) {
      return "0";
    }
    const rounded = Math.round(value * 10) / 10;
    return Number.isInteger(rounded) ? `${rounded}` : rounded.toFixed(1);
  };

  const prepareSteps = (input) => {
    if (!Array.isArray(input) || !input.length) {
      return [];
    }
    return input.map((step, index, list) => {
      const rawWhite = normaliseShare(step?.white ?? 0);
      const rawDraw = normaliseShare(step?.draw ?? 0);
      const rawBlack = normaliseShare(step?.black ?? 0);
      const total = rawWhite + rawDraw + rawBlack;
      const scale = total > 0 ? 1 / total : 0;
      const white = clamp(rawWhite * scale, 0, 1);
      const draw = clamp(rawDraw * scale, 0, 1);
      const black = clamp(rawBlack * scale, 0, 1);
      const cumulativeWhite = white * chartHeight;
      const cumulativeDraw = (white + draw) * chartHeight;
      const cumulativeBlack = (white + draw + black) * chartHeight;
      const denominator = Math.max(list.length - 1, 1);
      const ratio = list.length === 1 ? 0 : index / denominator;
      const x = ratio * chartWidth;
      return {
        x,
        ratio,
        white,
        draw,
        black,
        whiteBottom: clamp(cumulativeWhite, 0, chartHeight),
        drawBottom: clamp(cumulativeDraw, 0, chartHeight),
        blackBottom: clamp(cumulativeBlack, 0, chartHeight),
        label: step?.label ?? step?.title ?? "",
        ply: step?.ply ?? index + 1,
        whitePercent: Number.isFinite(step?.whitePercent)
          ? step.whitePercent
          : white * 100,
        drawPercent: Number.isFinite(step?.drawPercent)
          ? step.drawPercent
          : draw * 100,
        blackPercent: Number.isFinite(step?.blackPercent)
          ? step.blackPercent
          : black * 100,
      };
    });
  };

  const buildAreaPath = (points, topAccessor, bottomAccessor) => {
    if (!points.length) {
      return "";
    }
    const topPoints = points.map((point) => [point.x, topAccessor(point)]);
    const bottomPoints = [];
    for (let i = points.length - 1; i >= 0; i -= 1) {
      bottomPoints.push([points[i].x, bottomAccessor(points[i])]);
    }
    const lastTop = topPoints[topPoints.length - 1];
    if (lastTop[0] !== chartWidth) {
      const anchor = points[points.length - 1];
      const extraTop = [chartWidth, topAccessor(anchor)];
      const extraBottom = [chartWidth, bottomAccessor(anchor)];
      topPoints.push(extraTop);
      bottomPoints.unshift(extraBottom);
    }
    if (topPoints[0][0] !== 0) {
      const anchor = points[0];
      const extraTop = [0, topAccessor(anchor)];
      const extraBottom = [0, bottomAccessor(anchor)];
      topPoints.unshift(extraTop);
      bottomPoints.push(extraBottom);
    }
    const commands = [];
    const start = topPoints[0];
    commands.push(`M ${start[0].toFixed(2)} ${start[1].toFixed(2)}`);
    for (let i = 1; i < topPoints.length; i += 1) {
      const [x, y] = topPoints[i];
      commands.push(`L ${x.toFixed(2)} ${y.toFixed(2)}`);
    }
    for (let i = 0; i < bottomPoints.length; i += 1) {
      const [x, y] = bottomPoints[i];
      commands.push(`L ${x.toFixed(2)} ${y.toFixed(2)}`);
    }
    commands.push("Z");
    return commands.join(" ");
  };

  const ratioToIndex = (ratio) => {
    if (!Number.isFinite(ratio)) {
      return null;
    }
    if (!prepared.length) {
      return null;
    }
    const segments = Math.max(prepared.length - 1, 1);
    const scaled = clamp(ratio, 0, 1) * segments;
    return Math.round(scaled);
  };

  const eventToIndex = (event) => {
    if (!svgRef || !prepared.length) {
      return null;
    }
    const rect = svgRef.getBoundingClientRect();
    if (!rect.width) {
      return null;
    }
    const ratio = (event.clientX - rect.left) / rect.width;
    return ratioToIndex(ratio);
  };

  const commitIndex = (index) => {
    if (index === null || !Number.isFinite(index)) {
      return;
    }
    const maxIndex = Math.max(prepared.length - 1, 0);
    const clampedIndex = clamp(Math.round(index), 0, maxIndex);
    dispatch("select", { index: clampedIndex });
  };

  const commitFromEvent = (event) => {
    const index = eventToIndex(event);
    if (index === null) {
      return;
    }
    commitIndex(index);
  };

  const handlePointerDown = (event) => {
    pointerActive = true;
    svgRef?.setPointerCapture?.(event.pointerId);
    commitFromEvent(event);
  };

  const handlePointerMove = (event) => {
    if (!pointerActive) {
      return;
    }
    event.preventDefault();
    commitFromEvent(event);
  };

  const handlePointerUp = (event) => {
    if (!pointerActive) {
      return;
    }
    pointerActive = false;
    svgRef?.releasePointerCapture?.(event.pointerId);
    commitFromEvent(event);
  };

  const handlePointerLeave = (event) => {
    if (!pointerActive) {
      return;
    }
    pointerActive = false;
    svgRef?.releasePointerCapture?.(event.pointerId);
  };

  const handleClick = (event) => {
    commitFromEvent(event);
  };

  $: prepared = prepareSteps(steps);
  $: clampedIndex = prepared.length
    ? clamp(Math.round(currentIndex), 0, prepared.length - 1)
    : null;
  $: markerPoint =
    clampedIndex === null ? null : prepared[clampedIndex] ?? null;
  $: whitePath = buildAreaPath(
    prepared,
    () => 0,
    (point) => point.whiteBottom,
  );
  $: drawPath = buildAreaPath(
    prepared,
    (point) => point.whiteBottom,
    (point) => point.drawBottom,
  );
  $: blackPath = buildAreaPath(
    prepared,
    (point) => point.drawBottom,
    (point) => point.blackBottom,
  );
  $: markerX = (() => {
    if (!markerPoint) {
      return null;
    }
    if (prepared.length === 1) {
      return chartWidth / 2;
    }
    return markerPoint.x;
  })();
  $: markerY = markerPoint ? markerRadius + 0.9 : null;
  $: markerLabel = markerPoint?.label
    ? markerPoint.label
    : labels.timeline || labels.heading;
  $: markerSummary = markerPoint
    ? `${labels.white || "White"}: ${formatPercent(markerPoint.whitePercent)}% · ${labels.draw || "Draw"}: ${formatPercent(markerPoint.drawPercent)}% · ${labels.black || "Black"}: ${formatPercent(markerPoint.blackPercent)}%`
    : "";
  $: ariaLabel = labels.aria
    ? labels.aria
    : markerSummary
    ? `${markerLabel} · ${markerSummary}`
    : markerLabel;
</script>

{#if prepared.length}
  <div class="probability-timeline">
    {#if labels.timeline || labels.heading}
      <p class="heading">{labels.timeline || labels.heading}</p>
    {/if}
    <svg
      class="chart"
      bind:this={svgRef}
      viewBox={`0 0 ${chartWidth} ${chartHeight}`}
      role="img"
      aria-label={ariaLabel}
      preserveAspectRatio="xMidYMid meet"
      on:pointerdown={handlePointerDown}
      on:pointermove={handlePointerMove}
      on:pointerup={handlePointerUp}
      on:pointerleave={handlePointerLeave}
      on:pointercancel={handlePointerLeave}
      on:click={handleClick}
    >
      {#if whitePath}
        <path class="area white" d={whitePath} />
      {/if}
      {#if drawPath}
        <path class="area draw" d={drawPath} />
      {/if}
      {#if blackPath}
        <path class="area black" d={blackPath} />
      {/if}
      {#if markerPoint && markerX !== null && markerY !== null}
        <g class="marker" transform={`translate(${markerX} 0)`}>
          <line class="marker-line" x1="0" y1="0" x2="0" y2={chartHeight} />
          <circle class="marker-dot" cy={markerY} r={markerRadius} />
        </g>
      {/if}
    </svg>
    <div class="marker-label" aria-hidden="true">
      <span class="label">{markerLabel}</span>
      {#if markerPoint}
        <span class="values">{markerSummary}</span>
      {/if}
    </div>
  </div>
{:else}
  <div class="probability-timeline empty">
    {#if labels.timeline || labels.heading}
      <p class="heading">{labels.timeline || labels.heading}</p>
    {/if}
    <p class="placeholder">{labels.timeline || labels.heading}</p>
  </div>
{/if}

<style>
  .probability-timeline {
    display: grid;
    gap: 0.22rem;
  }

  .probability-timeline.empty .placeholder {
    margin: 0;
    font-size: 0.68rem;
    color: rgba(148, 163, 184, 0.55);
  }

  .heading {
    margin: 0;
    font-size: 0.6rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: rgba(148, 163, 184, 0.78);
  }

  .chart {
    width: 100%;
    aspect-ratio: 100 / 16;
    background: rgba(15, 23, 42, 0.42);
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid rgba(148, 163, 184, 0.1);
    cursor: pointer;
    touch-action: none;
  }

  .area {
    fill-opacity: 0.4;
    stroke: none;
    transition: fill-opacity 0.2s ease;
  }

  .area.white {
    fill: rgba(148, 163, 184, 0.45);
  }

  .area.draw {
    fill: rgba(94, 234, 212, 0.45);
  }

  .area.black {
    fill: rgba(59, 130, 246, 0.55);
  }

  .marker {
    pointer-events: none;
  }

  .marker-line {
    stroke: rgba(148, 163, 184, 0.32);
    stroke-width: 0.4;
  }

  .marker-dot {
    fill: rgba(248, 113, 113, 0.92);
    stroke: rgba(248, 113, 113, 0.6);
    stroke-width: 0.5;
  }

  .marker-label {
    display: flex;
    flex-wrap: wrap;
    gap: 0.22rem;
    font-size: 0.64rem;
    color: rgba(203, 213, 225, 0.75);
  }

  .marker-label .label {
    font-weight: 600;
    letter-spacing: 0.02em;
    text-transform: uppercase;
  }

  .marker-label .values {
    opacity: 0.9;
  }
</style>
