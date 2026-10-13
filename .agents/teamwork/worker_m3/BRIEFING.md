# BRIEFING — 2026-10-13T20:21:00Z

## Mission
Implement `ChordBuilder` in `src/game_design/chord_builder.py`, export in `src/game_design/__init__.py`, and implement comprehensive unit tests in `tests/test_game_design/test_chord_builder.py` meeting all game design constraints and pass all lint, type, and test suites.

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa, specialist
- Working directory: /home/adiel/Projects/music2chart/.agents/teamwork/worker_m3
- Original parent: c32a8c2d-046d-4e36-96ca-60cf3fc9e81f
- Milestone: milestone_3

## 🔒 Key Constraints
- Genuine implementation only, no dummy/facade implementations or hardcoded results.
- Write only to owned files: `src/game_design/chord_builder.py`, `src/game_design/__init__.py`, `tests/test_game_design/test_chord_builder.py`, and files in our teamwork folder.
- Group notes at the same tick into chords.
- Open Note exclusivity: if `FretType.OPEN` (7) present at a tick, drop all fretted notes (0-4), retain only open note with max sustain.
- Monophonic pass-through: single notes unchanged; duplicate frets merged taking max sustain.
- Cluster reduction: at most 3 frets (max_frets=3 by default); simplify 4/5-note clusters to canonical triads.
- Canonical power chords: (0, 1), (0, 2), (1, 2), (1, 3), (2, 3), (2, 4), (3, 4).
- Canonical triads: (0, 1, 2), (0, 2, 3), (1, 2, 3), (2, 3, 4).
- Stretch clamping:
  - Dyad: if `high - low > 2`, clamp `high = low + 2` (e.g. (0, 4) -> (0, 2), (0, 3) -> (0, 2), (1, 4) -> (1, 3)).
  - Triad: (0, 1, 4) -> (0, 1, 2), (0, 3, 4) -> (2, 3, 4), and (0, 2, 4) -> (0, 2, 3) unless allow_wide_triads=True.
- Deterministic output sorting by `(tick, fret)` ascending.
- Pass pytest, mypy, and ruff checks.

## Current Parent
- Conversation ID: c32a8c2d-046d-4e36-96ca-60cf3fc9e81f
- Updated: 2026-10-13T20:21:00Z

## Task Summary
- **What to build**: `ChordBuilder` class with `build_chords` and aliases (`build`, `process`, `__call__`); complete unit test suite in `tests/test_game_design/test_chord_builder.py`.
- **Success criteria**: All tests passing, full test suite passing (151 tests), mypy 0 errors, ruff check 0 errors, ruff format clean.
- **Interface contracts**: `src/models/chart.py` (`ChartNote`, `FretType`), `src/game_design/chord_builder.py`.
- **Code layout**: `src/game_design/chord_builder.py`, `tests/test_game_design/test_chord_builder.py`.

## Key Decisions Made
- Implemented `__init__` supporting both `open_note_precedence` and `prefer_open` aliases.
- Implemented generalized dyad clamping formula `if high - low > 2: high = low + 2` which precisely handles `(0, 4) -> (0, 2)`, `(0, 3) -> (0, 2)`, and `(1, 4) -> (1, 3)`.
- Implemented triad stretch clamping resolving `(0, 1, 4) -> (0, 1, 2)`, `(0, 3, 4) -> (2, 3, 4)`, and `(0, 2, 4) -> (0, 2, 3)` (or `(0, 2, 4)` if `allow_wide_triads=True`).
- Handled polyphonic 4/5-note cluster reductions mapping to canonical triads.
- Preserved modifier notes (`FretType.HOPO_FORCE`, `FretType.STRUM_FORCE`).
- Preserved max sustain length and hopo attributes during deduplication and open note precedence.

## Change Tracker
- **Files modified**:
  - `src/game_design/chord_builder.py`: Implemented `ChordBuilder` class with cluster reduction, stretch clamping, open note exclusivity, and output sorting.
  - `src/game_design/__init__.py`: Exported `ChordBuilder`.
  - `tests/test_game_design/test_chord_builder.py`: Comprehensive test suite covering 54 test invocations.
- **Build status**: All checks passed (151/151 tests passing, mypy 0 errors, ruff 0 errors).
- **Pending issues**: None.

## Quality Status
- **Build/test result**: 54/54 tests passed in `test_chord_builder.py`, 151/151 passed across entire suite.
- **Lint status**: 0 violations in `ruff check`, 0 formatting issues in `ruff format --check`.
- **Tests added/modified**: 54 test cases covering all 30 specification cases + edge cases.

## Loaded Skills
- None specified in dispatch.

## Artifact Index
- /home/adiel/Projects/music2chart/.agents/teamwork/worker_m3/progress.md — Liveness & progress tracking
- /home/adiel/Projects/music2chart/.agents/teamwork/worker_m3/handoff.md — Final handoff report
