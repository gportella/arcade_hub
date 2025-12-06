<script>
    import {
        BOARD_COLS,
        BOARD_ROWS,
        COLOR_CLASS,
        COLOR_LABELS,
    } from "../../lib/constants.js";
    export let onSelect = undefined;

    export let board = [];
    export let playableColumns = [];
    export let lastMove = null;
    export let disabled = false;

    $: rows = board.length || BOARD_ROWS;
    $: cols = board[0]?.length || BOARD_COLS;

    function handleColumn(column) {
        if (disabled || !playableColumns.includes(column)) {
            return;
        }
        if (typeof onSelect === "function") {
            onSelect(column);
        }
    }

    function cellClass(row, column, value) {
        const classes = ["cell"];
        if (value !== null) {
            classes.push(COLOR_CLASS[value]);
        }
        if (lastMove && lastMove.row === row && lastMove.column === column) {
            classes.push("recent");
        }
        if (!disabled && playableColumns.includes(column)) {
            classes.push("interactive");
        }
        return classes.join(" ");
    }

    function cellLabel(row, column, value) {
        if (value === null) {
            return `Empty slot row ${row + 1}, column ${column + 1}`;
        }
        return `${COLOR_LABELS[value]} disc row ${row + 1}, column ${column + 1}`;
    }
</script>

<div
    class="board"
    role="grid"
    aria-label="Connect 4 board"
    style={`--rows:${rows};--cols:${cols};`}
>
    {#each board as row, rowIndex}
        <div class="row" role="row">
            {#each row as cell, columnIndex}
                <button
                    type="button"
                    class={cellClass(rowIndex, columnIndex, cell)}
                    on:click={() => handleColumn(columnIndex)}
                    disabled={disabled ||
                        !playableColumns.includes(columnIndex)}
                    role="gridcell"
                    aria-label={cellLabel(rowIndex, columnIndex, cell)}
                >
                    <span class="disc" aria-hidden="true"></span>
                </button>
            {/each}
        </div>
    {/each}
</div>

<style>
    .board {
        display: inline-grid;
        grid-template-rows: repeat(var(--rows), auto);
        gap: 0.4rem;
        background: var(--board-bg, rgba(18, 55, 105, 0.95));
        padding: 0.8rem;
        border-radius: 1.25rem;
        box-shadow: inset 0 0 1rem rgba(0, 0, 0, 0.4);
        max-width: min(100%, 30rem);
    }

    .row {
        display: grid;
        grid-template-columns: repeat(var(--cols), minmax(2.8rem, 1fr));
        gap: 0.4rem;
    }

    .cell {
        position: relative;
        width: 100%;
        padding-top: 100%;
        border-radius: 50%;
        border: none;
        background: var(--slot-bg, rgba(255, 255, 255, 0.12));
        cursor: pointer;
        transition:
            transform 120ms ease,
            background 120ms ease;
    }

    .cell:disabled {
        cursor: default;
        opacity: 0.6;
    }

    .cell.interactive:not(:disabled):hover {
        transform: translateY(-4px);
        background: rgba(255, 255, 255, 0.25);
    }

    .disc {
        position: absolute;
        inset: 15%;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.1);
        box-shadow: inset 0 0.6rem 0.8rem rgba(0, 0, 0, 0.35);
    }

    .cell.disc-yellow .disc {
        background: linear-gradient(145deg, #ffdf60, #f9b53f);
    }

    .cell.disc-red .disc {
        background: linear-gradient(145deg, #ff6f6f, #e03a3a);
    }

    .cell.recent .disc {
        box-shadow:
            0 0 0 3px rgba(255, 255, 255, 0.6),
            inset 0 0.6rem 0.8rem rgba(0, 0, 0, 0.35);
    }
</style>
