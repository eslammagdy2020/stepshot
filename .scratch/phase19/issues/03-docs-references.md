# Ticket 03 — Update docs for the onedir distribution

Blocked by: (none)
Blocks: 04

Context pointers: `Phase19.md` (spec), `AGENTS.md`, `upgrade-v2.md`.

## Task — `AGENTS.md` (Commands and body notes only; do NOT touch the Status numbers)

- Commands section: `dist\StepShot.exe` → `dist\StepShot\StepShot.exe` (run frozen build); smoke-gate line path update; build-command comment `→ dist/StepShot.exe (~250 MB one-file)` → `→ dist/StepShot/ (onedir)`.
- Keep the `runw.exe` windowed-bootloader note — still true under onedir.
- Update any other body reference to the one-file build to describe the folder build.

## Task — `upgrade-v2.md`

- Session status line "Next plan starts at Phase 19." → "Phase 19 (App Size & Startup Time Reduction) in progress — see `Phase19.md`."
- Renumber the old optional backlog to clear the Phase 19 slot: "## Phase 19 — Inventory Persistence (Optional, Post-MVP)" → "## Phase 20 — …" and "## Phase 20 — Thumbnail Strip / Visual Inventory Panel (Optional)" → "## Phase 21 — …". Check for internal cross-references to those numbers.
- Insert a new section (after the Phase 18 record, before the renumbered sections): "## Phase 19 — App Size & Startup Time Reduction" containing: pointer to `Phase19.md` as the spec; one-line summary (slim PyInstaller spec + onedir switch); key decisions (onedir only, onefile retired; `opengl32sw.dll` kept; UPX rejected; sharing via manual zip); and the line `**Verification: pending — filled by ticket 04.**`
- Match the existing file's style and tone. Fix nothing else.

## Acceptance

- No stale bare `dist\StepShot.exe` command references in `AGENTS.md`.
- `upgrade-v2.md` has exactly one Phase 19 section (ours); old optional sections are Phase 20/21.
- Verification placeholder present for ticket 04.
- Only `AGENTS.md` and `upgrade-v2.md` are touched.

## Commit

Single commit, repo style: `Phase 19: update docs for onedir distribution`.
