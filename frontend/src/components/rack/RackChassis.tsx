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
  /** Callback triggered when user clicks the server compute / sponsor button. */
  onOpenSupport?: () => void;
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
  onOpenSupport,
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
            <div className="flex items-center gap-3 sm:gap-5">
              {headerRight}
              <a
                href="https://github.com/Adiells/music2chart"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 border border-hw-border bg-module px-2 py-1 font-mono text-[9px] font-semibold uppercase tracking-silk text-silk hover:border-silk hover:bg-panel transition-colors"
                title="View Music2Chart on GitHub"
              >
                <svg className="h-3.5 w-3.5 fill-current" viewBox="0 0 24 24" aria-hidden="true">
                  <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
                </svg>
                <span className="hidden sm:inline">GitHub</span>
              </a>
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
                  <a
                    href="https://github.com/Adiells/music2chart"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-silk transition-colors"
                  >
                    GITHUB: Adiells/music2chart
                  </a>
                  <span className="hidden sm:inline text-hw-screw">|</span>
                  <span className="text-silk-neutral">MIT LICENSE</span>
                </div>
                <div className="hidden lg:flex items-center gap-3 text-silk-neutral">
                  <span>CLOCK: 192 PPQ SYNC LOCKED</span>
                  <span className="text-hw-screw">•</span>
                  <span>LATENCY: 0 MS BUFFER</span>
                  <span className="text-hw-screw">•</span>
                  <span className="text-fret-green">DSP ENGINE ACTIVE</span>
                </div>
                <div className="flex items-center gap-3">
                  {onOpenSupport ? (
                    <button
                      type="button"
                      onClick={onOpenSupport}
                      className="flex items-center gap-1.5 border border-hw-border bg-module px-2 py-0.5 font-mono text-[9px] font-semibold tracking-silk text-fret-yellow hover:border-fret-yellow hover:bg-panel transition-colors"
                    >
                      <LedIndicator color="orange" on size="xs" blink="slow" />
                      <span>⚡ SERVER COMPUTE / SPONSOR</span>
                    </button>
                  ) : null}
                  <span className="tabular-nums hidden sm:inline">FW 1.0.0 • REV 2026-1016</span>
                  <span className="text-hw-screw hidden sm:inline">|</span>
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
