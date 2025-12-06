<script>
  import { onDestroy, onMount, tick } from "svelte";
  import Grid from "./components/Grid.svelte";
  import ConfigurationPicker from "./components/ConfigurationPicker.svelte";
  import { clonePuzzle, createEmptyPuzzle } from "./lib/defaultPuzzle";
  import {
    findPlacement,
    insertVehicle as insertVehicleDraft,
    nextVehicleId,
    removeVehicle as removeVehicleDraft,
    setBoardSize,
    setExitRow,
    updateVehicle as updateDraftVehicle,
    validateDraft,
    findOverlappingVehicles,
  } from "./lib/editorUtils";
  import { applyMove as applyMoveDraft } from "./lib/puzzleLogic";
  import {
    backendEnabled,
    completed,
    activatePuzzleConfiguration,
    fetchPuzzleConfiguration,
    fetchPuzzleConfigurations,
    lastError,
    loadPuzzle,
    loading,
    moveVehicle,
    notice,
    puzzle,
    replacePuzzleState,
    resetPuzzle,
    refreshRealtimeConnection,
    realtimeConnected,
    savePuzzleConfiguration,
    deletePuzzleConfiguration,
    updatePuzzleConfiguration,
    solutionPath,
    solutionStep,
    solutionAnimating,
    showSolutionStep,
    stepSolution,
    clearSolutionPath,
    solvePuzzle,
    setBackendEnabled,
  } from "./lib/puzzleStore";

  let selectedId = null;
  let editMode = false;
  let draftPuzzle = createEmptyPuzzle();
  let editorError = null;
  let editorNotice = null;
  let pendingLength = 2;
  let pendingOrientation = "horizontal";
  let pendingGoal = false;
  let pendingName = "";
  let activateAfterSave = true;
  let editingConfigId = null;
  let configurations = [];
  let configurationsError = null;
  let editorSectionLoading = false;
  let statusMessages = [];
  let configPickerRef = null;
  /** @type {HTMLElement | null} */
  let boardContainer = null;
  /** @type {HTMLElement | null} */
  let editorElement = null;
  let boardOffset = 0;
  /** @type {ResizeObserver | null} */
  let boardResizeObserver = null;
  /** @type {ResizeObserver | null} */
  let editorResizeObserver = null;

  $: overlappingIds = editMode
    ? findOverlappingVehicles(draftPuzzle)
    : new Set();
  $: hasOverlaps = overlappingIds.size > 0;

  $: liveState = $puzzle;
  $: liveCompleted = $completed;
  $: liveError = $lastError;
  $: liveNotice = $notice;
  $: state = editMode ? draftPuzzle : liveState;
  $: isLoading = $loading;
  $: isCompleted = editMode ? false : liveCompleted;
  $: error = editMode ? editorError : liveError;
  $: info = editMode ? editorNotice : liveNotice;
  $: selectedVehicle = state?.vehicles?.find(
    (vehicle) => vehicle.id === selectedId,
  );
  $: if (
    state &&
    selectedId &&
    !state.vehicles.some((vehicle) => vehicle.id === selectedId)
  ) {
    selectedId = null;
  }
  $: if (isCompleted && selectedId) {
    selectedId = null;
  }
  $: laneRow =
    selectedVehicle?.orientation === "horizontal" ? selectedVehicle.row : null;
  let overlayTimer;
  let overlayVisible = false;
  let viewportWidth = typeof window !== "undefined" ? window.innerWidth : 0;

  $: {
    if (isLoading) {
      if (!overlayTimer) {
        overlayTimer = setTimeout(() => {
          overlayVisible = true;
          overlayTimer = null;
        }, 150);
      }
    } else {
      if (overlayTimer) {
        clearTimeout(overlayTimer);
        overlayTimer = null;
      }
      overlayVisible = false;
    }
  }

  let keydownHandler;
  let resizeHandler;

  function refreshBoardOffset() {
    if (!editMode || !boardContainer || !editorElement) {
      if (boardOffset !== 0) {
        boardOffset = 0;
      }
      return;
    }

    const boardRect = boardContainer.getBoundingClientRect();
    const editorRect = editorElement.getBoundingClientRect();
    const delta = editorRect.height - boardRect.height;
    const nextOffset = delta > 0 ? delta / 2 : 0;

    if (Math.abs(nextOffset - boardOffset) > 0.5) {
      boardOffset = nextOffset;
    }
  }

  $: if (editMode) {
    refreshBoardOffset();
  } else if (boardOffset !== 0) {
    boardOffset = 0;
  }

  $: if (typeof ResizeObserver !== "undefined") {
    if (boardContainer && !boardResizeObserver) {
      boardResizeObserver = new ResizeObserver(() => refreshBoardOffset());
      boardResizeObserver.observe(boardContainer);
    } else if (!boardContainer && boardResizeObserver) {
      boardResizeObserver.disconnect();
      boardResizeObserver = null;
    }

    if (editorElement && !editorResizeObserver) {
      editorResizeObserver = new ResizeObserver(() => refreshBoardOffset());
      editorResizeObserver.observe(editorElement);
    } else if (!editorElement && editorResizeObserver) {
      editorResizeObserver.disconnect();
      editorResizeObserver = null;
    }
  }

  function formatOverlapMessage(overlaps) {
    if (!overlaps || overlaps.size === 0) {
      return null;
    }
    if (overlaps.size === 1) {
      return `Vehicle ${Array.from(overlaps)[0]} overlaps another piece.`;
    }
    const ids = Array.from(overlaps).slice(0, 3);
    const list =
      overlaps.size > ids.length ? `${ids.join(", ")}, …` : ids.join(", ");
    return `Vehicles ${list} overlap. Resolve overlaps before saving.`;
  }

  async function reloadPuzzle() {
    selectedId = null;
    clearSolutionPath();
    try {
      await loadPuzzle();
    } catch (error) {
      // error already surfaced through store
    }
  }

  async function restorePuzzle() {
    selectedId = null;
    clearSolutionPath();
    try {
      await resetPuzzle();
    } catch (error) {
      // error already surfaced through store
    }
  }

  onMount(() => {
    keydownHandler = (event) => {
      const key = event.key;
      if (key === "Escape") {
        selectedId = null;
        return;
      }

      if (!selectedVehicle || isLoading) {
        return;
      }

      const orientation = selectedVehicle.orientation;
      let delta = 0;

      if (orientation === "horizontal") {
        if (key === "ArrowLeft" || key === "a" || key === "A") {
          delta = -1;
        } else if (key === "ArrowRight" || key === "d" || key === "D") {
          delta = 1;
        }
      } else if (orientation === "vertical") {
        if (key === "ArrowUp" || key === "w" || key === "W") {
          delta = -1;
        } else if (key === "ArrowDown" || key === "s" || key === "S") {
          delta = 1;
        }
      }

      if (delta !== 0) {
        event.preventDefault();
        nudge(delta);
      }
    };

    window.addEventListener("keydown", keydownHandler);

    resizeHandler = () => {
      viewportWidth = window.innerWidth;
    };
    window.addEventListener("resize", resizeHandler);

    viewportWidth = window.innerWidth;

    if (!state) {
      reloadPuzzle();
    }
  });

  onDestroy(() => {
    if (keydownHandler) {
      window.removeEventListener("keydown", keydownHandler);
    }
    if (resizeHandler) {
      window.removeEventListener("resize", resizeHandler);
    }
    if (overlayTimer) {
      clearTimeout(overlayTimer);
      overlayTimer = null;
    }
    if (boardResizeObserver) {
      boardResizeObserver.disconnect();
      boardResizeObserver = null;
    }
    if (editorResizeObserver) {
      editorResizeObserver.disconnect();
      editorResizeObserver = null;
    }
  });

  async function submitMove(vehicleId, steps) {
    if (!vehicleId || steps === 0) {
      return;
    }

    if (editMode) {
      clearSolutionPath();
      resetEditorFeedback();
      try {
        const result = applyMoveDraft(draftPuzzle, { vehicleId, steps });
        draftPuzzle = result.state;
        editorNotice = `Moved vehicle ${vehicleId}`;
      } catch (moveError) {
        editorError =
          moveError instanceof Error ? moveError.message : "Move failed.";
      }
      return;
    }

    try {
      await moveVehicle(vehicleId, steps);
    } catch (err) {
      // Side-effect handled in the store (error state is exposed to the UI)
    }
  }

  async function nudge(steps) {
    if (!selectedVehicle) {
      return;
    }

    await submitMove(selectedVehicle.id, steps);
  }

  function handleSelect(event) {
    const id = event.detail.id;
    selectedId = selectedId === id ? null : id;
  }

  function clearSelection() {
    selectedId = null;
  }

  function handleSolutionScrub(event) {
    if ($solutionAnimating) {
      return;
    }
    const value = Number(event.currentTarget.value);
    if (Number.isNaN(value)) {
      return;
    }
    showSolutionStep(value);
  }

  function handleSolutionStep(delta) {
    if ($solutionAnimating) {
      return;
    }
    stepSolution(delta);
  }

  const moveLabels = {
    horizontal: { negative: "Move Left", positive: "Move Right" },
    vertical: { negative: "Move Up", positive: "Move Down" },
  };

  $: hasSidebarRoom = viewportWidth > 960;
  $: backendActive = $backendEnabled;
  $: realtimeOnline = $realtimeConnected;
  $: solutionFrames = Array.isArray($solutionPath) ? $solutionPath : [];
  $: hasSolutionPath = !editMode && solutionFrames.length > 0;
  $: solutionTotal = hasSolutionPath ? solutionFrames.length : 0;
  $: solutionPosition = hasSolutionPath ? $solutionStep + 1 : 0;
  $: solutionRangeMax = solutionTotal > 0 ? solutionTotal - 1 : 0;
  $: saveActionLabel =
    editingConfigId === null ? "Save draft" : "Update configuration";
  $: {
    const messages = [];
    if (editMode && editorError) {
      messages.push({ id: "error", icon: "!", label: editorError });
    }
    if (editMode && hasOverlaps && !editorError) {
      const overlapLabel = formatOverlapMessage(overlappingIds);
      if (overlapLabel) {
        messages.push({ id: "error", icon: "!", label: overlapLabel });
      }
    }
    if (editMode && editorNotice) {
      messages.push({ id: "info", icon: "✎", label: editorNotice });
    }
    if (!editMode && isCompleted) {
      messages.push({ id: "success", icon: "✓", label: "Solved!" });
    }
    if (!editMode && liveError) {
      messages.push({ id: "error", icon: "!", label: liveError });
    }
    if (!editMode && liveNotice) {
      messages.push({ id: "info", icon: "i", label: liveNotice });
    }
    statusMessages = messages;
  }

  async function handleMove(event) {
    const {
      id,
      steps = 0,
      axis = null,
      rowDelta = 0,
      colDelta = 0,
    } = event.detail;
    if (!id || (steps === 0 && rowDelta === 0 && colDelta === 0)) {
      return;
    }
    selectedId = id;
    clearSolutionPath();
    if (editMode) {
      const vehicle = draftPuzzle.vehicles.find((item) => item.id === id);
      if (!vehicle) {
        return;
      }
      const crossAxisMovement =
        (vehicle.orientation === "horizontal" && rowDelta !== 0) ||
        (vehicle.orientation === "vertical" && colDelta !== 0);

      if (crossAxisMovement) {
        resetEditorFeedback();
        try {
          const updates = {};
          if (rowDelta !== 0) {
            updates.row = vehicle.row + rowDelta;
          }
          if (colDelta !== 0) {
            updates.col = vehicle.col + colDelta;
          }
          draftPuzzle = updateDraftVehicle(draftPuzzle, id, updates, {
            validate: false,
          });
          editorNotice = `Moved vehicle ${id}.`;
          await tick();
          refreshBoardOffset();
        } catch (moveError) {
          editorError =
            moveError instanceof Error ? moveError.message : "Move failed.";
        }
        return;
      }
    }
    await submitMove(id, steps);
  }

  async function handleBackendToggle(event) {
    const enabled = event.currentTarget.checked;
    try {
      await setBackendEnabled(enabled);
    } catch (toggleError) {
      // surface error via existing store wiring
      console.error(toggleError);
    }
  }

  async function handleSolve() {
    selectedId = null;
    try {
      await solvePuzzle();
    } catch (error) {
      console.error(error);
    }
  }

  function resetEditorFeedback() {
    editorError = null;
    editorNotice = null;
  }

  async function loadConfigurationList() {
    configurationsError = null;
    editorSectionLoading = true;
    try {
      configurations = [];
      configurations = await fetchPuzzleConfigurations();
    } catch (error) {
      configurationsError =
        error instanceof Error
          ? error.message
          : "Failed to load configurations.";
    } finally {
      editorSectionLoading = false;
      await tick();
      refreshBoardOffset();
    }
  }

  async function refreshSidebarConfigs() {
    if (configPickerRef && typeof configPickerRef.refresh === "function") {
      try {
        await configPickerRef.refresh();
      } catch {
        // ignore picker refresh failures
      }
    }
  }

  async function toggleEditMode() {
    editMode = !editMode;
    selectedId = null;
    resetEditorFeedback();
    clearSolutionPath();
    if (editMode) {
      configurationsError = null;
      draftPuzzle = createEmptyPuzzle();
      pendingLength = 2;
      pendingOrientation = "horizontal";
      pendingGoal = false;
      pendingName = "";
      activateAfterSave = true;
      editingConfigId = null;
      void loadConfigurationList();
      await tick();
      refreshBoardOffset();
    } else {
      boardOffset = 0;
      editingConfigId = null;
    }
  }

  function startNewDraft() {
    resetEditorFeedback();
    draftPuzzle = createEmptyPuzzle(draftPuzzle.size);
    pendingName = "";
    pendingGoal = false;
    editingConfigId = null;
    clearSolutionPath();
    editorNotice = "Started a blank puzzle.";
    refreshBoardOffset();
  }

  function loadCurrentIntoEditor() {
    resetEditorFeedback();
    draftPuzzle = clonePuzzle(liveState ?? createEmptyPuzzle());
    pendingName = "";
    pendingGoal = false;
    editingConfigId = null;
    clearSolutionPath();
    editorNotice = "Copied the current puzzle into the editor.";
    refreshBoardOffset();
  }

  function handleBoardSizeChange(event) {
    const value = Number(event.currentTarget.value);
    resetEditorFeedback();
    try {
      draftPuzzle = setBoardSize(draftPuzzle, value);
      editorNotice = `Board resized to ${draftPuzzle.size}x${draftPuzzle.size}.`;
    } catch (error) {
      editorError = error instanceof Error ? error.message : "Resize failed.";
      event.currentTarget.value = draftPuzzle.size;
    }
  }

  function handleExitRowChange(event) {
    const rawValue = event.currentTarget.value;
    if (rawValue === "") {
      return;
    }
    const parsed = Number(rawValue);
    if (Number.isNaN(parsed)) {
      return;
    }
    resetEditorFeedback();
    draftPuzzle = setExitRow(draftPuzzle, parsed - 1);
    const sanitized = draftPuzzle.exit.row + 1;
    event.currentTarget.value = String(sanitized);
    editorNotice = `Exit row set to ${sanitized}.`;
  }

  function handleAddVehicle() {
    resetEditorFeedback();
    try {
      const id = nextVehicleId(draftPuzzle, pendingGoal);
      const pieceLength = Number(pendingLength);
      const spot = findPlacement(draftPuzzle, pendingOrientation, pieceLength);
      if (!spot) {
        throw new Error("No space available for that piece.");
      }
      const vehicle = {
        id,
        orientation: pendingOrientation,
        length: pieceLength,
        goal: pendingGoal,
        row: spot.row,
        col: spot.col,
      };
      draftPuzzle = insertVehicleDraft(draftPuzzle, vehicle);
      editorNotice = `Added vehicle ${id}.`;
      if (pendingGoal) {
        pendingGoal = false;
      }
      refreshBoardOffset();
    } catch (error) {
      editorError =
        error instanceof Error ? error.message : "Failed to add piece.";
    }
  }

  function handleRemoveVehicle(id) {
    resetEditorFeedback();
    draftPuzzle = removeVehicleDraft(draftPuzzle, id);
    editorNotice = `Removed vehicle ${id}.`;
    if (selectedId === id) {
      selectedId = null;
    }
    refreshBoardOffset();
  }

  function handleVehicleChange(id, field, rawValue) {
    resetEditorFeedback();
    let updates = {};
    try {
      if (typeof rawValue === "number" && Number.isNaN(rawValue)) {
        return;
      }
      if (field === "orientation") {
        updates = { orientation: rawValue };
      } else if (field === "goal") {
        updates = { goal: Boolean(rawValue) };
      } else if (field === "length") {
        updates = { length: Number(rawValue) };
      } else if (field === "row" || field === "col") {
        updates = { [field]: Number(rawValue) };
      }
      if (Object.keys(updates).length === 0) {
        return;
      }
      const autoPlace =
        Object.prototype.hasOwnProperty.call(updates, "orientation") ||
        Object.prototype.hasOwnProperty.call(updates, "length");
      draftPuzzle = updateDraftVehicle(draftPuzzle, id, updates, {
        autoPlace,
        validate: false,
      });
      editorNotice = `Updated vehicle ${id}.`;
      refreshBoardOffset();
    } catch (error) {
      editorError = error instanceof Error ? error.message : "Update failed.";
    }
  }

  function handleCellInput(event, id, field) {
    const raw = event.currentTarget.value;
    if (!raw) {
      return;
    }
    const parsed = Number.parseInt(raw, 10);
    if (Number.isNaN(parsed)) {
      return;
    }
    const zeroBased = parsed - 1;
    event.currentTarget.value = String(parsed);
    handleVehicleChange(id, field, zeroBased);
  }

  async function handleApplyDraft() {
    resetEditorFeedback();
    try {
      const overlapping = findOverlappingVehicles(draftPuzzle);
      if (overlapping.size > 0) {
        editorError = formatOverlapMessage(overlapping);
        return;
      }
      validateDraft(draftPuzzle);
      await replacePuzzleState(draftPuzzle);
      editorNotice = "Applied draft to the backend.";
      selectedId = null;
      await tick();
      refreshBoardOffset();
    } catch (error) {
      editorError = error instanceof Error ? error.message : "Apply failed.";
    }
  }

  async function handleSaveDraft() {
    resetEditorFeedback();
    const trimmedName = pendingName.trim();
    if (!trimmedName) {
      editorError = "Provide a puzzle name before saving.";
      return;
    }
    try {
      const overlapping = findOverlappingVehicles(draftPuzzle);
      if (overlapping.size > 0) {
        editorError = formatOverlapMessage(overlapping);
        return;
      }
      validateDraft(draftPuzzle);
      let payload;
      if (editingConfigId !== null) {
        payload = await updatePuzzleConfiguration({
          id: editingConfigId,
          name: trimmedName,
          state: draftPuzzle,
          activate: activateAfterSave,
        });
        editorNotice = activateAfterSave
          ? `Updated and activated "${payload.name}".`
          : `Updated "${payload.name}".`;
      } else {
        payload = await savePuzzleConfiguration({
          name: trimmedName,
          state: draftPuzzle,
          activate: activateAfterSave,
        });
        editorNotice = activateAfterSave
          ? `Saved and activated "${payload.name}".`
          : `Saved "${payload.name}".`;
      }
      pendingName = payload.name ?? trimmedName;
      editingConfigId = payload.id ?? editingConfigId;
      activateAfterSave = Boolean(payload.active);
      await loadConfigurationList();
      await refreshSidebarConfigs();
      await refreshSidebarConfigs();
      await tick();
      refreshBoardOffset();
    } catch (error) {
      editorError = error instanceof Error ? error.message : "Save failed.";
    }
  }

  async function handleSaveDraftAsNew() {
    resetEditorFeedback();
    const trimmedName = pendingName.trim();
    if (!trimmedName) {
      editorError = "Provide a puzzle name before saving.";
      return;
    }
    try {
      const overlapping = findOverlappingVehicles(draftPuzzle);
      if (overlapping.size > 0) {
        editorError = formatOverlapMessage(overlapping);
        return;
      }
      validateDraft(draftPuzzle);
      const payload = await savePuzzleConfiguration({
        name: trimmedName,
        state: draftPuzzle,
        activate: activateAfterSave,
      });
      editorNotice = activateAfterSave
        ? `Saved and activated "${payload.name}".`
        : `Saved "${payload.name}".`;
      pendingName = payload.name ?? trimmedName;
      editingConfigId = payload.id ?? null;
      activateAfterSave = Boolean(payload.active);
      await loadConfigurationList();
      await tick();
      refreshBoardOffset();
    } catch (error) {
      editorError = error instanceof Error ? error.message : "Save failed.";
    }
  }

  async function handleLoadConfiguration(configId) {
    resetEditorFeedback();
    try {
      const record = await fetchPuzzleConfiguration(configId);
      draftPuzzle = clonePuzzle(record.state);
      pendingName = record.name ?? "";
      pendingGoal = false;
      activateAfterSave = Boolean(record.active);
      editingConfigId = record.id;
      editorNotice = `Loaded "${record.name}" into the editor.`;
      selectedId = null;
      await tick();
      refreshBoardOffset();
    } catch (error) {
      editorError =
        error instanceof Error
          ? error.message
          : "Failed to load configuration.";
    }
  }

  async function handleActivateConfiguration(configId) {
    resetEditorFeedback();
    try {
      const result = await activatePuzzleConfiguration(configId);
      editorNotice = `Activated "${result.name}".`;
      await loadConfigurationList();
      await refreshSidebarConfigs();
      await tick();
      refreshBoardOffset();
      selectedId = null;
    } catch (error) {
      editorError =
        error instanceof Error
          ? error.message
          : "Failed to activate configuration.";
    }
  }

  async function handleDeleteConfiguration(configId) {
    resetEditorFeedback();
    const record = configurations.find((item) => item.id === configId);
    if (typeof window !== "undefined") {
      const label = record
        ? `Delete puzzle "${record.name}"?`
        : "Delete this puzzle configuration?";
      if (!window.confirm(label)) {
        return;
      }
    }
    editorSectionLoading = true;
    try {
      const payload = await deletePuzzleConfiguration(configId);
      const removedName =
        record?.name ?? payload?.removed_name ?? `#${configId}`;
      const activatedName = payload?.activated_name ?? null;
      editorNotice = activatedName
        ? `Deleted "${removedName}". Active puzzle: "${activatedName}".`
        : `Deleted "${removedName}".`;
      if (editingConfigId === configId) {
        editingConfigId = null;
      }
      await loadConfigurationList();
      await refreshSidebarConfigs();
      selectedId = null;
    } catch (error) {
      editorError =
        error instanceof Error
          ? error.message
          : "Failed to delete configuration.";
    } finally {
      editorSectionLoading = false;
      await tick();
      refreshBoardOffset();
    }
  }
