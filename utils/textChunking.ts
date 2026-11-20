/** Split speech at sentence or word boundaries without dropping text. */
export function chunkTextForTts(text: string, maxChars: number): string[] {
  const chunks: string[] = [];
  let remainder = text.trim();

  while (remainder.length > maxChars) {
    const window = remainder.slice(0, maxChars + 1);
    let sentenceEnd = 0;
    let wordEnd = 0;
    for (const match of window.matchAll(/\s+/gu)) {
      const boundary = match.index;
      wordEnd = boundary;
      if (/[.!?…]["'’”)\]]*$/.test(window.slice(0, boundary))) {
        sentenceEnd = boundary;
      }
    }
    let cut = sentenceEnd || wordEnd || maxChars;
    if (cut > 1 && /[\uDC00-\uDFFF]/.test(remainder[cut])) cut -= 1;
    chunks.push(remainder.slice(0, cut));
    remainder = remainder.slice(cut).trimStart();
  }

  if (remainder) chunks.push(remainder);
  return chunks;
}
