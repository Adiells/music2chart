import { cn } from '../../lib/utils';
import type { LedColorName } from '../../theme/tokens';
import { PushButton } from '../controls/PushButton';
import { LedIndicator } from '../rack/LedIndicator';
import { ModulePanel } from '../rack/ModulePanel';
import type { Language } from '../../lib/language';

export interface AboutPageProps {
  language?: Language;
  onReturnToWorkstation?: () => void;
  className?: string;
}

interface PipelineStageDoc {
  step: string;
  code: string;
  title: string;
  engine: string;
  led: LedColorName;
  description: string;
  spec: string;
}

interface KnobDoc {
  channel: string;
  name: string;
  range: string;
  defaultVal: string;
  apiParam: string;
  led: LedColorName;
  purpose: string;
  mechanics: string;
}

interface SwitchDoc {
  channel: string;
  name: string;
  states: string;
  defaultVal: string;
  apiParam: string;
  led: LedColorName;
  purpose: string;
  mechanics: string;
}

interface PresetDoc {
  id: string;
  name: string;
  targetGenre: string;
  led: LedColorName;
  knobsSummary: string;
  switchesSummary: string;
  rationale: string;
}

const PIPELINE_DOCS_EN: readonly PipelineStageDoc[] = [
  {
    step: 'STAGE 01',
    code: 'DSP-STEM',
    title: 'Demucs v4 Stem Separation',
    engine: 'META HTDEMUCS (HYBRID TRANSFORMER)',
    led: 'orange',
    description:
      'Isolates the electric/lead guitar stem from full stereo masters (MP3, WAV, FLAC, OGG) prior to pitch extraction, eliminating drum transients, vocal formants, and sub-bass bleed.',
    spec: '44.1 / 48 kHz FP32 Tensor -> Isolated Guitar Stem + Automatic Mono Fallback',
  },
  {
    step: 'STAGE 02',
    code: 'DSP-SYNC',
    title: 'BeatNet & Librosa Tempo Tracking',
    engine: 'VARIABLE BPM & 192 PPQ TICK GRID',
    led: 'yellow',
    description:
      'Extracts dynamic tempo maps, beat positions, and meter signatures ([SyncTrack]). Converts continuous audio timestamps (seconds) into discrete 192 Pulses-Per-Quarter-Note (PPQ) grid ticks.',
    spec: 'Resolution: 192 PPQ | Milli-BPM Serialization (e.g. 120.0 BPM -> B 120000)',
  },
  {
    step: 'STAGE 03',
    code: 'AI-MIDI',
    title: 'Spotify Basic Pitch Transcription',
    engine: 'POLYPHONIC CNN AUDIO-TO-MIDI',
    led: 'blue',
    description:
      'Predicts polyphonic note events (MIDI pitch 0–127, onset time, offset time, and normalized confidence amplitude) directly from the isolated guitar stem.',
    spec: 'Output: NoteEvent(start_time, end_time, pitch, amplitude [0.0..1.0])',
  },
  {
    step: 'STAGE 04',
    code: 'DSP-FILT',
    title: 'Harmonic Overtone Suppression',
    engine: 'SPECTRAL & OCTAVE ARTIFACT FILTER',
    led: 'red',
    description:
      'Removes high-gain guitar distortion harmonics (octave +12 semitones and fifth +19 semitones) and sub-threshold pick noise that would otherwise produce false multi-note chords.',
    spec: 'Suppresses concurrent overtone spikes within 25 ms of fundamental onset',
  },
  {
    step: 'STAGE 05',
    code: 'MAP-5FRT',
    title: 'Game Design Mapping Engine',
    engine: 'TESSITURA PROJECTION & HOPO HEURISTICS',
    led: 'green',
    description:
      'Fuses string-roll micro-delays into unified chords, snaps onsets to valid 192 PPQ subdivisions, projects MIDI pitches onto the 5 Clone Hero frets (Green 0 -> Orange 4), and calculates HOPOs, sustains, and Star Power.',
    spec: 'Subdivisions: 1/4 (192), 1/8 (96), 1/12 (64), 1/16 (48), 1/24 (32), 1/32 (24)',
  },
  {
    step: 'STAGE 06',
    code: 'PKG-BIN',
    title: 'ChartWriter & Packaging Serialization',
    engine: 'CLONE HERO .CHART & .ZIP ARCHIVE',
    led: 'starpower',
    description:
      'Generates industry-standard text notes.chart, song.ini metadata, and Vorbis song.ogg streams, then packages them into complete Clone Hero archives and raw chart note files.',
    spec: 'Outputs: notes.chart (UTF-8) and .zip full ready-to-play archive',
  },
];

const PIPELINE_DOCS_PT: readonly PipelineStageDoc[] = [
  {
    step: 'ETAPA 01',
    code: 'DSP-STEM',
    title: 'Separação de Faixas Demucs v4',
    engine: 'META HTDEMUCS (HYBRID TRANSFORMER)',
    led: 'orange',
    description:
      'Isola a guitarra elétrica/solo da mixagem completa (MP3, WAV, FLAC, OGG) antes da extração de notas, eliminando batidas de bateria, voz e vazamentos de subgraves.',
    spec: 'Tensor FP32 44.1 / 48 kHz -> Faixa de Guitarra Isolada + Fallback Mono Automático',
  },
  {
    step: 'ETAPA 02',
    code: 'DSP-SYNC',
    title: 'Rastreamento de Tempo BeatNet & Librosa',
    engine: 'BPM VARIÁVEL & GRADE 192 PPQ',
    led: 'yellow',
    description:
      'Extrai o mapa dinâmico de tempo, posições de batida e compasso ([SyncTrack]). Converte o tempo contínuo em segundos para marcações discretas de 192 pulsos por semínima (PPQ).',
    spec: 'Resolução: 192 PPQ | Serialização em mili-BPM (ex: 120.0 BPM -> B 120000)',
  },
  {
    step: 'ETAPA 03',
    code: 'AI-MIDI',
    title: 'Transcrição Polyphonic Basic Pitch (Spotify)',
    engine: 'CNN POLIFÔNICA ÁUDIO-PARA-MIDI',
    led: 'blue',
    description:
      'Detecta eventos de notas musicais polifônicas (altura MIDI 0–127, início, fim e amplitude de confiança) diretamente do áudio isolado da guitarra.',
    spec: 'Saída: NoteEvent(start_time, end_time, pitch, amplitude [0.0..1.0])',
  },
  {
    step: 'ETAPA 04',
    code: 'DSP-FILT',
    title: 'Filtro de Harmônicos e Distorção',
    engine: 'FILTRO ESPECTRAL DE OITAVAS E ARTEFATOS',
    led: 'red',
    description:
      'Remove harmônicos gerados pelo ganho alto da distorção (oitava +12 semitons e quinta +19 semitons) e ruídos de palheta que causariam falsos acordes.',
    spec: 'Suprime picos de sobretons em até 25 ms do ataque fundamental',
  },
  {
    step: 'ETAPA 05',
    code: 'MAP-5FRT',
    title: 'Motor de Game Design e Mapeamento',
    engine: 'PROJEÇÃO DE TESSITURA & REGRAS DE HOPO',
    led: 'green',
    description:
      'Une micro-atrasos de palhetada em acordes unificados, quantiza na grade 192 PPQ, projeta alturas nos 5 fretes do Clone Hero (Verde 0 ao Laranja 4) e calcula HOPOs, notas longas e Star Power.',
    spec: 'Subdivisões: 1/4 (192), 1/8 (96), 1/12 (64), 1/16 (48), 1/24 (32), 1/32 (24)',
  },
  {
    step: 'ETAPA 06',
    code: 'PKG-BIN',
    title: 'Serialização ChartWriter e Pacotes',
    engine: 'CLONE HERO .CHART & ARQUIVO .ZIP',
    led: 'starpower',
    description:
      'Gera o arquivo padronizado notes.chart em texto, metadados song.ini e áudio song.ogg em Vorbis, empacotando tudo em arquivos .zip prontos para jogar ou .chart puro.',
    spec: 'Saídas: notes.chart (UTF-8) e pacote completo .zip para Clone Hero e YARG',
  },
];

