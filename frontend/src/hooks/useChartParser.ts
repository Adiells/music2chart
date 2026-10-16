import { useCallback, useEffect, useState } from 'react';
import { clamp } from '../lib/utils';

export const RELEASE_MARGIN_TICKS = 24;
export const DEFAULT_RESOLUTION = 192;
export const DEFAULT_HOPO_THRESHOLD = 65;

export type PlayableFret = 0 | 1 | 2 | 3 | 4 | 7;

export interface ParsedBpmChange {
  tick: number;
  bpm: number;
  timeSeconds: number;
}

export interface ParsedTimeSignature {
  tick: number;
  numerator: number;
  denominator: number;
  timeSeconds: number;
}

export interface ParsedSection {
  tick: number;
  name: string;
  timeSeconds: number;
}

export interface ParsedStarPower {
  tick: number;
  lengthTicks: number;
  startTimeSeconds: number;
  endTimeSeconds: number;
}

export interface ParsedChartNote {
  id: string;
  tick: number;
  timeSeconds: number;
  /** 0=Green, 1=Red, 2=Yellow, 3=Blue, 4=Orange, 7=Open (purple bar). */
  fret: PlayableFret;
  rawSustainTicks: number;
  /** Sustain duration in ticks after enforcing the 24-tick release margin. */
  sustainTicks: number;
  sustainEndTick: number;
  sustainEndTimeSeconds: number;
  sustainDurationSeconds: number;
  isHopo: boolean;
  isForcedHopo: boolean;
  isForcedStrum: boolean;
  isOpen: boolean;
  isChordMember: boolean;
  inStarPower: boolean;
}

export interface ParsedBeatLine {
  tick: number;
  timeSeconds: number;
  isMeasure: boolean;
  measureNumber: number;
  beatNumber: number;
}

export interface NpsBucket {
  index: number;
  startTime: number;
  endTime: number;
  nps: number;
  noteCount: number;
}

export interface ChartStats {
  totalNotes: number;
  totalGems: number;
  hopoCount: number;
  hopoPercentage: number;
  chordCount: number;
  openNoteCount: number;
  sustainCount: number;
  starPowerCount: number;
  peakNps: number;
  avgNps: number;
}

export interface ParsedChart {
  songName: string;
  artist: string;
  charter: string;
  genre: string;
  resolution: number;
  offsetSeconds: number;
  difficulty: number;
  durationSeconds: number;
  bpmChanges: ParsedBpmChange[];
  timeSignatures: ParsedTimeSignature[];
  sections: ParsedSection[];
  starPower: ParsedStarPower[];
  notes: ParsedChartNote[];
  beatLines: ParsedBeatLine[];
  npsBuckets: NpsBucket[];
  stats: ChartStats;
  rawText: string;
}

export interface InstantTempoSnapshot {
  bpm: number;
  numerator: number;
  denominator: number;
  tick: number;
  measure: number;
  beat: number;
  beatProgress: number;
  activeSection: string;
}

/**
 * Convert a musical tick into seconds using piecewise-constant BPM segments.
 */
export function tickToSeconds(
  tick: number,
  bpmChanges: readonly ParsedBpmChange[],
  resolution = DEFAULT_RESOLUTION,
  offsetSeconds = 0,
): number {
  if (bpmChanges.length === 0) {
    return offsetSeconds + (tick / resolution) * (60 / 120);
  }

  let active = bpmChanges[0];
  for (let i = 0; i < bpmChanges.length; i += 1) {
    if (bpmChanges[i].tick <= tick) {
      active = bpmChanges[i];
    } else {
      break;
    }
  }

  const deltaTicks = Math.max(0, tick - active.tick);
  const secondsPerTick = 60 / (active.bpm * resolution);
  return active.timeSeconds + deltaTicks * secondsPerTick;
}

/**
 * Convert a timestamp in seconds into the corresponding musical grid tick.
 */
