// Generated from landing-preview.html (markup parity with the reference).
import type { CSSProperties } from 'react';
import type { Language } from '../../lib/language';

export function LandingPipeline({ language = 'en' }: { language?: Language }) {
  const pt = language === 'pt-BR';
  return (
<section className="section" id="pipeline">
    <div className="wrap">
      <div className="sec-head">
        <div className="sec-head-copy reveal">
          <div className="sec-eyebrow"><span className="idx">01</span> {pt ? "Fluxo de sinal" : "Signal flow"}</div>
          <h2>{pt ? <>Seis etapas.<br />Uma chart limpa.</> : <>Six stages.<br />One clean chart.</>}</h2>
          <p className="sec-lead">
            Every upload runs the full DSP + neural pipeline — no cloud black box, no manual
            mapping. Each stage streams its progress live over Server-Sent Events.
          </p>
        </div>
        <div className="sec-aside reveal" style={{ "--delay": ".08s" } as CSSProperties}>
          <b>Pipeline integrity</b>
          192 PPQ grid<br />
          24-tick sustain margin<br />
          35–40 ms chord fusion
        </div>
      </div>

      <div className="pipeline-grid">
        <article className="stage-card reveal" data-step="01" style={{ "--c": "var(--orange)", "--delay": "0s" } as CSSProperties}>
          <div className="stage-card-head">
            <span className="stage-code"><i className="led on" style={{ color: "var(--orange)" } as CSSProperties}></i> DSP-STEM</span>
            <span className="mono-label" style={{ fontSize: "7.5px" } as CSSProperties}>Stage 01</span>
          </div>
          <h3>Demucs v4 stem separation</h3>
          <div className="stage-engine">Meta htdemucs · hybrid transformer</div>
          <p>Isolates the lead guitar from full stereo masters before pitch extraction — stripping drums, vocals and sub-bass bleed.</p>
          <div className="stage-spec"><i className="led" style={{ color: "var(--orange)" } as CSSProperties}></i> 44.1 / 48 kHz FP32 tensor → isolated guitar stem + mono fallback</div>
        </article>

        <article className="stage-card reveal" data-step="02" style={{ "--c": "var(--yellow)", "--delay": ".05s" } as CSSProperties}>
          <div className="stage-card-head">
            <span className="stage-code"><i className="led on" style={{ color: "var(--yellow)" } as CSSProperties}></i> DSP-SYNC</span>
            <span className="mono-label" style={{ fontSize: "7.5px" } as CSSProperties}>Stage 02</span>
          </div>
          <h3>Tempo & beat tracking</h3>
          <div className="stage-engine">BeatNet & Librosa · 192 PPQ grid</div>
          <p>Extracts dynamic tempo maps, beat positions and meter signatures, then converts seconds into 192-pulse-per-quarter ticks.</p>
          <div className="stage-spec"><i className="led" style={{ color: "var(--yellow)" } as CSSProperties}></i> Milli-BPM serialization · 120.0 BPM → <span style={{ color: "var(--silk)" } as CSSProperties}>B 120000</span></div>
        </article>

        <article className="stage-card reveal" data-step="03" style={{ "--c": "var(--blue)", "--delay": ".1s" } as CSSProperties}>
          <div className="stage-card-head">
            <span className="stage-code"><i className="led on" style={{ color: "var(--blue)" } as CSSProperties}></i> AI-MIDI</span>
            <span className="mono-label" style={{ fontSize: "7.5px" } as CSSProperties}>Stage 03</span>
          </div>
          <h3>Polyphonic transcription</h3>
          <div className="stage-engine">Spotify Basic Pitch · CNN audio-to-MIDI</div>
          <p>Predicts note events — pitch 0–127, onset, offset and confidence amplitude — directly from the isolated guitar stem.</p>
          <div className="stage-spec"><i className="led" style={{ color: "var(--blue)" } as CSSProperties}></i> NoteEvent(start, end, pitch, amplitude[0.0–1.0])</div>
        </article>

        <article className="stage-card reveal" data-step="04" style={{ "--c": "var(--red)", "--delay": "0s" } as CSSProperties}>
          <div className="stage-card-head">
            <span className="stage-code"><i className="led on" style={{ color: "var(--red)" } as CSSProperties}></i> DSP-FILT</span>
            <span className="mono-label" style={{ fontSize: "7.5px" } as CSSProperties}>Stage 04</span>
          </div>
          <h3>Harmonic suppression</h3>
          <div className="stage-engine">Spectral & octave artifact filter</div>
          <p>Removes high-gain distortion harmonics — octave +12 st and fifth +19 st — that would otherwise become false chords.</p>
          <div className="stage-spec"><i className="led" style={{ color: "var(--red)" } as CSSProperties}></i> Suppresses overtone spikes within 25 ms of the fundamental onset</div>
        </article>

        <article className="stage-card reveal" data-step="05" style={{ "--c": "var(--green)", "--delay": ".05s" } as CSSProperties}>
          <div className="stage-card-head">
            <span className="stage-code"><i className="led on" style={{ color: "var(--green)" } as CSSProperties}></i> MAP-5FRT</span>
            <span className="mono-label" style={{ fontSize: "7.5px" } as CSSProperties}>Stage 05</span>
          </div>
          <h3>Game design mapping</h3>
          <div className="stage-engine">Tessitura projection · HOPO heuristics</div>
          <p>Fuses string-roll micro-delays into chords, snaps onsets to valid subdivisions, and projects pitch onto the five frets.</p>
          <div className="stage-spec"><i className="led" style={{ color: "var(--green)" } as CSSProperties}></i> 1/4 (192) · 1/8 (96) · 1/12 (64) · 1/16 (48) · 1/24 (32) · 1/32 (24)</div>
        </article>

        <article className="stage-card reveal" data-step="06" style={{ "--c": "var(--power)", "--delay": ".1s" } as CSSProperties}>
          <div className="stage-card-head">
            <span className="stage-code"><i className="led on" style={{ color: "var(--power)" } as CSSProperties}></i> PKG-BIN</span>
            <span className="mono-label" style={{ fontSize: "7.5px" } as CSSProperties}>Stage 06</span>
          </div>
          <h3>Chart & package writing</h3>
          <div className="stage-engine">notes.chart · song.ini · song.ogg</div>
          <p>Serializes strict Clone Hero text charts and little-endian .sng containers, then packages a drop-in song folder.</p>
          <div className="stage-spec"><i className="led" style={{ color: "var(--power)" } as CSSProperties}></i> UTF-8 notes.chart + .sng v1 + ready-to-play ZIP archive</div>
        </article>
      </div>
    </div>
  </section>
  );
}
