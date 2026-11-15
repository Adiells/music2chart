import type { Language } from './language';

/**
 * API configuration and URL resolution.
 * When deployed on static hosts like GitHub Pages, VITE_API_URL points to the backend URL
 * (e.g. https://music2chart-api-122453307762.us-central1.run.app).
 * During local development with Vite dev server proxy or same-host deployment, it defaults to "".
 */
const DEFAULT_CLOUD_RUN_API = 'https://music2chart-api-122453307762.us-central1.run.app';

/**
 * Hosted backend availability switch.
 *
 * The Cloud Run backend was shut down to cut hosting costs. While this flag is `true`
 * no request leaves the browser: every call that would reach the API fails fast and the
 * UI explains that the backend is offline and how to run the project locally instead.
 * Set it back to `false` (and restore `VITE_API_URL`) to reconnect to a live backend.
 */
export const BACKEND_OFFLINE = true;

/** Public repository used in the "run it locally" notice. */
export const REPOSITORY_URL = 'https://github.com/Adiells/music2chart';

const BACKEND_OFFLINE_NOTICE_EN =
  'The backend was temporarily shut down to reduce hosting costs. To use or test the chart generator, import the repository and run the project locally — see the README for the setup commands.';
const BACKEND_OFFLINE_NOTICE_PT_BR =
  'O backend foi temporariamente desligado por conta dos custos de hospedagem. Para usar ou testar o gerador de charts, importe o repositório e rode o projeto localmente — veja o README com os comandos de instalação.';

/** Bilingual explanation for every blocked backend interaction. */
export function backendOfflineNotice(language: Language = 'pt-BR'): string {
  return language === 'pt-BR' ? BACKEND_OFFLINE_NOTICE_PT_BR : BACKEND_OFFLINE_NOTICE_EN;
}

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
  preset_used?: string;
  genre?: string;
  generation_parameters?: ChartGenerationParameters;
}

export interface ChartGenerationParameters {
  selected_preset: string;
  backend_preset: string;
  output_format: string;
  max_frets: number;
  difficulty: number;
  hopo_threshold: number;
  disable_open_notes: boolean;
  collapse_fast_runs: boolean;
  consistent_patterns: boolean;
  creativity: number;
  min_amplitude: number;
  min_sustain_ticks: number;
  chord_fusion_window_s: number;
  bpm_scale: number;
  auto_calibrate_bpm: boolean;
  merge_sustained_notes: boolean;
}

export interface ChartGenerationFeedbackMetadata {
  genre: string;
  generation_parameters: ChartGenerationParameters;
}

const CHART_GENERATION_METADATA_PREFIX = 'm2c_chart_generation:';

export function storeChartGenerationMetadata(
  taskId: string,
  metadata: ChartGenerationFeedbackMetadata,
): void {
  try {
    localStorage.setItem(
      `${CHART_GENERATION_METADATA_PREFIX}${taskId}`,
      JSON.stringify(metadata),
    );
  } catch {
    // Feedback can still be submitted if browser storage is unavailable.
  }
}

export function loadChartGenerationMetadata(
  taskId: string | null,
): ChartGenerationFeedbackMetadata | null {
  if (!taskId) return null;
  try {
    const raw = localStorage.getItem(`${CHART_GENERATION_METADATA_PREFIX}${taskId}`);
    return raw ? (JSON.parse(raw) as ChartGenerationFeedbackMetadata) : null;
  } catch {
    return null;
  }
}

/** POST /api/v1/chart/feedback: sends a user rating for a generated chart. */
export async function submitChartFeedback(payload: ChartFeedbackPayload): Promise<void> {
  if (BACKEND_OFFLINE) {
    throw new Error(backendOfflineNotice());
  }
  const response = await fetch(getApiUrl('/api/v1/chart/feedback'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`Feedback request failed with status ${response.status}`);
  }
}
