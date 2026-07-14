/**
 * Reliable microphone recorder that produces a WAV blob — no MediaRecorder.
 *
 * MediaRecorder is flaky on iOS/Safari (mimeType support varies, data sometimes
 * never flushes, and its webm output won't play back in an <audio> element on
 * Safari). This captures raw PCM via the Web Audio API (the same ScriptProcessor
 * path the live-voice pipeline uses, which works on iOS) and encodes a standard
 * 16-bit PCM WAV — which records everywhere and previews everywhere. The backend
 * decodes WAV trivially (pydub) and resamples to 24 kHz.
 */

function encodeWav(chunks: Float32Array[], sampleRate: number): Blob {
  const length = chunks.reduce((n, c) => n + c.length, 0);
  const flat = new Float32Array(length);
  let off = 0;
  for (const c of chunks) { flat.set(c, off); off += c.length; }

  const buffer = new ArrayBuffer(44 + flat.length * 2);
  const view = new DataView(buffer);
  const writeStr = (o: number, s: string) => { for (let i = 0; i < s.length; i++) view.setUint8(o + i, s.charCodeAt(i)); };
  writeStr(0, 'RIFF');
  view.setUint32(4, 36 + flat.length * 2, true);
  writeStr(8, 'WAVE');
  writeStr(12, 'fmt ');
  view.setUint32(16, 16, true);      // PCM chunk size
  view.setUint16(20, 1, true);       // PCM format
  view.setUint16(22, 1, true);       // mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true); // byte rate
  view.setUint16(32, 2, true);       // block align
  view.setUint16(34, 16, true);      // bits per sample
  writeStr(36, 'data');
  view.setUint32(40, flat.length * 2, true);
  let o = 44;
  for (let i = 0; i < flat.length; i++, o += 2) {
    const s = Math.max(-1, Math.min(1, flat[i]));
    view.setInt16(o, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Blob([view], { type: 'audio/wav' });
}

export class WavRecorder {
  private ctx?: AudioContext;
  private stream?: MediaStream;
  private source?: MediaStreamAudioSourceNode;
  private processor?: ScriptProcessorNode;
  private chunks: Float32Array[] = [];
  private sampleRate = 44100;

  /** Request the mic and begin capturing. Throws on permission/hardware errors
   * (caller should surface err.name). */
  async start(): Promise<void> {
    if (!navigator.mediaDevices?.getUserMedia) {
      const e: any = new Error('getUserMedia unavailable'); e.name = 'NotSupportedError'; throw e;
    }
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true },
    });
    const Ctx: typeof AudioContext = (window.AudioContext || (window as any).webkitAudioContext);
    this.ctx = new Ctx();
    // iOS starts contexts suspended; resume within the user gesture that called start().
    if (this.ctx.state === 'suspended') { try { await this.ctx.resume(); } catch { /* re-checked at stop */ } }
    this.sampleRate = this.ctx.sampleRate;
    this.source = this.ctx.createMediaStreamSource(this.stream);
    this.processor = this.ctx.createScriptProcessor(4096, 1, 1);
    this.chunks = [];
    this.processor.onaudioprocess = (e) => {
      // Copy — the underlying buffer is reused by the browser.
      this.chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
    };
    this.source.connect(this.processor);
    this.processor.connect(this.ctx.destination); // some browsers won't fire onaudioprocess otherwise
  }

  /** Stop, release the mic, and return the recorded WAV. */
  stop(): Blob {
    try { this.processor?.disconnect(); } catch { /* ignore */ }
    try { this.source?.disconnect(); } catch { /* ignore */ }
    this.stream?.getTracks().forEach((t) => t.stop());
    const wav = encodeWav(this.chunks, this.sampleRate);
    try { this.ctx?.close(); } catch { /* ignore */ }
    return wav;
  }
}
