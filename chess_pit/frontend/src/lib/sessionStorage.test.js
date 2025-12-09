import { describe, expect, it, beforeEach, vi } from 'vitest';
import {
    TOKEN_STORAGE_KEY,
    loadStoredToken,
    persistToken,
    clearStoredToken,
} from './sessionStorage.js';

describe('sessionStorage helpers', () => {
    beforeEach(() => {
        window.localStorage.clear();
        vi.restoreAllMocks();
    });

    it('returns null when nothing is stored', () => {
        expect(loadStoredToken()).toBeNull();
    });

    it('persists and retrieves tokens', () => {
        persistToken('example-token');
        expect(window.localStorage.getItem(TOKEN_STORAGE_KEY)).toBe('example-token');
        expect(loadStoredToken()).toBe('example-token');
    });

    it('clears the stored token', () => {
        persistToken('temporary-token');
        clearStoredToken();
        expect(window.localStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull();
        expect(loadStoredToken()).toBeNull();
    });

    it('removes storage when persistToken receives falsy values', () => {
        persistToken('keep-me');
        persistToken('');
        expect(window.localStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull();
        persistToken(null);
        expect(window.localStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull();
    });

    it('fails silently when localStorage throws', () => {
        const getItemSpy = vi.spyOn(window.localStorage, 'getItem').mockImplementation(() => {
            throw new Error('denied');
        });
        const setItemSpy = vi.spyOn(window.localStorage, 'setItem').mockImplementation(() => {
            throw new Error('denied');
        });
        const removeItemSpy = vi.spyOn(window.localStorage, 'removeItem').mockImplementation(() => {
            throw new Error('denied');
        });

        expect(loadStoredToken()).toBeNull();
        expect(() => persistToken('value')).not.toThrow();
        expect(() => clearStoredToken()).not.toThrow();

        getItemSpy.mockRestore();
        setItemSpy.mockRestore();
        removeItemSpy.mockRestore();
    });
});
