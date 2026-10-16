import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { KeyboardEvent, PointerEvent } from 'react';
import { clamp, cn, quantize } from '../../lib/utils';
import { resolveLedColor } from '../../theme/tokens';
import type { LedColorName } from '../../theme/tokens';
import { KnobGraphic } from './KnobGraphic';

export interface RotaryKnobProps {
  value: number;
  onChange: (value: number) => void;
  /** Silk-screened parameter name. */
  label: string;
  min?: number;
  max?: number;
  step?: number;
  /** Value restored on double-click. */
  defaultValue?: number;
  /** Unit suffix shown in the readout (e.g. `MS`, `%`, `X`). */
  unit?: string;
  /** Custom readout formatter. */
  format?: (value: number) => string;
  /** Rendered knob diameter (including graduation ring) in px. */
  size?: number;
  /** Number of graduation ticks across the 270 degree sweep. */
  ticks?: number;
  /** Colour of the value arc (functional indicator). */
  accent?: LedColorName | string;
  /** Pixels of pointer travel needed to sweep the full range. */
  travel?: number;
  disabled?: boolean;
}

const START_ANGLE = -135;
const SWEEP = 270;
const CX = 50;
const CY = 50;

function polar(r: number, deg: number): { x: number; y: number } {
  const rad = (deg * Math.PI) / 180;
  return { x: CX + r * Math.sin(rad), y: CY - r * Math.cos(rad) };
}

function arcPath(r: number, fromDeg: number, toDeg: number): string {
  const a = polar(r, fromDeg);
  const b = polar(r, toDeg);
  const large = toDeg - fromDeg > 180 ? 1 : 0;
  return `M ${a.x} ${a.y} A ${r} ${r} 0 ${large} 1 ${b.x} ${b.y}`;
}

/**
 * Graduated rotary knob with smooth vertical/horizontal drag, wheel, keyboard
 * and double-click reset. Hold Shift while dragging or scrolling for fine control.
 * Exposed to assistive technology as an ARIA slider.
 */
