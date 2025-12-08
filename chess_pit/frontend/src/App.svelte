<script>
  import { onDestroy } from "svelte";
  import LandingView from "./lib/views/LandingView.svelte";
  import GameHubView from "./lib/views/GameHubView.svelte";
  import GamePlayView from "./lib/views/GamePlayView.svelte";
  import ProfileView from "./lib/views/ProfileView.svelte";

  import {
    login,
    fetchHubOverview,
    fetchGameDetail,
    createGame,
    submitMove,
    updateUser,
    resignGame,
    connectToGame,
  } from "./lib/api/client";

  const VIEW = Object.freeze({
    LANDING: "landing",
    GAMES: "games",
    PLAY: "play",
    PROFILE: "profile",
  });

  const SHOWCASE_FEN =
    "r1bq1rk1/ppp2ppp/2n2n2/2bp4/4P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 2 9";

  /** @type {"landing" | "games" | "play" | "profile"} */
  let currentView = VIEW.LANDING;
  let isAuthenticated = false;
  let accessToken = "";
  let currentUser = null;
  let rawSummaryIndex = new Map();
  let uiSummaryIndex = new Map();
  let games = [];
  let orderedGames = [];
  let selectedGameId = null;
  let selectedGame = null;
  let showNewGameForm = false;
  let newGameOpponentId = "";
  let newGameColor = "white";
  let availableOpponents = [];
  let profileDraft = { avatarUrl: "", password: "" };
  let landingError = "";
  let isLandingLoading = false;
  let hubError = "";
  let gameError = "";
  let socket = null;
  let hubUser = null;
  let hubPollTimer = null;
  const HUB_POLL_INTERVAL = 15000;

  function fallbackAvatar(username = "player") {
    const slug = encodeURIComponent(username || "player");
    return `https://avatar.vercel.sh/${slug}`;
  }

  function startHubPolling() {
    if (hubPollTimer) {
      return;
    }
    hubPollTimer = setInterval(() => {
      if (isAuthenticated && currentView === VIEW.GAMES) {
        void loadHub();
      }
    }, HUB_POLL_INTERVAL);
  }

  function stopHubPolling() {
    if (!hubPollTimer) {
      return;
    }
    clearInterval(hubPollTimer);
    hubPollTimer = null;
  }

  function toOpponent(player) {
    if (!player) {
      return {
        id: 0,
        nickname: "Unknown",
        avatar: fallbackAvatar("unknown"),
        title: "",
      };
    }
    return {
      id: player.id,
      nickname: player.username,
      avatar: player.avatar_url || fallbackAvatar(player.username),
      title: "",
    };
  }

  function formatResult(result) {
    if (result === "white") return "1-0";
    if (result === "black") return "0-1";
    if (result === "draw") return "½-½";
    return "";
  }

  const formatTime = (iso) => {
    if (!iso) return "";
    const target = new Date(iso);
    const diff = Date.now() - target.getTime();
    const minute = 60000;
    const hour = 60 * minute;
    const day = 24 * hour;

    if (diff < minute) return "moments ago";
    if (diff < hour) {
      const value = Math.round(diff / minute);
      return `${value} min ago`;
    }
    if (diff < day) {
      const value = Math.round(diff / hour);
      return `${value} hr ago`;
    }
    if (diff < 7 * day) {
      const value = Math.round(diff / day);
      return `${value} day${value === 1 ? "" : "s"} ago`;
    }
    return target.toLocaleDateString();
  };

  const parseActiveColor = (fen) => {
    if (!fen) return "white";
    const parts = fen.split(" ");
    return parts[1] === "b" ? "black" : "white";
  };

  function mapGameSummary(summary) {
    const opponent = toOpponent(summary.opponent);
    const fen = summary.current_fen || summary.initial_fen;
    const lastUpdated = summary.last_updated || summary.started_at;
    return {
      id: summary.id,
      opponent,
      status: summary.status,
      result: summary.result,
      resultDisplay: formatResult(summary.result),
      summary: summary.summary || "Friendly challenge",
      fen,
      initialFen: summary.initial_fen,
      pgn: summary.pgn,
      yourColor: summary.your_color,
      turn: summary.turn || parseActiveColor(fen),
      lastUpdated,
      startedAt: summary.started_at,
      movesCount: summary.moves_count,
      currentPositionHash: summary.current_position_hash,
    };
  }

  function mapGameDetail(detail) {
    const summaryUi = uiSummaryIndex.get(detail.id);
    const summaryRaw = rawSummaryIndex.get(detail.id);
    const fen = detail.current_fen || detail.initial_fen;
    const opponent = summaryUi?.opponent || toOpponent(summaryRaw?.opponent);
    const yourColor =
      summaryUi?.yourColor ||
      (currentUser && detail.white_player_id === currentUser.id
        ? "white"
        : "black");
    const turn = parseActiveColor(fen);
    return {
      id: detail.id,
      opponent,
      status: detail.status,
      result: detail.result,
      resultDisplay: formatResult(detail.result),
      summary: detail.summary || summaryUi?.summary || "Friendly challenge",
      fen,
      initialFen: detail.initial_fen,
      pgn: detail.pgn,
      yourColor,
      turn,
      lastUpdated: detail.last_move_at || detail.started_at,
      startedAt: detail.started_at,
      movesCount: detail.moves?.length ?? detail.moves_count,
      currentPositionHash: detail.current_position_hash,
      moves: detail.moves ?? [],
    };
  }

  function sortGames(entries = []) {
    return entries.slice().sort((a, b) => {
      const finishedA = a.status === "completed" || a.status === "aborted";
      const finishedB = b.status === "completed" || b.status === "aborted";
      if (finishedA !== finishedB) {
        return Number(finishedA) - Number(finishedB);
      }
      const timeA = new Date(a.lastUpdated ?? 0).getTime();
      const timeB = new Date(b.lastUpdated ?? 0).getTime();
      return timeB - timeA;
    });
  }

  const gameStatusLabel = (game) => {
    if (!game) return "";
    if (game.status === "completed") {
      return game.resultDisplay ? `Final · ${game.resultDisplay}` : "Final";
    }
    if (game.status === "aborted") {
      return "Aborted";
    }
    if (game.turn === game.yourColor) {
      return "Your move";
    }
    return `${game.opponent.nickname}'s move`;
  };

  const colorLabel = (color) => (color === "black" ? "Black" : "White");

  async function performLogin(credentials) {
    const username = credentials?.username?.trim();
    const password = credentials?.password?.trim();
    landingError = "";
    if (!username || !password) {
      landingError = "Username and password are required.";
      return;
    }
    isLandingLoading = true;
    try {
      accessToken = await login(username, password);
      isAuthenticated = true;
      await loadHub();
      currentView = VIEW.GAMES;
      startHubPolling();
    } catch (error) {
      landingError =
        error instanceof Error ? error.message : "Unable to sign in.";
      accessToken = "";
      isAuthenticated = false;
    } finally {
      isLandingLoading = false;
    }
  }

  async function loadHub() {
    hubError = "";
    if (!accessToken) return;
    try {
      const hub = await fetchHubOverview(accessToken);
      currentUser = hub.user;
      rawSummaryIndex = new Map();
      uiSummaryIndex = new Map();
      for (const summary of hub.games) {
        rawSummaryIndex.set(summary.id, summary);
        uiSummaryIndex.set(summary.id, mapGameSummary(summary));
      }
      games = Array.from(uiSummaryIndex.values());
      availableOpponents = hub.opponents.map(toOpponent);
      profileDraft = {
        avatarUrl: hub.user.avatar_url || "",
        password: "",
      };
    } catch (error) {
      hubError =
        error instanceof Error ? error.message : "Failed to load games.";
    }
  }

  async function refreshSelectedGame(gameId) {
    if (!accessToken) return;
    gameError = "";
    try {
      const detail = await fetchGameDetail(gameId, accessToken);
      selectedGame = mapGameDetail(detail);
    } catch (error) {
      gameError =
        error instanceof Error ? error.message : "Failed to load game.";
    }
  }

  function teardownSocket() {
    if (socket) {
      socket.close();
      socket = null;
    }
  }

  function connectSocket(gameId) {
    teardownSocket();
    try {
      socket = connectToGame(gameId);
    } catch (error) {
      console.warn("Unable to open websocket", error);
      return;
    }
    socket.onmessage = (event) => handleSocketMessage(gameId, event);
    socket.onclose = () => {
      socket = null;
    };
  }

  async function openGame(id) {
    if (!id || !isAuthenticated) return;
    selectedGameId = id;
    gameError = "";
    await refreshSelectedGame(id);
    connectSocket(id);
    currentView = VIEW.PLAY;
    stopHubPolling();
  }

  function handleSocketMessage(gameId, event) {
    let payload;
    try {
      payload = JSON.parse(event.data);
    } catch (_error) {
      return;
    }
    if (!payload || payload.game_id !== gameId) {
      return;
    }
    if (payload.type === "move" || payload.type === "game_finished") {
      void loadHub();
      if (selectedGameId === gameId) {
        void refreshSelectedGame(gameId);
      }
    }
  }

  const toggleNewGameForm = () => {
    showNewGameForm = !showNewGameForm;
  };

  const handleOpponentChange = (opponentId) => {
    if (opponentId === null || opponentId === undefined) return;
    newGameOpponentId = String(opponentId);
  };

  const handleColorChange = (color) => {
    newGameColor = color === "black" ? "black" : "white";
  };

  const launchGame = async () => {
    if (!currentUser || !isAuthenticated || !newGameOpponentId) {
      return;
    }
    const opponentId = Number(newGameOpponentId);
    const opponent = availableOpponents.find(
      (entry) => entry.id === opponentId,
    );
    if (!opponent) return;
    const payload =
      newGameColor === "white"
        ? {
            white_player_id: currentUser.id,
            black_player_id: opponent.id,
          }
        : {
            white_player_id: opponent.id,
            black_player_id: currentUser.id,
          };
    payload.summary = "Friendly challenge";
    try {
      const created = await createGame(payload, accessToken);
      await loadHub();
      await openGame(created.id);
      showNewGameForm = false;
    } catch (error) {
      hubError =
        error instanceof Error ? error.message : "Unable to create game.";
    }
  };

  const handleBoardMove = async (event) => {
    if (!selectedGame || !isAuthenticated) return;
    const detail =
      event && typeof event === "object" && "detail" in event
        ? (event.detail ?? {})
        : (event ?? {});
    const notation = detail.move?.san;
    const fen = detail.fen;
    if (!notation) return;
    gameError = "";
    try {
      await submitMove(selectedGame.id, { notation, fen }, accessToken);
    } catch (error) {
      gameError =
        error instanceof Error ? error.message : "Move could not be recorded.";
      await refreshSelectedGame(selectedGame.id);
    } finally {
      await loadHub();
    }
  };

  const handleBoardUndo = async () => {
    if (!selectedGame) return;
    await refreshSelectedGame(selectedGame.id);
  };

  const handleResign = async () => {
    if (!selectedGame || !isAuthenticated) return;
    gameError = "";
    try {
      await resignGame(selectedGame.id, accessToken);
    } catch (error) {
      gameError =
        error instanceof Error
          ? error.message
          : "Unable to resign from the game.";
    } finally {
      await refreshSelectedGame(selectedGame.id);
      await loadHub();
    }
  };

  const saveProfile = async () => {
    if (!currentUser || !isAuthenticated) return;
    const avatar = profileDraft.avatarUrl.trim();
    const password = profileDraft.password.trim();
    const payload = {};
    if (avatar !== (currentUser.avatar_url || "")) {
      payload.avatar_url = avatar || null;
    }
    if (password) {
      payload.password = password;
    }
    if (!Object.keys(payload).length) {
      return;
    }
    try {
      const updated = await updateUser(currentUser.id, payload, accessToken);
      currentUser = updated;
      profileDraft = { avatarUrl: updated.avatar_url || "", password: "" };
    } catch (error) {
      hubError =
        error instanceof Error ? error.message : "Failed to update profile.";
    }
  };

  const openProfile = () => {
    currentView = VIEW.PROFILE;
    stopHubPolling();
  };

  const returnToGames = () => {
    currentView = VIEW.GAMES;
    teardownSocket();
    startHubPolling();
    void loadHub();
  };

  const handleProfileFieldChange = (field, value) => {
    profileDraft = { ...profileDraft, [field]: value };
  };

  const logout = () => {
    teardownSocket();
    stopHubPolling();
    isAuthenticated = false;
    accessToken = "";
    currentUser = null;
    rawSummaryIndex = new Map();
    uiSummaryIndex = new Map();
    games = [];
    orderedGames = [];
    selectedGame = null;
    selectedGameId = null;
    availableOpponents = [];
    profileDraft = { avatarUrl: "", password: "" };
    showNewGameForm = false;
    newGameOpponentId = "";
    newGameColor = "white";
    landingError = "";
    hubError = "";
    gameError = "";
    currentView = VIEW.LANDING;
  };

  onDestroy(() => {
    teardownSocket();
    stopHubPolling();
  });

  $: orderedGames = sortGames(games);

  $: if (availableOpponents.length) {
    if (
      !newGameOpponentId ||
      !availableOpponents.some(
        (opponent) => String(opponent.id) === newGameOpponentId,
      )
    ) {
      newGameOpponentId = String(availableOpponents[0].id);
    }
  }

  $: if (!orderedGames.length) {
    selectedGameId = null;
  } else if (
    selectedGameId !== null &&
    !orderedGames.some((game) => game.id === selectedGameId)
  ) {
    selectedGameId = orderedGames[0].id;
  }

  $: if (!isAuthenticated && currentView !== VIEW.LANDING) {
    currentView = VIEW.LANDING;
  }

  $: if (currentView === VIEW.PLAY && (!selectedGame || !isAuthenticated)) {
    currentView = isAuthenticated ? VIEW.GAMES : VIEW.LANDING;
  }

  $: if (isAuthenticated && currentView === VIEW.GAMES) {
    startHubPolling();
  } else if (currentView !== VIEW.GAMES) {
    stopHubPolling();
  }

  $: hubUser = currentUser
    ? {
        id: currentUser.id,
        nickname: currentUser.username,
        avatar: currentUser.avatar_url || fallbackAvatar(currentUser.username),
        rating:
          1200 +
          ((currentUser.games_won ?? 0) - (currentUser.games_lost ?? 0)) * 10,
      }
    : null;