const KNOB_DOCS_EN: readonly KnobDoc[] = [
  {
    channel: 'POT-01',
    name: 'Chord Fusion Window',
    range: '10 .. 60 MS (STEP 1 MS)',
    defaultVal: '35 MS (0.035 S)',
    apiParam: 'chord_fusion_window_s',
    led: 'green',
    purpose: 'Prevents guitar string-roll strumming delays from rendering as unplayable micro-staircases.',
    mechanics:
      'When a guitarist strums across strings, onsets arrive 10–35 ms apart. Notes detected within this sliding window fuse into a single unified chord hit at the earliest tick before 192 PPQ quantization.',
  },
  {
    channel: 'POT-02',
    name: 'Noise Gate / Sensitivity',
    range: '0.00 .. 0.50 (STEP 0.01)',
    defaultVal: '0.10',
    apiParam: 'min_amplitude',
    led: 'red',
    purpose: 'Filters out ghost notes, palm-mute transients, string buzz, and background bleed.',
    mechanics:
      'Discards transcribed NoteEvents whose normalized confidence falls below this threshold. Higher values yield cleaner rhythm charts; lower values preserve delicate legato and tapping nuances.',
  },
  {
    channel: 'POT-03',
    name: 'Creativity Factor',
    range: '0 .. 100 % (STEP 1 %)',
    defaultVal: '50 % (0.50)',
    apiParam: 'creativity',
    led: 'yellow',
    purpose: 'Balances strict positional fret economy against wide, expressive solo movement across Green -> Orange.',
    mechanics:
      'Controls dynamic pitch-to-fret projection spread across the sliding tessitura window. Lower values anchor rhythm riffs on lower frets; higher values expand solo lane traversal.',
  },
  {
    channel: 'POT-04',
    name: 'HOPO Distance Cutoff',
    range: '32 .. 192 TICKS (STEP 4)',
    defaultVal: '96 TICKS (1/8 NOTE)',
    apiParam: 'hopo_threshold',
    led: 'blue',
    purpose: 'Defines the maximum rhythmic interval between notes that automatically become Hammer-Ons / Pull-Offs.',
    mechanics:
      'At 192 PPQ, 64 ticks covers eighth-note triplets, while 96 ticks covers eighth notes. Notes within this tick delta receive HOPO state and explicit N 5 0 forcers when required.',
  },
  {
    channel: 'POT-05',
    name: 'Sustain Tail Cutoff',
    range: '0 .. 256 TICKS (STEP 6)',
    defaultVal: '90 TICKS (~1/8 NOTE)',
    apiParam: 'min_sustain_ticks',
    led: 'open',
    purpose: 'Prevents short staccato eighth/sixteenth notes from cluttering the highway with stubby sustain tails.',
    mechanics:
      'Notes whose quantized duration is shorter than this threshold have sustain length set to 0. Notes meeting the cutoff render full sustain ribbons minus the 24-tick release margin.',
  },
  {
    channel: 'POT-06',
    name: 'BPM / Scroll Scale',
    range: '0.50 .. 2.00 X (STEP 0.05X)',
    defaultVal: '1.00 X',
    apiParam: 'bpm_scale',
    led: 'orange',
    purpose: 'Scales the internal tempo grid multiplier to fine-tune highway scroll speed and subdivision density.',
    mechanics:
      'Multiplies detected BPM markers by the chosen factor before grid snapping. Useful for half-time feel tracks (0.50x–0.75x) or double-time metal transcriptions (1.25x–2.00x).',
  },
];

const KNOB_DOCS_PT: readonly KnobDoc[] = [
  {
    channel: 'POT-01',
    name: 'Janela de Fusão de Acordes',
    range: '10 .. 60 MS (PASSO 1 MS)',
    defaultVal: '35 MS (0.035 S)',
    apiParam: 'chord_fusion_window_s',
    led: 'green',
    purpose: 'Impede que o pequeno atraso natural de palhetada entre cordas vire uma escadinha confusa de notas.',
    mechanics:
      'Ao palhetar um acorde, cada corda soa com diferença de 10 a 35 ms. Todas as notas detectadas dentro desta janela móvel são unificadas em um único acorde na primeira batida antes da quantização.',
  },
  {
    channel: 'POT-02',
    name: 'Noise Gate / Sensibilidade',
    range: '0.00 .. 0.50 (PASSO 0.01)',
    defaultVal: '0.10',
    apiParam: 'min_amplitude',
    led: 'red',
    purpose: 'Filtra notas fantasmas, resíduos de abafamento de corda, ruídos de palheta e vazamentos de fundo.',
    mechanics:
      'Descarta notas cuja confiança de transcrição esteja abaixo do limite configurado. Valores mais altos produzem charts mais limpas e rítmicas; valores menores capturam solos sutis e dedilhados.',
  },
  {
    channel: 'POT-03',
    name: 'Fator de Criatividade',
    range: '0 .. 100 % (PASSO 1 %)',
    defaultVal: '50 % (0.50)',
    apiParam: 'creativity',
    led: 'yellow',
    purpose: 'Equilibra economia de movimentos em riffs rítmicos contra solos dinâmicos e expressivos nas 5 cores.',
    mechanics:
      'Controla a abertura da tessitura melódica nos 5 fretes. Valores baixos mantêm as notas concentradas nos fretes iniciais; valores altos estimulam o uso de toda a extensão do braço.',
  },
  {
    channel: 'POT-04',
    name: 'Sensibilidade de HOPO',
    range: '32 .. 192 TICKS (PASSO 4)',
    defaultVal: '96 TICKS (COLCHEIA)',
    apiParam: 'hopo_threshold',
    led: 'blue',
    purpose: 'Define a distância rítmica máxima entre notas consecutivas para ativá-las como Hammer-On / Pull-Off.',
    mechanics:
      'Em 192 PPQ, 64 ticks cobre tercinas de colcheia e 96 ticks cobre colcheias inteiras. Notas dentro desse intervalo em fretes distintos viram HOPOs (tocadas sem palhetar), com modificador N 5 0.',
  },
  {
    channel: 'POT-05',
    name: 'Corte de Notas Longas (Sustain)',
    range: '0 .. 256 TICKS (PASSO 6)',
    defaultVal: '90 TICKS (~1/8)',
    apiParam: 'min_sustain_ticks',
    led: 'open',
    purpose: 'Evita que notas curtas e staccatos fiquem com caudas mínimas que poluem a visualização na pista.',
    mechanics:
      'Notas com duração menor que este limite perdem a cauda (viram gemas secas de impacto). Notas que superam o limite ganham cauda de sustentação, com desconto obrigatório de 24 ticks para nova palhetada.',
  },
  {
    channel: 'POT-06',
    name: 'Multiplicador BPM / Rolagem',
    range: '0.50 .. 2.00 X (PASSO 0.05X)',
    defaultVal: '1.00 X',
    apiParam: 'bpm_scale',
    led: 'orange',
    purpose: 'Ajusta a velocidade de rolagem da pista e a densidade da grade de notas sem alterar o áudio.',
    mechanics:
      'Multiplica os marcadores de BPM detectados pelo fator configurado. Perfeito para faixas lentas com sensação de meio-tempo (0.50x–0.75x) ou transcrições de ritmos rápidos (1.25x–2.00x).',
  },
];

const SWITCH_DOCS_EN: readonly SwitchDoc[] = [
  {
    channel: 'SW-01',
    name: 'Open Notes',
    states: 'ALLOW (UP) // MUTE (DOWN)',
    defaultVal: 'MUTE (DISABLE_OPEN = TRUE)',
    apiParam: 'disable_open_notes',
    led: 'open',
    purpose: 'Controls whether lowest-register pitches emit purple Open Strum bars (N 7 0) or Green (N 0 0) gems.',
    mechanics:
      'Lead guitar charts traditionally restrict Open notes to bass tracks or modern metal breakdowns. Keeping Open Notes muted remaps sub-bass roots to Fret 0 (Green) to preserve classic 5-fret hand positioning.',
  },
  {
    channel: 'SW-02',
    name: 'Fast Runs',
    states: 'COLLAPSE (UP) // CHORDS (DOWN)',
    defaultVal: 'COLLAPSE (TRUE)',
    apiParam: 'collapse_fast_runs',
    led: 'green',
    purpose: 'Protects player ergonomics by preventing multi-fret chords inside rapid sixteenth-note shred passages.',
    mechanics:
      'When enabled, any tick whose distance to adjacent notes is <= 48 ticks (1/16 note at 192 PPQ) has concurrent chord notes collapsed into a single dominant melodic root gem.',
  },
  {
    channel: 'SW-03',
    name: 'Motif Lock',
    states: 'LOCKED (UP) // FREE (DOWN)',
    defaultVal: 'LOCKED (TRUE)',
    apiParam: 'consistent_patterns',
    led: 'blue',
    purpose: 'Guarantees that recurring verse and chorus guitar riffs map to identical, muscle-memory fret color sequences across song sections.',
    mechanics:
      'Employs dynamic-programming fuzzy sequence alignment with soft substitution penalties (vibrato ±1 semitone, bends ±2 st, octave harmonics ±12 st) and ghost-note interpolation. Even if transcription noise or turnaround variations alter endings, the riff body locks onto the canonical fret pattern while modified fills transition smoothly (Option A).',
  },
  {
    channel: 'SW-04',
    name: 'Auto-Calibrate BPM',
    states: 'AUTO (UP) // RAW (DOWN)',
    defaultVal: 'AUTO (TRUE)',
    apiParam: 'auto_calibrate_bpm',
    led: 'orange',
    purpose: 'Automatically folds excessive double-time tempo detections (> 160.0 BPM) into comfortable highway scroll speeds.',
    mechanics:
      'When the tempo tracker locks onto eighth-note hi-hats at 180–240 BPM, AUTO mode halves the base tempo map into the 90–120 BPM range while preserving exact note timing.',
  },
  {
    channel: 'SW-05',
    name: 'Sustain Merge',
    states: 'MERGE (UP) // STACCATO (DOWN)',
    defaultVal: 'MERGE (TRUE)',
    apiParam: 'merge_sustained_notes',
    led: 'yellow',
    purpose: 'Fuses artificial re-triggers caused by guitar vibrato or ringing string decay into a single continuous hold.',
    mechanics:
      'When the transcriber splits a ringing bend or vibrato into adjacent identical-pitch segments, MERGE coalesces them into one sustained note head.',
  },
  {
    channel: 'SW-06',
    name: 'Triad Chords',
    states: 'TRIADS (UP) // POWER (DOWN)',
    defaultVal: 'POWER (MAX_FRETS = 2)',
    apiParam: 'max_frets (3 vs 2)',
    led: 'red',
    purpose: 'Selects between canonical 2-button Power Chords (dyads) and full 3-button Triads on accented beats.',
    mechanics:
      'POWER mode clamps all simultaneous hits to ergonomic 2-note dyads. TRIADS mode permits 3-note chords exclusively on accented beats with sustain >= 96 ticks.',
  },
];

