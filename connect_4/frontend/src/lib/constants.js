export const BOARD_COLS = 7;
export const BOARD_ROWS = 6;

export const COLORS = {
    YELLOW: 0,
    RED: 1,
};

export const COLOR_SEQUENCE = [COLORS.YELLOW, COLORS.RED];
export const COLOR_LABELS = {
    [COLORS.YELLOW]: 'Yellow',
    [COLORS.RED]: 'Red',
};

export const COLOR_CLASS = {
    [COLORS.YELLOW]: 'disc-yellow',
    [COLORS.RED]: 'disc-red',
};

export const MODES = {
    SOLO: 'solo',
    MULTIPLAYER: 'multiplayer',
};

export const DIFFICULTIES = {
    CASUAL: 'casual',
    STANDARD: 'standard',
    CHALLENGER: 'challenger',
    EXPERT: 'expert',
};

export const DEFAULT_DIFFICULTY = DIFFICULTIES.STANDARD;

export const DIFFICULTY_LABELS = {
    [DIFFICULTIES.CASUAL]: 'Casual',
    [DIFFICULTIES.STANDARD]: 'Standard',
    [DIFFICULTIES.CHALLENGER]: 'Challenger',
    [DIFFICULTIES.EXPERT]: 'Expert',
};

export const DIFFICULTY_DESCRIPTIONS = {
    [DIFFICULTIES.CASUAL]: 'Quick games, shallow lookahead.',
    [DIFFICULTIES.STANDARD]: 'Balanced challenge with moderate search.',
    [DIFFICULTIES.CHALLENGER]: 'Stronger AI with deeper tactics.',
    [DIFFICULTIES.EXPERT]: 'Maximum depth for serious competition.',
};

export const DIFFICULTY_DEPTH = {
    [DIFFICULTIES.CASUAL]: 3,
    [DIFFICULTIES.STANDARD]: 5,
    [DIFFICULTIES.CHALLENGER]: 7,
    [DIFFICULTIES.EXPERT]: 9,
};
