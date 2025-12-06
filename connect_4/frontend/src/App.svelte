<script>
  import { onMount } from "svelte";
  import {
    MODES,
    COLORS,
    DIFFICULTY_LABELS,
    DIFFICULTY_DEPTH,
    COLOR_LABELS,
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
  let copyStatus = "";
  let lastGameId = null;

  onMount(() => {
    document.title = appName;
    refreshLobbyList();
  });

  $: state = $gameStore;

  function colorLabelFromName(name) {
    if (!name) {
      return null;
    }
    const normalized = name.toLowerCase();
    if (normalized === "yellow") {
      return COLOR_LABELS[COLORS.YELLOW];
    }
    if (normalized === "red") {
      return COLOR_LABELS[COLORS.RED];
    }
    return null;
  }

  function playerColorLabel(playerId) {
    return colorLabelFromName(state?.playerColors?.[playerId]);
  }

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

  async function copyInviteLink() {
    if (!state?.gameId) {
      return;
    }
    const link =
      state.shareUrl ??
      (typeof window !== "undefined"
        ? new URL(window.location.href).toString()
        : state.gameId);
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(link);
      } else {
        const dummy = document.createElement("textarea");
        dummy.value = link;
        document.body.appendChild(dummy);
        dummy.select();
        document.execCommand("copy");
        document.body.removeChild(dummy);
      }
      copyStatus = "Link copied!";
      setTimeout(() => {
        copyStatus = "";
      }, 2000);
    } catch (error) {
      console.error("Failed to copy invite link", error);
      copyStatus = "Copy failed";
      setTimeout(() => {
        copyStatus = "";
      }, 2000);
    }
  }

  function refreshLobbyList() {
    gameStore
      .refreshLobby()
      .catch((error) => console.error("Failed to refresh lobby", error));
  }

  function handleJoinFromLobby(gameId) {
    if (!gameId) {
      return;
    }
    gameStore
      .joinGame(gameId)
      .catch((error) => console.error("Failed to join lobby game", error));
  }

  function summarizePlayers(list) {
    if (!Array.isArray(list) || list.length === 0) {
      return "";
    }
    return list.map((id) => id.slice(0, 6)).join(", ");
  }

  $: isBoardInteractive =
    state &&
    !state.winner &&
    !state.draw &&
    state.connectionState === "connected" &&
    (state.mode === MODES.SOLO
      ? state.toPlay !== COLORS.RED
      : Array.isArray(state.players) &&
        state.players.length >= 2 &&
        typeof state.localColorValue === "number" &&
        state.localColorValue === state.toPlay);

  $: difficultyLabel =
    state && state.difficulty ? DIFFICULTY_LABELS[state.difficulty] : null;
  $: difficultyDepth =
    state && state.aiDepth != null
      ? state.aiDepth
      : state && state.difficulty
        ? DIFFICULTY_DEPTH[state.difficulty]
        : null;
  $: localColorLabel = colorLabelFromName(state?.localColor);
  $: if (state?.gameId !== lastGameId) {
    lastGameId = state?.gameId ?? null;
    copyStatus = "";
  }
</script>

