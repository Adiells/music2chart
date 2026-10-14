## 2026-10-13T19:21:17Z
You are explorer_m2_1, an Explorer subagent for Milestone 2 of music2chart Phase 4.
Your working directory is: /home/adiel/Projects/music2chart/.agents/teamwork/explorer_m2_1

MANDATORY: Read /home/adiel/Projects/music2chart/.agents/teamwork/ORIGINAL_REQUEST.md before starting work.
Also read:
- /home/adiel/Projects/music2chart/.agents/teamwork/orchestrator/SCOPE.md
- /home/adiel/Projects/music2chart/.agents/teamwork/orchestrator/PROJECT.md
- /home/adiel/Projects/music2chart/src/game_design/quantizer.py
- /home/adiel/Projects/music2chart/src/models/chart.py

Task:
Investigate and design the sliding-window pitch percentile projection algorithm for `PitchToFretMapper` in `src/game_design/pitch_to_fret.py`:
1. Window size: default `window_ticks = 1536` (~2 measures in 4/4 time at 192 PPQ).
2. For each note at `tick`, how should the local pitch window `[tick - window_ticks/2, tick + window_ticks/2]` (or centered/causal) be selected?
3. How should the pitches in the window be normalized across percentiles to produce frets 0 to 4 (Green, Red, Yellow, Blue, Orange)?
   - Consider percentiles: [min, 20%, 40%, 60%, 80%] or [min, 25%, 50%, 75%, max] or rank-based mapping.
   - Address degenerate cases: all notes in window have identical pitch, window contains only 1 or 2 notes, narrow pitch range (< 5 semitones vs > 24 semitones).
4. Provide precise, non-ambiguous pseudo-code and formulas for the Worker. (Do NOT write to source files directly).

Write your findings to:
- /home/adiel/Projects/music2chart/.agents/teamwork/explorer_m2_1/analysis.md
- /home/adiel/Projects/music2chart/.agents/teamwork/explorer_m2_1/handoff.md

Send a completion message to the parent orchestrator when finished.
