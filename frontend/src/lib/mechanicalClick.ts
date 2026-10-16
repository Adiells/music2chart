/**
 * Synthesised mechanical click for tactile controls.
 *
 * Generates a ~12 ms band-passed noise transient through the Web Audio API.
 * The AudioContext is created lazily on the first user gesture (autoplay-policy safe)
 * and reused as a singleton. Any audio failure is swallowed: the click is cosmetic.
 */

interface WindowWithWebkitAudio extends Window {
  webkitAudioContext?: typeof AudioContext;
}

let sharedContext: AudioContext | null = null;

function getContext(): AudioContext | null {
  if (typeof window === 'undefined') return null;
  if (sharedContext) return sharedContext;
  const Ctor = window.AudioContext ?? (window as WindowWithWebkitAudio).webkitAudioContext;
  if (!Ctor) return null;
  sharedContext = new Ctor();
  return sharedContext;
}

/**
 * Play a short mechanical click.
 *
 * @param tone - Centre frequency of the transient in Hz (higher = smaller switch).
 * @param level - Output gain in [0, 1].
 */
export function playMechanicalClick(tone = 3200, level = 0.22): void {
  try {
    const ctx = getContext();
    if (!ctx) return;
    if (ctx.state === 'suspended') void ctx.resume();

    const length = Math.max(1, Math.floor(ctx.sampleRate * 0.012));
    const buffer = ctx.createBuffer(1, length, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < length; i += 1) {
      const decay = (1 - i / length) ** 6;
      data[i] = (Math.random() * 2 - 1) * decay;
    }

    const source = ctx.createBufferSource();
    source.buffer = buffer;
    const band = ctx.createBiquadFilter();
    band.type = 'bandpass';
    band.frequency.value = tone;
    band.Q.value = 1.4;
    const gain = ctx.createGain();
    gain.gain.value = level;

    source.connect(band).connect(gain).connect(ctx.destination);
    source.start();
  } catch {
    // Audio is optional feedback; never let it break an interaction.
  }
}
