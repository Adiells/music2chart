import { useState } from 'react';
import type { ButtonHTMLAttributes, KeyboardEvent, PointerEvent } from 'react';
import { cn } from '../../lib/utils';
import { playMechanicalClick } from '../../lib/mechanicalClick';
import type { LedColorName } from '../../theme/tokens';
import type { LedBlink } from '../rack/LedIndicator';
import { LedIndicator } from '../rack/LedIndicator';

export type PushButtonVariant = 'standard' | 'master' | 'alert';
export type PushButtonSize = 'sm' | 'md' | 'lg';

export interface PushButtonProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children' | 'color'> {
  /** Silk-screened cap legend. */
  label: string;
  /** Secondary legend printed under the main label. */
  sublabel?: string;
  /** Embedded LED colour; omit for a plain cap. */
  led?: LedColorName | string;
  ledOn?: boolean;
  ledBlink?: LedBlink;
  /** Latched (pressed-in) appearance for radio / latching use. */
  latched?: boolean;
  variant?: PushButtonVariant;
  size?: PushButtonSize;
  /** Play a synthesised mechanical click on actuation. */
  clickSound?: boolean;
}

const CAP_BG: Record<PushButtonVariant, string> = {
  standard: 'bg-[#252932]',
  master: 'bg-[#2C313B]',
  alert: 'bg-[#2E1A1F]',
};

const SIZE_CLASS: Record<PushButtonSize, string> = {
  sm: 'min-w-[56px] px-2.5 py-1.5 text-[9px]',
  md: 'min-w-[76px] px-3.5 py-2.5 text-[10px]',
  lg: 'min-w-[150px] px-5 py-4 text-[12px]',
};

const RAISED = 'inset 1px 1px 0 rgba(255,255,255,0.08), inset -1px -1px 0 rgba(0,0,0,0.55), 0 2px 0 #050608';
const SUNK = 'inset 1px 1px 0 rgba(0,0,0,0.6), inset -1px -1px 0 rgba(255,255,255,0.03), 0 0 0 #050608';

/**
 * Tactile mechanical push button: recessed bezel, square cap with 2px travel,
 * optional embedded LED and synthesised click on actuation.
 */
export function PushButton({
  label,
  sublabel,
  led,
  ledOn = false,
  ledBlink = false,
  latched = false,
  variant = 'standard',
  size = 'md',
  clickSound = true,
  disabled,
  className,
  onPointerDown,
  onPointerUp,
  onPointerLeave,
  onKeyDown,
  onKeyUp,
  type = 'button',
  ...rest
}: PushButtonProps) {
  const [pressed, setPressed] = useState(false);
  const down = pressed || latched;

  const actuate = (): void => {
    setPressed(true);
    if (clickSound) playMechanicalClick(variant === 'master' ? 2600 : 3400, 0.22);
  };

  const handlePointerDown = (e: PointerEvent<HTMLButtonElement>): void => {
    onPointerDown?.(e);
    if (!disabled && e.button === 0) actuate();
  };
  const handlePointerUp = (e: PointerEvent<HTMLButtonElement>): void => {
    onPointerUp?.(e);
    setPressed(false);
  };
  const handlePointerLeave = (e: PointerEvent<HTMLButtonElement>): void => {
    onPointerLeave?.(e);
    setPressed(false);
  };
  const handleKeyDown = (e: KeyboardEvent<HTMLButtonElement>): void => {
    onKeyDown?.(e);
    if (!disabled && !e.repeat && (e.key === ' ' || e.key === 'Enter')) actuate();
  };
  const handleKeyUp = (e: KeyboardEvent<HTMLButtonElement>): void => {
    onKeyUp?.(e);
    setPressed(false);
  };

  return (
    <button
      {...rest}
      type={type}
      disabled={disabled}
      aria-pressed={rest.role ? undefined : latched || undefined}
      onPointerDown={handlePointerDown}
      onPointerUp={handlePointerUp}
      onPointerLeave={handlePointerLeave}
      onKeyDown={handleKeyDown}
      onKeyUp={handleKeyUp}
      className={cn(
        'no-select inline-block border border-hw-border bg-chassis p-[3px] shadow-recess outline-none',
        'focus-visible:outline focus-visible:outline-1 focus-visible:outline-offset-2 focus-visible:outline-silk-neutral',
        disabled ? 'cursor-not-allowed opacity-40' : 'cursor-pointer',
        className,
      )}
    >
      <span
        className={cn(
          'flex flex-col items-center justify-center gap-1.5 border border-black/60 font-mono font-medium uppercase tracking-silk-wide transition-[transform,box-shadow] duration-[60ms] ease-out',
          CAP_BG[variant],
          SIZE_CLASS[size],
          down ? 'translate-y-[2px] text-silk' : 'text-silk-neutral',
        )}
        style={{ boxShadow: down ? SUNK : RAISED }}
      >
        {led ? <LedIndicator color={led} on={ledOn} blink={ledBlink} size={size === 'lg' ? 'sm' : 'xs'} /> : null}
        <span className="whitespace-nowrap leading-none">{label}</span>
        {sublabel ? <span className="silk-wide whitespace-nowrap text-[8px] leading-none">{sublabel}</span> : null}
      </span>
    </button>
  );
}