export function RotaryKnob({
  value,
  onChange,
  label,
  min = 0,
  max = 100,
  step = 1,
  defaultValue,
  unit,
  format,
  size = 76,
  ticks = 21,
  accent = '#E6E8EE',
  travel = 220,
  disabled = false,
}: RotaryKnobProps) {
  const [dragging, setDragging] = useState(false);
  const surfaceRef = useRef<HTMLDivElement>(null);
  // Float accumulator so sub-step pointer motion is never lost (smooth drag).
  const dragRef = useRef<{ lastX: number; lastY: number; acc: number } | null>(null);
  const latest = useRef({ value, onChange, min, max, step, disabled });
  useLayoutEffect(() => {
    latest.current = { value, onChange, min, max, step, disabled };
  });

  const range = max - min || 1;
  const norm = clamp((value - min) / range, 0, 1);
  const angle = START_ANGLE + norm * SWEEP;
  const accentHex = resolveLedColor(accent);
  const readout = format ? format(value) : `${value}`;

  const commit = useCallback((next: number) => {
    const { value: current, onChange: emit, min: lo, max: hi, step: st } = latest.current;
    const q = quantize(next, lo, hi, st);
    if (q !== current) emit(q);
  }, []);

  // Native non-passive wheel listener so the page does not scroll while adjusting.
  useEffect(() => {
    const el = surfaceRef.current;
    if (!el) return undefined;
    const onWheel = (e: WheelEvent): void => {
      if (latest.current.disabled) return;
      e.preventDefault();
      const { value: v, step: st, max: hi, min: lo } = latest.current;
      const fine = e.shiftKey ? 1 : Math.max(1, Math.round((hi - lo) / st / 50));
      commit(v + (e.deltaY < 0 ? 1 : -1) * st * fine);
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, [commit]);

  const onPointerDown = (e: PointerEvent<HTMLDivElement>): void => {
    if (disabled || e.button !== 0) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    e.currentTarget.focus();
    dragRef.current = { lastX: e.clientX, lastY: e.clientY, acc: value };
    setDragging(true);
  };

  const onPointerMove = (e: PointerEvent<HTMLDivElement>): void => {
    const drag = dragRef.current;
    if (!drag) return;
    const delta = drag.lastY - e.clientY + (e.clientX - drag.lastX);
    drag.lastX = e.clientX;
    drag.lastY = e.clientY;
    const fine = e.shiftKey ? 0.15 : 1;
    drag.acc = clamp(drag.acc + (delta / travel) * range * fine, min, max);
    commit(drag.acc);
  };

  const endDrag = (e: PointerEvent<HTMLDivElement>): void => {
    if (!dragRef.current) return;
    dragRef.current = null;
    setDragging(false);
    if (e.currentTarget.hasPointerCapture(e.pointerId)) e.currentTarget.releasePointerCapture(e.pointerId);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>): void => {
    if (disabled) return;
    const big = step * Math.max(1, Math.round(range / step / 10));
    const map: Record<string, number | undefined> = {
      ArrowUp: value + step,
      ArrowRight: value + step,
      ArrowDown: value - step,
      ArrowLeft: value - step,
      PageUp: value + big,
      PageDown: value - big,
      Home: min,
      End: max,
    };
    const next = map[e.key];
    if (next === undefined) return;
    e.preventDefault();
    commit(next);
  };

  const onDoubleClick = (): void => {
    if (!disabled && defaultValue !== undefined) commit(defaultValue);
  };

  return (
    <div className={cn('no-select flex flex-col items-center gap-2', disabled && 'cursor-not-allowed')}>
      <span className="silk text-center">{label}</span>

      <div
        ref={surfaceRef}
        role="slider"
        tabIndex={disabled ? -1 : 0}
        aria-label={label}
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuenow={value}
        aria-valuetext={`${readout}${unit ? ` ${unit}` : ''}`}
        aria-disabled={disabled || undefined}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onKeyDown={onKeyDown}
        onDoubleClick={onDoubleClick}
        className={cn(
          'touch-none outline-none focus-visible:outline focus-visible:outline-1 focus-visible:outline-offset-2 focus-visible:outline-silk-neutral',
          disabled ? 'cursor-not-allowed' : dragging ? 'cursor-grabbing' : 'cursor-grab',
        )}
        style={{ width: size, height: size }}
      >
        <svg width={size} height={size} viewBox="0 0 100 100" aria-hidden="true">
          {/* Silk-screened graduation */}
          {Array.from({ length: ticks }, (_, i) => {
            const t = ticks === 1 ? 0 : i / (ticks - 1);
            const deg = START_ANGLE + t * SWEEP;
            const major = i === 0 || i === ticks - 1 || i % 5 === 0;
            const a = polar(major ? 41 : 43, deg);
            const b = polar(48, deg);
            return (
              <line
                key={i}
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                stroke={major ? '#8E95A5' : '#4A5060'}
                strokeWidth={major ? 1.6 : 1}
              />
            );
          })}

          {/* Value arc track + functional indicator */}
          <path d={arcPath(38, START_ANGLE, START_ANGLE + SWEEP)} fill="none" stroke="#0A0B0D" strokeWidth={2.4} />
          {norm > 0.002 ? (
            <path
              d={arcPath(38, START_ANGLE, angle)}
              fill="none"
              stroke={accentHex}
              strokeWidth={2.4}
              opacity={disabled ? 0.35 : 0.95}
            />
          ) : null}

          <KnobGraphic
            cx={CX}
            cy={CY}
            r={31}
            angle={angle}
            disabled={disabled}
            transition={dragging ? '' : 'transform 90ms ease-out'}
          />
        </svg>
      </div>

      <output
        className="min-w-[64px] border border-hw-border bg-chassis px-2 py-0.5 text-center font-mono text-[11px] tabular-nums tracking-silk text-silk shadow-recess"
        aria-hidden="true"
      >
        {readout}
        {unit ? <span className="ml-1 text-silk-dim">{unit}</span> : null}
      </output>
    </div>
  );
}
