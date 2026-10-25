/**
 * API configuration and URL resolution.
 * When deployed on static hosts like GitHub Pages, VITE_API_URL points to the backend URL
 * (e.g. https://music2chart-api-122453307762.us-central1.run.app).
 * During local development with Vite dev server proxy or same-host deployment, it defaults to "".
 */
const DEFAULT_CLOUD_RUN_API = 'https://music2chart-api-122453307762.us-central1.run.app';

function resolveApiBaseUrl(): string {
  const envUrl = (import.meta.env.VITE_API_URL as string | undefined)?.trim();
  if (envUrl) {
    return envUrl.replace(/\/+$/, '');
  }
  // When running on GitHub Pages (or any non-localhost domain), use Cloud Run API
  if (
    typeof window !== 'undefined' &&
    window.location.hostname !== 'localhost' &&
    window.location.hostname !== '127.0.0.1'
  ) {
    return DEFAULT_CLOUD_RUN_API;
  }
  return '';
}

export const API_BASE_URL: string = resolveApiBaseUrl();

export function getApiUrl(path: string): string {
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${cleanPath}`;
}

export interface ChartFeedbackPayload {
  task_id: string | null;
  rating: number;
  tags: string[];
  comment?: string;
  song_name?: string;
  artist?: string;
}

/** POST /api/v1/chart/feedback: sends a user rating for a generated chart. */
export async function submitChartFeedback(payload: ChartFeedbackPayload): Promise<void> {
  const response = await fetch(getApiUrl('/api/v1/chart/feedback'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`Feedback request failed with status ${response.status}`);
  }
}
