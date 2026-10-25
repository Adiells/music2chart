// Generated from landing-preview.html (markup parity with the reference).
import type { CSSProperties } from 'react';
import type { Language } from '../../lib/language';

export function LandingSelfHost({ language = 'en', onOpenStudio }: { language?: Language; onOpenStudio: () => void }) {
  const pt = language === 'pt-BR';
  return (
<section className="section" id="selfhost">
    <div className="wrap">
      <div className="sec-head">
        <div className="sec-head-copy reveal">
          <div className="sec-eyebrow"><span className="idx">05</span> {pt ? "Deploy e entrega" : "Deploy & deliver"}</div>
          <h2>{pt ? <>Rode em qualquer lugar.<br />Entregue jogável.</> : <>Run it anywhere.<br />Ship it playable.</>}</h2>
          <p className="sec-lead">
            The public demo is free forever. Want your own GPU, your own queue, your own
            storage? The whole stack is containerized.
          </p>
        </div>
      </div>

      <div className="deploy">
        <div className="deploy-panel reveal">
          <div className="mono-label" style={{ marginBottom: "12px" } as CSSProperties}>Self-host in one command</div>
          <h3>Your metal. Your queue.</h3>
          <p>FastAPI + React 19 + PyTorch/Demucs in a single Compose stack. GPU if you have it, CPU fallback if you don't.</p>

          <div className="terminal">
            <div className="terminal-bar">
              <span className="dots"><i></i><i></i><i></i></span>
              <span>bash — music2chart</span>
              <button className="copy-btn" type="button" data-copy="term">Copy</button>
            </div>
            <pre id="term"><span className="c">{"# clone + launch the full stack"}</span>{"\n"}<span className="p">{"$"}</span>{" git clone https://github.com/Adiells/music2chart.git\n"}<span className="p">{"$"}</span>{" cd music2chart\n"}<span className="p">{"$"}</span>{" docker compose up --build -d\n\n"}<span className="ok">{"✔"}</span>{" api        "}<span className="out">{"http://localhost:8000"}</span>{"\n"}<span className="ok">{"✔"}</span>{" frontend   "}<span className="out">{"http://localhost:5173"}</span>{"\n"}<span className="ok">{"✔"}</span>{" demucs     "}<span className="out">{"htdemucs loaded"}</span>{"\n"}<span className="p">{"$"}</span>{" "}<span className="s">{"open"}</span>{" http://localhost:5173 "}<span className="c">{"# drop a song"}</span></pre>
          </div>

          <div className="mono-label" style={{ margin: "18px 0 10px" } as CSSProperties}>{pt ? 'Requisitos técnicos' : 'Technical requirements'}</div>
          <div className="deploy-foot">
            <span><i className="led" style={{ color: "var(--green)" } as CSSProperties}></i> Python 3.11+</span>
            <span><i className="led" style={{ color: "var(--yellow)" } as CSSProperties}></i> GPU / CUDA</span>
            <span><i className="led" style={{ color: "var(--blue)" } as CSSProperties}></i> Apple Silicon MPS</span>
            <span><i className="led" style={{ color: "var(--orange)" } as CSSProperties}></i> {pt ? 'Fallback em CPU' : 'CPU fallback'}</span>
          </div>
          <div className="deploy-foot">
            <span><i className="led" style={{ color: "var(--green)" } as CSSProperties}></i> Docker Compose</span>
            <span><i className="led" style={{ color: "var(--blue)" } as CSSProperties}></i> FastAPI</span>
            <span><i className="led" style={{ color: "var(--yellow)" } as CSSProperties}></i> PyTorch</span>
            <span><i className="led" style={{ color: "var(--power)" } as CSSProperties}></i> React 19</span>
          </div>
        </div>

        <div className="deploy-panel reveal" style={{ "--delay": ".06s" } as CSSProperties}>
          <div className="mono-label" style={{ marginBottom: "12px" } as CSSProperties}>Export bay</div>
          <h3>Three ways out.</h3>
          <p>Every artifact is generated from the same 192 PPQ chart. No re-processing, no surprises.</p>

          <div className="exports">
            <button type="button" className="export-row" onClick={onOpenStudio}>
              <span className="export-ext" style={{ "--c": "var(--power)" } as CSSProperties}>.sng</span>
              <span className="export-body"><b>SongBinary container</b><span>v1 · metadata + XOR-masked streams · Clone Hero & YARG</span></span>
              <span className="export-go" aria-hidden="true">→</span>
            </button>
            <button type="button" className="export-row" onClick={onOpenStudio}>
              <span className="export-ext" style={{ "--c": "var(--yellow)" } as CSSProperties}>.chart</span>
              <span className="export-body"><b>notes.chart</b><span>Strict UTF-8 text · SyncTrack · ExpertSingle</span></span>
              <span className="export-go" aria-hidden="true">→</span>
            </button>
            <button type="button" className="export-row" onClick={onOpenStudio}>
              <span className="export-ext" style={{ "--c": "var(--green)" } as CSSProperties}>.zip</span>
              <span className="export-body"><b>Complete song folder</b><span>notes.chart + song.ini + song.ogg · drop-in ready</span></span>
              <span className="export-go" aria-hidden="true">→</span>
            </button>
          </div>

          <div className="deploy-foot">
            <span><i className="led" style={{ color: "var(--green)" } as CSSProperties}></i> No account</span>
            <span><i className="led" style={{ color: "var(--yellow)" } as CSSProperties}></i> No watermark</span>
            <span><i className="led" style={{ color: "var(--power)" } as CSSProperties}></i> No paywall</span>
          </div>
        </div>
      </div>

      <div className="sponsor reveal" style={{ marginTop: "12px" } as CSSProperties}>
        <div className="sponsor-copy">
          <div className="sec-eyebrow" style={{ marginBottom: "12px" } as CSSProperties}><span className="led blink" style={{ color: "var(--orange)" } as CSSProperties}></span> Infrastructure fund</div>
          <h3>100% free. Forever MIT. Running on CPU.</h3>
          <p>
            The public demo runs on Cloud Run CPU instances, so a full track takes ~90 seconds.
            Sponsors fund the jump to <b>dedicated NVIDIA GPUs</b> — targeting sub-15-second charts,
            no cold starts and no concurrency queue.
          </p>
        </div>
        <div className="sponsor-actions">
          <a className="btn btn-sponsor" href="https://github.com/sponsors/Adiells" target="_blank" rel="noopener">
            <span aria-hidden="true">♥</span> Sponsor the GPU
          </a>
          <a className="btn btn-ghost btn-sm" href="https://github.com/Adiells/music2chart" target="_blank" rel="noopener">View source</a>
        </div>
      </div>
    </div>
  </section>
  );
}