</script>

<main class="layout">
  <header class="layout__header">
    <h1>Solve Parking</h1>
    <p class="layout__subtitle">
      Slide the orange car to the exit on the right edge.
    </p>
  </header>

  <section
    class="layout__board"
    bind:this={boardContainer}
    style={`margin-top: ${editMode ? boardOffset : 0}px;`}
  >
    {#if state}
      <Grid
        size={state.size}
        exit={state.exit}
        vehicles={state.vehicles}
        {selectedId}
        highlightRow={laneRow}
        allowCrossAxisDrag={editMode}
        conflictedIds={overlappingIds}
        on:select={handleSelect}
        on:clear={clearSelection}
        on:move={handleMove}
      />
    {:else}
      <p class="placeholder">Loading puzzle…</p>
    {/if}
    {#if hasSolutionPath}
      <div class="solution-controls" aria-label="Solution playback controls">
        <button
          type="button"
          class="solution-controls__button"
          on:click={() => handleSolutionStep(-1)}
          disabled={$solutionAnimating || $solutionStep <= 0}
        >
          ◀
        </button>
        <input
          class="solution-controls__slider"
          type="range"
          min="0"
          max={solutionRangeMax}
          value={$solutionStep}
          disabled={$solutionAnimating || solutionTotal <= 1}
          on:input={handleSolutionScrub}
        />
        <span class="solution-controls__status">
          {solutionPosition} / {solutionTotal}
        </span>
        <button
          type="button"
          class="solution-controls__button"
          on:click={() => handleSolutionStep(1)}
          disabled={$solutionAnimating || $solutionStep >= solutionRangeMax}
        >
          ▶
        </button>
      </div>
    {/if}
  </section>

  <section class="layout__sidebar" aria-live="polite">
    <div class="sidebar__main">
      <div class="backend-controls">
        <label class="backend-toggle">
          <input
            type="checkbox"
            checked={backendActive}
            on:change={handleBackendToggle}
            disabled={isLoading || editMode}
          />
          <span class="backend-toggle__label">
            {backendActive
              ? realtimeOnline
                ? "Backend control"
                : "Backend control (reconnecting)"
              : "Local control"}
          </span>
        </label>
        {#if backendActive && !realtimeOnline}
          <button
            class="backend-controls__retry"
            type="button"
            on:click={refreshRealtimeConnection}
            disabled={isLoading || editMode}
            aria-label="Retry backend connection"
          >
            Retry
          </button>
        {/if}
      </div>

      <div class="controls">
        <button
          class="controls__action"
          on:click={reloadPuzzle}
          disabled={isLoading || editMode}
        >
          Reload
        </button>
        <button
          class="controls__action"
          on:click={restorePuzzle}
          disabled={isLoading || editMode}
        >
          Reset
        </button>
        <button
          class={`controls__action ${editMode ? "controls__action--active" : ""}`}
          on:click={toggleEditMode}
          disabled={isLoading}
        >
          {editMode ? "Exit Edit" : "Edit"}
        </button>
        <button
          class="controls__action"
          on:click={handleSolve}
          title={backendActive
            ? "Let the backend solve the current puzzle"
            : "Enable backend control to use the solver"}
          disabled={isLoading || !backendActive || editMode}
        >
          Solve
        </button>
      </div>

      {#if backendActive}
        <ConfigurationPicker bind:this={configPickerRef} disabled={isLoading} />
      {/if}

      {#if editMode}
        <div class="editor panel" bind:this={editorElement}>
          <div class="editor__header">
            <h2 class="panel__heading">Editor</h2>
            <div class="editor__quick">
              <button
                type="button"
                on:click={startNewDraft}
                disabled={isLoading}
              >
                Blank Board
              </button>
              <button
                type="button"
                on:click={loadCurrentIntoEditor}
                disabled={isLoading}
              >
                Use Current
              </button>
            </div>
          </div>

          <div class="editor__section">
            <h3>Board</h3>
            <label>
              Size
              <input
                type="number"
                min="2"
                max="12"
                value={draftPuzzle.size}
                on:change={handleBoardSizeChange}
              />
            </label>
            <label>
              Exit Row
              <input
                type="number"
                min="1"
                max={draftPuzzle.size}
                value={draftPuzzle.exit.row + 1}
                on:input={handleExitRowChange}
              />
            </label>
          </div>

          <div class="editor__section">
            <h3>Pieces</h3>
            <div class="editor__piece-controls">
              <label>
                Orientation
                <select bind:value={pendingOrientation}>
                  <option value="horizontal">Horizontal</option>
                  <option value="vertical">Vertical</option>
                </select>
              </label>
              <label>
                Length
                <select bind:value={pendingLength}>
                  <option value={2}>2</option>
                  <option value={3}>3</option>
                </select>
              </label>
              <label class="editor__goal">
                <input type="checkbox" bind:checked={pendingGoal} /> Goal piece
              </label>
              <button type="button" on:click={handleAddVehicle}>
                Add piece
              </button>
            </div>

            <div class="editor__vehicles">
              {#if draftPuzzle.vehicles.length === 0}
                <p class="editor__empty">No vehicles yet.</p>
              {:else}
                <table class="editor__table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Row</th>
                      <th>Col</th>
                      <th>Orientation</th>
                      <th>Length</th>
                      <th>Goal</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {#each draftPuzzle.vehicles as vehicle (vehicle.id)}
                      <tr
                        class={`editor__row${overlappingIds.has(vehicle.id) ? " editor__row--conflict" : ""}`}
                      >
                        <td>{vehicle.id}</td>
                        <td>
                          <input
                            type="number"
                            min="1"
                            step="1"
                            max={draftPuzzle.size}
                            value={vehicle.row + 1}
                            on:input={(event) =>
                              handleCellInput(event, vehicle.id, "row")}
                          />
                        </td>
                        <td>
                          <input
                            type="number"
                            min="1"
                            step="1"
                            max={draftPuzzle.size}
                            value={vehicle.col + 1}
                            on:input={(event) =>
                              handleCellInput(event, vehicle.id, "col")}
                          />
                        </td>
                        <td>
                          <select
                            value={vehicle.orientation}
                            on:change={(event) =>
                              handleVehicleChange(
                                vehicle.id,
                                "orientation",
                                event.currentTarget.value,
                              )}
                          >
                            <option value="horizontal">Horizontal</option>
                            <option value="vertical">Vertical</option>
                          </select>
                        </td>
                        <td>
                          <select
                            value={vehicle.length}
                            on:change={(event) =>
                              handleVehicleChange(
                                vehicle.id,
                                "length",
                                Number(event.currentTarget.value),
                              )}
                          >
                            <option value={2}>2</option>
                            <option value={3}>3</option>
                          </select>
                        </td>
                        <td class="editor__goal-cell">
                          <input
                            type="checkbox"
                            checked={vehicle.goal}
                            on:change={(event) =>
                              handleVehicleChange(
                                vehicle.id,
                                "goal",
                                event.currentTarget.checked,
                              )}
                          />
                        </td>
                        <td>
                          <button
                            type="button"
                            class="editor__remove"
                            on:click={() => handleRemoveVehicle(vehicle.id)}
                          >
                            Remove
                          </button>
                        </td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              {/if}
            </div>
          </div>

          <div class="editor__section">
            <h3>Save &amp; Apply</h3>
            {#if editingConfigId !== null}
              <p class="editor__context">
                Editing saved puzzle "{pendingName || `#${editingConfigId}`}"
              </p>
            {/if}
            <label>
              Puzzle name
              <input
                type="text"
                bind:value={pendingName}
                placeholder="New puzzle"
              />
            </label>
            <label class="editor__goal">
              <input type="checkbox" bind:checked={activateAfterSave} /> Activate
              after saving
            </label>
            <div class="editor__actions">
              <button
                type="button"
                on:click={handleApplyDraft}
                disabled={isLoading || hasOverlaps}
              >
                Apply draft
              </button>
              <button
                type="button"
                on:click={handleSaveDraft}
                disabled={isLoading || hasOverlaps}
              >
                {saveActionLabel}
              </button>
              {#if editingConfigId !== null}
                <button
                  type="button"
                  on:click={handleSaveDraftAsNew}
                  disabled={isLoading || hasOverlaps}
                >
                  Save as new
                </button>
              {/if}
            </div>
            {#if hasOverlaps}
              <p class="editor__warning">
                Resolve overlapping pieces to enable saving.
              </p>
            {/if}
          </div>

          <div class="editor__section">
            <h3>Saved puzzles</h3>
            {#if editorSectionLoading}
              <p>Loading configurations…</p>
            {:else if configurationsError}
              <p class="editor__empty">{configurationsError}</p>
            {:else if configurations.length === 0}
              <p class="editor__empty">No saved puzzles yet.</p>
            {:else}
              <ul class="editor__configs">
                {#each configurations as config (config.id)}
                  <li>
                    <span>
                      {config.name} · {config.vehicle_count} vehicles
                      {#if config.active}
                        <span class="editor__badge">active</span>
                      {/if}
                    </span>
                    <div class="editor__config-actions">
                      <button
                        type="button"
                        on:click={() => handleLoadConfiguration(config.id)}
                        disabled={isLoading || editorSectionLoading}
                      >
                        Load
                      </button>
                      <button
                        type="button"
                        on:click={() => handleActivateConfiguration(config.id)}
                        disabled={isLoading || editorSectionLoading}
                      >
                        Activate
                      </button>
                      <button
                        type="button"
                        class="editor__config-delete"
                        on:click={() => handleDeleteConfiguration(config.id)}
                        disabled={isLoading || editorSectionLoading}
                      >
                        Delete
                      </button>
                    </div>
                  </li>
                {/each}
              </ul>
            {/if}
          </div>
        </div>
      {/if}

      {#if hasSidebarRoom}
        {#if selectedVehicle}
          <div class="panel">
            <h2 class="panel__heading">Vehicle {selectedVehicle.id}</h2>
            <p class="panel__meta">
              Orientation: {selectedVehicle.orientation}. Length: {selectedVehicle.length}
              tiles.
            </p>
            <dl class="panel__facts">
              <div>
                <dt>Row</dt>
                <dd>{selectedVehicle.row + 1}</dd>
              </div>
              <div>
                <dt>Column</dt>
                <dd>{selectedVehicle.col + 1}</dd>
              </div>
            </dl>
            <div class="panel__actions">
              <button on:click={() => nudge(-1)} disabled={isLoading}>
                {moveLabels[selectedVehicle.orientation].negative}
              </button>
              <button on:click={() => nudge(1)} disabled={isLoading}>
                {moveLabels[selectedVehicle.orientation].positive}
              </button>
            </div>
          </div>
        {:else}
          <p class="hint">
            Tap a vehicle to select it, then move it with the controls.
          </p>
        {/if}
      {/if}
    </div>

    <aside class="status-rail" role="status" aria-live="polite">
      {#if statusMessages.length === 0}
        <span class="chip chip--muted" aria-hidden="true">—</span>
      {:else}
        {#each statusMessages as message (message.id)}
          <span class={`chip chip--${message.id}`}>
            <span class="chip__icon" aria-hidden="true">{message.icon}</span>
            <span class="chip__label">{message.label}</span>
          </span>
        {/each}
      {/if}
    </aside>
  </section>
  {#if overlayVisible}
    <div class="overlay" aria-hidden="true">
      <div class="spinner"></div>
    </div>
  {/if}
</main>

<style>
  .layout {
    display: grid;
    grid-template-columns: minmax(0, 1fr) clamp(220px, 26vw, 320px);
    align-items: start;
    gap: 2rem;
    padding: clamp(1.5rem, 2.5vw, 3rem);
    max-width: 1200px;
    margin: 0 auto;
  }

  .layout__header {
    grid-column: 1 / -1;
    text-align: center;
  }

  .layout__header h1 {
    margin: 0;
    font-size: clamp(2rem, 5vw, 3rem);
  }

  .layout__subtitle {
    margin: 0.25rem 0 0;
    color: rgba(15, 23, 42, 0.7);
  }

  .layout__board {
    display: flex;
    align-items: flex-start;
    justify-content: center;
    position: sticky;
    top: clamp(1.25rem, 2vw, 2.5rem);
    align-self: start;
    transition: margin-top 150ms ease;
    flex-direction: column;
    gap: 0.75rem;
  }

  .solution-controls {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    align-self: stretch;
    background: rgba(15, 23, 42, 0.06);
    border-radius: 0.75rem;
    padding: 0.5rem 0.75rem;
  }

  .solution-controls__button {
    border: none;
    background: rgba(15, 23, 42, 0.12);
    color: rgba(15, 23, 42, 0.88);
    border-radius: 0.5rem;
    padding: 0.25rem 0.6rem;
    font-size: 1rem;
    line-height: 1;
    transition: background 120ms ease;
  }

  .solution-controls__button:enabled:hover {
    background: rgba(15, 23, 42, 0.18);
  }

  .solution-controls__button:disabled {
    opacity: 0.35;
    cursor: default;
  }

  .solution-controls__slider {
    flex: 1;
    min-width: 120px;
  }

  .solution-controls__status {
    font-size: 0.85rem;
    color: rgba(15, 23, 42, 0.7);
    min-width: 3.5rem;
    text-align: center;
  }

  .layout__sidebar {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    justify-content: space-between;
    gap: 0.75rem;
  }

  .sidebar__main {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 0.75rem;
    width: 100%;
  }

  .backend-controls {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    align-self: stretch;
    justify-content: space-between;
  }

  .backend-toggle {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: rgba(30, 41, 59, 0.6);
    user-select: none;
  }

  .backend-toggle input {
    accent-color: #2563eb;
    width: 1.05rem;
    height: 1.05rem;
    margin: 0;
  }

  .backend-toggle__label {
    font-weight: 600;
    white-space: nowrap;
  }

  .backend-controls__retry {
    padding: 0.25rem 0.6rem;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    border-radius: 999px;
    border: 1px solid rgba(37, 99, 235, 0.35);
    background: rgba(37, 99, 235, 0.1);
    color: #1d4ed8;
    font-weight: 600;
  }

  .status-rail {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: 0.4rem;
    padding: 0.5rem 0.55rem;
    border-radius: 1rem;
    background: rgba(15, 23, 42, 0.05);
    box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
    min-width: 8rem;
    max-width: 100%;
  }

  .chip {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.35rem 0.6rem;
    border-radius: 999px;
    font-weight: 600;
    font-size: 0.78rem;
    line-height: 1.2;
    background: rgba(148, 163, 184, 0.28);
    color: #1e293b;
    word-break: break-word;
  }

  .chip__icon {
    font-size: 0.85rem;
  }

  .chip__label {
    flex: 1 1 auto;
    min-width: 0;
  }

  .chip--success {
    background: rgba(34, 197, 94, 0.22);
    color: #047857;
  }

  .chip--error {
    background: rgba(248, 113, 113, 0.24);
    color: #b91c1c;
  }

  .chip--info {
    background: rgba(59, 130, 246, 0.22);
    color: #1d4ed8;
  }

  .chip--muted {
    justify-content: center;
    background: rgba(148, 163, 184, 0.2);
    color: rgba(71, 85, 105, 0.7);
    font-weight: 500;
  }

  .placeholder {
    font-size: 1.1rem;
    color: rgba(15, 23, 42, 0.65);
  }

  .controls {
    display: flex;
    gap: 0.6rem;
    width: 100%;
    justify-content: flex-end;
  }

  .controls__action {
    flex: 0 0 auto;
    min-width: 4.5rem;
  }

  .controls__action--active {
    background: linear-gradient(135deg, #3b82f6, #2563eb);
    color: #ffffff;
  }

  .panel {
    padding: 1rem;
    border-radius: 1rem;
    background-color: #ffffff;
    box-shadow: 0 10px 20px rgba(15, 23, 42, 0.12);
  }

  .panel__heading {
    margin: 0 0 0.5rem;
    font-size: 1.25rem;
  }

  .panel__meta {
    margin: 0 0 1rem;
    color: rgba(15, 23, 42, 0.6);
  }

  .panel__facts {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.75rem;
    margin: 0 0 1rem;
    padding: 0;
  }

  .panel__facts div {
    background-color: rgba(148, 163, 184, 0.12);
    border-radius: 0.75rem;
    padding: 0.6rem 0.75rem;
  }

  .editor {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .editor__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
  }

  .editor__quick {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .editor__section {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    border-top: 1px solid rgba(148, 163, 184, 0.25);
    padding-top: 0.75rem;
  }

  .editor__section:first-of-type {
    border-top: none;
    padding-top: 0;
  }

  .editor__section h3 {
    margin: 0;
    font-size: 1rem;
    color: rgba(15, 23, 42, 0.85);
  }

  .editor__piece-controls {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 0.75rem;
    align-items: end;
  }

  .editor__piece-controls label {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    font-size: 0.85rem;
  }

  .editor__goal {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.85rem;
  }

  .editor__vehicles {
    max-height: 220px;
    overflow: auto;
    padding: 0.5rem;
    border-radius: 0.75rem;
    background: rgba(148, 163, 184, 0.12);
  }

  .editor__empty {
    margin: 0;
    color: rgba(15, 23, 42, 0.6);
  }

  .editor__context {
    margin: 0;
    font-size: 0.85rem;
    color: rgba(15, 23, 42, 0.65);
  }

  .editor__table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
    background: rgba(255, 255, 255, 0.9);
    border-radius: 0.5rem;
    overflow: hidden;
  }

  .editor__table th,
  .editor__table td {
    padding: 0.35rem 0.45rem;
    text-align: left;
  }

  .editor__table tbody tr:nth-child(even) {
    background: rgba(148, 163, 184, 0.12);
  }

  .editor__table input,
  .editor__table select {
    width: 100%;
    box-sizing: border-box;
  }

  .editor__goal-cell {
    text-align: center;
  }

  .editor__remove {
    color: #dc2626;
  }

  .editor__actions {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .editor__configs {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
  }

  .editor__row {
    transition: background 120ms ease;
  }

  .editor__row--conflict {
    background: rgba(248, 113, 113, 0.18);
  }

  .editor__row--conflict input,
  .editor__row--conflict select {
    border-color: rgba(185, 28, 28, 0.6);
  }

  .editor__warning {
    margin: 0.5rem 0 0;
    font-size: 0.8rem;
    color: #b91c1c;
  }

  .editor__configs li {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.75rem;
    padding: 0.5rem 0.75rem;
    border-radius: 0.75rem;
    background: rgba(15, 23, 42, 0.08);
  }

  .editor__config-actions {
    display: flex;
    gap: 0.4rem;
  }

  .editor__config-delete {
    color: #b91c1c;
  }

  .editor__config-delete:disabled {
    color: rgba(185, 28, 28, 0.6);
  }

  .editor__badge {
    margin-left: 0.35rem;
    padding: 0.1rem 0.5rem;
    border-radius: 999px;
    background: #22c55e;
    color: #ffffff;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .panel__facts dt {
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: rgba(30, 41, 59, 0.6);
    margin: 0 0 0.25rem;
  }

  .panel__facts dd {
    margin: 0;
    font-weight: 600;
    font-size: 1.1rem;
  }

  .panel__actions {
    display: flex;
    gap: 0.75rem;
  }

  .hint {
    margin: 0;
    color: rgba(15, 23, 42, 0.6);
  }

  @media (max-width: 720px) {
    .layout {
      grid-template-columns: 1fr;
    }

    .layout__sidebar {
      order: -1;
      gap: 0.75rem;
      align-items: stretch;
    }

    .layout__board {
      position: static;
      margin-top: 0 !important;
      align-self: stretch;
      gap: 0.75rem;
    }

    .sidebar__main {
      align-items: stretch;
    }

    .status-rail {
      flex-direction: row;
      justify-content: flex-end;
      border-radius: 999px;
      padding: 0.4rem 0.6rem;
      min-width: auto;
      flex-wrap: wrap;
    }
  }

  .overlay {
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.1);
    display: grid;
    place-items: center;
    pointer-events: none;
    z-index: 10;
  }

  .spinner {
    width: 3rem;
    height: 3rem;
    border-radius: 50%;
    border: 4px solid rgba(59, 130, 246, 0.2);
    border-top-color: #2563eb;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }
</style>
