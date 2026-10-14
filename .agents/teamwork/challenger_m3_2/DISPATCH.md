# Dispatch: challenger_m3_2
Oracle property test Milestone 3 (ChordBuilder)

## 2026-10-13T20:23:49Z
You are challenger_m3_2, a Challenger subagent for Milestone 3 of music2chart Phase 4.
Your working directory is: /home/adiel/Projects/music2chart/.agents/teamwork/challenger_m3_2

MANDATORY: Read /home/adiel/Projects/music2chart/.agents/teamwork/ORIGINAL_REQUEST.md before starting work.
Also read:
- /home/adiel/Projects/music2chart/.agents/teamwork/orchestrator/SCOPE.md
- /home/adiel/Projects/music2chart/.agents/teamwork/worker_m3/handoff.md

Task:
Empirically verify `ChordBuilder` ergonomic constraints and property invariants:
1. Write an oracle or property-based verification harness in your working directory (e.g. `oracle_test.py`) to verify:
   - For every distinct tick in output, `len(frets_at_tick) <= 3`.
   - Never output isolated `{0, 4}` at any tick.
   - If `7` (Open) is in output at a tick, `len(frets_at_tick) == 1` (no frets 0-4 present).
   - Verify that all canonical power chords `{(0, 1), (0, 2), (1, 2), (1, 3), (2, 3), (2, 4), (3, 4)}` pass through 100% invariant.
   - Verify that all canonical triads `{(0, 1, 2), (0, 2, 3), (1, 2, 3), (2, 3, 4)}` pass through 100% invariant.
2. Run your harness using `.venv/bin/python` (DO NOT use BypassSandbox=true).
3. Record your findings and an explicit verdict: `APPROVE` or `REQUEST_CHANGES` in `/home/adiel/Projects/music2chart/.agents/teamwork/challenger_m3_2/handoff.md`. Send a completion message to the parent orchestrator when done.
