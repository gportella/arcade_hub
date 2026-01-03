<script>
  import { onDestroy, onMount } from "svelte";
  import { get } from "svelte/store";
  import { Chess } from "chess.js";

  import PuzzleScoreCard from "../puzzles/PuzzleScoreCard.svelte";
  import PuzzleControls from "../puzzles/PuzzleControls.svelte";
  import PuzzleHistory from "../puzzles/PuzzleHistory.svelte";
  import PuzzleTrainerHeader from "../puzzles/PuzzleTrainerHeader.svelte";
  import PuzzleMetaPanel from "../puzzles/PuzzleMetaPanel.svelte";
  import PuzzleBoardPanel from "../puzzles/PuzzleBoardPanel.svelte";
  import {
    fetchRandomPuzzle,
    restartPuzzleAttempt,
    requestPuzzleHint,
    submitPuzzleMove,
  } from "../api/client";
  import { normalizeFen } from "../fen";
  import { t } from "../i18n";

  export let token = "";
  export let user = null;
  export let onBack = () => {};
  export let onLogout = () => {};

  const difficulties = [
    { value: "easy" },
    { value: "medium" },
    { value: "hard" },
    { value: "expert" },
  ];

  const MAX_HISTORY = 10;
  const game = new Chess();

  const normalizeMove = (move) => {
    if (typeof move !== "string") return "";
    const trimmed = move.trim().toLowerCase();
    return trimmed.length >= 4 ? trimmed : "";
  };

  const normalizeMoveList = (moves) => {
    if (!Array.isArray(moves)) return [];
    return moves.map(normalizeMove).filter(Boolean);
  };

  const parseUciMove = (uci) => {
    const value = normalizeMove(uci);
    if (!value) return null;
    return {
      from: value.slice(0, 2),
      to: value.slice(2, 4),
      promotion: value.length > 4 ? value.slice(4, 5) : undefined,
    };
  };

  const buildArrowShapes = (uci, brush = "green") => {
    const move = normalizeMove(uci);
    if (!move) return [];
    const from = move.slice(0, 2);
    const to = move.slice(2, 4);
    if (!to) return [{ brush, orig: from }];
    return [
      { brush, orig: from, dest: to },
      { brush, orig: from },
      { brush, orig: to },
    ];
  };

  const playMoves = (baseFen, moves) => {
    const scratch = new Chess();
    try {
      if (baseFen) {
        scratch.load(baseFen);
      } else {
        scratch.reset();
      }
    } catch (_error) {
      scratch.reset();
    }

    const history = [];
    for (const moveText of normalizeMoveList(moves)) {
      const parsed = parseUciMove(moveText);
      if (!parsed) break;
      try {
        const outcome = scratch.move(parsed);
        if (!outcome) break;
        history.push({ uci: moveText, san: outcome.san ?? moveText });
      } catch (_error) {
        break;
      }
    }

    return {
      fen: normalizeFen(scratch.fen()) ?? scratch.fen(),
      history,
    };
  };

  const derivePlayerMoveIndices = (baseFen, solution, playerColor) => {
    if (!Array.isArray(solution) || !solution.length) return [];

    const scratch = new Chess();
    try {
      if (baseFen) {
        scratch.load(baseFen);
      } else {
        scratch.reset();
      }
    } catch (_error) {
      scratch.reset();
    }

    const target = playerColor === "black" ? "black" : "white";
    const indices = [];
    for (let index = 0; index < solution.length; index += 1) {
      const turnColor = scratch.turn() === "b" ? "black" : "white";
      if (turnColor === target) {
        indices.push(index);
      }

      const parsed = parseUciMove(solution[index]);
      if (!parsed) break;
      try {
        if (!scratch.move(parsed)) break;
      } catch (_error) {
        break;
      }
    }

    return indices;
  };

  const computeRemainingPlayerMoves = (submittedLength, indices) => {
    if (!Array.isArray(indices) || !indices.length) return 0;
    let solvedCount = 0;
    for (const index of indices) {
      if (index < submittedLength) {
        solvedCount += 1;
      }
    }
    return Math.max(0, indices.length - solvedCount);
  };

  const createHistoryEntry = (sessionSnapshot, solved, points) => ({
    id: `${sessionSnapshot.coolId}-${Date.now()}`,
    coolId: sessionSnapshot.coolId,
    difficulty: sessionSnapshot.difficulty,
    solved,
    points,
    hints: sessionSnapshot.hintCount ?? 0,
    timestamp: new Date(),
  });

  const formatSanForMove = (baseFen, priorMoves, targetMove) => {
    const normalizedMove = normalizeMove(targetMove);
    if (!normalizedMove) return "";

    const scratch = new Chess();
    try {
      if (baseFen) {
        scratch.load(baseFen);
      } else {
        scratch.reset();
      }
    } catch (_error) {
      scratch.reset();
    }

    for (const moveText of normalizeMoveList(priorMoves)) {
      const parsed = parseUciMove(moveText);
      if (!parsed) return "";
      try {
        if (!scratch.move(parsed)) return "";
      } catch (_error) {
        return "";
      }
    }

    const parsedTarget = parseUciMove(normalizedMove);
    if (!parsedTarget) return "";
    try {
      const result = scratch.move(parsedTarget);
      return result?.san ?? normalizedMove;
    } catch (_error) {
      return "";
    }
  };

  const buildSessionFromPayload = (payload, difficulty) => {
    const baseFen = normalizeFen(payload.fen) ?? payload.fen;
    const solution = normalizeMoveList(payload.correct_moves);
    const playerColor = payload.side_to_move === "black" ? "black" : "white";
    const indices = derivePlayerMoveIndices(baseFen, solution, playerColor);
    const submitted = normalizeMoveList(payload.submitted_moves ?? []);
    const remainingPlayerMoves = typeof payload.remaining_moves === "number"
      ? Math.max(0, payload.remaining_moves)
      : computeRemainingPlayerMoves(submitted.length, indices);

    return {
      attemptId: payload.attempt_id,
      coolId: payload.cool_id,
      difficulty,
      baseFen,
      currentFen: baseFen,
      solution,
      submitted,
      playerColor,
      playerIndices: indices,
      remainingPlayerMoves,
      hintAvailable: payload.hint_available,
      hintCount: 0,
      status: "active",
      points: {
        current: payload.current_points ?? 0,
        max: payload.max_points ?? 3,
      },
      stats: {
        presented: payload.times_presented ?? 0,
        solved: payload.times_solved ?? 0,
      },
    };
  };

  let selectedDifficulty = "easy";
  let loadingPuzzle = false;
  let submittingMove = false;
  let hintLoading = false;
  let autoAdvanceTimer = null;

  let session = null;
  let boardFen = null;
  let orientation = "white";
  let boardResetToken = Date.now();

  let infoMessage = "";
  let errorMessage = "";
  let hintMessage = "";
  let pendingMoveLabel = "";
  let guidanceShapes = [];
  let totalPoints = 0;
  let history = [];
  let sideAnnouncement = "";
  let boardInteractive = false;
  let lastSubmittedUci = "";
  let celebrationActive = false;
  let restartingAttempt = false;
  let canResetCurrentAttempt = false;
  const submissionQueue = [];
  let submissionInFlight = false;

  const formatPuzzleName = (value) => {
    if (!value) return "Puzzle";
    const trimmed = String(value).replace(/[-_]+/g, " ").trim();
    if (!trimmed) {
      return "Puzzle";
    }
    return trimmed
      .split(/\s+/)
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  };

  const setBoard = (fen, { forceReset = false } = {}) => {
    const fallbackFen = fen || session?.baseFen || game.fen();
    const normalized = normalizeFen(fallbackFen) ?? fallbackFen;
    try {
      game.load(normalized);
    } catch (_error) {
      game.reset();
      if (session?.baseFen) {
        try {
          game.load(session.baseFen);
        } catch (_innerError) {
          game.reset();
        }
      }
    }
    const current = normalizeFen(game.fen()) ?? game.fen();
    boardFen = current;
    if (forceReset) {
      boardResetToken = Date.now();
    }
    orientation = session?.playerColor === "black" ? "black" : "white";

    const translator = get(t);
    if (session) {
      const colorKey = game.turn() === "b" ? "color.black" : "color.white";
      const colorLabel = translator(colorKey);
      sideAnnouncement = translator("puzzles.status.sideToMove", { color: colorLabel });
    } else {
      sideAnnouncement = "";
    }
  };

  const syncBoardToSession = ({ forceReset = false } = {}) => {
    if (!session?.currentFen) {
      return;
    }
    setBoard(session.currentFen, { forceReset });
  };

  const clearAutoAdvance = () => {
    if (autoAdvanceTimer) {
      clearTimeout(autoAdvanceTimer);
      autoAdvanceTimer = null;
    }
  };

  const processSubmissionQueue = () => {
    if (submissionInFlight) return;
    if (!submissionQueue.length) {
      submittingMove = false;
      return;
    }
    if (!token) return;

    submissionInFlight = true;
    const next = submissionQueue[0];

    submitPuzzleMove(
      next.coolId,
      {
        attemptId: next.attemptId,
        move: next.uci,
      },
      token,
    )
      .then((response) => {
        void handleSubmissionResponse(response);
      })
      .catch((error) => {
        submissionQueue.length = 0;
        submissionInFlight = false;
        submittingMove = false;
        handleSubmissionError(error);
      })
      .finally(() => {
        submissionQueue.shift();
        submissionInFlight = false;
        if (submissionQueue.length) {
          processSubmissionQueue();
        } else {
          submittingMove = false;
        }
      });
  };

  const enqueueSubmission = (uci) => {
    if (!session?.attemptId || !session?.coolId) {
      return;
    }
    submissionQueue.push({
      uci,
      attemptId: session.attemptId,
      coolId: session.coolId,
    });
    submittingMove = true;
    processSubmissionQueue();
  };

  const applyLocalMoveProgress = (uci, moveDetail) => {
    if (!session) return;

    const translator = get(t);
    const normalized = normalizeMove(uci);
    const submittedBefore = Array.isArray(session.submitted) ? session.submitted : [];
    const solution = Array.isArray(session.solution) ? session.solution : [];
    const updatedSubmitted = [...submittedBefore, normalized];

    const pointer = determinePlayerPointer(session);
    const expectedIndex = Array.isArray(session.playerIndices)
      ? session.playerIndices[pointer]
      : undefined;

    let opponentMove = "";
    if (typeof expectedIndex === "number") {
      const nextIndex = expectedIndex + 1;
      if (
        nextIndex < solution.length &&
        Array.isArray(session.playerIndices) &&
        !session.playerIndices.includes(nextIndex)
      ) {
        const autoMove = normalizeMove(solution[nextIndex]);
        if (autoMove) {
          updatedSubmitted.push(autoMove);
          opponentMove = autoMove;
        }
      }
    }

    const boardState = playMoves(session.baseFen, updatedSubmitted);
    const remainingPlayerMoves = computeRemainingPlayerMoves(
      updatedSubmitted.length,
      session.playerIndices,
    );
    const history = Array.isArray(boardState.history) ? boardState.history : [];
    const opponentSan = opponentMove ? history.at(-1)?.san ?? opponentMove : "";

    session = {
      ...session,
      submitted: updatedSubmitted,
      currentFen: boardState.fen,
      remainingPlayerMoves,
    };

    pendingMoveLabel = "";
    lastSubmittedUci = normalized;
    guidanceShapes = [];
    errorMessage = "";
    hintMessage = "";
    syncBoardToSession();

    if (remainingPlayerMoves > 0) {
      const keepGoing = translator("puzzles.feedback.keepGoing");
      const opponentMessage = opponentSan
        ? translator("puzzles.feedback.opponentMove", { move: opponentSan })
        : "";
      const remainingLabel = translator("puzzles.feedback.movesRemaining", {
        count: remainingPlayerMoves,
        suffix: remainingPlayerMoves === 1 ? "" : "s",
      });
      infoMessage = [keepGoing, opponentMessage, remainingLabel]
        .map((chunk) => chunk?.trim())
        .filter(Boolean)
        .join(" ");
      celebrationActive = false;
    } else {
      infoMessage = translator("puzzles.feedback.solved");
      celebrationActive = true;
      clearAutoAdvance();
    }
  };

  const handleImmediateFailure = (uci) => {
    if (!session) return;

    const translator = get(t);
    errorMessage = translator("puzzles.feedback.failed");
    infoMessage = "";
    hintMessage = "";
    guidanceShapes = [];
    pendingMoveLabel = "";
    celebrationActive = false;

    const submittedBefore = Array.isArray(session.submitted) ? session.submitted : [];
    const updatedSubmitted = [...submittedBefore, normalizeMove(uci)];

    session = {
      ...session,
      submitted: updatedSubmitted,
      currentFen: session.baseFen ?? session.currentFen,
      remainingPlayerMoves: 0,
      status: "failed",
    };

    syncBoardToSession({ forceReset: true });
    clearAutoAdvance();
  };

  const resetTransientState = () => {
    infoMessage = "";
    errorMessage = "";
    hintMessage = "";
    guidanceShapes = [];
    pendingMoveLabel = "";
    lastSubmittedUci = "";
    submissionQueue.length = 0;
    submissionInFlight = false;
    submittingMove = false;
  };

  const determinePlayerPointer = (snapshot) => {
    if (!snapshot) return 0;
    const indices = Array.isArray(snapshot.playerIndices) ? snapshot.playerIndices : [];
    if (!indices.length) return 0;
    const submitted = normalizeMoveList(snapshot.submitted ?? []);
    let solved = 0;
    for (const index of indices) {
      if (index < submitted.length) {
        const played = submitted[index] ?? "";
        const expected = normalizeMove(snapshot.solution?.[index] ?? "");
        if (played && expected && played === expected) {
          solved += 1;
        }
      } else {
        break;
      }
    }
    return Math.min(indices.length, solved);
  };

  const expectedMove = () => {
    if (!session) return "";
    if (!Array.isArray(session.playerIndices) || !session.playerIndices.length) return "";
    const pointer = determinePlayerPointer(session);
    if (pointer >= session.playerIndices.length) return "";
    const targetIndex = session.playerIndices[pointer];
    return session.solution?.[targetIndex] ?? "";
  };

  const applySubmissionPayload = (payload) => {
    if (!session) return;

    const solution = normalizeMoveList(payload.correct_moves ?? session.solution ?? []);
    const submittedSource = Array.isArray(payload.submitted_moves) && payload.submitted_moves.length
      ? payload.submitted_moves
      : session.submitted ?? [];
    const submitted = normalizeMoveList(submittedSource);
    const playerIndices = derivePlayerMoveIndices(session.baseFen, solution, session.playerColor);
    const remainingPlayerMoves = typeof payload.remaining_moves === "number"
      ? Math.max(0, payload.remaining_moves)
      : computeRemainingPlayerMoves(submitted.length, playerIndices);

    const boardState = playMoves(session.baseFen, submitted);
    const nextFen = normalizeFen(payload.board_fen) ?? boardState.fen ?? session.currentFen;

    session = {
      ...session,
      attemptId: payload.attempt_id ?? session.attemptId,
      solution,
      submitted,
      playerIndices,
      remainingPlayerMoves,
      currentFen: nextFen,
      hintAvailable:
        typeof payload.hint_available === "boolean" ? payload.hint_available : session.hintAvailable,
      hintCount: typeof payload.hint_count === "number" ? payload.hint_count : session.hintCount,
      points: {
        current: typeof payload.current_points === "number" ? payload.current_points : session.points.current,
        max: session.points.max,
      },
      status: payload.status === "solved" ? "solved" : payload.status === "failed" ? "failed" : "active",
    };
  };

  const recordHistory = (solved, points) => {
    if (!session) return;
    const entry = createHistoryEntry(session, solved, points);
    history = [entry, ...history].slice(0, MAX_HISTORY);
  };

  const loadPuzzle = async ({ difficulty = selectedDifficulty, resetHistory = false } = {}) => {
    if (!token) return;

    clearAutoAdvance();
    loadingPuzzle = true;
    submittingMove = false;
    hintLoading = false;
    resetTransientState();

    const translator = get(t);
    const order = [
      difficulty,
      ...difficulties.map((entry) => entry.value).filter((value) => value !== difficulty),
    ];
    const visited = new Set();
    let resolved = null;
    let resolvedDifficulty = difficulty;
    let detail = "";

    try {
      for (const option of order) {
        if (visited.has(option)) continue;
        visited.add(option);
        const payload = await fetchRandomPuzzle({ difficulty: option }, token);
        if (payload && !payload.missing) {
          resolved = payload;
          resolvedDifficulty = option;
          break;
        }
        if (payload?.missing && !detail) {
          detail = payload.detail ?? "";
        }
      }

      if (!resolved) {
        try {
          const fallbackPayload = await fetchRandomPuzzle({}, token);
          if (fallbackPayload && !fallbackPayload.missing) {
            resolved = fallbackPayload;
            resolvedDifficulty = String(
              fallbackPayload.difficulty ?? difficulty ?? selectedDifficulty,
            );
          }
        } catch (fallbackError) {
          if (!detail) {
            detail = fallbackError instanceof Error ? fallbackError.message : "";
          }
        }
      }

      if (!resolved) {
        session = null;
        game.reset();
        setBoard(game.fen(), { forceReset: true });
        infoMessage = detail || translator("puzzles.info.noneAvailable");
        return;
      }

      session = buildSessionFromPayload(resolved, resolvedDifficulty);
      if (typeof resolved.total_user_points === "number") {
        totalPoints = resolved.total_user_points;
      }
      selectedDifficulty = resolvedDifficulty;
      if (resetHistory) {
        history = [];
      }

      game.reset();
      if (session.baseFen) {
        try {
          game.load(session.baseFen);
        } catch (_error) {
          game.reset();
        }
      }
      session.currentFen = normalizeFen(game.fen()) ?? game.fen();
      syncBoardToSession({ forceReset: true });

      infoMessage = "";
      totalPoints = Number.isFinite(totalPoints) ? totalPoints : 0;
    } catch (error) {
      const message = error instanceof Error ? error.message : translator("puzzles.error.load");
      session = null;
      game.reset();
      setBoard(game.fen(), { forceReset: true });
      errorMessage = message;
    } finally {
      loadingPuzzle = false;
    }
  };

  const restartCurrentPuzzle = async () => {
    if (!session || !token || restartingAttempt) return;

    const translator = get(t);
    const targetCoolId = session.coolId;
    const fallbackDifficulty = session.difficulty ?? selectedDifficulty;
    const playerMoveSlots = Array.isArray(session.playerIndices) ? session.playerIndices.length : 0;

    clearAutoAdvance();
    submissionQueue.length = 0;
    submissionInFlight = false;
    submittingMove = false;
    restartingAttempt = true;
    submittingMove = false;
    hintLoading = false;
    resetTransientState();
    celebrationActive = false;

    const baseFen = session.baseFen ?? session.currentFen;
    session = {
      ...session,
      attemptId: null,
      status: "active",
      submitted: [],
      remainingPlayerMoves: playerMoveSlots,
      currentFen: baseFen,
      hintAvailable: session.hintAvailable,
      hintCount: 0,
    };

    syncBoardToSession({ forceReset: true });
    infoMessage = "";
    errorMessage = "";

    try {
      const payload = await restartPuzzleAttempt(targetCoolId, token);
      const resolvedDifficulty = payload?.difficulty ?? fallbackDifficulty;
      const rebuilt = buildSessionFromPayload(payload, resolvedDifficulty);
      if (typeof payload.total_user_points === "number") {
        totalPoints = payload.total_user_points;
      }
      selectedDifficulty = resolvedDifficulty;

      game.reset();
      if (rebuilt.baseFen) {
        try {
          game.load(rebuilt.baseFen);
        } catch (_error) {
          game.reset();
        }
      }

      rebuilt.currentFen = normalizeFen(game.fen()) ?? game.fen();
      session = rebuilt;
      syncBoardToSession({ forceReset: true });
    } catch (error) {
      const message = error instanceof Error ? error.message : translator("puzzles.error.load");
      errorMessage = message;
      syncBoardToSession({ forceReset: true });
    } finally {
      restartingAttempt = false;
    }
  };

  const handleSubmissionResponse = async (payload) => {
    if (!session) return;

    const translator = get(t);
    applySubmissionPayload(payload);
    if (session) {
      const forceReset = session.status === "failed";
      syncBoardToSession({ forceReset });
    }

    if (typeof payload.total_user_points === "number") {
      totalPoints = payload.total_user_points;
    }

    if (session.status === "solved") {
      infoMessage = translator("puzzles.feedback.solved");
      celebrationActive = true;
      recordHistory(true, payload.points_awarded ?? session.points.current);
      session.stats = {
        ...session.stats,
        solved: (session.stats.solved ?? 0) + 1,
      };
      hintMessage = "";
      guidanceShapes = [];
      clearAutoAdvance();
    } else if (session.status === "failed") {
      errorMessage = translator("puzzles.feedback.failed");
      celebrationActive = false;
      recordHistory(false, 0);
      hintMessage = "";
      guidanceShapes = [];
      clearAutoAdvance();
      void restartCurrentPuzzle();
    } else {
      const opponentLabel = payload.opponent_move_san || payload.opponent_move || "";
      const keepGoing = translator("puzzles.feedback.keepGoing");
      const opponentMessage = opponentLabel
        ? translator("puzzles.feedback.opponentMove", { move: opponentLabel })
        : "";
      const remainingLabel = session.remainingPlayerMoves > 0
        ? translator("puzzles.feedback.movesRemaining", {
            count: session.remainingPlayerMoves,
            suffix: session.remainingPlayerMoves === 1 ? "" : "s",
          })
        : "";
      infoMessage = [keepGoing, opponentMessage, remainingLabel]
        .map((chunk) => chunk?.trim())
        .filter(Boolean)
        .join(" ");
    }

    submittingMove = submissionQueue.length > 0 || submissionInFlight;
    pendingMoveLabel = "";
    lastSubmittedUci = "";
  };

  const handleSubmissionError = (error) => {
    const translator = get(t);
    const message = error instanceof Error ? error.message : translator("puzzles.error.submit");
    errorMessage = message;
    submissionQueue.length = 0;
    submissionInFlight = false;
    submittingMove = false;
    pendingMoveLabel = "";
    lastSubmittedUci = "";
    celebrationActive = false;
    syncBoardToSession({ forceReset: true });
  };

  const handleBoardMove = (detail) => {
    if (!session || session.status !== "active" || restartingAttempt || loadingPuzzle) {
      syncBoardToSession({ forceReset: true });
      return;
    }

    const moveDetail = detail?.move;
    const uci = normalizeMove(
      moveDetail ? `${moveDetail.from}${moveDetail.to}${moveDetail.promotion ?? ""}` : "",
    );
    if (!moveDetail || !uci) {
      syncBoardToSession({ forceReset: true });
      return;
    }

    const expected = expectedMove();

    pendingMoveLabel = moveDetail.san || formatSanForMove(session.baseFen, session.submitted, uci);
    errorMessage = "";
    infoMessage = "";
    hintMessage = "";
    guidanceShapes = [];

    if (expected && uci !== expected) {
      handleImmediateFailure(uci);
      enqueueSubmission(uci);
      return;
    }

    if (expected) {
      enqueueSubmission(uci);
      applyLocalMoveProgress(uci, moveDetail);
      return;
    }

    if ((session?.remainingPlayerMoves ?? 0) === 0) {
      pendingMoveLabel = "";
      return;
    }

    submittingMove = true;
    submitPuzzleMove(
      session.coolId,
      {
        attemptId: session.attemptId,
        move: uci,
      },
      token,
    )
      .then((response) => {
        void handleSubmissionResponse(response);
      })
      .catch((error) => {
        handleSubmissionError(error);
      });
  };

  const handleHint = async () => {
    if (!session || session.status !== "active" || hintLoading || submittingMove) return;

    const translator = get(t);
    const expected = expectedMove();
    const fallbackShapes = expected ? buildArrowShapes(expected, "green") : [];

    const applyFallback = () => {
      guidanceShapes = fallbackShapes;
      if (fallbackShapes.length) {
        hintMessage = translator("puzzles.feedback.hintDisplayed");
      } else {
        hintMessage = translator("puzzles.error.hint");
      }
    };

    if (!session.hintAvailable || session.hintCount >= 1) {
      applyFallback();
      return;
    }

    hintLoading = true;
    errorMessage = "";

    try {
      const payload = await requestPuzzleHint(
        session.coolId,
        { attemptId: session.attemptId },
        token,
      );

      session = {
        ...session,
        hintAvailable: false,
        hintCount: (session.hintCount ?? 0) + 1,
        points: {
          ...session.points,
          current:
            typeof payload.current_points === "number"
              ? payload.current_points
              : session.points.current,
        },
      };

      const moveUci = payload.move_uci || expected;
      guidanceShapes = buildArrowShapes(moveUci, "green");
      hintMessage = translator("puzzles.feedback.hintDisplayed");
    } catch (error) {
      const message = error instanceof Error ? error.message : translator("puzzles.error.hint");
      errorMessage = message;
      applyFallback();
    } finally {
      hintLoading = false;
    }
  };

  const handleResetMove = async () => {
    if (!session) return;
    if (session.status !== "active" || !hasSubmittedMoves()) {
      void restartCurrentPuzzle();
      return;
    }
    const boardState = playMoves(session.baseFen, session.submitted);
    session = {
      ...session,
      currentFen: boardState.fen,
    };
    syncBoardToSession({ forceReset: true });
    pendingMoveLabel = "";
    guidanceShapes = [];
    infoMessage = "";
    errorMessage = "";
    hintMessage = "";
  };

  const handleRetryPuzzle = async () => {
    void restartCurrentPuzzle();
  };

  const handleNextPuzzle = () => {
    if (!token) return;
    clearAutoAdvance();
    celebrationActive = false;
    void loadPuzzle({ difficulty: selectedDifficulty });
  };

  const handleDifficultyChange = (event) => {
    const value = event?.detail?.value;
    if (!value || loadingPuzzle) return;
    selectedDifficulty = value;
    void loadPuzzle({ difficulty: value, resetHistory: false });
  };

  const hasSubmittedMoves = () => {
    return Array.isArray(session?.submitted) && session.submitted.length > 0;
  };

  onMount(() => {
    if (token) {
      void loadPuzzle({ difficulty: selectedDifficulty, resetHistory: true });
    }
  });

  onDestroy(() => {
    clearAutoAdvance();
  });

  let lastToken = token;
  $: if (token !== lastToken) {
    lastToken = token;
    clearAutoAdvance();
    session = null;
    history = [];
    if (token) {
      void loadPuzzle({ difficulty: selectedDifficulty, resetHistory: true });
    } else {
      game.reset();
      setBoard(game.fen());
    }
  }

  $: currentPoints = session?.points?.current ?? 0;
  $: maxPoints = session?.points?.max ?? 3;
  $: timesPresented = session?.stats?.presented ?? 0;
  $: timesSolved = session?.stats?.solved ?? 0;
  $: hintCount = session?.hintCount ?? 0;
  $: attemptFinished = session ? session.status !== "active" : false;
  $: canResetCurrentAttempt = Boolean(session && !loadingPuzzle && !submittingMove && !restartingAttempt);
  $: boardInteractive = Boolean(
    session && session.status === "active" && session.attemptId && !loadingPuzzle && !restartingAttempt,
  );
  $: puzzleTitle = formatPuzzleName(session?.coolId);
  $: difficultyKey = `puzzles.difficulty.${session?.difficulty ?? selectedDifficulty}`;
  $: difficultyLabel = $t(difficultyKey);
  $: statusTone = errorMessage ? "error" : infoMessage ? "info" : hintMessage ? "hint" : "muted";
  $: statusText = errorMessage || infoMessage || hintMessage || "ready";
  $: nextPuzzleLabel = $t("puzzles.controls.nextPuzzle");
  $: retryPuzzleLabel = $t("puzzles.controls.retryPuzzle");
