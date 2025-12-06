<script>
  import { onMount } from "svelte";
  import {
    MODES,
    COLORS,
    DIFFICULTY_LABELS,
    DIFFICULTY_DEPTH,
  } from "./lib/constants.js";
  import { gameStore } from "./lib/game/store.js";
  import ModeSwitcher from "./lib/components/ModeSwitcher.svelte";
  import DifficultySelector from "./lib/components/DifficultySelector.svelte";
  import ConnectFourBoard from "./lib/components/ConnectFourBoard.svelte";
  import GameStatus from "./lib/components/GameStatus.svelte";

  const ALTERNATE_NAMES = [
    "Stack 4",
    "Drop 4",
    "Combo 4",
    "Link-Up 4",
    "Quad Link",
    "Row Rush",
    "W-Row",
    "GG Connect",
    "Clutch 4",
    "GG 4",
    "4 Lolz",
    "Big W 4",
    "Finish Four",
    "Win Line",
    "Fire Four",
    "Lit Lines",
    "GOAT Row",
    "Based Lines",
    "No Cap Row",
    "Lowkey Link",
    "Row Flow",
    "Stack Attack",
    "Token Drop",
    "Chain Four",
    "Grid Lock",
  ];

  function randomName() {
    const index = Math.floor(Math.random() * ALTERNATE_NAMES.length);
    return ALTERNATE_NAMES[index];
  }

  let appName = randomName();
  let controlsCollapsed = false;

  onMount(() => {
    document.title = appName;
  });

  $: state = $gameStore;

  function handleModeChange(mode) {
    const difficulty = state?.difficulty;
    gameStore
      .startNewGame(mode, difficulty)
      .catch((error) => console.error("Failed to start new game", error));
  }

  function handleColumnSelect(column) {
    gameStore.playColumn(column);
  }

  function handleReset() {
    gameStore.reset();
  }

  function handleDifficultyChange(difficulty) {
    gameStore
      .startNewGame(MODES.SOLO, difficulty)
      .catch((error) => console.error("Failed to change difficulty", error));
  }

  function toggleControls() {
    controlsCollapsed = !controlsCollapsed;
  }

  $: isBoardInteractive =
    state &&
    !state.winner &&
    !state.draw &&
    state.connectionState === "connected" &&
    !(state.mode === MODES.SOLO && state.toPlay === COLORS.RED);

  $: difficultyLabel =
    state && state.difficulty ? DIFFICULTY_LABELS[state.difficulty] : null;
  $: difficultyDepth =
    state && state.aiDepth != null
      ? state.aiDepth
      : state && state.difficulty
        ? DIFFICULTY_DEPTH[state.difficulty]
        : null;
</script>

<main class="app">
  <header class="app__header">
    <div class="app__title-row">
      <h1>{appName}</h1>
      <button
        type="button"
        class="controls-toggle"
        on:click={toggleControls}
        aria-expanded={!controlsCollapsed}
      >
        {controlsCollapsed ? "Show Controls" : "Hide Controls"}
      </button>
    </div>
  </header>

  <section class="app__board">
    <ConnectFourBoard
      board={state.board}
      playableColumns={state.playableColumns}
      lastMove={state.lastMove}
      disabled={!isBoardInteractive}
      onSelect={handleColumnSelect}
    />
  </section>

  <div class="status-bar">
    <div class="status-bar__status">
      <GameStatus
        mode={state.mode}
        toPlay={state.toPlay}
        winner={state.winner}
        draw={state.draw}
        moveCount={state.moveCount}
        connectionState={state.connectionState}
        error={state.error}
        difficulty={state.mode === MODES.SOLO ? state.difficulty : null}
        aiDepth={state.aiDepth}
      />
    </div>
    <button type="button" class="status-bar__reset" on:click={handleReset}>
      Reset Board
    </button>
  </div>

  {#if state.mode === MODES.MULTIPLAYER}
    <div class="player-avatars">
      {#each state.players as player, index}
        <div class="player-avatar">
          <span class="player-avatar__icon">{index === 0 ? "😎" : "🧢"}</span>
          <span class="player-avatar__name">{player}</span>
        </div>
      {/each}
      {#if state.players.length === 0}
        <div class="player-avatar placeholder">Waiting for players…</div>
      {/if}
    </div>
  {/if}

  {#if !controlsCollapsed}
    <section class="app__sidebar">
      <ModeSwitcher mode={state.mode} onModeChange={handleModeChange} />
      {#if state.mode === MODES.SOLO}
        <DifficultySelector
          difficulty={state.difficulty}
          onDifficultyChange={handleDifficultyChange}
        />
      {/if}
      {#if state.mode === MODES.SOLO}
        <p class="hint">
          You play as Yellow. The computer drops Red discs.
          {#if difficultyLabel && difficultyDepth}
            Current difficulty: {difficultyLabel} (depth {difficultyDepth}).
          {/if}
        </p>
      {/if}
    </section>
  {/if}
</main>

<style>
  .app {
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

  .app__title-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
  }

  .app__title-row h1 {
    margin: 0;
    font-size: clamp(2.25rem, 2.5vw + 1.5rem, 3rem);
  }

  .controls-toggle {
    border: none;
    border-radius: 999px;
    padding: 0.45rem 1rem;
    font-size: 0.9rem;
    font-weight: 600;
    color: rgba(10, 24, 52, 0.85);
    background: rgba(255, 255, 255, 0.9);
    cursor: pointer;
    transition: background 0.2s ease;
  }

  .controls-toggle:hover {
    background: rgba(255, 255, 255, 0.98);
  }

  .status-bar {
    display: flex;
    gap: 1rem;
    align-items: stretch;
  }

  .status-bar__status {
    flex: 1 1 auto;
  }

  .status-bar__reset {
    flex: 0 0 25%;
    min-width: 160px;
    border: none;
    border-radius: 999px;
    background: var(--accent-color);
    color: white;
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
    transition:
      transform 100ms ease,
      box-shadow 100ms ease;
  }

  .status-bar__reset:hover {
    transform: translateY(-1px);
    box-shadow: 0 0.5rem 1rem rgba(40, 60, 120, 0.35);
  }

  .status-bar__reset:active {
    transform: translateY(0);
    box-shadow: none;
  }

  .app__sidebar {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
    padding: 1.25rem;
    background: rgba(11, 26, 52, 0.65);
    border-radius: 1.25rem;
    backdrop-filter: blur(9px);
    box-shadow: 0 1.5rem 2.5rem rgba(0, 0, 0, 0.25);
  }

  .app__board {
    display: flex;
    justify-content: center;
    align-items: center;
  }

  .hint {
    margin: 0;
    font-size: 0.9rem;
    color: rgba(255, 255, 255, 0.7);
  }

  @media (max-width: 720px) {
    .status-bar {
      flex-direction: column;
      gap: 0.75rem;
    }

    .status-bar__reset {
      flex: none;
      width: 100%;
      min-width: unset;
    }

    .controls-toggle {
      font-size: 0.85rem;
      padding: 0.35rem 0.85rem;
    }

    .app__sidebar {
      padding: 1rem;
      gap: 1rem;
    }

    .hint {
      font-size: 0.85rem;
    }
  }
</style>
