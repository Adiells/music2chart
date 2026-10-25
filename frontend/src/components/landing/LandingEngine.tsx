// Generated from landing-preview.html (markup parity with the reference).
import type { CSSProperties } from 'react';
import type { Language } from '../../lib/language';

export function LandingEngine({ language = 'en' }: { language?: Language }) {
  const pt = language === 'pt-BR';
  return (
<section className="section section-alt" id="engine">
    <div className="wrap">
      <div className="sec-head">
        <div className="sec-head-copy reveal">
          <div className="sec-eyebrow"><span className="idx">02</span> {pt ? "Engenharia" : "Engineering"}</div>
          <h2>{pt ? <>Feito para as partes<br />que outros conversores ignoram.</> : <>Built for the parts<br />other converters skip.</>}</h2>
          <p className="sec-lead">
            Naive audio-to-chart tools emit walls of ghost notes. Music2Chart treats charting
            as a game-design problem — with the signal processing and ergonomics to match.
          </p>
        </div>
        <div className="sec-aside reveal" style={{ "--delay": ".08s" } as CSSProperties}>
          <b>Design targets</b>
          Playable over literal<br />
          Ergonomics over density<br />
          Deterministic over random
        </div>
      </div>

      <div className="bento">
        <article className="feature span-2 reveal">
          <div className="feature-head">
            <span className="feature-kicker"><i className="led on" style={{ color: "var(--red)" } as CSSProperties}></i> DSP-FILT / overtone guard</span>
            <span className="tag">Before mapping</span>
          </div>
          <h3>Distortion harmonics, removed.</h3>
          <p>High-gain amps ring at +12 and +19 semitones. The spectral filter identifies and deletes those artifacts before a single fret is assigned.</p>
          <div className="feature-visual">
            <div className="spectrum" aria-hidden="true" style={{ "--x": "68%", "--h": "88%" } as CSSProperties}>
              <span className="filtered-tag">Filtered</span>
              <i style={{ "--h": "34%" } as CSSProperties}></i><i style={{ "--h": "58%" } as CSSProperties}></i><i style={{ "--h": "96%" } as CSSProperties}></i><i style={{ "--h": "44%" } as CSSProperties}></i>
              <i style={{ "--h": "28%" } as CSSProperties}></i><i style={{ "--h": "72%" } as CSSProperties}></i><i style={{ "--h": "22%" } as CSSProperties}></i><i className="hot" style={{ "--h": "88%" } as CSSProperties}></i>
              <i style={{ "--h": "18%" } as CSSProperties}></i><i style={{ "--h": "12%" } as CSSProperties}></i><i className="hot" style={{ "--h": "54%" } as CSSProperties}></i><i style={{ "--h": "9%" } as CSSProperties}></i>
              <span className="spectrum-mark" style={{ "--x": "62.5%", "--h": "88%" } as CSSProperties}>+12 st <s>×</s></span>
              <span className="spectrum-mark" style={{ "--x": "87.5%", "--h": "54%" } as CSSProperties}>+19 st <s>×</s></span>
              <div className="axis"><span>Fundamental</span><span>2nd harmonic</span><span>3rd harmonic</span><span>Noise floor</span></div>
            </div>
          </div>
        </article>

        <article className="feature reveal" style={{ "--delay": ".05s" } as CSSProperties}>
          <div className="feature-head">
            <span className="feature-kicker"><i className="led on" style={{ color: "var(--yellow)" } as CSSProperties}></i> MAP / fusion</span>
          </div>
          <h3>Chord fusion window</h3>
          <p>Pick drags across six strings land 10–30 ms apart. Onsets inside 35–40 ms fuse into one ergonomic chord.</p>
          <div className="feature-visual">
            <div className="fusion" aria-hidden="true">
              <div className="fusion-in">
                <span className="fusion-window" style={{ "--a": "8%", "--b": "26%" } as CSSProperties}></span>
                <span className="fdot" style={{ "--x": "12%", "--y": "-7px" } as CSSProperties}></span>
                <span className="fdot" style={{ "--x": "26%", "--y": "5px" } as CSSProperties}></span>
                <span className="fdot" style={{ "--x": "41%", "--y": "-3px" } as CSSProperties}></span>
                <span className="fdot" style={{ "--x": "57%", "--y": "8px" } as CSSProperties}></span>
                <span className="fdot" style={{ "--x": "72%", "--y": "0" } as CSSProperties}></span>
              </div>
              <div className="fusion-arrow"><b>40 ms</b>window<br />→</div>
              <div className="fusion-out">
                <span className="fbar g"></span><span className="fbar r"></span><span className="fbar y"></span>
              </div>
            </div>
          </div>
        </article>

        <article className="feature reveal">
          <div className="feature-head">
            <span className="feature-kicker"><i className="led on" style={{ color: "var(--blue)" } as CSSProperties}></i> MAP / hopo</span>
          </div>
          <h3>Natural HOPO engine</h3>
          <p>Fast runs anchor on one strum, then chain <code style={{ color: "var(--power)", fontSize: "10px", whiteSpace: "nowrap" } as CSSProperties}>N 5 0</code> forcers. Same-fret repeats re-strum automatically.</p>
          <div className="feature-visual">
            <div className="hopo" aria-hidden="true">
              <span className="hopo-tag">N 5 0</span>
              <span className="hopo-note strum" style={{ "--c": "var(--green)" } as CSSProperties}></span>
              <span className="hopo-link"></span>
              <span className="hopo-note" style={{ "--c": "var(--red)" } as CSSProperties}></span>
              <span className="hopo-link"></span>
              <span className="hopo-note" style={{ "--c": "var(--yellow)" } as CSSProperties}></span>
              <span className="hopo-link"></span>
              <span className="hopo-note" style={{ "--c": "var(--blue)" } as CSSProperties}></span>
              <span className="hopo-link"></span>
              <span className="hopo-note" style={{ "--c": "var(--orange)" } as CSSProperties}></span>
              <span className="hopo-legend"><span>▼ Strum</span><span>48–65 tick HOPO window</span></span>
            </div>
          </div>
        </article>

        <article className="feature span-2 reveal" style={{ "--delay": ".05s" } as CSSProperties}>
          <div className="feature-head">
            <span className="feature-kicker"><i className="led on" style={{ color: "var(--power)" } as CSSProperties}></i> PKG / container</span>
            <span className="tag">SongBinary v1</span>
          </div>
          <h3>Byte-perfect .sng output.</h3>
          <p>Little-endian metadata, a file index and a 16-byte pseudo-random XOR stream mask. Drop it straight into <code style={{ color: "var(--neutral)", fontSize: "10px" } as CSSProperties}>Clone Hero/Songs/</code>.</p>
          <div className="feature-visual">
            <pre className="hexdump" aria-label="Example .sng container hex dump"><code><span className="hex-off">{"0000"}</span>{" 53 4E 47 00 "}<span className="hex-hl">{"01 00 00 00"}</span>{" 4D 32 43 2D 50 4B 47 "}<span className="hex-ascii">{"SNG.....M2C-PKG"}</span>{"\n"}<span className="hex-off">{"0010"}</span>{" 0C 00 00 00 6E 6F 74 65 73 2E 63 68 61 72 74 00 "}<span className="hex-ascii">{"....notes.chart."}</span>{"\n"}<span className="hex-off">{"0020"}</span>{" 0B 00 00 00 73 6F 6E 67 2E 69 6E 69 00 00 00 00 "}<span className="hex-ascii">{"....song.ini...."}</span>{"\n"}<span className="hex-off">{"0030"}</span>{" "}<span className="hex-key">{"A7 3F 91 0C 5E D2 48 B6 17 83 FA 2D 6C E1 09 74"}</span>{" "}<span className="hex-ascii">{"..?.^H....-l..t"}</span>{"\n"}<span className="hex-off">{"0040"}</span>{" "}<span className="hex-key">{"E4 52 08 BB 71 CD 36 9A 4F 12 D8 25 87 EF 63 A0"}</span>{" "}<span className="hex-ascii">{".R..q6.O..%.c."}</span></code></pre>
            <div className="hex-cap"><span>xor_key[i % 16] ^ (i & 0xFF)</span><span>Little-endian · v1</span></div>
          </div>
        </article>

        <article className="feature span-2 reveal">
          <div className="feature-head">
            <span className="feature-kicker"><i className="led on" style={{ color: "var(--green)" } as CSSProperties}></i> API / telemetry</span>
            <span className="tag">SSE</span>
          </div>
          <h3>Watch every stage, live.</h3>
          <p>The FastAPI backend streams progress percentages and stage transitions over Server-Sent Events — no refresh, no polling guesswork.</p>
          <div className="feature-visual">
            <div className="telemetry" aria-hidden="true">
              <div className="tm-top"><span>Task <b>8f484ddf</b></span><span>64%</span></div>
              <div className="tm-bar"><i></i></div>
              <div className="tm-stages">
                <span className="done"></span><span className="done"></span><span className="done"></span>
                <span className="now"></span><span></span><span></span>
              </div>
              <div className="tm-line"><span className="ok">✔</span> Demucs stem separation <b>complete</b></div>
              <div className="tm-line"><span className="ok">✔</span> Tempo map · <b>192 PPQ</b></div>
              <div className="tm-line"><span className="run">▶</span> Harmonic filtering <b>running</b> · 0.64</div>
            </div>
          </div>
        </article>

        <article className="feature reveal" style={{ "--delay": ".05s" } as CSSProperties}>
          <div className="feature-head">
            <span className="feature-kicker"><i className="led on" style={{ color: "var(--yellow)" } as CSSProperties}></i> OPS / rails</span>
          </div>
          <h3>Safe by default</h3>
          <p>Caps, validation and garbage collection ship in the container — not bolted on later.</p>
          <ul className="safety">
            <li><span>Rate limit / IP</span><b>20 charts / hour</b></li>
            <li><span>Concurrent tasks</span><b>1 per IP</b></li>
            <li><span>Upload validation</span><b>Magic bytes</b></li>
            <li><span>Cache retention</span><b>2 h TTL + auto-GC</b></li>
          </ul>
        </article>
      </div>
    </div>
  </section>
  );
}
