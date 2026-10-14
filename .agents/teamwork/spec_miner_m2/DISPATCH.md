## 2026-10-13T19:21:17Z
You are spec_miner_m2, a Specification Miner subagent for Milestone 2 of music2chart Phase 4.
Your working directory is: /home/adiel/Projects/music2chart/.agents/teamwork/spec_miner_m2

MANDATORY: Read /home/adiel/Projects/music2chart/.agents/teamwork/ORIGINAL_REQUEST.md before starting work.
Also read:
- /home/adiel/Projects/music2chart/.agents/teamwork/orchestrator/SCOPE.md
- /home/adiel/Projects/music2chart/.agents/teamwork/orchestrator/PROJECT.md
- /home/adiel/Projects/music2chart/PROMPTS.md (Prompt 4.2)
- /home/adiel/Projects/music2chart/AGENTS.md (Section 7.2)

Task:
Author a comprehensive test plan and concrete test cases for `tests/test_game_design/test_pitch_to_fret.py`:
1. Ascending scale flow: chromatic/diatonic scale maps smoothly from Green (0) to Orange (4).
2. Relative tessitura windowing during solo passages: high register passages (pitches 75 to 90) use the full 5-fret span organically rather than clustering only on Orange (4).
3. Sub-bass open note: pitch < 40 maps to `FretType.OPEN` (7).
4. Rapid passage jump penalty: interval < 48 ticks clamps jumps > 3 frets (e.g. Green 0 to Orange 4 clamped to <= Blue 3).
5. Edge cases: empty list, single note, monophonic repeating pitch, simultaneous notes (chords with multiple pitches at same tick).
6. Provide complete, runnable pytest test code conforming to strict mypy and ruff.

Write your findings to:
- /home/adiel/Projects/music2chart/.agents/teamwork/spec_miner_m2/spec_report.md
- /home/adiel/Projects/music2chart/.agents/teamwork/spec_miner_m2/handoff.md

Send a completion message to the parent orchestrator when finished.
