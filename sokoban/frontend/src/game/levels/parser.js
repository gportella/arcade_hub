export function normalizeLevel(level) {
    const layout = Array.isArray(level.layout) ? level.layout : null;
    const symbolMap = level.symbolMap && typeof level.symbolMap === "object" ? level.symbolMap : null;
    const normalized = {
        ...level,
        grid: { ...(level.grid || {}) },
        wallMask: Array.isArray(level.wallMask) ? level.wallMask.slice() : [],
        pushables: Array.isArray(level.pushables) ? level.pushables.map(cloneCell) : [],
        targets: Array.isArray(level.targets) ? level.targets.map(cloneCell) : [],
        player: level.player ? cloneCell(level.player) : undefined
    };

    if (!layout || layout.length === 0) {
        return finalizeMask(normalized);
    }

    const layoutWidth = layout.reduce((max, row) => Math.max(max, row.length), 0);
    const derivedMask = [];
    const derivedTargets = [];
    const derivedPushables = [];
    let derivedPlayer = normalized.player || null;

    layout.forEach((rawRow, row) => {
        const rowChars = rawRow.split("");
        const maskCells = new Array(layoutWidth).fill("0");

        for (let col = 0; col < layoutWidth; col++) {
            let symbol = rowChars[col] || " ";
            if (symbolMap && Object.prototype.hasOwnProperty.call(symbolMap, symbol)) {
                symbol = symbolMap[symbol];
            }
            switch (symbol) {
                case "#":
                case "X":
                    maskCells[col] = "1";
                    break;
                case ".":
                    derivedTargets.push({ col, row });
                    break;
                case "$":
                    derivedPushables.push({ col, row });
                    break;
                case "@":
                    derivedPlayer = { col, row };
                    break;
                case "*":
                    derivedPushables.push({ col, row });
                    derivedTargets.push({ col, row });
                    break;
                case "+":
                    derivedTargets.push({ col, row });
                    derivedPlayer = { col, row };
                    break;
                default:
                    break;
            }
        }

        derivedMask.push(maskCells.join(""));
    });

    normalized.wallMask = derivedMask;
    if (derivedTargets.length) normalized.targets = derivedTargets;
    if (derivedPushables.length) normalized.pushables = derivedPushables;
    if (derivedPlayer) normalized.player = derivedPlayer;

    if (!normalized.grid.cols || normalized.grid.cols < layoutWidth) {
        normalized.grid.cols = layoutWidth;
    }
    if (!normalized.grid.rows || normalized.grid.rows < layout.length) {
        normalized.grid.rows = layout.length;
    }

    delete normalized.symbolMap;
    return finalizeMask(normalized);
}

function cloneCell(cell) {
    return { col: cell.col, row: cell.row };
}

function finalizeMask(level) {
    if (!Array.isArray(level.wallMask) || level.wallMask.length === 0) {
        return level;
    }

    const cols = level.grid?.cols;
    if (!cols) {
        return level;
    }

    level.wallMask = level.wallMask.map(row => (typeof row === "string" ? row : "").padEnd(cols, "0"));
    if (level.wallMask.length < (level.grid?.rows || 0)) {
        const missing = (level.grid.rows || 0) - level.wallMask.length;
        for (let i = 0; i < missing; i++) {
            level.wallMask.push("0".repeat(cols));
        }
    }
    return level;
}

export function parseSokoban(text, options = {}) {
    if (typeof text !== "string" || !text.length) return [];

    const { baseId = "sokoban", baseName = "Sokoban", symbolMap = null } = options;
    const levels = [];
    const lines = text.replace(/\r\n?/g, "\n").split("\n");
    let current = [];

    const flush = () => {
        if (!current.length) return;
        const index = levels.length + 1;
        const id = `${baseId}-${index}`;
        const name = `${baseName} ${index}`;
        const minLeading = current.reduce((min, row) => {
            const match = row.match(/^\s*/);
            const leading = match ? match[0].length : 0;
            return row.trim().length === 0 ? min : Math.min(min, leading);
        }, Infinity);
        const offset = Number.isFinite(minLeading) ? minLeading : 0;
        const layout = current.map(row => (offset > 0 ? row.slice(offset) : row));
        levels.push(normalizeLevel({ id, name, contour: false, layout, symbolMap }));
        current = [];
    };

    lines.forEach(rawLine => {
        const expanded = rawLine.replace(/\t/g, " ");
        if (expanded.trim().length === 0) {
            flush();
            return;
        }
        if (expanded.trimStart().startsWith(";")) return;
        current.push(expanded);
    });

    flush();
    return levels;
}
