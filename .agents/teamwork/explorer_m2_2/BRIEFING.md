# BRIEFING — 2026-10-13T19:26:10Z

## Mission
Investigate and design jump penalty constraints, Open Note mapping, and API contract for PitchToFretMapper in Milestone 2.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigation, synthesis
- Working directory: /home/adiel/Projects/music2chart/.agents/teamwork/explorer_m2_2
- Original parent: c32a8c2d-046d-4e36-96ca-60cf3fc9e81f
- Milestone: Milestone 2

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Do NOT write to source files directly
- Write findings to analysis.md and handoff.md
- Send message to parent orchestrator upon completion

## Current Parent
- Conversation ID: c32a8c2d-046d-4e36-96ca-60cf3fc9e81f
- Updated: 2026-10-13T19:21:17Z

## Investigation State
- **Explored paths**: `src/models/chart.py`, `src/game_design/quantizer.py`, `src/game_design/__init__.py`, `tests/test_game_design/test_quantizer.py`, `tests/conftest.py`, `orchestrator/SCOPE.md`, `PROMPTS.md`, `AGENTS.md`.
- **Key findings**:
  1. Open Note mapping: Sub-bass notes (`pitch < 40`) map directly to `FretType.OPEN` (7) and must be excluded from sliding window fretted percentiles to prevent distortion of melodic solos. Open notes are excluded from fret leap distance metrics and reset the fretting anchor state machine.
  2. Rapid passage jump penalty: In rapid passages (`0 < interval < 48` ticks), fret leaps $> 3$ (Green 0 to Orange 4 and Orange 4 to Green 0) are clamped preserving motion direction: $0 \to 4$ becomes Blue (3); $4 \to 0$ becomes Red (1). Simultaneous notes ($\Delta\text{tick} = 0$) are never clamped.
  3. API & Output contract: `PitchToFretMapper.map_notes(notes: Sequence[QuantizedNote]) -> list[ChartNote]` returns notes with `sustain_length=0` and `is_hopo=False`, strictly sorted chronologically.
- **Unexplored areas**: None for Milestone 2 jump penalty and open note mapping scope.

## Key Decisions Made
- Excluded Open notes from fret leap distance calculations; Open notes reset the fretting anchor because an unfretted strum frees the player's left hand to reach any fret.
- Applied directional clamping formula $\text{prev\_fret} \pm \text{max\_jump}$ bounded to $[0, 4]$.
- Designed tick-grouped processing to cleanly handle simultaneous notes and prevent intra-chord clamping.

## Artifact Index
- /home/adiel/Projects/music2chart/.agents/teamwork/explorer_m2_2/analysis.md — Detailed analysis and architectural recommendations
- /home/adiel/Projects/music2chart/.agents/teamwork/explorer_m2_2/handoff.md — 5-component handoff report
