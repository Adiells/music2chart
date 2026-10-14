## 2026-10-13T20:53:49Z
You are worker_m4 for Milestone 4 (HOPO, Strum & Sustain Duration Engine) in music2chart Phase 4.

Your working directory is:
/home/adiel/Projects/music2chart/.agents/teamwork/worker_m4

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MANDATORY READING:
You MUST read the following files before taking any action:
1. /home/adiel/Projects/music2chart/.agents/teamwork/ORIGINAL_REQUEST.md
2. /home/adiel/Projects/music2chart/.agents/teamwork/spec_miner_m4/spec_report.md (Authoritative M4 Specification & Runnable Test Suite)
3. /home/adiel/Projects/music2chart/AGENTS.md (Sections 4 & 7)
4. /home/adiel/Projects/music2chart/PROMPTS.md (Phase 4: Prompts 4.1 to 4.4)
5. /home/adiel/Projects/music2chart/.agents/teamwork/orchestrator/SCOPE.md

Write Ownership:
You exclusively own and may edit:
- /home/adiel/Projects/music2chart/src/game_design/hopo_engine.py
- /home/adiel/Projects/music2chart/src/game_design/sustain_processor.py
- /home/adiel/Projects/music2chart/src/game_design/star_power_generator.py
- /home/adiel/Projects/music2chart/src/game_design/__init__.py
- /home/adiel/Projects/music2chart/tests/test_game_design/test_hopo_engine.py
- /home/adiel/Projects/music2chart/tests/test_game_design/test_sustain_processor.py (if integrating into test_hopo_engine.py, ensure no stale/conflicting tests remain)

Task Instructions:
1. Inspect the existing code in `src/game_design/` and tests in `tests/test_game_design/`.
2. Inspect `spec_miner_m4/spec_report.md` which has already designed the exact behavioral rules, API contracts, mathematical clamping formulas, and full 38-case test suite + E2E test.
3. Complete and polish `HopoEngine`, `SustainProcessor`, `StarPowerGenerator`, and ensure `src/game_design/__init__.py` properly exports all classes (`NoteQuantizer`, `QuantizedNote`, `PitchToFretMapper`, `ChordBuilder`, `HopoEngine`, `SustainProcessor`, `StarPowerGenerator`).
4. Write/update the complete test suite in `tests/test_game_design/test_hopo_engine.py` (and `test_sustain_processor.py` if kept separate) covering:
   - Natural HOPO threshold (<= 65 ticks with fret variation)
   - Strums (> 65 ticks)
   - Forced strums on repeated frets/chords
   - First note of track is always Strum
   - Chords and Open note interactions
   - Sustain cutoff (< 90 ticks -> 0)
   - Sustain margin calculation (duration - 24 ticks)
   - Next-note collision clamping (t_next - t_curr - 24 ticks)
   - Star power periodic phrases and empty/short chart handling
   - Pipeline E2E integration test
5. Run the required verifications using the local venv:
   - `.venv/bin/pytest tests/test_game_design/ -v`
   - `.venv/bin/pytest tests/ -v` (full project regression suite)
   - `.venv/bin/mypy src/game_design tests/test_game_design`
   - `.venv/bin/ruff check src/game_design tests/test_game_design`
   - `.venv/bin/ruff format --check src/game_design tests/test_game_design`
6. Maintain `progress.md` with your liveness heartbeat in your working directory.
7. Write your final report to `/home/adiel/Projects/music2chart/.agents/teamwork/worker_m4/handoff.md` with full test execution outputs, then notify me via send_message.
