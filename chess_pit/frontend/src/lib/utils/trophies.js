const CUP_TYPES = [
    { type: "gold", value: 10 },
    { type: "silver", value: 5 },
    { type: "bronze", value: 2 },
];

const countTemplate = () => ({ gold: 0, silver: 0, bronze: 0 });

const asNonNegativeInteger = (value) => {
    const parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed <= 0) {
        return 0;
    }
    return Math.floor(parsed);
};

const normaliseLimit = (value) => {
    const parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed <= 0) {
        return 0;
    }
    return Math.floor(parsed);
};

/**
 * Calculate trophy cups for a win count.
 * @param {number | null | undefined} wins
 * @param {number | null | undefined} maxCups
 */
const calculateTrophies = (wins, maxCups = 4) => {
    const availableWins = asNonNegativeInteger(wins);
    const cupLimit = normaliseLimit(maxCups);
    const counts = countTemplate();

    if (!availableWins || !cupLimit) {
        return {
            cups: [],
            counts,
            representedWins: 0,
            remainingWins: availableWins,
            sourceWins: availableWins,
            maxCups: cupLimit,
        };
    }

    let remaining = availableWins;
    const cups = [];

    for (const config of CUP_TYPES) {
        while (remaining >= config.value && cups.length < cupLimit) {
            cups.push({ type: config.type, value: config.value });
            counts[config.type] += 1;
            remaining -= config.value;
        }
    }

    const representedWins = cups.reduce((total, entry) => total + entry.value, 0);

    return {
        cups,
        counts,
        representedWins,
        remainingWins: remaining,
        sourceWins: availableWins,
        maxCups: cupLimit,
    };
};

export { CUP_TYPES, calculateTrophies };