const SWITCH_DOCS_PT: readonly SwitchDoc[] = [
  {
    channel: 'SW-01',
    name: 'Notas Abertas (Open Notes)',
    states: 'PERMITIR (LIGADO) // SILENCIAR (DESLIGADO)',
    defaultVal: 'SILENCIAR (PADRÃO GUITARRA)',
    apiParam: 'disable_open_notes',
    led: 'open',
    purpose: 'Controla se notas de frequências muito graves emitem barras roxas de corda solta (N 7 0) ou gemas Verdes.',
    mechanics:
      'Charts de guitarra solo tradicionalmente reservam notas abertas para baixo ou breakdowns de metal moderno. Ao silenciar, notas graves viram o Frete Verde (0) para manter o posicionamento clássico de 5 dedos.',
  },
  {
    channel: 'SW-02',
    name: 'Escalas Rápidas (Fast Runs)',
    states: 'COLAPSAR (LIGADO) // ACORDES (DESLIGADO)',
    defaultVal: 'COLAPSAR (ATIVADO)',
    apiParam: 'collapse_fast_runs',
    led: 'green',
    purpose: 'Protege a ergonomia do jogador evitando acordes dentro de solos rápidos em semicolcheias (1/16).',
    mechanics:
      'Quando ativado, notas a menos de 48 ticks (1/16 em 192 PPQ) de distância têm acordes convertidos na nota fundamental mais destacada, tornando a passagem fluida e jogável.',
  },
  {
    channel: 'SW-03',
    name: 'Trava de Padrão (Motif Lock)',
    states: 'TRAVADO (LIGADO) // LIVRE (DESLIGADO)',
    defaultVal: 'TRAVADO (ATIVADO)',
    apiParam: 'consistent_patterns',
    led: 'blue',
    purpose: 'Garante que riffs repetidos de verso e refrão mantenham sempre a mesma sequência visual de botões coloridos para fixar a memória muscular.',
    mechanics:
      'Utiliza motor de alinhamento difuso de sequências (programação dinâmica) com custos suaves para vibrato (±1 semitom), bends (±2 st), harmônicos de oitava (±12 st) e interpolação ergonômica de ghost notes. Mesmo com flutuações de áudio ou variações melódicas de final de riff (fills/turnarounds), o corpo do riff preserva os trastes canônicos enquanto a virada transiciona com fluidez (Opção A).',
  },
  {
    channel: 'SW-04',
    name: 'Auto BPM (Auto-Calibrate BPM)',
    states: 'AUTO (LIGADO) // BRUTO (DESLIGADO)',
    defaultVal: 'AUTO (ATIVADO)',
    apiParam: 'auto_calibrate_bpm',
    led: 'orange',
    purpose: 'Ajusta automaticamente andamentos acelerados (> 160 BPM) para manter a rolagem da pista agradável.',
    mechanics:
      'Quando o rastreador detecta chimbal rápido e marca 180–240 BPM, o modo AUTO divide o mapa de tempo pela metade (90–120 BPM) mantendo o alinhamento exato de cada nota.',
  },
  {
    channel: 'SW-05',
    name: 'Mesclar Sustentadas (Sustain Merge)',
    states: 'MESCLAR (LIGADO) // STACCATO (DESLIGADO)',
    defaultVal: 'MESCLAR (ATIVADO)',
    apiParam: 'merge_sustained_notes',
    led: 'yellow',
    purpose: 'Une repetições falsas causadas por vibrato de guitarra ou ressonância de corda em uma única nota sustentada.',
    mechanics:
      'Quando a IA fatia uma nota longa com vibrato em pedaços adjacentes de mesma frequência, o modo MESCLAR une tudo em uma nota única com cauda de sustentação.',
  },
  {
    channel: 'SW-06',
    name: 'Tríades (Triad Chords)',
    states: 'TRÍADES (LIGADO) // POWER CHORDS (DESLIGADO)',
    defaultVal: 'POWER CHORDS (MÁX 2 FRETES)',
    apiParam: 'max_frets (3 vs 2)',
    led: 'red',
    purpose: 'Escolhe entre power chords tradicionais de 2 botões e acordes ricos de 3 notas em momentos de destaque.',
    mechanics:
      'O modo POWER limita todos os acordes a no máximo 2 notas conjuntas confortáveis. O modo TRÍADES permite 3 notas apenas em batidas fortes com sustentação mínima de 96 ticks.',
  },
];

const PRESET_DOCS_EN: readonly PresetDoc[] = [
  {
    id: 'POS 01 // THE BEST',
    name: 'The Best (Developer Recommended Profile)',
    targetGenre: 'HEAVY ROCK / METAL / ALL-ROUND OPTIMIZED TRACKING',
    led: 'green',
    knobsSummary: 'FUSION 40MS | GATE 0.41 | CREAT 15% | HOPO 64T | SUS 120T | BPM 0.65X',
    switchesSummary: 'OPEN: MUTE | RUNS: COLLAPSE | MOTIF: LOCKED | AUTO BPM: AUTO | MERGE: ON | CHORDS: POWER (2)',
    rationale:
      'Developer suggested preset: tuned strict rhythm profile with noise gate set to 0.41 and BPM scale at 0.65 for high-clarity riff separation and robust beat tracking.',
  },
  {
    id: 'POS 02 // STANDARD',
    name: 'Standard (Balanced Studio Default)',
    targetGenre: 'CLASSIC ROCK / ALTERNATIVE / GENERAL LEAD',
    led: 'yellow',
    knobsSummary: 'FUSION 35MS | GATE 0.10 | CREAT 50% | HOPO 96T | SUS 90T | BPM 1.00X',
    switchesSummary: 'OPEN: MUTE | RUNS: COLLAPSE | MOTIF: LOCKED | AUTO BPM: AUTO | MERGE: ON | CHORDS: POWER (2)',
    rationale:
      'Reference all-rounder profile. Balances clean 2-note power chords on rhythm sections with responsive eighth/sixteenth-note HOPO runs and strict motif consistency.',
  },
  {
    id: 'POS 03 // STRICT RHYTHM',
    name: 'Strict Rhythm (Tight Riffing & Downstrokes)',
    targetGenre: 'PUNK / HARD ROCK / RHYTHM GUITAR',
    led: 'yellow',
    knobsSummary: 'FUSION 40MS | GATE 0.20 | CREAT 15% | HOPO 64T | SUS 120T | BPM 1.00X',
    switchesSummary: 'OPEN: MUTE | RUNS: COLLAPSE | MOTIF: LOCKED | AUTO BPM: AUTO | MERGE: ON | CHORDS: POWER (2)',
    rationale:
      'Emphasizes solid chord foundations and downstroke stamina by tightening quantization to 40ms and reducing solo spread.',
  },
  {
    id: 'POS 04 // DYNAMIC SOLO',
    name: 'Dynamic Solo (Expressive Lead Shredding)',
    targetGenre: 'NEOCLASSICAL / SPEED METAL / GUITAR SOLOS',
    led: 'blue',
    knobsSummary: 'FUSION 30MS | GATE 0.08 | CREAT 85% | HOPO 128T | SUS 60T | BPM 1.00X',
    switchesSummary: 'OPEN: MUTE | RUNS: OFF | MOTIF: FREE | AUTO BPM: AUTO | MERGE: OFF | CHORDS: POWER (2)',
    rationale:
      'Unlocks the full 5-fret highway with 85% creativity factor, 128-tick expanded HOPO window, and delicate 0.08 noise gate.',
  },
  {
    id: 'POS 05 // MELODIC',
    name: 'Melodic (Motif Recognition & Clean Leads)',
    targetGenre: 'PROGRESSIVE ROCK / INDIE / BALLADS',
    led: 'starpower',
    knobsSummary: 'FUSION 35MS | GATE 0.12 | CREAT 65% | HOPO 96T | SUS 72T | BPM 1.00X',
    switchesSummary: 'OPEN: MUTE | RUNS: COLLAPSE | MOTIF: LOCKED | AUTO BPM: AUTO | MERGE: ON | CHORDS: POWER (2)',
    rationale:
      'Optimized for expressive melodic motifs. Balances comfortable 72-tick sustains with tight motif lock and responsive HOPO phrasing.',
  },
  {
    id: 'POS 06 // CHORD HEAVY',
    name: 'Chord Heavy (Triads & Polyphonic Rhythm)',
    targetGenre: 'POST-ROCK / GRUNGE / STONER ROCK',
    led: 'red',
    knobsSummary: 'FUSION 45MS | GATE 0.15 | CREAT 35% | HOPO 64T | SUS 96T | BPM 1.00X',
    switchesSummary: 'OPEN: ALLOW | RUNS: OFF | MOTIF: LOCKED | AUTO BPM: AUTO | MERGE: ON | CHORDS: TRIADS (3)',
    rationale:
      'Enables 3-note triads on accented hits with an expanded 45ms fusion window and open note strum bar support.',
  },
];

