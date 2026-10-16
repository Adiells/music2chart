/**
 * Design tokens shared by components that cannot rely on Tailwind classes
 * (SVG fills, inline glow shadows, Three.js materials).
 * Must stay in sync with tailwind.config.js and src/index.css.
 */

export const HW = {
  chassis: '#0D0E11',
  panel: '#14161B',
  module: '#1A1D24',
  border: '#2A2E39',
  screw: '#434958',
  silk: '#E6E8EE',
  silkDim: '#8E95A5',
  silkNeutral: '#A1A7B5',
} as const;

/** Canonical Clone Hero lane colours plus Open / Star Power accents. */
export const LED_COLORS = {
  green: '#00E676',
  red: '#FF1744',
  yellow: '#FFEA00',
  blue: '#2979FF',
  orange: '#FF9100',
  open: '#9D4EDD',
  starpower: '#00E5FF',
} as const;

export type LedColorName = keyof typeof LED_COLORS;

/** The five fret lanes in highway order (Green = 0 ... Orange = 4). */
export const FRET_LANES = ['green', 'red', 'yellow', 'blue', 'orange'] as const;
export type FretLane = (typeof FRET_LANES)[number];

/**
 * Resolve a named LED colour or pass through a raw hex string.
 *
 * @param color - Token name (e.g. `"green"`) or a `#RRGGBB` hex value.
 * @returns A `#RRGGBB` hex string.
 */
export function resolveLedColor(color: LedColorName | string): string {
  return color in LED_COLORS ? LED_COLORS[color as LedColorName] : color;
}
