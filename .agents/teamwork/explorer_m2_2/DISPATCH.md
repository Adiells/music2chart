## 2026-10-13T19:21:17Z
You are explorer_m2_2, an Explorer subagent for Milestone 2 of chartgen Phase 4.
Your working directory is: /home/adiel/Projects/music2chart/.agents/teamwork/explorer_m2_2

MANDATORY: Read /home/adiel/Projects/music2chart/.agents/teamwork/ORIGINAL_REQUEST.md before starting work.
Also read:
- /home/adiel/Projects/music2chart/.agents/teamwork/orchestrator/SCOPE.md
- /home/adiel/Projects/music2chart/.agents/teamwork/orchestrator/PROJECT.md
- /home/adiel/Projects/music2chart/src/game_design/quantizer.py
- /home/adiel/Projects/music2chart/src/models/chart.py

Task:
Investigate and design the jump penalty constraint, Open Note mapping, and API contract for `PitchToFretMapper`:
1. Open Note mapping:
   - Extreme sub-bass notes (< MIDI 40, e.g. low E / Drop D / 7-string bass) map to `FretType.OPEN` (7).
   - How should Open notes interact with the sliding window and jump penalty? (Should open notes affect fret leap tracking or be excluded from fret leap distance?)
2. Rapid passage jump penalty:
   - When interval between consecutive notes is `< 48` ticks (16th note threshold) and fret distance leap is `> 3` frets (e.g. Green 0 to Orange 4, leap 4):
     - How should the leap be penalized/clamped? (e.g., clamped to `prev_fret + 3` or `prev_fret - 3`, or bounded within [0, 4] preserving leap direction).
3. Output format: returns `list[ChartNote]` with `sustain_length=0` and `is_hopo=False`.
4. Provide precise, robust architecture recommendations for the Worker. (Do NOT write to source files directly).

Write your findings to:
- /home/adiel/Projects/music2chart/.agents/teamwork/explorer_m2_2/analysis.md
- /home/adiel/Projects/music2chart/.agents/teamwork/explorer_m2_2/handoff.md

Send a completion message to the parent orchestrator when finished.
