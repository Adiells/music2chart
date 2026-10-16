import type { CSSProperties } from 'react';
import { cn } from '../../lib/utils';
import { useSvgId } from '../../lib/useSvgId';

export interface ScrewProps {
  /** Rendered diameter in px. */
  size?: number;
  /** Rotation of the hex socket in degrees (vary per screw for realism). */
  angle?: number;
  className?: string;
  style?: CSSProperties;
}

function hexagon(cx: number, cy: number, r: number): string {
  return Array.from({ length: 6 }, (_, i) => {
    const a = (Math.PI / 3) * i;
    return `${(cx + r * Math.cos(a)).toFixed(3)},${(cy + r * Math.sin(a)).toFixed(3)}`;
  }).join(' ');
}

/**
 * Countersunk Allen (hex socket) screw head used on module and rack corners.
 * Purely decorative: hidden from assistive technology and pointer events.
 */
export function Screw({ size = 10, angle = 0, className, style }: ScrewProps) {
  const id = useSvgId('screw');

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      className={cn('pointer-events-none shrink-0', className)}
      style={style}
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <radialGradient id={`${id}-head`} cx="34%" cy="30%" r="78%">
          <stop offset="0%" stopColor="#6E7587" />
          <stop offset="50%" stopColor="#434958" />
          <stop offset="100%" stopColor="#23262E" />
        </radialGradient>
      </defs>
      {/* Countersink recess machined into the panel */}
      <circle cx="10" cy="10" r="9.6" fill="#08090B" />
      <circle cx="10" cy="10" r="8.4" fill={`url(#${id}-head)`} stroke="#17191F" strokeWidth="0.6" />
      {/* Hex socket */}
      <g transform={`rotate(${angle} 10 10)`}>
        <polygon points={hexagon(10, 10, 3.7)} fill="#0B0C0F" stroke="#1E2128" strokeWidth="0.5" />
        <polygon points={hexagon(10, 10.6, 2.6)} fill="#050607" />
      </g>
      {/* Specular rim */}
      <path
        d="M4.6 7.4 A6.2 6.2 0 0 1 8.6 3.9"
        fill="none"
        stroke="rgba(255,255,255,0.22)"
        strokeWidth="0.8"
        strokeLinecap="round"
      />
    </svg>
  );
}
