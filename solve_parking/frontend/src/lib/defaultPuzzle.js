const basePuzzle = {
    size: 6,
    exit: { row: 2, col: 5 },
    vehicles: [
        { id: 'C', row: 0, col: 0, length: 3, orientation: 'vertical', goal: false },
        { id: 'A', row: 0, col: 3, length: 2, orientation: 'vertical', goal: false },
        { id: 'B', row: 0, col: 4, length: 3, orientation: 'vertical', goal: false },
        { id: 'D', row: 3, col: 2, length: 2, orientation: 'horizontal', goal: false },
        { id: 'E', row: 4, col: 1, length: 3, orientation: 'horizontal', goal: false },
        { id: 'F', row: 3, col: 5, length: 2, orientation: 'vertical', goal: false },
        { id: 'G', row: 5, col: 0, length: 2, orientation: 'horizontal', goal: false },
        { id: 'H', row: 5, col: 2, length: 2, orientation: 'horizontal', goal: false },
        { id: 'X', row: 2, col: 1, length: 2, orientation: 'horizontal', goal: true }
    ]
}

export const defaultPuzzle = Object.freeze(basePuzzle)

export function clonePuzzle(puzzle = defaultPuzzle) {
    if (typeof structuredClone === 'function') {
        return structuredClone(puzzle)
    }
    return JSON.parse(JSON.stringify(puzzle))
}

export function createEmptyPuzzle(size = 6) {
    const clampedSize = Math.min(Math.max(size, 2), 12)
    const exitRow = Math.min(2, clampedSize - 1)
    return {
        size: clampedSize,
        exit: { row: exitRow, col: clampedSize - 1 },
        vehicles: [],
    }
}
