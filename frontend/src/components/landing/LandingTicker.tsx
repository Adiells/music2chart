const TERMS = [
  'DEMUCS V4 HTDEMUCS',
  '192 PPQ TIMEBASE',
  'CLONE HERO COMPLIANT',
  'SPOTIFY BASIC PITCH',
  'DYNAMIC TESSITURA',
  'POLYPHONIC VOICING',
  'FUZZY MOTIF MATCHING',
  'MICRO-QUANTIZER',
  'MP3',
  'WAV',
  'FLAC',
  'OGG',
  'YARG',
  '.SNG V1',
  'HOPO',
  'STAR POWER',
  'CHORD FUSION',
  'SSE TELEMETRY',
  'OPEN SOURCE',
];

/** Infinite horizontal technical ticker (two identical runs loop seamlessly). */
export function LandingTicker() {
  return (
    <div className="ticker" aria-hidden="true">
      <div className="ticker-track">
        {[0, 1].map((run) => (
          <div className="ticker-run" key={run}>
            {TERMS.map((t) => (
              <span key={t}>{t}</span>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
