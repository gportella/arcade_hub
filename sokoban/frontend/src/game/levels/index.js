import demoLevel from "./demo.json";
import puzzlesRaw from "./puzzles.sok?raw";
import { normalizeLevel, parseSokoban } from "./parser.js";

const jsonLevels = [demoLevel].map(normalizeLevel);

const LEGACY_SYMBOL_MAP = {
    "&": "*",
    "*": "$",
    "?": " "
};

const ALLOWED_LAYOUT_CHARS = /^[\s#X.@$+*&?]+$/;
const START_LAYOUT_CHARS = /[X#.@$+&?]/;

function detectSymbolMap(lines) {
    if (!Array.isArray(lines) || lines.length === 0) return null;
    return lines.some(line => /[&?]/.test(line)) ? LEGACY_SYMBOL_MAP : null;
}

function parseMasterFile(rawText) {
    const levels = [];
    const blocks = rawText.replace(/\r\n?/g, "\n").split(/\n\s*\n/);

    blocks.forEach(block => {
        const lines = block.split("\n");
        /** @type {string | null} */
        let displayName = null;
        /** @type {string | null} */
        let setLabel = null;
        let baseId = "puzzle";
        const layoutLines = [];
        let collecting = false;

        lines.forEach(line => {
            const normalizedLine = line.replace(/\r$/, "");
            const trimmedRight = normalizedLine.trimEnd();
            if (trimmedRight.length === 0) return;

            const trimmedStart = trimmedRight.trimStart();
            if (trimmedStart.startsWith(";")) {
                const meta = parseMetadata(trimmedStart.slice(1));
                if (meta.name) displayName = meta.name;
                if (meta.set) setLabel = meta.set;
                if (meta.id) baseId = meta.id;
                return;
            }

            if (!collecting) {
                if (!ALLOWED_LAYOUT_CHARS.test(trimmedRight)) return;
                if (!START_LAYOUT_CHARS.test(trimmedRight)) return;
                collecting = true;
            } else if (!ALLOWED_LAYOUT_CHARS.test(trimmedRight)) {
                return;
            }

            layoutLines.push(normalizedLine);
        });

        if (layoutLines.length === 0) return;
        const rawLayout = layoutLines.join("\n");
        const symbolMap = detectSymbolMap(layoutLines);
        const baseName = displayName || (setLabel ? setLabel.toUpperCase() : "IMPORTED");
        const parsed = parseSokoban(rawLayout, { baseId, baseName, symbolMap });
        levels.push(...parsed);
    });

    return levels;
}

function parseMetadata(text) {
    const meta = {};
    if (typeof text !== "string" || text.trim().length === 0) return meta;

    const normalized = text.trim();
    const matches = [...normalized.matchAll(/(\w+)\s*=\s*/g)];
    matches.forEach((match, index) => {
        const keyRaw = match[1];
        const start = match.index + match[0].length;
        const end = index + 1 < matches.length ? matches[index + 1].index : normalized.length;
        const valueRaw = normalized.slice(start, end).trim();
        if (!keyRaw || !valueRaw) return;
        const key = keyRaw.toLowerCase();
        if (meta[key]) return;
        meta[key] = valueRaw;
    });
    return meta;
}

const sokobanLevels = parseMasterFile(puzzlesRaw);

export const LEVELS = [...sokobanLevels, ...jsonLevels];
export const LEVEL_SEQUENCE = sokobanLevels.map(level => level.id);

export function getDefaultLevelId() {
    if (LEVEL_SEQUENCE.length > 0) return LEVEL_SEQUENCE[0];
    return LEVELS[0] ? LEVELS[0].id : null;
}

export function getLevelById(id) {
    const fallbackId = getDefaultLevelId();
    if (!id) return LEVELS.find(level => level.id === fallbackId) || LEVELS[0];

    const exact = LEVELS.find(level => level.id === id);
    if (exact) return exact;

    const prefixMatch = LEVELS.find(level => level.id.startsWith(`${id}-`) || level.id.startsWith(id));
    return prefixMatch || (fallbackId ? LEVELS.find(level => level.id === fallbackId) : LEVELS[0]);
}

export function getNextLevelId(id) {
    if (!id) return getDefaultLevelId();
    const index = LEVEL_SEQUENCE.indexOf(id);
    if (index >= 0 && index + 1 < LEVEL_SEQUENCE.length) {
        return LEVEL_SEQUENCE[index + 1];
    }
    return null;
}

export function getPreviousLevelId(id) {
    if (!id) return null;
    const index = LEVEL_SEQUENCE.indexOf(id);
    if (index > 0) {
        return LEVEL_SEQUENCE[index - 1];
    }
    return null;
}

export function getLevelProgress(id) {
    const total = LEVEL_SEQUENCE.length;
    const index = id ? LEVEL_SEQUENCE.indexOf(id) : -1;
    return {
        index: index >= 0 ? index : 0,
        total
    };
}
