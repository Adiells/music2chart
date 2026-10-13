## 2026-10-13T20:03:07Z
You are explorer_m3_1, an Explorer subagent for Milestone 3 of chartgen Phase 4.
Your working directory is: /home/adiel/Projects/music2chart/.agents/teamwork/explorer_m3_1

MANDATORY: Read /home/adiel/Projects/music2chart/.agents/teamwork/ORIGINAL_REQUEST.md before starting work.
Also read:
- /home/adiel/Projects/music2chart/.agents/teamwork/orchestrator/SCOPE.md
- /home/adiel/Projects/music2chart/.agents/teamwork/orchestrator/PROJECT.md
- /home/adiel/Projects/music2chart/src/game_design/pitch_to_fret.py
- /home/adiel/Projects/music2chart/src/models/chart.py
- /home/adiel/Projects/music2chart/PROMPTS.md (Prompt 4.3)
- /home/adiel/Projects/music2chart/AGENTS.md (Section 7.3)

Task:
Investigate and design polyphonic cluster simplification and canonical chord preservation for `ChordBuilder` in `src/game_design/chord_builder.py`:
1. Grouping: Notes with identical `tick` are grouped into chord clusters.
2. Max concurrent frets constraint: A Clone Hero chord must have at most 3 frets (e.g. `max_frets = 3`).
   - If a cluster has 4 or 5 notes (e.g., frets 0, 1, 2, 3 or 0, 1, 2, 3, 4), how should it be simplified to <= 3 frets?
   - What heuristic should be used? (e.g. root + 5th + octave, or prioritizing lowest root + highest melody + canonical triad shape, or matching CANONICAL_TRIADS).
3. Canonical chord shapes:
   - Power chords: (0, 1), (0, 2), (1, 2), (1, 3), (2, 3), (2, 4), (3, 4).
   - Triads: (0, 1, 2), (0, 2, 3), (1, 2, 3), (2, 3, 4).
4. Provide precise pseudo-code and algorithmic formulas for the Worker. (Do NOT write to source files directly).

Write your findings to:
- /home/adiel/Projects/music2chart/.agents/teamwork/explorer_m3_1/analysis.md
- /home/adiel/Projects/music2chart/.agents/teamwork/explorer_m3_1/handoff.md

Send a completion message to the parent orchestrator when finished.
