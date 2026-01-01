const MAX_CP = 2000;
const DEFAULT_WDL = { white: 1 / 3, draw: 1 / 3, black: 1 / 3 };

function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
}

function normaliseProbabilities(probabilities) {
    const total = probabilities.white + probabilities.draw + probabilities.black;
    if (total <= 0) {
        return { ...DEFAULT_WDL };
    }
    return {
        white: probabilities.white / total,
        draw: probabilities.draw / total,
        black: probabilities.black / total,
    };
}

export function evaluationToWdl({ evaluationCp = null, mateIn = null } = {}) {
    if (typeof mateIn === "number" && mateIn !== 0) {
        if (mateIn > 0) {
            return normaliseProbabilities({ white: 0.99, draw: 0.01, black: 0 });
        }
        return normaliseProbabilities({ white: 0, draw: 0.01, black: 0.99 });
    }

    if (typeof evaluationCp !== "number" || Number.isNaN(evaluationCp)) {
        return { ...DEFAULT_WDL };
    }

    const capped = clamp(evaluationCp, -MAX_CP, MAX_CP);
    const absScore = Math.abs(capped);
    const drawBase = 0.15 + 0.55 * Math.exp(-absScore / 250);
    const decisiveShare = Math.max(0, 1 - drawBase);
    const logistic = 1 / (1 + Math.exp(-capped / 120));
    const probabilities = {
        white: decisiveShare * logistic,
        draw: drawBase,
        black: decisiveShare * (1 - logistic),
    };

    return normaliseProbabilities(probabilities);
}

export function toPercentage(value) {
    if (typeof value !== "number" || !Number.isFinite(value)) {
        return 0;
    }
    return clamp(Math.round(value * 100), 0, 100);
}
