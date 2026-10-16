import type { ChartStats } from '../../hooks/useChartParser';
import { cn } from '../../lib/utils';
import { LedIndicator } from '../rack/LedIndicator';

export interface StatsCardProps {
  stats: ChartStats;
  className?: string;
}

/**
 * Hardware counter panel displaying audited chart statistics:
 * Total Notes, % HOPOs, Chords, Star Power phrases, Open Notes, and Sustains.
 */
export function StatsCard({ stats, className }: StatsCardProps) {
  const chordPct =
    stats.totalNotes > 0 ? ((stats.chordCount / stats.totalNotes) * 100).toFixed(1) : '0.0';

  return (
    <div
      className={cn(
        'flex flex-col justify-between gap-2.5 border border-hw-border bg-module p-3.5 shadow-bevel',
        className,
      )}
    >
      <div className="flex items-center justify-between border-b border-hw-border pb-1.5">
        <span className="silk-wide">A-04 // CHART AUDIT COUNTERS</span>
        <LedIndicator color="starpower" on={stats.starPowerCount > 0} size="xs" label="SP" />
      </div>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {/* Total Notes */}
        <div className="flex flex-col justify-between border border-hw-border bg-chassis px-2.5 py-2 shadow-recess">
          <span className="silk text-[8px]">TOTAL NOTES</span>
          <div className="mt-0.5 font-mono text-base font-bold tabular-nums leading-none tracking-silk text-silk">
            {String(stats.totalNotes).padStart(4, '0')}
          </div>
          <span className="silk-wide mt-1 tabular-nums text-[8px]">
            {stats.totalGems} GEMS TOTAL
          </span>
        </div>

        {/* % HOPOs */}
        <div className="flex flex-col justify-between border border-hw-border bg-chassis px-2.5 py-2 shadow-recess">
          <span className="silk text-[8px]">HOPO RATIO</span>
          <div className="mt-0.5 font-mono text-base font-bold tabular-nums leading-none tracking-silk text-fret-yellow">
            {stats.hopoPercentage.toFixed(1)}%
          </div>
          <span className="silk-wide mt-1 tabular-nums text-[8px]">
            {stats.hopoCount} TAP / HOPO
          </span>
        </div>

        {/* Chords */}
        <div className="flex flex-col justify-between border border-hw-border bg-chassis px-2.5 py-2 shadow-recess">
          <span className="silk text-[8px]">CHORDS</span>
          <div className="mt-0.5 font-mono text-base font-bold tabular-nums leading-none tracking-silk text-fret-blue">
            {String(stats.chordCount).padStart(3, '0')}
          </div>
          <span className="silk-wide mt-1 tabular-nums text-[8px]">
            {chordPct}% DYAD/TRIAD
          </span>
        </div>

        {/* Star Power */}
        <div className="flex flex-col justify-between border border-hw-border bg-chassis px-2.5 py-2 shadow-recess">
          <span className="silk text-[8px]">STAR POWER</span>
          <div className="mt-0.5 font-mono text-base font-bold tabular-nums leading-none tracking-silk text-starpower">
            {String(stats.starPowerCount).padStart(2, '0')} PHR
          </div>
          <span className="silk-wide mt-1 tabular-nums text-[8px]">
            {stats.sustainCount} SUS / {stats.openNoteCount} OPEN
          </span>
        </div>
      </div>

      <div className="flex items-center justify-between border-t border-hw-border pt-1.5 text-[8px]">
        <span className="silk-wide">TRACK: [EXPERTSINGLE]</span>
        <span className="font-mono uppercase tracking-silk text-silk-neutral">
          RELEASE MARGIN: 24 TICKS VERIFIED
        </span>
      </div>
    </div>
  );
}