</script>

<section class="trainer">
  <PuzzleTrainerHeader
    {user}
    on:back={() => onBack()}
    on:logout={() => onLogout()}
  />

  <PuzzleMetaPanel
    title={puzzleTitle}
    difficultyLabel={difficultyLabel}
    sideAnnouncement={sideAnnouncement}
    statusTone={statusTone}
    statusText={statusText}
    celebrating={celebrationActive}
  />

  <div class="trainer__layout">
    <PuzzleBoardPanel
      startingFen={session?.baseFen ?? null}
      positionFen={boardFen}
      resetToken={boardResetToken}
      orientation={orientation}
      guidanceShapes={guidanceShapes}
      interactive={boardInteractive}
      attemptFinished={attemptFinished}
      loadingPuzzle={loadingPuzzle}
      nextLabel={nextPuzzleLabel}
      retryLabel={retryPuzzleLabel}
      on:move={(event) => handleBoardMove(event.detail)}
      on:next={() => handleNextPuzzle()}
      on:retry={() => handleRetryPuzzle()}
    />

    <aside class="sidebar">
      <PuzzleScoreCard
        coolId={session?.coolId ?? ""}
        difficulty={session?.difficulty ?? selectedDifficulty}
        currentPoints={currentPoints}
        maxPoints={maxPoints}
        totalPoints={totalPoints}
        timesPresented={timesPresented}
        timesSolved={timesSolved}
        hintCount={hintCount}
        status={session?.status ?? "active"}
      />

      <PuzzleControls
        {difficulties}
        {selectedDifficulty}
        loadingPuzzle={loadingPuzzle}
        hintLoading={hintLoading}
        submitLoading={submittingMove}
        hintAvailable={Boolean(session?.status === "active" && session?.hintAvailable)}
        hintUsed={(session?.hintCount ?? 0) > 0}
        hasPendingMove={Boolean(pendingMoveLabel)}
        canResetMove={canResetCurrentAttempt}
        previewAvailable={false}
        previewActive={false}
        attemptFinished={attemptFinished}
        pendingMoveLabel={pendingMoveLabel}
        disableActions={loadingPuzzle || submittingMove}
        on:difficulty={handleDifficultyChange}
        on:refresh={() => void loadPuzzle({ difficulty: selectedDifficulty })}
        on:submit={() => {}}
        on:resetMove={() => void handleResetMove()}
        on:retry={() => void handleRetryPuzzle()}
        on:hint={handleHint}
        on:preview={() => {}}
        on:next={() => handleNextPuzzle()}
      />

      <PuzzleHistory {history} />
    </aside>
  </div>
