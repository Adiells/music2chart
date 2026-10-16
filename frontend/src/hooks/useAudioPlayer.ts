import { useCallback, useEffect, useRef, useState } from 'react';
import { getApiUrl } from '../lib/api';
import { clamp } from '../lib/utils';

export type PlaybackSpeed = 0.5 | 0.75 | 1.0;

export interface AudioPlayerOptions {
  /** Completed backend task UUID; streams from `/api/v1/chart/preview/{task_id}/audio`. */
  taskId: string | null;
  /** Optional local uploaded file used as fallback or pre-generation preview. */
  localFile?: File | null;
  /** Fallback duration in seconds when operating in synthetic demo mode. */
  fallbackDuration?: number;
}

export interface AudioPlayerController {
  isPlaying: boolean;
  isLoaded: boolean;
  currentTime: number;
  duration: number;
  playbackRate: PlaybackSpeed;
  waveformPeaks: readonly number[];
  audioSourceLabel: string;
  play: () => Promise<void>;
  pause: () => void;
  togglePlay: () => void;
  stop: () => void;
  seek: (timeSeconds: number) => void;
  setPlaybackRate: (rate: PlaybackSpeed) => void;
  /** High-precision synchronous time accessor for the Three.js 60/120Hz render loop. */
  getCurrentTime: () => number;
}

const DEFAULT_PEAK_BINS = 180;

/**
 * Generate a deterministic, musically structured PCM WAV blob in memory so the
 * HTML5 Audio element and Web Audio pipeline work identically during synthetic
 * bench tests or when no external backend stream is mounted.
 */
