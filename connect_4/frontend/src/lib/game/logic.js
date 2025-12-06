import { BOARD_COLS, BOARD_ROWS, COLOR_LABELS, COLOR_SEQUENCE } from '../constants.js';

export function createEmptyBoard() {
    return Array.from({ length: BOARD_ROWS }, () => Array(BOARD_COLS).fill(null));
}

export function cloneBoard(board) {
    return board.map((row) => row.slice());
}

export function listPlayableColumns(board) {
    const playable = [];
    for (let column = 0; column < BOARD_COLS; column += 1) {
        if (board[0][column] === null) {
            playable.push(column);
        }
    }
    return playable;
}

export function dropPiece(board, column, color) {
    const target = cloneBoard(board);
    for (let row = BOARD_ROWS - 1; row >= 0; row -= 1) {
        if (target[row][column] === null) {
            target[row][column] = color;
            return { board: target, row, column };
        }
    }
    return null;
}

function countDirection(board, row, column, color, deltaRow, deltaCol) {
    let r = row + deltaRow;
    let c = column + deltaCol;
    let total = 0;
    while (r >= 0 && r < BOARD_ROWS && c >= 0 && c < BOARD_COLS) {
        if (board[r][c] !== color) {
            break;
        }
        total += 1;
        r += deltaRow;
        c += deltaCol;
    }
    return total;
}

export function isWinningMove(board, row, column, color) {
    const directions = [
        [0, 1],
        [1, 0],
        [1, 1],
        [1, -1],
    ];

    return directions.some(([dRow, dCol]) => {
        const forward = countDirection(board, row, column, color, dRow, dCol);
        const backward = countDirection(board, row, column, color, -dRow, -dCol);
        return forward + backward >= 3;
    });
}

export function isBoardFull(board) {
    return board[0].every((cell) => cell !== null);
}

export function otherColor(color) {
    return color === COLOR_SEQUENCE[0] ? COLOR_SEQUENCE[1] : COLOR_SEQUENCE[0];
}

export function describeTurn(color) {
    return `${COLOR_LABELS[color]} to move`;
}

export function describeVictory(color) {
    return `${COLOR_LABELS[color]} wins!`;
}

export function chooseAiColumn(playableColumns) {
    if (playableColumns.length === 0) {
        return null;
    }
    const index = Math.floor(Math.random() * playableColumns.length);
    return playableColumns[index];
}