const PRESET_DOCS_PT: readonly PresetDoc[] = [
  {
    id: 'POS 01 // THE BEST',
    name: 'The Best (Perfil Recomendado pelo Desenvolvedor)',
    targetGenre: 'HEAVY ROCK / METAL / PROCESSAMENTO OTIMIZADO GERAL',
    led: 'green',
    knobsSummary: 'FUSÃO 40MS | GATE 0.41 | CRIAT 15% | HOPO 64T | SUST 120T | BPM 0.65X',
    switchesSummary: 'ABERTAS: NÃO | ESCALAS: COLAPSAR | PADRÃO: TRAVADO | AUTO BPM: SIM | MESCLAR: SIM | ACORDES: POWER (2)',
    rationale:
      'Preset recomendado pelo criador do projeto: perfil rítmico rígido com noise gate em 0.41 e escala BPM em 0.65 para máxima separação de riffs e sincronia impecável.',
  },
  {
    id: 'POS 02 // STANDARD',
    name: 'Padrão (Equilíbrio de Estúdio)',
    targetGenre: 'ROCK CLÁSSICO / ALTERNATIVO / GUITARRA GERAL',
    led: 'yellow',
    knobsSummary: 'FUSÃO 35MS | GATE 0.10 | CRIAT 50% | HOPO 96T | SUST 90T | BPM 1.00X',
    switchesSummary: 'ABERTAS: NÃO | ESCALAS: COLAPSAR | PADRÃO: TRAVADO | AUTO BPM: SIM | MESCLAR: SIM | ACORDES: POWER (2)',
    rationale:
      'Perfil de referência equilibrado. Combina power chords limpos de 2 notas em estrofes com passagens ágeis em HOPO e consistência estrita de padrões.',
  },
  {
    id: 'POS 03 // STRICT RHYTHM',
    name: 'Ritmo Rigoroso (Riffs Firmes e Palhetada para Baixo)',
    targetGenre: 'PUNK / HARD ROCK / GUITARRA BASE',
    led: 'yellow',
    knobsSummary: 'FUSÃO 40MS | GATE 0.20 | CRIAT 15% | HOPO 64T | SUST 120T | BPM 1.00X',
    switchesSummary: 'ABERTAS: NÃO | ESCALAS: COLAPSAR | PADRÃO: TRAVADO | AUTO BPM: SIM | MESCLAR: SIM | ACORDES: POWER (2)',
    rationale:
      'Valoriza bases sólidas de acordes e pegada rítmica constante, aumentando o noise gate para 0.20 e mantendo a criatividade em 15% para fidelidade aos riffs.',
  },
  {
    id: 'POS 04 // DYNAMIC SOLO',
    name: 'Solo Dinâmico (Shredding Expressivo)',
    targetGenre: 'NEOCLÁSSICO / SPEED METAL / SOLOS DE GUITARRA',
    led: 'blue',
    knobsSummary: 'FUSÃO 30MS | GATE 0.08 | CRIAT 85% | HOPO 128T | SUST 60T | BPM 1.00X',
    switchesSummary: 'ABERTAS: NÃO | ESCALAS: NÃO | PADRÃO: LIVRE | AUTO BPM: SIM | MESCLAR: NÃO | ACORDES: POWER (2)',
    rationale:
      'Libera todo o braço da highway com 85% de criatividade, janela expandida de 128 ticks para HOPOs sem palhetar e captação sensível de 0.08.',
  },
  {
    id: 'POS 05 // MELODIC',
    name: 'Melódico (Reconhecimento de Motivos e Temas Limpos)',
    targetGenre: 'ROCK PROGRESSIVO / INDIE / BALADAS',
    led: 'starpower',
    knobsSummary: 'FUSÃO 35MS | GATE 0.12 | CRIAT 65% | HOPO 96T | SUST 72T | BPM 1.00X',
    switchesSummary: 'ABERTAS: NÃO | ESCALAS: COLAPSAR | PADRÃO: TRAVADO | AUTO BPM: SIM | MESCLAR: SIM | ACORDES: POWER (2)',
    rationale:
      'Otimizado para linhas melódicas marcantes. Oferece sustentações confortáveis de 72 ticks com trava firme de temas e fraseado de HOPO fluido.',
  },
  {
    id: 'POS 06 // CHORD HEAVY',
    name: 'Foco em Acordes (Tríades e Ritmo Polifônico)',
    targetGenre: 'POST-ROCK / GRUNGE / STONER ROCK',
    led: 'red',
    knobsSummary: 'FUSÃO 45MS | GATE 0.15 | CRIAT 35% | HOPO 64T | SUST 96T | BPM 1.00X',
    switchesSummary: 'ABERTAS: SIM | ESCALAS: NÃO | PADRÃO: TRAVADO | AUTO BPM: SIM | MESCLAR: SIM | ACORDES: TRÍADES (3)',
    rationale:
      'Habilita acordes completos de 3 fretes em notas de destaque com janela ampla de fusão de 45ms e suporte a notas abertas.',
  },
];

const GRID_SUBDIVISIONS_EN = [
  { note: 'Quarter Note', ratio: '1/4 BEAT', ticks: '192 TICKS', usage: 'Full pulse beat & primary [SyncTrack] grid' },
  { note: 'Quarter Triplet', ratio: '1/6 BEAT', ticks: '128 TICKS', usage: 'Polyrhythmic lead figures & triplet solos' },
  { note: 'Eighth Note', ratio: '1/8 BEAT', ticks: '96 TICKS', usage: 'Standard rock chugs & triad minimum sustain' },
  { note: 'Eighth Triplet', ratio: '1/12 BEAT', ticks: '64 TICKS', usage: 'Shuffle grooves & natural HOPO boundary' },
  { note: 'Sixteenth Note', ratio: '1/16 BEAT', ticks: '48 TICKS', usage: 'Fast-run chord collapse threshold' },
  { note: 'Sixteenth Triplet', ratio: '1/24 BEAT', ticks: '32 TICKS', usage: 'Sextuplet shred runs & rapid fills' },
  { note: 'Thirty-Second Note', ratio: '1/32 BEAT', ticks: '24 TICKS', usage: 'Minimum note spacing & sustain release margin' },
];

const GRID_SUBDIVISIONS_PT = [
  { note: 'Semínima (1/4)', ratio: '1/4 COMPASSO', ticks: '192 TICKS', usage: 'Pulso base da batida e grade principal [SyncTrack]' },
  { note: 'Tercina de Semínima', ratio: '1/6 COMPASSO', ticks: '128 TICKS', usage: 'Frases polirrítmicas e solos em tercina' },
  { note: 'Colcheia (1/8)', ratio: '1/8 COMPASSO', ticks: '96 TICKS', usage: 'Palhetadas de rock padrão e sustentação mínima de tríade' },
  { note: 'Tercina de Colcheia', ratio: '1/12 COMPASSO', ticks: '64 TICKS', usage: 'Ritmos com suingue e limite clássico de HOPO' },
  { note: 'Semicolcheia (1/16)', ratio: '1/16 COMPASSO', ticks: '48 TICKS', usage: 'Limite para colapsar acordes em notas únicas' },
  { note: 'Sextina (1/24)', ratio: '1/24 COMPASSO', ticks: '32 TICKS', usage: 'Passagens ultra rápidas de shredding e viradas' },
  { note: 'Fusa (1/32)', ratio: '1/32 COMPASSO', ticks: '24 TICKS', usage: 'Espaçamento mínimo entre notas e margem de soltura da cauda' },
];

/**
 * Technical Reference Manual & Architecture Specification
 * for the music2chart Studio Workstation (Bilingual PT-BR and English).
 */