export function secondsToTick(
  seconds: number,
  bpmChanges: readonly ParsedBpmChange[],
  resolution = DEFAULT_RESOLUTION,
): number {
  if (seconds <= 0) return 0;
  if (bpmChanges.length === 0) {
    return Math.round(seconds * (120 / 60) * resolution);
  }

  let active = bpmChanges[0];
  for (let i = 0; i < bpmChanges.length; i += 1) {
    if (bpmChanges[i].timeSeconds <= seconds) {
      active = bpmChanges[i];
    } else {
      break;
    }
  }

  const deltaSec = Math.max(0, seconds - active.timeSeconds);
  const ticksPerSecond = (active.bpm / 60) * resolution;
  return Math.round(active.tick + deltaSec * ticksPerSecond);
}

/**
 * Query instantaneous BPM, time signature, measure/beat counter, and section at `timeSeconds`.
 */
export function getInstantTempoAtTime(
  timeSeconds: number,
  chart: ParsedChart,
): InstantTempoSnapshot {
  const t = Math.max(0, timeSeconds);
  const tick = secondsToTick(t, chart.bpmChanges, chart.resolution);

  let bpm = 120;
  for (const b of chart.bpmChanges) {
    if (b.tick <= tick) bpm = b.bpm;
    else break;
  }

  let ts: ParsedTimeSignature = chart.timeSignatures[0] ?? {
    tick: 0,
    numerator: 4,
    denominator: 4,
    timeSeconds: 0,
  };
  for (const candidate of chart.timeSignatures) {
    if (candidate.tick <= tick) ts = candidate;
    else break;
  }

  const ticksPerBeat = Math.max(1, Math.round((chart.resolution * 4) / ts.denominator));
  const ticksPerMeasure = Math.max(1, ticksPerBeat * ts.numerator);
  const relTicks = Math.max(0, tick - ts.tick);
  const measure = Math.floor(relTicks / ticksPerMeasure) + 1;
  const beatFloat = (relTicks % ticksPerMeasure) / ticksPerBeat;
  const beat = Math.floor(beatFloat) + 1;
  const beatProgress = beatFloat - Math.floor(beatFloat);

  let activeSection = 'Intro';
  for (const sec of chart.sections) {
    if (sec.timeSeconds <= t + 0.02) {
      activeSection = sec.name;
    } else {
      break;
    }
  }

  return {
    bpm,
    numerator: ts.numerator,
    denominator: ts.denominator,
    tick,
    measure,
    beat,
    beatProgress,
    activeSection,
  };
}

/**
 * Built-in reference `.chart` file showcasing all Clone Hero features:
 * [SyncTrack] variable BPMs, [Events] sections (Intro, Verse, Chorus, Solo, Outro),
 * 5-fret gems, power chords, HOPO runs (N 5 0), strum forcers (N 6 0),
 * sustains with 24-tick release margins, Open notes (N 7 0), and Star Power (S 2).
 */
