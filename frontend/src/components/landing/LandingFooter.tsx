import type { Language } from '../../lib/language';

const GH = 'https://github.com/Adiells/music2chart';

export function LandingFooter({ language = 'en', onOpenStudio }: { language?: Language; onOpenStudio: () => void }) {
  const pt = language === 'pt-BR';
  const ext = (href: string, label: string) => (
    <a href={href} target="_blank" rel="noopener noreferrer" className="text-silk-dim hover:text-silk">{label} ↗</a>
  );
  return (
    <footer className="border-t border-hw-border bg-panel py-10">
      <div className="mx-auto max-w-6xl px-4">
        <div className="grid gap-8 text-xs sm:grid-cols-4">
          <div className="sm:col-span-2">
            <div className="font-grotesk text-lg font-bold text-silk">Music2Chart</div>
            <p className="mt-2 max-w-sm text-silk-dim">
              {pt
                ? 'Estação automatizada de áudio para chart para Clone Hero e YARG. Stems neurais, mapeamento 192 PPQ, prévia 3D e exportações perfeitas.'
                : 'Automated high-fidelity audio-to-chart workstation for Clone Hero and YARG. Neural stems, 192 PPQ mapping, 3D preview, byte-perfect exports.'}
            </p>
          </div>
          <div className="flex flex-col gap-2">
            <span className="silk-wide">{pt ? 'Produto' : 'Product'}</span>
            <button type="button" onClick={onOpenStudio} className="text-left text-silk-dim hover:text-silk">Studio</button>
            <a href="#pipeline" className="text-silk-dim hover:text-silk">Pipeline</a>
            <a href="#presets" className="text-silk-dim hover:text-silk">Presets</a>
          </div>
          <div className="flex flex-col gap-2">
            <span className="silk-wide">{pt ? 'Recursos' : 'Resources'}</span>
            {ext(GH, 'GitHub')}
            {ext(`${GH}/blob/main/docs/API.md`, 'REST API')}
            {ext('https://github.com/sponsors/Adiells', 'Sponsor')}
          </div>
        </div>
        <div className="mt-8 flex flex-wrap justify-between gap-2 border-t border-hw-border pt-4 font-mono text-[10px] uppercase tracking-silk text-silk-dim">
          <span>MIT © 2026 Adiel Emilson</span>
          <span>{pt ? 'Feito para Clone Hero e YARG' : 'Built for Clone Hero & YARG'}</span>
        </div>
      </div>
    </footer>
  );
}
