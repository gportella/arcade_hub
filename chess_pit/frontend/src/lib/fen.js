const DEFAULT_FEN_FIELDS = 6;

export function normalizeFen(rawFen) {
    if (rawFen == null) {
        return null;
    }
    const trimmed = String(rawFen).trim();
    if (!trimmed) {
        return null;
    }
    const parts = trimmed.split(/\s+/);
    if (parts.length < 2) {
        return null;
    }
    while (parts.length < DEFAULT_FEN_FIELDS) {
        parts.push('-');
    }
    return parts.slice(0, DEFAULT_FEN_FIELDS).join(' ');
}

export function fenEquals(a, b) {
    const left = normalizeFen(a);
    const right = normalizeFen(b);
    if (left === null || right === null) {
        return left === right;
    }
    const leftParts = left.split(' ');
    const rightParts = right.split(' ');
    const compareFields = Math.min(4, leftParts.length, rightParts.length);
    for (let index = 0; index < compareFields; index += 1) {
        if (leftParts[index] !== rightParts[index]) {
            return false;
        }
    }
    return true;
}
