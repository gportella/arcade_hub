import { clonePuzzle } from './defaultPuzzle'

function buildBoard(vehicles, size, excludeId) {
    const board = Array.from({ length: size }, () => Array(size).fill(null))

    for (const vehicle of vehicles) {
        if (vehicle.id === excludeId) {
            continue
        }

        for (const [row, col] of occupiedCells(vehicle)) {
            if (board[row][col] !== null) {
                throw new Error('Overlapping vehicles in puzzle state.')
            }
            board[row][col] = vehicle.id
        }
    }

    return board
}

function occupiedCells(vehicle) {
    const cells = []
    for (let offset = 0; offset < vehicle.length; offset += 1) {
        if (vehicle.orientation === 'horizontal') {
            cells.push([vehicle.row, vehicle.col + offset])
        } else {
            cells.push([vehicle.row + offset, vehicle.col])
        }
    }
    return cells
}

function ensureWithinBounds(value, size, axis) {
    if (value < 0 || value >= size) {
        throw new Error(`Move would push vehicle beyond the board on the ${axis} axis.`)
    }
}

export function isSolved(state) {
    for (const vehicle of state.vehicles) {
        if (!vehicle.goal) {
            continue
        }

        if (vehicle.orientation !== 'horizontal') {
            return false
        }

        const tailCol = vehicle.col + vehicle.length - 1
        if (vehicle.row === state.exit.row && tailCol === state.exit.col) {
            return true
        }
    }

    return false
}

export function applyMove(state, move) {
    if (!move || typeof move.steps !== 'number' || move.steps === 0) {
        throw new Error('Move must include a non-zero step count.')
    }

    const nextState = clonePuzzle(state)
    const vehiclesById = new Map(nextState.vehicles.map((vehicle) => [vehicle.id, vehicle]))
    const target = vehiclesById.get(move.vehicleId)

    if (!target) {
        throw new Error(`Vehicle '${move.vehicleId}' does not exist.`)
    }

    const stepCount = Math.abs(move.steps)
    const direction = move.steps > 0 ? 1 : -1

    const board = buildBoard(nextState.vehicles, nextState.size, target.id)

    let row = target.row
    let col = target.col

    for (let index = 0; index < stepCount; index += 1) {
        if (target.orientation === 'horizontal') {
            const nextCol = direction > 0 ? col + target.length : col - 1
            ensureWithinBounds(nextCol, nextState.size, 'col')
            if (board[row][nextCol] !== null) {
                throw new Error('Another vehicle blocks the path.')
            }
            col += direction
        } else {
            const nextRow = direction > 0 ? row + target.length : row - 1
            ensureWithinBounds(nextRow, nextState.size, 'row')
            if (board[nextRow][col] !== null) {
                throw new Error('Another vehicle blocks the path.')
            }
            row += direction
        }
    }

    target.row = row
    target.col = col

    return { state: nextState, completed: isSolved(nextState) }
}

export function resetState(base) {
    return clonePuzzle(base)
}
