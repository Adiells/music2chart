// Generated from landing-preview.html (markup parity with the reference).
import type { CSSProperties } from 'react';
import type { Language } from '../../lib/language';

export function LandingWorkflow({ language = 'en' }: { language?: Language }) {
  const pt = language === 'pt-BR';
  return (
<section className="section section-alt" id="workflow">
    <div className="wrap">
      <div className="sec-head">
        <div className="sec-head-copy reveal">
          <div className="sec-eyebrow"><span className="idx">04</span> {pt ? "Fluxo de trabalho" : "Workflow"}</div>
          <h2>{pt ? <>Quatro passos do<br />MP3 ao jogável.</> : <>Four moves from<br />MP3 to playable.</>}</h2>
          <p className="sec-lead">
            A tactile studio rack, not a form. Drop, tune, inspect, export — the whole loop
            stays in the browser.
          </p>
        </div>
      </div>

      <div className="flow">
        <article className="flow-step reveal">
          <div className="flow-num">01</div>
          <h3>Ingest</h3>
          <p>Drag in a track. Format is inspected client-side, magic bytes are verified, metadata is inferred.</p>
          <div className="flow-meta">MP3 · WAV · FLAC · OGG</div>
        </article>
        <article className="flow-step reveal" style={{ "--delay": ".05s" } as CSSProperties}>
          <div className="flow-num">02</div>
          <h3>Calibrate</h3>
          <p>Pick a preset or turn the knobs: noise gate, BPM scale, HOPO sensitivity, chord fusion.</p>
          <div className="flow-meta">Presets + rotary controls</div>
        </article>
        <article className="flow-step reveal" style={{ "--delay": ".1s" } as CSSProperties}>
          <div className="flow-num">03</div>
          <h3>Preview</h3>
          <p>Scrub the audio and watch the generated notes run down a synchronized 3D highway.</p>
          <div className="flow-meta">Three.js · seek · strike bar</div>
        </article>
        <article className="flow-step reveal" style={{ "--delay": ".15s" } as CSSProperties}>
          <div className="flow-num">04</div>
          <h3>Export</h3>
          <p>Inspect NPS density and note stats, then download .sng, notes.chart or a full song ZIP.</p>
          <div className="flow-meta">Clone Hero & YARG ready</div>
        </article>
      </div>

      <div className="compat reveal" aria-label={pt ? 'Matriz de formatos suportados' : 'Supported formats matrix'}>
        <table>
          <thead>
            <tr>
              <th>{pt ? 'Formato' : 'Format'}</th>
              <th>{pt ? 'Exportação Music2Chart' : 'Music2Chart export'}</th>
              <th>Clone Hero</th>
              <th>YARG</th>
              <th>Guitar Hero</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="fmt">.chart</td>
              <td className="ok">● {pt ? 'Disponível' : 'Available'}</td>
              <td className="ok">● {pt ? 'Nativo' : 'Native'}</td>
              <td className="ok">● {pt ? 'Nativo' : 'Native'}</td>
              <td className="part">◐ {pt ? 'Via conversor' : 'Via converter'}</td>
            </tr>
            <tr>
              <td className="fmt">.mid</td>
              <td className="part">◐ {pt ? 'Roadmap' : 'Roadmap'}</td>
              <td className="ok">● {pt ? 'Nativo' : 'Native'}</td>
              <td className="ok">● {pt ? 'Nativo' : 'Native'}</td>
              <td className="part">◐ {pt ? 'Via conversor' : 'Via converter'}</td>
            </tr>
            <tr>
              <td className="fmt">.sng</td>
              <td className="ok">● {pt ? 'Disponível' : 'Available'}</td>
              <td className="ok">● {pt ? 'Nativo' : 'Native'}</td>
              <td className="ok">● {pt ? 'Nativo' : 'Native'}</td>
              <td className="no">○ {pt ? 'Não suportado' : 'Unsupported'}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
  );
}
