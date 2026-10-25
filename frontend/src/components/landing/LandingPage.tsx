import { useLanguage } from '../../lib/language';
import { cn } from '../../lib/utils';
import { LandingEngine } from './LandingEngine';
import { LandingFooter } from './LandingFooter';
import { LandingHeroHighway } from './LandingHeroHighway';
import { LandingPipeline } from './LandingPipeline';
import { LandingPresets } from './LandingPresets';

export interface LandingPageProps {
  onOpenStudio: () => void;
}

export function LandingPage({ onOpenStudio }: LandingPageProps) {
  const [language, setLanguage] = useLanguage();
  const pt = language === 'pt-BR';

  return (
    <div className="min-h-screen bg-chassis text-silk">
      <header className="fixed inset-x-0 top-0 z-50 border-b border-hw-border bg-chassis/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-4 px-4">
          <a href="#top" className="font-grotesk text-base font-bold tracking-tight text-silk">
            Music2Chart <span className="hidden font-mono text-[10px] font-normal uppercase tracking-silk text-silk-dim sm:inline">AI Chart Studio</span>
          </a>
          <nav className="hidden items-center gap-5 font-mono text-[11px] uppercase tracking-silk text-silk-dim md:flex" aria-label="Primary">
            <a href="#pipeline" className="hover:text-silk">Pipeline</a>
            <a href="#engine" className="hover:text-silk">{pt ? 'Motor' : 'Engine'}</a>
            <a href="#presets" className="hover:text-silk">Presets</a>
          </nav>
          <div className="flex items-center gap-3">
            <div className="flex border border-hw-border font-mono text-[10px] uppercase tracking-silk" role="group" aria-label="Language">
              {(['en', 'pt-BR'] as const).map((l) => (
                <button
                  key={l}
                  type="button"
                  onClick={() => setLanguage(l)}
                  aria-pressed={language === l}
                  className={cn('px-2 py-1', language === l ? 'bg-fret-green text-chassis' : 'text-silk-dim hover:text-silk')}
                >
                  {l === 'en' ? 'EN' : 'PT-BR'}
                </button>
              ))}
            </div>
            <button
              type="button"
              onClick={onOpenStudio}
              className="border border-fret-green bg-fret-green px-3 py-1.5 font-mono text-[11px] font-semibold uppercase tracking-silk text-chassis hover:bg-transparent hover:text-fret-green"
            >
              {pt ? 'Abrir Studio' : 'Open Studio'}
            </button>
          </div>
        </div>
      </header>

      <main id="top">
        <section className="px-4 pb-16 pt-24">
          <div className="mx-auto grid max-w-6xl items-center gap-10 lg:grid-cols-2">
            <div>
              <div className="silk-wide mb-4">{pt ? 'Estação Áudio → Chart' : 'Audio → Chart Workstation'} / v1.0 / MIT</div>
              <h1 className="font-grotesk text-4xl font-bold leading-tight sm:text-5xl">
                {pt ? 'Qualquer música. Uma chart de Clone Hero ' : 'Any track. One '}
                <span className="text-fret-green">{pt ? 'nível campeonato.' : 'tournament-grade'}</span>
                {pt ? '' : ' Clone Hero chart.'}
              </h1>
              <p className="mt-5 max-w-xl text-sm leading-relaxed text-silk-dim">
                {pt
                  ? 'Envie um MP3, WAV, FLAC ou OGG. O Music2Chart isola a guitarra com Demucs v4, transcreve com Spotify Basic Pitch e mapeia com heurísticas de game design — depois você confere cada nota na highway 3D antes de exportar .sng ou .chart.'
                  : 'Drop in an MP3, WAV, FLAC or OGG. Music2Chart isolates the guitar with Demucs v4, transcribes it with Spotify Basic Pitch, and maps it with game-design heuristics — then preview every note on a 3D highway before exporting .sng or .chart.'}
              </p>
              <div className="mt-7 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={onOpenStudio}
                  className="border border-fret-green bg-fret-green px-5 py-2.5 font-mono text-xs font-semibold uppercase tracking-silk text-chassis hover:bg-transparent hover:text-fret-green"
                >
                  {pt ? 'Abrir Studio →' : 'Open Studio →'}
                </button>
                <a href="#pipeline" className="border border-hw-border px-5 py-2.5 font-mono text-xs uppercase tracking-silk text-silk hover:border-silk">
                  {pt ? 'Como funciona' : 'How it works'}
                </a>
              </div>
            </div>
            <LandingHeroHighway language={language} />
          </div>
        </section>

        <LandingPipeline language={language} />
        <LandingEngine language={language} />
        <LandingPresets language={language} />
      </main>

      <LandingFooter language={language} onOpenStudio={onOpenStudio} />
    </div>
  );
}
