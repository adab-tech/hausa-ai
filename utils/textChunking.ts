/**
 * Splits text into chunks safe for a single /api/tts request.
 *
 * backend/routers/audio.py's tts_endpoint caps a single request's text at
 * max_length=2000 -- added after one unbounded ~4,000-char request ran for
 * 1,107s and OOM-killed the production backend on 2026-09-03. A long
 * assistant reply (routinely well past 2000 chars for a detailed
 * explanation) now needs several requests instead of the one the server
 * would reject outright -- this is the splitting logic behind that.
 *
 * Prefers sentence boundaries so a chunk seam doesn't cut audio mid-
 * sentence; falls back to a hard word-boundary split only for a single
 * "sentence" that alone exceeds maxChars (no terminal punctuation in
 * range).
 */
export function chunkTextForTts(text: string, maxChars: number): string[] {
  const trimmed = text.trim();
  if (!trimmed) return [];
  if (trimmed.length <= maxChars) return [trimmed];

  // Each match is a run of non-terminal characters ending in ./!/? (plus
  // trailing whitespace), or -- the fallback alternative -- a final run
  // with no terminal punctuation at all (e.g. a reply cut off mid-thought).
  const sentences = trimmed.match(/[^.!?]+[.!?]+(\s+|$)|[^.!?]+$/g) ?? [trimmed];

  const chunks: string[] = [];
  let current = '';

  const pushCurrent = () => {
    if (current.trim()) chunks.push(current.trim());
    current = '';
  };

  for (const rawSentence of sentences) {
    const sentence = rawSentence.trim();
    if (!sentence) continue;

    if (sentence.length > maxChars) {
      // No terminal punctuation anywhere in range to split on -- hard-cut
      // at the last word boundary before the limit rather than mid-word.
      pushCurrent();
      let remainder = sentence;
      while (remainder.length > maxChars) {
        let cut = remainder.lastIndexOf(' ', maxChars);
        if (cut <= 0) cut = maxChars; // no space to break on at all
        chunks.push(remainder.slice(0, cut).trim());
        remainder = remainder.slice(cut).trim();
      }
      current = remainder;
      continue;
    }

    const candidate = current ? `${current} ${sentence}` : sentence;
    if (candidate.length > maxChars) {
      pushCurrent();
      current = sentence;
    } else {
      current = candidate;
    }
  }
  pushCurrent();

  return chunks;
}
