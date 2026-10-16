import { cn } from '../../lib/utils';
import { playMechanicalClick } from '../../lib/mechanicalClick';
import { useSvgId } from '../../lib/useSvgId';
import type { LedColorName } from '../../theme/tokens';
import { LedIndicator } from '../rack/LedIndicator';

export interface ToggleSwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  /** Silk-screened function name. */
  label: string;
  onLabel?: string;
  offLabel?: string;
  /** Status LED colour next to the lever; `false` hides the LED. */
  led?: LedColorName | string | false;
  /** Play a synthesised mechanical click when thrown. */
  clickSound?: boolean;
  disabled?: boolean;
  className?: string;
}

/**
 * Mechanical bat-handle toggle switch: hex nut, threaded bushing and chrome lever
 * that snaps between ON (up) and OFF (down). Exposed as an ARIA switch.
 */
export function ToggleSwitch({
  checked,
  onChange,
  label,
  onLabel = 'ON',
  offLabel = 'OFF',
  led = 'green',
  clickSound = true,
  disabled = false,
  className,
}: ToggleSwitchProps) {
  const id = useSvgId('toggle');

  const toggle = (): void => {
    if (disabled) return;
    if (clickSound) playMechanicalClick(2400, 0.26);
    onChange(!checked);
  };

  return (
    <div className={cn('no-select flex flex-col items-center gap-2', className)}>
      <div className="flex min-h-[28px] w-full items-center justify-center px-1">
        <span className="silk max-w-[110px] text-center leading-tight">{label}</span>
      </div>

      {/* The lever defines the column axis; the LED floats to its right, out of flow. */}
      <div className="relative flex items-center justify-center">
        <button
          type="button"
          role="switch"
          aria-checked={checked}
          aria-label={label}
          disabled={disabled}
          onClick={toggle}
          className={cn(
            'group flex flex-col items-center gap-1 outline-none',
            'focus-visible:outline focus-visible:outline-1 focus-visible:outline-offset-2 focus-visible:outline-silk-neutral',
            disabled ? 'cursor-not-allowed opacity-40' : 'cursor-pointer',
          )}
        >
          <span className={cn('silk text-[9px]', checked ? 'text-silk' : 'text-silk-dim/60')}>{onLabel}</span>

          <svg width={30} height={48} viewBox="0 0 40 64" aria-hidden="true">
            <defs>
              <linearGradient id={`${id}-nut`} x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#5C6272" />
                <stop offset="100%" stopColor="#262A33" />
              </linearGradient>
              <linearGradient id={`${id}-lever`} x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#4C5262" />
                <stop offset="45%" stopColor="#D5D9E2" />
                <stop offset="100%" stopColor="#4C5262" />
              </linearGradient>
              <radialGradient id={`${id}-tip`} cx="38%" cy="32%" r="70%">
                <stop offset="0%" stopColor="#F2F4F8" />
                <stop offset="60%" stopColor="#8A90A0" />
                <stop offset="100%" stopColor="#3A3F4B" />
              </radialGradient>
            </defs>

            {/* Mounting plate cut-out */}
            <rect x="3" y="3" width="34" height="58" fill="#121418" stroke="#2A2E39" strokeWidth="1" />
            {/* Hex nut */}
            <polygon
              points="20,20 30.4,26 30.4,38 20,44 9.6,38 9.6,26"
              fill={`url(#${id}-nut)`}
              stroke="#0B0C0F"
              strokeWidth="0.8"
            />
            {/* Threaded bushing */}
            <circle cx="20" cy="32" r="7" fill="#1C1F26" stroke="#0A0B0D" strokeWidth="0.8" />
            <circle cx="20" cy="32" r="5.2" fill="none" stroke="#2F3440" strokeWidth="0.6" />

            {/* Lever: flips through vertical on state change */}
            <g
              style={{
                transform: `scaleY(${checked ? 1 : -1})`,
                transformOrigin: '20px 32px',
                transformBox: 'view-box',
                transition: 'transform 110ms cubic-bezier(0.7, 0, 0.3, 1)',
              }}
            >
              <ellipse cx="21.5" cy="20" rx="4.4" ry="11" fill="rgba(0,0,0,0.45)" />
              <polygon points="16.6,32 23.4,32 22.3,12 17.7,12" fill={`url(#${id}-lever)`} stroke="#1A1D24" strokeWidth="0.5" />
              <circle cx="20" cy="10.5" r="4.6" fill={`url(#${id}-tip)`} stroke="#1A1D24" strokeWidth="0.5" />
            </g>
          </svg>

          <span className={cn('silk text-[9px]', !checked ? 'text-silk' : 'text-silk-dim/60')}>{offLabel}</span>
        </button>

        {led ? (
          <span className="pointer-events-none absolute left-full top-1/2 ml-3 flex -translate-y-1/2 items-center">
            <LedIndicator color={led} on={checked && !disabled} size="xs" />
          </span>
        ) : null}
      </div>
    </div>
  );
}
