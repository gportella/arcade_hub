<script>
  import { onDestroy, onMount } from "svelte";
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
    requestEngineMove,
    updateUser,
    resignGame,
    connectToGame,
  } from "./lib/api/client";
  import {
    persistToken,
    loadStoredToken,
    clearStoredToken,
  } from "./lib/sessionStorage";
  import { normalizeFen } from "./lib/fen";

  const VIEW = Object.freeze({
    LANDING: "landing",
    GAMES: "games",
    PLAY: "play",
    PROFILE: "profile",
  });

  // --- Simple router (hash-based) ---

  function routeFor(view, params = {}) {
    if (view === VIEW.LANDING) return "#/login";
    if (view === VIEW.GAMES) return "#/games";
    if (view === VIEW.PROFILE) return "#/profile";
    if (view === VIEW.PLAY) {
      const id = params.id ?? selectedGameId;
      return id ? `#/game/${id}` : "#/games";
    }
    return "#/login";
  }

  function parseRouteFromURL() {
    const hash = location.hash || "#/login";
    const parts = hash.slice(1).split("/").filter(Boolean); // remove '#', split
    const [segment, arg] = parts;

    if (segment === "games") return { view: VIEW.GAMES, params: {} };
    if (segment === "profile") return { view: VIEW.PROFILE, params: {} };
    if (segment === "game" && arg) {
      const idNum = Number(arg);
      return {
        view: VIEW.PLAY,
        params: { id: Number.isFinite(idNum) ? idNum : arg },
      };
    }
    return { view: VIEW.LANDING, params: {} };
  }

  function navigateTo(view, params = {}) {
    const url = routeFor(view, params);
    if (location.hash !== url) {
      // Changing the hash creates a browser history entry
      location.hash = url;
    } else {
      // If it's the same route, apply immediately
      void applyFromHash();
    }
  }

  async function applyFromHash() {
    const { view, params } = parseRouteFromURL();

    // Block protected routes when not authenticated
    if (!isAuthenticated && view !== VIEW.LANDING) {
      currentView = VIEW.LANDING;
      return;
    }

    if (view === VIEW.GAMES) {
      currentView = VIEW.GAMES;
      teardownSocket();
      startHubPolling();
      void loadHub();
      return;
    }

    if (view === VIEW.PROFILE) {
      currentView = VIEW.PROFILE;
      stopHubPolling();
      return;
    }

    if (view === VIEW.PLAY) {
      const id = params.id ?? selectedGameId;
      if (!id) {
        currentView = VIEW.GAMES;
        return;
      }
      selectedGameId = id;
      gameError = "";
      await refreshSelectedGame(id); // load before switching to avoid reactive fallback
      connectSocket(id);
      stopHubPolling();
      currentView = VIEW.PLAY;
      return;
    }

    currentView = VIEW.LANDING;
  }
  // --- END Simple router (hash-based) ---

  const SHOWCASE_FEN =
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

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
  let engineMovePending = false;
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
        isEngine: false,
        engineKey: null,
      };
    }
    const nickname = player.display_name || player.username;
    return {
      id: player.id,
      nickname,
      avatar:
        player.avatar_url ||
        fallbackAvatar(nickname || player.username || "player"),
      title: player.is_engine ? "Engine" : "",
      isEngine: Boolean(player.is_engine),
      engineKey: player.engine_key ?? null,
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

  function appendPgn(existing, moveNumber, notation) {
    const history = existing?.trim() ?? "";
    if (!notation) return history;
    const moveNo = Number.isFinite(moveNumber) ? Number(moveNumber) : 0;
    const turn = Math.max(1, Math.floor((moveNo + 1) / 2));
    const isWhiteMove = moveNo % 2 === 1;
    let snippet;
    if (isWhiteMove) {
      snippet = `${turn}. ${notation}`;
    } else {
      snippet = notation;
      if (!history) {
        snippet = `${turn}... ${notation}`;
      }
    }
    return history ? `${history} ${snippet}`.trim() : snippet;
  }

  function applySelfMoveUpdate(payload) {
    if (!selectedGame) return;
    const moveNumber = payload.move_number ?? selectedGame.movesCount + 1;
    const notation = payload.notation ?? "";
    const fen = normalizeFen(payload.fen) ?? selectedGame.fen;
    const playedAt = payload.played_at ?? new Date().toISOString();
    const turn = parseActiveColor(fen);
    const moves = Array.isArray(selectedGame.moves)
      ? [
          ...selectedGame.moves,
          {
            move_number: moveNumber,
            notation,
            fen,
            player_id: payload.player_id,
            played_at: playedAt,
          },
        ]
      : [
          {
            move_number: moveNumber,
            notation,
            fen,
            player_id: payload.player_id,
            played_at: playedAt,
          },
        ];
    selectedGame = {
      ...selectedGame,
      fen,
      turn,
      movesCount: moveNumber,
      lastUpdated: playedAt,
      pgn: appendPgn(selectedGame.pgn, moveNumber, notation),
      moves,
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
      const token = await login(username, password);
      persistToken(token);
      accessToken = token;
      const loaded = await loadHub();
      if (!loaded) {
        accessToken = "";
        persistToken("");
        landingError = hubError || "Unable to finish signing in.";
        isAuthenticated = false;
        return;
      }
      isAuthenticated = true;
      currentView = VIEW.GAMES;
      navigateTo(VIEW.GAMES);
      startHubPolling();
    } catch (error) {
      landingError =
        error instanceof Error ? error.message : "Unable to sign in.";
      accessToken = "";
      isAuthenticated = false;
      persistToken("");
    } finally {
      isLandingLoading = false;
    }
  }

  async function loadHub() {
    hubError = "";
    if (!accessToken) return false;
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
      availableOpponents = Array.isArray(hub.opponents)
        ? hub.opponents.map(toOpponent).sort((a, b) => {
            if (a.isEngine !== b.isEngine) {
              return a.isEngine ? 1 : -1;
            }
            return a.nickname.localeCompare(b.nickname);
          })
        : [];
      profileDraft = {
        avatarUrl: hub.user.avatar_url || "",
        password: "",
      };
      return true;
    } catch (error) {
      hubError =
        error instanceof Error ? error.message : "Failed to load games.";
      return false;
    }
  }

  async function refreshSelectedGame(gameId) {
    if (!accessToken) return;
    gameError = "";
    try {
      const detail = await fetchGameDetail(gameId, accessToken);
      selectedGame = mapGameDetail(detail);
      await maybeTriggerEngineMove(selectedGame);
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
    stopHubPolling();
    currentView = VIEW.PLAY;
    navigateTo(VIEW.PLAY, { id });
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
    const isMove = payload.type === "move";
    const isFinished = payload.type === "game_finished";
    if (!isMove && !isFinished) {
      return;
    }
    void loadHub();
    if (selectedGameId !== gameId) {
      return;
    }
    if (isMove) {
      if (payload.player_id === currentUser?.id) {
        applySelfMoveUpdate(payload);
        void maybeTriggerEngineMove(selectedGame);
        return;
      }
      void refreshSelectedGame(gameId);
      return;
    }
    void refreshSelectedGame(gameId);
  }

  async function maybeTriggerEngineMove(game) {
    if (!game || !isAuthenticated || !accessToken) return;
    if (!game.opponent?.isEngine) return;
    if (game.status === "completed" || game.status === "aborted") return;
    if (game.turn === game.yourColor) return;
    if (engineMovePending) return;
    const engineKey = game.opponent.engineKey;
    if (!engineKey) return;
    engineMovePending = true;
    try {
      await requestEngineMove(game.id, { engine_key: engineKey }, accessToken);
      if (!socket) {
        const detail = await fetchGameDetail(game.id, accessToken);
        selectedGame = mapGameDetail(detail);
        await loadHub();
      }
    } catch (error) {
      const rawMessage =
        error instanceof Error ? error.message : "Engine move request failed.";
      if (rawMessage.includes("Engine binary")) {
        gameError =
          "Chess engine unavailable. Install the required host binary (e.g. skaks) and retry.";
      } else if (rawMessage.includes("Engine terminated")) {
        gameError =
          "Chess engine terminated unexpectedly. Please try again soon.";
      } else {
        gameError = rawMessage;
      }
    } finally {
      engineMovePending = false;
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
    payload.summary = opponent.isEngine
      ? `Engine match vs ${opponent.nickname}`
      : "Friendly challenge";
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
    const normalizedFen = normalizeFen(fen) ?? fen;
    if (!notation) return;
    gameError = "";
    try {
      await submitMove(
        selectedGame.id,
        { notation, fen: normalizedFen },
        accessToken,
      );
      if (!socket) {
        await refreshSelectedGame(selectedGame.id);
        await loadHub();
      }
    } catch (error) {
      gameError =
        error instanceof Error ? error.message : "Move could not be recorded.";
      await refreshSelectedGame(selectedGame.id);
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
    navigateTo(VIEW.PROFILE);
  };

  const returnToGames = () => {
    currentView = VIEW.GAMES;
    teardownSocket();
    startHubPolling();
    void loadHub();
    navigateTo(VIEW.GAMES);
  };

  const handleProfileFieldChange = (field, value) => {
    profileDraft = { ...profileDraft, [field]: value };
  };

  const logout = () => {
    teardownSocket();
    stopHubPolling();
    isAuthenticated = false;
    accessToken = "";
    clearStoredToken();
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
    navigateTo(VIEW.LANDING);
  };

  async function restoreSession(token) {
    accessToken = token;
    const loaded = await loadHub();
    if (!loaded) {
      accessToken = "";
      clearStoredToken();
      isAuthenticated = false;
      currentView = VIEW.LANDING;
      return;
    }
    isAuthenticated = true;
    currentView = VIEW.GAMES;
    navigateTo(VIEW.GAMES);
    startHubPolling();
  }

  onMount(() => {
    const storedToken = loadStoredToken();
    if (storedToken) {
      void restoreSession(storedToken).then(() => {
        // Go to the hash route if present, otherwise default to games
        if (location.hash) {
          void applyFromHash();
        } else {
          navigateTo(VIEW.GAMES);
        }
      });
    } else {
      navigateTo(VIEW.LANDING);
    }

    window.addEventListener("hashchange", applyFromHash);
  });

  onDestroy(() => {
    teardownSocket();
    stopHubPolling();
    window.removeEventListener("hashchange", applyFromHash);
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
