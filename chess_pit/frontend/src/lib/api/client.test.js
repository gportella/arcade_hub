import { describe, expect, it } from 'vitest';
import { composeWebSocketUrl } from './client.js';

describe('composeWebSocketUrl', () => {
    it('builds websocket URL for direct backend access', () => {
        const result = composeWebSocketUrl('http://localhost:8000', '/ws/games/5');
        expect(result).toBe('ws://localhost:8000/ws/games/5');
    });

    it('avoids duplicating ws segment when base already ends with ws', () => {
        const result = composeWebSocketUrl('https://example.com/chess/ws', '/ws/games/12');
        expect(result).toBe('wss://example.com/chess/ws/games/12');
    });

    it('works when base already has trailing slash', () => {
        const result = composeWebSocketUrl('https://example.com/chess/ws/', '/ws/games/9');
        expect(result).toBe('wss://example.com/chess/ws/games/9');
    });

    it('handles custom path segments without ws prefix', () => {
        const result = composeWebSocketUrl('https://example.com/chess', '/api/health');
        expect(result).toBe('wss://example.com/chess/api/health');
    });
});
