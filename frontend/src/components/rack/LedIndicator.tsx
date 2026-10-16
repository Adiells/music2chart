import { cn, hexToRgba, shadeHex } from '../../lib/utils';
import { useSvgId } from '../../lib/useSvgId';
import { resolveLedColor } from '../../theme/tokens';
import type { LedColorName } from '../../theme/tokens';

export type LedSize = 'xs' | 'sm' | 'md' | 'lg';
export type LedBlink = false | 'slow' | 'fast';

export interface LedIndicatorProps {
  /** Token name (`green`, `red`, ... `open`, `starpower`) or raw hex colour. */
  color?: LedColorName | string;
  /** Whether the LED is lit. */
  on?: boolean;
  size?: LedSize;
  /** Blink pattern while lit. */
  blink?: LedBlink;
  /** Optional silk-screened label next to the LED. */
  label?: string;
  labelPosition?: 'right' | 'bottom';
  className?: string;
}

const LENS_PX: Record<LedSize, number> = { xs: 8, sm: 11, md: 14, lg: 20 };

/**
 * Panel-mount LED with a machined metal bezel, tinted lens and specular highlight.
 * When lit, a soft halo is emitted around the bezel; blinking only affects the lit layer,
 * so the dark lens tint stays visible exactly like a physical LED.
 */
export function LedIndicator({
  color = 'green',
  on = false,
  size = 'sm',
  blink = false,
  label,
  labelPosition = 'right',
  className,
}: LedIndicatorProps) {
  const id = useSvgId('led');
  const hex = resolveLedColor(color);
  const px = LENS_PX[size];
  const outer = Math.round(px * 1.45);

  const blinkClass = on && blink ? (blink === 'fast' ? 'animate-led-blink-fast' : 'animate-led-blink') : '';

  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center',
        labelPosition === 'bottom' ? 'flex-col gap-1.5' : 'gap-2',
        className,
      )}
      role="img"
      aria-label={`${label ?? 'LED'} ${on ? 'on' : 'off'}`}
    >
      <span className="relative inline-block" style={{ width: outer, height: outer }}>
        {/* Base: bezel + unlit tinted lens */}
        <svg width={outer} height={outer} viewBox="0 0 24 24" className="absolute inset-0" aria-hidden="true">
          <defs>
            <linearGradient id={`${id}-bezel`} x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#6A7182" />
              <stop offset="55%" stopColor="#353A46" />
              <stop offset="100%" stopColor="#1A1D24" />
            </linearGradient>
            <radialGradient id={`${id}-off`} cx="40%" cy="38%" r="70%">
              <stop offset="0%" stopColor={shadeHex(hex, 0.42)} />
              <stop offset="100%" stopColor={shadeHex(hex, 0.12)} />
            </radialGradient>
          </defs>
          <circle cx="12" cy="12" r="11.6" fill={`url(#${id}-bezel)`} />
          <circle cx="12" cy="12" r="9.9" fill="#060708" />
          <circle cx="12" cy="12" r="8.6" fill={`url(#${id}-off)`} />
          <ellipse cx="9.4" cy="8.6" rx="3.1" ry="1.9" fill="rgba(255,255,255,0.16)" transform="rotate(-32 9.4 8.6)" />
        </svg>

        {/* Lit layer: halo + emissive lens */}
        <span
          className={cn('absolute inset-0 transition-opacity duration-150 ease-out', blinkClass)}
          style={{ opacity: on ? 1 : 0 }}
          aria-hidden="true"
        >
          <span
            className="hw-round absolute"
            style={{
              inset: outer * 0.12,
              boxShadow: `0 0 ${px * 0.55}px ${px * 0.12}px ${hexToRgba(hex, 0.6)}, 0 0 ${px * 1.5}px ${px * 0.25}px ${hexToRgba(hex, 0.22)}`,
            }}
          />
          <svg width={outer} height={outer} viewBox="0 0 24 24" className="absolute inset-0">
            <defs>
              <radialGradient id={`${id}-on`} cx="42%" cy="40%" r="62%">
                <stop offset="0%" stopColor="#FFFFFF" />
                <stop offset="28%" stopColor={shadeHex(hex, 1.25)} />
                <stop offset="70%" stopColor={hex} />
                <stop offset="100%" stopColor={shadeHex(hex, 0.6)} />
              </radialGradient>
            </defs>
            <circle cx="12" cy="12" r="8.6" fill={`url(#${id}-on)`} />
            <ellipse cx="9.4" cy="8.6" rx="3.1" ry="1.9" fill="rgba(255,255,255,0.55)" transform="rotate(-32 9.4 8.6)" />
          </svg>
        </span>
      </span>

      {label ? <span className="silk whitespace-nowrap">{label}</span> : null}
    </span>
  );
}
