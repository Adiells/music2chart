# Tooling, Linter, Type-Checker, and Test Suite Baseline Survey

**Date**: 2026-10-13  
**Subagent**: `explorer_survey_3`  
**Working Directory**: `/home/adiel/Projects/music2chart/.agents/teamwork/explorer_survey_3`  
**Target Subsystems**: `src/game_design/`, `tests/test_game_design/`, and global tooling baseline

---

## 1. Executive Summary

A comprehensive tooling and testing survey was performed for music2chart Phase 4.
The global project environment is healthy, fully typed, and passing existing regression tests (57 tests passing).
Currently, `src/game_design/` and `tests/test_game_design/` contain only stub `__init__.py` files. Consequently, running pytest targeted at `tests/test_game_design/` produces exit code 5 (`no tests ran in 0.00s`), while mypy and ruff report 0 errors on the existing stubs.

**Key Findings Summary**:
| Command / Target | Exit Code | Status | Notes |
|---|---|---|---|
| `pytest tests/` | 0 | **PASSED** | 57 passed across 9 test modules in 1.96s |
| `pytest tests/test_game_design/` | 5 | **NO TESTS** | Exit code 5: 0 test files collected (`__init__.py` only) |
| `mypy src/game_design tests/test_game_design` | 0 | **PASSED** | Success: 0 issues in 2 source files |
| `ruff check src/game_design tests/test_game_design` | 0 | **PASSED** | All checks passed |
| `ruff format --check src/game_design tests/test_game_design` | 0 | **PASSED** | 2 files already formatted |
| `mypy src tests` (Repo-wide) | 0 | **PASSED** | Success: 0 issues in 31 source files |
| `ruff check .` (Repo-wide) | 0 | **PASSED** | All checks passed across entire repo |
| `ruff format --check src tests` | 0 | **PASSED** | 31 source files already formatted |
| `ruff format --check .` | 1 | **WARNING** | Flags markdown Python block in `AGENTS.md` |

---

## 2. Environment & Tooling Configuration

### 2.1 Python Runtime & Virtual Environment
- **Virtual Environment Path**: `/home/adiel/Projects/music2chart/.venv`
- **Python Executable**: `/home/adiel/.local/share/uv/python/cpython-3.12-linux-x86_64-gnu/bin/python3.12` (symlinked via `.venv/bin/python`)
- **Python Version**: `3.12.14`
- **Tool Executable Paths**:
  - `pytest`: `/home/adiel/Projects/music2chart/.venv/bin/pytest` (version `9.1.1`)
  - `mypy`: `/home/adiel/Projects/music2chart/.venv/bin/mypy` (version `2.4.0`)
  - `ruff`: `/home/adiel/Projects/music2chart/.venv/bin/ruff` (version `0.17.0`)
- **Invocation Pre-requisite**: Global shell PATH does not include `.venv/bin`. Commands must be executed either with `source .venv/bin/activate && <command>` or via explicit binary prefix `./.venv/bin/<command>`.

### 2.2 pyproject.toml Configuration Analysis

#### pytest Configuration (`[tool.pytest.ini_options]`)
```toml
[tool.pytest.ini_options]
minversion = "8.0"
testpaths = ["tests"]
asyncio_mode = "auto"
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-ra -q --strict-markers -o cache_dir=/tmp/.pytest_cache"
```
- **Discovery**: Automatically discovers test files matching `test_*.py` under `tests/`. Classes must start with `Test`, functions with `test_`.
- **Asyncio**: `asyncio_mode = "auto"` automatically handles async tests without requiring manual loop fixtures.
- **Cache**: Pytest cache is redirected to `/tmp/.pytest_cache`, keeping repository workspaces clean.

#### ruff Configuration (`[tool.ruff]`)
```toml
[tool.ruff]
target-version = "py311"
line-length = 100
cache-dir = "/tmp/.ruff_cache"

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "B",    # flake8-bugbear
    "C4",   # flake8-comprehensions
    "UP",   # pyupgrade
]
ignore = [
    "E501", # line too long (handled by formatter)
]

[tool.ruff.lint.isort]
known-first-party = ["src", "config", "dataset"]
```
- **Line Length**: 100 characters.
- **Rules**: Enforces PEP 8 error/warning checks, Pyflakes, isort import order, bugbear, comprehensions, and Python 3.11+ upgrades (`UP`).
- **isort First Party**: `src`, `config`, and `dataset` must be sorted as local packages.
- **Formatting Caveat**: Running `ruff format --check .` attempts to reformat code snippets inside `.md` documentation files (`AGENTS.md`). For code verification, target `src` and `tests` (`ruff format --check src tests`).

