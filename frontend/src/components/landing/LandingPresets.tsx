// Generated from landing-preview.html (markup parity with the reference).
import type { CSSProperties } from 'react';
import type { Language } from '../../lib/language';

export function LandingPresets({ language = 'en' }: { language?: Language }) {
  const pt = language === 'pt-BR';
  return (
<section className="section" id="presets">
    <div className="wrap">
      <div className="sec-head">
        <div className="sec-head-copy reveal">
          <div className="sec-eyebrow"><span className="idx">03</span> Calibration</div>
          <h2>{pt ? <>Calibrado como hardware.<br />Não como palpite.</> : <>Tuned like hardware.<br />Not guesswork.</>}</h2>
          <p className="sec-lead">
            Four calibrated profiles cover the usual suspects — from strict rhythm riffs to
            shredding leads. Pick one, then trim the knobs in the calibration bay.
          </p>
        </div>
        <div className="sec-aside reveal" style={{ "--delay": ".08s" } as CSSProperties}>
          <b>Every preset enforces</b>
          192 PPQ quantization<br />
          24-tick release margin<br />
          Sliding tessitura projection
        </div>
      </div>

      <div className="preset-grid">
        <article className="preset featured reveal">
          <div className="preset-head">
            <div>
              <h3>The Best</h3>
              <div className="preset-id">the_best · default</div>
            </div>
            <span className="preset-tag">Dev pick</span>
          </div>
          <div className="knob-wrap">
            <div className="knob" style={{ "--rot": "38deg" } as CSSProperties} aria-hidden="true"></div>
            <div className="knob-side">
              <div className="knob-label">Noise gate</div>
              <div className="knob-value">0.41 <small>min amp</small></div>
            </div>
          </div>
          <div className="spec-grid">
            <div className="spec-cell"><span>BPM scale</span><b>×0.65</b></div>
            <div className="spec-cell"><span>HOPO</span><b>48 ticks</b></div>
            <div className="spec-cell"><span>Chord fusion</span><b>40 ms</b></div>
            <div className="spec-cell"><span>Max frets</span><b>2</b></div>
          </div>
          <p className="preset-note">High-precision, ghost-note-free charting with a comfortable scroll speed. The safest first pass.</p>
        </article>

        <article className="preset reveal" style={{ "--delay": ".05s" } as CSSProperties}>
          <div className="preset-head">
            <div>
              <h3>Standard</h3>
              <div className="preset-id">standard</div>
            </div>
            <span className="preset-tag">Balanced</span>
          </div>
          <div className="knob-wrap">
            <div className="knob" style={{ "--rot": "-50deg" } as CSSProperties} aria-hidden="true"></div>
            <div className="knob-side">
              <div className="knob-label">Noise gate</div>
              <div className="knob-value">0.10 <small>min amp</small></div>
            </div>
          </div>
          <div className="spec-grid">
            <div className="spec-cell"><span>BPM scale</span><b>×1.00</b></div>
            <div className="spec-cell"><span>HOPO</span><b>65 ticks</b></div>
            <div className="spec-cell"><span>Chord fusion</span><b>35 ms</b></div>
            <div className="spec-cell"><span>Max frets</span><b>2</b></div>
          </div>
          <p className="preset-note">Balanced 5-fret mapping with standard HOPO logic. Good for general rock and metal.</p>
        </article>

        <article className="preset reveal" style={{ "--delay": ".1s" } as CSSProperties}>
          <div className="preset-head">
            <div>
              <h3>Strict Rhythm</h3>
              <div className="preset-id">strict_rhythm</div>
            </div>
            <span className="preset-tag">Rhythm</span>
          </div>
          <div className="knob-wrap">
            <div className="knob" style={{ "--rot": "-24deg" } as CSSProperties} aria-hidden="true"></div>
            <div className="knob-side">
              <div className="knob-label">Noise gate</div>
              <div className="knob-value">0.20 <small>min amp</small></div>
            </div>
          </div>
          <div className="spec-grid">
            <div className="spec-cell"><span>BPM scale</span><b>×1.00</b></div>
            <div className="spec-cell"><span>HOPO</span><b>48 ticks</b></div>
            <div className="spec-cell"><span>Chord fusion</span><b>40 ms</b></div>
            <div className="spec-cell"><span>Max frets</span><b>3</b></div>
          </div>
          <p className="preset-note">Tight quantization and a solid chord foundation for punk, riff-driven and power-chord tracks.</p>
        </article>

        <article className="preset reveal" style={{ "--delay": ".15s" } as CSSProperties}>
          <div className="preset-head">
            <div>
              <h3>Dynamic Solo</h3>
              <div className="preset-id">dynamic_solo</div>
            </div>
            <span className="preset-tag">Expressive</span>
          </div>
          <div className="knob-wrap">
            <div className="knob" style={{ "--rot": "-58deg" } as CSSProperties} aria-hidden="true"></div>
            <div className="knob-side">
              <div className="knob-label">Noise gate</div>
              <div className="knob-value">0.08 <small>min amp</small></div>
            </div>
          </div>
          <div className="spec-grid">
            <div className="spec-cell"><span>BPM scale</span><b>×1.00</b></div>
            <div className="spec-cell"><span>HOPO</span><b>80 ticks</b></div>
            <div className="spec-cell"><span>Chord fusion</span><b>30 ms</b></div>
            <div className="spec-cell"><span>Max frets</span><b>2</b></div>
          </div>
          <p className="preset-note">Expanded HOPO threshold for sweep picking, fast runs and virtuosic lead passages.</p>
        </article>
      </div>
    </div>
  </section>
  );
}
