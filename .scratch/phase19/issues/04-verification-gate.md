# Ticket 04 — Full verification gate and status records

Blocked by: 02, 03
Blocks: (none — final ticket)

Context pointers: `Phase19.md`, `AGENTS.md`, `upgrade-v2.md` (with ticket 03's placeholder), `.scratch/phase19/issues/02-build-pipeline.md` (what was measured).

## Task — run the full gate on a fresh worktree of the PR branch

1. `$env:QT_QPA_PLATFORM="offscreen"; pytest` — all green; record the count.
2. `$env:QT_QPA_PLATFORM="offscreen"; pytest -m acceptance` — all green; record the count.
3. `python build.py` — full clean build (allow up to 15 min).
4. `$env:QT_QPA_PLATFORM="offscreen"; dist\StepShot\StepShot.exe --smoke-test` — exit code 0; record wall time.
5. Measure: `dist/StepShot` folder size (MB), file count, `StepShot.exe` size.

## Task — record the real numbers

- `AGENTS.md` Status block: "All planned phases (1–18) complete" → "(1–19)"; update the pytest/acceptance counts and date; replace the frozen-build line with: onedir build `dist\StepShot\` (X MB, rebuilt 2026-09-10) passes its `--smoke-test` round-trip with exit code 0; note Phase 19 is tracked in `Phase19.md`.
- `upgrade-v2.md`: replace `**Verification: pending — filled by ticket 04.**` with the verification block in the repo's per-phase style (commands + results), including the before/after story (~250 MB one-file / 46–68s cold start → X MB onedir / measured smoke time).
- `upgrade-v2.md` session status: "Phase 19 complete and verified green… Next plan starts at Phase 20."

## Acceptance

- All four gates green with exit codes to prove it.
- Both docs carry the measured numbers; no placeholder remains.

## Commit

Single commit, repo style: `Phase 19: verification gate and status records`.
