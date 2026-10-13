## 2026-10-13T20:41:54Z
You are explorer_m4_1, an Explorer subagent for Milestone 4 of chartgen Phase 4.
Your working directory is: /home/adiel/Projects/music2chart/.agents/teamwork/explorer_m4_1

MANDATORY: Read /home/adiel/Projects/music2chart/.agents/teamwork/ORIGINAL_REQUEST.md before starting work.
Also read:
- /home/adiel/Projects/music2chart/.agents/teamwork/orchestrator/SCOPE.md
- /home/adiel/Projects/music2chart/.agents/teamwork/orchestrator/PROJECT.md
- /home/adiel/Projects/music2chart/PROMPTS.md (Prompt 4.4)
- /home/adiel/Projects/music2chart/AGENTS.md (Section 7.4)
- /home/adiel/Projects/music2chart/src/models/chart.py

Task:
Investigate and design `HopoEngine` in `src/game_design/hopo_engine.py`:
1. Core HOPO rules:
   - For consecutive notes at ticks t_prev and t_curr:
     - If delta_tick <= hopo_threshold (default 65 ticks) AND fret differs -> is_hopo = True.
     - If delta_tick > 65 ticks -> is_hopo = False (regular strum).
   - First note of the song:
     - Must always be a Strum (is_hopo = False).
   - Repeated notes:
     - Consecutive notes with the same fret (or same chord) must always be Strums (is_hopo = False).
2. Chord interactions:
   - What happens when moving from single note to chord, chord to single note, or chord to chord within <= 65 ticks?
     - In Clone Hero, can chords be natural HOPOs or are chords generally strums unless explicitly forced? How should HopoEngine handle chords?
   - Open notes:
     - How do Open notes (fret 7) behave in HOPO sequences? (Can an Open note be a HOPO from a fretted note? Can a fretted note be a HOPO from an Open note?)
3. API Signature and Data Flow:
   - `process_hopos(self, notes: Sequence[ChartNote]) -> list[ChartNote]` (with alias `process` or `tag_hopos`).
   - Does it modify notes or return new ChartNote instances? (Recommend returning new instances to keep ChartNote immutable).
4. Provide precise, non-ambiguous pseudo-code and formulas for the Worker. (Do NOT write to source files directly).

Write your findings to:
- /home/adiel/Projects/music2chart/.agents/teamwork/explorer_m4_1/analysis.md
- /home/adiel/Projects/music2chart/.agents/teamwork/explorer_m4_1/handoff.md

Send a completion message to the parent orchestrator when finished.