<main class="app" class:app--controls-collapsed={controlsCollapsed}>
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
        players={state.players}
        localColor={state.localColorValue}
      />
    </div>
    <button type="button" class="status-bar__reset" on:click={handleReset}>
      Reset Board
    </button>
  </div>

  {#if state.mode === MODES.MULTIPLAYER && !controlsCollapsed}
    <div class="player-avatars">
      {#each state.players as player, index}
        <div
          class={`player-avatar ${player === state.playerId ? "player-avatar--self" : ""}`}
        >
          <span class="player-avatar__icon">{index === 0 ? "😎" : "🧢"}</span>
          <span class="player-avatar__name">{player}</span>
          {#if playerColorLabel(player)}
            <span
              class={`player-avatar__color player-avatar__color--${playerColorLabel(player) === COLOR_LABELS[COLORS.YELLOW] ? "yellow" : "red"}`}
            >
              {playerColorLabel(player)}
            </span>
          {/if}
        </div>
      {/each}
      {#if state.players.length < 2}
        <div class="player-avatar placeholder">Waiting for another player…</div>
      {/if}
    </div>
  {/if}

  {#if state.mode === MODES.MULTIPLAYER && !controlsCollapsed}
    <section class="multiplayer-meta">
      {#if state.gameId}
        <div class="invite-row">
          <span class="invite-label">Invite code</span>
          <code class="invite-code">{state.gameId}</code>
          <button type="button" class="invite-copy" on:click={copyInviteLink}>
            {copyStatus || "Copy Link"}
          </button>
        </div>
      {/if}
      {#if localColorLabel}
        <p class="color-note">You are playing as {localColorLabel}.</p>
      {/if}
    </section>
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

      <section class="lobby-panel">
        <div class="lobby-panel__header">
          <h2>Waiting Room</h2>
          <button
            type="button"
            class="lobby-panel__refresh"
            on:click={refreshLobbyList}
          >
            Refresh
          </button>
        </div>
        {#if state.lobbyLoading}
          <p class="lobby-panel__status">Loading games…</p>
        {:else if state.lobbyError}
          <p class="lobby-panel__status lobby-panel__status--error">
            {state.lobbyError}
          </p>
        {:else if !state.lobbyGames || state.lobbyGames.length === 0}
          <p class="lobby-panel__status">No open games yet. Start one above!</p>
        {:else}
          <ul class="lobby-panel__list">
            {#each state.lobbyGames as lobbyGame (lobbyGame.gameId)}
              <li class="lobby-panel__item">
                <div class="lobby-panel__info">
                  <code class="lobby-panel__code" title={lobbyGame.gameId}
                    >{lobbyGame.gameId}</code
                  >
                  <span
                    class="lobby-panel__players"
                    title={lobbyGame.players.length > 0
                      ? lobbyGame.players.join(", ")
                      : undefined}
                  >
                    {lobbyGame.players.length}/{lobbyGame.capacity} players
                    {#if lobbyGame.players.length > 0}
                      • {summarizePlayers(lobbyGame.players)}
                    {/if}
                  </span>
                </div>
                <button
                  type="button"
                  class="lobby-panel__join"
                  on:click={() => handleJoinFromLobby(lobbyGame.gameId)}
                >
                  Join
                </button>
              </li>
            {/each}
          </ul>
        {/if}
      </section>
    </section>
  {/if}
</main>

<style>
  .app {
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

  .app--controls-collapsed .app__sidebar,
  .app--controls-collapsed .multiplayer-meta,
  .app--controls-collapsed .player-avatars {
    display: none !important;
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

  .multiplayer-meta {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .invite-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .invite-label {
    font-weight: 600;
    color: rgba(255, 255, 255, 0.85);
  }

  .invite-code {
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.12);
    border: 1px solid rgba(255, 255, 255, 0.2);
    font-family: var(--font-mono, "Fira Code", monospace);
    font-size: 0.9rem;
    color: rgba(255, 255, 255, 0.9);
  }

  .invite-copy {
    border: none;
    border-radius: 999px;
    padding: 0.4rem 0.9rem;
    background: rgba(255, 255, 255, 0.92);
    color: rgba(12, 26, 54, 0.85);
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s ease;
  }

  .invite-copy:hover {
    background: rgba(255, 255, 255, 0.98);
  }

  .color-note {
    margin: 0;
    font-size: 0.9rem;
    color: rgba(255, 255, 255, 0.75);
  }

  .player-avatars {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
  }

  .player-avatar {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.45rem 0.75rem;
    background: rgba(9, 22, 47, 0.6);
    border-radius: 999px;
    border: 1px solid rgba(255, 255, 255, 0.16);
    box-shadow: 0 0.25rem 0.75rem rgba(0, 0, 0, 0.2);
  }

  .player-avatar--self {
    border-color: rgba(255, 255, 255, 0.35);
    background: rgba(17, 40, 82, 0.75);
  }

  .player-avatar.placeholder {
    color: rgba(255, 255, 255, 0.6);
    font-style: italic;
  }

  .player-avatar__icon {
    font-size: 1.25rem;
  }

  .player-avatar__name {
    font-weight: 600;
    color: rgba(255, 255, 255, 0.85);
  }

  .player-avatar__color {
    padding: 0.15rem 0.55rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: rgba(10, 24, 52, 0.85);
  }

  .player-avatar__color--yellow {
    background: #ffd447;
  }

  .player-avatar__color--red {
    background: #ff5964;
  }

  .lobby-panel {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    padding: 1rem;
    background: rgba(9, 22, 47, 0.45);
    border-radius: 1rem;
    border: 1px solid rgba(255, 255, 255, 0.15);
  }

  .lobby-panel__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
  }

  .lobby-panel__header h2 {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.95);
  }

  .lobby-panel__refresh {
    border: none;
    border-radius: 999px;
    padding: 0.35rem 0.85rem;
    background: rgba(255, 255, 255, 0.9);
    color: rgba(12, 26, 54, 0.85);
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s ease;
  }

  .lobby-panel__refresh:hover {
    background: rgba(255, 255, 255, 0.98);
  }

  .lobby-panel__status {
    margin: 0;
    font-size: 0.9rem;
    color: rgba(255, 255, 255, 0.75);
  }

  .lobby-panel__status--error {
    color: #ff7b7b;
  }

  .lobby-panel__list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .lobby-panel__item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    padding: 0.6rem 0.85rem;
    background: rgba(11, 25, 52, 0.65);
    border-radius: 0.85rem;
    border: 1px solid rgba(255, 255, 255, 0.12);
  }

  .lobby-panel__info {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    min-width: 0;
  }

  .lobby-panel__code {
    display: inline-block;
    max-width: 14rem;
    padding: 0.15rem 0.55rem;
    background: rgba(255, 255, 255, 0.12);
    border-radius: 0.65rem;
    border: 1px solid rgba(255, 255, 255, 0.18);
    font-family: var(--font-mono, "Fira Code", monospace);
    font-size: 0.85rem;
    color: rgba(255, 255, 255, 0.95);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .lobby-panel__players {
    font-size: 0.8rem;
    color: rgba(255, 255, 255, 0.7);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .lobby-panel__join {
    border: none;
    border-radius: 999px;
    padding: 0.35rem 0.85rem;
    background: #ffd447;
    color: rgba(12, 26, 54, 0.9);
    font-weight: 700;
    cursor: pointer;
    transition: transform 0.2s ease;
  }

  .lobby-panel__join:hover {
    transform: translateY(-1px);
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

    .player-avatars {
      gap: 0.5rem;
    }

    .invite-row {
      gap: 0.35rem;
    }

    .invite-code {
      font-size: 0.8rem;
    }

    .color-note {
      font-size: 0.8rem;
    }

    .app__sidebar {
      padding: 1rem;
      gap: 1rem;
    }

    .hint {
      font-size: 0.85rem;
    }

    .lobby-panel {
      padding: 0.85rem;
    }

    .lobby-panel__item {
      flex-direction: column;
      align-items: stretch;
      gap: 0.6rem;
    }

    .lobby-panel__code {
      max-width: 100%;
    }

    .lobby-panel__join {
      width: 100%;
    }
  }
</style>
