import type { ReactNode } from 'react';
import { cn } from '../../lib/utils';
import { Screw } from './Screw';

export interface ModulePanelProps {
  /** Silk-screened module title (rendered uppercase). */
  title: string;
  /** Module code stamped before the title, e.g. `M-01`. */
  code?: string;
  /** Optional hardware placed on the right side of the header strip (LEDs, readouts). */
  headerRight?: ReactNode;
  /** Optional silk-screened footer strip (spec notes, signal flow). */
  footer?: ReactNode;
  /** Render Allen screws on the four corners. */
  screws?: boolean;
  className?: string;
  bodyClassName?: string;
  children: ReactNode;
}

const SCREW_ANGLES = [14, 47, 81, 29] as const;

/**
 * Rack-mounted aluminium module: sharp 1px frame, machined bevel, brushed texture,
 * four corner Allen screws and a silk-screened header strip.
 */
export function ModulePanel({
  title,
  code,
  headerRight,
  footer,
  screws = true,
  className,
  bodyClassName,
  children,
}: ModulePanelProps) {
  return (
    <section
      aria-label={title}
      className={cn('texture-brushed relative flex flex-col border border-hw-border bg-module shadow-bevel', className)}
    >
      {screws ? (
        <>
          <Screw size={9} angle={SCREW_ANGLES[0]} className="absolute left-2 top-2" />
          <Screw size={9} angle={SCREW_ANGLES[1]} className="absolute right-2 top-2" />
          <Screw size={9} angle={SCREW_ANGLES[2]} className="absolute bottom-2 left-2" />
          <Screw size={9} angle={SCREW_ANGLES[3]} className="absolute bottom-2 right-2" />
        </>
      ) : null}

      <header className="flex min-h-[34px] items-center justify-between gap-4 border-b border-hw-border px-5 py-2">
        <div className="flex items-center gap-3">
          {code ? <span className="silk-wide tabular-nums">{code}</span> : null}
          {code ? <span className="h-3 w-px bg-hw-border" aria-hidden="true" /> : null}
          <h2 className="font-mono text-[11px] font-medium uppercase tracking-silk-wide text-silk">{title}</h2>
        </div>
        {headerRight ? <div className="flex items-center gap-3">{headerRight}</div> : null}
      </header>

      <div className={cn('px-5 py-3.5', bodyClassName)}>{children}</div>

      {footer ? (
        <footer className="silk-wide border-t border-hw-border px-5 py-1.5 text-[9px]">{footer}</footer>
      ) : null}
    </section>
  );
}
