import { useRef, useState } from 'react';
import type { PointerEvent } from 'react';
import type { ParsedSection, ParsedStarPower } from '../../hooks/useChartParser';
import { clamp, cn } from '../../lib/utils';

export interface WaveformBarProps {
  peaks: readonly number[];
  currentTime: number;
  duration: number;
  sections: readonly ParsedSection[];
  starPower?: readonly ParsedStarPower[];
  audioSourceLabel?: string;
  onSeek: (timeSeconds: number) => void;
  className?: string;
}

function formatTimecode(sec: number): string {
  const safe = Math.max(0, sec);
  const mins = Math.floor(safe / 60);
  const rem = safe - mins * 60;
  const secs = Math.floor(rem);
  const ms = Math.floor((rem - secs) * 100);
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}.${String(ms).padStart(2, '0')}`;
}

/**
 * Navigable studio waveform bar with [Events] section markers (Intro, Verse, Chorus, Solo),
 * Star Power phrase highlights, and pointer drag scrubbing playhead.
 */
export function WaveformBar({
  peaks,
  currentTime,
  duration,
  sections,
  starPower = [],
  audioSourceLabel = 'MASTER STREAM',
  onSeek,
  className,
}: WaveformBarProps) {
  const trackRef = useRef<HTMLDivElement>(null);
  const [scrubbing, setScrubbing] = useState(false);

  const safeDuration = Math.max(0.1, duration);
  const progressRatio = clamp(currentTime / safeDuration, 0, 1);

  const clientXToTime = (clientX: number): number => {
    const el = trackRef.current;
    if (!el) return 0;
    const rect = el.getBoundingClientRect();
    const ratio = clamp((clientX - rect.left) / Math.max(1, rect.width), 0, 1);
    return ratio * safeDuration;
  };

  const handlePointerDown = (e: PointerEvent<HTMLDivElement>): void => {
    if (e.button !== 0) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    setScrubbing(true);
    onSeek(clientXToTime(e.clientX));
  };

  const handlePointerMove = (e: PointerEvent<HTMLDivElement>): void => {
    if (!scrubbing) return;
    onSeek(clientXToTime(e.clientX));
  };

  const handlePointerUp = (e: PointerEvent<HTMLDivElement>): void => {
    if (!scrubbing) return;
    setScrubbing(false);
    if (e.currentTarget.hasPointerCapture(e.pointerId)) {
      e.currentTarget.releasePointerCapture(e.pointerId);
    }
  };

  return (
    <div className={cn('flex flex-col gap-2 border border-hw-border bg-module p-3.5 shadow-bevel', className)}>
      {/* Header & Section Jump Buttons */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <span className="silk-wide">A-01 // WAVEFORM &amp; SECTION NAVIGATOR</span>
          <span className="h-3 w-px bg-hw-border" aria-hidden="true" />
          <span className="silk-wide text-[9px] text-silk-neutral">{audioSourceLabel}</span>
        </div>

        <div className="font-mono text-xs font-semibold tabular-nums tracking-silk text-silk">
          {formatTimecode(currentTime)} <span className="text-silk-dim">/ {formatTimecode(safeDuration)}</span>
        </div>
      </div>

      {/* Section Marker Pills from [Events] */}
      <div className="flex items-center gap-1.5 overflow-x-auto py-0.5 no-scrollbar" role="navigation" aria-label="Chart Sections">
        {sections.map((sec, idx) => {
          const nextSec = sections[idx + 1];
          const isCurrent =
            currentTime + 0.05 >= sec.timeSeconds &&
            (!nextSec || currentTime + 0.05 < nextSec.timeSeconds);
          return (
            <button
              key={`${sec.tick}-${sec.name}`}
              type="button"
              onClick={() => onSeek(sec.timeSeconds)}
              className={cn(
                'shrink-0 whitespace-nowrap border px-2 py-0.5 font-mono text-[9px] uppercase tracking-silk transition-colors',
                isCurrent
                  ? 'border-fret-green bg-[#102019] text-fret-green'
                  : 'border-hw-border bg-chassis text-silk-neutral hover:border-hw-screw hover:text-silk',
              )}
            >
              {sec.name} <span className="text-silk-dim">({formatTimecode(sec.timeSeconds).slice(0, 5)})</span>
            </button>
          );
        })}
      </div>

      {/* Interactive Scrubbing Waveform Track */}
      <div
        ref={trackRef}
        role="slider"
        tabIndex={0}
        aria-label="Audio Waveform Timeline Scrubber"
        aria-valuemin={0}
        aria-valuemax={Math.round(safeDuration)}
        aria-valuenow={Math.round(currentTime)}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        onKeyDown={(e) => {
          if (e.key === 'ArrowRight') {
            e.preventDefault();
            onSeek(currentTime + 1);
          } else if (e.key === 'ArrowLeft') {
            e.preventDefault();
            onSeek(currentTime - 1);
          }
        }}
        className={cn(
          'no-select relative h-20 w-full touch-none overflow-hidden border border-hw-border bg-chassis shadow-recess',
          scrubbing ? 'cursor-grabbing' : 'cursor-pointer',
        )}
      >
        {/* Star Power phrase background regions */}
        {starPower.map((sp) => {
          const leftPct = clamp((sp.startTimeSeconds / safeDuration) * 100, 0, 100);
          const widthPct = clamp(
            ((sp.endTimeSeconds - sp.startTimeSeconds) / safeDuration) * 100,
            0.5,
            100 - leftPct,
          );
          return (
            <div
              key={`sp-${sp.tick}`}
              className="pointer-events-none absolute inset-y-0 border-x border-starpower/30 bg-starpower/10"
              style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
              title="Star Power Phrase (S 2)"
            />
          );
        })}

        {/* Vertical Section Division Lines inside Waveform */}
        {sections.map((sec) => {
          const leftPct = clamp((sec.timeSeconds / safeDuration) * 100, 0, 99.5);
          return (
            <div
              key={`line-${sec.tick}-${sec.name}`}
              className="pointer-events-none absolute inset-y-0 border-l border-hw-screw/70"
              style={{ left: `${leftPct}%` }}
            >
              <span className="bg-panel/90 px-1 font-mono text-[8px] uppercase tracking-silk text-silk-neutral">
                {sec.name}
              </span>
            </div>
          );
        })}

        {/* Symmetric Mirrored Waveform SVG */}
        <svg
          viewBox={`0 0 ${peaks.length * 3} 100`}
          preserveAspectRatio="none"
          className="pointer-events-none absolute inset-0 h-full w-full"
          aria-hidden="true"
        >
          <line x1="0" y1="50" x2={peaks.length * 3} y2="50" stroke="#222631" strokeWidth="1" />
          {peaks.map((amp, i) => {
            const barRatio = i / Math.max(1, peaks.length - 1);
            const passed = barRatio <= progressRatio;
            const h = Math.max(4, Math.round(amp * 82));
            const y = 50 - h / 2;
            return (
              <rect
                key={i}
                x={i * 3 + 0.5}
                y={y}
                width={1.9}
                height={h}
                fill={passed ? '#00E676' : '#434958'}
                opacity={passed ? 0.92 : 0.65}
              />
            );
          })}
        </svg>

        {/* High-Contrast Playhead Cursor */}
        <div
          className="pointer-events-none absolute inset-y-0 w-[2px] bg-fret-orange"
          style={{ left: `${progressRatio * 100}%` }}
        >
          <span className="absolute -left-[4px] top-0 h-2 w-2.5 bg-fret-orange" />
          <span className="absolute -left-[4px] bottom-0 h-2 w-2.5 bg-fret-orange" />
        </div>
      </div>
    </div>
  );
}