export const DEMO_CHART_TEXT = `[Song]
{
  Name = "Anodized Pulse (Studio Reference)"
  Artist = "music2chart DSP"
  Charter = "music2chart AI"
  Offset = 0
  Resolution = 192
  Player2 = bass
  Difficulty = 6
  PreviewStart = 0
  PreviewEnd = 0
  Genre = "prog"
  MediaType = "cd"
  MusicStream = "song.ogg"
}
[SyncTrack]
{
  0 = TS 4
  0 = B 128000
  12288 = B 136000
  21504 = TS 4
  21504 = B 128000
}
[Events]
{
  0 = E "section Intro"
  3072 = E "section Verse 1"
  7680 = E "section Chorus"
  12288 = E "section Guitar Solo"
  21504 = E "section Outro"
}
[ExpertSingle]
{
  0 = N 7 0
  192 = N 0 168
  192 = N 1 168
  384 = N 7 0
  576 = N 1 168
  576 = N 2 168
  768 = N 0 360
  768 = N 2 360
  1152 = N 2 168
  1152 = N 3 168
  1344 = N 1 168
  1344 = N 2 168
  1536 = N 0 0
  1632 = N 1 0
  1632 = N 5 0
  1728 = N 2 0
  1728 = N 5 0
  1824 = N 3 0
  1824 = N 5 0
  1920 = N 4 360
  2304 = N 7 0
  2496 = N 0 168
  2496 = N 1 168
  2688 = N 2 360
  2688 = N 3 360
  3072 = S 2 1536
  3072 = N 0 0
  3168 = N 2 0
  3168 = N 5 0
  3264 = N 1 0
  3264 = N 5 0
  3360 = N 3 0
  3360 = N 5 0
  3456 = N 2 0
  3456 = N 5 0
  3552 = N 4 0
  3552 = N 5 0
  3648 = N 3 0
  3648 = N 5 0
  3744 = N 1 0
  3744 = N 5 0
  3840 = N 0 360
  3840 = N 1 360
  4224 = N 1 360
  4224 = N 3 360
  4608 = N 0 0
  4704 = N 0 0
  4704 = N 6 0
  4800 = N 1 0
  4800 = N 5 0
  4896 = N 2 0
  4896 = N 5 0
  4992 = N 3 360
  5376 = N 2 360
  5760 = N 1 360
  6144 = N 0 552
  6144 = N 1 552
  6720 = N 2 168
  6720 = N 3 168
  6912 = N 3 552
  6912 = N 4 552
  7680 = S 2 2304
  7680 = N 0 360
  7680 = N 2 360
  8064 = N 1 360
  8064 = N 3 360
  8448 = N 2 360
  8448 = N 4 360
  8832 = N 1 168
  8832 = N 3 168
  9024 = N 0 168
  9024 = N 2 168
  9216 = N 7 0
  9408 = N 0 0
  9504 = N 1 0
  9504 = N 5 0
  9600 = N 2 0
  9600 = N 5 0
  9696 = N 3 0
  9696 = N 5 0
  9792 = N 4 0
  9792 = N 5 0
  9888 = N 3 0
  9888 = N 5 0
  9984 = N 2 0
  9984 = N 5 0
  10080 = N 1 0
  10080 = N 5 0
  10176 = N 0 552
  10176 = N 1 552
  10752 = N 2 360
  10752 = N 3 360
  11136 = N 3 360
  11136 = N 4 360
  11520 = N 0 744
  11520 = N 2 744
  12288 = S 2 3072
  12288 = N 4 0
  12336 = N 3 0
  12336 = N 5 0
  12384 = N 2 0
  12384 = N 5 0
  12432 = N 1 0
  12432 = N 5 0
  12480 = N 0 0
  12480 = N 5 0
  12528 = N 1 0
  12528 = N 5 0
  12576 = N 2 0
  12576 = N 5 0
  12624 = N 3 0
  12624 = N 5 0
  12672 = N 4 0
  12672 = N 5 0
  12720 = N 3 0
  12720 = N 5 0
  12768 = N 2 0
  12768 = N 5 0
  12816 = N 1 0
  12816 = N 5 0
  12864 = N 2 0
  12864 = N 5 0
  12912 = N 3 0
  12912 = N 5 0
  12960 = N 4 0
  12960 = N 5 0
  13056 = N 4 360
  13440 = N 0 0
  13488 = N 2 0
  13488 = N 5 0
  13536 = N 1 0
  13536 = N 5 0
  13584 = N 3 0
  13584 = N 5 0
  13632 = N 2 0
  13632 = N 5 0
  13680 = N 4 0
  13680 = N 5 0
  13728 = N 3 0
  13728 = N 5 0
  13776 = N 4 0
  13776 = N 5 0
  13824 = N 4 552
  14400 = N 3 0
  14464 = N 2 0
  14464 = N 5 0
  14528 = N 1 0
  14528 = N 5 0
  14592 = N 0 0
  14592 = N 5 0
  14656 = N 1 0
  14656 = N 5 0
  14720 = N 2 0
  14720 = N 5 0
  14784 = N 3 0
  14784 = N 5 0
  14848 = N 4 0
  14848 = N 5 0
  14912 = N 3 0
  14912 = N 5 0
  14976 = N 2 0
  14976 = N 5 0
  15040 = N 1 0
  15040 = N 5 0
  15104 = N 0 0
  15104 = N 5 0
  15168 = N 2 552
  15168 = N 4 552
  15744 = N 1 552
  15744 = N 3 552
  16320 = N 0 0
  16416 = N 1 0
  16416 = N 5 0
  16512 = N 2 0
  16512 = N 5 0
  16608 = N 3 0
  16608 = N 5 0
  16704 = N 4 0
  16704 = N 5 0
  16800 = N 3 0
  16800 = N 5 0
  16896 = N 2 0
  16896 = N 5 0
  16992 = N 1 0
  16992 = N 5 0
  17088 = N 0 552
  17664 = N 4 552
  18240 = N 2 0
  18336 = N 3 0
  18336 = N 5 0
  18432 = N 4 0
  18432 = N 5 0
  18528 = N 3 0
  18528 = N 5 0
  18624 = N 2 0
  18624 = N 5 0
  18720 = N 1 0
  18720 = N 5 0
  18816 = N 0 0
  18816 = N 5 0
  18912 = N 1 0
  18912 = N 5 0
  19008 = N 2 744
  19008 = N 4 744
  19776 = N 1 744
  19776 = N 3 744
  20544 = N 0 936
  20544 = N 2 936
  21504 = S 2 1536
  21504 = N 7 0
  21696 = N 0 168
  21696 = N 1 168
  21888 = N 7 0
  22080 = N 1 168
  22080 = N 2 168
  22272 = N 2 360
  22272 = N 3 360
  22656 = N 3 360
  22656 = N 4 360
  23040 = N 0 1128
  23040 = N 1 1128
  23040 = N 2 1128
}
`;