#### mypy Configuration (`[tool.mypy]`)
```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
cache_dir = "/tmp/.mypy_cache"

[[tool.mypy.overrides]]
module = [
    "torch.*",
    "torchaudio.*",
    "librosa.*",
    "soundfile.*",
    "scipy.*",
    "basic_pitch.*",
    "demucs.*",
]
ignore_missing_imports = true
```
- **Strict Typing Policy**: `disallow_untyped_defs = true` and `disallow_incomplete_defs = true`. Every function/method signature in Phase 4 must provide complete type annotations for all arguments and return values.
- **Third-Party Overrides**: DSP and DL libraries (`torch`, `torchaudio`, `librosa`, `soundfile`, `scipy`, `basic_pitch`, `demucs`) ignore missing imports. Custom project modules (`src.models.*`, etc.) are strictly checked.

---

## 3. Baseline Command Execution Outputs

### Command 1: `pytest tests/`
- **Command**: `source .venv/bin/activate && pytest -v tests/`
- **Exit Code**: `0`
- **Output**:
```text
============================= test session starts ==============================
platform linux -- Python 3.12.14, pytest-9.1.1, pluggy-1.6.0
cachedir: /tmp/.pytest_cache
rootdir: /home/adiel/Projects/music2chart
configfile: pyproject.toml
plugins: asyncio-1.4.0, anyio-4.15.1, platformdirs-4.13.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collecting 5 items                                                             collected 57 items                                                             

tests/test_audio_processing/test_harmonic_filter.py .....                [  8%]
tests/test_audio_processing/test_pitch_transcriber.py ...                [ 14%]
tests/test_audio_processing/test_separator.py ....                       [ 21%]
tests/test_audio_processing/test_tempo_tracker.py .....                  [ 29%]
tests/test_config.py ....                                                [ 36%]
tests/test_dataset/test_chart_parser.py .....                            [ 45%]
tests/test_dataset/test_chorus_scraper.py .........                      [ 61%]
tests/test_dataset/test_evaluator.py .......                             [ 73%]
tests/test_models.py ...............                                     [100%]

============================== 57 passed in 1.96s ==============================
```

### Command 2: `pytest tests/test_game_design/`
- **Command**: `source .venv/bin/activate && pytest -v tests/test_game_design/`
- **Exit Code**: `5`
- **Output**:
```text
============================= test session starts ==============================
platform linux -- Python 3.12.14, pytest-9.1.1, pluggy-1.6.0
cachedir: /tmp/.pytest_cache
rootdir: /home/adiel/Projects/music2chart
configfile: pyproject.toml
plugins: asyncio-1.4.0, anyio-4.15.1, platformdirs-4.13.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 0 items                                                              

============================ no tests ran in 0.00s =============================
```
- **Error Analysis**: Pytest exit code 5 is defined by pytest specification as `ExitCode.NO_TESTS_COLLECTED`. The directory `tests/test_game_design/` currently contains only `__init__.py` and has no test files matching `test_*.py`.

### Command 3: `mypy src/game_design tests/test_game_design`
- **Command**: `source .venv/bin/activate && mypy src/game_design tests/test_game_design`
- **Exit Code**: `0`
- **Output**:
```text
Success: no issues found in 2 source files
```

### Command 4: `ruff check src/game_design tests/test_game_design`
- **Command**: `source .venv/bin/activate && ruff check src/game_design tests/test_game_design`
- **Exit Code**: `0`
- **Output**:
```text
All checks passed!
```

### Command 5: `ruff format --check src/game_design tests/test_game_design`
- **Command**: `source .venv/bin/activate && ruff format --check src/game_design tests/test_game_design`
- **Exit Code**: `0`
- **Output**:
```text
2 files already formatted
```

---

## 4. Current State of `src/game_design/` and `tests/test_game_design/`

### 4.1 Existing Files
1. `src/game_design/__init__.py`:
   - Content:
     ```python
     """Game design mapping intelligence for Clone Hero."""
     ```
   - Status: Empty module stub, valid syntax, properly formatted.
