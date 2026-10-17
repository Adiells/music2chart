import { useId } from 'react';
import type { KeyboardEvent } from 'react';
import { cn } from '../../lib/utils';
import { playMechanicalClick } from '../../lib/mechanicalClick';
import { LedIndicator } from '../rack/LedIndicator';

export interface PresetItem<T extends string> {
  value: T;
  label: string;
  description: string;
  tag?: string;
}

export interface PresetSelectorProps<T extends string> {
  options: readonly PresetItem<T>[];
  value: T;
  onChange: (value: T) => void;
  label?: string;
  disabled?: boolean;
  className?: string;
}

/**
 * Linear tactile preset selector for Clone Hero mapping heuristics.
 * Replaces cumbersome rotary dials with high-precision, one-click segmented cards.
 */
export function PresetSelector<T extends string>({
  options,
  value,
  onChange,
  label = 'MAPPING PROFILE',
  disabled = false,
  className,
}: PresetSelectorProps<T>) {
  const groupId = useId();

  const handleSelect = (nextVal: T): void => {
    if (disabled || nextVal === value) return;
    playMechanicalClick(3200, 0.2);
    onChange(nextVal);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>, currentIndex: number): void => {
    if (disabled) return;
    let nextIndex = currentIndex;
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
      nextIndex = (currentIndex + 1) % options.length;
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      nextIndex = (currentIndex - 1 + options.length) % options.length;
    } else if (e.key === 'Home') {
      nextIndex = 0;
    } else if (e.key === 'End') {
      nextIndex = options.length - 1;
    } else {
      return;
    }
    e.preventDefault();
    handleSelect(options[nextIndex].value);
  };

  return (
    <div className={cn('flex flex-col gap-2', className)}>
      <div className="flex items-center justify-between">
        <span className="silk">{label}</span>
        <span className="silk-wide text-[9px]">
          {options.find((o) => o.value === value)?.tag ?? 'PROFILE SELECTED'}
        </span>
      </div>

      <div
        role="radiogroup"
        aria-label={label}
        className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3"
      >
        {options.map((opt, idx) => {
          const isSelected = opt.value === value;
          return (
            <div
              key={opt.value}
              id={`${groupId}-${opt.value}`}
              role="radio"
              tabIndex={disabled ? -1 : isSelected ? 0 : -1}
              aria-checked={isSelected}
              aria-disabled={disabled || undefined}
              onClick={() => handleSelect(opt.value)}
              onKeyDown={(e) => handleKeyDown(e, idx)}
              className={cn(
                'group relative flex flex-col justify-between border p-3 text-left transition-all duration-150',
                isSelected
                  ? 'border-fret-orange bg-[#181B22] shadow-[0_0_12px_rgba(255,145,0,0.15)]'
                  : 'border-hw-border bg-chassis hover:border-hw-screw hover:bg-panel',
                disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'
              )}
            >
              {/* Header with Title and Active LED Indicator */}
              <div className="flex items-center justify-between gap-2">
                <span
                  className={cn(
                    'font-mono text-[11px] font-semibold uppercase tracking-silk',
                    isSelected ? 'text-silk' : 'text-silk-dim group-hover:text-silk'
                  )}
                >
                  {opt.label}
                </span>
                <LedIndicator
                  color={isSelected ? 'orange' : 'yellow'}
                  on={isSelected}
                  size="xs"
                />
              </div>

              {/* Description */}
              <p className="mt-1.5 font-mono text-[10px] leading-relaxed text-silk-neutral">
                {opt.description}
              </p>

              {/* Bottom Tag / Indicator */}
              {opt.tag ? (
                <div className="mt-2 flex items-center justify-between border-t border-hw-border/60 pt-1.5">
                  <span className="silk-wide text-[8px]">{opt.tag}</span>
                  {isSelected ? (
                    <span className="font-mono text-[8px] uppercase tracking-silk text-fret-orange">
                      ACTIVE
                    </span>
                  ) : null}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
