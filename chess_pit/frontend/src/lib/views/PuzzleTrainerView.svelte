<script>
  import { onDestroy, onMount } from "svelte";
  import { get } from "svelte/store";
  import { Chess } from "chess.js";

  import ChessBoard from "../ChessBoard.svelte";
  import PuzzleScoreCard from "../puzzles/PuzzleScoreCard.svelte";
  import PuzzleControls from "../puzzles/PuzzleControls.svelte";
  import PuzzleHistory from "../puzzles/PuzzleHistory.svelte";
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
  let canResetCurrentAttempt = false;

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

  const resetTransientState = () => {
    infoMessage = "";
    errorMessage = "";
    hintMessage = "";
    guidanceShapes = [];
    pendingMoveLabel = "";
    lastSubmittedUci = "";
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
    let submitted = normalizeMoveList(submittedSource);
    if (lastSubmittedUci && !submitted.includes(lastSubmittedUci)) {
      submitted = [...submitted, lastSubmittedUci];
    }
    const playerIndices = derivePlayerMoveIndices(session.baseFen, solution, session.playerColor);
    const remainingPlayerMoves = typeof payload.remaining_moves === "number"
      ? Math.max(0, payload.remaining_moves)
      : computeRemainingPlayerMoves(submitted.length, playerIndices);

    const boardState = playMoves(session.baseFen, submitted);
    const nextFen = normalizeFen(payload.board_fen) ?? boardState.fen ?? session.currentFen;

    session = {
      ...session,
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
    if (!session || !token || loadingPuzzle) return;

    clearAutoAdvance();
    loadingPuzzle = true;
    submittingMove = false;
    hintLoading = false;
    resetTransientState();
    celebrationActive = false;

    const translator = get(t);

    try {
      const payload = await restartPuzzleAttempt(session.coolId, token);
      const resolvedDifficulty = payload?.difficulty ?? session.difficulty ?? selectedDifficulty;
      session = buildSessionFromPayload(payload, resolvedDifficulty);
      if (typeof payload.total_user_points === "number") {
        totalPoints = payload.total_user_points;
      }
      selectedDifficulty = resolvedDifficulty;

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
      errorMessage = "";
    } catch (error) {
      const message = error instanceof Error ? error.message : translator("puzzles.error.load");
      errorMessage = message;
      syncBoardToSession({ forceReset: true });
    } finally {
      loadingPuzzle = false;
    }
  };

  const handleSubmissionResponse = async (payload) => {
    if (!session) return;

    const translator = get(t);
    const previousStatus = session?.status ?? null;
    applySubmissionPayload(payload);
    if ((session?.status ?? previousStatus) !== "solved") {
      syncBoardToSession();
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
      await restartCurrentPuzzle();
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

    submittingMove = false;
    pendingMoveLabel = "";
    lastSubmittedUci = "";
  };

  const handleSubmissionError = (error) => {
    const translator = get(t);
    const message = error instanceof Error ? error.message : translator("puzzles.error.submit");
    errorMessage = message;
    submittingMove = false;
    pendingMoveLabel = "";
    lastSubmittedUci = "";
    celebrationActive = false;
    syncBoardToSession({ forceReset: true });
  };

  const handleBoardMove = (detail) => {
    if (!session || session.status !== "active" || submittingMove || loadingPuzzle) {
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

    submittingMove = true;
    errorMessage = "";
    infoMessage = "";
    hintMessage = "";
    guidanceShapes = [];
    pendingMoveLabel = moveDetail.san || formatSanForMove(session.baseFen, session.submitted, uci);
    lastSubmittedUci = uci;

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
      })
      .finally(() => {
        if (!session || session.status !== "active") {
          guidanceShapes = [];
        }
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
      await restartCurrentPuzzle();
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
    await restartCurrentPuzzle();
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
  $: canResetCurrentAttempt = Boolean(session && !loadingPuzzle && !submittingMove);
  $: boardInteractive = Boolean(session && session.status === "active" && !loadingPuzzle && !submittingMove);
  $: puzzleTitle = formatPuzzleName(session?.coolId);
  $: statusTone = errorMessage ? "error" : infoMessage ? "info" : hintMessage ? "hint" : "muted";
  $: statusText = errorMessage || infoMessage || hintMessage || "ready";
</script>

<section class="trainer">
  <header class="trainer__header">
    <div class="trainer__left">
      <button type="button" class="back" on:click={onBack}>
        {$t("puzzles.header.back")}
      </button>
      <h1>{$t("puzzles.header.title")}</h1>
      <p class="trainer__subtitle">{$t("puzzles.header.tagline")}</p>
    </div>
    <div class="trainer__actions">
      {#if user}
        <div class="trainer__user">
          <span class="trainer__avatar" aria-hidden="true">♟</span>
          <span>{user.username ?? $t("puzzles.header.player")}</span>
        </div>
      {/if}
      <button type="button" class="ghost" on:click={onLogout}>
        {$t("puzzles.header.logout")}
      </button>
    </div>
  </header>

  <section class="puzzle-meta" aria-live="polite">
    <div class="puzzle-meta__title" data-celebrating={celebrationActive}>
      <span class="puzzle-meta__glyph" aria-hidden="true">♞</span>
      <span class="puzzle-meta__name">{puzzleTitle}</span>
      <span class="puzzle-meta__glyph" aria-hidden="true">♘</span>
    </div>
    <div class="puzzle-meta__details">
      <span class="chip chip--difficulty">
        {$t(`puzzles.difficulty.${session?.difficulty ?? selectedDifficulty}`)}
      </span>
      {#if sideAnnouncement}
        <span class="chip chip--side">{sideAnnouncement}</span>
      {/if}
      <span class={`chip chip--${statusTone}`}>{statusText}</span>
    </div>
  </section>

  <div class="trainer__layout">
    <section class="board-panel">
      <ChessBoard
        startingFen={session?.baseFen ?? null}
        positionFen={boardFen}
        resetToken={boardResetToken}
        orientation={orientation}
        guidanceShapes={guidanceShapes}
        onMove={handleBoardMove}
        interactive={boardInteractive}
        showStatus={false}
        showControls={false}
      />
    </section>

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

  .trainer__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
  }

  .trainer__left {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }

  h1 {
    margin: 0;
    font-size: 1.6rem;
    letter-spacing: 0.06em;
    color: #f8fafc;
  }

  .trainer__subtitle {
    margin: 0;
    color: rgba(148, 163, 184, 0.75);
    font-size: 0.9rem;
    letter-spacing: 0.04em;
  }

  .trainer__actions {
    display: flex;
    gap: 0.65rem;
    align-items: center;
  }

  .trainer__user {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    background: rgba(15, 23, 42, 0.45);
    border: 1px solid rgba(148, 163, 184, 0.25);
    padding: 0.4rem 0.8rem;
    border-radius: 999px;
    font-size: 0.9rem;
    color: #e2e8f0;
  }

  .trainer__avatar {
    font-size: 1.1rem;
  }

  .ghost,
  .back {
    border: 1px solid rgba(148, 163, 184, 0.3);
    background: rgba(15, 23, 42, 0.65);
    color: #e2e8f0;
    padding: 0.55rem 0.9rem;
    border-radius: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: transform 0.18s ease, box-shadow 0.18s ease;
  }

  .ghost:hover,
  .back:hover {
    transform: translateY(-1px);
    box-shadow: 0 10px 22px rgba(15, 23, 42, 0.35);
  }

  .back {
    align-self: flex-start;
  }

  .puzzle-meta {
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
    padding: 0.9rem 1.2rem;
    border-radius: 16px;
    background: rgba(15, 23, 42, 0.5);
    border: 1px solid rgba(148, 163, 184, 0.22);
    box-shadow: 0 12px 28px rgba(15, 23, 42, 0.3);
    font-family: "IBM Plex Mono", "Fira Code", "Menlo", monospace;
  }

  .puzzle-meta__title {
    display: flex;
    align-items: baseline;
    justify-content: center;
    gap: 0.75rem;
    font-size: 1.25rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #e2e8f0;
  }

  .puzzle-meta__title[data-celebrating="true"] {
    color: #facc15;
    text-shadow: 0 0 14px rgba(250, 204, 21, 0.4);
  }

  .puzzle-meta__glyph {
    font-size: 1.2rem;
    opacity: 0.8;
  }

  .puzzle-meta__name {
    font-size: 1.1em;
    white-space: nowrap;
  }

  .puzzle-meta__details {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 0.5rem;
  }

  .chip {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.35rem 0.75rem;
    border-radius: 999px;
    font-size: 0.8rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    border: 1px solid transparent;
  }

  .chip--difficulty {
    background: rgba(59, 130, 246, 0.18);
    border-color: rgba(59, 130, 246, 0.35);
    color: #bfdbfe;
  }

  .chip--side {
    background: rgba(148, 163, 184, 0.18);
    border-color: rgba(148, 163, 184, 0.28);
    color: rgba(226, 232, 240, 0.9);
  }

  .chip--info {
    background: rgba(20, 184, 166, 0.18);
    border-color: rgba(16, 185, 129, 0.32);
    color: #99f6e4;
  }

  .chip--error {
    background: rgba(248, 113, 113, 0.16);
    border-color: rgba(239, 68, 68, 0.32);
    color: #fecaca;
  }

  .chip--hint {
    background: rgba(234, 179, 8, 0.16);
    border-color: rgba(234, 179, 8, 0.28);
    color: #fef9c3;
  }

  .chip--muted {
    background: rgba(100, 116, 139, 0.18);
    border-color: rgba(100, 116, 139, 0.28);
    color: rgba(226, 232, 240, 0.75);
  }

  .trainer__layout {
    display: grid;
    grid-template-columns: minmax(0, 1.15fr) minmax(0, 0.85fr);
    gap: 1.25rem;
  }

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

    .trainer__header {
      flex-direction: column;
      align-items: flex-start;
      gap: 0.75rem;
    }

    .trainer__actions {
      width: 100%;
      justify-content: space-between;
    }

    .puzzle-meta {
      padding: 0.8rem 1rem;
    }

    .puzzle-meta__title {
      font-size: 1.15rem;
    }
  }
</style>