export function AboutPage({
  language = 'en',
  onReturnToWorkstation,
  className,
}: AboutPageProps) {
  const portuguese = language === 'pt-BR';

  const pipelineDocs = portuguese ? PIPELINE_DOCS_PT : PIPELINE_DOCS_EN;
  const knobDocs = portuguese ? KNOB_DOCS_PT : KNOB_DOCS_EN;
  const switchDocs = portuguese ? SWITCH_DOCS_PT : SWITCH_DOCS_EN;
  const presetDocs = portuguese ? PRESET_DOCS_PT : PRESET_DOCS_EN;
  const gridSubdivisions = portuguese ? GRID_SUBDIVISIONS_PT : GRID_SUBDIVISIONS_EN;

  return (
    <div className={cn('flex flex-col gap-4', className)}>
      {/* Top Manual Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 border border-hw-border bg-module px-6 py-4 shadow-bevel">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-3">
            <span className="silk-wide text-fret-green">
              {portuguese ? 'MANUAL REV 1.0 // ESPECIFICAÇÃO TÉCNICA' : 'MANUAL REV 1.0 // SPECIFICATION DOCUMENT'}
            </span>
            <span className="h-3 w-px bg-hw-border" aria-hidden="true" />
            <span className="silk-wide">
              {portuguese ? 'PADRÃO CLONE HERO 192 PPQ' : 'CLONE HERO 192 PPQ STANDARD'}
            </span>
          </div>
          <h1 className="font-grotesk text-base font-bold uppercase tracking-silk-wide text-silk sm:text-lg">
            {portuguese
              ? 'MUSIC2CHART // GUIA DIDÁTICO E MANUAL DE CALIBRAÇÃO DSP'
              : 'MUSIC2CHART // TECHNICAL REFERENCE & DSP CALIBRATION MANUAL'}
          </h1>
          <p className="font-mono text-[11px] leading-relaxed tracking-silk text-silk-neutral">
            {portuguese
              ? 'Documentação completa do pipeline de inteligência artificial para síntese de charts, banco analógico de calibração de 6 canais, matriz heurística de roteamento e formatos de exportação para Clone Hero e YARG.'
              : 'Complete operational documentation for the AI audio-to-chart synthesis pipeline, 6-channel analog potentiometer calibration bank, 6-channel heuristic routing matrix, and Clone Hero / YARG packages.'}
          </p>
        </div>

        {onReturnToWorkstation ? (
          <PushButton
            size="md"
            variant="master"
            label={portuguese ? 'Voltar ao Estúdio' : 'Return To Workstation'}
            sublabel={portuguese ? 'Abrir Console' : 'Open Studio Console'}
            led="green"
            ledOn
            onClick={onReturnToWorkstation}
          />
        ) : null}
      </div>

      {/* ================================================================== */}
      {/* DEDICATED DIDACTIC SECTION: GUIA DESCOMPLICADO DE PARÂMETROS       */}
      {/* ================================================================== */}
      <ModulePanel
        code="GUIA-00"
        title={
          portuguese
            ? 'Guia Didático e Descomplicado de Parâmetros'
            : 'Quick & Simple Parameter Guide'
        }
        headerRight={<LedIndicator color="green" on size="xs" label={portuguese ? 'TUTORIAL' : 'HOW IT WORKS'} />}
        footer={
          portuguese
            ? 'CONSULTE ESTE GUIA SEMPRE QUE QUISER AFINAR A CHART PERFEITAMENTE PARA SEU ESTILO DE JOGO'
            : 'REFER TO THIS GUIDE TO FINE-TUNE CHARTS FOR YOUR PREFERRED PLAYSTYLE'
        }
      >
        <div className="flex flex-col gap-4 font-mono text-[11px] leading-relaxed text-silk-neutral">
          <p className="border-b border-hw-border pb-3 text-silk">
            {portuguese
              ? 'Entenda de forma rápida o que cada controle do Music2Chart faz, sem complicação:'
              : 'Understand exactly how each control in Music2Chart alters the generated chart:'}
          </p>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
            {/* Noise Gate */}
            <div className="border border-hw-border bg-chassis p-3 shadow-recess flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between border-b border-hw-border pb-1.5 mb-2">
                  <span className="font-bold text-silk">Noise Gate (Sensibilidade)</span>
                  <LedIndicator color="red" on size="xs" />
                </div>
                {portuguese ? (
                  <ul className="space-y-1.5 list-disc list-inside">
                    <li><strong className="text-silk">Mais alto:</strong> corta ruídos e palhetadas fantasmas, focando somente nas notas principais e ataques firmes.</li>
                    <li><strong className="text-silk">Mais baixo:</strong> capta dedilhados sutis, notas fracas e nuances de legato/tapping.</li>
                  </ul>
                ) : (
                  <ul className="space-y-1.5 list-disc list-inside">
                    <li><strong className="text-silk">Higher:</strong> cuts ghost notes & pick noise, isolating main riff transients.</li>
                    <li><strong className="text-silk">Lower:</strong> captures delicate fingerpicking and quiet legato nuances.</li>
                  </ul>
                )}
              </div>
            </div>

            {/* Janela de Fusão */}
            <div className="border border-hw-border bg-chassis p-3 shadow-recess flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between border-b border-hw-border pb-1.5 mb-2">
                  <span className="font-bold text-silk">
                    {portuguese ? 'Janela de Fusão (Chord Fusion)' : 'Chord Fusion Window'}
                  </span>
                  <LedIndicator color="green" on size="xs" />
                </div>
                {portuguese ? (
                  <ul className="space-y-1.5 list-disc list-inside">
                    <li><strong className="text-silk">Mais alto:</strong> junta notas tocadas em momentos próximos em um mesmo acorde.</li>
                    <li><strong className="text-silk">Mais baixo:</strong> separa notas individuais com precisão cirúrgica.</li>
                  </ul>
                ) : (
                  <ul className="space-y-1.5 list-disc list-inside">
                    <li><strong className="text-silk">Higher:</strong> merges close notes into cohesive simultaneous chords.</li>
                    <li><strong className="text-silk">Lower:</strong> preserves subtle timing differences as separate notes.</li>
                  </ul>
                )}
              </div>
            </div>

            {/* Criatividade */}
            <div className="border border-hw-border bg-chassis p-3 shadow-recess flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between border-b border-hw-border pb-1.5 mb-2">
                  <span className="font-bold text-silk">
                    {portuguese ? 'Criatividade (Creativity)' : 'Creativity Factor'}
                  </span>
                  <LedIndicator color="yellow" on size="xs" />
                </div>
                {portuguese ? (
                  <ul className="space-y-1.5 list-disc list-inside">
                    <li><strong className="text-silk">Mais alto:</strong> gera solos expressivos e dinâmicos pelas 5 cores do braço.</li>
                    <li><strong className="text-silk">Mais baixo:</strong> foco no ritmo base com dedilhados econômicos e ancorados.</li>
                  </ul>
                ) : (
                  <ul className="space-y-1.5 list-disc list-inside">
                    <li><strong className="text-silk">Higher:</strong> expressive solo traversals across all 5 fret colors.</li>
                    <li><strong className="text-silk">Lower:</strong> keeps rhythm riffs tightly anchored on lower frets.</li>
                  </ul>
                )}
              </div>
            </div>

            {/* Sensibilidade HOPO */}
            <div className="border border-hw-border bg-chassis p-3 shadow-recess flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between border-b border-hw-border pb-1.5 mb-2">
                  <span className="font-bold text-silk">
                    {portuguese ? 'Sensibilidade HOPO' : 'HOPO Distance Cutoff'}
                  </span>
                  <LedIndicator color="blue" on size="xs" />
                </div>
                {portuguese ? (
                  <ul className="space-y-1.5 list-disc list-inside">
                    <li><strong className="text-silk">Mais alto:</strong> mais notas viram HOPO (sem precisar palhetar).</li>
                    <li><strong className="text-silk">Mais baixo:</strong> exige palhetada firme na maioria das notas.</li>
                  </ul>
                ) : (
                  <ul className="space-y-1.5 list-disc list-inside">
                    <li><strong className="text-silk">Higher:</strong> triggers more notes as HOPOs without picking.</li>
                    <li><strong className="text-silk">Lower:</strong> requires strict strumming for almost every note.</li>
                  </ul>
                )}
              </div>
            </div>

            {/* Corte de Notas Longas */}
            <div className="border border-hw-border bg-chassis p-3 shadow-recess flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between border-b border-hw-border pb-1.5 mb-2">
                  <span className="font-bold text-silk">
                    {portuguese ? 'Corte de Notas Longas (Sustain)' : 'Sustain Tail Cutoff'}
                  </span>
                  <LedIndicator color="open" on size="xs" />
                </div>
                {portuguese ? (
                  <ul className="space-y-1.5 list-disc list-inside">
                    <li><strong className="text-silk">Mais alto:</strong> somente notas compridas ganham cauda de sustentação.</li>
                    <li><strong className="text-silk">Mais baixo:</strong> notas curtas também ganham caudas visuais.</li>
                  </ul>
                ) : (
                  <ul className="space-y-1.5 list-disc list-inside">
                    <li><strong className="text-silk">Higher:</strong> only truly prolonged holds receive visual sustain ribbons.</li>
                    <li><strong className="text-silk">Lower:</strong> shorter note holds also receive sustain tails.</li>
                  </ul>
                )}
              </div>
            </div>

            {/* Multiplicador BPM */}
            <div className="border border-hw-border bg-chassis p-3 shadow-recess flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between border-b border-hw-border pb-1.5 mb-2">
                  <span className="font-bold text-silk">
                    {portuguese ? 'Multiplicador BPM' : 'BPM Scale'}
                  </span>
                  <LedIndicator color="orange" on size="xs" />
                </div>
                {portuguese ? (
                  <ul className="space-y-1.5 list-disc list-inside">
                    <li><strong className="text-silk">Mais alto:</strong> acelera a rolagem da pista para ritmos rápidos e dobrados.</li>
                    <li><strong className="text-silk">Mais baixo:</strong> reduz pela metade para músicas lentas e cadenciadas.</li>
                  </ul>
                ) : (
                  <ul className="space-y-1.5 list-disc list-inside">
                    <li><strong className="text-silk">Higher:</strong> increases scroll velocity for rapid downstroke passages.</li>
                    <li><strong className="text-silk">Lower:</strong> halves highway scroll speed for slow ballads.</li>
                  </ul>
                )}
              </div>
            </div>
          </div>

          {/* Direct Switches Guide */}
          <div className="border-t border-hw-border pt-3">
            <h3 className="font-bold uppercase tracking-silk text-silk mb-2">
              {portuguese
                ? 'Chaves Seletoras: O que acontece se LIGADO e se DESLIGADO?'
                : 'Toggle Switches: What happens when ON vs OFF?'}
            </h3>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
              <div className="border border-hw-border bg-chassis p-3 shadow-recess">
                <span className="font-bold text-silk">{portuguese ? 'Notas Abertas' : 'Open Notes'}</span>
                <div className="mt-1.5 space-y-1">
                  <p><span className="text-fret-green font-semibold">{portuguese ? 'Ligado:' : 'On:'}</span> {portuguese ? 'Permite notas roxas sem frete na guitarra solo.' : 'Emits purple open strum bars.'}</p>
                  <p><span className="text-fret-red font-semibold">{portuguese ? 'Desligado:' : 'Off:'}</span> {portuguese ? 'Mapeia tudo para os 5 fretes coloridos tradicionais.' : 'Restricts all notes to 5 standard colored frets.'}</p>
                </div>
              </div>

              <div className="border border-hw-border bg-chassis p-3 shadow-recess">
                <span className="font-bold text-silk">{portuguese ? 'Escalas Rápidas' : 'Fast Runs'}</span>
                <div className="mt-1.5 space-y-1">
                  <p><span className="text-fret-green font-semibold">{portuguese ? 'Ligado:' : 'On:'}</span> {portuguese ? 'Em corridas 1/16 rápidas, colapsa acordes em notas únicas.' : 'Collapses multi-note chords to single gems in fast runs.'}</p>
                  <p><span className="text-fret-red font-semibold">{portuguese ? 'Desligado:' : 'Off:'}</span> {portuguese ? 'Mantém acordes mesmo em passagens velozes.' : 'Preserves multi-note chords even at shred speeds.'}</p>
                </div>
              </div>

              <div className="border border-hw-border bg-chassis p-3 shadow-recess">
                <span className="font-bold text-silk">{portuguese ? 'Trava de Padrão' : 'Motif Lock'}</span>
                <div className="mt-1.5 space-y-1">
                  <p><span className="text-fret-green font-semibold">{portuguese ? 'Ligado:' : 'On:'}</span> {portuguese ? 'Riffs repetidos mantêm o mesmo dedilhado visual.' : 'Repeating riffs keep identical fret button sequences.'}</p>
                  <p><span className="text-fret-red font-semibold">{portuguese ? 'Desligado:' : 'Off:'}</span> {portuguese ? 'Varia livremente segundo a transcrição bruta instantânea.' : 'Varies freely according to instantaneous audio transcription.'}</p>
                </div>
              </div>

              <div className="border border-hw-border bg-chassis p-3 shadow-recess">
                <span className="font-bold text-silk">Auto BPM</span>
                <div className="mt-1.5 space-y-1">
                  <p><span className="text-fret-green font-semibold">{portuguese ? 'Ligado:' : 'On:'}</span> {portuguese ? 'Divide andamentos >160 BPM para rolagem confortável.' : 'Halves BPM >160 to avoid dizzying scroll speeds.'}</p>
                  <p><span className="text-fret-red font-semibold">{portuguese ? 'Desligado:' : 'Off:'}</span> {portuguese ? 'Mantém o BPM original detectado sem divisão.' : 'Keeps raw detected BPM without scaling.'}</p>
                </div>
              </div>

              <div className="border border-hw-border bg-chassis p-3 shadow-recess">
                <span className="font-bold text-silk">{portuguese ? 'Mesclar Sustentadas' : 'Sustain Merge'}</span>
                <div className="mt-1.5 space-y-1">
                  <p><span className="text-fret-green font-semibold">{portuguese ? 'Ligado:' : 'On:'}</span> {portuguese ? 'Unifica repetições da mesma nota em uma sustentação longa.' : 'Merges repeated note hits into one continuous hold.'}</p>
                  <p><span className="text-fret-red font-semibold">{portuguese ? 'Desligado:' : 'Off:'}</span> {portuguese ? 'Separa cada ataque como nota curta independente.' : 'Treats every re-trigger as an independent staccato note.'}</p>
                </div>
              </div>

              <div className="border border-hw-border bg-chassis p-3 shadow-recess">
                <span className="font-bold text-silk">{portuguese ? 'Tríades' : 'Triad Chords'}</span>
                <div className="mt-1.5 space-y-1">
                  <p><span className="text-fret-green font-semibold">{portuguese ? 'Ligado:' : 'On:'}</span> {portuguese ? 'Permite acordes de até 3 fretes em batidas acentuadas.' : 'Allows 3-fret triad chords on accented downbeats.'}</p>
                  <p><span className="text-fret-red font-semibold">{portuguese ? 'Desligado:' : 'Off:'}</span> {portuguese ? 'Limita todos os acordes a no máximo 2 fretes (power chords).' : 'Restricts all chords to standard 2-fret power chords.'}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </ModulePanel>

      {/* ================================================================== */}
      {/* MODULE 01: SYSTEM PIPELINE & ARCHITECTURE                          */}
      {/* ================================================================== */}
      <ModulePanel
        code="DOC-01"
        title={portuguese ? 'Pipeline do Sistema & Arquitetura' : 'System Pipeline & Architecture'}
        headerRight={<LedIndicator color="green" on size="xs" label={portuguese ? '6 ETAPAS DSP' : '6-STAGE DSP'} />}
        footer={
          portuguese
            ? 'FLUXO DE SINAL: ÁUDIO BRUTO -> HTDEMUCS -> BEATNET (192 PPQ) -> BASIC PITCH -> FILTRO HARMÔNICO -> MAPEAMENTO 5 FRETES -> .ZIP / .CHART'
            : 'SIGNAL FLOW: RAW AUDIO -> HTDEMUCS -> BEATNET (192 PPQ) -> BASIC PITCH -> HARMONIC FILTER -> 5-FRET MAPPER -> .ZIP / .CHART'
        }
      >
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {pipelineDocs.map((item) => (
            <div
              key={item.code}
              className="flex flex-col justify-between gap-2.5 border border-hw-border bg-chassis p-3.5 shadow-recess"
            >
              <div className="flex items-center justify-between border-b border-hw-border pb-2">
                <div className="flex items-center gap-2">
                  <span className="border border-hw-screw bg-panel px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase tracking-silk text-silk">
                    {item.step}
                  </span>
                  <span className="silk-wide text-[9px]">{item.code}</span>
                </div>
                <LedIndicator color={item.led} on size="xs" />
              </div>

              <div>
                <h3 className="font-mono text-xs font-bold uppercase tracking-silk text-silk">
                  {item.title}
                </h3>
                <div className="mt-0.5 font-mono text-[9px] uppercase tracking-silk text-fret-yellow">
                  {item.engine}
                </div>
                <p className="mt-2 font-mono text-[10px] leading-relaxed tracking-silk text-silk-neutral">
                  {item.description}
                </p>
              </div>

              <div className="border-t border-hw-border pt-2 font-mono text-[9px] uppercase tracking-silk text-silk-dim">
                {item.spec}
              </div>
            </div>
          ))}
        </div>
      </ModulePanel>

      {/* ================================================================== */}
      {/* MODULE 02: 6-CH ANALOG POTENTIOMETER BANK                          */}
      {/* ================================================================== */}
      <ModulePanel
        code="DOC-02"
        title={
          portuguese
            ? 'Banco de 6 Potenciômetros Analógicos // Especificações dos Knobs'
            : '6-Ch Analog Potentiometer Bank // Rotary Knob Specifications'
        }
        headerRight={<LedIndicator color="yellow" on size="xs" label="POT-01..06" />}
        footer={
          portuguese
            ? 'INTERAÇÃO: ARRASTE VERTICAL OU HORIZONTAL | SEGURE SHIFT PARA AJUSTE FINO | DUPLO CLIQUE PARA RESTAURAR PADRÃO'
            : 'INTERACTION: DRAG VERTICAL OR HORIZONTAL | HOLD SHIFT FOR FINE PRECISION | DOUBLE-CLICK TO RESTORE FACTORY DEFAULT'
        }
      >
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {knobDocs.map((knob) => (
            <div
              key={knob.channel}
              className="flex flex-col justify-between gap-2.5 border border-hw-border bg-chassis p-3.5 shadow-recess"
            >
              <div className="flex items-center justify-between border-b border-hw-border pb-2">
                <div className="flex items-center gap-2">
                  <span className="border border-hw-screw bg-panel px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase tracking-silk text-silk">
                    {knob.channel}
                  </span>
                  <span className="font-mono text-xs font-bold uppercase tracking-silk text-silk">
                    {knob.name}
                  </span>
                </div>
                <LedIndicator color={knob.led} on size="xs" />
              </div>

              <div className="grid grid-cols-2 gap-2 border border-hw-border/70 bg-panel px-2.5 py-1.5 font-mono text-[9px] uppercase tracking-silk">
                <div>
                  <span className="text-silk-dim">{portuguese ? 'INTERVALO: ' : 'RANGE: '}</span>
                  <span className="tabular-nums text-silk">{knob.range}</span>
                </div>
                <div>
                  <span className="text-silk-dim">{portuguese ? 'PADRÃO: ' : 'DEFAULT: '}</span>
                  <span className="tabular-nums text-fret-green">{knob.defaultVal}</span>
                </div>
              </div>

              <div className="flex flex-col gap-1.5 font-mono text-[10px] leading-relaxed tracking-silk">
                <div className="font-semibold text-silk">{knob.purpose}</div>
                <p className="text-silk-neutral">{knob.mechanics}</p>
              </div>

              <div className="border-t border-hw-border pt-2 font-mono text-[9px] uppercase tracking-silk text-silk-dim">
                API PARAM: <span className="text-silk">{knob.apiParam}</span>
              </div>
            </div>
          ))}
        </div>
      </ModulePanel>

      {/* ================================================================== */}
      {/* MODULE 03: 6-CH HEURISTIC ROUTING MATRIX                           */}
      {/* ================================================================== */}
      <ModulePanel
        code="DOC-03"
        title={
          portuguese
            ? 'Matriz de Roteamento Heurístico 6-CH // Chaves Mecânicas'
            : '6-Ch Heuristic Routing Matrix // Mechanical Toggle Specifications'
        }
        headerRight={<LedIndicator color="blue" on size="xs" label="SW-01..06" />}
        footer={
          portuguese
            ? 'MODIFICAÇÕES MECÂNICAS APLICADAS DIRETAMENTE ANTES DA QUANTIZAÇÃO 192 PPQ'
            : 'MECHANICAL TOGGLES APPLIED INLINE TO THE 192 PPQ NOTE QUANTIZATION MATRIX'
        }
      >
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {switchDocs.map((sw) => (
            <div
              key={sw.channel}
              className="flex flex-col justify-between gap-2.5 border border-hw-border bg-chassis p-3.5 shadow-recess"
            >
              <div className="flex items-center justify-between border-b border-hw-border pb-2">
                <div className="flex items-center gap-2">
                  <span className="border border-hw-screw bg-panel px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase tracking-silk text-silk">
                    {sw.channel}
                  </span>
                  <span className="font-mono text-xs font-bold uppercase tracking-silk text-silk">
                    {sw.name}
                  </span>
                </div>
                <LedIndicator color={sw.led} on size="xs" />
              </div>

              <div className="grid grid-cols-2 gap-2 border border-hw-border/70 bg-panel px-2.5 py-1.5 font-mono text-[9px] uppercase tracking-silk">
                <div>
                  <span className="text-silk-dim">{portuguese ? 'ESTADOS: ' : 'STATES: '}</span>
                  <span className="text-silk">{sw.states}</span>
                </div>
                <div>
                  <span className="text-silk-dim">{portuguese ? 'PADRÃO: ' : 'DEFAULT: '}</span>
                  <span className="text-fret-green">{sw.defaultVal}</span>
                </div>
              </div>

              <div className="flex flex-col gap-1.5 font-mono text-[10px] leading-relaxed tracking-silk">
                <div className="font-semibold text-silk">{sw.purpose}</div>
                <p className="text-silk-neutral">{sw.mechanics}</p>
              </div>

              <div className="border-t border-hw-border pt-2 font-mono text-[9px] uppercase tracking-silk text-silk-dim">
                API PARAM: <span className="text-silk">{sw.apiParam}</span>
              </div>
            </div>
          ))}
        </div>
      </ModulePanel>

      {/* ================================================================== */}
      {/* MODULE 04: PRESET PROFILES                                         */}
      {/* ================================================================== */}
      <ModulePanel
        code="DOC-04"
        title={
          portuguese
            ? 'Perfis de Mapeamento Pré-configurados (Presets)'
            : 'Pre-Calibrated Tactile Preset Profiles'
        }
        headerRight={<LedIndicator color="orange" on size="xs" label={portuguese ? '6 PRESETS' : '6 PRESETS'} />}
        footer={
          portuguese
            ? 'SELECIONAR QUALQUER PRESET CONFIGURA INSTANTANEAMENTE OS 6 KNOBS E AS 6 CHAVES SELETORAS'
            : 'SELECTING A PRESET INSTANTLY RESTORES ITS TARGET 6 KNOBS & 6 SWITCH STATE CONFIGURATION'
        }
      >
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {presetDocs.map((p) => (
            <div
              key={p.id}
              className="flex flex-col justify-between gap-2.5 border border-hw-border bg-chassis p-3.5 shadow-recess"
            >
              <div className="flex items-center justify-between border-b border-hw-border pb-2">
                <span className="font-mono text-xs font-bold uppercase tracking-silk text-silk">
                  {p.name}
                </span>
                <LedIndicator color={p.led} on size="xs" />
              </div>

              <div className="font-mono text-[9px] uppercase tracking-silk text-fret-yellow">
                {p.targetGenre}
              </div>

              <p className="font-mono text-[10px] leading-relaxed tracking-silk text-silk-neutral">
                {p.rationale}
              </p>

              <div className="flex flex-col gap-1.5 border-t border-hw-border pt-2 font-mono text-[9px] uppercase tracking-silk">
                <div className="text-silk-dim">{p.knobsSummary}</div>
                <div className="text-silk-dim">{p.switchesSummary}</div>
              </div>
            </div>
          ))}
        </div>
      </ModulePanel>

      {/* ================================================================== */}
      {/* MODULE 05 & MODULE 06 SIDE-BY-SIDE                                 */}
      {/* ================================================================== */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
        {/* MODULE 05: CLONE HERO PLAYABILITY SPECIFICATION */}
        <ModulePanel
          code="DOC-05"
          title={
            portuguese
              ? 'Especificação de Jogabilidade Clone Hero (192 PPQ)'
              : 'Clone Hero Playability Specification (192 PPQ)'
          }
          className="xl:col-span-7"
          headerRight={<LedIndicator color="starpower" on size="xs" label="192 PPQ" />}
          footer={
            portuguese
              ? 'TODAS AS CHARTS RESPEITAM RIGOROSAMENTE AS REGRAS OFICIAIS DO MOTOR CLONE HERO'
              : 'ALL GENERATED CHARTS ENFORCE OFFICIAL CLONE HERO & GUITAR HERO ENGINE CONSTRAINTS'
          }
        >
          <div className="flex flex-col gap-3">
            {/* Subdivision Table */}
            <div className="overflow-x-auto border border-hw-border bg-chassis shadow-recess">
              <table className="w-full border-collapse text-left font-mono text-[10px] uppercase tracking-silk">
                <thead>
                  <tr className="border-b border-hw-border bg-panel text-silk-dim">
                    <th className="px-3 py-2">{portuguese ? 'Subdivisão Musical' : 'Musical Subdivision'}</th>
                    <th className="px-3 py-2">{portuguese ? 'Fração' : 'Meter Ratio'}</th>
                    <th className="px-3 py-2">{portuguese ? 'Delta na Grade (192 PPQ)' : 'Grid Delta (192 PPQ)'}</th>
                    <th className="px-3 py-2">{portuguese ? 'Aplicação no Motor' : 'Engine Application'}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-hw-border/60">
                  {gridSubdivisions.map((sub) => (
                    <tr key={sub.ratio} className="text-silk">
                      <td className="px-3 py-1.5 font-semibold">{sub.note}</td>
                      <td className="px-3 py-1.5 tabular-nums text-fret-yellow">{sub.ratio}</td>
                      <td className="px-3 py-1.5 tabular-nums text-fret-green">{sub.ticks}</td>
                      <td className="px-3 py-1.5 text-silk-neutral">{sub.usage}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Core Engine Rules */}
            <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
              <div className="border border-hw-border bg-chassis p-3 shadow-recess">
                <div className="font-mono text-[10px] font-bold uppercase tracking-silk text-fret-green">
                  {portuguese ? 'MARGEM DE SOLTURA DE 24 TICKS' : '24-TICK RE-STRUM RELEASE MARGIN'}
                </div>
                <p className="mt-1 font-mono text-[10px] leading-relaxed tracking-silk text-silk-neutral">
                  {portuguese
                    ? 'Toda nota longa com cauda subtrai obrigatoriamente 24 ticks (fusa de 1/32) antes do próximo ataque. Isso impede que a cauda cubra a próxima nota e garante o registro limpo de uma nova palhetada.'
                    : 'Every sustained note subtracts a mandatory 24-tick (1/32 note) release gap before the next note onset. This prevents sustain tails from overlapping subsequent note heads and guarantees clean re-strum registration.'}
                </p>
              </div>

              <div className="border border-hw-border bg-chassis p-3 shadow-recess">
                <div className="font-mono text-[10px] font-bold uppercase tracking-silk text-fret-yellow">
                  {portuguese ? 'MODIFICADORES HOPO & STRUM (N 5 0 / N 6 0)' : 'HOPO & STRUM FORCERS (N 5 0 / N 6 0)'}
                </div>
                <p className="mt-1 font-mono text-[10px] leading-relaxed tracking-silk text-silk-neutral">
                  {portuguese
                    ? 'Em passagens rápidas de notas simples, a primeira nota é sempre uma palhetada (Strum), enquanto as notas seguintes emitem forçadores explícitos de HOPO (N 5 0). Repetições da mesma gema forçam palhetada (N 6 0).'
                    : 'In rapid single-note runs, note 1 is anchored as a Strum note while notes 2..N emit explicit HOPO force modifiers (N 5 0). Repeated notes on the same fret emit Strum forcers (N 6 0) to override native engine auto-HOPO states.'}
                </p>
              </div>
            </div>
          </div>
        </ModulePanel>

        {/* MODULE 06: OUTPUT CONTAINERS & COMPATIBILITY */}
        <ModulePanel
          code="DOC-06"
          title={
            portuguese
              ? 'Pacotes de Exportação e Compatibilidade'
              : 'Output Containers & Binary Compatibility'
          }
          className="xl:col-span-5"
          headerRight={<LedIndicator color="green" on size="xs" label="CLONE HERO" />}
          footer={
            portuguese
              ? 'TOTALMENTE COMPATÍVEL COM CLONE HERO (V1.0+) E YARG'
              : 'COMPATIBLE WITH CLONE HERO (V1.0+) AND YARG (YET ANOTHER RHYTHM GAME)'
          }
        >
          <div className="flex flex-col gap-3">
            <div className="border border-hw-border bg-chassis p-3 shadow-recess">
              <div className="font-mono text-xs font-bold uppercase tracking-silk text-fret-green">
                {portuguese ? '.ZIP // PACOTE COMPLETO PARA CLONE HERO' : '.ZIP // FULL STUDIO PACKAGE ARCHIVE'}
              </div>
              <p className="mt-1 font-mono text-[10px] leading-relaxed tracking-silk text-silk-neutral">
                {portuguese
                  ? 'Arquivo compactado completo contendo notes.chart, song.ini e o áudio em Ogg Vorbis (song.ogg). Basta descompactar diretamente na pasta Songs do Clone Hero ou YARG para jogar imediatamente.'
                  : 'Standard deflated archive bundling notes.chart, song.ini, and Vorbis-encoded song.ogg for direct extraction into the Clone Hero Songs directory or external chart editors (Moonscraper).'}
              </p>
            </div>

            <div className="border border-hw-border bg-chassis p-3 shadow-recess">
              <div className="font-mono text-xs font-bold uppercase tracking-silk text-fret-blue">
                {portuguese ? '.CHART // ESPECIFICAÇÃO DE NOTAS EM TEXTO' : '.CHART // 192 PPQ STRUCTURED TEXT SPECIFICATION'}
              </div>
              <p className="mt-1 font-mono text-[10px] leading-relaxed tracking-silk text-silk-neutral">
                {portuguese
                  ? 'Arquivo estruturado em texto legível contendo metadados [Song], mapa de BPM e compasso [SyncTrack], seções de treino [Events] e eventos de notas em 5 cores [ExpertSingle] com Star Power.'
                  : 'Human-readable section-delimited file containing [Song] metadata, [SyncTrack] milli-BPM and time signature markers, [Events] practice sections, and [ExpertSingle] note events (N 0..4, N 5/6 modifiers, and Star Power).'}
              </p>
            </div>

            <div className="border border-hw-border bg-chassis p-3 shadow-recess">
              <div className="font-mono text-xs font-bold uppercase tracking-silk text-silk-dim">
                {portuguese ? 'FORMATO .SNG LEGADO' : 'LEGACY .SNG CONTAINER'}
              </div>
              <p className="mt-1 font-mono text-[10px] leading-relaxed tracking-silk text-silk-dim">
                {portuguese
                  ? 'O formato binário SongBinary v1 (.sng) foi descontinuado na interface primária em favor de .ZIP e .CHART, garantindo máxima interoperabilidade sem problemas de codificação.'
                  : 'SongBinary v1 (.sng) has been phased out from primary export options in favor of .ZIP and .CHART, providing direct drag-and-drop compatibility across all song loaders.'}
              </p>
            </div>
          </div>
        </ModulePanel>
      </div>

      {/* ================================================================== */}
      {/* MODULE 07: OPEN SOURCE & COMMUNITY INFRASTRUCTURE                 */}
      {/* ================================================================== */}
      <ModulePanel
        code="DOC-07"
        title={
          portuguese
            ? 'Identidade de Código Aberto & Apoio da Comunidade'
            : 'Open-Source Identity & Community Infrastructure'
        }
        headerRight={<LedIndicator color="orange" on size="xs" label="MIT LICENSE" />}
        footer={
          portuguese
            ? 'SOFTWARE LIVRE E GRATUITO // MANTIDO POR APOIO COMUNITÁRIO // OBJETIVO: SERVIDORES COM GPU DEDICADA'
            : 'FREE & OPEN-SOURCE SOFTWARE // POWERED BY COMMUNITY SPONSORSHIP // GOAL: DEDICATED GPU HARDWARE'
        }
      >
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <div className="flex flex-col justify-between gap-2.5 border border-hw-border bg-chassis p-3.5 shadow-recess">
            <div>
              <div className="flex items-center justify-between border-b border-hw-border pb-2">
                <span className="silk-wide text-[9px]">
                  {portuguese ? 'CÓDIGO FONTE & REPOSITÓRIO' : 'SOURCE CODE & REPO'}
                </span>
                <LedIndicator color="green" on size="xs" />
              </div>
              <h3 className="mt-2 font-mono text-xs font-bold uppercase tracking-silk text-silk">
                GitHub Repository
              </h3>
              <p className="mt-2 font-mono text-[10px] leading-relaxed tracking-silk text-silk-neutral">
                {portuguese
                  ? 'Código completo do pipeline de IA (Demucs v4, Basic Pitch, BeatNet), heurísticas de game design e aplicação React/Three.js sob licença permissiva MIT.'
                  : 'Complete codebase for backend AI pipelines (Demucs v4, Basic Pitch, BeatNet), game design heuristics, and React/Three.js workstation. Licensed under the permissive MIT License.'}
              </p>
            </div>
            <a
              href="https://github.com/Adiells/music2chart"
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 flex items-center justify-center gap-2 border border-hw-border bg-panel py-2 font-mono text-[10px] font-semibold uppercase tracking-silk text-silk hover:border-silk hover:bg-module transition-colors"
            >
              <span>{portuguese ? 'Ver no GitHub' : 'View on GitHub'}</span>
              <span className="text-fret-green">↗</span>
            </a>
          </div>

          <div className="flex flex-col justify-between gap-2.5 border border-hw-border bg-chassis p-3.5 shadow-recess">
            <div>
              <div className="flex items-center justify-between border-b border-hw-border pb-2">
                <span className="silk-wide text-[9px]">
                  {portuguese ? 'INFRAESTRUTURA & EVOLUÇÃO' : 'INFRASTRUCTURE & EVOLUTION'}
                </span>
                <LedIndicator color="orange" on blink="slow" size="xs" />
              </div>
              <h3 className="mt-2 font-mono text-xs font-bold uppercase tracking-silk text-silk">
                {portuguese ? 'Fundo para GPU Dedicada' : 'GPU Upgrade Fund'}
              </h3>
              <p className="mt-2 font-mono text-[10px] leading-relaxed tracking-silk text-silk-neutral">
                {portuguese
                  ? 'Atualmente hospedado em Google Cloud Run CPU (4 vCPU, 8 GiB RAM). Os apoios da comunidade financiam a migração para servidores com GPU NVIDIA dedicada, reduzindo a geração de charts para menos de 15 segundos.'
                  : 'Currently deployed on Google Cloud Run CPU (4 vCPU, 8 GiB RAM). Sponsorships directly fund our milestone to upgrade to dedicated Cloud GPU instances (NVIDIA Tensor Core), unlocking instant sub-15s transcription.'}
              </p>
            </div>
            <a
              href="https://github.com/sponsors/Adiells"
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 flex items-center justify-center gap-2 border border-fret-yellow bg-[#26200F] py-2 font-mono text-[10px] font-semibold uppercase tracking-silk text-fret-yellow hover:bg-[#382F15] transition-colors"
            >
              <span>{portuguese ? 'Apoiar no GitHub' : 'Sponsor on GitHub'}</span>
              <span className="text-fret-yellow">↗</span>
            </a>
          </div>

          <div className="flex flex-col justify-between gap-2.5 border border-hw-border bg-chassis p-3.5 shadow-recess">
            <div>
              <div className="flex items-center justify-between border-b border-hw-border pb-2">
                <span className="silk-wide text-[9px]">
                  {portuguese ? 'COLABORAÇÃO' : 'COLLABORATION'}
                </span>
                <LedIndicator color="blue" on size="xs" />
              </div>
              <h3 className="mt-2 font-mono text-xs font-bold uppercase tracking-silk text-silk">
                {portuguese ? 'Issues & Contribuições' : 'Issues & Contributions'}
              </h3>
              <p className="mt-2 font-mono text-[10px] leading-relaxed tracking-silk text-silk-neutral">
                {portuguese
                  ? 'Contribuições para as heurísticas 192 PPQ, filtros DSP e visualizador 3D são bem-vindas. Reporte problemas de transcrição ou sugira melhorias no GitHub Issues.'
                  : 'Contributions to the 192 PPQ mapping heuristics, audio DSP filters, and highway visualizer are warmly welcomed. Report chart transcription bugs or propose feature requests on GitHub Issues.'}
              </p>
            </div>
            <a
              href="https://github.com/Adiells/music2chart/issues"
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 flex items-center justify-center gap-2 border border-hw-border bg-panel py-2 font-mono text-[10px] font-semibold uppercase tracking-silk text-silk hover:border-silk hover:bg-module transition-colors"
            >
              <span>{portuguese ? 'Abrir Issue / PR' : 'Open Issue / PR'}</span>
              <span className="text-fret-blue">↗</span>
            </a>
          </div>
        </div>
      </ModulePanel>
    </div>
  );
}
