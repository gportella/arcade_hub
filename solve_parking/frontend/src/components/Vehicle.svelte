<script>
  import { createEventDispatcher } from "svelte";

  export let vehicle;
  export let selected = false;
  export let dragOffset = { x: 0, y: 0 };
  export let conflicted = false;

  const dispatch = createEventDispatcher();

  const DRAG_THRESHOLD = 6;

  $: width = vehicle.orientation === "horizontal" ? vehicle.length : 1;
  $: height = vehicle.orientation === "vertical" ? vehicle.length : 1;

  $: offsetX = `${dragOffset?.x ?? 0}px`;
  $: offsetY = `${dragOffset?.y ?? 0}px`;

  let isDragging = false;
  let pendingDrag = null;

  $: style = `
    width: calc(var(--cell-size) * ${width});
    height: calc(var(--cell-size) * ${height});
    left: calc(var(--cell-size) * ${vehicle.col});
    top: calc(var(--cell-size) * ${vehicle.row});
    --offset-x: ${offsetX};
    --offset-y: ${offsetY};
  `;

  function handleSelect(event) {
    event.stopPropagation();
    dispatch("select", { id: vehicle.id });
  }

  function handlePointerDown(event) {
    if (event.pointerType === "mouse" && event.button !== 0) {
      return;
    }
    event.stopPropagation();
    if (event.pointerType === "touch") {
      event.preventDefault();
    }
    pendingDrag = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function handlePointerMove(event) {
    if (!event.currentTarget.hasPointerCapture(event.pointerId)) {
      return;
    }
    if (
      pendingDrag &&
      pendingDrag.pointerId === event.pointerId &&
      !isDragging
    ) {
      const deltaX = event.clientX - pendingDrag.startX;
      const deltaY = event.clientY - pendingDrag.startY;
      const delta = Math.abs(deltaX) + Math.abs(deltaY);
      if (delta >= DRAG_THRESHOLD) {
        isDragging = true;
        dispatch("select", { id: vehicle.id });
        dispatch("dragstart", {
          id: vehicle.id,
          orientation: vehicle.orientation,
          pointerId: event.pointerId,
          startX: pendingDrag.startX,
          startY: pendingDrag.startY,
        });
        pendingDrag = null;
      }
    }

    if (!isDragging) {
      return;
    }

    event.preventDefault();
    dispatch("dragmove", {
      id: vehicle.id,
      pointerId: event.pointerId,
      clientX: event.clientX,
      clientY: event.clientY,
    });
  }

  function handlePointerEnd(event) {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }

    if (isDragging) {
      event.preventDefault();
      dispatch("dragend", {
        id: vehicle.id,
        pointerId: event.pointerId,
        clientX: event.clientX,
        clientY: event.clientY,
      });
    }

    isDragging = false;
    pendingDrag = null;
  }

  function handlePointerCancel(event) {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    if (isDragging) {
      event.preventDefault();
      dispatch("dragcancel", {
        id: vehicle.id,
        pointerId: event.pointerId,
        clientX: event.clientX,
        clientY: event.clientY,
      });
    }
    isDragging = false;
    pendingDrag = null;
  }
</script>

<button
  class:selected
  class:goal={vehicle.goal}
  class:dragging={isDragging}
  class:conflicted
  class="vehicle"
  data-orientation={vehicle.orientation}
  aria-pressed={selected}
  aria-label={`Vehicle ${vehicle.id}, ${vehicle.orientation}, length ${vehicle.length}`}
  type="button"
  {style}
  on:click={handleSelect}
  on:pointerdown={handlePointerDown}
  on:pointermove={handlePointerMove}
  on:pointerup={handlePointerEnd}
  on:pointercancel={handlePointerCancel}
  on:lostpointercapture={handlePointerCancel}
>
  <span class="vehicle__label">{vehicle.id}</span>
</button>

<style>
  .vehicle {
    --offset-x: 0px;
    --offset-y: 0px;
    --scale: 1;
    position: absolute;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 0.6rem;
    border: 1px solid rgba(15, 23, 42, 0.2);
    background: linear-gradient(
      135deg,
      rgba(59, 130, 246, 0.85),
      rgba(37, 99, 235, 0.85)
    );
    color: #fff;
    font-weight: 600;
    letter-spacing: 0.02em;
    box-shadow: 0 10px 20px rgba(15, 23, 42, 0.15);
    transition:
      transform 150ms ease,
      box-shadow 150ms ease,
      border-color 150ms ease;
    padding: 0;
    z-index: 3;
    cursor: grab;
    transform: translate3d(var(--offset-x), var(--offset-y), 0)
      scale(var(--scale));
    touch-action: none;
  }

  .vehicle.goal {
    background: linear-gradient(135deg, #f97316, #fb923c);
  }

  .vehicle.selected {
    --scale: 1.03;
    box-shadow: 0 12px 24px rgba(59, 130, 246, 0.25);
    border-color: rgba(37, 99, 235, 0.8);
  }

  .vehicle.conflicted {
    border-color: rgba(185, 28, 28, 0.85);
    box-shadow: 0 0 0 2px rgba(185, 28, 28, 0.35);
  }

  .vehicle.dragging {
    cursor: grabbing;
    transition:
      box-shadow 150ms ease,
      border-color 150ms ease;
  }

  .vehicle:focus-visible {
    outline: 2px solid #3b82f6;
    outline-offset: 2px;
  }

  .vehicle__label {
    pointer-events: none;
    font-size: 1.1rem;
  }
</style>
