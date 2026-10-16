/**
 * Join conditional class names, skipping falsy entries.
 *
 * @param parts - Class name fragments; `false`, `null`, `undefined` and `""` are ignored.
 * @returns A single space-separated class string.
 */
export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(' ');
}

/**
 * Clamp a number into the inclusive range [min, max].
 */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

/**
 * Convert a `#RRGGBB` hex colour into an `rgba()` string.
 *
 * @param hex - Six-digit hex colour, with or without leading `#`.
 * @param alpha - Opacity in [0, 1].
 */
export function hexToRgba(hex: string, alpha: number): string {
  const { r, g, b } = parseHex(hex);
  return `rgba(${r}, ${g}, ${b}, ${clamp(alpha, 0, 1)})`;
}

/**
 * Darken (factor < 1) or lighten (factor > 1) a hex colour by scaling its channels.
 */
export function shadeHex(hex: string, factor: number): string {
  const { r, g, b } = parseHex(hex);
  const ch = (v: number): string =>
    Math.round(clamp(v * factor, 0, 255))
      .toString(16)
      .padStart(2, '0');
  return `#${ch(r)}${ch(g)}${ch(b)}`;
}

function parseHex(hex: string): { r: number; g: number; b: number } {
  const clean = hex.replace('#', '');
  const full =
    clean.length === 3
      ? clean
          .split('')
          .map((c) => c + c)
          .join('')
      : clean.slice(0, 6);
  const num = Number.parseInt(full, 16);
  if (Number.isNaN(num)) return { r: 0, g: 0, b: 0 };
  return { r: (num >> 16) & 0xff, g: (num >> 8) & 0xff, b: num & 0xff };
}

/**
 * Number of decimal places implied by a step value (e.g. 0.05 -> 2).
 */
export function stepDecimals(step: number): number {
  const text = step.toString();
  const dot = text.indexOf('.');
  return dot === -1 ? 0 : text.length - dot - 1;
}

/**
 * Snap a value to the nearest step inside [min, max] without float drift.
 */
export function quantize(value: number, min: number, max: number, step: number): number {
  const snapped = min + Math.round((value - min) / step) * step;
  return Number(clamp(snapped, min, max).toFixed(stepDecimals(step)));
}
