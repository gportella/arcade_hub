<script>
  import { createEventDispatcher } from "svelte";
  import ChessBoard from "../ChessBoard.svelte";

  export let startingFen = null;
  export let positionFen = null;
  export let resetToken = 0;
  export let orientation = "white";
  export let guidanceShapes = [];
  export let interactive = false;
  export let attemptFinished = false;
  export let loadingPuzzle = false;
  export let nextLabel = "";
  export let retryLabel = "";

  const dispatch = createEventDispatcher();

  const handleMove = (detail) => {
    dispatch("move", detail);
  };

  const handleNext = () => {
    dispatch("next");
  };

  const handleRetry = () => {
    dispatch("retry");
  };
</script>

<section class="board-panel">
  <ChessBoard
    {startingFen}
    positionFen={positionFen}
    resetToken={resetToken}
    {orientation}
    {guidanceShapes}
    interactive={interactive}
    showStatus={false}
    showControls={false}
    onMove={handleMove}
  />

  {#if attemptFinished}
    <div class="board-actions">
      <button type="button" class="board-actions__next" on:click={handleNext} disabled={loadingPuzzle}>
        {nextLabel}
      </button>
      <button type="button" class="board-actions__retry" on:click={handleRetry} disabled={loadingPuzzle}>
        {retryLabel}
      </button>
    </div>
  {/if}
</section>

<style>
  .board-panel {
    background: rgba(15, 23, 42, 0.38);
    border-radius: 18px;
    padding: 1.1rem;
    border: 1px solid rgba(148, 163, 184, 0.16);
    transition: box-shadow 0.2s ease;
  }

  .board-panel:hover {
    box-shadow: 0 16px 32px rgba(15, 23, 42, 0.35);
  }

  .board-actions {
    display: none;
    margin-top: 0.85rem;
    gap: 0.65rem;
  }

  .board-actions__next,
  .board-actions__retry {
    flex: 1 1 auto;
    border-radius: 12px;
    padding: 0.65rem 0.9rem;
    font-size: 0.9rem;
    font-weight: 600;
    border: none;
    cursor: pointer;
    transition: transform 140ms ease, filter 140ms ease;
  }

  .board-actions__next {
    background: linear-gradient(135deg, #22c55e, #16a34a);
    color: #f8fafc;
  }

  .board-actions__retry {
    background: rgba(15, 23, 42, 0.75);
    border: 1px solid rgba(148, 163, 184, 0.35);
    color: #e2e8f0;
  }

  .board-actions__next:disabled,
  .board-actions__retry:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .board-actions__next:not(:disabled):hover,
  .board-actions__retry:not(:disabled):hover {
    transform: translateY(-1px);
  }

  @media (max-width: 680px) {
    .board-panel {
      padding: 0.75rem;
    }

    .board-actions {
      display: flex;
    }
  }
</style>
