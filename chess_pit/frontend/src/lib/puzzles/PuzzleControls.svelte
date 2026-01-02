<script>
  import { createEventDispatcher } from "svelte";
  import { t } from "../i18n";

  const dispatch = createEventDispatcher();

  export let difficulties = [];
  export let selectedDifficulty = "easy";
  export let loadingPuzzle = false;
  export let hintLoading = false;
  export let submitLoading = false;
  export let hintAvailable = false;
  export let hintUsed = false;
  export let hasPendingMove = false;
  export let canResetMove = false;
  export let previewAvailable = false;
  export let previewActive = false;
  export let attemptFinished = false;
  export let pendingMoveLabel = "";
  export let disableActions = false;

  const changeDifficulty = (event) => {
    const selectEl = event?.currentTarget;
    if (!selectEl) return;
    dispatch("difficulty", { value: selectEl.value });
  };
</script>

<section class="controls" aria-label={$t("puzzles.controls.aria")}>
  <div class="controls__row">
    <label class="controls__difficulty">
      <span>{$t("puzzles.controls.difficulty")}</span>
      <select on:change={changeDifficulty} bind:value={selectedDifficulty} disabled={loadingPuzzle || submitLoading}>
        {#each difficulties as option}
          <option value={option.value}>{$t(`puzzles.difficulty.${option.value}`)}</option>
        {/each}
      </select>
    </label>
    <button
      type="button"
      class="ghost"
      on:click={() => dispatch("refresh")}
      disabled={loadingPuzzle || submitLoading}
    >
      {#if loadingPuzzle}
        {$t("puzzles.controls.loading")}
      {:else}
        {$t("puzzles.controls.newPuzzle")}
      {/if}
    </button>
  </div>

  <div class="controls__row">
    <button
      type="button"
      class="primary"
      on:click={() => dispatch("submit")}
      disabled={!hasPendingMove || submitLoading || disableActions || attemptFinished}
    >
      {#if submitLoading}
        {$t("puzzles.controls.submitting")}
      {:else if hasPendingMove}
        {$t("puzzles.controls.submitMove")}
      {:else}
        {$t("puzzles.controls.submitDisabled")}
      {/if}
    </button>
    <button
      type="button"
      class="ghost"
      on:click={() => dispatch("resetMove")}
      disabled={!canResetMove || submitLoading || disableActions}
    >
      {$t("puzzles.controls.resetMove")}
    </button>
    <button
      type="button"
      class="hint"
      on:click={() => dispatch("hint")}
      disabled={!hintAvailable || hintLoading || hintUsed || disableActions || attemptFinished}
    >
      {#if hintLoading}
        {$t("puzzles.controls.hintLoading")}
      {:else}
        {$t("puzzles.controls.hintButton")}
      {/if}
    </button>
  </div>

  <div class="controls__row">
    <button
      type="button"
      class="preview"
      on:click={() => dispatch("preview")}
      disabled={!previewAvailable || submitLoading || disableActions || attemptFinished}
    >
      {#if previewActive}
        {$t("puzzles.controls.hideLine")}
      {:else}
        {$t("puzzles.controls.showLine")}
      {/if}
    </button>
  </div>

  {#if pendingMoveLabel}
    <p class="pending">{$t("puzzles.controls.pendingMove", { move: pendingMoveLabel })}</p>
  {/if}

  {#if attemptFinished}
    <div class="controls__row controls__row--complete">
      <button
        type="button"
        class="ghost retry"
        on:click={() => dispatch("retry")}
        disabled={disableActions}
      >
        {$t("puzzles.controls.retryPuzzle")}
      </button>
      <button
        type="button"
        class="next"
        on:click={() => dispatch("next")}
        disabled={loadingPuzzle}
      >
        {$t("puzzles.controls.nextPuzzle")}
      </button>
    </div>
  {/if}
</section>

<style>
  .controls {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    background: rgba(15, 23, 42, 0.45);
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 16px;
    padding: 1.25rem;
    color: #e2e8f0;
  }

  .controls__row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
  }

  .controls__difficulty {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: rgba(148, 163, 184, 0.75);
  }

  select {
    appearance: none;
    background: rgba(15, 23, 42, 0.75);
    border-radius: 12px;
    border: 1px solid rgba(148, 163, 184, 0.35);
    color: inherit;
    padding: 0.55rem 0.85rem;
    font-size: 0.95rem;
  }

  button {
    border: none;
    border-radius: 12px;
    padding: 0.75rem 1.15rem;
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
    transition: transform 120ms ease, filter 120ms ease;
  }

  button:disabled {
    cursor: not-allowed;
    opacity: 0.55;
  }

  .primary {
    background: linear-gradient(130deg, #6366f1, #22d3ee);
    color: #fff;
  }

  .ghost {
    background: rgba(15, 23, 42, 0.75);
    border: 1px solid rgba(148, 163, 184, 0.35);
    color: inherit;
  }

  .hint {
    background: rgba(245, 158, 11, 0.18);
    border: 1px solid rgba(245, 158, 11, 0.55);
    color: #fbbf24;
  }

  .preview {
    width: 100%;
    background: rgba(34, 197, 94, 0.16);
    border: 1px solid rgba(34, 197, 94, 0.42);
    color: #bbf7d0;
  }

  .next {
    align-self: flex-start;
    background: linear-gradient(130deg, #22c55e, #16a34a);
    color: #fff;
  }

  .retry {
    flex: 1 1 auto;
  }

  .controls__row--complete {
    justify-content: flex-start;
  }

  .pending {
    margin: 0;
    font-size: 0.85rem;
    color: rgba(148, 163, 184, 0.8);
  }

  @media (max-width: 680px) {
    .controls__row {
      flex-direction: column;
      align-items: stretch;
    }

    button,
    select {
      width: 100%;
    }
  }
</style>
