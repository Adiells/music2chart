import type { Language } from '../../lib/language';

const PRESETS = [
  { id: 'the_best', name: 'The Best', tag: { en: 'DEV PICK', pt: 'RECOMENDADO' }, gate: '0.41', bpm: '×0.65', fusion: '40 ms', en: 'High-precision, ghost-note-free charting with a comfortable scroll speed. The safest first pass.', pt: 'Charting de alta precisão, sem notas fantasma e com velocidade confortável. A opção mais segura.' },
  { id: 'standard', name: 'Standard', tag: { en: 'BALANCED', pt: 'BALANCEADO' }, gate: '0.10', bpm: '×1.00', fusion: '35 ms', en: 'Balanced 5-fret mapping with classic HOPO logic.', pt: 'Mapeamento balanceado em 5 fretes com lógica clássica de HOPO.' },
  { id: 'strict_rhythm', name: 'Strict Rhythm', tag: { en: 'RHYTHM', pt: 'RITMO' }, gate: '0.20', bpm: '×1.00', fusion: '40 ms', en: 'Tight quantization and a solid chord foundation.', pt: 'Quantização rígida e base sólida de acordes.' },
  { id: 'dynamic_solo', name: 'Dynamic Solo', tag: { en: 'EXPRESSIVE', pt: 'EXPRESSIVO' }, gate: '0.08', bpm: '×1.00', fusion: '30 ms', en: 'Expressive lead mapping with expanded HOPO threshold and rapid runs.', pt: 'Mapeamento expressivo de solo com limite HOPO expandido e escalas rápidas.' },
] as const;

export function LandingPresets({ language = 'en' }: { language?: Language }) {
  const pt = language === 'pt-BR';
  const lang = pt ? 'pt' : 'en';
  return (
    <section id="presets" className="scroll-mt-16 border-t border-hw-border bg-chassis py-16">
      <div className="mx-auto max-w-6xl px-4">
        <div className="silk-wide mb-2">03 // Presets</div>
        <h2 className="font-grotesk text-3xl font-bold text-silk sm:text-4xl">
          {pt ? 'Calibrado como hardware. Não como palpite.' : 'Tuned like hardware. Not guesswork.'}
        </h2>
        <div className="mt-8 grid gap-3 sm:grid-cols-2">
          {PRESETS.map((p) => (
            <article key={p.id} className="border border-hw-border bg-module p-4 shadow-bevel">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-grotesk text-base font-semibold text-silk">{p.name}</h3>
                  <div className="font-mono text-[10px] text-silk-dim">{p.id}</div>
                </div>
                <span className="border border-hw-screw bg-chassis px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-silk text-starpower">{p.tag[lang]}</span>
              </div>
              <div className="mt-3 grid grid-cols-3 gap-2 font-mono text-[10px] uppercase tracking-silk">
                <div className="border border-hw-border bg-chassis p-2"><div className="text-silk-dim">Noise gate</div><div className="text-silk">{p.gate}</div></div>
                <div className="border border-hw-border bg-chassis p-2"><div className="text-silk-dim">BPM</div><div className="text-silk">{p.bpm}</div></div>
                <div className="border border-hw-border bg-chassis p-2"><div className="text-silk-dim">{pt ? 'Fusão' : 'Fusion'}</div><div className="text-silk">{p.fusion}</div></div>
              </div>
              <p className="mt-3 text-xs leading-relaxed text-silk-dim">{p[lang]}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
