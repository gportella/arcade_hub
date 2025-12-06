<script>
  import { createEventDispatcher, onDestroy, onMount } from "svelte";
  import Vehicle from "./Vehicle.svelte";

  export let size = 6;
  export let exit = undefined;
  export let vehicles = [];
  export let selectedId = null;
  export let highlightRow = null;
  export let allowCrossAxisDrag = false;
  export let conflictedIds = new Set();

  const dispatch = createEventDispatcher();

  let boardElement;
  let cellSize = 0;
  let dragState = null;
  let dragOffsets = new Map();
  let resizeObserver;
  let observedElement;

  $: exitPosition = exit ?? { row: 0, col: Math.max(size - 1, 0) };
  $: boardStyle = `--grid-size: ${size};`;

  const CROSS_AXIS_THRESHOLD = 12;

  const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

  function buildOccupancy(excludeId) {
    const occupied = new Set();
    for (const candidate of vehicles) {
      if (!candidate || candidate.id === excludeId) {
        continue;
      }
      const { row, col, length, orientation } = candidate;
      for (let offset = 0; offset < length; offset += 1) {
        const key =
          orientation === "horizontal"
            ? `${row}:${col + offset}`
            : `${row + offset}:${col}`;
        occupied.add(key);
      }
    }
    return occupied;
  }

  function computeAxisBounds(target, occupied) {
    if (!target) {
      return { horizontal: { min: 0, max: 0 }, vertical: { min: 0, max: 0 } };
    }

    const horizontal = { min: 0, max: 0 };
    const vertical = { min: 0, max: 0 };

    const width = target.orientation === "horizontal" ? target.length : 1;
    const height = target.orientation === "vertical" ? target.length : 1;

    // Horizontal forward (positive steps)
    for (let step = 1; ; step += 1) {
      const nextCol = target.col + width - 1 + step;
      if (nextCol >= size) {
        break;
      }
      let blocked = false;
      for (let rowOffset = 0; rowOffset < height; rowOffset += 1) {
        const key = `${target.row + rowOffset}:${nextCol}`;
        if (occupied.has(key)) {
          blocked = true;
          break;
        }
      }
      if (blocked) {
        break;
      }
      horizontal.max = step;
    }

    for (let step = 1; ; step += 1) {
      const nextCol = target.col - step;
      if (nextCol < 0) {
        break;
      }
      let blocked = false;
      for (let rowOffset = 0; rowOffset < height; rowOffset += 1) {
        const key = `${target.row + rowOffset}:${nextCol}`;
        if (occupied.has(key)) {
          blocked = true;
          break;
        }
      }
      if (blocked) {
        break;
      }
      horizontal.min = -step;
    }

    // Vertical forward (positive steps)
    for (let step = 1; ; step += 1) {
      const nextRow = target.row + height - 1 + step;
      if (nextRow >= size) {
        break;
      }
      let blocked = false;
      for (let colOffset = 0; colOffset < width; colOffset += 1) {
        const key = `${nextRow}:${target.col + colOffset}`;
        if (occupied.has(key)) {
          blocked = true;
          break;
        }
      }
      if (blocked) {
        break;
      }
      vertical.max = step;
    }

    for (let step = 1; ; step += 1) {
      const nextRow = target.row - step;
      if (nextRow < 0) {
        break;
      }
      let blocked = false;
      for (let colOffset = 0; colOffset < width; colOffset += 1) {
        const key = `${nextRow}:${target.col + colOffset}`;
        if (occupied.has(key)) {
          blocked = true;
          break;
        }
      }
      if (blocked) {
        break;
      }
      vertical.min = -step;
    }

    return { horizontal, vertical };
  }

  function updateCellSize() {
    if (!boardElement) {
      return;
    }
    const rect = boardElement.getBoundingClientRect();
    if (rect.width === 0) {
      return;
    }
    cellSize = rect.width / size;
  }

  function setDragOffset(id, value) {
    dragOffsets.set(id, value);
    dragOffsets = new Map(dragOffsets);
  }

  function handleBoardClick() {
    if (dragState) {
      return;
    }
    dispatch("clear");
  }

  function handleBoardKey(event) {
    if (dragState) {
      return;
    }
    const { key } = event;
    if (key === "Escape") {
      event.preventDefault();
      dispatch("clear");
      return;
    }

    if (key === "Enter" || key === " ") {
      event.preventDefault();
      dispatch("clear");
    }
  }

  function handleSelect(event) {
    dispatch("select", event.detail);
  }

  function handleDragStart(event) {
    updateCellSize();
    const { id, orientation, pointerId, startX, startY } = event.detail;
    const target = vehicles.find((vehicle) => vehicle.id === id);
    const bounds = computeAxisBounds(target, buildOccupancy(id));
    dragState = {
      id,
      orientation,
      pointerId,
      startX,
      startY,
      axis: null,
      bounds,
    };
    setDragOffset(id, { x: 0, y: 0 });
  }

  function handleDragMove(event) {
    if (!dragState || dragState.id !== event.detail.id) {
      return;
    }
    const { pointerId, clientX, clientY } = event.detail;
    if (pointerId !== dragState.pointerId) {
      return;
    }
    const deltaX = clientX - dragState.startX;
    const deltaY = clientY - dragState.startY;

    let axis = dragState.axis ?? dragState.orientation;
    if (allowCrossAxisDrag) {
      const absX = Math.abs(deltaX);
      const absY = Math.abs(deltaY);
      const primary = axis === "horizontal" ? absX : absY;
      const secondary = axis === "horizontal" ? absY : absX;
      if (secondary > primary + CROSS_AXIS_THRESHOLD) {
        axis = axis === "horizontal" ? "vertical" : "horizontal";
      }
    }
    dragState.axis = axis;

    const bounds = dragState.bounds?.[axis] ?? { min: 0, max: 0 };
    const rawSteps = cellSize
      ? (axis === "horizontal" ? deltaX : deltaY) / cellSize
      : 0;
    const clampedSteps = clamp(rawSteps, bounds.min, bounds.max);
    const clampedDelta = clampedSteps * cellSize;

    if (axis === "horizontal") {
      setDragOffset(dragState.id, { x: clampedDelta, y: 0 });
    } else {
      setDragOffset(dragState.id, { x: 0, y: clampedDelta });
    }
  }

  function finalizeDrag(event, shouldCommit = true) {
    if (!dragState || dragState.id !== event.detail.id) {
      return;
    }
    const { pointerId, clientX, clientY } = event.detail;
    if (pointerId !== dragState.pointerId) {
      return;
    }
    const deltaX = clientX - dragState.startX;
    const deltaY = clientY - dragState.startY;
    const axis = dragState.axis ?? dragState.orientation;
    const distance = axis === "horizontal" ? deltaX : deltaY;
    const bounds = dragState.bounds?.[axis] ?? { min: 0, max: 0 };
    const rawSteps = cellSize ? distance / cellSize : 0;
    const clampedSteps = clamp(rawSteps, bounds.min, bounds.max);
    const steps = Math.round(clampedSteps);
    const vehicleId = dragState.id;

    setDragOffset(vehicleId, { x: 0, y: 0 });
    dragState = null;

    if (shouldCommit && steps !== 0) {
      const payload = {
        id: vehicleId,
        steps,
        axis,
        rowDelta: axis === "vertical" ? steps : 0,
        colDelta: axis === "horizontal" ? steps : 0,
      };
      dispatch("move", payload);
    }
  }

  function handleDragEnd(event) {
    finalizeDrag(event, true);
  }

  function handleDragCancel(event) {
    finalizeDrag(event, false);
  }

  onMount(() => {
    updateCellSize();
    if (typeof ResizeObserver !== "undefined") {
      resizeObserver = new ResizeObserver(() => updateCellSize());
      if (boardElement) {
        resizeObserver.observe(boardElement);
        observedElement = boardElement;
      }
    }
    window.addEventListener("resize", updateCellSize);
  });

  onDestroy(() => {
    window.removeEventListener("resize", updateCellSize);
    resizeObserver?.disconnect();
    dragOffsets.clear();
    dragState = null;
  });

  $: if (boardElement) {
    updateCellSize();
  }

  $: if (resizeObserver) {
    if (boardElement && boardElement !== observedElement) {
      if (observedElement) {
        resizeObserver.unobserve(observedElement);
      }
      resizeObserver.observe(boardElement);
      observedElement = boardElement;
    }
  }

  $: {
    const validIds = new Set(vehicles.map((vehicle) => vehicle.id));
    const staleIds = [];
    for (const id of dragOffsets.keys()) {
      if (!validIds.has(id)) {
        staleIds.push(id);
      }
    }
    if (staleIds.length > 0) {
      for (const id of staleIds) {
        dragOffsets.delete(id);
      }
      dragOffsets = new Map(dragOffsets);
    }
  }
