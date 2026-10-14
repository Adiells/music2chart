## 2026-10-13T20:41:54Z
You are spec_miner_m4, a Specification Miner subagent for Milestone 4 of music2chart Phase 4.
Your working directory is: /home/adiel/Projects/music2chart/.agents/teamwork/spec_miner_m4

MANDATORY: Read /home/adiel/Projects/music2chart/.agents/teamwork/ORIGINAL_REQUEST.md before starting work.
Also read:
- /home/adiel/Projects/music2chart/.agents/teamwork/orchestrator/SCOPE.md
- /home/adiel/Projects/music2chart/.agents/teamwork/orchestrator/PROJECT.md
- /home/adiel/Projects/music2chart/PROMPTS.md (Prompt 4.4)
- /home/adiel/Projects/music2chart/AGENTS.md (Sections 4.2, 7.4, 7.5)
- /home/adiel/Projects/music2chart/src/models/chart.py

Task:
Author a comprehensive test plan and concrete test cases for `tests/test_game_design/test_hopo_engine.py` (and any related game design test modules):
1. HopoEngine test cases:
   - Consecutive notes <= 65 ticks with different frets: marked as HOPO (`is_hopo=True`).
   - Consecutive notes > 65 ticks (e.g. 66, 96, 192 ticks): marked as Strum (`is_hopo=False`).
   - Repeated frets within <= 65 ticks (e.g. Green then Green at 48 ticks): forced Strum (`is_hopo=False`).
   - First note of track: always Strum (`is_hopo=False`).
   - Rapid ascending/descending scales (e.g. 0 -> 1 -> 2 -> 3 -> 4 every 48 ticks): all except first note are HOPOs.
   - Chords: single-note to chord, chord to single-note, chord to chord.
   - Open notes (fret 7) transitions.
2. SustainProcessor test cases:
   - Duration < 90 ticks (e.g. 0, 48, 89 ticks): sustain_length = 0.
   - Duration >= 90 ticks (e.g. 90, 192, 384 ticks): sustain_length = duration - 24.
   - Next-note overlap clamping: long note (duration 500 ticks) followed by next note at +192 ticks -> sustain clamped to 192 - 24 = 168 ticks.
   - Consecutive notes with 48-tick spacing and long durations -> sustain clamped to 48 - 24 = 24 ticks.
   - Final note of track: retains full duration - 24.
3. StarPowerGenerator test cases:
   - Empty notes -> empty star power phrases.
   - Single short note -> appropriate handling.
   - Long song (e.g. 64 measures): generates periodic phrases at configured interval (e.g. every ~16 measures).
   - Star power phrases fall within active note regions.
4. Provide complete, runnable pytest test code conforming to strict mypy and ruff.

Write your findings to:
- /home/adiel/Projects/music2chart/.agents/teamwork/spec_miner_m4/spec_report.md
- /home/adiel/Projects/music2chart/.agents/teamwork/spec_miner_m4/handoff.md

Send a completion message to the parent orchestrator when finished.
