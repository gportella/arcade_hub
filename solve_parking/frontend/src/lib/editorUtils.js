import { clonePuzzle } from './defaultPuzzle'

function occupiedCells(vehicle) {
    const cells = []
    for (let index = 0; index < vehicle.length; index += 1) {
        if (vehicle.orientation === 'horizontal') {
            cells.push([vehicle.row, vehicle.col + index])
        } else {
            cells.push([vehicle.row + index, vehicle.col])
        }
    }
    return cells
}

function buildBoard(vehicles, size, excludeId) {
    const board = Array.from({ length: size }, () => Array(size).fill(null))

    for (const vehicle of vehicles) {
        if (vehicle.id === excludeId) {
            continue
        }
        for (const [row, col] of occupiedCells(vehicle)) {
            board[row][col] = vehicle.id
        }
    }

    return board
}

function assertPlacement(puzzle, candidate, excludeId) {
    if (candidate.row < 0 || candidate.col < 0) {
        throw new Error('Vehicle coordinates must be non-negative.')
    }

    if (candidate.goal && candidate.orientation !== 'horizontal') {
        throw new Error('Goal vehicle must be horizontal.')
    }

    if (candidate.orientation === 'horizontal') {
        if (candidate.col + candidate.length > puzzle.size) {
            throw new Error('Vehicle extends beyond the board horizontally.')
        }
    } else if (candidate.row + candidate.length > puzzle.size) {
        throw new Error('Vehicle extends beyond the board vertically.')
    }

    const board = buildBoard(puzzle.vehicles, puzzle.size, excludeId)

    for (const [row, col] of occupiedCells(candidate)) {
        if (row >= puzzle.size || col >= puzzle.size) {
            throw new Error('Vehicle occupies a cell outside the board.')
        }
        if (board[row][col] !== null) {
            throw new Error('Vehicle overlaps another piece.')
        }
    }
}

export function nextVehicleId(puzzle, goal) {
    const used = new Set(puzzle.vehicles.map((vehicle) => vehicle.id))
    if (goal) {
        if (puzzle.vehicles.some((vehicle) => vehicle.goal)) {
            throw new Error('Puzzle already has a goal vehicle.')
        }
        return 'X'
    }

    const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    for (const letter of alphabet) {
        if (letter === 'X') {
            continue
        }
        if (!used.has(letter)) {
            return letter
        }
    }

    throw new Error('No available vehicle identifiers remaining.')
}

export function findPlacement(puzzle, orientation, length) {
    const candidate = { row: 0, col: 0, length, orientation, goal: false, id: '_' }

    for (let row = 0; row < puzzle.size; row += 1) {
        for (let col = 0; col < puzzle.size; col += 1) {
            candidate.row = row
            candidate.col = col
            try {
                assertPlacement(puzzle, candidate, null)
                return { row, col }
            } catch (error) {
                // try next position
            }
        }
    }

    return null
}

export function insertVehicle(puzzle, vehicle) {
    const draft = clonePuzzle(puzzle)
    if (vehicle.goal && draft.vehicles.some((existing) => existing.goal)) {
        throw new Error('Only one goal vehicle is allowed.')
    }
    assertPlacement(draft, vehicle, null)
    draft.vehicles = [...draft.vehicles, { ...vehicle }]
    return draft
}

export function removeVehicle(puzzle, id) {
    const draft = clonePuzzle(puzzle)
    draft.vehicles = draft.vehicles.filter((vehicle) => vehicle.id !== id)
    return draft
}

function clampVehicleWithinBounds(vehicle, size) {
    const maxRow = vehicle.orientation === 'vertical'
        ? size - vehicle.length
        : size - 1
    const maxCol = vehicle.orientation === 'horizontal'
        ? size - vehicle.length
        : size - 1

    vehicle.row = Math.min(Math.max(vehicle.row, 0), Math.max(0, maxRow))
    vehicle.col = Math.min(Math.max(vehicle.col, 0), Math.max(0, maxCol))
}

function findRelocationSpot(puzzle, vehicle, excludeId) {
    const candidate = { ...vehicle }
    for (let row = 0; row < puzzle.size; row += 1) {
        candidate.row = row
        for (let col = 0; col < puzzle.size; col += 1) {
            candidate.col = col
            try {
                assertPlacement(puzzle, candidate, excludeId)
                return { row, col }
            } catch (error) {
                // try next location
            }
        }
    }
    return null
}

