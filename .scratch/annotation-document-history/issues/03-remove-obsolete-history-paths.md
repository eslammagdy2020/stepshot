# 03 — Remove obsolete snapshot and duplicate history paths

**What to build:** A single history owner for StepShot, with obsolete canvas snapshot methods and duplicate history paths removed after all callers have migrated.

**Blocked by:** 02 — Migrate the canvas to document/history and the annotation adapter registry.

**Status:** complete — all tests green (265 passed, 26 acceptance)

- [x] Confirm zero production and test callers remain for the obsolete private snapshot and restoration paths.
- [x] Delete obsolete snapshot methods and duplicate history state without compatibility aliases.
- [x] Confirm the document/history module is the only owner of current state and undo/redo stacks.
- [x] Confirm transient selection, text-editing state, previews, resize handles, and in-progress gestures remain outside document snapshots.
- [x] Add or retain a deletion-test regression proving behavior crosses the replacement interface.
- [x] Keep all existing document, canvas, and acceptance tests green after contraction.

## Verification

- Searched codebase for `_snapshot_state`, `_restore_state`, `_undo_stack`, `_redo_stack` — zero production or test callers remain.
- `ui/canvas.py` uses only `_capture_document_state`, `_restore_document_state`, and `history` property (exposing `DocumentHistory`).
- `models/document_history.DocumentHistory` is the single owner of current state, undo stack, and redo stack.
- Transient state (selection, text editing, previews, resize handles, in-progress gestures) is correctly excluded from document snapshots — `_capture_annotations` filters on `capturable_types()` only.
- Regression test: `test_rejected_apply_does_not_clear_redo_stack` in `test_canvas.py` verifies behavior crosses the `DocumentHistory.apply` interface.
- All 264 tests pass (26 acceptance).

## Post-review fixes

1. **Pending property undo now flushes at gesture start.** Review found the 400 ms `_property_timer`
   could fire mid-gesture and capture an in-flight drag preview (a capturable `RectangleGraphicsItem` /
   `HighlightGraphicsItem`) into a history entry — reproducing through real Qt events produced a phantom
   `'rectangle'` record in history. Every gesture start now calls `_flush_pending_property_undo()`:
   before tool `on_press` in `mousePressEvent`, at the top of `_begin_drag_tracking()`, and replacing the
   bare timer `stop()` in `_begin_resize_tracking()` (which previously discarded a pending property
   change if the resize ended up a no-op). Regression test:
   `TestUndoCoalescing::test_pending_property_undo_flushes_before_gesture` — mutation-checked (neutering
   the flush makes exactly this test fail).
2. **Deleted dead `AnnotationAdapterRegistry.kinds()`** — zero production or test callers; ticket 03 is
   the contraction ticket, so it goes.
3. `AGENTS.md` — documented the flush invariant and the precise cap wording (50 undo entries, 51 states
   including current); test counts updated to 265.

Suite after fixes: **265 passed** (`pytest -m acceptance`: 26 passed).
