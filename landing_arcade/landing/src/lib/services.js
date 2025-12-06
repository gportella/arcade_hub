const HUB_TITLES = [
    'Arcade Hub: Stack Ws',
    'Arcade Hub: Tap In',
    'Arcade Hub: Run It',
    'Arcade Hub: Lock In & Play',
    'Arcade Hub: Brain Flex',
    'Quick plays, big Ws',
    'No cap, these games hit',
    'Lowkey chill, highkey wins',
    'OG puzzles, modern drip',
    'New Drops',
    'Trending Now',
    'New drop unlocked',
    'Daily streak on',
];

const SERVICE_TAGLINES = {
    connect4: [
        'Slide, drop, connect',
        'Connect 4: Drop 4',
        'Connect 4: Stack 4',
        'Connect 4: Quad Link',
        'Tap In',
        'Run It',
        'Queue Up',
        'Drop In',
        'Lock In',
        'Speedrun',
        'Rematch',
        'Versus Mode',
        'Clutch Drop',
        'Stack Master',
        'Speedrunner',
        'GOAT Move',
        'W secured',
        'Rematch queued',
        'First W',
        'Giga Brain',
        'Locking in...',
    ],
    unblock: [
        'Unblock Me: Slide Escape',
        'Unblock Me: Path Flex',
        'Unblock Me: Exit Rush',
        'Unblock Me: Grid Glide',
        'Chill Mode',
        'Sweaty Mode',
        'Quick Hits',
        'Brain Flex',
        'OG Classics',
        'Slide Savant',
        'Grid Guru',
        'Hint ready (lowkey)',
    ],
};

function pickRandom(options) {
    if (!Array.isArray(options) || options.length === 0) {
        return null;
    }
    const index = Math.floor(Math.random() * options.length);
    return options[index];
}

function createDefaultServices() {
    return [
        {
            id: 'unblock',
            name: 'Unblock Me',
            description: 'Slide the blocks to free the target piece.',
            url: import.meta.env.VITE_UNBLOCK_URL ?? 'http://localhost:9000',
            healthUrl: import.meta.env.VITE_UNBLOCK_HEALTH ?? 'http://localhost:9000/health',
            tagline: pickRandom(SERVICE_TAGLINES.unblock),
        },
        {
            id: 'connect4',
            name: 'Connect 4 Arena',
            description: 'Challenge a friend or the AI to a round of Connect 4.',
            url: import.meta.env.VITE_CONNECT4_URL ?? 'http://localhost:8180',
            healthUrl: import.meta.env.VITE_CONNECT4_HEALTH ?? 'http://localhost:8100/health',
            tagline: pickRandom(SERVICE_TAGLINES.connect4),
        },
    ];
}

function inferTaglineKey(id, name) {
    const normalizedId = (id ?? '').toLowerCase();
    const normalizedName = (name ?? '').toLowerCase();

    if (
        normalizedId.includes('connect4') ||
        normalizedId.includes('connect-4') ||
        normalizedId.includes('connect 4') ||
        normalizedName.includes('connect 4')
    ) {
        return 'connect4';
    }
    if (
        normalizedId.includes('unblock') ||
        normalizedName.includes('unblock') ||
        normalizedName.includes('slide')
    ) {
        return 'unblock';
    }
    return null;
}

function enrichService(entry, index) {
    const id = entry.id ?? `service-${index}`;
    const name = entry.name ?? `Service ${index + 1}`;
    const tagline =
        entry.tagline ??
        (() => {
            const key = inferTaglineKey(id, name);
            return key ? pickRandom(SERVICE_TAGLINES[key]) : null;
        })();

    return {
        id,
        name,
        description: entry.description ?? '',
        url: entry.url,
        healthUrl: entry.healthUrl ?? null,
        tagline,
    };
}

export function randomHubTitle() {
    return pickRandom(HUB_TITLES) ?? 'Arcade Hub';
}

export function loadServices() {
    const raw = import.meta.env.VITE_SERVICES;
    if (!raw) {
        return createDefaultServices();
    }

    try {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.length > 0) {
            return parsed.map((entry, index) => enrichService(entry, index));
        }
    } catch (error) {
        console.warn('Failed to parse VITE_SERVICES, using defaults.', error);
    }

    return createDefaultServices();
}