export function updateVehicle(puzzle, id, updates, options = {}) {
    const { autoPlace = false, validate = true } = options
    const draft = clonePuzzle(puzzle)
    const index = draft.vehicles.findIndex((vehicle) => vehicle.id === id)
    if (index === -1) {
        throw new Error(`Vehicle ${id} not found`)
    }

    const nextVehicle = { ...draft.vehicles[index], ...updates }
    if (nextVehicle.goal) {
        for (const vehicle of draft.vehicles) {
            if (vehicle.id !== id && vehicle.goal) {
                throw new Error('Only one goal vehicle is allowed.')
            }
        }
    }
    clampVehicleWithinBounds(nextVehicle, draft.size)

    if (validate) {
        let placementError = null
        try {
            assertPlacement(draft, nextVehicle, id)
        } catch (error) {
            placementError = error
        }

        if (placementError) {
            if (!autoPlace) {
                throw placementError
            }
            const alternative = findRelocationSpot(draft, nextVehicle, id)
            if (!alternative) {
                throw placementError
            }
            nextVehicle.row = alternative.row
            nextVehicle.col = alternative.col
        }

        assertPlacement(draft, nextVehicle, id)
    } else if (autoPlace) {
        const alternative = findRelocationSpot(draft, nextVehicle, id)
        if (alternative) {
            nextVehicle.row = alternative.row
            nextVehicle.col = alternative.col
        }
    }

    draft.vehicles = [
        ...draft.vehicles.slice(0, index),
        nextVehicle,
        ...draft.vehicles.slice(index + 1),
    ]
    return draft
}

export function validateDraft(puzzle) {
    if (!puzzle || typeof puzzle.size !== 'number') {
        throw new Error('Puzzle must include a board size.')
    }

    if (puzzle.size < 2 || puzzle.size > 12) {
        throw new Error('Board size must be between 2 and 12.')
    }

    if (puzzle.exit.row < 0 || puzzle.exit.row >= puzzle.size) {
        throw new Error('Exit row must be within the board bounds.')
    }

    if (puzzle.exit.col < 0 || puzzle.exit.col >= puzzle.size) {
        throw new Error('Exit column must be within the board bounds.')
    }

    if (!Array.isArray(puzzle.vehicles) || puzzle.vehicles.length === 0) {
        throw new Error('Puzzle must contain at least one vehicle.')
    }

    const goalVehicles = puzzle.vehicles.filter((vehicle) => vehicle.goal)
    if (goalVehicles.length !== 1) {
        throw new Error('Puzzle must include exactly one goal vehicle.')
    }

    if (goalVehicles[0].orientation !== 'horizontal') {
        throw new Error('Goal vehicle must be horizontal.')
    }

    for (const vehicle of puzzle.vehicles) {
        assertPlacement(puzzle, vehicle, vehicle.id)
    }
}

export function findOverlappingVehicles(puzzle) {
    if (!puzzle || typeof puzzle.size !== 'number' || !Array.isArray(puzzle.vehicles)) {
        return new Set()
    }

    const size = puzzle.size
    const conflicts = new Set()
    const board = Array.from({ length: size }, () => Array(size).fill(null))

    for (const vehicle of puzzle.vehicles) {
        for (const [row, col] of occupiedCells(vehicle)) {
            if (row < 0 || col < 0 || row >= size || col >= size) {
                conflicts.add(vehicle.id)
                continue
            }
            const occupant = board[row][col]
            if (occupant && occupant !== vehicle.id) {
                conflicts.add(vehicle.id)
                conflicts.add(occupant)
            } else {
                board[row][col] = vehicle.id
            }
        }
    }

    return conflicts
}

export function setBoardSize(puzzle, size) {
    const nextSize = Math.min(Math.max(Math.trunc(size), 2), 12)
    const draft = clonePuzzle(puzzle)
    draft.size = nextSize
    if (draft.exit.row >= nextSize) {
        draft.exit.row = nextSize - 1
    }
    draft.exit.col = nextSize - 1

    for (const vehicle of draft.vehicles) {
        if (vehicle.orientation === 'horizontal') {
            if (vehicle.col + vehicle.length > nextSize) {
                throw new Error(`Vehicle ${vehicle.id} no longer fits after resizing.`)
            }
        } else if (vehicle.row + vehicle.length > nextSize) {
            throw new Error(`Vehicle ${vehicle.id} no longer fits after resizing.`)
        }
    }

    return draft
}

export function setExitRow(puzzle, row) {
    const draft = clonePuzzle(puzzle)
    const nextRow = Math.min(Math.max(Math.trunc(row), 0), draft.size - 1)
    draft.exit = { ...draft.exit, row: nextRow }
    return draft
}

export function setExitCol(puzzle, col) {
    const draft = clonePuzzle(puzzle)
    const nextCol = Math.min(Math.max(Math.trunc(col), 0), draft.size - 1)
    draft.exit = { ...draft.exit, col: nextCol }
    return draft
}