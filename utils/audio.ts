
/**
 * Create an AudioContext as close to `desiredRate` as the browser allows.
 *
 * Quirks this absorbs:
 * - Older Safari only exposes `webkitAudioContext` (no unprefixed ctor).
 * - Some browsers (older Safari, certain Android WebViews) THROW when the
 *   constructor is given a `sampleRate` they don't support; others accept it
 *   but silently ignore it. We therefore try the hint, fall back to a
 *   default-rate context, and callers must always read the REAL
 *   `ctx.sampleRate` instead of assuming the hint took effect.
 */
export function makeAudioContext(desiredRate?: number): AudioContext {
  const Ctor: typeof AudioContext =
    window.AudioContext || (window as any).webkitAudioContext;
  if (desiredRate) {
    try {
      return new Ctor({ sampleRate: desiredRate });
    } catch {
      // Constructor rejected the rate hint — fall through to default rate.
    }
  }
  return new Ctor();
}

/**
 * Linear-interpolation resampler for mono Float32 mic frames.
 *
 * Needed because the live-voice protocol requires 16 kHz PCM-16, but many
 * browsers capture at their hardware rate (commonly 44.1/48 kHz) regardless
 * of the AudioContext sampleRate hint. Sending 48 kHz samples labelled as
 * 16 kHz makes speech sound ~3x slow/garbled to the server's ASR — this is
 * the main "voice not detected on some devices" failure mode.
 *
 * Always returns a fresh array (even when rates match) so callers can hold
 * onto it safely after the ScriptProcessor recycles its input buffer.
 */
export function resampleLinear(
  input: Float32Array,
  fromRate: number,
  toRate: number,
): Float32Array {
  if (fromRate === toRate) return new Float32Array(input);
  const outLength = Math.max(1, Math.round((input.length * toRate) / fromRate));
  const out = new Float32Array(outLength);
  const step = (input.length - 1) / Math.max(1, outLength - 1);
  for (let i = 0; i < outLength; i++) {
    const pos = i * step;
    const i0 = Math.floor(pos);
    const i1 = Math.min(i0 + 1, input.length - 1);
    const frac = pos - i0;
    out[i] = input[i0] * (1 - frac) + input[i1] * frac;
  }
  return out;
}

export function encode(bytes: Uint8Array): string {
  let binary = '';
  const len = bytes.byteLength;
  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

export function decode(base64: string): Uint8Array {
  const binaryString = atob(base64);
  const len = binaryString.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes;
}

export async function decodeAudioData(
  data: Uint8Array,
  ctx: AudioContext,
  sampleRate: number,
  numChannels: number,
): Promise<AudioBuffer> {
  const dataInt16 = new Int16Array(data.buffer);
  const frameCount = dataInt16.length / numChannels;
  const buffer = ctx.createBuffer(numChannels, frameCount, sampleRate);

  for (let channel = 0; channel < numChannels; channel++) {
    const channelData = buffer.getChannelData(channel);
    for (let i = 0; i < frameCount; i++) {
      channelData[i] = dataInt16[i * numChannels + channel] / 32768.0;
    }
  }
  return buffer;
}

export function createBlob(data: Float32Array): { data: string; mimeType: string } {
  const l = data.length;
  const int16 = new Int16Array(l);
  for (let i = 0; i < l; i++) {
    int16[i] = data[i] * 32768;
  }
  return {
    data: encode(new Uint8Array(int16.buffer)),
    mimeType: 'audio/pcm;rate=16000',
  };
}
