## 2026-10-13T20:41:54Z
Sender: c32a8c2d-046d-4e36-96ca-60cf3fc9e81f (parent orchestrator)

You are explorer_m4_2, an Explorer subagent for Milestone 4 of chartgen Phase 4.
Your working directory is: /home/adiel/Projects/music2chart/.agents/teamwork/explorer_m4_2

MANDATORY: Read /home/adiel/Projects/music2chart/.agents/teamwork/ORIGINAL_REQUEST.md before starting work.
Also read:
- /home/adiel/Projects/music2chart/.agents/teamwork/orchestrator/SCOPE.md
- /home/adiel/Projects/music2chart/.agents/teamwork/orchestrator/PROJECT.md
- /home/adiel/Projects/music2chart/PROMPTS.md (Prompt 4.4)
- /home/adiel/Projects/music2chart/AGENTS.md (Section 7.5 & Section 4.2)
- /home/adiel/Projects/music2chart/src/models/chart.py

Task:
Investigate and design `SustainProcessor` and `StarPowerGenerator`:
1. `SustainProcessor` in `src/game_design/sustain_processor.py`:
   - Inputs: Notes with raw durations (either from NoteEvent/QuantizedNote duration_ticks or pre-populated sustain_length).
   - Threshold: If duration < min_sustain_ticks (default 90 ticks) -> sustain_length = 0 (staccato/impact note).
   - Release cut: If duration >= 90 ticks -> sustain_length = duration - release_margin (default 24 ticks).
   - Consecutive note clearance:
     - When the next note onset is at next_tick: sustain must not overlap the next note.
     - Clearance constraint: sustain_length <= max(0, next_tick - tick - release_margin).
     - How should chords at the same tick be handled? (All notes in a chord have the same tick; next_tick is the onset of the next distinct tick).
   - API Signature: `process_sustains(self, notes: Sequence[ChartNote]) -> list[ChartNote]`.
2. `StarPowerGenerator` in `src/game_design/star_power_generator.py`:
   - Class `StarPowerGenerator(phrase_interval_measures: int = 16, phrase_length_measures: int = 2, resolution: int = 192)`
   - Identifies candidate passages with notes to place `StarPowerPhrase(tick, length)`.
   - Ensures phrases do not overlap, are placed during active note sections, and span appropriate measure lengths (e.g. 2 measures = 1536 ticks at 192 PPQ in 4/4).
   - Output: `list[StarPowerPhrase]`.
3. Provide precise pseudo-code and architecture recommendations for the Worker. (Do NOT write to source files directly).

Write your findings to:
- /home/adiel/Projects/music2chart/.agents/teamwork/explorer_m4_2/analysis.md
- /home/adiel/Projects/music2chart/.agents/teamwork/explorer_m4_2/handoff.md

Send a completion message to the parent orchestrator when finished.
