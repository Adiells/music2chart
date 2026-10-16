import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { KeyboardEvent, PointerEvent } from 'react';
import { cn, hexToRgba } from '../../lib/utils';
import { playMechanicalClick } from '../../lib/mechanicalClick';
import { useSvgId } from '../../lib/useSvgId';
import { resolveLedColor } from '../../theme/tokens';
import type { LedColorName } from '../../theme/tokens';
import { KnobGraphic } from './KnobGraphic';

export interface RotarySelectorOption<T extends string> {
  value: T;
  label: string;
}

export interface RotarySelectorProps<T extends string> {
  options: readonly RotarySelectorOption<T>[];
  value: T;
  onChange: (value: T) => void;
  /** Silk-screened function name. */
  label: string;
  /** Total angular sweep between first and last detent, in degrees. */
  sweep?: number;
  /** Colour of the active-position LED. */
  accent?: LedColorName | string;
  clickSound?: boolean;
  disabled?: boolean;
  className?: string;
}

const VB_W = 340;
const VB_H = 152;
const CX = 170;
const CY = 88;
const KNOB_R = 30;

function polar(r: number, deg: number): { x: number; y: number } {
  const rad = (deg * Math.PI) / 180;
  return { x: CX + r * Math.sin(rad), y: CY - r * Math.cos(rad) };
}

/**
 * Detented rotary preset selector (default 5 positions).
 * Interactions: drag the knob around its axis, click the knob to advance,
 * click a silk legend to jump, mouse wheel, or arrow / Home / End keys.
 */
