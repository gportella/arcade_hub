import { readable } from "svelte/store";

export function createClockStore({
    initialWhite = null,
    initialBlack = null,
    turnStart = null,
    activeColor = "white",
    isActive = false,
    tickInterval = 250,
} = {}) {
    let frame = null;
    let lastUpdate = Date.now();
    let white = initialWhite;
    let black = initialBlack;
    let startTime = turnStart ? Date.parse(turnStart) : null;
    let color = activeColor;
    let running = isActive;

    const calculate = () => {
        const now = Date.now();
        if (running && startTime !== null) {
            const elapsedMs = Math.max(0, now - startTime);
            if (color === "white" && white !== null) {
                white = Math.max(0, initialWhite === null ? white : initialWhite - elapsedMs / 1000);
            } else if (color === "black" && black !== null) {
                black = Math.max(0, initialBlack === null ? black : initialBlack - elapsedMs / 1000);
            }
        }
        lastUpdate = now;
        return {
            whiteRemaining: white,
            blackRemaining: black,
            activeColor: color,
            running,
        };
    };

    const start = (currentColor, startTimestamp) => {
        color = currentColor;
        startTime = typeof startTimestamp === "number" ? startTimestamp : Date.parse(startTimestamp ?? "");
        running = true;
        schedule();
    };

    const stop = (updates = {}) => {
        if (updates.white !== undefined) {
            white = updates.white;
        }
        if (updates.black !== undefined) {
            black = updates.black;
        }
        running = false;
        startTime = null;
        cancel();
    };

    const schedule = () => {
        cancel();
        frame = setInterval(() => {
            subscribers.forEach((subscriber) => subscriber(calculate()));
        }, tickInterval);
    };

    const cancel = () => {
        if (frame !== null) {
            clearInterval(frame);
            frame = null;
        }
    };

    const subscribers = new Set();

    const store = readable(calculate(), (set) => {
        subscribers.add(set);
        if (running) {
            schedule();
        }
        return () => {
            subscribers.delete(set);
            if (!subscribers.size) {
                cancel();
            }
        };
    });

    return {
        subscribe: store.subscribe,
        start,
        stop,
        updateFromServer({
            whiteRemaining,
            blackRemaining,
            turnStartTime,
            active,
            activeColor: newColor,
        }) {
            white = typeof whiteRemaining === "number" ? whiteRemaining : white;
            black = typeof blackRemaining === "number" ? blackRemaining : black;
            color = newColor ?? color;
            running = Boolean(active);
            startTime = turnStartTime ? Date.parse(turnStartTime) : null;
            if (running) {
                initialWhite = white;
                initialBlack = black;
                schedule();
            } else {
                cancel();
            }
            subscribers.forEach((subscriber) => subscriber(calculate()));
        },
    };
}

export function formatClock(seconds) {
    if (seconds == null) {
        return "--:--";
    }
    const clamped = Math.max(0, Math.floor(seconds));
    const minutes = Math.floor(clamped / 60);
    const secs = clamped % 60;
    return `${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}
