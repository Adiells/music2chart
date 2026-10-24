import type { ParsedChart } from '../../hooks/useChartParser';
import { getInstantTempoAtTime } from '../../hooks/useChartParser';
import { cn } from '../../lib/utils';
import { LedIndicator } from '../rack/LedIndicator';
import type { Language } from '../../lib/language';

export interface TempoDisplayProps {
  chart: ParsedChart;
  currentTime: number;
  isPlaying: boolean;
  className?: string;
  language?: Language;
}

/**
 * Digital studio sync readout displaying instantaneous BPM ([SyncTrack]),
 * Time Signature (meter), Measure:Beat position, 192 PPQ Tick, and Beat LED pulse array.
 */
export function TempoDisplay({
  chart,
  currentTime,
  isPlaying,
  className,
  language = 'en',
}: TempoDisplayProps) {
  const portuguese = language === 'pt-BR';
  const snap = getInstantTempoAtTime(currentTime, chart);
  const beatCount = Math.min(8, Math.max(1, snap.numerator));

  return (
    <div
      className={cn(
        'flex flex-col justify-between gap-2.5 border border-hw-border bg-module p-3.5 shadow-bevel',
        className,
      )}
    >
      <div className="flex items-center justify-between border-b border-hw-border pb-1.5">
        <span className="silk-wide">
          {portuguese ? 'A-02 // RELÓGIO SYNCTRACK' : 'A-02 // SYNCTRACK CLOCK'}
        </span>
        <span className="silk-wide tabular-nums text-[9px]">{chart.resolution} PPQ</span>
      </div>

      <div className="grid grid-cols-3 gap-2">
        {/* Instantaneous BPM Digital Readout */}
        <div className="flex flex-col justify-between border border-hw-border bg-chassis px-2.5 py-2 shadow-recess">
          <span className="silk text-[8px]">{portuguese ? 'BPM INSTANTÂNEO' : 'INSTANT BPM'}</span>
          <div className="mt-0.5 font-mono text-lg font-bold tabular-nums leading-none tracking-silk text-fret-green">
            {snap.bpm.toFixed(1)}
          </div>
          <span className="silk-wide mt-1 text-[8px]">
            {chart.bpmChanges.length > 1
              ? (portuguese ? `VARIÁVEL (${chart.bpmChanges.length} PTS)` : `VAR (${chart.bpmChanges.length} PTS)`)
              : (portuguese ? 'GRADE FIXA' : 'FIXED GRID')}
          </span>
        </div>

        {/* Time Signature / Meter Readout */}
        <div className="flex flex-col justify-between border border-hw-border bg-chassis px-2.5 py-2 shadow-recess">
          <span className="silk text-[8px]">{portuguese ? 'COMPASSO' : 'METER / TS'}</span>
          <div className="mt-0.5 font-mono text-lg font-bold tabular-nums leading-none tracking-silk text-silk">
            {snap.numerator}/{snap.denominator}
          </div>
          <span className="silk-wide mt-1 text-[8px]">
            {portuguese ? 'FÓRMULA DE COMPASSO' : 'TIME SIGNATURE'}
          </span>
        </div>

        {/* Measure : Beat & Tick Readout */}
        <div className="flex flex-col justify-between border border-hw-border bg-chassis px-2.5 py-2 shadow-recess">
          <span className="silk text-[8px]">{portuguese ? 'COMP : TEMPO' : 'BAR : BEAT'}</span>
          <div className="mt-0.5 font-mono text-base font-bold tabular-nums leading-none tracking-silk text-fret-yellow">
            {String(snap.measure).padStart(3, '0')}:{snap.beat}
          </div>
          <span className="silk-wide mt-1 tabular-nums text-[8px]">
            T {String(snap.tick).padStart(6, '0')}
          </span>
        </div>
      </div>

      {/* Hardware Metronome Beat LED Strip */}
      <div className="flex items-center justify-between border-t border-hw-border pt-2">
        <span className="silk-wide text-[8px]">{portuguese ? 'PULSO DE TEMPO' : 'BEAT PULSE'}</span>
        <div className="flex items-center gap-2.5">
          {Array.from({ length: beatCount }, (_, idx) => {
            const beatNum = idx + 1;
            const active = isPlaying && snap.beat === beatNum;
            return (
              <LedIndicator
                key={beatNum}
                color={beatNum === 1 ? 'green' : 'yellow'}
                on={active}
                size="xs"
                label={`B${beatNum}`}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
}
