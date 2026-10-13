# Dispatch: challenger_m3_1
Adversarial stress-test Milestone 3 (ChordBuilder)
## 2026-10-13T20:23:49Z
You are challenger_m3_1, a Challenger subagent for Milestone 3 of chartgen Phase 4.
Your working directory is: /home/adiel/Projects/music2chart/.agents/teamwork/challenger_m3_1

MANDATORY: Read /home/adiel/Projects/music2chart/.agents/teamwork/ORIGINAL_REQUEST.md before starting work.
Also read:
- /home/adiel/Projects/music2chart/.agents/teamwork/orchestrator/SCOPE.md
- /home/adiel/Projects/music2chart/.agents/teamwork/worker_m3/handoff.md

Task:
Empirically stress-test `ChordBuilder` in `src/game_design/chord_builder.py`:
1. Author an adversarial test script or stress harness in your working directory (e.g. `adversarial_test.py`) that tests:
   - High-throughput streams with thousands of dense polyphonic clusters (10,000+ notes).
   - Massive clusters at a single tick: 10, 20, 50 notes at the exact same tick with mixed frets and open notes.
   - All $2^5 = 32$ possible combinations of 5 frets $\{0, 1, 2, 3, 4\}$ at a single tick: verify every combination outputs $\le 3$ frets, zero forbidden (0, 4) stretches, and valid canonical shapes.
   - Extreme sustain values and duplicate fret merging.
2. Run your harness using `.venv/bin/python` (DO NOT use BypassSandbox=true).
3. Report whether any invariant was violated, performance degraded, or unhandled exceptions occurred.
4. Record your findings and an explicit verdict: `APPROVE` or `REQUEST_CHANGES` in `/home/adiel/Projects/music2chart/.agents/teamwork/challenger_m3_1/handoff.md`. Send a completion message to the parent orchestrator when done.
