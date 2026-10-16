import type { ReactNode } from 'react';
import { cn } from '../../lib/utils';
import { LedIndicator } from './LedIndicator';
import { Screw } from './Screw';

export interface RackChassisProps {
  /** Brand mark silk-screened on the faceplate. */
  brand?: string;
  /** Model designation shown next to the brand. */
  model?: string;
  /** Serial / firmware stamp shown on the right of the header. */
  serial?: string;
  /** Power LED state. */
  powered?: boolean;
  /** Extra hardware for the header's right side (status LEDs, links). */
  headerRight?: ReactNode;
  /** Optional custom footer content; defaults to the industrial chassis telemetry bar. */
  footer?: ReactNode;
  className?: string;
  children: ReactNode;
}

function RackEar({ side }: { side: 'left' | 'right' }) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        'hidden w-8 shrink-0 flex-col items-center justify-between bg-panel py-3 sm:flex',
        side === 'left' ? 'border-r border-hw-border' : 'border-l border-hw-border',
      )}
    >
      <Screw size={13} angle={side === 'left' ? 22 : 58} />
      <div className="texture-vent my-4 w-3 flex-1 border border-hw-border bg-chassis" />
      <Screw size={13} angle={side === 'left' ? 71 : 9} />
    </div>
  );
}

/**
 * 19-inch style rack chassis: anodised outer frame, vented rack ears with mounting
 * screws and a silk-screened faceplate header. Children are the rack's modules.
 */
export function RackChassis({
  brand = 'MUSIC2CHART',
  model = 'M2C-01 / CHART SYNTHESIS WORKSTATION',
  serial = 'SN 0000-0001',
  powered = true,
  headerRight,
  footer,
  className,
  children,
}: RackChassisProps) {
  return (
    <div className={cn('min-h-screen bg-chassis p-3 md:p-6', className)}>
      <div className="flex border border-hw-border bg-panel shadow-lift">
        <RackEar side="left" />

        <div className="texture-brushed flex min-w-0 flex-1 flex-col">
          <header className="flex flex-wrap items-center justify-between gap-4 border-b border-hw-border px-5 py-3">
            <div className="flex items-baseline gap-4">
              <span className="font-grotesk text-lg font-bold uppercase tracking-silk-wide text-silk">{brand}</span>
              <span className="silk hidden md:inline">{model}</span>
            </div>
            <div className="flex items-center gap-5">
              {headerRight}
              <span className="silk-wide hidden xl:inline tabular-nums">{serial}</span>
              <LedIndicator color="green" on={powered} size="sm" label="PWR" />
            </div>
          </header>

          <div className="flex-1 p-3 md:p-4">{children}</div>

          <footer className="border-t border-hw-border bg-panel px-5 py-3">
            {footer ?? (
              <div className="flex flex-wrap items-center justify-between gap-4 font-mono text-[9px] uppercase tracking-silk text-silk-dim">
                <div className="flex items-center gap-3">
                  <span className="font-semibold text-silk">MUSIC2CHART // DUAL-CHASSIS WORKSTATION</span>
                  <span className="hidden sm:inline text-hw-screw">|</span>
                  <span className="hidden sm:inline text-silk-neutral">STANDARDS: CLONE HERO 192 PPQ • SONGBINARY V1 (.SNG)</span>
                </div>
                <div className="hidden lg:flex items-center gap-3 text-silk-neutral">
                  <span>CLOCK: 192 PPQ SYNC LOCKED</span>
                  <span className="text-hw-screw">•</span>
                  <span>LATENCY: 0 MS BUFFER</span>
                  <span className="text-hw-screw">•</span>
                  <span className="text-fret-green">DSP ENGINE ACTIVE</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="tabular-nums">FW 1.0.0 • REV 2026-1016</span>
                  <span className="text-hw-screw">|</span>
                  <LedIndicator color="green" on size="xs" label="ONLINE" />
                </div>
              </div>
            )}
          </footer>
        </div>

        <RackEar side="right" />
      </div>
    </div>
  );
}
