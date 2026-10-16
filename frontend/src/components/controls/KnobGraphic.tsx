import { useSvgId } from '../../lib/useSvgId';

export interface KnobGraphicProps {
  cx: number;
  cy: number;
  /** Outer skirt radius in SVG user units. */
  r: number;
  /** Pointer angle in degrees, 0 = 12 o'clock, clockwise positive. */
  angle: number;
  /** CSS transition applied to the rotating group (e.g. detent snap). Empty for none. */
  transition?: string;
  disabled?: boolean;
}

/**
 * Shared knob body: drop shadow, knurled skirt, machined cap and pointer line.
 * Rendered inside a parent `<svg>` so knobs and selectors share identical hardware.
 */
export function KnobGraphic({ cx, cy, r, angle, transition = '', disabled = false }: KnobGraphicProps) {
  const id = useSvgId('knob');
  const knurlCount = 44;
  const capR = r * 0.76;

  return (
    <g opacity={disabled ? 0.45 : 1}>
      <defs>
        <radialGradient id={`${id}-cap`} cx="36%" cy="30%" r="80%">
          <stop offset="0%" stopColor="#474D5B" />
          <stop offset="45%" stopColor="#2A2E38" />
          <stop offset="100%" stopColor="#15171C" />
        </radialGradient>
        <radialGradient id={`${id}-skirt`} cx="40%" cy="35%" r="75%">
          <stop offset="0%" stopColor="#2B2F39" />
          <stop offset="100%" stopColor="#121418" />
        </radialGradient>
      </defs>

      {/* Contact shadow on the panel */}
      <circle cx={cx + r * 0.05} cy={cy + r * 0.1} r={r * 1.04} fill="rgba(0,0,0,0.55)" />

      <g
        style={{
          transform: `rotate(${angle}deg)`,
          transformOrigin: `${cx}px ${cy}px`,
          transformBox: 'view-box',
          transition,
        }}
      >
        <circle cx={cx} cy={cy} r={r} fill={`url(#${id}-skirt)`} stroke="#07080A" strokeWidth={r * 0.04} />
        {Array.from({ length: knurlCount }, (_, i) => {
          const a = (i / knurlCount) * Math.PI * 2;
          const sin = Math.sin(a);
          const cos = Math.cos(a);
          return (
            <line
              key={i}
              x1={cx + sin * capR * 1.04}
              y1={cy - cos * capR * 1.04}
              x2={cx + sin * r * 0.97}
              y2={cy - cos * r * 0.97}
              stroke="#343946"
              strokeWidth={r * 0.035}
            />
          );
        })}
        <circle cx={cx} cy={cy} r={capR} fill={`url(#${id}-cap)`} stroke="#0B0C0F" strokeWidth={r * 0.03} />
        {/* Concentric machining ring */}
        <circle cx={cx} cy={cy} r={capR * 0.62} fill="none" stroke="rgba(255,255,255,0.045)" strokeWidth={r * 0.025} />
        {/* Pointer line, silk white */}
        <line
          x1={cx}
          y1={cy - capR * 0.28}
          x2={cx}
          y2={cy - capR * 0.94}
          stroke="#E6E8EE"
          strokeWidth={r * 0.08}
          strokeLinecap="butt"
        />
        {/* Skirt notch aligned with pointer */}
        <rect x={cx - r * 0.035} y={cy - r * 0.99} width={r * 0.07} height={r * 0.2} fill="#A1A7B5" />
      </g>

      {/* Static specular highlight (light source does not rotate with the knob) */}
      <path
        d={`M ${cx - capR * 0.72} ${cy - capR * 0.2} A ${capR * 0.75} ${capR * 0.75} 0 0 1 ${cx - capR * 0.1} ${cy - capR * 0.74}`}
        fill="none"
        stroke="rgba(255,255,255,0.12)"
        strokeWidth={r * 0.05}
        strokeLinecap="round"
      />
    </g>
  );
}