2. `tests/test_game_design/__init__.py`:
   - Content:
     ```python
     """Tests for game design modules."""
     ```
   - Status: Empty test package stub.

### 4.2 Missing Components Required for Phase 4
According to `AGENTS.md` (Sections 2, 4, 7) and `ORIGINAL_REQUEST.md`:

| Target Module | Target Test File | Responsibility |
|---|---|---|
| `src/game_design/quantizer.py` | `tests/test_game_design/test_quantizer.py` | Musical quantization & grid snapping to 192 PPQ subdivisions (1/4, 1/8, 1/12, 1/16, 1/24, 1/32) with 16-18 tick tolerance, deduplication while preserving velocity/amplitude. |
| `src/game_design/pitch_to_fret.py` | `tests/test_game_design/test_pitch_to_fret.py` | Dynamic sliding-window pitch projection mapping pitch tessitura percentiles into 5 frets (0 to 4) and Open Strum (7), jump penalty (>3 frets) in rapid passages (<48 ticks). |
| `src/game_design/chord_builder.py` | `tests/test_game_design/test_chord_builder.py` | Grouping simultaneous notes into valid Clone Hero chords (power chords, extended triads <= 3 frets), eliminating unplayable stretches. |
| `src/game_design/hopo_engine.py` | `tests/test_game_design/test_hopo_engine.py` | HOPO auto-detection (intervals <= 65 ticks with fret variation), strum forcing on identical fret repetitions. |
| `src/game_design/sustain_processor.py` | (Integrated in game design tests) | Sustain duration calculation with 24-tick release margin prior to consecutive notes; zero-length for notes < 90 ticks. |
| `src/game_design/star_power_generator.py` | (Integrated in game design tests) | Periodic Star Power phrases allocation. |

---

## 5. Existing Models Available for Phase 4

The following domain models in `src/models/` are tested and ready for immediate consumption by Phase 4 modules:

1. `src/models/midi_events.py`:
   - `NoteEvent(start_time: float, end_time: float, pitch: int, amplitude: float)`
   - Properties: `.duration` (seconds).
   - Validations: `start_time >= 0`, `end_time > start_time`, `0 <= pitch <= 127`, `0.0 <= amplitude <= 1.0`.

2. `src/models/tempo.py`:
   - `BPMChange(tick: int, bpm: float)`
   - `TimeSignature(tick: int, numerator: int, denominator: int)`
   - `TempoMap(resolution: int = 192, bpm_changes: list[BPMChange], time_signatures: list[TimeSignature])`
   - Methods: `tick_to_seconds(tick: int) -> float`, `seconds_to_tick(seconds: float) -> int`.

3. `src/models/chart.py`:
   - `FretType(IntEnum)`: `GREEN = 0`, `RED = 1`, `YELLOW = 2`, `BLUE = 3`, `ORANGE = 4`, `HOPO_FORCE = 5`, `STRUM_FORCE = 6`, `OPEN = 7`.
   - `ChartNote(tick: int, fret: FretType, sustain_length: int = 0, is_hopo: bool = False)`
   - `StarPowerPhrase(tick: int, length: int)`
   - `SongTrack(name: str, notes: list[ChartNote], star_power: list[StarPowerPhrase])`

---

## 6. Recommendations for Implementation and Testing

1. **Test Execution Protocol**:
   - Always invoke tests and quality checkers through `.venv`:
     ```bash
     source .venv/bin/activate && pytest tests/test_game_design/
     source .venv/bin/activate && pytest tests/
     source .venv/bin/activate && mypy src/game_design tests/test_game_design
     source .venv/bin/activate && ruff check src/game_design tests/test_game_design
     source .venv/bin/activate && ruff format --check src/game_design tests/test_game_design
     ```
2. **Pytest Exit Code 5 Resolution**:
   - Creating the first test file (e.g. `tests/test_game_design/test_quantizer.py`) with at least one test function will immediately resolve pytest exit code 5 to exit code 0.
3. **Type Safety**:
   - Every function in `src/game_design/` must be annotated with explicit argument types and return types to comply with `disallow_untyped_defs = true`.
4. **Formatting Scope**:
   - Target `src tests` when verifying code formatting with `ruff format --check src tests` to avoid checking documentation markdown files.