</section>

<style>
  .trainer {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    width: 100%;
    max-width: 1200px;
    padding: 1.25rem;
  }

  .trainer__layout {
    display: grid;
    grid-template-columns: minmax(0, 1.15fr) minmax(0, 0.85fr);
    gap: 1.25rem;
  }

  .sidebar {
    display: flex;
    flex-direction: column;
    gap: 1.1rem;
  }

  @media (max-width: 1024px) {
    .trainer__layout {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 768px) {
    .trainer {
      padding: 1rem;
    }

    .trainer__layout {
      gap: 1rem;
    }
  }

  @media (max-width: 680px) {
    .trainer {
      padding: 0.85rem;
      gap: 0.85rem;
    }

    .trainer__layout {
      gap: 0.85rem;
    }

    .sidebar {
      gap: 0.9rem;
    }

    :global(.score-card) {
      padding: 1rem;
      gap: 0.9rem;
    }

    :global(.score-card__grid) {
      gap: 0.85rem;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    }

    :global(.controls) {
      padding: 1rem;
      gap: 0.85rem;
    }

    :global(.controls__row) {
      gap: 0.65rem;
    }

    :global(.history) {
      padding: 1rem;
      gap: 0.8rem;
    }

    :global(.history__list) {
      gap: 0.75rem;
    }

    :global(.history__item) {
      padding: 0.75rem 0.85rem;
    }
  }
</style>
