// Generated from landing-preview.html (markup parity with the reference).
import type { CSSProperties } from 'react';
import type { Language } from '../../lib/language';

export function LandingFooter({ language = 'en', onOpenStudio }: { language?: Language; onOpenStudio: () => void }) {
  const pt = language === 'pt-BR';
  return (
<footer className="site-footer">
  <div className="wrap">
    <div className="footer-top">
      <div className="footer-brand">
        <a className="brand" href="#top">
          <span className="brand-mark" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></span>
          <span className="brand-name">Music2Chart</span>
        </a>
        <p>Automated high-fidelity audio-to-chart workstation for Clone Hero and YARG. Neural stems, 192 PPQ mapping, 3D preview, byte-perfect exports.</p>
      </div>
      <div className="footer-col">
        <h4>{pt ? "Produto" : "Product"}</h4>
        <button type="button" className="" onClick={onOpenStudio}>Studio</button>
        <a href="#pipeline">Pipeline</a>
        <a href="#presets">Presets</a>
        <a href="#selfhost">Self-host</a>
      </div>
      <div className="footer-col">
        <h4>{pt ? "Recursos" : "Resources"}</h4>
        <a href="https://github.com/Adiells/music2chart" target="_blank" rel="noopener" className="ext">GitHub</a>
        <a href="https://github.com/Adiells/music2chart/blob/main/docs/API.md" target="_blank" rel="noopener" className="ext">REST API</a>
        <a href="https://github.com/Adiells/music2chart/blob/main/docs/ARCHITECTURE.md" target="_blank" rel="noopener" className="ext">Architecture</a>
        <a href="https://github.com/Adiells/music2chart/blob/main/CONTRIBUTING.md" target="_blank" rel="noopener" className="ext">Contributing</a>
      </div>
      <div className="footer-col">
        <h4>{pt ? "Comunidade" : "Community"}</h4>
        <a href="https://github.com/sponsors/Adiells" target="_blank" rel="noopener" className="ext">Sponsor</a>
        <a href="https://github.com/Adiells/music2chart/blob/main/CODE_OF_CONDUCT.md" target="_blank" rel="noopener" className="ext">Code of Conduct</a>
        <a href="https://github.com/Adiells/music2chart/blob/main/SECURITY.md" target="_blank" rel="noopener" className="ext">Security</a>
        <span>Interface in EN / PT-BR</span>
      </div>
    </div>
    <div className="frets" aria-hidden="true" style={{ marginTop: "22px" } as CSSProperties}>
        <i style={{ "--c": "var(--green)" } as CSSProperties}></i><i style={{ "--c": "var(--red)" } as CSSProperties}></i><i style={{ "--c": "var(--yellow)" } as CSSProperties}></i><i style={{ "--c": "var(--blue)" } as CSSProperties}></i><i style={{ "--c": "var(--orange)" } as CSSProperties}></i>
      </div>
      <div className="footer-bottom">
      <span>MIT © 2026 Adiel Emilson</span>
      <span className="status"><i className="led on" style={{ color: "var(--green)" } as CSSProperties}></i> {pt ? "Todos os sistemas operando" : "All systems nominal"}</span>
      <span>{pt ? "Feito para Clone Hero e YARG" : "Built for Clone Hero & YARG"}</span>
    </div>
  </div>
</footer>
  );
}
