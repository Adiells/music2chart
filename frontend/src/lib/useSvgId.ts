import { useId } from 'react';

/**
 * Stable, URL-safe id for SVG `<defs>` references (`url(#id)`).
 * React's `useId` may contain characters (`:`, `«`, `»`) that break `url()` lookups.
 */
export function useSvgId(prefix: string): string {
  const raw = useId();
  return `${prefix}-${raw.replace(/[^a-zA-Z0-9_-]/g, '')}`;
}
