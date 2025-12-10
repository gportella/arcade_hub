const DEFAULT_FEN_FIELDS = 6;

function canonicalCastling(raw) {
    if (!raw || raw === "-") return "-";
    const set = new Set(raw.split("").filter((c) => "KQkq".includes(c)));
    const order = ["K", "Q", "k", "q"];
    const out = order.filter((c) => set.has(c)).join("");
    return out.length ? out : "-";
}

function canonicalEp(raw) {
    if (!raw || raw === "-") return "-";
    const s = String(raw).toLowerCase();
    // En passant targets are only valid on ranks 3 or 6
    return /^[a-h][36]$/.test(s) ? s : "-";
}

export function normalizeFen(rawFen) {
    if (rawFen == null) return null;
    const trimmed = String(rawFen).trim();
    if (!trimmed) return null;

    const parts = trimmed.split(/\s+/);
    while (parts.length < DEFAULT_FEN_FIELDS) parts.push("-");

    const board = parts[0];
    const turn = parts[1] === "b" ? "b" : "w";
    const castling = canonicalCastling(parts[2] || "-");
    const ep = canonicalEp(parts[3] || "-");
    const half = String(parseInt(parts[4] ?? "0", 10) || 0);
    const full = String(parseInt(parts[5] ?? "1", 10) || 1);

    return `${board} ${turn} ${castling} ${ep} ${half} ${full}`;
}

function positionKey(rawFen) {
    const norm = normalizeFen(rawFen);
    if (norm == null) return null;
    const [board, turn, castling, ep] = norm.split(" ");
    return `${board} ${turn} ${castling} ${ep}`;
}

export function fenEquals(a, b) {
    const A = positionKey(a);
    const B = positionKey(b);
    if (A === null || B === null) return A === B;
    return A === B;
}

/**
 * Monotonic ply index from FEN:
 * start (1 w) => 0; after white (1 b) => 1; after black (2 w) => 2; etc.
 */
export function fenPlyIndex(rawFen) {
    const norm = normalizeFen(rawFen);
    if (!norm) return null;
    const parts = norm.split(/\s+/);
    const turn = parts[1]; // 'w' or 'b'
    const full = parseInt(parts[5], 10);
    if (!full || (turn !== "w" && turn !== "b")) return null;
    return (full - 1) * 2 + (turn === "b" ? 1 : 0);
}