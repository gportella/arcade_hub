const TOKEN_STORAGE_KEY = "rook-on.auth.token";

function getStorage() {
    if (typeof window === "undefined") {
        return null;
    }
    try {
        return window.localStorage ?? null;
    } catch (_error) {
        return null;
    }
}

export function loadStoredToken() {
    const storage = getStorage();
    if (!storage) {
        return null;
    }
    try {
        const token = storage.getItem(TOKEN_STORAGE_KEY);
        return token && token.trim() ? token : null;
    } catch (_error) {
        return null;
    }
}

export function persistToken(token) {
    const storage = getStorage();
    if (!storage) {
        return;
    }
    if (!token) {
        clearStoredToken();
        return;
    }
    try {
        storage.setItem(TOKEN_STORAGE_KEY, token);
    } catch (_error) {
        /* no-op */
    }
}

export function clearStoredToken() {
    const storage = getStorage();
    if (!storage) {
        return;
    }
    try {
        storage.removeItem(TOKEN_STORAGE_KEY);
    } catch (_error) {
        /* no-op */
    }
}

export { TOKEN_STORAGE_KEY };
