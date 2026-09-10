# Ticket 01 — Amend Phase19.md to the settled interview decisions

Blocked by: (none)
Blocks: 02

Context pointers: `Phase19.md` (the spec, at repo root). Decisions below come from the user interview on 2026-09-10; the user is non-technical, so the file should stay plain-language.

## Task

`Phase19.md` was written before the interview. Amend it so it is the single source of truth:

1. **Phase B:** remove the "retain the ability to build a `--onefile` executable (perhaps via a build flag)" item entirely. Final decision: `--onedir` is the **only** distribution format. No build flag, no onefile fallback.
2. **Sharing is manual:** the user zips `dist\StepShot\` by hand when sharing with colleagues. No auto-zip tooling.
3. **Phase C:** the smoke-test command becomes `$env:QT_QPA_PLATFORM="offscreen"; dist\StepShot\StepShot.exe --smoke-test`.
4. **Resolved Design Decisions:** update decision #1 to folder-only; add decisions: onefile build retired (no flag); no auto-zip; users = owner + a few colleagues; success bar = "opens fast" (no hard size or time number).
5. **Execution order:** note that Phase A and Phase B land as one change — the "measure Phase A before finalizing Phase B" step is obsolete because the distribution format was already decided in the interview. Measurement happens on the final onedir build.
6. Add a short "## Interview Decisions (2026-09-10)" section listing the six settled answers (audience, folder-only, fast-open bar, folder-only build, no shortcuts to preserve, manual zip).

## Acceptance

- No mention of retaining onefile build capability remains.
- Smoke-test path is `dist\StepShot\StepShot.exe`.
- Interview decisions section exists and matches the above.
- No other files are touched.