function stripQuotes(val: string): string {
  return val.trim().replace(/^"(.*)"$/, '$1').trim();
}

/**
 * Parse a Clone Hero `.chart` text document into structured timeline objects,
 * enforcing the 24-tick release margin on sustains, resolving HOPO/Strum modifiers,
 * and computing NPS density buckets and summary telemetry.
 */
export function parseChartText(rawText: string): ParsedChart {
  const sectionsMap = new Map<string, string[]>();
  let currentHeader: string | null = null;
  let insideBraces = false;

  const lines = rawText.split(/\r?\n/);
  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line || line.startsWith('//')) continue;

    if (line.startsWith('[') && line.endsWith(']')) {
      currentHeader = line.slice(1, -1).trim();
      if (!sectionsMap.has(currentHeader)) {
        sectionsMap.set(currentHeader, []);
      }
      insideBraces = false;
      continue;
    }

    if (line === '{') {
      insideBraces = true;
      continue;
    }

    if (line === '}') {
      insideBraces = false;
      currentHeader = null;
      continue;
    }

    if (currentHeader && insideBraces) {
      sectionsMap.get(currentHeader)?.push(line);
    }
  }

  // 1. Parse [Song]
  let songName = 'Untitled Chart';
  let artist = 'Unknown Artist';
  let charter = 'music2chart AI';
  let genre = 'rock';
  let resolution = DEFAULT_RESOLUTION;
  let offsetSeconds = 0;
  let difficulty = 6;

  for (const line of sectionsMap.get('Song') ?? []) {
    const eqIdx = line.indexOf('=');
    if (eqIdx < 0) continue;
    const key = line.slice(0, eqIdx).trim();
    const val = stripQuotes(line.slice(eqIdx + 1));

    switch (key) {
      case 'Name':
        songName = val || songName;
        break;
      case 'Artist':
        artist = val || artist;
        break;
      case 'Charter':
        charter = val || charter;
        break;
      case 'Genre':
        genre = val || genre;
        break;
      case 'Resolution': {
        const parsed = Number.parseInt(val, 10);
        if (Number.isFinite(parsed) && parsed > 0) resolution = parsed;
        break;
      }
      case 'Offset': {
        const parsed = Number.parseFloat(val);
        if (Number.isFinite(parsed)) offsetSeconds = parsed;
        break;
      }
      case 'Difficulty': {
        const parsed = Number.parseInt(val, 10);
        if (Number.isFinite(parsed)) difficulty = parsed;
        break;
      }
      default:
        break;
    }
  }

  // 2. Parse [SyncTrack]
  const rawBpms: { tick: number; bpm: number }[] = [];
  const rawTs: { tick: number; numerator: number; denominator: number }[] = [];

  for (const line of sectionsMap.get('SyncTrack') ?? []) {
    const match = /^(\d+)\s*=\s*(B|TS)\s+(.+)$/i.exec(line);
    if (!match) continue;
    const tick = Number.parseInt(match[1], 10);
    const kind = match[2].toUpperCase();
    const rest = match[3].trim().split(/\s+/);

    if (kind === 'B') {
      const milliBpm = Number.parseInt(rest[0], 10);
      if (Number.isFinite(milliBpm) && milliBpm > 0) {
        rawBpms.push({ tick, bpm: milliBpm / 1000 });
      }
    } else if (kind === 'TS') {
      const num = Number.parseInt(rest[0], 10);
      const denExp = rest[1] !== undefined ? Number.parseInt(rest[1], 10) : 2;
      if (Number.isFinite(num) && num > 0) {
        const den = Number.isFinite(denExp) ? 2 ** denExp : 4;
        rawTs.push({ tick, numerator: num, denominator: den });
      }
    }
  }

  rawBpms.sort((a, b) => a.tick - b.tick);
  if (rawBpms.length === 0 || rawBpms[0].tick > 0) {
    rawBpms.unshift({ tick: 0, bpm: rawBpms[0]?.bpm ?? 120 });
  }

  const bpmChanges: ParsedBpmChange[] = [];
  let accSeconds = offsetSeconds;
  for (let i = 0; i < rawBpms.length; i += 1) {
    const cur = rawBpms[i];
    if (i > 0) {
      const prev = bpmChanges[bpmChanges.length - 1];
      const deltaTicks = Math.max(0, cur.tick - prev.tick);
      accSeconds = prev.timeSeconds + (deltaTicks / resolution) * (60 / prev.bpm);
    }
    bpmChanges.push({
      tick: cur.tick,
      bpm: cur.bpm,
      timeSeconds: accSeconds,
    });
  }

  rawTs.sort((a, b) => a.tick - b.tick);
  if (rawTs.length === 0 || rawTs[0].tick > 0) {
    rawTs.unshift({ tick: 0, numerator: 4, denominator: 4 });
  }

  const timeSignatures: ParsedTimeSignature[] = rawTs.map((ts) => ({
    tick: ts.tick,
    numerator: ts.numerator,
    denominator: ts.denominator,
    timeSeconds: tickToSeconds(ts.tick, bpmChanges, resolution, offsetSeconds),
  }));

  // 3. Parse [Events]
  const sections: ParsedSection[] = [];
  for (const line of sectionsMap.get('Events') ?? []) {
    const match = /^(\d+)\s*=\s*E\s+(.+)$/i.exec(line);
    if (!match) continue;
    const tick = Number.parseInt(match[1], 10);
    const rawEvent = stripQuotes(match[2]);
    if (rawEvent.toLowerCase().startsWith('section ')) {
      const secName = rawEvent.slice(8).trim() || 'Section';
      sections.push({
        tick,
        name: secName,
        timeSeconds: tickToSeconds(tick, bpmChanges, resolution, offsetSeconds),
      });
    } else if (rawEvent.length > 0 && !rawEvent.startsWith('lyric ')) {
      sections.push({
        tick,
        name: rawEvent,
        timeSeconds: tickToSeconds(tick, bpmChanges, resolution, offsetSeconds),
      });
    }
  }
  sections.sort((a, b) => a.tick - b.tick);

  // 4. Parse Note Track ([ExpertSingle] or first available difficulty track)
  const trackOrder = [
    'ExpertSingle',
    'HardSingle',
    'MediumSingle',
    'EasySingle',
    'ExpertDoubleBass',
    'ExpertDrums',
  ];
  let trackLines: string[] = [];
  for (const candidate of trackOrder) {
    const found = sectionsMap.get(candidate);
    if (found && found.length > 0) {
      trackLines = found;
      break;
    }
  }

  interface RawTickGroup {
    tick: number;
    frets: Map<PlayableFret, number>;
    forceHopo: boolean;
    forceStrum: boolean;
  }

  const tickGroupsMap = new Map<number, RawTickGroup>();
  const starPower: ParsedStarPower[] = [];

  const getGroup = (tick: number): RawTickGroup => {
    let g = tickGroupsMap.get(tick);
    if (!g) {
      g = { tick, frets: new Map<PlayableFret, number>(), forceHopo: false, forceStrum: false };
      tickGroupsMap.set(tick, g);
    }
    return g;
  };

  for (const line of trackLines) {
    const match = /^(\d+)\s*=\s*(N|S)\s+(\d+)\s+(\d+)/i.exec(line);
    if (!match) continue;
    const tick = Number.parseInt(match[1], 10);
    const kind = match[2].toUpperCase();
    const code = Number.parseInt(match[3], 10);
    const length = Number.parseInt(match[4], 10);

    if (kind === 'N') {
      const group = getGroup(tick);
      if (code === 5) {
        group.forceHopo = true;
      } else if (code === 6) {
        group.forceStrum = true;
      } else if (code === 0 || code === 1 || code === 2 || code === 3 || code === 4 || code === 7) {
        const playable = code as PlayableFret;
        const prevSus = group.frets.get(playable) ?? 0;
        group.frets.set(playable, Math.max(prevSus, length));
      }
    } else if (kind === 'S' && code === 2) {
      const startTimeSeconds = tickToSeconds(tick, bpmChanges, resolution, offsetSeconds);
      const endTimeSeconds = tickToSeconds(tick + length, bpmChanges, resolution, offsetSeconds);
      starPower.push({
        tick,
        lengthTicks: length,
        startTimeSeconds,
        endTimeSeconds,
      });
    }
  }

  starPower.sort((a, b) => a.tick - b.tick);

  const sortedGroups = Array.from(tickGroupsMap.values())
    .filter((g) => g.frets.size > 0)
    .sort((a, b) => a.tick - b.tick);

  // Build notes with HOPO state and 24-tick release margin on sustains
  const notes: ParsedChartNote[] = [];
  let hopoCount = 0;
  let chordCount = 0;
  let openNoteCount = 0;
  let sustainCount = 0;

  const hopoMaxDelta = Math.round((DEFAULT_HOPO_THRESHOLD / 192) * resolution);

  for (let i = 0; i < sortedGroups.length; i += 1) {
    const group = sortedGroups[i];
    const prevGroup = i > 0 ? sortedGroups[i - 1] : null;
    const nextGroup = i + 1 < sortedGroups.length ? sortedGroups[i + 1] : null;

    const fretEntries = Array.from(group.frets.entries()).sort((a, b) => a[0] - b[0]);
    const isChord = fretEntries.length > 1;
    if (isChord) chordCount += 1;

    // Determine HOPO status according to Clone Hero & AGENTS.md rules:
    // - STRUM_FORCE (N 6 0) strictly forces Strum (isHopo = false)
    // - HOPO_FORCE (N 5 0) strictly forces HOPO (isHopo = true)
    // - Otherwise, natural HOPO applies on single notes within hopoMaxDelta ticks of a different fret
    let isHopo = false;
    if (group.forceStrum) {
      isHopo = false;
    } else if (group.forceHopo) {
      isHopo = true;
    } else if (!isChord && prevGroup && group.tick - prevGroup.tick <= hopoMaxDelta) {
      const currentFret = fretEntries[0][0];
      const prevFrets = Array.from(prevGroup.frets.keys());
      const sameSingleFret = prevFrets.length === 1 && prevFrets[0] === currentFret;
      if (!sameSingleFret && currentFret !== 7) {
        isHopo = true;
      }
    }

    if (isHopo) hopoCount += 1;

    const inStarPower = starPower.some(
      (sp) => group.tick >= sp.tick && group.tick < sp.tick + sp.lengthTicks,
    );
    const timeSeconds = tickToSeconds(group.tick, bpmChanges, resolution, offsetSeconds);

    for (const [fret, rawSus] of fretEntries) {
      const isOpen = fret === 7;
      if (isOpen) openNoteCount += 1;

      // Enforce 24-tick release margin prior to next note onset
      let sustainTicks = rawSus;
      if (sustainTicks > 0 && nextGroup) {
        const maxAllowed = Math.max(0, nextGroup.tick - group.tick - RELEASE_MARGIN_TICKS);
        sustainTicks = Math.min(sustainTicks, maxAllowed);
      }

      if (sustainTicks > 0) sustainCount += 1;

      const sustainEndTick = group.tick + sustainTicks;
      const sustainEndTimeSeconds =
        sustainTicks > 0
          ? tickToSeconds(sustainEndTick, bpmChanges, resolution, offsetSeconds)
          : timeSeconds;

      notes.push({
        id: `${group.tick}-${fret}`,
        tick: group.tick,
        timeSeconds,
        fret,
        rawSustainTicks: rawSus,
        sustainTicks,
        sustainEndTick,
        sustainEndTimeSeconds,
        sustainDurationSeconds: Math.max(0, sustainEndTimeSeconds - timeSeconds),
        isHopo,
        isForcedHopo: group.forceHopo && !group.forceStrum,
        isForcedStrum: group.forceStrum,
        isOpen,
        isChordMember: isChord,
        inStarPower,
      });
    }
  }

  const lastNoteEndTick = notes.reduce((acc, n) => Math.max(acc, n.sustainEndTick), 0);
  const maxTick = Math.max(lastNoteEndTick + resolution * 4, resolution * 16);
  const durationSeconds = Math.max(4, tickToSeconds(maxTick, bpmChanges, resolution, offsetSeconds));

  // If the chart only had the default single "Intro" event, synthesize structural section markers
  if (sections.length <= 1 && lastNoteEndTick > resolution * 16) {
    const measureTicks = resolution * 4;
    const totalMeasures = Math.floor(lastNoteEndTick / measureTicks);
    const autoSections: { ratio: number; label: string }[] = [
      { ratio: 0, label: sections[0]?.name || 'Intro' },
      { ratio: 0.2, label: 'Verse' },
      { ratio: 0.45, label: 'Chorus' },
      { ratio: 0.68, label: 'Solo' },
      { ratio: 0.88, label: 'Outro' },
    ];
    sections.length = 0;
    const usedTicks = new Set<number>();
    for (const item of autoSections) {
      const m = Math.round(totalMeasures * item.ratio);
      const t = m * measureTicks;
      if (!usedTicks.has(t)) {
        usedTicks.add(t);
        sections.push({
          tick: t,
          name: item.label,
          timeSeconds: tickToSeconds(t, bpmChanges, resolution, offsetSeconds),
        });
      }
    }
  } else if (sections.length === 0) {
    sections.push({ tick: 0, name: 'Intro', timeSeconds: 0 });
  }

  // 5. Generate Beat & Measure Grid Lines
  const beatLines: ParsedBeatLine[] = [];
  let cursorTick = 0;
  let measureCounter = 1;
  while (cursorTick <= maxTick) {
    let activeTs = timeSignatures[0];
    for (const ts of timeSignatures) {
      if (ts.tick <= cursorTick) activeTs = ts;
      else break;
    }
    const beatStep = Math.max(24, Math.round((resolution * 4) / activeTs.denominator));
    for (let b = 1; b <= activeTs.numerator && cursorTick <= maxTick; b += 1) {
      beatLines.push({
        tick: cursorTick,
        timeSeconds: tickToSeconds(cursorTick, bpmChanges, resolution, offsetSeconds),
        isMeasure: b === 1,
        measureNumber: measureCounter,
        beatNumber: b,
      });
      cursorTick += beatStep;
    }
    measureCounter += 1;
  }

  // 6. Compute NPS Density Buckets (1-second windows)
  const bucketCount = Math.max(8, Math.ceil(durationSeconds));
  const bucketWidth = durationSeconds / bucketCount;
  const npsBuckets: NpsBucket[] = Array.from({ length: bucketCount }, (_, idx) => ({
    index: idx,
    startTime: idx * bucketWidth,
    endTime: (idx + 1) * bucketWidth,
    nps: 0,
    noteCount: 0,
  }));

  // Count distinct onset events (or gems) per bucket
  for (const g of sortedGroups) {
    const tSec = tickToSeconds(g.tick, bpmChanges, resolution, offsetSeconds);
    const idx = clamp(Math.floor(tSec / bucketWidth), 0, bucketCount - 1);
    npsBuckets[idx].noteCount += 1;
  }

  let peakNps = 0;
  for (const b of npsBuckets) {
    b.nps = Number((b.noteCount / bucketWidth).toFixed(2));
    if (b.nps > peakNps) peakNps = b.nps;
  }

  const totalNotes = sortedGroups.length;
  const totalGems = notes.length;
  const activeSpanSeconds =
    sortedGroups.length >= 2
      ? Math.max(
          1,
          tickToSeconds(sortedGroups[sortedGroups.length - 1].tick, bpmChanges, resolution, offsetSeconds) -
            tickToSeconds(sortedGroups[0].tick, bpmChanges, resolution, offsetSeconds),
        )
      : durationSeconds;
  const avgNps = Number((totalNotes / activeSpanSeconds).toFixed(2));
  const hopoPercentage = totalNotes > 0 ? Number(((hopoCount / totalNotes) * 100).toFixed(1)) : 0;

  return {
    songName,
    artist,
    charter,
    genre,
    resolution,
    offsetSeconds,
    difficulty,
    durationSeconds,
    bpmChanges,
    timeSignatures,
    sections,
    starPower,
    notes,
    beatLines,
    npsBuckets,
    stats: {
      totalNotes,
      totalGems,
      hopoCount,
      hopoPercentage,
      chordCount,
      openNoteCount,
      sustainCount,
      starPowerCount: starPower.length,
      peakNps,
      avgNps,
    },
    rawText,
  };
}

