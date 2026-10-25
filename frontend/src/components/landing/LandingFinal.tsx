// Generated from landing-preview.html (markup parity with the reference).
import type { CSSProperties } from 'react';
import type { Language } from '../../lib/language';

export function LandingFinal({ language = 'en', onOpenStudio }: { language?: Language; onOpenStudio: () => void }) {
  const pt = language === 'pt-BR';
  return (
<section className="final">
    <div className="wrap final-inner">
      <div className="mono-label reveal"><span className="led on" style={{ color: "var(--green)" } as CSSProperties}></span>  {pt ? "Pronto quando você estiver" : "Ready when you are"}</div>
      <h2 className="reveal" style={{ "--delay": ".05s" } as CSSProperties}>{pt ? <>Solte a agulha.<br /><em>A chart é com a gente.</em></> : <>Drop the needle.<br /><em>Chart the rest.</em></>}</h2>
      <p className="reveal" style={{ "--delay": ".1s" } as CSSProperties}>
        Free, open source and built for the rhythm-game community.
        Bring a song — leave with something playable.
      </p>
      <div className="final-actions reveal" style={{ "--delay": ".15s" } as CSSProperties}>
        <button type="button" className="btn btn-primary" onClick={onOpenStudio}>
          {pt ? "Abrir Studio" : "Open the Studio"} <span className="arrow" aria-hidden="true">→</span>
        </button>
        <a className="btn btn-ghost" href="https://github.com/Adiells/music2chart" target="_blank" rel="noopener">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" /></svg>
          {pt ? "Favoritar no GitHub" : "Star on GitHub"}
        </a>
      </div>
      <div className="frets reveal" style={{ "--delay": ".2s" } as CSSProperties} aria-hidden="true">
        <i style={{ "--c": "var(--green)" } as CSSProperties}></i><i style={{ "--c": "var(--red)" } as CSSProperties}></i><i style={{ "--c": "var(--yellow)" } as CSSProperties}></i><i style={{ "--c": "var(--blue)" } as CSSProperties}></i><i style={{ "--c": "var(--orange)" } as CSSProperties}></i>
      </div>
    </div>
  </section>
  );
}
