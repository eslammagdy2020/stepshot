# 05 — Verify the complete refactor across document and canvas seams

**What to build:** A verified annotation document/history refactor whose framework-neutral state, Qt adapter, interaction workflows, rendered output, and frozen build preserve every existing contract.

**Blocked by:** 04 — Decouple tool handlers and MainWindow from canvas internals.

**Status:** complete — independently verified 2026-09-06

- [x] Verify document/history tests cover immutable state, image ownership, complete equality, version handling, atomic restoration, accepted/rejected mutations, undo/redo, history cap, and undo granularity.
- [x] Verify serialization tests cover every supported annotation family, mixed ordering, geometry, user-visible properties, metadata, background state, and fail-closed capture.
- [x] Verify canvas interaction tests cover draw, move, resize, crop, effects, select, delete, duplicate, reset, undo, redo, text-edit protection, and invalid-operation no-ops.
- [x] Verify rendered-pixel assertions and scene-space coordinate assertions cover visual and geometry behavior.
- [x] Run the full test suite under `QT_QPA_PLATFORM=offscreen` and the acceptance-marked suite.
- [x] Mutation-check the key regression tests by reverting and restoring each relevant production fix.
- [x] Run hidden-import verification and the frozen Windows smoke gate when new modules or build configuration are affected.
- [x] Record the explicit test delta and any accepted limitations in the canonical project history.

## Verification (independently re-run 2026-09-06)

**Coverage audit**

- Document/history (`tests/test_models/test_document_history.py`, 40 tests): immutability
  (frozen records, owned/copied pixel bytes), 6-axis complete equality, version handling,
  atomic restoration, accepted/rejected mutations (including malformed-document and
  non-record rejection), undo/redo direction, 50-entry cap, seeded initial state, and
  undo granularity via the 400 ms coalescing tests in `test_canvas.py`.
- Serialization (`test_annotation_adapters.py`, 15 tests): every one of the seven families
  round-trips; odd-width stride, device-pixel-ratio, position, geometry, color/opacity,
  text, blur patch metadata, pen points; fail-closed capture (unregistered item type) and
  restore (unknown kind).
- Canvas interactions: draw (arrow/rect/highlight/pen/step/text/blur/crop), move
  (`test_annotation_drag.py`), resize (`test_resize.py`), crop (`test_crop.py`), effects
  (`test_blur_redaction.py`), select/duplicate (`test_scenario3_features.py`), delete,
  reset, undo/redo incl. text-edit protection (`test_text_history.py`,
  `test_canvas.py`), invalid-operation no-ops (wholly-invalid crop, short arrow,
  single-point pen).
- Pixel/geometry assertions: `test_mixed_annotation_roundtrip.py` (6 tests) asserts
  pixel-perfect rendered output across undo/redo cycles, multi-level undo/redo,
  new-action-after-undo, load_image/reset history resets, and delete; drag/resize tests
  map viewport↔scene via `mapFromScene` rather than hardcoded pixels.

**Gates**

- `pytest` under `QT_QPA_PLATFORM=offscreen`: **292 passed**
- `pytest -m acceptance`: **26 passed**
- Hidden-import verification (`test_spec_hiddenimports.py`) green inside the 292 —
  `models.document_history`, `ui.annotation_adapters`, `tools.handlers.context` all listed.
- Frozen build: `dist\StepShot.exe` rebuilt 2026-09-06 10:59 from the committed tree
  (zero code diff HEAD↔working tree); `--smoke-test` exit code **0**.

**Mutation checks (production code reverted → exactly the targeted tests fail → restored)**

- Stacking order: `reversed(state.annotations)` → forward iteration in
  `_restore_document_state` — exactly 1 failure
  (`test_undo_redo_preserves_mixed_annotations_pixel_perfect`).
- `annotation_count()` → `return 0` — 5 failures (3 new MainWindow interface tests +
  2 pre-existing status-bar tests).
- `has_background()` → `return False` — exactly 1 failure (the new test is its only guard).
- Property-timer flush → bare `stop()` (ticket 03 post-review) — exactly 1 failure
  (`test_pending_property_undo_flushes_before_gesture`).

**Test delta: 202 → 292 (+90)**

- `tests/test_models/test_document_history.py`: 40 (33 at issue-01 commit + 7 hardening)
- `tests/test_ui/test_annotation_adapters.py`: 15
- `tests/test_ui/test_mixed_annotation_roundtrip.py`: 6
- `tests/test_ui/test_handler_context.py`: 27
- `tests/test_ui/test_canvas.py`: +2 regressions (`test_rejected_apply_does_not_clear_redo_stack`,
  `test_pending_property_undo_flushes_before_gesture`)

**Accepted limitations (carried, not regressions)**

- Crop retention is bbox-based (Phase 14 decision) — an arrow whose padded
  `sceneBoundingRect()` touches the crop is retained even if its line is outside.
- Blur patch is selectable but not movable and not duplicable (Phase 9 decision).
- `test_mixed_annotation_roundtrip.py:76` duck-types `BlurPatchGraphicsItem` via
  `__class__.__name__` (non-blocking nit, accepted).