export interface UseChartParserResult {
  chart: ParsedChart;
  loading: boolean;
  error: string | null;
  isDemoChart: boolean;
  loadFromText: (rawChartText: string) => void;
  resetToDemo: () => void;
}

const PARSED_DEMO_CHART: ParsedChart = parseChartText(DEMO_CHART_TEXT);

interface LoadedTaskChart {
  taskId: string;
  chart: ParsedChart | null;
  error: string | null;
}

/**
 * React hook that downloads and parses `/api/v1/chart/download/{task_id}?format=chart`
 * whenever a completed `taskId` is provided, falling back to the built-in Studio Reference
 * `.chart` for immediate 3D Highway inspection.
 */
export function useChartParser(completedTaskId: string | null): UseChartParserResult {
  const [loaded, setLoaded] = useState<LoadedTaskChart | null>(null);
  const [manualChart, setManualChart] = useState<ParsedChart | null>(null);

  const isRealTask = Boolean(completedTaskId && !completedTaskId.startsWith('demo-'));

  useEffect(() => {
    if (!completedTaskId || completedTaskId.startsWith('demo-')) {
      return undefined;
    }

    let cancelled = false;

    const fetchChart = async (): Promise<void> => {
      try {
        const url = `/api/v1/chart/download/${encodeURIComponent(completedTaskId)}?format=chart`;
        const res = await fetch(url);
        if (!res.ok) {
          throw new Error(`HTTP ${res.status} fetching notes.chart`);
        }
        const text = await res.text();
        if (cancelled) return;
        const parsed = parseChartText(text);
        setLoaded({ taskId: completedTaskId, chart: parsed, error: null });
      } catch (err) {
        if (cancelled) return;
        const msg = err instanceof Error ? err.message : 'Failed to parse .chart';
        setLoaded({ taskId: completedTaskId, chart: null, error: msg });
      }
    };

    void fetchChart();

    return () => {
      cancelled = true;
    };
  }, [completedTaskId]);

  const loadFromText = useCallback((rawChartText: string): void => {
    setManualChart(parseChartText(rawChartText));
  }, []);

  const resetToDemo = useCallback((): void => {
    setManualChart(null);
    setLoaded(null);
  }, []);

  const matchedTask = isRealTask && loaded?.taskId === completedTaskId ? loaded : null;
  const chart = manualChart ?? matchedTask?.chart ?? PARSED_DEMO_CHART;
  const isDemoChart = !manualChart && !matchedTask?.chart;
  const loading = isRealTask && loaded?.taskId !== completedTaskId;
  const error = matchedTask?.error ?? null;

  return {
    chart,
    loading,
    error,
    isDemoChart,
    loadFromText,
    resetToDemo,
  };
}
