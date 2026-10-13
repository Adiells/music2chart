## 2026-10-13T19:33:55Z
You are worker_m2, a Worker subagent for Milestone 2 of chartgen Phase 4.
Your working directory is: /home/adiel/Projects/music2chart/.agents/teamwork/worker_m2

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MANDATORY: Read /home/adiel/Projects/music2chart/.agents/teamwork/ORIGINAL_REQUEST.md before starting work.
Also read:
- /home/adiel/Projects/music2chart/.agents/teamwork/orchestrator/SCOPE.md
- /home/adiel/Projects/music2chart/.agents/teamwork/orchestrator/PROJECT.md
- /home/adiel/Projects/music2chart/.agents/teamwork/explorer_m2_1/handoff.md & analysis.md (windowing math & quartile anchoring)
- /home/adiel/Projects/music2chart/.agents/teamwork/explorer_m2_2/handoff.md & analysis.md (Open Note mapping & jump penalty directional clamping)
- /home/adiel/Projects/music2chart/.agents/teamwork/spec_miner_m2/handoff.md & spec_report.md (21 unit test cases for test_pitch_to_fret.py)

Write ownership:
You exclusively own and may modify or create:
- `src/game_design/pitch_to_fret.py`
- `src/game_design/__init__.py`
- `tests/test_game_design/test_pitch_to_fret.py`

Mission:
1. Implement `PitchToFretMapper` in `src/game_design/pitch_to_fret.py`:
   - `__init__(self, window_ticks: int = 1536, max_jump: int = 3, rapid_interval: int = 48, open_threshold: int = 40) -> None`
   - Open Note mapping: Notes with `pitch < open_threshold` map to `FretType.OPEN` (7). They are excluded from the sliding window percentile pool and excluded from fret leap distance metrics, and reset the fretting anchor state machine.
   - Sliding window: Centered window `[tick - window_ticks // 2, tick + window_ticks // 2]` across fretted notes.
   - 5-point quartile / percentile mapping:
     - Monotone / identical pitch in window -> Green (0).
     - Narrow range (< 5 semitones) -> map unique ranks directly to consecutive frets starting at Green (0).
     - Wide range (>= 5 semitones) -> partition percentiles into frets 0 to 4 (Green to Orange).
   - Rapid passage jump penalty: In rapid passages ($0 < \Delta\text{tick} < rapid_interval$), fret leap $> max_jump$ is directionally clamped: e.g. leap from 0 to 4 is clamped to 3 (Blue), leap from 4 to 0 is clamped to 1 (Red). Simultaneous notes ($\Delta\text{tick} = 0$) form chords and are not clamped by sequential jump penalty.
   - Method `map_notes(self, notes: Sequence[QuantizedNote]) -> list[ChartNote]` and alias `map = map_notes`. Returns `ChartNote`s with `sustain_length=0` and `is_hopo=False`, sorted deterministically by `(tick, fret)`.
2. Export `PitchToFretMapper` in `src/game_design/__init__.py` (retaining `NoteQuantizer` and `QuantizedNote`).
3. Implement all 21 unit test cases in `tests/test_game_design/test_pitch_to_fret.py` based on `spec_miner_m2/spec_report.md`.
4. Run all verification checks using `.venv`:
   - `.venv/bin/pytest tests/test_game_design/test_pitch_to_fret.py -v`
   - `.venv/bin/pytest tests/`
   - `.venv/bin/mypy src/game_design tests/test_game_design`
   - `.venv/bin/ruff check src/game_design tests/test_game_design`
   - `.venv/bin/ruff format --check src/game_design tests/test_game_design`
5. Write your complete handoff report documenting code changes and verbatim verification outputs to:
   `/home/adiel/Projects/music2chart/.agents/teamwork/worker_m2/handoff.md`

Send a completion message to the parent orchestrator when finished.
