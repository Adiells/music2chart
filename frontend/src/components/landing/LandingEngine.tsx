import type { Language } from '../../lib/language';

const FEATURES = [
  { en: ['Distortion harmonics, removed.', 'Naive converters emit walls of ghost notes. A noise gate and harmonic suppression keep only what a player would play.'], pt: ['Harmônicos de distorção, removidos.', 'Conversores ingênuos geram paredes de notas fantasma. Noise gate e supressão harmônica mantêm só o que um jogador tocaria.'] },
  { en: ['Chord fusion window', 'Near-simultaneous notes (35–40 ms) fuse into authentic chords and power chords.'], pt: ['Janela de fusão de acordes', 'Notas quase simultâneas (35–40 ms) viram acordes e power chords autênticos.'] },
  { en: ['Natural HOPO engine', 'Hammer-ons and pull-offs are derived from pitch distance and timing, like a human charter.'], pt: ['Motor de HOPO natural', 'Hammer-ons e pull-offs derivados da distância de tom e tempo, como um charter humano.'] },
  { en: ['Byte-perfect .sng output.', 'Export .sng, .chart or a full .zip that loads straight into Clone Hero and YARG.'], pt: ['Saída .sng perfeita.', 'Exporte .sng, .chart ou um .zip completo que carrega direto no Clone Hero e YARG.'] },
  { en: ['Watch every stage, live.', 'Real-time telemetry shows each pipeline stage as it runs.'], pt: ['Veja cada etapa, ao vivo.', 'Telemetria em tempo real mostra cada etapa do pipeline enquanto executa.'] },
  { en: ['Safe by default', '100% free, MIT licensed, CPU-friendly and self-hostable.'], pt: ['Seguro por padrão', '100% gratuito, licença MIT, roda em CPU e pode ser hospedado por você.'] },
];

export function LandingEngine({ language = 'en' }: { language?: Language }) {
  const pt = language === 'pt-BR';
  return (
    <section id="engine" className="scroll-mt-16 border-t border-hw-border bg-panel py-16">
      <div className="mx-auto max-w-6xl px-4">
        <div className="silk-wide mb-2">02 // {pt ? 'Engenharia' : 'Engineering'}</div>
        <h2 className="font-grotesk text-3xl font-bold text-silk sm:text-4xl">
          {pt ? 'Feito para o que outros conversores ignoram.' : 'Built for the parts other converters skip.'}
        </h2>
        <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => {
            const [title, body] = pt ? f.pt : f.en;
            return (
              <article key={f.en[0]} className="border border-hw-border bg-module p-4 shadow-bevel">
                <h3 className="font-grotesk text-base font-semibold text-silk">{title}</h3>
                <p className="mt-2 text-xs leading-relaxed text-silk-dim">{body}</p>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
