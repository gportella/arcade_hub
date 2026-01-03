<script>
    import { onMount, onDestroy } from "svelte";
    import { t } from "../i18n";

    let logId = 0;
    function stamp() {
        return (++logId).toString().padStart(4, "0");
    }
    onMount(() => console.debug(`[${stamp()}] [mount] ChessBoard`));
    onDestroy(() => console.debug(`[${stamp()}] [destroy] ChessBoard`));
    import ChessBoard from "../ChessBoard.svelte";
    import GameAnalysisViewer from "../GameAnalysisViewer.svelte";
    import GameVictoryBadge from "../games/GameVictoryBadge.svelte";
    import { evaluationToWdl, toPercentage } from "../utils/evaluation";
    import { createClockStore, formatClock as formatClockDisplay } from "../stores/clocks";

    /** @type {any} */
    export let game = null;
    export let formatTime = (_iso) => "";
    export let gameStatusLabel = (_game) => "";
    export let onMove = (_event) => {};
    export let onUndo = (_event) => {};
    export let onResign = () => {};
    export let onBack = () => {};
    export let onLogout = () => {};
    export let analysisEngine = null;
    export let analysisResult = null;
    export let analysisError = "";
    export let isAnalysisLoading = false;
    export let analysisFetchedAt = null;
    export let onAnalyze = () => {};
    export let analysisSteps = [];

    let analysisReplayActive = false;
    let analysisFocusIndex = null;

    const analysisMissingValue = "-";
    const clock = createClockStore();
    const SILVER_DELTA_THRESHOLD = 15;
    const BRONZE_DELTA_THRESHOLD = 1;

    const isCriticalClock = (value) =>
        typeof value === "number" && Number.isFinite(value) && value <= 10;

    const formatTimeControlLabel = (initialSeconds, incrementSeconds) => {
        if (initialSeconds === null || initialSeconds === undefined) {
            return $t("play.clock.unlimited");
        }
        const minutes = Math.floor(initialSeconds / 60);
        const seconds = initialSeconds % 60;
        const pieces = [];
        if (minutes > 0) {
            pieces.push(`${minutes}${$t("play.clock.minutesSuffix")}`);
        }
        if (seconds > 0 || pieces.length === 0) {
            pieces.push(`${seconds}${$t("play.clock.secondsSuffix")}`);
        }
        if (
            typeof incrementSeconds === "number" &&
            Number.isFinite(incrementSeconds) &&
            incrementSeconds > 0
        ) {
            pieces.push(
                $t("play.clock.increment", {
                    value: incrementSeconds,
                    unit: $t("play.clock.secondsSuffix"),
                }),
            );
        }
        return pieces.join(" ");
    };

    const normalizeSanString = (value) =>
        typeof value === "string" ? value.replace(/[+#?!]/g, "").trim() : "";

    const formatMate = (mateValue) => {
        if (typeof mateValue !== "number" || mateValue === 0) {
            return "";
        }
        const moves = Math.abs(mateValue);
        const colorKey = mateValue > 0 ? "analysis.mateWhite" : "analysis.mateBlack";
        return $t("analysis.mate", { moves, color: $t(colorKey) });
    };

    const formatEvaluation = (cpValue, mateValue) => {
        if (typeof mateValue === "number" && mateValue !== 0) {
            return formatMate(mateValue);
        }
        if (typeof cpValue !== "number") {
            return $t("analysis.noScore");
        }
        const score = cpValue / 100;
        const digits = Math.abs(score) >= 10 ? 1 : 2;
        const formatted = score.toFixed(digits);
        const sign = score > 0 ? "+" : "";
        return `${sign}${formatted}`;
    };

    const formatDelta = (before, after, fallback) => {
        if (typeof before !== "number" || typeof after !== "number") {
            return fallback;
        }
        const delta = after - before;
        if (delta === 0) {
            return "0.00";
        }
        const value = delta / 100;
        const digits = Math.abs(value) >= 10 ? 1 : 2;
        const formatted = value.toFixed(digits);
        const sign = value > 0 ? "+" : "";
        return `${sign}${formatted}`;
    };

    const classifyMoveQuality = (step, { isBestMatch }) => {
        if (typeof step.played_san === "string" && step.played_san.includes("#")) {
            return {
                marker: "#",
                labelKey: "analysis.annotation.checkmate",
            };
        }
        if (isBestMatch) {
            return {
                marker: "!!",
                labelKey: "analysis.annotation.brilliant",
            };
        }

        const beforeCp = step.evaluation_before_cp;
        const afterCp = step.evaluation_after_cp;

        if (typeof beforeCp === "number" && typeof afterCp === "number") {
            const deltaCp = afterCp - beforeCp;
            const normalized = step.turn === "white" ? deltaCp : -deltaCp;
            if (Number.isFinite(normalized)) {
                if (normalized >= 150) {
                    return {
                        marker: "!!",
                        labelKey: "analysis.annotation.brilliant",
                    };
                }
                if (normalized >= 70) {
                    return {
                        marker: "!",
                        labelKey: "analysis.annotation.strong",
                    };
                }
                if (normalized >= 35) {
                    return {
                        marker: "!?",
                        labelKey: "analysis.annotation.interesting",
                    };
                }
                if (normalized <= -220) {
                    return {
                        marker: "??",
                        labelKey: "analysis.annotation.blunder",
                    };
                }
                if (normalized <= -140) {
                    return {
                        marker: "?",
                        labelKey: "analysis.annotation.mistake",
                    };
                }
                if (normalized <= -70) {
                    return {
                        marker: "?!",
                        labelKey: "analysis.annotation.dubious",
                    };
                }
            }
        }

        const mateBefore = step.mate_before;
        const mateAfter = step.mate_after;
        if (typeof mateBefore === "number" || typeof mateAfter === "number") {
            const before = typeof mateBefore === "number" ? mateBefore : null;
            const after = typeof mateAfter === "number" ? mateAfter : null;
            if (before !== null && after !== null) {
                const normalizedMate = step.turn === "white" ? before - after : after - before;
                if (normalizedMate > 0) {
                    return {
                        marker: "!!",
                        labelKey: "analysis.annotation.brilliant",
                    };
                }
                if (normalizedMate < 0) {
                    const severity = Math.abs(normalizedMate);
                    if (severity >= 2) {
                        return {
                            marker: "??",
                            labelKey: "analysis.annotation.blunder",
                        };
                    }
                    return {
                        marker: "?",
                        labelKey: "analysis.annotation.mistake",
                    };
                }
            } else if (before === null && after !== null && after > 0) {
                return {
                    marker: "!!",
                    labelKey: "analysis.annotation.brilliant",
                };
            } else if (before !== null && before > 0 && after === null) {
                return {
                    marker: "??",
                    labelKey: "analysis.annotation.blunder",
                };
            }
        }

        return { marker: "", labelKey: "" };
    };

    const isActiveGame = () =>
        game?.status === "active" || game?.status === "pending";
    let boardRef;
    let yourTurn = false;

    // Track the last FEN to prevent unnecessary updates
    let lastGameFen = null;
    let stablePositionFen = null;
    let fenUpdateCounter = 0;

    const handleUndoClick = () => {
        if (!yourTurn) return;
        boardRef?.undoMove();
    };

    const handleResignClick = () => {
        if (!active) return;
        onResign();
    };

    $: active = isActiveGame();
    $: yourTurn = active && game?.turn === game?.yourColor;
    $: opponentNameRaw = game?.opponent?.nickname ?? "";
    $: opponentName = opponentNameRaw && opponentNameRaw.trim()
        ? opponentNameRaw
        : $t("label.unknown");
    $: opponentAvatar = game?.opponent?.avatar ?? "";
    $: lastUpdated = game ? formatTime(game.lastUpdated) : "";
    $: statusLabel = game ? gameStatusLabel(game) : "";
    $: colorTitle = game
        ? $t(game.yourColor === "black" ? "color.black" : "color.white")
        : "";
    $: colorLower = game
        ? $t(
              game.yourColor === "black"
                  ? "color.blackLower"
                  : "color.whiteLower",
          )
        : "";
    $: resultLabel = game?.resultDisplay ?? null;
    $: summary = game?.summary ?? "";
    $: pgn = game?.pgn ?? "";
    $: summaryText = summary && summary.trim()
        ? summary.trim()
        : $t("game.summary.default");
    $: metaLine = game ? $t("play.meta", { colorTitle, colorLower }) : "";
    $: updatedLine = game && lastUpdated
        ? $t("play.updated", { time: lastUpdated })
        : "";
    $: backLabel = $t("play.back");
    $: backAria = $t("play.backAria");
    $: logoutLabel = $t("play.logout");
    $: boardControlsLabel = $t("play.controls.board");
    $: resignLabel = $t("play.controls.resign");
    $: summaryHeading = $t("play.info.summary");
    $: resultHeading = $t("play.info.result");
    $: pgnHeading = $t("play.info.pgn");
    $: clockHeading = $t("play.clock.heading");
    $: clockControlLabel = $t("play.clock.label");
    $: clockWhiteLabel = $t("color.white");
    $: clockBlackLabel = $t("color.black");
    $: emptyText = $t("play.placeholder");
    $: opponentAlt = $t("avatar.label", { name: opponentName });
    $: analysisHeading = $t("analysis.heading");
    $: analysisLoadingText = $t("analysis.loading");
    $: analysisPendingText = $t("analysis.pending");
    $: analysisEngineLabel = $t("analysis.field.engine");
    $: analysisDepthLabel = $t("analysis.field.depth");
    $: analysisScoreLabel = $t("analysis.field.score");
    $: analysisMateLabel = $t("analysis.field.mate");
    $: analysisBestMoveLabel = $t("analysis.field.bestMove");
    $: analysisLineLabel = $t("analysis.field.variation");
    $: analysisEngineFallback = $t("analysis.engineFallback");
    $: analysisEngineName =
        analysisResult?.engine?.name ?? analysisEngine?.name ?? "";
    $: analysisEngineKey = analysisEngine?.key ?? analysisResult?.engine?.key ?? null;
    $: analysisHasEngine = Boolean(analysisEngineKey);
    $: analysisCanRequest = Boolean(
        game?.status === "completed" && analysisHasEngine,
    );
    $: analysisUnavailableMessage = (() => {
        if (!analysisHasEngine) {
            return $t("analysis.unavailable.engine");
        }
        if (!game || game.status !== "completed") {
            return $t("analysis.unavailable.status");
        }
        return "";
    })();
    $: engineKeyLower = (game?.opponent?.engineKey || "").toLowerCase();
    $: engineDepth = typeof game?.engineDepth === "number" && Number.isFinite(game.engineDepth)
        ? Math.round(game.engineDepth)
        : null;
    $: ratingDelta = typeof game?.ratingDelta === "number" && Number.isFinite(game.ratingDelta)
        ? Math.round(game.ratingDelta)
        : 0;
    $: playerWon = Boolean(
        game &&
            game.status === "completed" &&
            ((game.result === "white" && game.yourColor === "white") ||
                (game.result === "black" && game.yourColor === "black")),
    );
    $: qualifiesGold = Boolean(
        playerWon &&
            game?.opponent?.isEngine &&
            engineDepth !== null &&
            engineDepth >= 6 &&
            (engineKeyLower === "skaks" || engineKeyLower === "stockfish"),
    );
    $: rawVictoryReward = (() => {
        if (!playerWon) {
            return null;
        }
        if (qualifiesGold) {
            return {
                level: "gold",
                engineName: game?.opponent?.nickname || "",
                engineDepth,
            };
        }
        if (ratingDelta >= SILVER_DELTA_THRESHOLD) {
            return {
                level: "silver",
                ratingDelta,
            };
        }
        if (ratingDelta >= BRONZE_DELTA_THRESHOLD) {
            return {
                level: "bronze",
                ratingDelta,
            };
        }
        return null;
    })();
    $: victoryReward = rawVictoryReward
        ? {
              level: rawVictoryReward.level,
              title: $t(`play.reward.title.${rawVictoryReward.level}`),
              subtitle:
                  rawVictoryReward.level === "gold"
                      ? (() => {
                            const engineName = rawVictoryReward.engineName?.trim();
                            if (engineName) {
                                return $t("play.reward.reason.engine", {
                                    engine: engineName,
                                    depth: rawVictoryReward.engineDepth ?? 0,
                                });
                            }
                            return $t("play.reward.reason.engineFallback", {
                                depth: rawVictoryReward.engineDepth ?? 0,
                            });
                        })()
                      : $t("play.reward.reason.rating", {
                            delta: Math.abs(rawVictoryReward.ratingDelta ?? 0),
                        }),
          }
        : null;
    $: analysisRunLabel = isAnalysisLoading
        ? $t("analysis.running")
        : $t("analysis.button", {
              engine: analysisEngineName || analysisEngineFallback,
          });
    $: analysisButtonDisabled = !analysisCanRequest || isAnalysisLoading;
    $: analysisSummary = analysisResult;
    $: analysisFinalStep = (Array.isArray(analysisSteps) && analysisSteps.length)
        ? analysisSteps[analysisSteps.length - 1]
        : null;
    $: analysisHasResult = Boolean(analysisSummary || (analysisSteps && analysisSteps.length));
    $: analysisScoreFallback = formatEvaluation(
        analysisSummary?.evaluation_cp ??
            analysisFinalStep?.evaluation_after_cp ??
            analysisFinalStep?.evaluation_before_cp ??
            null,
        analysisSummary?.mate_in ??
            analysisFinalStep?.mate_after ??
            analysisFinalStep?.mate_before ??
            null,
    );
    $: analysisDepthDisplay = (() => {
        if (analysisSummary?.depth) {
            return String(analysisSummary.depth);
        }
        if (analysisSummary?.engine?.default_depth) {
            return String(analysisSummary.engine.default_depth);
        }
        if (analysisEngine?.default_depth) {
            return String(analysisEngine.default_depth);
        }
        return analysisMissingValue;
    })();
    $: analysisLastRunText = analysisFetchedAt
        ? $t("analysis.lastRun", { time: formatTime(analysisFetchedAt) })
        : "";
    $: analysisSectionVisible = Boolean(
        game &&
            (game.status === "completed" ||
                analysisHasResult ||
                isAnalysisLoading ||
                analysisError),
    );
    $: analysisTimelineMoveTemplate = (params) =>
        $t("analysis.timeline.move", params);
    $: analysisTimelineNoDelta = $t("analysis.timeline.noDelta");
    $: analysisProbabilityLabels = {
        heading: $t("analysis.probability.heading"),
        timeline: $t("analysis.probability.timeline"),
        aria: $t("analysis.probability.aria"),
        white: $t("analysis.probability.white"),
        draw: $t("analysis.probability.draw"),
        black: $t("analysis.probability.black"),
    };
    $: analysisViewerSteps = (Array.isArray(analysisSteps) ? analysisSteps : []).map(
        (step) => {
            const moveNumber = Math.ceil(step.move_number / 2);
            const playerLabel =
                step.turn === "white" ? $t("color.white") : $t("color.black");
            const evalBefore = formatEvaluation(step.evaluation_before_cp, step.mate_before);
            const evalAfter = formatEvaluation(step.evaluation_after_cp, step.mate_after);
            const delta = formatDelta(step.evaluation_before_cp, step.evaluation_after_cp, analysisTimelineNoDelta);
            const bestText = (() => {
                if (step.best_move_san) {
                    return step.best_move_san;
                }
                if (step.best_move_uci) {
                    return step.best_move_uci;
                }
                return $t("analysis.noBest");
            })();
            const variation = step.best_line_san?.length
                ? step.best_line_san.join(" ")
                : $t("analysis.noLine");
            const hasBest = Boolean(step.best_move_san || step.best_move_uci);
            const isBestMatch = hasBest
                ? normalizeSanString(step.best_move_san || step.best_move_uci) ===
                  normalizeSanString(step.played_san || step.played_uci)
                : false;
            const { marker, labelKey } = classifyMoveQuality(step, { isBestMatch });
            const probabilities = evaluationToWdl({
                evaluationCp: step.evaluation_after_cp,
                mateIn: step.mate_after,
            });
            const probabilityPercents = {
                white: toPercentage(probabilities.white),
                draw: toPercentage(probabilities.draw),
                black: toPercentage(probabilities.black),
            };
            return {
                id: step.move_index,
                title: analysisTimelineMoveTemplate({ number: moveNumber, player: playerLabel }),
                played: step.played_san ?? step.played_uci ?? analysisMissingValue,
                evalBefore,
                evalAfter,
                delta,
                best: bestText,
                variation,
                isBestMatch,
                hasBest,
                annotation: marker,
                annotationLabel: labelKey ? $t(labelKey) : "",
                probabilities,
                probabilityPercents,
                evaluationBeforeCp: step.evaluation_before_cp ?? null,
                evaluationAfterCp: step.evaluation_after_cp ?? null,
                mateBefore: step.mate_before ?? null,
                mateAfter: step.mate_after ?? null,
                bestMoveSan: step.best_move_san ?? null,
                bestMoveUci: step.best_move_uci ?? null,
            };
        },
    );
    $: analysisProbabilityTimeline = analysisViewerSteps.map((entry, idx) => ({
        white: entry.probabilities?.white ?? 0,
        draw: entry.probabilities?.draw ?? 0,
        black: entry.probabilities?.black ?? 0,
        whitePercent: entry.probabilityPercents?.white ?? null,
        drawPercent: entry.probabilityPercents?.draw ?? null,
        blackPercent: entry.probabilityPercents?.black ?? null,
        label: entry.title,
        ply: idx + 1,
    }));
    $: clockInitialSeconds =
        typeof game?.timeControlInitialSeconds === "number" &&
        Number.isFinite(game.timeControlInitialSeconds)
            ? game.timeControlInitialSeconds
            : null;
    $: clockIncrementSeconds =
        typeof game?.timeControlIncrementSeconds === "number" &&
        Number.isFinite(game.timeControlIncrementSeconds)
            ? game.timeControlIncrementSeconds
            : null;
    $: clockSectionVisible = clockInitialSeconds !== null;
    $: clockSummaryLabel = clockSectionVisible
        ? formatTimeControlLabel(clockInitialSeconds, clockIncrementSeconds)
        : "";
    $: clockIsActive = Boolean(
        clockSectionVisible &&
            (game?.status === "active" || game?.status === "pending") &&
            game?.turnStartTime,
    );
    $: if (game) {
        const fallback = clockSectionVisible ? clockInitialSeconds : null;
        clock.updateFromServer({
            whiteRemaining:
                typeof game.whiteTimeRemainingSeconds === "number" &&
                Number.isFinite(game.whiteTimeRemainingSeconds)
                    ? game.whiteTimeRemainingSeconds
                    : fallback,
            blackRemaining:
                typeof game.blackTimeRemainingSeconds === "number" &&
                Number.isFinite(game.blackTimeRemainingSeconds)
                    ? game.blackTimeRemainingSeconds
                    : fallback,
            turnStartTime: game.turnStartTime ?? null,
            active: clockSectionVisible && clockIsActive,
            activeColor: game.turn ?? "white",
        });
    }
    $: whiteClockDisplay = formatClockDisplay($clock.whiteRemaining);
    $: blackClockDisplay = formatClockDisplay($clock.blackRemaining);
    $: whiteClockActive = Boolean($clock.running && $clock.activeColor === "white");
    $: blackClockActive = Boolean($clock.running && $clock.activeColor === "black");
    $: whiteClockCritical = isCriticalClock($clock.whiteRemaining);
    $: blackClockCritical = isCriticalClock($clock.blackRemaining);
    $: analysisViewerStepCount = analysisViewerSteps.length;
    $: {
        const total = analysisViewerStepCount;
        if (!total) {
            analysisFocusIndex = null;
        } else if (
            typeof analysisFocusIndex === "number" &&
            analysisFocusIndex >= total
        ) {
            analysisFocusIndex = total - 1;
        } else if (analysisFocusIndex === null && !analysisReplayActive) {
            analysisFocusIndex = total - 1;
        }
    }
    $: analysisViewerEntry =
        typeof analysisFocusIndex === "number" && analysisFocusIndex >= 0 &&
        analysisFocusIndex < analysisViewerStepCount
            ? analysisViewerSteps[analysisFocusIndex]
            : null;
    $: analysisScoreText = analysisViewerEntry?.evalAfter ?? analysisScoreFallback;
    $: analysisMateText = (() => {
        const activeMate = (() => {
            if (typeof analysisViewerEntry?.mateAfter === "number" && analysisViewerEntry.mateAfter !== 0) {
                return analysisViewerEntry.mateAfter;
            }
            if (typeof analysisViewerEntry?.mateBefore === "number" && analysisViewerEntry.mateBefore !== 0) {
                return analysisViewerEntry.mateBefore;
            }
            return null;
        })();
        if (typeof activeMate === "number") {
            return formatMate(activeMate);
        }
        const fallbackMate =
            analysisSummary?.mate_in ??
            analysisFinalStep?.mate_after ??
            analysisFinalStep?.mate_before ??
            null;
        if (typeof fallbackMate === "number" && fallbackMate !== 0) {
            return formatMate(fallbackMate);
        }
        return "";
    })();
    $: analysisBestMoveText = (() => {
        const activeBest = analysisViewerEntry?.best;
        if (activeBest && activeBest !== $t("analysis.noBest")) {
            return activeBest;
        }
        const activeBestSan = analysisViewerEntry?.bestMoveSan;
        if (activeBestSan) {
            return activeBestSan;
        }
        const activeBestUci = analysisViewerEntry?.bestMoveUci;
        if (activeBestUci) {
            return activeBestUci;
        }
        const final = analysisFinalStep;
        if (final?.best_move_san) {
            return final.best_move_san;
        }
        if (final?.best_move_uci) {
            return final.best_move_uci;
        }
        return $t("analysis.noBest");
    })();
    $: analysisLineDisplay = (() => {
        const activeLine = analysisViewerEntry?.variation;
        if (activeLine && activeLine !== $t("analysis.noLine")) {
            return activeLine;
        }
        const finalLine = analysisFinalStep?.best_line_san;
        if (finalLine && finalLine.length) {
            return finalLine.join(" ");
        }
        return $t("analysis.noLine");
    })();
    $: analysisShowSummaryDetails = !analysisViewerEntry;
    $: analysisViewerCounter =
        typeof analysisFocusIndex === "number" &&
        analysisViewerStepCount
            ? $t("analysis.viewer.counter", {
                  current: analysisFocusIndex + 1,
                  total: analysisViewerStepCount,
              })
            : "";
    $: analysisViewerBaseLabels = {
        heading: $t("analysis.viewer.heading"),
        played: $t("analysis.timeline.played"),
        evalBefore: $t("analysis.timeline.evalBefore"),
        evalAfter: $t("analysis.timeline.evalAfter"),
        delta: $t("analysis.timeline.delta"),
        best: $t("analysis.timeline.best"),
        variation: $t("analysis.timeline.variation"),
        prev: $t("analysis.viewer.prev"),
        next: $t("analysis.viewer.next"),
        close: $t("analysis.viewer.close"),
        sliderAria: $t("analysis.viewer.sliderAria"),
        empty: $t("analysis.viewer.empty"),
    };
    $: analysisViewerLabels = {
        ...analysisViewerBaseLabels,
        counter: analysisViewerCounter,
    };
    $: analysisAnnotationsByIndex = analysisViewerSteps.reduce(
        (result, entry) => {
            if (entry.annotation) {
                result[entry.id] = {
                    marker: entry.annotation,
                    label: entry.annotationLabel,
                };
            }
            return result;
        },
        {},
    );

    const handleAnalyzeClick = () => {
        if (!analysisCanRequest || isAnalysisLoading) {
            return;
        }
        const engineKey = analysisEngine?.key ?? analysisResult?.engine?.key ?? undefined;
        onAnalyze({ engineKey });
    };

    const handleReplayStateChange = (detail) => {
        analysisReplayActive = Boolean(detail?.active);
        if (!analysisReplayActive && analysisViewerStepCount) {
            analysisFocusIndex = analysisViewerStepCount - 1;
        }
    };

    const handleReplayPositionChange = (detail) => {
        if (detail && "active" in detail) {
            analysisReplayActive = Boolean(detail.active);
        }
        const total = analysisViewerStepCount;
        const nextIndex =
            typeof detail?.index === "number" && detail.index >= 0 && total
                ? Math.min(detail.index, total - 1)
                : null;
        const resolvedActive = detail?.active ?? analysisReplayActive;
        if (nextIndex === null) {
            if (resolvedActive) {
                analysisFocusIndex = null;
            }
            return;
        }
        analysisFocusIndex = nextIndex;
    };

    function seekAnalysisIndex(targetIndex) {
        if (!analysisViewerStepCount) {
            return;
        }
        if (!boardRef?.seekReplay) {
            return;
        }
        const clamped = Math.max(
            0,
            Math.min(targetIndex, analysisViewerStepCount - 1),
        );
        analysisFocusIndex = clamped;
        boardRef.seekReplay(clamped);
    }

    const handleViewerSeek = (targetIndex) => {
        if (typeof targetIndex !== "number" || !Number.isFinite(targetIndex)) {
            return;
        }
        seekAnalysisIndex(targetIndex);
    };

    const handleViewerPrev = () => {
        if (!analysisViewerStepCount) {
            return;
        }
        const base =
            typeof analysisFocusIndex === "number" ? analysisFocusIndex : 0;
        const nextIndex = Math.max(base - 1, 0);
        seekAnalysisIndex(nextIndex);
    };

    const handleViewerNext = () => {
        if (!analysisViewerStepCount) {
            return;
        }
        const base =
            typeof analysisFocusIndex === "number" ? analysisFocusIndex : -1;
        const nextIndex = Math.min(
            base + 1,
            Math.max(analysisViewerStepCount - 1, 0),
        );
        seekAnalysisIndex(nextIndex);
    };

    const handleViewerClose = () => {
        if (boardRef?.exitReplayMode) {
            boardRef.exitReplayMode();
        }
    };

    // Only update stablePositionFen when game.fen actually changes
    $: if (game?.fen && game.fen !== lastGameFen) {
        lastGameFen = game.fen;
        stablePositionFen = game.fen;
    }
</script>

{#if game}
    <main class="play">
        <header class="play-header">
            <button class="ghost" on:click={onBack} aria-label={backAria}>
                {backLabel}
            </button>
            <div class="match-overview">
                <div class="opponent">
                    <img
                        src={opponentAvatar}
                        alt={opponentAlt}
                    />
                    <div>
                        <h1>{opponentName}</h1>
                        <p class="meta">
                            {metaLine}
                            {#if statusLabel}
                                · {statusLabel}
                            {/if}
                        </p>
                    </div>
                </div>
                <p class="timestamp">{updatedLine}</p>
            </div>
            <button class="secondary micro" on:click={onLogout}>
                {logoutLabel}
            </button>
        </header>

        <div class="play-body">
            <section class="board-section">
                {#if clockSectionVisible}
                    <div class="clock-panel" aria-label={clockHeading}>
                        <div class="clock-header">
                            <h2>{clockHeading}</h2>
                            {#if clockSummaryLabel}
                                <span class="clock-summary">
                                    {clockControlLabel}: {clockSummaryLabel}
                                </span>
                            {/if}
                        </div>
                        <div class="clock-rows">
                            <div
                                class="clock-row"
                                class:active={whiteClockActive}
                                class:critical={whiteClockCritical}
                            >
                                <span class="clock-label">{clockWhiteLabel}</span>
                                <span class="clock-value">{whiteClockDisplay}
                                    {#if clockIncrementSeconds}
                                        <small class="clock-increment">+{clockIncrementSeconds}s</small>
                                    {/if}
                                </span>
                            </div>
                            <div
                                class="clock-row"
                                class:active={blackClockActive}
                                class:critical={blackClockCritical}
                            >
                                <span class="clock-label">{clockBlackLabel}</span>
                                <span class="clock-value">{blackClockDisplay}
                                    {#if clockIncrementSeconds}
                                        <small class="clock-increment">+{clockIncrementSeconds}s</small>
                                    {/if}
                                </span>
                            </div>
                        </div>
                    </div>
                {/if}
                <ChessBoard
                    bind:this={boardRef}
                    startingFen={game.initialFen}
                    positionFen={stablePositionFen}
                    resetToken={game.id}
                    orientation={game.yourColor}
                    {onMove}
                    {onUndo}
                    showStatus={false}
                    showControls={false}
                    interactive={yourTurn}
                    {pgn}
                    analysisSteps={analysisSteps}
                    analysisAnnotations={analysisAnnotationsByIndex}
                    onReplayPositionChange={handleReplayPositionChange}
                    onReplayStateChange={handleReplayStateChange}
                />
                {#if active}
                    <div class="board-controls" aria-label={boardControlsLabel}>
                        <!--
                <button
                class="pill"
                on:click={handleUndoClick}
                disabled={!yourTurn}
                >
                Undo
                </button>
                -->
                        <button class="pill resign" on:click={handleResignClick}>
                            {resignLabel}
                        </button>
                    </div>
                {/if}
            </section>

            <section class="game-info">
            {#if victoryReward}
                <GameVictoryBadge
                    level={victoryReward.level}
                    title={victoryReward.title}
                    subtitle={victoryReward.subtitle}
                    celebrating={victoryReward.level === "gold"}
                />
            {/if}
            {#if analysisSectionVisible}
                <div class="info-card analysis-card">
                    <div class="analysis-top">
                        <h2>{analysisHeading}</h2>
                        <button
                            class="secondary micro"
                            on:click={handleAnalyzeClick}
                            disabled={analysisButtonDisabled}
                        >
                            {analysisRunLabel}
                        </button>
                    </div>

                    {#if analysisError}
                        <p class="analysis-error" role="alert">{analysisError}</p>
                    {:else if isAnalysisLoading}
                        <p class="analysis-status">{analysisLoadingText}</p>
                    {:else if !analysisCanRequest}
                        <p class="analysis-status">{analysisUnavailableMessage}</p>
                    {:else if analysisHasResult}
                        <dl class="analysis-grid">
                            <div>
                                <dt>{analysisEngineLabel}</dt>
                                <dd>{analysisEngineName || analysisEngineFallback}</dd>
                            </div>
                            <div>
                                <dt>{analysisDepthLabel}</dt>
                                <dd>{analysisDepthDisplay}</dd>
                            </div>
                            {#if analysisShowSummaryDetails}
                                <div>
                                    <dt>{analysisScoreLabel}</dt>
                                    <dd>{analysisScoreText}</dd>
                                </div>
                                {#if analysisMateText}
                                    <div>
                                        <dt>{analysisMateLabel}</dt>
                                        <dd>{analysisMateText}</dd>
                                    </div>
                                {/if}
                                <div>
                                    <dt>{analysisBestMoveLabel}</dt>
                                    <dd>{analysisBestMoveText}</dd>
                                </div>
                            {/if}
                        </dl>
                        {#if analysisShowSummaryDetails}
                            <div class="analysis-line-block">
                                <h3>{analysisLineLabel}</h3>
                                <p>{analysisLineDisplay}</p>
                            </div>
                        {/if}
                        <GameAnalysisViewer
                            entry={analysisViewerEntry}
                            index={analysisFocusIndex ?? 0}
                            total={analysisViewerStepCount}
                            labels={analysisViewerLabels}
                            probabilityLabels={analysisProbabilityLabels}
                            probabilities={analysisViewerEntry?.probabilities}
                            probabilityPercents={analysisViewerEntry?.probabilityPercents}
                            probabilityTimeline={analysisProbabilityTimeline}
                            onPrev={handleViewerPrev}
                            onNext={handleViewerNext}
                            onSeek={handleViewerSeek}
                            onClose={handleViewerClose}
                        />
                        {#if analysisLastRunText}
                            <p class="analysis-updated">{analysisLastRunText}</p>
                        {/if}
                    {:else}
                        <p class="analysis-status">{analysisPendingText}</p>
                    {/if}
                </div>
            {/if}
            {#if summaryText}
                <div class="info-card">
                    <h2>{summaryHeading}</h2>
                    <p>{summaryText}</p>
                </div>
            {/if}
            {#if resultLabel}
                <div class="info-card">
                    <h2>{resultHeading}</h2>
                    <p>{resultLabel}</p>
                </div>
            {/if}
            {#if pgn}
                <div class="info-card">
                    <h2>{pgnHeading}</h2>
                    <textarea readonly rows="6">{pgn}</textarea>
                </div>
            {/if}
            </section>
        </div>
    </main>
{:else}
    <main class="play empty">
        <header class="play-header">
            <button class="ghost" on:click={onBack}>{backLabel}</button>
            <span></span>
            <button class="secondary micro" on:click={onLogout}>
                {logoutLabel}
            </button>
        </header>
        <p class="placeholder">{emptyText}</p>
    </main>
{/if}

<style>
    .play {
        min-height: 100vh;
        display: flex;
        flex-direction: column;
        gap: clamp(1rem, 3vw, 1.5rem);
        padding: clamp(0.75rem, 3vw, 1.35rem) clamp(1.25rem, 2.5vw + 1.5rem, 3rem)
            2.75rem;
        width: 100%;
        max-width: 1440px;
        margin-inline: auto;
    }

    .play.empty {
        align-items: center;
        justify-content: flex-start;
    }

    .play-header {
        display: grid;
        grid-template-columns: auto 1fr auto;
        grid-template-rows: auto auto;
        align-items: center;
        column-gap: 1.5rem;
        row-gap: 0.75rem;
    }

    .match-overview {
        display: flex;
        flex-direction: column;
        gap: 0.6rem;
        align-items: flex-start;
        flex: 1 1 auto;
        min-width: 0;
        width: 100%;
        grid-column: 1 / span 3;
        grid-row: 2;
    }

    .play-header .ghost {
        grid-column: 1;
        grid-row: 1;
        justify-self: start;
    }

    .play-header .secondary.micro {
        grid-column: 3;
        grid-row: 1;
        justify-self: end;
    }

    .opponent {
        display: flex;
        gap: 0.75rem;
        align-items: center;
    }

    .opponent img {
        width: 52px;
        height: 52px;
        border-radius: 20px;
        object-fit: cover;
        border: 1px solid rgba(148, 163, 184, 0.35);
    }

    .match-overview h1 {
        margin: 0;
        font-size: clamp(1.6rem, 4vw, 2.1rem);
        color: #f8fafc;
        max-width: 100%;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .meta {
        margin: 0.25rem 0 0;
        color: rgba(226, 232, 240, 0.72);
        font-size: 0.95rem;
        max-width: 100%;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .timestamp {
        margin: 0;
        color: rgba(148, 163, 184, 0.75);
        font-size: 0.85rem;
        max-width: 100%;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .play-body {
        display: grid;
        gap: clamp(1rem, 2.5vw, 1.4rem);
        align-items: start;
    }

    .board-section {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.75rem;
    }

    .clock-panel {
        width: 100%;
        display: grid;
        gap: 0.6rem;
        padding: 0.9rem 1rem;
        border-radius: 16px;
        background: rgba(15, 23, 42, 0.55);
        border: 1px solid rgba(96, 165, 250, 0.15);
    }

    .clock-header {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 0.5rem;
        flex-wrap: wrap;
    }

    .clock-header h2 {
        margin: 0;
        font-size: 1rem;
        color: #f8fafc;
    }

    .clock-summary {
        font-size: 0.85rem;
        color: rgba(148, 163, 184, 0.85);
    }

    .clock-rows {
        display: grid;
        gap: 0.45rem;
    }

    .clock-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.45rem 0.65rem;
        border-radius: 12px;
        background: rgba(15, 23, 42, 0.45);
        border: 1px solid transparent;
        color: #e2e8f0;
        transition: border-color 0.2s ease, background 0.2s ease, color 0.2s ease;
    }

    .clock-row.active {
        border-color: rgba(96, 165, 250, 0.55);
        background: rgba(30, 64, 175, 0.35);
        color: #f8fafc;
    }

    .clock-row.critical {
        border-color: rgba(251, 191, 36, 0.6);
        background: rgba(251, 146, 60, 0.25);
        color: #fffbeb;
    }

    .clock-label {
        font-size: 0.95rem;
        font-weight: 600;
    }

    .clock-value {
        font-family: "Roboto Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
            "Liberation Mono", "Courier New", monospace;
        font-size: 1.25rem;
        display: flex;
        align-items: baseline;
        gap: 0.5rem;
    }

    .clock-increment {
        font-size: 0.7rem;
        background: rgba(15, 23, 42, 0.25);
        border: 1px solid rgba(148, 163, 184, 0.12);
        padding: 0.1rem 0.35rem;
        border-radius: 999px;
        color: rgba(226, 232, 240, 0.82);
    }

    .board-section :global(.chess-widget) {
        width: 100%;
    }

    .board-controls {
        display: flex;
        gap: 0.65rem;
        justify-content: center;
        flex-wrap: wrap;
    }

    .pill {
        padding: 0.45rem 0.95rem;
        border-radius: 999px;
        border: none;
        font-weight: 600;
        letter-spacing: 0.01em;
        background: rgba(37, 99, 235, 0.85);
        color: #eaf2ff;
        cursor: pointer;
        transition: background 0.15s ease;
    }

    .pill:hover {
        background: rgba(59, 130, 246, 0.95);
    }

    .pill:disabled {
        opacity: 0.5;
        cursor: not-allowed;
        box-shadow: none;
    }

    .pill.resign {
        background: rgba(239, 68, 68, 0.88);
        color: #fee2e2;
    }

    .pill.resign:hover {
        background: rgba(220, 38, 38, 0.95);
    }

    .game-info {
        display: flex;
        flex-direction: column;
        gap: 0.85rem;
        width: 100%;
    }

    .info-card {
        background: rgba(15, 23, 42, 0.6);
        border-radius: 16px;
        padding: 1rem 1.1rem;
        display: grid;
        gap: 0.5rem;
    }

    .info-card h2 {
        margin: 0;
        color: #f8fafc;
        font-size: 1.05rem;
    }

    .info-card p {
        margin: 0;
        color: rgba(226, 232, 240, 0.72);
        line-height: 1.5;
    }

    .analysis-card {
        gap: 0.8rem;
    }

    .analysis-top {
        display: flex;
        gap: 0.75rem;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
    }

    .analysis-top h2 {
        margin: 0;
    }

    .analysis-status {
        margin: 0;
        color: rgba(148, 163, 184, 0.78);
        font-size: 0.9rem;
    }

    .analysis-error {
        margin: 0;
        padding: 0.65rem 0.75rem;
        border-radius: 12px;
        border: 1px solid rgba(239, 68, 68, 0.35);
        background: rgba(239, 68, 68, 0.15);
        color: #fecaca;
        font-size: 0.9rem;
    }

    .analysis-grid {
        display: grid;
        gap: 0.75rem 1.25rem;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    }

    .analysis-grid div {
        display: grid;
        gap: 0.15rem;
    }

    .analysis-grid dt {
        margin: 0;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: rgba(148, 163, 184, 0.75);
    }

    .analysis-grid dd {
        margin: 0;
        font-size: 0.95rem;
        color: rgba(226, 232, 240, 0.88);
        font-family: "JetBrains Mono", "Fira Code", monospace;
    }

    .analysis-line-block {
        display: grid;
        gap: 0.25rem;
    }

    .analysis-line-block h3 {
        margin: 0;
        font-size: 0.78rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: rgba(148, 163, 184, 0.78);
    }

    .analysis-line-block p {
        margin: 0;
        font-family: "JetBrains Mono", "Fira Code", monospace;
        font-size: 0.92rem;
        line-height: 1.45;
        color: rgba(226, 232, 240, 0.9);
        word-break: break-word;
    }

    .analysis-card :global(.analysis-viewer) {
        margin-top: 0.6rem;
    }

    .analysis-updated {
        margin: 0;
        color: rgba(148, 163, 184, 0.68);
        font-size: 0.78rem;
    }

    textarea {
        width: 100%;
        border-radius: 12px;
        border: 1px solid rgba(148, 163, 184, 0.3);
        background: rgba(2, 6, 23, 0.6);
        color: #e2e8f0;
        padding: 0.75rem;
        font-family: "JetBrains Mono", "Fira Code", monospace;
        resize: none;
        max-height: 240px;
        overflow-y: auto;
        line-height: 1.45;
    }

    .ghost {
        border: none;
        background: transparent;
        color: #bfdbfe;
        font-weight: 600;
        cursor: pointer;
        padding: 0.35rem 0.6rem;
    }

    .ghost:hover {
        color: #e0f2fe;
    }

    .secondary.micro {
        padding: 0.45em 0.9em;
        font-size: 0.85rem;
    }

    .placeholder {
        margin-top: 4rem;
        color: rgba(226, 232, 240, 0.7);
    }

    @media (min-width: 960px) {
        .play-body {
            grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr);
            column-gap: clamp(1.4rem, 3.5vw, 2.4rem);
        }

        .game-info {
            position: sticky;
            top: clamp(1rem, 3vw, 1.6rem);
            max-height: calc(100vh - clamp(1rem, 3vw, 1.6rem) - 2rem);
            overflow-y: auto;
            padding-right: 0.35rem;
            scrollbar-width: thin;
            scrollbar-color: rgba(148, 163, 184, 0.3) transparent;
        }

        .game-info::-webkit-scrollbar {
            width: 6px;
        }

        .game-info::-webkit-scrollbar-thumb {
            background: rgba(148, 163, 184, 0.3);
            border-radius: 999px;
        }
    }

    @media (max-width: 640px) {
        .play {
            padding-inline: 1rem;
            gap: 1rem;
        }

        .play-header {
            grid-template-columns: auto auto;
            grid-template-rows: repeat(2, auto);
            column-gap: 0.75rem;
            row-gap: 0.75rem;
        }

        .play-header .ghost {
            grid-column: 1;
            grid-row: 1;
        }

        .play-header .secondary.micro {
            grid-column: 2;
            grid-row: 1;
            justify-self: end;
        }

        .match-overview {
            width: 100%;
            max-width: none;
            grid-column: 1 / span 2;
            grid-row: 2;
        }

        .match-overview h1,
        .meta,
        .timestamp {
            white-space: normal;
            overflow: visible;
            text-overflow: unset;
        }

        .board-section {
            gap: 0.65rem;
        }

        .board-controls {
            width: 100%;
            justify-content: space-between;
        }

        .ghost {
            padding-left: 0;
        }
    }
</style>