</script>

<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
<div
  class="board"
  bind:this={boardElement}
  style={boardStyle}
  on:click={handleBoardClick}
  on:keydown={handleBoardKey}
  tabindex="0"
  role="application"
  aria-label={`Parking board ${size} by ${size}`}
  aria-keyshortcuts="Enter Space Escape"
>
  <div class="board__grid"></div>
  {#if highlightRow !== null}
    <div
      aria-hidden="true"
      class="board__lane"
      style={`top: calc(var(--cell-size) * ${highlightRow});`}
    ></div>
  {/if}
  <div
    aria-hidden="true"
    class="board__exit"
    style={`top: calc(var(--cell-size) * ${exitPosition.row} + var(--cell-size) / 2 - var(--exit-height) / 2);`}
  ></div>
  {#each vehicles as vehicle (vehicle.id)}
    <Vehicle
      {vehicle}
      selected={vehicle.id === selectedId}
      dragOffset={dragOffsets.get(vehicle.id) ?? { x: 0, y: 0 }}
      conflicted={typeof conflictedIds?.has === "function"
        ? conflictedIds.has(vehicle.id)
        : false}
      on:select={handleSelect}
      on:dragstart={handleDragStart}
      on:dragmove={handleDragMove}
      on:dragend={handleDragEnd}
      on:dragcancel={handleDragCancel}
    />
  {/each}
</div>

<style>
  .board {
    --board-size: min(80vmin, 520px);
    --cell-size: calc(var(--board-size) / var(--grid-size));
    --grid-line: rgba(15, 23, 42, 0.16);
    --exit-height: calc(var(--cell-size) * 0.75);
    position: relative;
    width: var(--board-size);
    height: var(--board-size);
    margin: 0 auto;
    border-radius: 1.25rem;
    background: #f1f5f9;
    box-shadow: 0 20px 35px rgba(15, 23, 42, 0.16);
    overflow: hidden;
    touch-action: none;
    overscroll-behavior: contain;
  }

  .board__grid {
    position: absolute;
    inset: 0;
    background-image: linear-gradient(
        to right,
        transparent calc(var(--cell-size) - 1px),
        var(--grid-line) calc(var(--cell-size) - 1px)
      ),
      linear-gradient(
        to bottom,
        transparent calc(var(--cell-size) - 1px),
        var(--grid-line) calc(var(--cell-size) - 1px)
      );
    background-size: var(--cell-size) var(--cell-size);
    pointer-events: none;
    z-index: 1;
  }

  .board__lane {
    position: absolute;
    left: 0;
    right: 0;
    height: var(--cell-size);
    background: radial-gradient(
      circle at 0% 50%,
      rgba(37, 99, 235, 0.25),
      transparent 65%
    );
    pointer-events: none;
    transition: opacity 150ms ease;
    z-index: 2;
  }

  .board__exit {
    position: absolute;
    right: -12px;
    width: 18px;
    height: var(--exit-height);
    border-radius: 0.5rem;
    background: linear-gradient(180deg, #10b981, #22c55e);
    box-shadow: 0 0 12px rgba(16, 185, 129, 0.45);
  }
</style>
