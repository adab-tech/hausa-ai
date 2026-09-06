import { describe, it, expect } from 'vitest';
import { chunkTextForTts } from '../textChunking.ts';

describe('chunkTextForTts', () => {
  it('returns the whole text as one chunk when already under the limit', () => {
    expect(chunkTextForTts('Sannu, yaya kake?', 1800)).toEqual(['Sannu, yaya kake?']);
  });

  it('returns an empty array for blank input', () => {
    expect(chunkTextForTts('   ', 1800)).toEqual([]);
    expect(chunkTextForTts('', 1800)).toEqual([]);
  });

  it('splits at sentence boundaries, keeping terminal punctuation attached', () => {
    const text = 'Wannan jimla ce ta farko. Wannan ita ce ta biyu! Kuma wannan ita ce ta uku?';
    // Force a split after each short sentence by using a tiny limit.
    const chunks = chunkTextForTts(text, 30);
    expect(chunks.length).toBeGreaterThan(1);
    for (const chunk of chunks) {
      expect(chunk.length).toBeLessThanOrEqual(30);
    }
    // Rejoining should reproduce the original sentences (modulo the single
    // space chunkTextForTts uses to join sentences within a chunk).
    expect(chunks.join(' ')).toBe(text);
  });

  it('never produces a chunk over the limit', () => {
    const sentence = 'a '.repeat(50).trim() + '.';
    const text = `${sentence} ${sentence} ${sentence}`;
    const chunks = chunkTextForTts(text, 40);
    for (const chunk of chunks) {
      expect(chunk.length).toBeLessThanOrEqual(40);
    }
  });

  it('hard-splits a single sentence with no terminal punctuation that alone exceeds the limit', () => {
    const words = Array.from({ length: 40 }, (_, i) => `kalma${i}`);
    const text = words.join(' '); // no '.', '!', or '?' anywhere
    const chunks = chunkTextForTts(text, 50);
    expect(chunks.length).toBeGreaterThan(1);
    for (const chunk of chunks) {
      expect(chunk.length).toBeLessThanOrEqual(50);
    }
    // No word should be split in half, and no word should be lost.
    expect(chunks.join(' ').split(/\s+/).sort()).toEqual(words.slice().sort());
  });

  it('packs multiple short sentences into one chunk when they fit together', () => {
    const text = 'Ɗan gajeren jimla. Wani kuma. Da wani.';
    const chunks = chunkTextForTts(text, 1800);
    expect(chunks).toEqual([text]);
  });
});
