import { useEffect, useRef, useState } from 'react';
import { Message, Role, AddresseeGender } from '../types.ts';
import { gemini } from '../services/localService.ts';
import { decodeAudioData, decode, createBlob, makeAudioContext, resampleLinear } from '../utils/audio.ts';

/** Live spoken conversation: mic capture -> WebSocket -> streamed TTS reply,
 * with a half-duplex gate (client-side + server-side backstop) so the
 * assistant doesn't hear and answer itself. This is the most delicate part
 * of the app -- see the inline comments below for why each piece exists;
 * they're all hard-won fixes for real device bugs (iOS Safari suspended
 * contexts, sample-rate mismatches, mic-stays-lit-after-hangup, etc.), not
 * speculative hardening. */
export function useLiveVoice(
  speakerId: number | null,
  addresseeGender: AddresseeGender,
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>,
  showToast: (message: string, variant?: 'error' | 'info') => void
) {
  const [isLiveActive, setIsLiveActive] = useState(false);
  const [volume, setVolume] = useState(0);
  const [callDuration, setCallDuration] = useState(0);
  const [voiceStatus, setVoiceStatus] = useState<'idle' | 'requesting_permission' | 'connecting' | 'connected' | 'error'>('idle');

  const sessionPromiseRef = useRef<Promise<any> | null>(null);
  const audioContextsRef = useRef<{ in?: AudioContext, out?: AudioContext, nextStartTime: number }>({ nextStartTime: 0 });
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  // Pending "assistant finished speaking" notification for the live-voice
  // server-side echo backstop (see setAssistantSpeaking in localService.ts).
  // Re-armed on every TTS chunk so it always fires `tail` seconds after the
  // LAST scheduled chunk of the current reply finishes, not the first.
  const assistantSpeakingOffTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // The live mic stream + the audio graph nodes built on top of it in
  // onopen — stored here so hangup/onclose/onerror can actually tear them
  // down. Previously these were only local closure variables inside
  // onopen, so nothing ever stopped the MediaStream or disconnected the
  // ScriptProcessor: the browser's mic-in-use indicator stayed lit after
  // hangup, and redialing (audioContextsRef.current.in is reused across
  // calls) attached a SECOND onaudioprocess handler while the orphaned
  // first one kept firing into whatever session sessionPromiseRef now
  // pointed at — a real risk of doubled/garbled mic audio on redial.
  const liveAudioNodesRef = useRef<{
    stream: MediaStream;
    source: MediaStreamAudioSourceNode;
    scriptProcessor: ScriptProcessorNode;
  } | null>(null);

  const teardownLiveAudio = () => {
    if (assistantSpeakingOffTimerRef.current) {
      clearTimeout(assistantSpeakingOffTimerRef.current);
      assistantSpeakingOffTimerRef.current = null;
    }
    const nodes = liveAudioNodesRef.current;
    if (nodes) {
      nodes.scriptProcessor.onaudioprocess = null;
      nodes.scriptProcessor.disconnect();
      nodes.source.disconnect();
      nodes.stream.getTracks().forEach(t => t.stop());
      liveAudioNodesRef.current = null;
    }
    sessionPromiseRef.current = null;
  };

  // Handle call timer when live voice is active
  useEffect(() => {
    if (isLiveActive) {
      setCallDuration(0);
      timerRef.current = setInterval(() => {
        setCallDuration(prev => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
      setCallDuration(0);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isLiveActive]);

  const toggleLiveVoice = async () => {
    if (isLiveActive) {
      if (sessionPromiseRef.current) (await sessionPromiseRef.current).close();
      teardownLiveAudio();
      setIsLiveActive(false);
      setVolume(0);
      setVoiceStatus('idle');
      return;
    }

    // Idempotency guard: isLiveActive only flips to true inside onopen
    // below, once getUserMedia + the WebSocket handshake both complete --
    // so a second tap of the mic button while still 'requesting_permission'
    // or 'connecting' re-enters this whole branch a second time. That opened
    // a second MediaStream and a second live session concurrently, with
    // liveAudioNodesRef overwritten by whichever onopen fired last --
    // orphaning the first call's stream/source/scriptProcessor exactly like
    // the redial bug teardownLiveAudio exists to prevent (see its comment
    // above), just triggered by an impatient double-tap instead of a
    // hangup-then-redial.
    if (voiceStatus === 'requesting_permission' || voiceStatus === 'connecting') {
      return;
    }

    // Microphone requires a secure context (HTTPS or localhost) and a browser
    // that exposes getUserMedia. Over plain http on a network IP, or inside a
    // sandboxed iframe, navigator.mediaDevices is undefined — surface that
    // precisely instead of a misleading "permission denied".
    if (!navigator.mediaDevices?.getUserMedia) {
      setVoiceStatus('error');
      showToast(
        "Ba a iya buɗe makirufo ba. Ana buƙatar amintacciyar hanya (HTTPS ko 'localhost') " +
        "kuma browser mai goyon bayan makirufo.\n" +
        "(Live voice needs a secure HTTPS or localhost page — it won't work over plain http " +
        "or inside a restricted preview frame. It will work on the deployed https site.)"
      );
      return;
    }

    try {
        setVoiceStatus('requesting_permission');
        // echoCancellation is essential: without it the mic picks up the
        // assistant's own TTS from the speakers and the model ends up
        // transcribing and answering itself. (Belt: the half-duplex gate in
        // onaudioprocess below; braces: this constraint.)
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
        });
        setVoiceStatus('connecting');

        // Robust context creation. The 16000 for input is only a HINT — older
        // Safari and some Android WebViews throw on (or silently ignore) a
        // forced sampleRate, so makeAudioContext falls back to the device
        // default and we resample mic frames to 16 kHz ourselves below. The
        // output context deliberately uses the default rate: decodeAudioData
        // builds AudioBuffers tagged 24000 explicitly, and WebAudio resamples
        // buffers to the context rate automatically at playback.
        if (!audioContextsRef.current.in) audioContextsRef.current.in = makeAudioContext(16000);
        if (!audioContextsRef.current.out) audioContextsRef.current.out = makeAudioContext();

        const inputCtx = audioContextsRef.current.in!;
        const outputCtx = audioContextsRef.current.out!;

        // iOS Safari frequently leaves AudioContexts "suspended" even after a
        // user gesture — playback then never happens and out.currentTime stays
        // frozen, which would also jam the half-duplex mic gate below. We are
        // still inside the tap handler here, so resume() is permitted; await
        // it so scheduling starts from a running clock.
        try {
          await Promise.all([inputCtx.resume(), outputCtx.resume()]);
        } catch {
          // Non-fatal: some browsers reject resume() on an already-running
          // context; state is re-checked before each playback below.
        }

        sessionPromiseRef.current = gemini.connectLive(speakerId, {
          onopen: () => {
            setIsLiveActive(true);
            setVoiceStatus('connected');
            const source = inputCtx.createMediaStreamSource(stream);
            // ScriptProcessor is deprecated (future migration: AudioWorklet
            // with a ScriptProcessor fallback), but it still works everywhere
            // today and keeps the volume meter + half-duplex gate logic simple.
            // It is connected to destination below because some browsers never
            // fire onaudioprocess otherwise (its output is silence).
            const scriptProcessor = inputCtx.createScriptProcessor(4096, 1, 1);
            // Stored so hangup/onclose/onerror can actually stop the stream
            // and disconnect these nodes — see teardownLiveAudio above.
            liveAudioNodesRef.current = { stream, source, scriptProcessor };
            // The REAL capture rate — browsers that ignored the 16000 hint
            // (Safari, many WebViews) typically run at 44100/48000 here.
            const captureRate = inputCtx.sampleRate;
            scriptProcessor.onaudioprocess = (e) => {
              const inputData = e.inputBuffer.getChannelData(0);
              let sum = 0;
              for (let i = 0; i < inputData.length; i++) sum += inputData[i] * inputData[i];
              setVolume(Math.sqrt(sum / inputData.length));
              // Half-duplex gate: while the assistant's reply is still playing
              // (nextStartTime marks the scheduled END of queued TTS audio),
              // plus a short tail for speaker-to-mic latency, do NOT stream mic
              // frames — otherwise the model hears and answers itself even
              // with echoCancellation on (speakerphones/low-end devices leak).
              //
              // CRITICAL: only gate when the output context is actually RUNNING
              // and some TTS has been scheduled (nextStartTime > 0). iOS Safari
              // routinely leaves the output context 'suspended', which FREEZES
              // out.currentTime at 0 — without these guards the gate would then
              // read "still playing" forever and mute the mic for the whole call
              // (the model never hears you: "connects but silent"). When the
              // context isn't running there is no TTS coming out anyway, so it
              // is safe to send the mic.
              const out = audioContextsRef.current.out;
              if (
                out && out.state === 'running' &&
                audioContextsRef.current.nextStartTime > 0 &&
                out.currentTime < audioContextsRef.current.nextStartTime + 0.4
              ) return;
              // The server expects 16 kHz mono PCM-16. If the context runs at
              // the hardware rate (hint ignored), downsample this frame first —
              // otherwise 48 kHz audio gets interpreted as 16 kHz and the
              // user's voice arrives ~3x slow/garbled at the ASR. Encode the
              // blob synchronously: the browser may recycle inputData before
              // the session promise resolves (resampleLinear always copies).
              const frame16k = resampleLinear(inputData, captureRate, 16000);
              const media = createBlob(frame16k);
              sessionPromiseRef.current?.then(s => s.sendRealtimeInput({ media }));
            };
            source.connect(scriptProcessor);
            scriptProcessor.connect(inputCtx.destination);
          },
          onmessage: async (msg: any) => {
            const base64 = msg.serverContent?.modelTurn?.parts[0]?.inlineData?.data;
            if (base64) {
              // iOS Safari can re-suspend the context (tab switch, route
              // change, interruption); scheduling on a suspended context is
              // silent and freezes currentTime, jamming the mic gate above.
              if (outputCtx.state === 'suspended') {
                try { await outputCtx.resume(); } catch { /* re-checked next chunk */ }
              }
              // 24000 here is the SERVER's PCM rate, not the context rate —
              // WebAudio resamples the buffer to outputCtx.sampleRate on play.
              const buffer = await decodeAudioData(decode(base64), outputCtx, 24000, 1);
              const source = outputCtx.createBufferSource();
              source.buffer = buffer;
              source.connect(outputCtx.destination);
              audioContextsRef.current.nextStartTime = Math.max(outputCtx.currentTime, audioContextsRef.current.nextStartTime);
              source.start(audioContextsRef.current.nextStartTime);
              audioContextsRef.current.nextStartTime += buffer.duration;

              // Server-side echo backstop: tell the backend the assistant is
              // (still) speaking so it drops any mic audio that leaks past
              // this client's own half-duplex gate above — e.g. the brief
              // scheduling race between a chunk starting to play and the
              // next onaudioprocess callback picking up the new
              // nextStartTime, or echoCancellation simply not being enough
              // on a laptop's built-in speakers. "false" is re-armed on
              // every chunk so it always fires after the LAST queued chunk
              // of this reply (+ the same 0.4s tail as the client gate),
              // not the first.
              sessionPromiseRef.current?.then(s => s.setAssistantSpeaking?.(true));
              if (assistantSpeakingOffTimerRef.current) clearTimeout(assistantSpeakingOffTimerRef.current);
              const offDelayMs = Math.max(0, (audioContextsRef.current.nextStartTime - outputCtx.currentTime + 0.4) * 1000);
              assistantSpeakingOffTimerRef.current = setTimeout(() => {
                sessionPromiseRef.current?.then(s => s.setAssistantSpeaking?.(false));
              }, offDelayMs);
            }
            if (msg.text) {
              setMessages(prev => [...prev, {
                // Date.now() alone can collide if two messages land in the
                // same millisecond (e.g. a fast user+assistant transcript
                // pair); crypto.randomUUID() (with the same _uuidv4
                // fallback localService.ts already uses for older WebViews)
                // guarantees a unique React key/message id.
                id: globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`,
                role: msg.isUser ? Role.user : Role.assistant,
                text: msg.text,
                timestamp: new Date(),
                normalized: msg.normalized,
                // localService.ts's connectLive() already renames this field
                // to camelCase (msg.toneMapped) before calling back here --
                // reading the old snake_case msg.tone_mapped meant the
                // tonal-melody trace was always empty for live-voice turns.
                toneMapped: msg.toneMapped,
                // Still added to `messages` (so unifiedExchange's history
                // param keeps real memory of the call for a later typed
                // follow-up), but flagged so the visible thread below never
                // renders it -- live voice should read as a real phone
                // call, not a chat log with a transcription window.
                fromLiveVoice: true,
              }]);
            }
          },
          onclose: () => {
            teardownLiveAudio();
            setIsLiveActive(false);
            setVoiceStatus('idle');
          },
          onerror: () => {
            teardownLiveAudio();
            setIsLiveActive(false);
            setVoiceStatus('error');
          }
        }, addresseeGender);

        // connectLive() can reject before the WebSocket is even constructed
        // (the ticket-fetch step, private/firewalled deployments only --
        // see its own comment) -- none of onopen/onclose/onerror above ever
        // get wired in that case, so nothing else recovers voiceStatus out
        // of 'connecting'. Uncaught here, that left the mic button
        // permanently stuck (worse now that the idempotency guard above
        // refuses to re-enter this branch while 'connecting'/
        // 'requesting_permission'), an unhandled promise rejection in the
        // console, and the already-acquired MediaStream never released
        // (mic-in-use indicator stays lit) since liveAudioNodesRef, which
        // teardownLiveAudio relies on, is only populated inside onopen.
        sessionPromiseRef.current.catch((err: any) => {
          console.error("Live voice connection failed:", err);
          stream.getTracks().forEach(t => t.stop());
          teardownLiveAudio();
          setIsLiveActive(false);
          setVoiceStatus('error');
          showToast(
            "An kasa haɗawa da murya kai-tsaye. A sake gwadawa.\n" +
            "(Could not start the live voice connection: " + (err?.message || 'unknown error') + ")"
          );
        });
    } catch (e: any) {
        const name = e?.name || '';
        console.error("Live voice mic error:", name, e);
        setVoiceStatus('error');
        setIsLiveActive(false);
        if (name === 'NotAllowedError' || name === 'SecurityError' || name === 'PermissionDeniedError') {
          showToast("Ba a ba da izinin makirufo ba. Da fatan za a ba da izini a saitunan browser sannan a sake gwadawa.\n(Microphone permission was denied — allow it in your browser and try again.)");
        } else if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
          showToast("Ba a sami makirufo ba a na'urarka.\n(No microphone was found on this device.)");
        } else if (name === 'NotReadableError' || name === 'TrackStartError') {
          showToast("Makirufo yana amfani da wata manhaja a yanzu. A rufe ta sannan a sake gwadawa.\n(The microphone is in use by another application.)");
        } else {
          showToast("An samu matsala wajen buɗe makirufo: " + (e?.message || name || 'unknown') + "\n(Could not start the microphone.)");
        }
    }
  };

  return { isLiveActive, volume, callDuration, voiceStatus, toggleLiveVoice };
}
