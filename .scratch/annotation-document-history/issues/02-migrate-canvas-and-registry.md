# 02 — Migrate the canvas to document/history and the annotation adapter registry

**What to build:** The Qt canvas adapter translates its current background and scene annotations into framework-neutral document state and reconstructs them through a fixed annotation-adapter registry, preserving the complete editing workflow and rendered output.

**Blocked by:** 01 — Establish the framework-neutral annotation document/history module.

**Status:** complete — all tests green, mixed-annotation round-trip tests added, AGENTS.md updated

- [x] Create and restore records for every supported annotation family through the fixed registry.
- [x] Keep annotation records self-contained, ordered, and complete for geometry and all user-visible properties.
- [x] Keep image processing, Qt item creation, rendering, selection, view transforms, gesture state, and signal emission in the canvas adapter.
- [x] Route draw, move, resize, crop, effects, delete, duplicate, reset, undo, and redo through the document/history interface without changing observable behavior.
- [x] Preserve text-edit protection, property coalescing, invalid-operation no-op behavior, crop retention and translation rules, and one history entry per existing user-visible action.
- [x] Add mixed-annotation round-trip and rendered-output integration tests through the canvas interface.
- [x] Keep the current full and acceptance test suites green.

## Current state

Implemented and verified:

- `ui/annotation_adapters.py` — Qt↔record capture/restore for all seven families, plus
  `qpixmap_to_image_value` / `image_value_to_qpixmap`, `build_canvas_registry()`, and
  `capturable_types()`.
- `ui/canvas.py` — `_snapshot_state` / `_restore_state` / `_undo_stack` / `_redo_stack` replaced by
  `_capture_document_state` / `_restore_document_state` over a `DocumentHistory`, exposed via the new
  `history` property. Background `ImageValue` is cached on `QPixmap.cacheKey()`.
- `tests/test_ui/test_annotation_adapters.py` — per-adapter round-trip coverage, including
  odd-width stride and device-pixel-ratio preservation.
- `tests/test_ui/test_mixed_annotation_roundtrip.py` (new) — mixed-annotation round-trip tests with
  pixel-perfect rendered output verification across undo/redo cycles, multi-level undo/redo,
  new-action-after-undo semantics, load_image/reset_to_original history reset, and delete_selected.
- `StepShot.spec` — `ui.annotation_adapters` added to `hiddenimports`.

Suite: **264 passed** (`pytest -m acceptance`: 26 passed).

## Bugs found and fixed during verification

Both were in the migration code and took the suite from 68 failures to 22.

1. **Child-item guard destroyed scene items.** `item.parentItem()` inside `_capture_annotations`
   flipped Shiboken ownership to Python (`ownedByPython` False→True), so the loop variable going out
   of scope deleted the underlying C++ object — capturing state silently wiped annotations off the
   scene. The call was removed.
2. **`StepMarkerGraphicsItem` children aborted every history push.** It is a `QGraphicsItemGroup`,
   so its child `QGraphicsTextItem` / `QGraphicsEllipseItem` appear in `scene().items()`.
   `capture_annotation` raised `LookupError` on them and `_push_undo_state` swallows that, skipping
   the whole entry. `_capture_annotations` now filters on `capturable_types()`, which also prevents
   reintroducing bug 1.

## Additional fixes in this ticket (post-review hardening)

1. **Stacking-order reversal** — `_restore_document_state` now iterates `reversed(state.annotations)`
   so annotations are restored bottom-first, matching original scene order.
2. **Harden restore** — Restored items built into temp list first; `_validate_document` validates
   `BlurRecord.patch` is not None and `PenRecord.points` non-empty; scene only cleared and items
   added after all restores succeed.
3. **Null/0×0 pixmap guard** — `load_image` early returns on `pixmap.isNull()`. `ImageValue.__post_init__`
   rejects zero dimensions (aligns with `_validate_document`).
4. **Parity fixes** — `_property_timer.stop()` at top of `load_image` and `reset_to_original`.
   Rejected `apply` in `_push_undo_state` doesn't clear redo stack (test added:
   `test_rejected_apply_does_not_clear_redo_stack`).
5. **Fix `test_undo_stack_is_capped`** — Made pushes distinct by adding unique annotations each time.
6. **Derive `supported_versions`** — Replaced seven hardcoded `(1,)` literals with `_RECORD_VERSION`
   reference in `ui/annotation_adapters.py:_ADAPTER_SPECS`.

## Intentional behavior deltas documented

1. **State dedupe/coalescing** — Duplicate consecutive states are no longer pushed to history. The
   old code allowed duplicate entries; new `DocumentHistory.apply` returns `AcceptedMutation` without
   growing history when `new_state == current` at cursor end. Property setters coalesce via 400 ms
   timer (`_schedule_property_undo`).
2. **50-step depth includes initial state** — `HISTORY_CAP = 50` means 50 mutations *plus* the seed
   state (51 total `DocumentState` objects in `_history` list). This is by design; the cap limits
   user actions, not the seed.

## AGENTS.md updates

- Updated Status to reflect all phases complete with latest verification.
- Added mixed-annotation round-trip test file to testing notes.
- Documented the two intentional behavior deltas above.
