import type { MouseEvent } from 'react';
import type { NpsBucket } from '../../hooks/useChartParser';
import { clamp, cn } from '../../lib/utils';

export interface NpsGraphProps {
  buckets: readonly NpsBucket[];
  peakNps: number;
  avgNps: number;
  currentTime: number;
  duration: number;
  onSeek?: (timeSeconds: number) => void;
  className?: string;
}

function npsColorHex(nps: number): string {
  if (nps >= 10) return '#FF1744';
  if (nps >= 6.5) return '#FF9100';
  if (nps >= 3.5) return '#FFEA00';
  return '#00E676';
}

/**
 * Notes-Per-Second (NPS) density histogram across the song timeline.
 * Highlights high-density solo passages, displays Instant / Avg / Peak NPS,
 * and tracks the active audio playhead.
 */
export function NpsGraph({
  buckets,
  peakNps,
  avgNps,
  currentTime,
  duration,
  onSeek,
  className,
}: NpsGraphProps) {
  const safeDuration = Math.max(0.1, duration);
  const progressRatio = clamp(currentTime / safeDuration, 0, 1);
  const maxScale = Math.max(8, Math.ceil(peakNps * 1.15));

  const activeBucket =
    buckets.find((b) => currentTime >= b.startTime && currentTime < b.endTime) ??
    buckets[0] ??
    null;
  const currentNps = activeBucket ? activeBucket.nps : 0;

  const handleClick = (e: MouseEvent<HTMLDivElement>): void => {
    if (!onSeek) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const ratio = clamp((e.clientX - rect.left) / Math.max(1, rect.width), 0, 1);
    onSeek(ratio * safeDuration);
  };

  return (
    <div
      className={cn(
        'flex flex-col justify-between gap-2.5 border border-hw-border bg-module p-3.5 shadow-bevel',
        className,
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-hw-border pb-1.5">
        <span className="silk-wide">A-03 // NPS DENSITY TELEMETRY</span>
        <div className="flex items-center gap-3 font-mono text-[10px] tabular-nums uppercase tracking-silk">
          <span>
            <span className="text-silk-dim">NOW: </span>
            <span className="font-semibold text-silk">{currentNps.toFixed(1)} NPS</span>
          </span>
          <span className="text-hw-screw">|</span>
          <span>
            <span className="text-silk-dim">AVG: </span>
            <span className="text-fret-green">{avgNps.toFixed(1)}</span>
          </span>
          <span className="text-hw-screw">|</span>
          <span>
            <span className="text-silk-dim">PEAK: </span>
            <span className="text-fret-orange">{peakNps.toFixed(1)}</span>
          </span>
        </div>
      </div>

      {/* Density Graph Viewport */}
      <div
        role={onSeek ? 'button' : undefined}
        tabIndex={onSeek ? 0 : undefined}
        aria-label="NPS Density Timeline Graph"
        onClick={handleClick}
        onKeyDown={(e) => {
          if (!onSeek) return;
          if (e.key === 'ArrowRight') {
            e.preventDefault();
            onSeek(currentTime + 1);
          } else if (e.key === 'ArrowLeft') {
            e.preventDefault();
            onSeek(currentTime - 1);
          }
        }}
        className={cn(
          'relative h-24 w-full overflow-hidden border border-hw-border bg-chassis p-1 shadow-recess',
          onSeek && 'cursor-pointer',
        )}
      >
        <svg
          viewBox={`0 0 ${Math.max(1, buckets.length) * 6} 100`}
          preserveAspectRatio="none"
          className="h-full w-full"
          aria-hidden="true"
        >
          {/* Horizontal reference grid lines (25%, 50%, 75%) */}
          <line x1="0" y1="25" x2={buckets.length * 6} y2="25" stroke="#1B1F28" strokeWidth="1" />
          <line x1="0" y1="50" x2={buckets.length * 6} y2="50" stroke="#1B1F28" strokeWidth="1" />
          <line x1="0" y1="75" x2={buckets.length * 6} y2="75" stroke="#1B1F28" strokeWidth="1" />

          {buckets.map((b, i) => {
            const h = b.nps <= 0 ? 2 : Math.max(6, Math.round((b.nps / maxScale) * 92));
            const y = 98 - h;
            const isPast = b.endTime <= currentTime;
            return (
              <rect
                key={b.index}
                x={i * 6 + 0.8}
                y={y}
                width={4.4}
                height={h}
                fill={npsColorHex(b.nps)}
                opacity={isPast ? 0.92 : 0.45}
              />
            );
          })}
        </svg>

        {/* Playhead Line */}
        <div
          className="pointer-events-none absolute inset-y-0 w-[1.5px] bg-silk"
          style={{ left: `${progressRatio * 100}%` }}
        />
      </div>

      {/* Legend */}
      <div className="flex items-center justify-between text-[8px]">
        <span className="silk-wide">WINDOW: 1.0S INTEGRATOR</span>
        <div className="flex items-center gap-3 font-mono uppercase tracking-silk text-silk-dim">
          <span className="text-fret-green">&lt;3.5 GROOVE</span>
          <span className="text-fret-yellow">3.5-6.5 RIFF</span>
          <span className="text-fret-orange">6.5-10 RUN</span>
          <span className="text-fret-red">&gt;10 SHRED</span>
        </div>
      </div>
    </div>
  );
}