</script>

<div class="app-frame">
  {#if currentView === VIEW.LANDING}
    <LandingView
      showcaseFen={SHOWCASE_FEN}
      error={landingError}
      isLoading={isLandingLoading}
      onPlay={performLogin}
      onAdminLogin={performLogin}
    />
  {:else if currentView === VIEW.GAMES && isAuthenticated}
    {#if hubError}
      <p class="notice" role="alert">{hubError}</p>
    {/if}
    <GameHubView
      user={hubUser}
      games={orderedGames}
      {selectedGameId}
      {showNewGameForm}
      {availableOpponents}
      {newGameOpponentId}
      {newGameColor}
      {formatTime}
      {gameStatusLabel}
      onOpenGame={openGame}
      onToggleNewGameForm={toggleNewGameForm}
      onChangeOpponent={handleOpponentChange}
      onChangeColor={handleColorChange}
      onLaunchGame={launchGame}
      onOpenProfile={openProfile}
      onLogout={logout}
      onRefreshGames={() => {
        void loadHub();
      }}
    />
  {:else if currentView === VIEW.PLAY && isAuthenticated && selectedGame}
    {#if gameError}
      <p class="notice" role="alert">{gameError}</p>
    {/if}
    <GamePlayView
      game={selectedGame}
      {formatTime}
      {gameStatusLabel}
      {colorLabel}
      onMove={handleBoardMove}
      onUndo={handleBoardUndo}
      onResign={handleResign}
      onBack={returnToGames}
      onLogout={logout}
    />
  {:else if currentView === VIEW.PROFILE && isAuthenticated}
    <ProfileView
      user={currentUser}
      {profileDraft}
      gameCount={orderedGames.length}
      onFieldChange={handleProfileFieldChange}
      onSave={saveProfile}
      onBack={returnToGames}
      onLogout={logout}
    />
  {/if}
</div>

<style>
  .app-frame {
    width: 100%;
    display: flex;
    justify-content: center;
  }

  .notice {
    margin-bottom: 1rem;
    background: rgba(239, 68, 68, 0.18);
    border: 1px solid rgba(239, 68, 68, 0.35);
    color: #fecaca;
    padding: 0.65rem 1rem;
    border-radius: 12px;
    font-size: 0.9rem;
  }
</style>
