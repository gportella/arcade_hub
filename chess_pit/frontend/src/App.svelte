<script>
  import { onDestroy, onMount } from "svelte";
  import { get } from "svelte/store";
  import LandingView from "./lib/views/LandingView.svelte";
  import GameHubView from "./lib/views/GameHubView.svelte";
  import AdminUsersView from "./lib/views/AdminUsersView.svelte";
  import GamePlayView from "./lib/views/GamePlayView.svelte";
  import ProfileView from "./lib/views/ProfileView.svelte";
  import PuzzleTrainerView from "./lib/views/PuzzleTrainerView.svelte";

  import {
    login,
    fetchHubOverview,
    fetchGameDetail,
    createGame,
    submitMove,
    requestEngineMove,
    analyzeGame,
    analyzeGameSequence,
    updateUser,
    resignGame,
    connectToGame,
    fetchAdminUsers,
    fetchAdminUserGames,
    fetchLeaderboard,
  } from "./lib/api/client";
  import {
    persistToken,
    loadStoredToken,
    clearStoredToken,
  } from "./lib/sessionStorage";
  import { normalizeFen } from "./lib/fen";
  import {
    detectInitialLocale,
    locale as localeStore,
    setLocale,
    t,
  } from "./lib/i18n";

  const VIEW = Object.freeze({
    LANDING: "landing",
    GAMES: "games",
    PLAY: "play",
    PROFILE: "profile",
    PUZZLES: "puzzles",
    ADMIN: "admin",
  });

  // --- Simple router (hash-based) ---

  function routeFor(view, params = {}) {
    if (view === VIEW.LANDING) return "#/login";
    if (view === VIEW.GAMES) return "#/games";
    if (view === VIEW.PROFILE) return "#/profile";
    if (view === VIEW.PUZZLES) return "#/puzzles";
    if (view === VIEW.ADMIN) return "#/admin";
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
    if (segment === "puzzles") return { view: VIEW.PUZZLES, params: {} };
    if (segment === "admin") return { view: VIEW.ADMIN, params: {} };
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

    if (view === VIEW.PUZZLES) {
      currentView = VIEW.PUZZLES;
      teardownSocket();
      stopHubPolling();
      return;
    }

    if (view === VIEW.ADMIN) {
      if (!isAuthenticated || !currentUser?.is_admin) {
        currentView = isAuthenticated ? VIEW.GAMES : VIEW.LANDING;
        return;
      }
      currentView = VIEW.ADMIN;
      teardownSocket();
      stopHubPolling();
      await loadAdminUsers();
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

  const HUB_POLL_INTERVAL = 15000;
  const MAX_INITIAL_MINUTES = 1440;
  const MAX_INCREMENT_SECONDS = 600;
  const ENGINE_MODE_DEPTH = "depth";
  const ENGINE_MODE_TIME = "time";
  const DEFAULT_TIME_MINUTES = 10;
  const DEFAULT_INCREMENT_SECONDS = 5;

  /** @type {"landing" | "games" | "play" | "profile" | "puzzles" | "admin"} */
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
  let newGameDepth = "";
  let newGameInitialMinutes = "";
  let newGameIncrementSeconds = "";
  let newGameEngineMode = ENGINE_MODE_TIME;
  let availableOpponents = [];
  let availableEngines = [];
  let lastDepthOpponentId = null;
  let profileDraft = { avatarUrl: "", password: "" };
  let landingError = "";
  let isLandingLoading = false;
  let hubError = "";
  let gameError = "";
  let socket = null;
  let hubUser = null;
  let hubPollTimer = null;
  let engineMovePending = false;
  let analysisResult = null;
  let analysisError = "";
  let isAnalysisLoading = false;
  let analysisFetchedAt = null;
  let adminUsers = [];
  let adminError = "";
  let isAdminLoading = false;
  let adminSelectedUserId = null;
  let adminUserGames = [];
  let isAdminGamesLoading = false;
  let adminGamesError = "";
  let adminGameContext = null;
  let selectedGameOrigin = "hub";
  let leaderboard = [];
  let isLeaderboardLoading = false;
  let leaderboardError = "";
  let leaderboardLoaded = false;
  let analysisEngineSpec = null;
  let analysisSteps = [];

  function resetAnalysis() {
    analysisResult = null;
    analysisError = "";
    isAnalysisLoading = false;
    analysisFetchedAt = null;
    analysisSteps = [];
  }

  function resolveTimeUnit(localeCode, unit, count) {
    const locale = localeCode === "ca" ? "ca" : "en";
    if (unit === "minute") {
      if (locale === "ca") {
        return count === 1 ? "minut" : "minuts";
      }
      return "min";
    }
    if (unit === "hour") {
      if (locale === "ca") {
        return count === 1 ? "hora" : "hores";
      }
      return count === 1 ? "hr" : "hrs";
    }
    if (unit === "day") {
      if (locale === "ca") {
        return count === 1 ? "dia" : "dies";
      }
      return count === 1 ? "day" : "days";
    }
    return "";
  }

  function resolveDateLocale(localeCode) {
    if (localeCode === "ca") {
      return "ca-ES";
    }
    return "en-US";
  }

  const tr = (key, params) => {
    const translator = get(t);
    return translator(key, params);
  };

  function fallbackAvatar(username = "player") {
    const slug = encodeURIComponent(username || "player");
    return `https://avatar.vercel.sh/${slug}`;
  }

  function findOpponentById(opponentId) {
    if (opponentId === null || opponentId === undefined) {
      return null;
    }
    const numericId = Number(opponentId);
    return availableOpponents.find((entry) => entry.id === numericId) ?? null;
  }

  function findEngineSpec(engineKey, specs = availableEngines) {
    if (!engineKey) {
      return null;
    }
    if (!Array.isArray(specs) || !specs.length) {
      return null;
    }
    return specs.find((engine) => engine.key === engineKey) ?? null;
  }

  function defaultDepthForEngine(engineKey, specs = availableEngines) {
    const spec = findEngineSpec(engineKey, specs);
    const depth = spec?.default_depth;
    const limit =
      typeof spec?.max_depth === "number" && Number.isFinite(spec.max_depth)
        ? spec.max_depth
        : 64;
    if (typeof depth === "number" && Number.isFinite(depth)) {
      return Math.max(1, Math.min(limit, Math.round(depth)));
    }
    return null;
  }

  function normalizeEngineDepth(depth, engineKey, specs = availableEngines) {
    if (depth === null || depth === undefined || depth === "") {
      return null;
    }
    const spec = findEngineSpec(engineKey, specs);
    const limit =
      typeof spec?.max_depth === "number" && Number.isFinite(spec.max_depth)
        ? spec.max_depth
        : 64;
    return clampDepthValue(depth, limit);
  }

  function sanitizeDepthInput(value) {
    if (value === null || value === undefined) {
      return "";
    }
    const text = String(value).trim();
    if (!text) {
      return "";
    }
    if (!/^[0-9]+$/.test(text)) {
      const digits = text.replace(/[^0-9]/g, "");
      return digits;
    }
    return text;
  }

  function clampDepthValue(value, limit = 64) {
    if (value === null || value === undefined || value === "") {
      return null;
    }
    const numeric = Number.parseInt(String(value).trim(), 10);
    if (!Number.isFinite(numeric)) {
      return null;
    }
    const limitNumber = Number(limit);
    const upperBound = Number.isFinite(limitNumber)
      ? Math.max(1, Math.min(64, Math.round(limitNumber)))
      : 64;
    return Math.max(1, Math.min(upperBound, Math.round(numeric)));
  }

  function sanitizeNumericInput(value) {
    if (value === null || value === undefined) {
      return "";
    }
    const text = String(value).trim();
    if (!text) {
      return "";
    }
    if (!/^[0-9]+$/.test(text)) {
      return text.replace(/[^0-9]/g, "");
    }
    return text;
  }

  function clampIntegerValue(value, { min = 0, max = Number.MAX_SAFE_INTEGER } = {}) {
    if (value === null || value === undefined || value === "") {
      return null;
    }
    const numeric = Number.parseInt(String(value).trim(), 10);
    if (!Number.isFinite(numeric)) {
      return null;
    }
    return Math.max(min, Math.min(max, numeric));
  }

  function normalizeInitialSeconds(value) {
    const sanitized = sanitizeNumericInput(value);
    if (!sanitized) {
      return null;
    }
    const clamped = clampIntegerValue(sanitized, {
      min: 0,
      max: MAX_INITIAL_MINUTES,
    });
    if (clamped === null) {
      return null;
    }
    if (clamped <= 0) {
      return null;
    }
    return clamped * 60;
  }

  function normalizeIncrementSeconds(value) {
    const sanitized = sanitizeNumericInput(value);
    if (!sanitized) {
      return null;
    }
    return clampIntegerValue(sanitized, {
      min: 0,
      max: MAX_INCREMENT_SECONDS,
    });
  }

  function ensureTimeDefaults(options = {}) {
    const allowUntimed = Boolean(options.allowUntimed);
    if (allowUntimed) {
      newGameInitialMinutes = "";
      newGameIncrementSeconds = "";
      return;
    }
    if (!newGameInitialMinutes) {
      newGameInitialMinutes = String(DEFAULT_TIME_MINUTES);
    }
    if (!newGameIncrementSeconds) {
      newGameIncrementSeconds = String(DEFAULT_INCREMENT_SECONDS);
    }
  }

  function syncOpponentPreferences(opponentId, { forceReset = false } = {}) {
    const opponent = findOpponentById(opponentId);
    if (!opponent) {
      newGameEngineMode = ENGINE_MODE_TIME;
      ensureTimeDefaults({ allowUntimed: true });
      newGameDepth = "";
      return;
    }
    if (opponent.isEngine) {
      if (
        forceReset ||
        (newGameEngineMode !== ENGINE_MODE_DEPTH && newGameEngineMode !== ENGINE_MODE_TIME)
      ) {
        newGameEngineMode = ENGINE_MODE_DEPTH;
      }
      if (newGameEngineMode === ENGINE_MODE_DEPTH) {
        syncNewGameDepth(opponentId, { forceReset });
        newGameInitialMinutes = "";
        newGameIncrementSeconds = "";
      } else {
        ensureTimeDefaults();
        newGameDepth = "";
      }
      return;
    }
    newGameEngineMode = ENGINE_MODE_TIME;
    if (forceReset) {
      ensureTimeDefaults({ allowUntimed: true });
    }
    newGameDepth = "";
  }

  function syncNewGameDepth(opponentId, { forceReset = false } = {}) {
    const opponent = findOpponentById(opponentId);
    if (!opponent || !opponent.isEngine) {
      newGameDepth = "";
      lastDepthOpponentId = opponent ? opponent.id : null;
      return;
    }
    if (newGameEngineMode !== ENGINE_MODE_DEPTH) {
      newGameDepth = "";
      lastDepthOpponentId = opponent.id;
      return;
    }
    const shouldReset = forceReset || lastDepthOpponentId !== opponent.id || !newGameDepth;
    if (shouldReset) {
      const defaultDepth = defaultDepthForEngine(opponent.engineKey);
      newGameDepth = defaultDepth !== null ? String(defaultDepth) : "";
    }
    lastDepthOpponentId = opponent.id;
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
        nickname: "",
        isUnknown: true,
        avatar: fallbackAvatar("unknown"),
        isEngine: false,
        engineKey: null,
        rating: null,
      };
    }
    const nickname = player.display_name || player.username || "";
    const avatarSource =
      player.avatar_url ||
      fallbackAvatar(nickname || player.username || "player");
    return {
      id: player.id,
      nickname,
      isUnknown: !nickname,
      avatar: avatarSource,
      isEngine: Boolean(player.is_engine),
      engineKey: player.engine_key ?? null,
      rating:
        typeof player.rating === "number" && Number.isFinite(player.rating)
          ? Math.round(player.rating)
          : null,
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
    const activeLocale = get(localeStore);
    const localeCode = activeLocale || "en";
    const target = new Date(iso);
    const diff = Date.now() - target.getTime();
    const minute = 60000;
    const hour = 60 * minute;
    const day = 24 * hour;

    if (diff < minute) {
      return tr("time.moments");
    }
    if (diff < hour) {
      const value = Math.round(diff / minute);
      const unit = resolveTimeUnit(localeCode, "minute", value);
      return tr("time.minutes", { count: value, unit });
    }
    if (diff < day) {
      const value = Math.round(diff / hour);
      const unit = resolveTimeUnit(localeCode, "hour", value);
      return tr("time.hours", { count: value, unit });
    }
    if (diff < 7 * day) {
      const value = Math.round(diff / day);
      const unit = resolveTimeUnit(localeCode, "day", value);
      return tr("time.days", { count: value, unit });
    }
    return target.toLocaleDateString(resolveDateLocale(localeCode));
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
    const summaryText = summary.summary?.trim() ?? "";
    const normalizeDelta = (value) =>
      typeof value === "number" && Number.isFinite(value) ? Math.round(value) : 0;
    const whiteRatingDelta = normalizeDelta(summary.white_rating_delta);
    const blackRatingDelta = normalizeDelta(summary.black_rating_delta);
    const initialSeconds =
      typeof summary.time_control_initial_seconds === "number" &&
      Number.isFinite(summary.time_control_initial_seconds)
        ? summary.time_control_initial_seconds
        : null;
    const incrementSeconds =
      typeof summary.time_control_increment_seconds === "number" &&
      Number.isFinite(summary.time_control_increment_seconds)
        ? summary.time_control_increment_seconds
        : null;
    const whiteRemaining =
      typeof summary.white_time_remaining_seconds === "number" &&
      Number.isFinite(summary.white_time_remaining_seconds)
        ? summary.white_time_remaining_seconds
        : null;
    const blackRemaining =
      typeof summary.black_time_remaining_seconds === "number" &&
      Number.isFinite(summary.black_time_remaining_seconds)
        ? summary.black_time_remaining_seconds
        : null;
    const turnStartTime = summary.turn_start_time ?? null;
    const yourColor = summary.your_color || "white";
    const ratingDelta =
      typeof summary.your_rating_delta === "number" && Number.isFinite(summary.your_rating_delta)
        ? Math.round(summary.your_rating_delta)
        : yourColor === "white"
        ? whiteRatingDelta
        : blackRatingDelta;
    return {
      id: summary.id,
      opponent,
      status: summary.status,
      result: summary.result,
      resultDisplay: formatResult(summary.result),
      summary: summaryText,
      hasCustomSummary: Boolean(summaryText),
      fen,
      initialFen: summary.initial_fen,
      pgn: summary.pgn,
      yourColor,
      turn: summary.turn || parseActiveColor(fen),
      lastUpdated,
      startedAt: summary.started_at,
      movesCount: summary.moves_count,
      currentPositionHash: summary.current_position_hash,
      engineDepth: normalizeEngineDepth(summary.engine_depth, opponent.engineKey),
      timeControlInitialSeconds: initialSeconds,
      timeControlIncrementSeconds: incrementSeconds,
      whiteTimeRemainingSeconds: whiteRemaining,
      blackTimeRemainingSeconds: blackRemaining,
      turnStartTime,
      whiteRatingDelta,
      blackRatingDelta,
      ratingDelta,
    };
  }

  function mapGameDetail(detail) {
    const summaryUi = uiSummaryIndex.get(detail.id);
    const summaryRaw = rawSummaryIndex.get(detail.id);
    const fen = detail.current_fen || detail.initial_fen;
    const opponent = summaryUi?.opponent || toOpponent(summaryRaw?.opponent);
    const engineKey = opponent?.engineKey ?? summaryRaw?.opponent?.engine_key ?? null;
    const yourColor =
      summaryUi?.yourColor ||
      (currentUser && detail.white_player_id === currentUser.id
        ? "white"
        : "black");
    const turn = parseActiveColor(fen);
    const detailSummary = detail.summary?.trim();
    const initialSeconds =
      typeof detail.time_control_initial_seconds === "number" &&
      Number.isFinite(detail.time_control_initial_seconds)
        ? detail.time_control_initial_seconds
        : summaryUi?.timeControlInitialSeconds ?? null;
    const incrementSeconds =
      typeof detail.time_control_increment_seconds === "number" &&
      Number.isFinite(detail.time_control_increment_seconds)
        ? detail.time_control_increment_seconds
        : summaryUi?.timeControlIncrementSeconds ?? null;
    const whiteRemaining =
      typeof detail.white_time_remaining_seconds === "number" &&
      Number.isFinite(detail.white_time_remaining_seconds)
        ? detail.white_time_remaining_seconds
        : summaryUi?.whiteTimeRemainingSeconds ?? null;
    const blackRemaining =
      typeof detail.black_time_remaining_seconds === "number" &&
      Number.isFinite(detail.black_time_remaining_seconds)
        ? detail.black_time_remaining_seconds
        : summaryUi?.blackTimeRemainingSeconds ?? null;
    const turnStartTime = detail.turn_start_time ?? summaryUi?.turnStartTime ?? null;
    const normalizeDelta = (value) =>
      typeof value === "number" && Number.isFinite(value) ? Math.round(value) : 0;
    const whiteRatingDelta = normalizeDelta(
      detail.white_rating_delta ?? summaryUi?.whiteRatingDelta ?? summaryRaw?.white_rating_delta,
    );
    const blackRatingDelta = normalizeDelta(
      detail.black_rating_delta ?? summaryUi?.blackRatingDelta ?? summaryRaw?.black_rating_delta,
    );
    const ratingDelta = yourColor === "white" ? whiteRatingDelta : blackRatingDelta;
    return {
      id: detail.id,
      opponent,
      status: detail.status,
      result: detail.result,
      resultDisplay: formatResult(detail.result),
      summary:
        detailSummary ?? summaryRaw?.summary?.trim() ?? summaryUi?.summary ?? "",
      hasCustomSummary:
        Boolean(detailSummary) || Boolean(summaryRaw?.summary?.trim()),
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
      engineDepth:
        normalizeEngineDepth(detail.engine_depth, engineKey) ??
        normalizeEngineDepth(summaryUi?.engineDepth, engineKey) ??
        null,
      timeControlInitialSeconds: initialSeconds,
      timeControlIncrementSeconds: incrementSeconds,
      whiteTimeRemainingSeconds: whiteRemaining,
      blackTimeRemainingSeconds: blackRemaining,
      turnStartTime,
      whiteRatingDelta,
      blackRatingDelta,
      ratingDelta,
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
    const initialSeconds =
      typeof payload.time_control_initial_seconds === "number" &&
      Number.isFinite(payload.time_control_initial_seconds)
        ? payload.time_control_initial_seconds
        : selectedGame.timeControlInitialSeconds ?? null;
    const incrementSeconds =
      typeof payload.time_control_increment_seconds === "number" &&
      Number.isFinite(payload.time_control_increment_seconds)
        ? payload.time_control_increment_seconds
        : selectedGame.timeControlIncrementSeconds ?? null;
    const whiteRemaining =
      typeof payload.white_time_remaining_seconds === "number" &&
      Number.isFinite(payload.white_time_remaining_seconds)
        ? payload.white_time_remaining_seconds
        : selectedGame.whiteTimeRemainingSeconds ?? null;
    const blackRemaining =
      typeof payload.black_time_remaining_seconds === "number" &&
      Number.isFinite(payload.black_time_remaining_seconds)
        ? payload.black_time_remaining_seconds
        : selectedGame.blackTimeRemainingSeconds ?? null;
    const turnStartTime = payload.turn_start_time ?? selectedGame.turnStartTime ?? null;
    selectedGame = {
      ...selectedGame,
      fen,
      turn,
      movesCount: moveNumber,
      lastUpdated: playedAt,
      pgn: appendPgn(selectedGame.pgn, moveNumber, notation),
      moves,
      timeControlInitialSeconds: initialSeconds,
      timeControlIncrementSeconds: incrementSeconds,
      whiteTimeRemainingSeconds: whiteRemaining,
      blackTimeRemainingSeconds: blackRemaining,
      turnStartTime,
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
    if (!game) {
      return "";
    }
    if (game.status === "completed") {
      return game.resultDisplay
        ? tr("game.status.finalWithResult", {
            result: game.resultDisplay,
          })
        : tr("game.status.final");
    }
    if (game.status === "aborted") {
      return tr("game.status.aborted");
    }
    if (game.turn === game.yourColor) {
      return tr("game.status.yourMove");
    }
    return tr("game.status.opponentMove");
  };

  async function performLogin(credentials) {
    const username = credentials?.username?.trim();
    const password = credentials?.password?.trim();
    landingError = "";
    if (!username || !password) {
      landingError = tr("landing.form.error.required");
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
        landingError = hubError || tr("errors.loginIncomplete");
        isAuthenticated = false;
        return;
      }
      isAuthenticated = true;
      currentView = VIEW.GAMES;
      navigateTo(VIEW.GAMES);
      startHubPolling();
    } catch (error) {
      const message = error instanceof Error ? error.message : "";
      landingError = message || tr("errors.login");
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
      availableEngines = Array.isArray(hub.engines)
        ? hub.engines.map((engine) => {
            const maxDepth =
              typeof engine.max_depth === "number" && Number.isFinite(engine.max_depth)
                ? Math.max(1, Math.min(64, Math.round(engine.max_depth)))
                : null;
            const limit = maxDepth ?? 64;
            const defaultDepth =
              typeof engine.default_depth === "number" && Number.isFinite(engine.default_depth)
                ? Math.max(1, Math.min(limit, Math.round(engine.default_depth)))
                : null;
            return {
              key: engine.key,
              name: engine.name,
              default_depth: defaultDepth,
              max_depth: maxDepth,
            };
          })
        : [];
      availableOpponents = Array.isArray(hub.opponents)
        ? hub.opponents.map(toOpponent).sort((a, b) => {
            if (a.isEngine !== b.isEngine) {
              return a.isEngine ? 1 : -1;
            }
            return a.nickname.localeCompare(b.nickname);
          })
        : [];
      rawSummaryIndex = new Map();
      uiSummaryIndex = new Map();
      const hubSummaries = Array.isArray(hub.games) ? hub.games : [];
      if (!Array.isArray(hub.games) && hub?.games != null) {
        console.warn("Hub payload provided non-array games data", hub.games);
      }
      for (const summary of hubSummaries) {
        rawSummaryIndex.set(summary.id, summary);
        uiSummaryIndex.set(summary.id, mapGameSummary(summary));
      }
      games = Array.from(uiSummaryIndex.values());
      profileDraft = {
        avatarUrl: hub.user.avatar_url || "",
        password: "",
      };
      return true;
    } catch (error) {
      const message = error instanceof Error ? error.message : "";
      hubError = message || tr("errors.loadHub");
      return false;
    }
  }

  async function loadAdminUsers() {
    if (!accessToken || !isAuthenticated || !currentUser?.is_admin) {
      adminUsers = [];
      adminError = "";
      adminSelectedUserId = null;
      adminUserGames = [];
      adminGamesError = "";
      isAdminGamesLoading = false;
      return;
    }
    isAdminLoading = true;
    adminError = "";
    try {
      const payload = await fetchAdminUsers(accessToken);
      const fetched = Array.isArray(payload) ? payload : [];
      adminUsers = fetched;
      if (
        adminSelectedUserId &&
        !fetched.some((entry) => entry.id === adminSelectedUserId)
      ) {
        adminSelectedUserId = null;
        adminUserGames = [];
      }
      if (!adminSelectedUserId && fetched.length) {
        adminSelectedUserId = fetched[0].id;
        adminGameContext = null;
        await loadAdminUserGames(adminSelectedUserId, { force: true });
      } else if (adminSelectedUserId) {
        void loadAdminUserGames(adminSelectedUserId, { force: true });
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "";
      adminError = message || tr("errors.loadAdminUsers");
      adminUsers = [];
    } finally {
      isAdminLoading = false;
    }
  }

  function buildAdminPlayerProfile({ id, username, rating }) {
    const rosterEntry = adminUsers.find((entry) => entry.id === id);
    const resolvedName = username || rosterEntry?.username || "";
    const avatarSource = rosterEntry?.avatar_url || fallbackAvatar(resolvedName || "player");
    return {
      id,
      username: resolvedName,
      rating: rating ?? rosterEntry?.rating ?? null,
      avatar: avatarSource,
      isEngine: Boolean(rosterEntry?.is_engine),
    };
  }

  function makeSpectatorOpponent(profile) {
    if (!profile) {
      return {
        id: 0,
        nickname: "",
        isUnknown: true,
        avatar: fallbackAvatar("unknown"),
        isEngine: false,
        engineKey: null,
        rating: null,
      };
    }
    const name = profile.username || "";
    return {
      id: profile.id ?? 0,
      nickname: name,
      isUnknown: !name,
      avatar: profile.avatar || fallbackAvatar(name || "player"),
      isEngine: Boolean(profile.isEngine),
      engineKey: null,
      rating:
        typeof profile.rating === "number" && Number.isFinite(profile.rating)
          ? Math.round(profile.rating)
          : null,
    };
  }

  async function loadAdminUserGames(userId, { force = false } = {}) {
    if (!userId) {
      adminUserGames = [];
      adminGamesError = "";
      return;
    }
    if (!accessToken || !isAuthenticated || !currentUser?.is_admin) {
      return;
    }
    if (
      !force &&
      adminSelectedUserId === userId &&
      adminUserGames.length &&
      !adminGamesError
    ) {
      return;
    }
    isAdminGamesLoading = true;
    adminGamesError = "";
    try {
      const payload = await fetchAdminUserGames(userId, accessToken);
      adminUserGames = Array.isArray(payload) ? payload : [];
    } catch (error) {
      const message = error instanceof Error ? error.message : "";
      adminGamesError = message || tr("errors.loadAdminGames");
      adminUserGames = [];
    } finally {
      isAdminGamesLoading = false;
    }
  }

  async function selectAdminUser(userId) {
    if (!isAuthenticated || !currentUser?.is_admin) {
      return;
    }
    const sameSelection = userId === adminSelectedUserId;
    adminGameContext = null;
    adminSelectedUserId = userId;
    if (!userId) {
      adminUserGames = [];
      adminGamesError = "";
      return;
    }
    await loadAdminUserGames(userId, { force: !sameSelection });
  }

  async function analyzeAdminGame(gameSummary) {
    if (!gameSummary || !isAuthenticated || !currentUser?.is_admin) {
      return;
    }
    const whiteProfile = buildAdminPlayerProfile({
      id: gameSummary.white_player_id,
      username: gameSummary.white_player_username,
      rating: gameSummary.white_player_rating,
    });
    const blackProfile = buildAdminPlayerProfile({
      id: gameSummary.black_player_id,
      username: gameSummary.black_player_username,
      rating: gameSummary.black_player_rating,
    });
    const perspective =
      gameSummary.white_player_id === adminSelectedUserId ? "white" : "black";
    adminGameContext = {
      players: {
        white: whiteProfile,
        black: blackProfile,
      },
      perspective,
    };
    await openGame(gameSummary.id, { origin: "admin" });
  }

  async function loadLeaderboard(force = false) {
    if (force) {
      leaderboardLoaded = false;
    }
    if (isLeaderboardLoading) {
      return;
    }
    if (leaderboardLoaded && !force) {
      return;
    }
    isLeaderboardLoading = true;
    leaderboardError = "";
    try {
      const payload = await fetchLeaderboard({ limit: 10 });
      leaderboard = Array.isArray(payload) ? payload : [];
      leaderboardLoaded = true;
    } catch (error) {
      const message = error instanceof Error ? error.message : "";
      leaderboardError = message || tr("errors.loadLeaderboard");
      leaderboard = [];
    } finally {
      isLeaderboardLoading = false;
    }
  }

  async function refreshSelectedGame(gameId) {
    if (!accessToken) return;
    gameError = "";
    try {
      const detail = await fetchGameDetail(gameId, accessToken);
      let mapped = mapGameDetail(detail);
      if (selectedGameOrigin === "admin" && adminGameContext) {
        const { players, perspective } = adminGameContext;
        const viewerColor = perspective === "black" ? "black" : "white";
        const opponentProfile = viewerColor === "white" ? players.black : players.white;
        mapped = {
          ...mapped,
          yourColor: viewerColor,
          players,
          opponent: opponentProfile ? makeSpectatorOpponent(opponentProfile) : mapped.opponent,
          isSpectator: true,
        };
      } else {
        mapped = { ...mapped, isSpectator: false };
      }
      selectedGame = mapped;
      if (selectedGameOrigin === "hub") {
        await maybeTriggerEngineMove(selectedGame);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "";
      gameError = message || tr("errors.loadGame");
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

  async function openGame(id, options = {}) {
    if (!id || !isAuthenticated) return;
    const origin = options.origin ?? "hub";
    resetAnalysis();
    selectedGameOrigin = origin;
    selectedGameId = id;
    gameError = "";
    await refreshSelectedGame(id);
    if (origin === "hub") {
      connectSocket(id);
    } else {
      teardownSocket();
    }
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
      const rawMessage = error instanceof Error ? error.message : "";
      if (rawMessage.includes("Engine binary")) {
        gameError = tr("errors.engineUnavailable");
      } else if (rawMessage.includes("Engine terminated")) {
        gameError = tr("errors.engineTerminated");
      } else {
        gameError = rawMessage || tr("errors.engineRequest");
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
    syncOpponentPreferences(opponentId, { forceReset: true });
  };

  const handleColorChange = (color) => {
    newGameColor = color === "black" ? "black" : "white";
  };

  const handleDepthChange = (value) => {
    const cleaned = sanitizeDepthInput(value);
    if (!cleaned) {
      newGameDepth = cleaned;
      return;
    }
    const opponent = findOpponentById(newGameOpponentId);
    const spec = opponent?.isEngine ? findEngineSpec(opponent.engineKey) : null;
    const limit =
      typeof spec?.max_depth === "number" && Number.isFinite(spec.max_depth)
        ? spec.max_depth
        : 64;
    const clamped = clampDepthValue(cleaned, limit);
    newGameDepth = clamped !== null ? String(clamped) : cleaned;
  };

  const handleInitialMinutesChange = (value) => {
    const cleaned = sanitizeNumericInput(value);
    if (!cleaned) {
      newGameInitialMinutes = "";
      return;
    }
    const numeric = Number.parseInt(cleaned, 10);
    if (!Number.isFinite(numeric) || numeric <= 0) {
      newGameInitialMinutes = "";
      return;
    }
    const clamped = clampIntegerValue(cleaned, {
      min: 1,
      max: MAX_INITIAL_MINUTES,
    });
    newGameInitialMinutes = clamped !== null ? String(clamped) : "";
  };

  const handleIncrementSecondsChange = (value) => {
    const cleaned = sanitizeNumericInput(value);
    if (!cleaned) {
      newGameIncrementSeconds = "";
      return;
    }
    const clamped = clampIntegerValue(cleaned, {
      min: 0,
      max: MAX_INCREMENT_SECONDS,
    });
    newGameIncrementSeconds = clamped !== null ? String(clamped) : cleaned;
  };

  const handleEngineModeChange = (mode) => {
    if (mode !== ENGINE_MODE_DEPTH && mode !== ENGINE_MODE_TIME) {
      return;
    }
    if (newGameEngineMode === mode) {
      return;
    }
    newGameEngineMode = mode;
    if (mode === ENGINE_MODE_DEPTH) {
      newGameInitialMinutes = "";
      newGameIncrementSeconds = "";
      syncNewGameDepth(newGameOpponentId, { forceReset: true });
      return;
    }
    newGameDepth = "";
    ensureTimeDefaults();
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
    const isEngineChallenge = Boolean(opponent.isEngine);
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
      ? tr("game.summary.engine", {
          name: opponent.nickname || tr("label.engine"),
        })
      : tr("game.summary.default");
    const useTimeControl = !isEngineChallenge || newGameEngineMode === ENGINE_MODE_TIME;
    if (useTimeControl) {
      const initialSeconds = normalizeInitialSeconds(newGameInitialMinutes);
      const incrementSeconds = normalizeIncrementSeconds(newGameIncrementSeconds);
      if (initialSeconds !== null) {
        payload.initial_time_seconds = initialSeconds;
        if (incrementSeconds !== null) {
          payload.increment_seconds = incrementSeconds;
        }
      } else if (incrementSeconds !== null && incrementSeconds > 0) {
        payload.increment_seconds = incrementSeconds;
      }
    }
    if (isEngineChallenge) {
      const spec = findEngineSpec(opponent.engineKey);
      const limit =
        typeof spec?.max_depth === "number" && Number.isFinite(spec.max_depth)
          ? spec.max_depth
          : 64;
      if (newGameEngineMode === ENGINE_MODE_DEPTH) {
        const depthValue = clampDepthValue(newGameDepth, limit);
        if (depthValue !== null) {
          payload.engine_depth = depthValue;
        }
      }
    }
    try {
      const created = await createGame(payload, accessToken);
      await loadHub();
      await openGame(created.id);
      showNewGameForm = false;
    } catch (error) {
      const message = error instanceof Error ? error.message : "";
      hubError = message || tr("errors.createGame");
    }
  };

  const handleBoardMove = async (event) => {
    if (!selectedGame || !isAuthenticated || selectedGame?.isSpectator) return;
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
      const message = error instanceof Error ? error.message : "";
      gameError = message || tr("errors.moveRecord");
      await refreshSelectedGame(selectedGame.id);
      await loadHub();
    }
  };

  const handleBoardUndo = async () => {
    if (!selectedGame || selectedGame?.isSpectator) return;
    await refreshSelectedGame(selectedGame.id);
  };

  const handleResign = async () => {
    if (!selectedGame || !isAuthenticated || selectedGame?.isSpectator) return;
    gameError = "";
    try {
      await resignGame(selectedGame.id, accessToken);
    } catch (error) {
      const message = error instanceof Error ? error.message : "";
      gameError = message || tr("errors.resign");
    } finally {
      await refreshSelectedGame(selectedGame.id);
      await loadHub();
    }
  };

  // Trigger a Stockfish analysis for the completed game and capture the result.
  async function runAnalysis(options = {}) {
    if (!selectedGame || !isAuthenticated || !accessToken) {
      return;
    }
    if (selectedGame.status !== "completed") {
      analysisError = tr("analysis.error.unfinished");
      return;
    }

    const requestedKey = options?.engineKey || analysisEngineSpec?.key || null;
    const spec = requestedKey ? findEngineSpec(requestedKey) : analysisEngineSpec;
    if (!spec) {
      analysisError = tr("analysis.error.noEngine");
      return;
    }

    const gameId = selectedGame.id;
    isAnalysisLoading = true;
    analysisError = "";

    try {
      const payload = { engine_key: spec.key };
      const limit =
        typeof spec.max_depth === "number" && Number.isFinite(spec.max_depth)
          ? spec.max_depth
          : 64;
      const candidateDepth =
        options?.depth ?? selectedGame.engineDepth ?? spec.default_depth ?? null;
      const resolvedDepth =
        candidateDepth !== null && candidateDepth !== undefined
          ? clampDepthValue(candidateDepth, limit)
          : null;
      if (resolvedDepth) {
        payload.depth = resolvedDepth;
      }

      const response = await analyzeGameSequence(gameId, payload, accessToken);
      if (!selectedGame || selectedGame.id !== gameId) {
        return;
      }
      analysisResult = {
        engine:
          response?.engine ?? {
            key: spec.key,
            name: spec.name,
            default_depth: spec.default_depth ?? null,
            max_depth: spec.max_depth ?? null,
          },
        depth: response?.depth ?? resolvedDepth ?? spec.default_depth ?? null,
        evaluation_cp: response?.final_evaluation_cp ?? null,
        mate_in: response?.final_mate_in ?? null,
      };
      analysisSteps = Array.isArray(response?.steps) ? response.steps : [];
      analysisFetchedAt = new Date().toISOString();
    } catch (error) {
      if (!selectedGame || selectedGame.id !== gameId) {
        return;
      }
      const message = error instanceof Error ? error.message : "";
      analysisError = message || tr("analysis.error.generic");
    } finally {
      if (selectedGame && selectedGame.id === gameId) {
        isAnalysisLoading = false;
      }
    }
  }

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
      const message = error instanceof Error ? error.message : "";
      hubError = message || tr("errors.profileUpdate");
    }
  };

  const openProfile = () => {
    if (!isAuthenticated) return;
    navigateTo(VIEW.PROFILE);
  };

  const openPuzzles = () => {
    if (!isAuthenticated) return;
    navigateTo(VIEW.PUZZLES);
  };

  const openAdmin = () => {
    if (!isAuthenticated || !currentUser?.is_admin) return;
    navigateTo(VIEW.ADMIN);
  };

  const returnToGames = () => {
    teardownSocket();
    resetAnalysis();
    selectedGameOrigin = "hub";
    currentView = VIEW.GAMES;
    startHubPolling();
    void loadHub();
    navigateTo(VIEW.GAMES);
  };

  const exitGameView = () => {
    if (selectedGameOrigin === "admin") {
      teardownSocket();
      resetAnalysis();
      selectedGameId = null;
      selectedGame = null;
      selectedGameOrigin = "hub";
      currentView = VIEW.ADMIN;
      navigateTo(VIEW.ADMIN);
      return;
    }
    returnToGames();
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
    newGameDepth = "";
    newGameInitialMinutes = "";
    newGameIncrementSeconds = "";
    newGameEngineMode = ENGINE_MODE_TIME;
    landingError = "";
    hubError = "";
    gameError = "";
    adminUsers = [];
    adminError = "";
    isAdminLoading = false;
    adminSelectedUserId = null;
    adminUserGames = [];
    adminGamesError = "";
    isAdminGamesLoading = false;
    adminGameContext = null;
    selectedGameOrigin = "hub";
    leaderboard = [];
    leaderboardError = "";
    isLeaderboardLoading = false;
    leaderboardLoaded = false;
    resetAnalysis();
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
    setLocale(detectInitialLocale());
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

  $: if (
    !leaderboardLoaded &&
    (currentView === VIEW.LANDING || currentView === VIEW.GAMES || currentView === VIEW.PROFILE)
  ) {
    void loadLeaderboard();
  }

  $: if (availableOpponents.length) {
    if (
      !newGameOpponentId ||
      !availableOpponents.some(
        (opponent) => String(opponent.id) === newGameOpponentId,
      )
    ) {
      const defaultId = String(availableOpponents[0].id);
      newGameOpponentId = defaultId;
      syncOpponentPreferences(defaultId, { forceReset: true });
    } else {
      syncOpponentPreferences(newGameOpponentId);
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

  $: if (currentView === VIEW.ADMIN && (!isAuthenticated || !currentUser?.is_admin)) {
    currentView = isAuthenticated ? VIEW.GAMES : VIEW.LANDING;
  }

  $: if (isAuthenticated && currentView === VIEW.GAMES) {
    startHubPolling();
  } else if (currentView !== VIEW.GAMES) {
    stopHubPolling();
  }

  $: analysisEngineSpec = (() => {
    const stockfish = findEngineSpec("stockfish");
    if (stockfish) {
      return stockfish;
    }
    if (Array.isArray(availableEngines) && availableEngines.length) {
      return availableEngines[0];
    }
    return null;
  })();

  $: hubUser = currentUser
    ? {
        id: currentUser.id,
        nickname: currentUser.username,
        avatar: currentUser.avatar_url || fallbackAvatar(currentUser.username),
        rating:
          typeof currentUser.rating === "number" && Number.isFinite(currentUser.rating)
            ? Math.round(currentUser.rating)
            : null,
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
      leaderboard={leaderboard}
      leaderboardError={leaderboardError}
      isLeaderboardLoading={isLeaderboardLoading}
      {formatTime}
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
      {availableEngines}
      {newGameOpponentId}
      {newGameColor}
      newGameDepth={newGameDepth}
      newGameInitialMinutes={newGameInitialMinutes}
      newGameIncrementSeconds={newGameIncrementSeconds}
      newGameEngineMode={newGameEngineMode}
      {formatTime}
      {gameStatusLabel}
      onOpenGame={openGame}
      onToggleNewGameForm={toggleNewGameForm}
      onChangeOpponent={handleOpponentChange}
      onChangeColor={handleColorChange}
      onChangeDepth={handleDepthChange}
      onChangeInitialMinutes={handleInitialMinutesChange}
      onChangeIncrementSeconds={handleIncrementSecondsChange}
      onChangeEngineMode={handleEngineModeChange}
      onLaunchGame={launchGame}
      onOpenProfile={openProfile}
      onOpenPuzzles={openPuzzles}
      onOpenAdmin={openAdmin}
      onLogout={logout}
      showAdminLink={Boolean(currentUser?.is_admin)}
      leaderboard={leaderboard}
      isLeaderboardLoading={isLeaderboardLoading}
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
      onMove={handleBoardMove}
      onUndo={handleBoardUndo}
      onResign={handleResign}
      analysisEngine={analysisEngineSpec}
      {analysisResult}
      analysisError={analysisError}
      isAnalysisLoading={isAnalysisLoading}
      analysisFetchedAt={analysisFetchedAt}
      analysisSteps={analysisSteps}
      onAnalyze={runAnalysis}
      onBack={exitGameView}
      onLogout={logout}
    />
  {:else if currentView === VIEW.PROFILE && isAuthenticated}
    <ProfileView
      user={currentUser}
      {profileDraft}
      gameCount={orderedGames.length}
      leaderboard={leaderboard}
      isLeaderboardLoading={isLeaderboardLoading}
      onFieldChange={handleProfileFieldChange}
      onSave={saveProfile}
      onBack={returnToGames}
      onLogout={logout}
    />
  {:else if currentView === VIEW.ADMIN && isAuthenticated && currentUser?.is_admin}
    <AdminUsersView
      users={adminUsers}
      isLoading={isAdminLoading}
      error={adminError}
      onRefresh={loadAdminUsers}
      onBack={returnToGames}
      onLogout={logout}
      {formatTime}
      selectedUserId={adminSelectedUserId}
      onSelectUser={selectAdminUser}
      userGames={adminUserGames}
      gamesLoading={isAdminGamesLoading}
      gamesError={adminGamesError}
      onAnalyzeGame={analyzeAdminGame}
    />
  {:else if currentView === VIEW.PUZZLES && isAuthenticated}
    <PuzzleTrainerView
      token={accessToken}
      user={currentUser}
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