export function RotarySelector<T extends string>({
  options,
  value,
  onChange,
  label,
  sweep = 240,
  accent = 'orange',
  clickSound = true,
  disabled = false,
  className,
}: RotarySelectorProps<T>) {
  const svgRef = useRef<SVGSVGElement>(null);
  const dragRef = useRef<{ startX: number; startY: number; moved: boolean } | null>(null);
  const [dragging, setDragging] = useState(false);
  const glowId = useSvgId('selector-glow');

  const count = options.length;
  const index = Math.max(
    0,
    options.findIndex((o) => o.value === value),
  );
  const angles = options.map((_, i) => (count <= 1 ? 0 : -sweep / 2 + (i * sweep) / (count - 1)));
  const accentHex = resolveLedColor(accent);

  const latest = useRef({ index, options, onChange, disabled, clickSound });
  useLayoutEffect(() => {
    latest.current = { index, options, onChange, disabled, clickSound };
  });

  const select = (next: number): void => {
    const { index: cur, options: opts, onChange: emit, disabled: off, clickSound: snd } = latest.current;
    if (off) return;
    const clamped = Math.min(opts.length - 1, Math.max(0, next));
    if (clamped === cur) return;
    if (snd) playMechanicalClick(4200, 0.18);
    emit(opts[clamped].value);
  };

  useEffect(() => {
    const el = svgRef.current;
    if (!el) return undefined;
    const onWheel = (e: WheelEvent): void => {
      if (latest.current.disabled) return;
      e.preventDefault();
      select(latest.current.index + (e.deltaY < 0 ? 1 : -1));
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
    // `select` only reads from `latest`, so binding once is safe.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const pointerToAngle = (clientX: number, clientY: number): number | null => {
    const svg = svgRef.current;
    const ctm = svg?.getScreenCTM();
    if (!svg || !ctm) return null;
    const p = new DOMPoint(clientX, clientY).matrixTransform(ctm.inverse());
    return (Math.atan2(p.x - CX, -(p.y - CY)) * 180) / Math.PI;
  };

  const nearestIndex = (deg: number): number => {
    let best = 0;
    let bestDiff = Number.POSITIVE_INFINITY;
    angles.forEach((a, i) => {
      const diff = Math.abs(a - deg);
      if (diff < bestDiff) {
        bestDiff = diff;
        best = i;
      }
    });
    return best;
  };

  const onKnobPointerDown = (e: PointerEvent<SVGGElement>): void => {
    if (disabled || e.button !== 0) return;
    svgRef.current?.setPointerCapture(e.pointerId);
    svgRef.current?.focus();
    dragRef.current = { startX: e.clientX, startY: e.clientY, moved: false };
    setDragging(true);
  };

  const onPointerMove = (e: PointerEvent<SVGSVGElement>): void => {
    const drag = dragRef.current;
    if (!drag) return;
    if (!drag.moved && Math.hypot(e.clientX - drag.startX, e.clientY - drag.startY) < 4) return;
    drag.moved = true;
    const deg = pointerToAngle(e.clientX, e.clientY);
    if (deg !== null) select(nearestIndex(deg));
  };

  const onPointerUp = (e: PointerEvent<SVGSVGElement>): void => {
    const drag = dragRef.current;
    if (!drag) return;
    dragRef.current = null;
    setDragging(false);
    if (svgRef.current?.hasPointerCapture(e.pointerId)) svgRef.current.releasePointerCapture(e.pointerId);
    // A click without travel advances one detent, wrapping to the first position.
    if (!drag.moved) select(index >= count - 1 ? 0 : index + 1);
  };

  const onKeyDown = (e: KeyboardEvent<SVGSVGElement>): void => {
    const map: Record<string, number | undefined> = {
      ArrowRight: index + 1,
      ArrowUp: index + 1,
      ArrowLeft: index - 1,
      ArrowDown: index - 1,
      Home: 0,
      End: count - 1,
    };
    const next = map[e.key];
    if (next === undefined) return;
    e.preventDefault();
    select(next);
  };

  return (
    <div className={cn('no-select flex flex-col items-center gap-1', disabled && 'opacity-50', className)}>
      <span className="silk">{label}</span>

      <svg
        ref={svgRef}
        viewBox={`0 0 ${VB_W} ${VB_H}`}
        className="w-full max-w-[420px] touch-none outline-none focus-visible:outline focus-visible:outline-1 focus-visible:outline-silk-neutral"
        role="slider"
        tabIndex={disabled ? -1 : 0}
        aria-label={label}
        aria-valuemin={1}
        aria-valuemax={count}
        aria-valuenow={index + 1}
        aria-valuetext={options[index]?.label}
        aria-disabled={disabled || undefined}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        onKeyDown={onKeyDown}
      >
        <defs>
          <filter id={glowId} x="-200%" y="-200%" width="500%" height="500%">
            <feGaussianBlur stdDeviation="2.2" />
          </filter>
        </defs>

        {/* Silk-screened detent ring */}
        <circle cx={CX} cy={CY} r={KNOB_R + 5} fill="none" stroke="#2A2E39" strokeWidth={1} />

        {options.map((opt, i) => {
          const deg = angles[i];
          const active = i === index;
          const t1 = polar(KNOB_R + 7, deg);
          const t2 = polar(KNOB_R + 13, deg);
          const ledPos = polar(KNOB_R + 19, deg);
          const lbl = polar(KNOB_R + 29, deg);
          const sin = Math.sin((deg * Math.PI) / 180);
          const anchor = sin < -0.25 ? 'end' : sin > 0.25 ? 'start' : 'middle';
          return (
            <g key={opt.value}>
              <line x1={t1.x} y1={t1.y} x2={t2.x} y2={t2.y} stroke={active ? '#E6E8EE' : '#4A5060'} strokeWidth={1.6} />
              {/* Position LED */}
              {active ? (
                <circle cx={ledPos.x} cy={ledPos.y} r={4.2} fill={hexToRgba(accentHex, 0.7)} filter={`url(#${glowId})`} />
              ) : null}
              <circle cx={ledPos.x} cy={ledPos.y} r={2.6} fill="#060708" stroke="#3A3F4B" strokeWidth={0.8} />
              <circle
                cx={ledPos.x}
                cy={ledPos.y}
                r={1.9}
                fill={active ? accentHex : hexToRgba(accentHex, 0.14)}
                style={{ transition: 'fill 120ms ease-out' }}
              />
              <text
                x={lbl.x}
                y={lbl.y}
                textAnchor={anchor}
                dominantBaseline="middle"
                fontSize={9}
                letterSpacing={0.9}
                fill={active ? '#E6E8EE' : '#8E95A5'}
                className={cn('uppercase', disabled ? 'cursor-not-allowed' : 'cursor-pointer')}
                onClick={() => select(i)}
              >
                {opt.label.toUpperCase()}
              </text>
            </g>
          );
        })}

        <g
          onPointerDown={onKnobPointerDown}
          className={disabled ? 'cursor-not-allowed' : dragging ? 'cursor-grabbing' : 'cursor-pointer'}
        >
          <KnobGraphic
            cx={CX}
            cy={CY}
            r={KNOB_R}
            angle={angles[index] ?? 0}
            disabled={disabled}
            transition="transform 140ms cubic-bezier(0.3, 1.5, 0.5, 1)"
          />
        </g>
      </svg>

      <output className="border border-hw-border bg-chassis px-2 py-0.5 font-mono text-[10px] tabular-nums tracking-silk text-silk shadow-recess">
        <span className="text-silk-dim">
          POS {String(index + 1).padStart(2, '0')}/{String(count).padStart(2, '0')}
        </span>
        <span className="mx-2 text-hw-screw">|</span>
        {options[index]?.label.toUpperCase()}
      </output>
    </div>
  );
}