function buildSyntheticTrackWavBlob(durationSeconds = 32, sampleRate = 22050): {
  blob: Blob;
  peaks: number[];
} {
  const numSamples = Math.max(1, Math.floor(durationSeconds * sampleRate));
  const buffer = new ArrayBuffer(44 + numSamples * 2);
  const view = new DataView(buffer);

  const writeStr = (offset: number, str: string): void => {
    for (let i = 0; i < str.length; i += 1) {
      view.setUint8(offset + i, str.charCodeAt(i));
    }
  };

  writeStr(0, 'RIFF');
  view.setUint32(4, 36 + numSamples * 2, true);
  writeStr(8, 'WAVE');
  writeStr(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // Mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeStr(36, 'data');
  view.setUint32(40, numSamples * 2, true);

  // Riff pitch sequence (E2, G2, A2, B2, D3, E3) at 128 BPM (beat = 0.46875s, 1/8 = 0.234375s)
  const eighthSec = 60 / 128 / 2;
  const freqs = [82.41, 98.0, 110.0, 123.47, 146.83, 164.81, 196.0, 220.0];
  const peaks = new Array<number>(DEFAULT_PEAK_BINS).fill(0.12);
  const samplesPerBin = Math.max(1, Math.floor(numSamples / DEFAULT_PEAK_BINS));

  for (let i = 0; i < numSamples; i += 1) {
    const t = i / sampleRate;
    const step = Math.floor(t / eighthSec);
    const stepPhase = (t % eighthSec) / eighthSec;
    const f = freqs[(step * 3 + Math.floor(step / 4)) % freqs.length];

    // Section envelope (Intro, Verse, Chorus, Solo)
    const sectionBoost = t > 15 && t < 26 ? 1.0 : t < 4 ? 0.55 : 0.8;
    const env = Math.exp(-stepPhase * 4.2) * sectionBoost;

    // Plucked electric guitar harmonic synthesis + soft overdrive
    const raw =
      0.6 * Math.sin(2 * Math.PI * f * t) +
      0.3 * Math.sin(2 * Math.PI * f * 2 * t) +
      0.15 * Math.sin(2 * Math.PI * f * 3 * t);
    const driven = Math.tanh(raw * 2.2) * env * 0.38;

    const pcm = clamp(Math.round(driven * 32767), -32768, 32767);
    view.setInt16(44 + i * 2, pcm, true);

    const binIdx = Math.min(DEFAULT_PEAK_BINS - 1, Math.floor(i / samplesPerBin));
    const amp = Math.min(1, Math.abs(driven) * 2.3);
    if (amp > peaks[binIdx]) peaks[binIdx] = amp;
  }

  return {
    blob: new Blob([buffer], { type: 'audio/wav' }),
    peaks,
  };
}

/**
 * Compute normalized waveform peaks from an ArrayBuffer via Web Audio API.
 */
async function extractPeaksFromArrayBuffer(
  arrayBuffer: ArrayBuffer,
  bins = DEFAULT_PEAK_BINS,
): Promise<number[] | null> {
  if (typeof window === 'undefined') return null;
  const Ctor =
    window.AudioContext ??
    (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!Ctor) return null;

  const ctx = new Ctor();
  try {
    const audioBuffer = await ctx.decodeAudioData(arrayBuffer.slice(0));
    const channel = audioBuffer.getChannelData(0);
    const blockSize = Math.max(1, Math.floor(channel.length / bins));
    const peaks: number[] = [];
    let maxPeak = 0.01;

    for (let i = 0; i < bins; i += 1) {
      const start = i * blockSize;
      const end = Math.min(channel.length, start + blockSize);
      let sum = 0;
      let peak = 0;
      for (let j = start; j < end; j += 1) {
        const abs = Math.abs(channel[j]);
        sum += abs;
        if (abs > peak) peak = abs;
      }
      const combined = peak * 0.65 + (sum / Math.max(1, end - start)) * 0.35;
      peaks.push(combined);
      if (combined > maxPeak) maxPeak = combined;
    }

    return peaks.map((p) => clamp(p / maxPeak, 0.06, 1.0));
  } catch {
    return null;
  } finally {
    void ctx.close().catch(() => undefined);
  }
}

/**
 * High-precision audio playback hook supporting `/api/v1/chart/preview/{task_id}/audio`,
 * local file blobs, and a synthesized test track fallback. Provides 0.5x, 0.75x, and 1.0x
 * pitch-preserved playback speeds and synchronous time access for Three.js rendering.
 */
export function useAudioPlayer({
  taskId,
  localFile = null,
  fallbackDuration = 32,
}: AudioPlayerOptions): AudioPlayerController {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const rafRef = useRef<number | null>(null);

  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(fallbackDuration);
  const [playbackRate, setPlaybackRateState] = useState<PlaybackSpeed>(1.0);
  const [waveformPeaks, setWaveformPeaks] = useState<readonly number[]>(() =>
    buildSyntheticTrackWavBlob(fallbackDuration).peaks,
  );
  const [audioSourceLabel, setAudioSourceLabel] = useState<string>('SYNTH BENCH STREAM');

  // Instantiate persistent HTMLAudioElement once
  useEffect(() => {
    const audio = new Audio();
    audio.preload = 'auto';
    audio.crossOrigin = 'anonymous';
    audio.preservesPitch = true;
    audioRef.current = audio;

    const onLoadedMetadata = (): void => {
      if (Number.isFinite(audio.duration) && audio.duration > 0) {
        setDuration(audio.duration);
      }
      setIsLoaded(true);
    };

    const onPlay = (): void => setIsPlaying(true);
    const onPause = (): void => setIsPlaying(false);
    const onEnded = (): void => {
      setIsPlaying(false);
      setCurrentTime(0);
      audio.currentTime = 0;
    };
    const onTimeUpdate = (): void => {
      setCurrentTime(audio.currentTime);
    };

    audio.addEventListener('loadedmetadata', onLoadedMetadata);
    audio.addEventListener('play', onPlay);
    audio.addEventListener('pause', onPause);
    audio.addEventListener('ended', onEnded);
    audio.addEventListener('timeupdate', onTimeUpdate);

    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
      audio.pause();
      audio.removeEventListener('loadedmetadata', onLoadedMetadata);
      audio.removeEventListener('play', onPlay);
      audio.removeEventListener('pause', onPause);
      audio.removeEventListener('ended', onEnded);
      audio.removeEventListener('timeupdate', onTimeUpdate);
      audioRef.current = null;
    };
  }, []);

  // Load audio stream from `/api/v1/chart/preview/{task_id}/audio`, local file, or synth fallback
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return undefined;

    let cancelled = false;
    let objectUrlToRevoke: string | null = null;

    audio.pause();
    audio.currentTime = 0;
    setCurrentTime(0);
    setIsPlaying(false);
    setIsLoaded(false);

    const mountSynthFallback = (dur: number): void => {
      if (cancelled) return;
      const synth = buildSyntheticTrackWavBlob(dur);
      objectUrlToRevoke = URL.createObjectURL(synth.blob);
      audio.src = objectUrlToRevoke;
      audio.playbackRate = playbackRate;
      audio.load();
      setWaveformPeaks(synth.peaks);
      setDuration(dur);
      setAudioSourceLabel('SYNTH TEST STREAM (22.05 KHZ)');
    };

    const loadAudioSource = async (): Promise<void> => {
      // 1. Completed backend task -> stream `/api/v1/chart/preview/{task_id}/audio`
      if (taskId && !taskId.startsWith('demo-')) {
        const previewUrl = getApiUrl(`/api/v1/chart/preview/${encodeURIComponent(taskId)}/audio`);
        try {
          const response = await fetch(previewUrl);
          if (response.ok && !cancelled) {
            const arrayBuf = await response.arrayBuffer();
            if (cancelled) return;
            const blob = new Blob([arrayBuf], {
              type: response.headers.get('content-type') || 'audio/ogg',
            });
            objectUrlToRevoke = URL.createObjectURL(blob);
            audio.src = objectUrlToRevoke;
            audio.playbackRate = playbackRate;
            audio.load();
            setAudioSourceLabel(`PREVIEW STREAM // ${taskId.slice(0, 8).toUpperCase()}`);

            const decodedPeaks = await extractPeaksFromArrayBuffer(arrayBuf);
            if (!cancelled && decodedPeaks) {
              setWaveformPeaks(decodedPeaks);
            }
            return;
          }
        } catch {
          // Fall through to local file or synth fallback
        }
      }

      // 2. Local uploaded file -> preview directly via ObjectURL + decode waveform
      if (localFile && !cancelled) {
        try {
          const arrayBuf = await localFile.arrayBuffer();
          if (cancelled) return;
          objectUrlToRevoke = URL.createObjectURL(localFile);
          audio.src = objectUrlToRevoke;
          audio.playbackRate = playbackRate;
          audio.load();
          setAudioSourceLabel(`LOCAL MASTER // ${localFile.name.toUpperCase()}`);

          const decodedPeaks = await extractPeaksFromArrayBuffer(arrayBuf);
          if (!cancelled && decodedPeaks) {
            setWaveformPeaks(decodedPeaks);
          }
          return;
        } catch {
          // Fall through to synth fallback
        }
      }

      // 3. Synthetic demo audio stream
      mountSynthFallback(fallbackDuration);
    };

    void loadAudioSource();

    return () => {
      cancelled = true;
      if (objectUrlToRevoke) {
        URL.revokeObjectURL(objectUrlToRevoke);
      }
    };
    // Intentionally re-run only when taskId, localFile, or fallbackDuration changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskId, localFile, fallbackDuration]);

  // High-frequency playhead update loop while playing
  useEffect(() => {
    if (!isPlaying) {
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
      return undefined;
    }

    const tick = (): void => {
      const audio = audioRef.current;
      if (audio) {
        setCurrentTime(audio.currentTime);
      }
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);

    return () => {
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
    };
  }, [isPlaying]);

  const play = useCallback(async (): Promise<void> => {
    const audio = audioRef.current;
    if (!audio) return;
    try {
      audio.playbackRate = playbackRate;
      await audio.play();
    } catch {
      setIsPlaying(false);
    }
  }, [playbackRate]);

  const pause = useCallback((): void => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.pause();
  }, []);

  const togglePlay = useCallback((): void => {
    const audio = audioRef.current;
    if (!audio) return;
    if (audio.paused) {
      void play();
    } else {
      pause();
    }
  }, [play, pause]);

  const stop = useCallback((): void => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.pause();
    audio.currentTime = 0;
    setCurrentTime(0);
  }, []);

  const seek = useCallback(
    (timeSeconds: number): void => {
      const audio = audioRef.current;
      const target = clamp(timeSeconds, 0, Math.max(0.1, duration));
      if (audio) {
        audio.currentTime = target;
      }
      setCurrentTime(target);
    },
    [duration],
  );

  const setPlaybackRate = useCallback((rate: PlaybackSpeed): void => {
    setPlaybackRateState(rate);
    const audio = audioRef.current;
    if (audio) {
      audio.preservesPitch = true;
      audio.playbackRate = rate;
    }
  }, []);

  const getCurrentTime = useCallback((): number => {
    return audioRef.current ? audioRef.current.currentTime : currentTime;
  }, [currentTime]);

  return {
    isPlaying,
    isLoaded,
    currentTime,
    duration,
    playbackRate,
    waveformPeaks,
    audioSourceLabel,
    play,
    pause,
    togglePlay,
    stop,
    seek,
    setPlaybackRate,
    getCurrentTime,
  };
}
