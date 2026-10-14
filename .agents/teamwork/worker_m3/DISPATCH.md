# Dispatch: worker_m3
Milestone 3 Implementation of ChordBuilder and Unit Tests
## 2026-10-13T20:13:32Z

You are worker_m3, a Worker subagent for Milestone 3 of music2chart Phase 4.
Your working directory is: /home/adiel/Projects/music2chart/.agents/teamwork/worker_m3

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MANDATORY: Read /home/adiel/Projects/music2chart/.agents/teamwork/ORIGINAL_REQUEST.md before starting work.
Also read:
- /home/adiel/Projects/music2chart/.agents/teamwork/orchestrator/SCOPE.md
- /home/adiel/Projects/music2chart/.agents/teamwork/orchestrator/PROJECT.md
- /home/adiel/Projects/music2chart/.agents/teamwork/explorer_m3_1/handoff.md & analysis.md (cluster simplification & canonical shapes)
- /home/adiel/Projects/music2chart/.agents/teamwork/explorer_m3_2/handoff.md & analysis.md (stretch elimination & open note exclusivity)
- /home/adiel/Projects/music2chart/.agents/teamwork/spec_miner_m3/handoff.md & spec_report.md (30 unit test cases for test_chord_builder.py)

Write ownership:
You exclusively own and may modify or create:
- `src/game_design/chord_builder.py`
- `src/game_design/__init__.py`
- `tests/test_game_design/test_chord_builder.py`

Mission:
1. Implement `ChordBuilder` in `src/game_design/chord_builder.py`:
   - `__init__(self, max_frets: int = 3, allow_wide_triads: bool = False, open_note_precedence: bool = True) -> None`
   - Grouping: Notes at the same `tick` are grouped into chord clusters.
   - Open Note exclusivity: If `FretType.OPEN` (7) is present in a cluster, drop any fretted notes (0-4) at that tick, keeping only the Open Note (preserving max sustain length).
   - Monophonic pass-through: Single notes pass through unchanged. Duplicate frets at same tick merged taking max sustain length.
   - Polyphonic cluster reduction (<= 3 frets):
     - Clusters with 4 or 5 notes simplified to at most 3 frets (e.g. mapping 4/5-note clusters to canonical triads `(0, 1, 2)`, `(0, 2, 3)`, `(1, 2, 3)`, `(2, 3, 4)`).
   - Canonical power chords preserved: (0, 1), (0, 2), (1, 2), (1, 3), (2, 3), (2, 4), (3, 4).
   - Canonical triads preserved: (0, 1, 2), (0, 2, 3), (1, 2, 3), (2, 3, 4).
   - Forbidden stretch elimination:
     - Isolated (0, 4) dyad simplified to (0, 2) (Green + Yellow).
     - Generalized dyad clamping: for any 2-note chord `(low, high)`, if `high - low > 2`, clamp `high = low + 2` (e.g. (0, 4) -> (0, 2), (0, 3) -> (0, 2), (1, 4) -> (1, 3)).
     - Triad stretch clamping: (0, 1, 4) -> (0, 1, 2), (0, 3, 4) -> (2, 3, 4), and (0, 2, 4) -> (0, 2, 3) unless `allow_wide_triads=True`.
   - Method: `build_chords(self, notes: Sequence[ChartNote]) -> list[ChartNote]` and alias `build = build_chords`.
   - Output sorting: deterministically sorted by `(tick, fret)` ascending.
2. Export `ChordBuilder` in `src/game_design/__init__.py` (retaining `NoteQuantizer`, `QuantizedNote`, `PitchToFretMapper`).
3. Implement all unit test cases in `tests/test_game_design/test_chord_builder.py` based on `spec_miner_m3/spec_report.md`.
4. Run all verification checks using `.venv` (DO NOT use BypassSandbox=true):
   - `.venv/bin/pytest tests/test_game_design/test_chord_builder.py -v`
   - `.venv/bin/pytest tests/`
   - `.venv/bin/mypy src/game_design tests/test_game_design`
   - `.venv/bin/ruff check src/game_design tests/test_game_design`
   - `.venv/bin/ruff format --check src/game_design tests/test_game_design`
5. Write your complete handoff report documenting code changes and verbatim verification outputs to:
   `/home/adiel/Projects/music2chart/.agents/teamwork/worker_m3/handoff.md`

Send a completion message to the parent orchestrator when finished.
