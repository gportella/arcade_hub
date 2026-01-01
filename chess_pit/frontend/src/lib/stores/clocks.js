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
    let lastTick = Date.now();
    let white = initialWhite;
    let black = initialBlack;
    let startTime = turnStart ? Date.parse(turnStart) : null;
    let color = activeColor;
    let running = isActive;

    // Helper to emit current values to subscribers
    const snapshot = () => ({
        whiteRemaining: white,
        blackRemaining: black,
        activeColor: color,
        running,
    });

    const tick = () => {
        const now = Date.now();
        const deltaMs = Math.max(0, now - lastTick);
        lastTick = now;
        if (!running) return;
        const deltaSec = deltaMs / 1000;
        if (color === "white" && typeof white === "number") {
            white = Math.max(0, white - deltaSec);
            if (white === 0) running = false;
        } else if (color === "black" && typeof black === "number") {
            black = Math.max(0, black - deltaSec);
            if (black === 0) running = false;
        }
    };

    const schedule = () => {
        cancel();
        lastTick = Date.now();
        frame = setInterval(() => {
            tick();
            subscribers.forEach((s) => s(snapshot()));
        }, tickInterval);
    };

    const cancel = () => {
        if (frame !== null) {
            clearInterval(frame);
            frame = null;
        }
    };

    const subscribers = new Set();

    const store = readable(snapshot(), (set) => {
        subscribers.add(set);
        // start scheduler if this store is currently running
        if (running) schedule();
        return () => {
            subscribers.delete(set);
            if (!subscribers.size) cancel();
        };
    });

    const start = (currentColor, startTimestamp) => {
        color = currentColor ?? color;
        // If server provided a start timestamp, use it to compute elapsed since then
        if (startTimestamp) {
            startTime = typeof startTimestamp === "number" ? startTimestamp : Date.parse(startTimestamp);
        } else {
            startTime = Date.now();
        }
        // Reset lastTick so first delta is small
        lastTick = Date.now();
        running = true;
        schedule();
    };

    const stop = (updates = {}) => {
        if (updates.white !== undefined && typeof updates.white === "number") {
            white = updates.white;
        }
        if (updates.black !== undefined && typeof updates.black === "number") {
            black = updates.black;
        }
        running = false;
        startTime = null;
        cancel();
        subscribers.forEach((s) => s(snapshot()));
    };

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
            // Accept numeric values from server; otherwise keep current
            white = typeof whiteRemaining === "number" ? whiteRemaining : white;
            black = typeof blackRemaining === "number" ? blackRemaining : black;
            color = newColor ?? color;
            running = Boolean(active);
            startTime = turnStartTime ? Date.parse(turnStartTime) : null;
            // If the server says it's running, ensure scheduler is active
            if (running) {
                // align lastTick to now so the next tick is accurate
                lastTick = Date.now();
                schedule();
            } else {
                cancel();
            }
            subscribers.forEach((s) => s(snapshot()));
        },
    };
}

export function formatClock(seconds) {
    if (seconds == null) return "--:--";
    const clamped = Math.max(0, Math.floor(seconds));
    const minutes = Math.floor(clamped / 60);
    const secs = clamped % 60;
    return `${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}
