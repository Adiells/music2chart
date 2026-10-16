/**
 * API configuration and URL resolution.
 * When deployed on static hosts like GitHub Pages, VITE_API_URL points to the backend URL
 * (e.g. https://api.music2chart.adiel.me or a Cloud Run service URL).
 * During local development with Vite dev server proxy or same-host deployment, it defaults to "".
 */
export const API_BASE_URL: string = (
  (import.meta.env.VITE_API_URL as string | undefined) || ''
).replace(/\/+$/, '');

export function getApiUrl(path: string): string {
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${cleanPath}`;
}
