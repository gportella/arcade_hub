import { describe, expect, it } from 'vitest';
import { normalizeFen, fenEquals } from './fen.js';

describe('normalizeFen', () => {
    it('returns null when input is empty', () => {
        expect(normalizeFen(null)).toBeNull();
        expect(normalizeFen('   ')).toBeNull();
    });

    it('normalizes fen spacing and truncates extra fields', () => {
        const value = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w   KQkq  -  0  1  extra';
        expect(normalizeFen(value)).toBe('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');
    });

    it('pads missing fields with dashes', () => {
        const value = '8/8/8/8/8/8/8/8 w';
        expect(normalizeFen(value)).toBe('8/8/8/8/8/8/8/8 w - - - -');
    });
});

describe('fenEquals', () => {
    it('treats equivalent FEN strings as equal', () => {
        const left = '8/8/8/8/8/8/8/8 w - - 0 1';
        const right = '8/8/8/8/8/8/8/8   w   - -   0 1';
        expect(fenEquals(left, right)).toBe(true);
    });

    it('detects differences after normalization', () => {
        const left = '8/8/8/8/8/8/8/8 w - - 0 1';
        const right = '8/8/8/8/8/8/8/8 b - - 0 1';
        expect(fenEquals(left, right)).toBe(false);
    });

    it('ignores halfmove and fullmove counters when comparing', () => {
        const left = '8/8/8/8/8/8/8/8 w - - 12 27';
        const right = '8/8/8/8/8/8/8/8 w - - 0 1';
        expect(fenEquals(left, right)).toBe(true);
    });

    it('handles null values', () => {
        expect(fenEquals(null, null)).toBe(true);
        expect(fenEquals(null, '8/8/8/8/8/8/8/8 w - - 0 1')).toBe(false);
    });
});
