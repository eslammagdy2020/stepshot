# StepShot — Upgrade Implementation Plan

Self-contained implementation guide for an AI coding agent (GLM or similar).
Work through tasks in order — later tasks depend on earlier ones.

---

## Session Status (updated 2026-09-06 — Phase 17 complete)

### Where to start next session
Phases 1–17 are complete and verified green. The last verified baseline is `pytest`
= 292 passed under `QT_QPA_PLATFORM=offscreen`, `pytest -m acceptance` = 26 passed,
and the frozen `dist\StepShot.exe` (2026-09-06 build) passes `--smoke-test` with
exit code 0. New work should be tracked in a new plan file; the Phase 17 records
below are the canonical history for the annotation document/history refactor.

### Done this session (Phase 17 — Issues 02–05, close-out)

Issues 02–05 implemented, reviewed, post-review fixed, and verified; recorded as
Tasks 17-02 through 17-05 below. Ticket records live in
`.scratch/annotation-document-history/issues/`.

### Done this session (post-review fixes)

Five real bugs and one UX question, all fixed:

- **#1 (Major) Handle size inverted relative to zoom.** `ui/resize_handles.py`
  `_compute_handles` divided `HANDLE_SCREEN_SIZE` by the view's zoom even though
  handle rects are drawn in viewport coordinates — so at low zoom the handles
  grew huge (covering the annotation) and at high zoom they collapsed to the
  floor. Now `size = HANDLE_SCREEN_SIZE` (constant 10 px on screen at every
  supported zoom). Mutation-checked.
- **#2 (Major) Stale handles after a Select-tool move.** `mouseReleaseEvent`
  in `ui/canvas.py` already ran `_commit_drag_tracking` on `_active_handler`
  release, but the select-tool drag path (the `ItemIsMovable` flow) never
  refreshed the resize layer. After a move, the handles still drew at the
  pre-move scene positions, so the next click landed on empty canvas and
  started another drag instead of a resize. Added
  `self._resize_layer.resize_to_viewport(self)` to the end of
  `_commit_drag_tracking` when `moved` is true. Mutation-checked.
- **#3 (Minor) Non-left release leaves the resize gesture half-open.**
  `mouseReleaseEvent` only handled the left button; any right/middle release
  returned without clearing `_resize_item` / `_resize_handle` /
  `_resize_geometry_before` / `_resize_pos_before`, so the next
  `mouseMoveEvent` kept mutating geometry. The else-branch now calls
  `_cancel_resize_tracking()`. Mutation-checked.
- **#4 (Minor) In-flight resize state survives undo / redo / load / reset /
  delete.** `_cancel_resize_tracking()` was only called from `set_tool_mode`
  and `_apply_crop`, so a keyboard-driven Ctrl+Z / Ctrl+Y / new-screenshot
  / Reset / Delete while a resize was in flight would dereference a
  detached item. The function is now also called at the top of `undo`,
  `redo`, `load_image`, `reset_to_original`, and `delete_selected`.
  Mutation-checked (`test_delete_selected_clears_in_flight_resize_state`
  catches the deletion revert).
- **#5 (Minor) Dead conditional in `PenStrokeGraphicsItem.__init__`.** Both
  branches of `if isinstance(path_or_start, QPointF)` were byte-identical
  (`self.path = QPainterPath(path_or_start)`). Collapsed to one line. Not
  behavior-mutation-testable (the runtime effect is the same), but the
  duplication invited a future fix that changes one side only.
- **Ctrl+Z / Ctrl+Y while a text item is in edit mode** (the unverifiable
  question in the review). Empirically: pressing Ctrl+Z in a text edit
  was undoing *only* the last text edit, not the previous canvas action.
  The toolbar's `QAction` shortcut is grabbed before the text doc's own
  undo runs, so the canvas's `undo()` was firing and *also* the text
  doc's undo was firing, but the test could only see the canvas state.
  Fix: `AnnotationCanvas.undo()` and `redo()` now early-return when
  `self._editing_text_item is not None` (after the safety-net calls to
  `_property_timer.stop()` and `_cancel_resize_tracking()`). The text
  doc's own Ctrl+Z / Ctrl+Y handlers take over for in-edit undo, and
  the canvas undo resumes once `_finalize_text_edit` clears
  `_editing_text_item`. Mutation-checked.

- **Verified green:** full `pytest` = 202 passed (was 193, +9 new);
  `pytest -m acceptance` = 26 passed. Each non-trivial fix is
  mutation-checked by reverting the production change and re-running
  the targeted test.

### Done this session (Phase 16)

- **[DONE] Phase 16 — Frozen Windows release validation** —
  `python build.py --no-clean` produces `dist\StepShot.exe` (~248.6 MB) on the
  first try using the existing `StepShot.spec` (no spec edits required: every
  first-party module is already in `hiddenimports`, `ui.resize_handles` included
  from the Phase 13 fix pass). Verified manually:
  - `dist\StepShot.exe --smoke-test` initializes `QApplication` (with
    `QT_QPA_PLATFORM=offscreen` so it runs headless), applies the theme, sets up
    logging, runs one event-loop tick, logs `smoke-test: Qt initialized, 1 screens`,
    and terminates with exit code 0.
  - Implementation: new `_smoke_test()` in `main.py` short-circuits
    `StepShotApp()` (and therefore `_register_hotkeys` / the `keyboard` import)
    for `--smoke-test`. Uses `os._exit(0)` rather than `SystemExit` because
    PyInstaller's `runw.exe` (windowed) bootloader keeps the host process
    alive across `SystemExit`; `os._exit` is the documented way to release
    the bootloader cleanly.
  - Caveat: the smoke run requires `QT_QPA_PLATFORM=offscreen` in the
    environment; a windowed run shows the main window normally (the spec
    already produced `console=False`, so `--smoke-test` is the only path
    that doesn't try to render to a screen).
  - Full test suite still green: `pytest` = 193 passed.

### Done this session (Phase 15)

- **[DONE] Phase 15 — Interaction-level acceptance coverage** — rewrote
  `tests/test_prd_acceptance/test_acceptance_criteria.py` so every test that claims a
  user workflow actually drives real Qt mouse / keyboard events through `qtbot`. Removed
  the four symbol-only checks (`test_rectangle_tool_module_exists`,
  `test_canvas_has_rectangle_mode`, `test_highlight_tool_in_left_toolbar`,
  `test_blur_tool_module_exists`); the toolbar / module existence is now implicit in
  the tool-driven tests. Replaced `test_arrow_is_movable` (was `arrow.setPos(20, 30)`)
  with a real Select-tool drag and an end-position assertion. Replaced
  `test_user_can_select_and_delete_annotation` with a real click-to-select + delete +
  undo round-trip. Renamed `test_unlimited_undo_during_session` to
  `test_undo_and_redo_around_fifty_state_cap` and added `test_redo_clears_after_new_action`
  (both test the real 50-state cap, not the previous "≤4 markers" fiction).
  Added `test_duplicate_creates_offset_copy_via_shortcut`,
  `test_filled_rectangle_appears_in_rendered_pixmap`,
  `test_highlight_modifies_rendered_pixels`, `test_blur_and_pixelate_modes_modify_pixels`,
  and `test_crop_updates_rendered_pixmap_dimensions` — each compares pixel values
  before vs after, or the rendered output dimensions, not just item counts.
  - **Stale marker / doc cleanup:** dropped the unused `not_implemented` marker from
    `pytest.ini`, the matching `pytest -m "not not_implemented"` line from
    `tests/README.md`, and the matching sentence in `AGENTS.md`; updated the
    acceptance module docstring to describe what the file actually does.
  - Verified green: `pytest -m acceptance` = 26 passed; full `pytest` = 193 passed.

- **[DONE] Phase 14 — Crop boundaries and annotation retention** —
  `AnnotationCanvas._apply_crop(rect)` now intersects the requested crop with the background's
  logical bounds before copying, returns `False` (a no-op that creates no history) when the
  intersection is degenerate or the physical copy is empty, removes annotations whose
  `sceneBoundingRect()` does not intersect the effective crop, translates retained annotations
  and blur-patch `source_rect`s by the **effective clamped origin** (not the requested origin),
  and finally intersects the physical copy rect with the pixmap bounds as a DPR-rounding guard.
  Reset All still restores the pre-crop `_original_pixmap` by design (unchanged).
  - Handler plumbing: `RectDragHandler.on_release` now gates the undo push + `image_changed`
    emit on `_commit`'s return value; rectangle / highlight / blur `_commit`s return `True`
    explicitly, and `CropHandler._commit` returns `canvas._apply_crop(rect)` — so a wholly
    invalid crop gesture creates no history and no stale status-bar update, while valid crops
    push exactly one state.
  - New `tests/test_ui/test_crop.py` (10 tests): in-bounds copy dimensions, clamping on all
    four sides, wholly-invalid no-op (direct + through the real CROP handler via synthesized
    mouse events, asserting no history and no `image_changed`), fully-outside removal,
    partially-intersecting retention with correct relative positions for arrows
    (`start_point + pos()`) and rectangles (`pos()` + uncorrupted local rect), and the
    undo / redo round-trip restoring the pre-crop image and full annotation set.
  - Verified green: focused `pytest tests/test_ui/test_crop.py` = 10 passed; full `pytest`
    = 189 passed; acceptance = 24 passed.

### Done this session (Phase 13)

- **[DONE] Phase 13 — Annotation resizing decision and implementation** —
  Resize is implemented (Scope 1 from the spec's Required decision). The product already
  shipped "resize" in user-facing copy (`test_draw_move_resize_change_color_and_thickness` +
  `select, move, delete, resize` docstring); removing the requirement would have been a
  user-visible regression.
  - **Scope:** arrow endpoints and rectangle / highlight boxes. Text, pen, and blur patches
    are explicitly out of scope (per the spec's "do not add generic scaling accidentally").
    Step markers are also out of scope — their `marker_size` is a property, not a geometry
    resize.
  - **One handle layer, two families.** New `ui/resize_handles.py` (`ResizeHandleLayer`,
    `HandleRole`, `Handle`) is owned by the canvas and shown only when exactly one resizable
    item is selected in `ToolMode.SELECT`. The layer is a transparent widget on the viewport
    (not in the scene), so handles never enter snapshots, exports, or clipboard output.
    2 endpoint handles for arrows; 4 corner + 4 edge handles for rectangle-style items; all
    sized in screen pixels (`10 px / zoom`, floor 6) so they stay usable at every supported
    zoom.
  - **One gesture, canvas-owned.** Left-press on a handle captures pre-resize geometry and
    intercepts `mouseMoveEvent` / `mouseReleaseEvent`; the canvas projects the move delta
    through one of two small pure functions (`_project_arrow` / `_project_rect`) and calls
    `item.set_geometry(...)` (a new method on each resizable item class that calls
    `prepareGeometryChange()` and clamps via `normalized()` + 4-pixel minimum). On release,
    exactly one undo state is pushed if geometry changed. The pattern mirrors Phase 10's
    drag tracking.
  - **`set_geometry` on the items.** `ArrowGraphicsItem` gains `set_geometry(start, end)`;
    `RectangleGraphicsItem` and `HighlightGraphicsItem` gain `set_geometry(rect)`. Snapshot
    format is unchanged (arrows already stored absolute start/end; rectangles stored `pos()`
    + local `QRectF`).
  - **Refresh hooks.** `scene.selectionChanged` triggers `_refresh_resize_layer`; viewport
    resize and `zoom_to_fit` call `_resize_layer.resize_to_viewport`. Property changes
    (color / thickness) do not move geometry, so the layer does not need to refresh on
    those.
  - **Tests.** New `tests/test_ui/test_resize.py` (9 tests) covers arrow endpoint resize,
    rectangle corner / edge / minimum-size clamp, highlight opacity preservation across
    resize, undo / redo round-trip on both arrow and rectangle, and the layer-hide
    behavior for no-selection and non-resizable items. The acceptance test
    `test_draw_move_resize_change_color_and_thickness` now exercises real resize via mouse
    input (handle-press + drag + release) and asserts the undo contract end-to-end.
  - Verified green: focused `pytest tests/test_ui/test_resize.py` = 13 passed; full
    `pytest` = 179 passed; acceptance = 24 passed.
- **Phase 13 fix pass (post-review):**
  - **B1 fixed.** `AnnotationCanvas._project_rect` now subtracts `item.pos()` from
    `scene_pos` before computing the new local rect. Without this, resizing any
    `RectangleGraphicsItem` / `HighlightGraphicsItem` whose `pos() != (0, 0)` produced
    geometry that overshot by exactly `pos()` and grew visibly with each drag. Two new
    regression tests (`TestResizeAtNonZeroPos`) cover both an arrow and a rectangle
    placed at `pos = (100, 100)` and assert the resulting scene-space bottom-right.
  - **B2 fixed.** `ArrowGraphicsItem.set_geometry` now refuses any update that would
    collapse the arrow below 4 scene-units (manhattan length), matching the rectangle
    / highlight 4-pixel floor. The existing `TestRectangleResize::test_minimum_size_clamped_to_four_pixels`
    covers the same invariant for rectangles.
  - **H1 fixed.** `AnnotationCanvas` now overrides `scrollContentsBy`, `scale`, and
    `resetTransform` to call `self._resize_layer.resize_to_viewport(self)`. Together
    with the existing `resizeEvent` and `zoom_to_fit` hooks, handles now track the
    selected item through every supported pan / zoom path (scrollbar drag, scroll-wheel,
    toolbar zoom in / out / reset, fit-to-window).
  - **S1 fixed.** Class docstring removed from `ResizeHandleLayer`; the one-line
    module docstring is kept.
  - **S2 / smell cleanup.** `_project_arrow` and `_project_rect` now use typed
    parameters and compare `handle.role` against `HandleRole` enum members (not
    `handle.role.value` strings). The resize state fields (`_resize_handle`,
    `_resize_geometry_before`, `_resize_item`) are now type-annotated. The
    rect/highlight min-size clamp is shared via a `_clamp_min_size` helper in
    `graphics_items.py`. The press / move / release test helper is now
    `tests.conftest.py::drag_on_canvas` and is used by both `test_resize.py` and
    the acceptance test.
  - **Test gaps closed.** New `test_highlight_undo_redo_round_trip` and
    `TestResizeRenderedOutput::test_resized_rectangle_appears_in_rendered_pixmap`
    (a pixel assertion through `render_to_pixmap`).
  - **Regression-safe documented intent:** handle size is constant in screen pixels
    (10 px), as the code now enforces after the bug-2 fix below. The earlier prose
    in this file (which mixed "8 px / zoom" and "constant in screen pixels") is
    reconciled with the implementation.
- **Phase 13 second fix pass (follow-up review):**
  - **B1 arrow half fixed.** `_project_arrow` now subtracts `item.pos()` from `scene_pos`
    exactly as `_project_rect` already did (both take `item_pos` from `_apply_resize_to`).
    The first fix pass had corrected rectangles only; an arrow with `pos() != (0, 0)` (e.g.
    after a Select-tool drag) still resized with its visual endpoint overshooting by exactly
    `pos()`.
  - **False-negative regression test fixed.**
    `TestResizeAtNonZeroPos::test_arrow_resize_preserves_scene_endpoint` now calls
    `arrow.setPos(100, 100)` and asserts the visual endpoint (`end_point + pos()`) tracks
    `canvas.mapToScene(cursor)` — mutation-checked: reverting the `_project_arrow` fix makes
    exactly this test fail. The odd
    `type(canvas._resize_layer._handles[1].role).__members__["ARROW_END"]` role lookup was
    replaced with a plain `HandleRole.ARROW_END` import.
  - **Type annotations now resolve at runtime.** `typing.get_type_hints` on
    `ResizeHandleLayer.update_for_item` / `AnnotationCanvas._begin_resize_tracking` /
    `_capture_geometry` / `_project_arrow` all succeed: `QGraphicsView` is imported for real
    in `resize_handles.py` (a `TYPE_CHECKING` guard would not satisfy `get_type_hints`),
    and `Handle` / `HandleRole` / `ResizeHandleLayer` are hoisted to module level in
    `canvas.py`. `paintEvent(self, event: QPaintEvent | None)` and `_capture_geometry(...)`
    are fully typed. `target()` returns the item union instead of `object | None`.
  - **Function-local imports removed.** The `__init__`-scoped `ResizeHandleLayer` import and
    the two `HandleRole` imports inside the static projectors are gone; module-level only
    (no import cycle: `resize_handles` imports only `graphics_items`).
- **Phase 13/14 third fix pass (review findings):**
  - **`prepareGeometryChange()` ordering fixed.** `ArrowGraphicsItem.set_geometry` now
    checks the minimum-length guard *before* calling `prepareGeometryChange()`, so a
    rejected degenerate update no longer leaves Qt notified of a geometry change that
    never happens.
  - **Undo comparison is now position-aware.** `_begin_resize_tracking` additionally
    captures `item.pos()` into `_resize_pos_before`, and `_commit_resize_tracking` pushes
    history when geometry *or* position changed. This removes the asymmetry where rect
    items were compared by local rect and arrows by local endpoints; mid-gesture `pos()`
    changes (only possible via programmatic API misuse today) can no longer slip past the
    comparison.
  - **Resize tracking state cleared on mode change and crop.** New
    `_cancel_resize_tracking()` nulls the four gesture fields; called from
    `set_tool_mode` (any mode change) and at the top of `_apply_crop`, so a stale
    `_resize_item` reference can never survive into a crop's scene mutation. Pinned by
    two new tests (`test_tool_mode_change_clears_in_flight_resize_state`,
    `test_apply_crop_clears_in_flight_resize_state`).
  - **Accepted limitation (documented, not fixed):** crop retention tests intersect via
    `sceneBoundingRect()`, which for arrows includes `max(12, thickness*4)` padding — an
    arrow whose *line* is outside the crop but whose padded bbox touches it is retained
    (invisible, slightly inflating the count). Fixing this requires overriding
    `shape()` on `ArrowGraphicsItem`, which would also tighten selection hit-testing
    app-wide; that behavior change is not worth the edge case. Retention is the safe
    direction (never destroys visible content).

### Done this session (Phase 12)

- **[DONE] Phase 12 — Cross-monitor and mixed-DPI region capture** —
  `ScreenshotService.capture_region()` intersects the requested global rect with every
  `QGuiApplication` screen it crosses, grabs each panel from that screen's local origin in
  **logical pixels** (matching Qt 6's `QScreen.grabWindow(0, x, y, w, h)` contract, where x/y/w/h
  are device-independent and Qt scales internally based on `devicePixelRatio`), and composes
  the pieces into one output pixmap whose pixel dimensions equal the requested `rect.width() ×
  rect.height()` and whose `devicePixelRatio` is set from the first intersecting screen. Qt's
  `QPainter::drawPixmap` handles the native-to-output scaling, so per-panel rescale code is not
  needed. Single-screen, negative-coord, mixed-DPI, no-intersection, and partial-grab-failure cases
  are all covered. Two review passes after the first cut: the first removed the single-screen fast
  path (coordinate-origin drift on secondary monitors) and the orphaned helpers
  (`screen_for_rect` / `to_native_rect` / `_to_logical` / `normalize_pixmap`); the second caught a
  pre-existing test assertion that asserted native dimensions against a now-logical-sized output
  and (more importantly) caught that the first rewrite was multiplying by DPR before
  `grabWindow` and re-scaling after — a redundant round-trip that would have visibly
  zoomed/shifted pixels on a real 150% / 200% monitor even though output dimensions stayed
  correct. The current code passes logical pixels to Qt and lets Qt do the scaling.
  - `services/screenshot_service.py` keeps `screens_intersecting(rect)`; `capture_region` is one
    unified composition loop with no DPR pre-multiplication, no post-grab rescale, and a single
    `setDevicePixelRatio(...)` on the output. `capture_full_screen` now also uses `try/finally`
    to release its `QPainter` and raises on any failed panel grab, matching the region path.
  - `TestCrossMonitorCapture` suite (6 tests) uses a `_MockScreen` that synthesizes a grab of
    the requested `(w, h)` and asserts on `grabWindow` call args, output dimensions, pixel
    sampling at known positions, and the new error paths. The mixed-DPI test now pins the
    `grabWindow` call to **logical** pixels (`high.calls == [(0, 100, 100, 100)]`).
  - `test_capture_region_returns_valid_pixmap` now asserts `pixmap.width() == rect.width()` and
    `pixmap.devicePixelRatio() == screen.devicePixelRatio()` — the logical-sized, DPR-aware
    contract.
  - **Spec-mandated manual Windows two-monitor smoke check: pending.** Phase 12's acceptance
    criteria explicitly require a documented manual run on real hardware. The offscreen
    platform reports DPR=1.0, so neither the high-DPI scaling behavior nor the per-screen
    `grabWindow` origin convention is exercised by the automated suite. Record the result in
    this block once performed; the most important verifications are (a) a region wholly on a
    secondary monitor captures the requested logical area, (b) a region crossing two monitors
    contains correctly positioned pixels from both, and (c) on a 150% / 200% display the
    captured pixels are not zoomed or shifted.
  - Verified green: focused `pytest tests/test_services/test_screenshot_service.py` = 11 passed;
    full `pytest` = 166 passed; acceptance = 24 passed.

### Done this session (Phase 11)

- **[DONE] Phase 11 — Atomic text creation and editing history** — text placement + first typing is
  now one undoable action, and all existing-text editing routes through canvas-owned history.
  - `TextHandler.on_press` no longer pushes undo or emits `image_changed` at create time; it marks
    the placeholder (`is_placeholder = True`) and starts the edit with `is_new=True`. Creation no
    longer double-pushes history.
  - `TextGraphicsItem` gains `is_placeholder`/`on_focus_out` fields, a `keyPressEvent` override that
    clears the placeholder text on the first keystroke, flag-based `finalize_editing` (blanks only
    when `is_placeholder` is still True — no longer special-cases the `"Enter instruction..."`
    string), and a canvas-routed `focusOutEvent`. `mouseDoubleClickEvent` was removed from the item.
  - `_start_text_edit(item, *, is_new=False)` captures the before-edit text and installs
    `on_focus_out`. Rewritten `_finalize_text_edit` is the single commit point: it nulls state and
    the callback first (re-entrancy-safe), discards empty new items with no history, commits a
    cleared existing item as a real change, and otherwise pushes exactly one state only when the
    text differs from before.
  - New `AnnotationCanvas.mouseDoubleClickEvent` routes double-click editing through the canvas
    regardless of active tool, finalizing any in-progress edit first.
  - New helper `double_click_on_canvas(canvas, app, scene_pos)` in `tests/conftest.py`; new suite
    `tests/test_ui/test_text_history.py` (8 tests) covering create+undo/redo, placeholder never
    surfacing, empty-new-no-history, edit undo/redo, no-change-no-history, double-click routing,
    Escape finalize, and multiline survival. Fixed
    `test_click_away_finishes_text_without_adding_another` for the placeholder-flag path.

### Done this session (Phases 9–10)

- **[DONE] Phase 10 — Undoable annotation movement** — a Select-tool mouse drag now commits exactly
  one undo state. The canvas snapshots every non-background item's position on left-press in SELECT
  mode (`_begin_drag_tracking`, stored in `self._drag_positions`), and on release
  (`_commit_drag_tracking`) pushes one history state + emits `image_changed` only if any position
  actually changed. Clicks and rubber-band selection without movement leave history untouched, and
  intermediate mouse-moves never push. Orchestration lives entirely on the canvas — graphics items
  are unchanged and know nothing about the undo stack. Wiring is in `mousePressEvent` (SELECT +
  left button → `_begin_drag_tracking`) and `mouseReleaseEvent` (→ `_commit_drag_tracking` before
  `_emit_selection`).
  - New helper `drag_item_on_canvas(canvas, app, scene_start, scene_end)` in `tests/conftest.py`
    drives a real press→move→move→release `QMouseEvent` sequence through the viewport.
  - New test suite `tests/test_ui/test_annotation_drag.py` (10 tests): one drag → one undo; undo
    restores original position and redo the final (asserted via `sceneBoundingRect().center()` since
    `ItemIsMovable` uses item-local coords, not `pos()`); click-without-move changes nothing; a
    property edit before a move retains correct undo order; and drag-is-undoable for all six movable
    families (arrow, rectangle, step, text, highlight, pen). Blur patches are non-movable (Phase 9)
    so they are correctly excluded.
  - Verified green: full `pytest` = 152 passed.

- **[DONE] Phase 9 — Safe blur/redaction** — the "preferred" redaction model from the plan was
  already implemented in the code (this doc's prose was stale): `BlurPatchGraphicsItem` sets only
  `ItemIsSelectable` (never `ItemIsMovable`, `ui/graphics_items.py:420`), `_clone_item()` has no
  blur branch so `duplicate_selected()` skips patches, original pixels stay in the background, and
  crop already translates the patch + `source_rect` together. The genuine gaps closed:
  - **Snapshot aliasing bug fixed.** `_snapshot_state()` stored the *live* `item.source_rect`
    `QRectF` into the "blur" tuple, and `_restore_state()` handed the stored rect straight back into
    the rebuilt patch. A later in-place `source_rect.translate()` (crop) retroactively mutated undo
    snapshots, so undoing a crop left the patch's `source_rect` at the cropped coordinates. Both
    sides now copy via `QRectF(...)` (`ui/canvas.py` snapshot ~815 and restore ~882).
  - **New pixel-level test suite** `tests/test_ui/test_blur_redaction.py` (9 tests) over a
    non-uniform gradient source; see git history for coverage detail.

### Done this session (Phase 7 + Phase 8)

- **[DONE] Phase 7 — Operations**
  - **Logging** — `main.py` gains a module `logger` (`"stepshot"`) and `_setup_logging()`, which
    attaches one `RotatingFileHandler` (1 MB × 2 backups) at
    `QStandardPaths.AppLocalDataLocation/stepshot.log`, falling back to the CWD when the directory
    cannot be created. It is idempotent (returns early if handlers exist) and called from
    `StepShotApp.__init__` after `QApplication` naming so the path resolves under `StepShot/`.
    Capture failures in `_capture_full_screen()` / `_capture_pending_region()` now log before the
    `QMessageBox`, and hotkey-registration failures log with `logger.exception()` instead of being
    swallowed.
  - **Keyboard-thread marshaling** — `capture_signals.region_requested` /
    `full_screen_requested` are connected with explicit `Qt.ConnectionType.QueuedConnection`,
    so `keyboard`'s worker-thread callbacks are marshaled to the GUI thread. The direct
    `main_window.*_requested` connections are left as-is: they already emit on the GUI thread.
  - **CI** — new `.github/workflows/ci.yml`: `pytest` on `ubuntu-latest` + `windows-latest`,
    `QT_QPA_PLATFORM=offscreen`, Python 3.13 (PySide6 6.11.1 ships `cp310-abi3` wheels; there is
    no 3.14 wheel yet), pip caching, and the `libegl1`/`libxcb-*` runtime libs Qt needs on Linux.
  - New tests: `tests/test_main/test_app_operations.py` (4 tests) covering handler creation,
    idempotency, and both capture-failure logging paths.
- **[DONE] Phase 8 — Hardening**
  - **H1** — `StepShot.spec` `hiddenimports` gains the 10 missing `tools.handlers*` entries, and
    `tests/test_build/test_spec_hiddenimports.py` now fails whenever a first-party module in
    `ui`/`services`/`models`/`tools` is absent from the list. Mutation-checked: deleting an entry
    fails with `Add to StepShot.spec hiddenimports: [...]`.
    `python build.py` was run end-to-end: it succeeds and produces `dist/StepShot.exe` (~248.6 MB).
    The frozen archive was inspected to confirm every `tools.handlers.*` module is embedded
    (`main` appears as the `PYSOURCE` entry-script in the PKG rather than in the PYZ, which is
    expected). The EXE on disk predates a later cosmetic docstring removal in `main.py`; rebuild
    if a byte-current binary is needed.
  - **H2** — `qpixmap_to_pil()` now passes `image.bytesPerLine()` as the raw decoder stride and
    reads through `constBits()` (no detach). Verified byte-identical output to the previous
    implementation on a striped 199×97 pixmap, and both blur and pixelate still render.
    New test `test_qpixmap_to_pil_handles_odd_widths` guards row mapping at width 37.
  - **H3** — `MIN_ZOOM`/`MAX_ZOOM` constants plus `zoom_to_fit()` / `clamp_zoom()` moved onto
    `AnnotationCanvas`; all three internal `fitInView` calls (`load_image`, `reset_to_original`,
    `_apply_crop`) now route through `zoom_to_fit()`, so fit can no longer escape the bounds.
    `load_image()` emits `image_changed`, and `MainWindow` connects that signal to
    `_update_zoom_indicator` as well as `_update_annotation_count`, fixing the stale `Zoom: N%`
    after Reset All / crop and the stale count after a new capture. `_scale_zoom` consumes the
    shared constants; `_zoom_reset` is unchanged. 5 new tests in `TestZoomIndicator` /
    `TestAnnotationCount`.
  - The predicted regression risk did not materialize: the 0.0625 fit scale for an unshown view
    stays above the 0.05 floor, so `clamp_zoom()` is inert there and every tool-coordinate test
    still passes.
  - **H4** — `AGENTS.md` synced: `.github/workflows/`, `tests/test_main/`, `tests/test_build/` in
    the tree; corrected line anchors in the Key Classes and Graphics Items tables (they had
    drifted); `settings_service` described as a module rather than a class; new conventions for
    logging, hotkey threads, zoom bounds, status-bar freshness, and the stride-safe conversion.

### Done in earlier sessions (verified green: `pytest` = 122 passed, acceptance = 24 passed)

- **[DONE] Phase 3 — Performance**
  - **P1** — `services/image_effects.py`: `qpixmap_to_pil()` now uses raw RGBA bytes
    (`QImage` → `bytes(image.bits())`); no more PNG round-trip via `BytesIO`/`QBuffer`.
    (Superseded by H2, which adds the stride and switches to `constBits()`.)
  - **P2** — `ui/canvas.py`: `drawBackground()` fills the viewport with a cached 32×32
    checkerboard `QBrush` (`_build_checker_brush()`) instead of a per-frame cell loop.
- **[DONE] Phase 4 — UX polish**
  - **X1** — `ui/main_window.py`: `_sync_panel_values(item)` populates spinbox/checkbox/slider/
    swatch from the selected item via `_set_widget_value()` (blockSignals-guarded). Wired into
    `_update_properties_panel()`.
  - **X2** — Tool defaults persist via new `services/settings_service.py` (`load`/`save` using
    QSettings org/app `StepShot`). `canvas` loads defaults in `__init__`, saves in `_save_tool_defaults()`
    (called by every setter), exposes `get_tool_settings()`. Panel initializes from canvas via
    `_sync_panel_from_defaults()`. Tests redirect persistence to an in-memory store via the new
    autouse `isolated_settings` fixture in `tests/conftest.py`.
  - **X3** — `TopToolBar` gains Zoom Fit (`Ctrl+0`) and Zoom 100% (`Ctrl+1`); zoom capped
    (5%–1600%); permanent status-bar `_zoom_label` shows `Zoom: N%` (`_update_zoom_indicator`).
  - **X4** — `TextGraphicsItem` draws a contrast backdrop: `paint()` renders a rounded rect
    (dark for light text, light for dark text via `_backdrop_color()`); `boundingRect()` adds margin.
- **[DONE] Phase 5 — Features**
  - **F1** — `LeftToolBar` adds `QShortcut` per tool (`TOOL_KEYS`: V/A/R/T/H/B/S/P/C) with tooltips;
    wired in the `TOOL_LABELS` loop. WindowShortcut does NOT hijack inline text typing
    (graphics view accepts ShortcutOverride).
  - **F2** — `AnnotationCanvas.duplicate_selected()` + `_clone_item()` (arrow, step, text, rect,
    highlight, blur patch, pen), offset `QPointF(20,20)`; duplicated step markers get `next_number`;
    one undo push. `TopToolBar` gains Duplicate (`Ctrl+D`), connected in MainWindow.
  - **F3** — Annotation count in status bar: `_update_annotation_count()` on `image_changed`,
    shown in permanent `_annotation_label` ("N annotations").
  - **F4** — Freehand pen: `tools/pen_tool.py` (`PenToolSettings`), `PenStrokeGraphicsItem`
    (QPainterPath, `add_point()`, selection border, set_color/thickness), `ToolMode.PEN`,
    press/move/release branches, snapshot "pen" tuples, panel + `set_pen_color`/`set_pen_thickness`,
    toolbar entry + `P` shortcut. Settings persisted.
  - **F5** — Crop: `ToolMode.CROP`, green rect preview, `_apply_crop(rect)` swaps the background
    pixmap, translates kept annotations by the crop origin, updates scene rect; undo restores the
    original background via the `__bg__` snapshot sentinel (needed U2). `_restore_state()` now also
    resets the scene rect. Panel falls through to the empty page; `C` shortcut.
- All prior Phase 1/2 work (R1, R2, U1–U3, step-counter desync, blur source_rect, hi-DPI blur,
  multi-monitor capture) remains green.
- `StepShot.spec` hiddenimports updated: `tools.pen_tool`, `services.settings_service`.
- `AGENTS.md` updated to reflect pen/crop tools, `settings_service`, shortcuts, and status-bar UI.
- **[DONE] Phase 6 — Refactor (F6)**
  - **F6** — Per-tool mouse logic extracted from `ui/canvas.py` into `tools/handlers/`:
    `base.py` (`ToolHandler` interface + `RectDragHandler` shared drag/preview flow),
    one handler module per tool (`arrow`, `step`, `rectangle`, `highlight`, `pen`, `blur`,
    `crop`, `text`), and `build_handlers(canvas)` wiring `canvas._handlers` + `_active_handler`.
  - `canvas.py` mouse events are now thin dispatch (~5–17 lines each): `mousePressEvent`
    routes to `_handlers[mode].on_press()` (committing handlers return `True`), move/release
    forward to `_active_handler`, `SELECT`/non-left clicks fall through to `super()`.
  - Preview state (`_arrow_start`, `_preview_rect`, `_pen_stroke`, ...) moved out of canvas
    into the handlers; `set_tool_mode` sweeps `handler.cancel()` over all handlers.
  - Handlers call canvas internals where needed (`_finalize_text_edit`, `_apply_blur_region`,
    `_apply_crop`, `_text_item_at`) per the design-correction in the F6 section below.
  - Verified green: full `pytest` = 122 passed, acceptance = 24 passed; all 8 tool flows are
    covered by existing qtbot mouse-simulation tests.

### Known environment issue (NOT caused by these changes)
There is a **pre-existing flaky hard crash** (exit code `0xC0000409`) when
`tests/test_services/test_image_effects.py` is run in isolation under pytest with
PySide6 6.11.1 + Python 3.14. It was reproduced with the **unmodified** code and does not occur
when running the full suite (`pytest` passes reliably). Treat isolated-single-file runs
of that module as unreliable; verify with the full suite.

### Remaining work

Phases 9–16 below are queued. They prioritize correctness and release confidence over adding more
annotation tools. Do not begin optional feature work until these phases are complete.

---

## Phase 9 — Safe blur/redaction

**Priority: Critical — users may rely on blur to conceal sensitive content**

**Decision:** Blur patches are selectable but non-movable and cannot be duplicated. Delete,
Undo, Redo, crop, and Reset All remain supported. Crop is a canvas-wide coordinate change and
translates the patch and its `source_rect` together.

### Current behavior

`AnnotationCanvas._apply_blur_region()` samples the background and adds a
`BlurPatchGraphicsItem`. The original pixels remain in the background, and the patch is selectable
and movable. `_clone_item()` duplicates the sampled pixmap at an offset rather than applying the
effect to the pixels under the clone's new position. Moving, deleting, or duplicating a patch can
therefore reveal content or show an effect generated from the wrong source area.

### Required decision

Use one consistent redaction model:

1. **Preferred:** make blur patches non-movable and do not support duplication. They remain
   removable through Delete and restorable through undo/redo. This is the smallest safe change and
   avoids implying that an already-sampled pixmap can be moved to redact another location.
2. If movable blur is retained, regenerate the patch from the unchanged background whenever its
   position changes or it is duplicated. Keep `source_rect`, item position, snapshots, crop, and
   export synchronized. Do not merely move the existing sampled pixmap.

Do not destructively modify `_original_pixmap`; Reset All must continue to restore the captured
screenshot. Undo snapshots must preserve enough state to recreate the visible redaction exactly.

### Implementation tasks

- Enforce the selected redaction model in `ui/graphics_items.py` and `ui/canvas.py`.
- Prevent `duplicate_selected()` from creating a misleading blur clone unless duplication
  regenerates the effect from the clone's destination.
- Verify Delete, Undo, Redo, Reset All, crop, Copy, and Save behavior with a blurred region.
- Keep blur and pixelate modes covered, including high-DPI pixmaps.
- Update UI copy only if the final behavior no longer matches the current blur description.

### Acceptance criteria

- A blur or pixelate region obscures the pixels under its visible location in rendered output.
- No supported move or duplicate operation displays pixels sampled from a different location.
- Undo and Redo restore the exact pre-action and post-action rendered pixels.
- Reset All restores the original unblurred screenshot by design.
- Pixel-level tests use a non-uniform source image so a misplaced or stale patch cannot pass.

### Verification

```powershell
pytest tests/test_services/test_image_effects.py tests/test_ui/test_scenario2_tools.py tests/test_ui/test_scenario3_features.py
pytest
```

---

## Phase 10 — Undoable annotation movement

**Priority: High — dragging an item is currently absent from history**

### Current behavior

Annotation items use `ItemIsMovable`, but canvas history is pushed only by explicit canvas/tool
mutations. A Select-tool drag does not commit a snapshot, so Undo can revert an earlier action
instead of the movement. Existing acceptance coverage calls `setPos()` directly and does not test
mouse dragging or history.

### Implementation tasks

- Capture the pre-drag scene state when a selectable annotation begins a Select-tool move.
- On release, push exactly one history state only if item positions changed.
- Do not create history entries for clicks without movement or for intermediate mouse-move events.
- Support all movable annotation families selected by the scene.
- Emit `image_changed` after a committed move so status and dependent UI remain fresh.
- Keep movement-history orchestration owned by the canvas; graphics items should not know about
  canvas undo stacks.

### Acceptance criteria

- One drag creates one undoable action.
- Undo restores the exact original position and Redo restores the final position.
- Clicking or selecting without moving does not change history.
- Moving multiple selected items, if Qt currently permits it, is one atomic action.
- Property edits immediately before or after a move retain the correct undo order.

### Verification

Add real `qtbot` mouse-drag tests for arrow, step, text, rectangle, highlight, pen, and any blur
behavior retained by Phase 9.

```powershell
pytest tests/test_ui/test_canvas.py tests/test_ui/test_scenario2_tools.py tests/test_ui/test_scenario3_features.py
pytest
```

---

## Phase 11 — Atomic text creation and editing history

**Priority: High — text placeholders and double-click edits are not reliable history actions**

### Current behavior

`TextHandler.on_press()` adds `"Enter instruction..."` and immediately pushes history.
`AnnotationCanvas._finalize_text_edit()` pushes another state. One Undo after creating text can
therefore restore the placeholder instead of removing the annotation. Separately,
`TextGraphicsItem.mouseDoubleClickEvent()` enables editing without registering the item through
`AnnotationCanvas._editing_text_item`, so existing-text edits can bypass canvas history.

### Implementation tasks

- Treat placement plus initial text entry as one atomic action.
- Do not commit placeholder text as a user-visible history state.
- Route all existing-text editing, including double-click, through canvas-owned start/finalize
  methods that retain the before-edit value.
- Commit one state only when text changed; focus loss and Escape must finalize consistently.
- Remove an empty new text item without leaving a placeholder or a no-op history entry.
- Preserve multiline text and current property-edit coalescing behavior.

### Acceptance criteria

- Create text, type, then Undo removes the item in one step; Redo restores the completed text.
- Edit existing text, then Undo restores the previous content and Redo restores the edit.
- Empty new text leaves no annotation and no extra undo action.
- Clicking away, pressing Escape, and double-click editing all use the same history contract.
- `"Enter instruction..."` never appears after Undo unless the user typed that exact value.

### Verification

```powershell
pytest tests/test_ui/test_canvas.py tests/test_ui/test_scenario2_tools.py
pytest
```

---

## Phase 12 — Cross-monitor and mixed-DPI region capture

**Priority: High — a region spanning screens is currently captured from one screen**

### Current behavior

`RegionSelector` spans the union of available screens, but
`ScreenshotService.capture_region()` chooses one screen from the selection center and performs one
`grabWindow()` call. A selection crossing a monitor boundary is not assembled from each intersected
screen. Applying one screen's device-pixel ratio to the entire rectangle is also insufficient for
mixed-DPI layouts.

### Implementation tasks

- Intersect the global selection rectangle with every screen it crosses.
- Convert each intersection to that screen's local/native capture coordinates.
- Grab each piece and compose it into one output pixmap at the correct offset.
- Define and consistently apply the output DPR/logical-size policy for mixed-DPI captures.
- Handle screens with negative global coordinates and layouts with gaps.
- Raise the existing clear errors for invalid regions, no screens, or a wholly failed capture.
- Keep the single-screen path correct and avoid changing its visible dimensions unexpectedly.

### Acceptance criteria

- Regions wholly on the primary or secondary screen capture the requested logical area.
- A region crossing two screens contains correctly positioned pixels from both screens.
- Negative monitor coordinates do not shift or clip the result.
- Mocked 100%/150% and 100%/200% layouts preserve expected logical geometry.
- Add a documented manual Windows smoke check for a real two-monitor setup; automated tests must
  not require multiple physical monitors.

### Verification

```powershell
pytest tests/test_services/test_screenshot_service.py tests/test_ui/test_region_selector.py
pytest
```

---

## Phase 13 — Annotation resizing decision and implementation

**Priority: High if resize remains an MVP requirement; otherwise acceptance-documentation debt**

### Current behavior

The acceptance suite describes the canvas as supporting resize and names an arrow test
`test_draw_move_resize_change_color_and_thickness`, but it changes style and calls `setPos()`; no
annotation has interactive geometry handles. Step-marker size is a property, not general selection
resizing.

### Required decision

Before coding, choose one scope and record it here:

1. **Implement resize:** add interactive geometry controls for arrow endpoints and rectangular
   items (rectangle, highlight, and blur if Phase 9 retains resizable blur). Define separately
   whether text and pen support scaling; do not add generic scaling accidentally.
2. **Remove the requirement:** rename acceptance descriptions/tests so they claim only implemented
   behavior. This is acceptable only if the product no longer requires interactive resizing.

### Decision (2026-08-30)

**Scope 1 — Implement resize.** The product has shipped "resize" in its user-facing copy
(`test_draw_move_resize_change_color_and_thickness`, `select, move, delete, resize` docstring);
removing the requirement would be a user-visible regression. Resize applies to **arrow endpoints**
and **rectangle / highlight boxes**. Text, pen, and blur patches are explicitly out of scope (per
the spec's "do not add generic scaling accidentally"). Step markers are also out of scope — their
`marker_size` is a property, not a geometry resize.

### Architecture

- **One handle layer, two families.** A single `ResizeHandleLayer` is owned by the canvas and
  shown only when exactly one resizable item is selected. It paints 2 endpoint handles for
  arrows and 4-corner / 4-edge handles for rectangle-style items, all sized in constant
  screen pixels (`10 px / zoom`, floor 6) so they stay usable at every supported zoom level.
- **No per-item handle child items.** The layer is a canvas overlay (a `QGraphicsItem` with no
  scene-add; it lives on the view), so handles never enter snapshots, exports, or
  clipboard output. The items themselves are not made aware of handles.
- **Gesture lives on the canvas, not on items.** The canvas intercepts a left-press whose
  scene position is inside a handle, captures the pre-resize geometry, forwards
  `mouseMoveEvent` deltas to the selected item through a new `set_geometry(rect)` method, and
  on `mouseReleaseEvent` pushes exactly one undo state only if geometry changed. The pattern
  mirrors Phase 10's drag-tracking so existing snapshot / undo / property-coalescing code does
  not need a second pathway.
- **Item API.** `ArrowGraphicsItem`, `RectangleGraphicsItem`, and `HighlightGraphicsItem` each
  gain a `set_geometry(start: QPointF, end: QPointF)` (arrows) or `set_geometry(rect: QRectF)`
  (rectangles/highlights) that calls `prepareGeometryChange()` once and clamps the result to a
  non-degenerate, non-negative-dimension rect via `QRectF.normalized()` plus a minimum size
  (4 × 4 scene units).
- **Snapshot format unchanged.** Arrow snapshots already store absolute `start_point + pos()`
  and `end_point + pos()`; rectangle and highlight snapshots already store `pos()` + local
  `QRectF`. Resize works against the same stored fields with no snapshot migration.
- **No second mechanism per family.** The `ResizeHandleLayer` and the canvas-side gesture are
  the only resize code; item classes do not implement their own.

### Implementation constraints if resize is retained

- Handles appear only for the selected item and remain usable at all supported zoom levels. ✅
  (handles drawn on the view at a constant 10 px on screen, at every supported zoom.)
- Geometry stays normalized and cannot produce invalid negative dimensions. ✅ (`set_geometry`
  clamps via `normalized()` + minimum-size.)
- One resize gesture creates one undo action; Undo/Redo restore exact geometry. ✅
  (`_begin_resize_tracking` / `_commit_resize_tracking` mirror Phase 10's drag tracking.)
- Crop/export/snapshots preserve resized geometry. ✅ (snapshots already store the geometry
  fields; no change needed.)
- Keep handles out of rendered exports and clipboard output. ✅ (overlay lives on the view,
  not in the scene, so `render_to_pixmap` and `ExportService` are unaffected.)
- Reuse one handle/gesture mechanism across compatible item families. ✅ (one
  `ResizeHandleLayer`, one canvas-side gesture.)

### Acceptance criteria

- Acceptance test names and behavior agree with the chosen product scope.
- If implemented, resize is exercised through mouse input, not direct geometry mutation.
- Arrow endpoint and rectangular-item tests cover resize, Undo, Redo, and rendered output.

### Verification

```powershell
pytest tests/test_prd_acceptance/test_acceptance_criteria.py tests/test_ui
pytest
```

---

## Phase 14 — Crop boundaries and annotation retention

**Priority: Medium-high — out-of-bounds crop geometry can misalign retained annotations**

### Current behavior

`AnnotationCanvas._apply_crop()` copies the requested rectangle but translates every annotation by
the unbounded requested origin. It retains annotations outside the crop, where they can become
invisible while still contributing to the annotation count. Reset All intentionally restores
`_original_pixmap`, which is the pre-crop screenshot; preserve that behavior unless a separate
product decision changes it.

### Required behavior

- Intersect the requested crop with the background bounds before copying or translating.
- Remove annotations fully outside the effective crop.
- Retain partially intersecting annotations without corrupting their geometry. Qt scene clipping
  may hide the outside portion, but snapshots and subsequent movement must remain valid.
- Base translation on the effective, clamped crop origin.
- Keep Undo/Redo and Reset All behavior explicit and tested.
- Emit `image_changed` after crop so zoom and annotation count are current.

### Acceptance criteria

- In-bounds and partially out-of-bounds crop gestures produce correctly aligned images/items.
- A wholly invalid crop is a no-op and does not create history.
- Fully outside annotations are removed; partially intersecting annotations remain correctly
  positioned relative to the new background.
- Undo restores the prior image and full annotation set; Redo reapplies the crop.
- The status bar count matches retained annotations.

### Verification

```powershell
pytest tests/test_ui/test_scenario3_features.py tests/test_ui/test_canvas.py
pytest
```

---

## Phase 15 — Interaction-level acceptance coverage

**Priority: Medium — current green tests do not exercise several claimed user workflows**

### Current behavior

Some acceptance tests verify symbols or mutate graphics items directly. Examples include rectangle
module existence, arrow movement through `setPos()`, a resize-named test with no resize, and
packaging checks that only verify files/callables. These are useful unit guards but do not prove the
named user interactions.

### Implementation tasks

- Replace or supplement direct mutation with real Qt mouse/keyboard interaction for selection,
  drag, text editing, resizing if retained, crop, duplicate, Delete, Undo, and Redo.
- Add pixel assertions for blur/pixelate, crop, and rendered export instead of relying only on item
  count or pixmap dimensions.
- Cover every item family supported by `duplicate_selected()` after Phase 9 defines blur behavior.
- Correct the acceptance wording from "unlimited undo" to the implemented 50-state history cap,
  then test the boundary and redo clearing after a new action.
- Remove stale `not_implemented` guidance from `tests/README.md` and `pytest.ini` if the marker still
  has no uses after the scope decision in Phase 13.
- Keep tests behavior-focused and avoid duplicating lower-level setter coverage already present in
  unit tests.

### Acceptance criteria

- Every acceptance-test name describes behavior that the test actually performs.
- Critical user workflows fail when their event wiring or rendered output is broken.
- Tests remain headless-compatible with `QT_QPA_PLATFORM=offscreen` on Linux and Windows.
- The full suite remains deterministic and does not depend on global hotkeys or physical monitors.

### Verification

```powershell
pytest -m acceptance
pytest
```

---

## Phase 16 — Frozen Windows release validation

**Priority: Medium — CI tests source code but does not validate the shipped executable**

### Current behavior

CI runs pytest on Ubuntu and Windows with Python 3.13. `StepShot.spec` hidden-import tests guard
module drift, and a manual `python build.py` previously produced `dist/StepShot.exe`, but CI does
not build or launch the frozen artifact.

### Implementation tasks

- Add a Windows build job for releases, tags, or a manually triggered workflow. Keep ordinary pull
  request CI duration reasonable.
- Install `requirements-build.txt`, run `python build.py`, and archive `dist/StepShot.exe`.
- Add a deterministic smoke mode that initializes the frozen Qt application and exits without
  registering global hotkeys, opening capture overlays, or requiring user input.
- Run that smoke mode against the built executable and fail the job on non-zero exit or timeout.
- Associate the artifact with its source revision in the workflow metadata or artifact name.
- Do not optimize the approximately 248 MB one-file build until the build-and-launch check is green.

### Acceptance criteria

- CI produces a Windows executable from a clean checkout.
- The executable initializes Qt and exits successfully in smoke mode.
- The artifact is downloadable and identifiable by source revision.
- Normal application startup remains unchanged when smoke mode is absent.

### Verification

```powershell
pip install -r requirements-build.txt
python build.py
dist\StepShot.exe --smoke-test
pytest
```

---

## Deferred follow-ups

These remain outside Phases 9–16 unless required to complete one of them:

- Revisit Python 3.14 in CI when the selected PySide6 release supports the required environment.
- Isolate the `test_image_effects.py` hard crash seen only under Python 3.14 + PySide6 6.11.1.
- Split Clear Annotations from Reset All only if product requirements call for post-crop reset
  behavior different from restoring the original capture.
- Optimize PyInstaller collection and startup after frozen-build validation is reliable.

---

## Orientation

Before starting, read these files in full:
- `AGENTS.md` — architecture overview and conventions
- `ui/canvas.py` — central hub, ~880 lines, dispatches mouse events to per-tool handlers
- `tools/handlers/` — `ToolHandler`/`RectDragHandler` base + one handler per tool
- `ui/graphics_items.py` — all 7 drawable item classes
- `models/step_marker.py` — `StepCounter` (now has `current` + `reset_to()`)
- `main.py` — app entry point and capture orchestration

Key conventions to follow:
- `from __future__ import annotations` at the top of every file
- No docstrings, minimal comments — code should be self-documenting
- Services are static classes (no instantiation)
- All signals/slots wired manually in `_connect_signals()` methods
- Type hints everywhere
- `AnnotationCanvas._snapshot_state()`/`_restore_state()` use `("__meta__", counter_value)` and
  `("__bg__", pixmap)` sentinels at the start of every snapshot — preserve them when editing
  snapshot code.
- `AnnotationCanvas._push_undo_state()` is capped at 50 entries and stops `_property_timer`;
  property setters use `_schedule_property_undo()` (400ms coalescing) instead of pushing directly.

---

## Phase 1 — Remaining correctness work ✅ (R1, R2 complete)

### Task R1 — Dead code cleanup: wire or remove `models/annotation.py` (was Task 3)

**Priority: Medium — reduces confusion for future contributors**

### Problem
`models/annotation.py` defines `ArrowAnnotation`, `StepMarkerAnnotation`, `TextAnnotation`,
and `clone_annotation()` but none of these are imported or used anywhere in production code
(only `tests/test_models/test_annotation.py` imports them).

### Decision
Remove the file entirely. The canvas snapshot tuples in `_snapshot_state()` serve as the
serialization format.

### Files to change
- Delete `models/annotation.py`
- `models/__init__.py` — remove any imports of annotation classes if present
- `tests/test_models/test_annotation.py` — delete this test file (tests dead code)

### Acceptance criteria
- `pytest` passes with no import errors
- No references to `ArrowAnnotation`, `StepMarkerAnnotation`, `TextAnnotation` remain

---

### Task R2 — Populate empty tool modules (was Task 4)

**Priority: Low — removes misleading empty files**

`tools/arrow_tool.py`, `tools/text_tool.py`, `tools/step_tool.py` are empty. Give each a settings
dataclass with a `defaults()` classmethod following `tools/rectangle_tool.py`:

- `ArrowToolSettings(color: QColor, thickness: int = 3)` → `defaults()` = red, 3
- `TextToolSettings(color: QColor, font_size: int = 14, bold: bool = False)` → `defaults()` = red
- `StepToolSettings(color: QColor, size: int = 28)` → `defaults()` = red

Then in `ui/canvas.py`, replace the hardcoded `QColor(255, 0, 0)` literals for arrow, text, and
step with `ArrowToolSettings.defaults().color` etc. (mirror how `RectangleToolSettings` is used at
`ui/canvas.py:81-98`).

### Acceptance criteria
- All three tool files are non-empty and importable
- `canvas.py` no longer has hardcoded `QColor(255, 0, 0)` for arrow/text/step defaults
- `pytest` passes

---

## Phase 2 — Undo/redo robustness ✅ (U1–U3 complete, new tasks)

### Task U1 — Cap undo stack + coalesce property pushes

**Priority: Medium**

`_push_undo_state()` (`ui/canvas.py`) appends a full scene snapshot on **every** mutation.
Dragging the highlight-opacity slider from 20→255 queues ~235 undo states (unusable Ctrl+Z), and
history is unbounded.

### What to do
- In `_push_undo_state()`, trim `self._undo_stack` to the last ~50 entries.
- Coalesce consecutive property changes: a 400ms `QTimer` defers the snapshot; re-arming it on each
  change collapses a slider drag into one undo entry. Trigger the snapshot only after the timer
  fires (or when a non-property action occurs).

### Acceptance criteria
- Dragging the opacity slider end-to-end creates exactly one undo entry (Ctrl+Z removes one step).
- Rapid color/thickness changes produce a small number of undo states.
- Existing undo/redo tests still pass.

---

### Task U2 — Background pixmap in snapshots

**Priority: Medium — enables crop undo later**

`_snapshot_state()`/`_restore_state()` never touch `_background_item`. Store the current
background as a **reference** (not a copy — every background replacement uses `copy()`, so
references are safe) so future features (crop, re-bake) can be undone.

### What to do
- In `_snapshot_state()`, add `("__bg__", self._background_item.pixmap())` to the snapshot list.
- In `_restore_state()`, when `"__bg__"` is seen, swap the background item's pixmap to the
  referenced one.
- Verify no in-place `QPixmap` mutation anywhere (search for `setPixmap`/painters on background).

### Acceptance criteria
- Undo/redo with an image loaded still works.
- A snapshot taken after a background swap restores the correct background.

---

### Task U3 — `delete_selected()` emits `image_changed`

**Priority: Low — prereq for the annotation-count feature**

`delete_selected()` (`ui/canvas.py`) pushes undo state but never emits `image_changed`, so any
UI driven by that signal (e.g. a status-bar annotation count) goes stale after Delete.

### What to do
- Emit `self.image_changed` after removing items in `delete_selected()`.

---

## Phase 3 — Performance ✅ (P1, P2 complete)

### Task P1 — Fix `qpixmap_to_pil` PNG round-trip (was Task 10)

**Priority: Medium — affects blur performance on large screenshots**

`services/image_effects.py` converts `QPixmap → PNG bytes → PIL Image`. Replace with raw bytes:

```python
def qpixmap_to_pil(pixmap: QPixmap) -> Image.Image:
    image = pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
    width, height = image.width(), image.height()
    return Image.frombytes("RGBA", (width, height), bytes(image.bits()))
```

Remove the now-unused `BytesIO`/`QBuffer` imports. Keep `pil_to_qpixmap()` as-is (it already uses
raw bytes and now accepts `device_pixel_ratio`).

### Acceptance criteria
- Blur and pixelate effects still work visually
- No PNG round-trip in the conversion path
- `pytest tests/test_services/test_image_effects.py` passes (run via full suite — see note above)

---

### Task P2 — Cache checkerboard background

**Priority: Low**

`drawBackground()` (`ui/canvas.py`) paints the checkerboard cell-by-cell every frame (O(px)).
Prebuild a small tile (e.g. 32×32) as a `QPixmap`/`QBrush` and fill the viewport with it in one
call. Guard against painting the pattern when the scene is zoomed far out.

### Acceptance criteria
- Visual output unchanged; background still renders on resize/zoom.
- No per-frame nested loop over viewport pixels.

---

## Phase 4 — UX polish ✅ (X1–X4 complete)

### Task X1 — Properties panel syncs to selection

**Priority: Medium**

`_update_properties_panel(item)` in `ui/main_window.py` only switches the stacked page; it never
populates widget values from the selected item. Selecting an arrow with thickness 5 still shows 3.

### What to do
- Add a `_sync_panel_values(item)` that sets spinbox/checkbox/slider/swatch values from the
  selected item's actual properties, using `blockSignals(True)` while setting.

### Acceptance criteria
- Selecting an item shows its real color/thickness/size/opacity in the panel.
- Changing a value still works (signals not permanently blocked).

---

### Task X2 — Persist tool defaults via `QSettings`

**Priority: Medium**

Colors/thickness/opacity/mode reset to defaults every launch. Persist per-tool settings with
`QSettings("StepShot", "StepShot")`; load in `MainWindow.__init__`/`AnnotationCanvas.__init__`,
save on property changes.

### Acceptance criteria
- Change arrow color, restart app → color persists.
- Defaults used on first run (no saved keys).

---

### Task X3 — Zoom fit/reset + % indicator

**Priority: Low**

`_zoom_in`/`_zoom_out` (`ui/main_window.py`) scale without bound and there is no way back to
fit/100%. Add "Fit to window" and "100%" actions to `TopToolBar` (new signals), cap zoom, and
show current % in the status bar (update on zoom changes).

### Acceptance criteria
- Zoom actions bounded; fit/100% restore expected views.
- Status bar shows zoom percentage.

---

### Task X4 — Text annotation contrast backdrop

**Priority: Low**

`TextGraphicsItem` floats over the screenshot with no background. Override `paint()` to draw a
translucent rounded rect behind `boundingRect()` (or use a `QGraphicsPathItem` child) so text is
readable on dark screenshots.

### Acceptance criteria
- Text is legible over dark and light regions.
- Editing/moving behavior unchanged.

---

## Phase 5 — Features ✅ (F1–F5 complete)

### Task F1 — Keyboard shortcuts for tool switching (was Task 5)

**Priority: High UX improvement**

In `LeftToolBar` (`ui/toolbar.py`), add `QShortcut` per tool. Map:

| ToolMode   | Key |
|------------|-----|
| SELECT     | `V` |
| ARROW      | `A` |
| RECTANGLE  | `R` |
| TEXT       | `T` |
| HIGHLIGHT  | `H` |
| BLUR       | `B` |
| STEP       | `S` |

Wire into the existing `TOOL_LABELS` loop (`ui/toolbar.py:191`) and add the key to the tooltip
(already handled at `ui/toolbar.py:155`).

### Acceptance criteria
- Each letter activates its tool (button checks + canvas mode changes).
- Existing toolbar clicks still work.

---

### Task F2 — Ctrl+D duplicate selected annotation (was Task 6)

**Priority: Medium**

Add `duplicate_selected()` to `AnnotationCanvas`: for each selected item (arrow, step, text,
rect, highlight, **blur patch**), create a copy offset by `QPointF(20, 20)`; duplicated step
markers get `next_number`; push one undo state. Add a `duplicate` signal/action in `TopToolBar`
and connect in `MainWindow._connect_signals()`.

### Acceptance criteria
- Ctrl+D duplicates the selection offset by 20px.
- Duplicated step markers get the next sequential number.
- Undo removes the duplicate; works for all 6 annotation types.

---

### Task F3 — Annotation count in status bar (was Task 7)

**Priority: Low**

Connect `self._canvas.image_changed` to a `_update_annotation_count()` in `MainWindow` that counts
annotation items and shows `"N annotations"` in the status bar (or the default ready message when
0). Requires Task U3 so Delete updates the count.

### Acceptance criteria
- Placing/removing annotations updates the count.
- Reset all returns to the default message.

---

### Task F4 — Freehand pen tool (was Task 8)

**Priority: Medium — fills a major annotation gap**

- `tools/pen_tool.py` — `PenToolSettings(color, thickness=3)` + `defaults()`.
- `ui/graphics_items.py` — `PenStrokeGraphicsItem(QGraphicsItem)` storing a `QPainterPath`,
  with `add_point()`, paint, selection border, and `set_color`/`set_thickness`.
- `ui/canvas.py` — add `PEN` to `ToolMode`; press/move/release branches; `"pen"` branches in
  `_snapshot_state()`/`_restore_state()`; `set_pen_color()`/`set_pen_thickness()`; import defaults.
- `ui/toolbar.py` — add `ToolMode.PEN: ("Pen", "✏")` + shortcut `P` (see Task F1).
- `ui/main_window.py` — `_build_pen_panel()` (color + thickness), register in the stack and in
  `_update_properties_panel()`.

### Acceptance criteria
- Pen draws smooth freehand strokes; selectable/movable/deletable; configurable color/thickness;
  undo/redo works; stroke exports.

---

### Task F5 — Crop tool (was Task 9)

**Priority: Medium — requires Task U2**

Add `CROP` to `ToolMode`. Reuse the rect-drag preview with a distinct color; on release with a
valid rect, `_apply_crop(rect)` replaces `_background_item` with the cropped pixmap, keeps
annotations, and pushes undo. **Important:** the "Undo restores the original background"
acceptance criterion is only achievable after Task U2 (background stored in snapshots). Without
U2 this task's undo criterion fails.

In `_update_properties_panel()`, `ToolMode.CROP` → `self._empty_page`. Shortcut `C` (Task F1).

### Acceptance criteria
- Dragging and releasing crops the background.
- Existing annotations preserved.
- Undo restores the original background (after U2).
- Exported image reflects the crop.

---

## Phase 6 — Refactor ✅ (F6 complete)

### Task F6 — Extract tool handlers from `canvas.py` (was Task 11)

**Priority: Medium — maintainability, canvas.py was ~740 lines**

Move each tool's mouse logic out of the monolithic `mousePressEvent`/`mouseMoveEvent`/
`mouseReleaseEvent` into dedicated handler objects in `tools/`.

**Design correction vs. original plan:** the `(scene_pos, scene)`-only `ToolHandler` interface
cannot host Step (commits on **press**, not release), Text (needs `_finalize_text_edit()` and
`_editing_text_item`), or Blur (needs the background + `_logical_to_physical_rect()`). Give
handlers a reference to the canvas (`attach(canvas)`), allow `on_press` to commit directly, and
let blur/text handlers call canvas internals.

Suggested base:

```python
class ToolHandler:
    def attach(self, canvas) -> None: ...
    def on_press(self, scene_pos) -> bool: ...      # True = committed (undo push)
    def on_move(self, scene_pos) -> None: ...
    def on_release(self, scene_pos) -> bool: ...    # True = committed
    def cancel(self) -> None: ...
```

Migrate one tool at a time and run `pytest` after each. Do this **last** — it touches the most code.

> **Status: DONE (2026-08-04).** Implemented as `tools/handlers/` package. `RectDragHandler`
> additionally DRYs the rectangle/highlight/blur/crop drag+preview flow (`_create_preview` /
> `_update_preview` / `_commit`). Verified green: 122 passed, acceptance 24 passed.

### Acceptance criteria
- All tools work identically. ✅ (behavior preserved; existing qtbot tests cover all 8 tools)
- Canvas mouse-event methods each under ~30 lines. ✅ (press 17, move 6, release 9)
- `pytest` passes after each migration. ✅

---

## Phase 7 — Operations ✅ (complete)

- **Logging** — `logging` setup in `main.py`; log capture failures instead of silent
  `QMessageBox` swallows.
- **Keyboard-thread marshaling** — `keyboard` callbacks in `main.py` run on a worker thread;
  connect `capture_signals` with explicit `Qt.QueuedConnection`.
- **CI** — add `.github/workflows/ci.yml` running `pytest` on `ubuntu-latest`
  (`QT_QPA_PLATFORM=offscreen`) + `windows-latest`, installing `requirements-test.txt`.

---

## Phase 8 — Hardening ✅ (H1–H4 complete)

Three defects found by auditing the code against this document's completion claims, plus the
documentation sync. None broke the test suite at the time; all three were latent-failure risks.
Independent of each other and of Phase 7 — implemented in H1 → H2 → H3 → H4 order,
running `pytest` after each.

### Task H1 — `StepShot.spec` misses the `tools.handlers` package

**Priority: Medium — silent frozen-build risk**

#### Problem
Phase 6 (F6) added `tools/handlers/` — 9 leaf modules plus the package `__init__` — but
`StepShot.spec:46-74` was never updated. Its `hiddenimports` list enumerates every other
first-party module (`ui.*`, `services.*`, `models.*`, `tools.*`) and stops at `tools.text_tool`
(`StepShot.spec:71`).

In practice PyInstaller will still bundle them: `ui/canvas.py:28` imports the package at module
level and `tools/handlers/__init__.py:5-13` statically imports every submodule, so static analysis
reaches them. The defect is that the spec's own stated convention — enumerate every first-party
module — is now violated, and **nothing catches the next omission**. A future handler added via a
lazy or conditional import would be missing from the EXE with no build-time error; the failure
surfaces as an `ImportError` at runtime in the frozen app only.

#### What to do
1. Add the 10 missing entries to `hiddenimports` in `StepShot.spec`, keeping the existing
   alphabetical-within-package grouping, after `tools.blur_tool` / before `tools.pen_tool`:

```python
    "tools.handlers",
    "tools.handlers.arrow",
    "tools.handlers.base",
    "tools.handlers.blur",
    "tools.handlers.crop",
    "tools.handlers.highlight",
    "tools.handlers.pen",
    "tools.handlers.rectangle",
    "tools.handlers.step",
    "tools.handlers.text",
```

2. Add a drift guard so this cannot silently recur — new file
   `tests/test_build/test_spec_hiddenimports.py` (plus an empty `tests/test_build/__init__.py`
   only if the other test dirs have one; they do not, so no `__init__.py`):

```python
"""Guards StepShot.spec against first-party module drift."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = ("ui", "services", "models", "tools")


def _spec_hiddenimports() -> set[str]:
    text = (ROOT / "StepShot.spec").read_text(encoding="utf-8")
    block = text.split("hiddenimports = [", 1)[1].split("]", 1)[0]
    return set(re.findall(r'"([\w.]+)"', block))


def _first_party_modules() -> set[str]:
    modules: set[str] = set()
    for package in PACKAGES:
        modules.add(package)
        for path in (ROOT / package).rglob("*.py"):
            relative = path.parent if path.name == "__init__.py" else path.with_suffix("")
            modules.add(".".join(relative.relative_to(ROOT).parts))
    return modules


def test_spec_lists_every_first_party_module():
    missing = sorted(_first_party_modules() - _spec_hiddenimports())
    assert not missing, f"Add to StepShot.spec hiddenimports: {missing}"
```

#### Rejected alternative
Replacing the hand-written list with `PyInstaller.utils.hooks.collect_submodules("tools")` is the
idiomatic PyInstaller answer, but `collect_submodules` imports each **package** `__init__` in an
isolated subprocess that does not inherit the spec's `sys.path`. Importing `tools.handlers` pulls
in `ui.graphics_items` → PySide6, so this trades a silent-omission risk for a build-time
`ModuleNotFoundError` risk. The explicit list plus the drift test achieves the same guarantee with
no build-time machinery.

#### Acceptance criteria — ✅ all met
- `StepShot.spec` lists all 10 `tools.handlers*` modules.
- `pytest tests/test_build` passes; deleting any spec entry makes it fail with a useful message.
- `python build.py` still produces `dist/StepShot.exe` (run once; not part of the suite).

#### Outcome
`python build.py` → `dist/StepShot.exe` (248.6 MB). Verified all 10 handler modules plus
`services.settings_service` appear in `build/StepShot/PYZ-00.toc`, and
`warn-StepShot.txt` reports no missing first-party module. (`main` is a `PYSOURCE` entry in
`PKG-00.toc` rather than the PYZ — normal for the entry script.) The pre-existing
`Qt6QuickShapesDesignHelpers.dll` resolve warning is unrelated to these changes.

---

### Task H2 — Stride-safe `qpixmap_to_pil()`

**Priority: Low — defensive, not a live bug**

#### Problem
`services/image_effects.py:17-20` reads the whole `QImage` buffer and hands it to
`Image.frombytes()` without a stride, which implicitly assumes `bytesPerLine == width * 4`.

Measured on this project's stack (PySide6 6.11.1 / Pillow 12.2.0), that assumption **holds** for
`Format_RGBA8888` — a 37px-wide image reports `bytesPerLine == 148 == 37 * 4`, because Qt's
32-bit-per-pixel rows are already 4-byte aligned. So this is not a live defect. It is an
undocumented invariant one format change away from producing diagonally-sheared blur patches with
no exception raised.

Secondary issue: `bits()` is the mutable accessor and forces a detach (deep copy) when the buffer
is shared; `constBits()` is read-only and skips it. This partially undoes P1's performance win.

#### What to do
Replace `qpixmap_to_pil()` in `services/image_effects.py`:

```python
def qpixmap_to_pil(pixmap: QPixmap) -> Image.Image:
    image = pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
    return Image.frombytes(
        "RGBA",
        (image.width(), image.height()),
        bytes(image.constBits()),
        "raw",
        "RGBA",
        image.bytesPerLine(),
    )
```

Verified working against the installed Qt/Pillow: `Image.frombytes(..., "raw", "RGBA", stride)`
accepts the stride as the raw decoder's line-width argument, and `bytes(constBits())` yields
`sizeInBytes()` bytes (740 for 37×5), which satisfies Pillow's buffer-length check.

Add to `tests/test_services/test_image_effects.py`:

```python
def test_qpixmap_to_pil_handles_odd_widths():
    from services.image_effects import qpixmap_to_pil

    pixmap = QPixmap(37, 5)
    pixmap.fill(QColor(255, 0, 0))
    painter = QPainter(pixmap)
    painter.fillRect(36, 0, 1, 5, QColor(0, 0, 255))
    painter.end()

    image = qpixmap_to_pil(pixmap)
    assert image.size == (37, 5)
    assert image.getpixel((0, 2))[:3] == (255, 0, 0)
    assert image.getpixel((36, 2))[:3] == (0, 0, 255)
```

Needs `QPainter` added to that file's imports. This asserts no row-to-row skew at a
non-power-of-two width; it cannot synthesize a padded stride through `QPixmap`, so it is a
regression guard on pixel mapping rather than a proof of stride handling.

#### Acceptance criteria — ✅ all met
- Blur and pixelate still render correctly (checked programmatically on a generated screenshot
  rather than by eye: both effects produce a changed, correctly-sized region).
- No `bits()` call remains in `image_effects.py`.
- Full suite green (see the isolated-run caveat above — verify with `pytest`, not the single file).

#### Outcome
Also confirmed the new conversion is **byte-identical** to the old one on a 199×97 striped pixmap
(`bytesPerLine == width * 4` on this stack, so the stride argument is currently a no-op guard —
it earns its place on future padded-scanline formats/platforms).

---

### Task H3 — Zoom bounds bypass and stale status indicators

**Priority: Medium — user-visible**

#### Problem
Two related defects around the view transform:

1. **`_zoom_fit` escapes the clamp.** `ui/main_window.py:587` bounds zoom to 5%–1600%, but only
   inside `_scale_zoom`. `_zoom_fit` (`:570-576`) calls `fitInView` directly, which computes an
   arbitrary scale from the viewport/pixmap ratio. Fit a 4×4 pixmap in a maximized window and the
   view lands far above 1600%; a very large screenshot in a small window lands below 5%. From
   there, `_zoom_in`/`_zoom_out` refuse to act (the next step is still out of range), so the view
   is stuck.
   `_zoom_reset` (`:578-580`) is **not** affected — `resetTransform()` yields exactly 1.0, which is
   in range. The original note flagged it; it is a false positive.

2. **The indicators go stale on canvas-initiated fits.** `AnnotationCanvas` calls `fitInView`
   itself at `ui/canvas.py:224` (`load_image`), `:502` (`reset_all`) and `:635` (`_apply_crop`).
   Only the first is followed by an indicator refresh, and only when entered via
   `MainWindow.load_screenshot` (`ui/main_window.py:95`). After **Reset All** or a **crop** the
   `Zoom: N%` label shows the pre-operation value.
   The same root cause hits `_annotation_label`: `load_image` (`ui/canvas.py:217-230`) never emits
   `image_changed`, so capturing a second screenshot leaves the previous image's count on screen
   ("5 annotations" over an empty canvas) until the next annotation is placed.

#### What to do

**1. Move the zoom bounds into the view that owns the transform.** In `ui/canvas.py`, add
module-level constants next to the existing ones and two methods on `AnnotationCanvas`:

```python
MIN_ZOOM = 0.05
MAX_ZOOM = 16.0
```

```python
    def zoom_to_fit(self) -> None:
        if self._background_item is None:
            return
        self.fitInView(self._background_item, Qt.AspectRatioMode.KeepAspectRatio)
        self.clamp_zoom()

    def clamp_zoom(self) -> None:
        scale = self.transform().m11()
        if scale <= 0:
            return
        target = min(max(scale, MIN_ZOOM), MAX_ZOOM)
        if target != scale:
            factor = target / scale
            self.scale(factor, factor)
```

Replace all three internal `self.fitInView(self._background_item, ...)` calls
(`ui/canvas.py:224`, `:502`, `:635`) with `self.zoom_to_fit()`.

**2. Emit `image_changed` from `load_image()`** — append `self.image_changed.emit()` at the end of
`ui/canvas.py:217-230`. `reset_all` (`:510`) and the crop commit (`tools/handlers/base.py:60`)
already emit, so this is the only missing site.

**3. Consume the constants and the signal in `ui/main_window.py`:**

```python
from ui.canvas import MAX_ZOOM, MIN_ZOOM, AnnotationCanvas, ToolMode   # extend existing import

    def _zoom_fit(self) -> None:
        self._canvas.zoom_to_fit()
        self._update_zoom_indicator()

    def _scale_zoom(self, factor: float) -> None:
        if self._canvas._background_item is None:
            return
        current = self._canvas.transform().m11()
        next_scale = current * factor
        if not (MIN_ZOOM <= next_scale <= MAX_ZOOM):
            return
        self._canvas.scale(factor, factor)
        self._update_zoom_indicator()
```

and one line in `_connect_signals()` beside `ui/main_window.py:151`:

```python
        self._canvas.image_changed.connect(self._update_zoom_indicator)
```

This makes both permanent status widgets refresh from the same signal, and lets
`_update_zoom_indicator()` at `ui/main_window.py:95` become redundant (leave it — it is harmless
and covers the no-signal path).

Leave `_zoom_reset` unchanged.

#### Regression risk to watch
`zoom_to_fit()` now runs on `load_image`, so it affects the view transform in **every** UI test
that loads a pixmap, which in turn affects viewport→scene mapping for the `qtbot` mouse-simulation
tests covering all 8 tools. An unshown `QGraphicsView` defaults to roughly 100×30, so fitting the
640×480 `sample_pixmap` yields `min(100/640, 30/480) ≈ 0.0625` — above the 0.05 floor, so the clamp
should be inert and mapping unchanged. This is close to the boundary: if any tool test starts
failing on coordinates after this change, that margin is the cause. Verify with the full suite
before and after.

#### Tests to add (`tests/test_ui/test_scenario3_features.py`, `TestZoomIndicator`)

```python
    def test_zoom_fit_respects_max_bound(self, qapp, qtbot):
        from ui.canvas import MAX_ZOOM

        window = MainWindow()
        qtbot.addWidget(window)
        window.show()
        tiny = QPixmap(4, 4)
        tiny.fill(QColor("steelblue"))
        window.load_screenshot(tiny)
        window._zoom_fit()
        assert window._canvas.transform().m11() <= MAX_ZOOM

    def test_clamp_zoom_raises_to_min_bound(self, qapp, qtbot, sample_pixmap):
        from ui.canvas import MIN_ZOOM

        window = MainWindow()
        qtbot.addWidget(window)
        window.load_screenshot(sample_pixmap)
        window._canvas.resetTransform()
        window._canvas.scale(0.001, 0.001)
        window._canvas.clamp_zoom()
        assert window._canvas.transform().m11() == pytest.approx(MIN_ZOOM)

    def test_annotation_count_resets_on_new_capture(self, qapp, qtbot, sample_pixmap):
        window = MainWindow()
        qtbot.addWidget(window)
        window.load_screenshot(sample_pixmap)
        window._canvas.add_step_marker(QPointF(10, 10))
        assert window._annotation_label.text() == "1 annotations"
        window.load_screenshot(sample_pixmap)
        assert window._annotation_label.text() == "0 annotations"
```

Match the existing helper/import style in that file; the step-marker call above must be replaced
with whatever public path those tests already use to place an annotation.

#### Acceptance criteria — ✅ all met
- `_zoom_fit` on a 4×4 image never exceeds 1600%; `clamp_zoom` lifts an under-floor transform to 5%.
- `Zoom: N%` is correct immediately after Reset All and after a crop.
- The annotation count reads `0 annotations` right after a new capture.
- `_zoom_reset` behavior unchanged.
- Full suite green — 122 existing tests plus the new ones (133 total).

#### Outcome
The crop test drives the real `CROP` handler through `left_press`/`left_move`/`left_release`
instead of calling `_apply_crop` directly, so it exercises the same path a user takes. Each new
test was mutation-checked: reverting its specific fix makes exactly that test fail.

---

### Task H4 — Documentation sync ✅ (complete)

After H1–H3, update `AGENTS.md`:
- Note `MIN_ZOOM`/`MAX_ZOOM` and `zoom_to_fit()`/`clamp_zoom()` on the `AnnotationCanvas` row.
- Add `tests/test_build/` to the project-structure tree.
- Add "`load_image()` emits `image_changed`" to the conventions list, since status-bar widgets now
  depend on it.

Mark Phase 8 done in the Session Status block at the top of this file.

#### Outcome
All three items done, plus: `.github/workflows/` and `tests/test_main/` added to the tree,
`settings_service` corrected from a class to a module, Phase 7 conventions documented (logging
path, hotkey-thread marshaling, stride-safe conversion), and the **Key Classes / Graphics Items
line anchors corrected** — they had drifted from the source (e.g. `StepShotApp` was listed at
`main.py:27`, actually `:61`; `BlurPatchGraphicsItem` at `:312`, actually `:406`). Anchors were
re-derived from the files rather than hand-edited. At that time, `AGENTS.md` open questions were
also trimmed to the unresolved items; the new roadmap above now incorporates the relevant work.

---

## Running tests after each task

```powershell
cd e:\AI\stepshot
pip install -r requirements-test.txt
pytest                          # full suite (primary verification)
pytest -m acceptance            # PRD acceptance only
```

Note: `pytest tests/test_services/test_image_effects.py` in isolation may hard-crash (see
"Known environment issue" above). Prefer the full suite. All tasks must leave the suite green;
add new tests in the appropriate `tests/test_*/` subdirectory following `tests/conftest.py` patterns.

---

## Phase 17 — Annotation document/history refactor (issues 01–05)

Architecture spec: `architecture-document-history-spec.md`. Issue tracker:
`.scratch/annotation-document-history/issues/01-…05-….md`. The refactor deepens
one seam — the document/history interface — and keeps the Qt canvas as the
adapter that translates interaction and rendering into that interface.

### Task 17-01 — Establish the framework-neutral document/history module ✅ (complete)

#### Problem
Document state, snapshot serialization, undo/redo, and crop semantics all
live in `ui/canvas.py`. Adding a new annotation family duplicates canvas
dispatch on both the snapshot and the restore sides. Tool handlers and the
main window reach into private canvas state for derived values. The result
is that a single behavioral change touches many files and most document
behavior can only be tested by constructing a `QGraphicsView`.

#### Decision
Build `models/document_history.py` first — the framework-neutral core —
before any canvas migration. It owns:

- **Immutable document state**: `DocumentState` (`@dataclass(frozen=True)`)
  with `version`, `image: ImageValue | None`, ordered
  `tuple[AnnotationRecord, ...]`, and `step_counter`.
- **Framework-neutral image value**: `ImageValue` with owned `pixels: bytes`,
  `width`, `height`, `format: ImageFormat` (string enum), `stride`,
  `device_pixel_ratio`. No `QImage.Format` reference anywhere.
- **Immutable annotation records**: one frozen dataclass per family
  (`ArrowRecord`, `StepRecord`, `TextRecord`, `RectangleRecord`,
  `HighlightRecord`, `BlurRecord`, `PenRecord`) with `kind`, `version`, and
  geometry/colour/opacity/text fields as plain Python values. Pen strokes
  store `tuple[tuple[float, float], ...]` rather than `QPainterPath`.
- **Fixed adapter registry**: `AnnotationAdapter` (`kind`,
  `supported_versions`, `capture` callable, `restore` callable) +
  `AnnotationAdapterRegistry` + `build_default_registry()`. The adapters
  for this stage are stubs whose capture/restore raise
  `NotImplementedError`; the canvas adapter will wire them up in Issue 02.
  `registry.supports(kind, version)` is the validation hook.
- **Mutation results**: `AcceptedMutation(state)` and `RejectedMutation(reason)`,
  discriminated union `MutationResult`. Rejected operations leave the
  current document, undo stack, and redo stack untouched.
- **Atomic restoration**: `restore_snapshot(state)` validates every record
  against the registry before mutating. Unknown kind, unsupported version,
  or any record the registry rejects → `RejectedMutation` and zero state change.
- **History ownership**: `DocumentHistory` holds the current state, the
  full `_history: list[DocumentState]`, and an integer `_cursor`. Linear
  history model: `cursor == 0` is the bottom of history (undo returns
  `None`); `cursor == len(history) - 1` is the top (redo returns `None`).
  `apply()` truncates everything past the cursor (redo invalidation),
  appends the new state, then drops from the front until
  `len(history) <= HISTORY_CAP + 1` (the initial seed counts as +1).
  `HISTORY_CAP = 50` matches the existing `_undo_cap` exactly: a maximum
  of 50 user-action entries plus one initial state.
- **Complete state equality**: every record and every `ImageValue` is a
  frozen dataclass, so equality is structural across pixels, format,
  stride, device-pixel-ratio, annotation order, geometry, colour, opacity,
  text, blur mode/strength, pen points, and step counter. Transient
  interaction state (selection, edit cursor, resize handles, gesture
  previews) is excluded by design.

#### Conventions matched
- `from __future__ import annotations` at the top of the module.
- Type hints on every public name.
- One-line module docstring; **no** function or class docstrings (verified
  via AST, consistent with `models/step_marker.py`).
- No PySide6 imports — `grep ^from PySide6 models/document_history.py` →
  no matches.
- New module added to `StepShot.spec` `hiddenimports`
  (`tests/test_build/test_spec_hiddenimports.py` enforced this).

#### Tests (33 new, under `tests/test_models/test_document_history.py`)
- **ImageValue** (3 tests): owns pixel bytes, is frozen, preserves
  format/stride/DPR without any Qt type.
- **AnnotationRecord** (2 tests): arrow record is frozen; every supported
  family carries `kind` and `version`.
- **DocumentState equality** (6 tests): empty-vs-empty, pixel difference,
  annotation-order difference, annotation-property difference,
  step-counter difference, DPR difference.
- **DocumentHistory basics** (3 tests): starts empty, `apply` accepts,
  history becomes undoable.
- **History direction** (5 tests): undo returns previous, redo restores
  it, undo short-circuits at the bottom, redo short-circuits at the top,
  new mutation invalidates the redo stack.
- **History cap** (1 test): 60 `apply()` calls leave the undo stack at
  exactly 50 entries.
- **Rejected mutations** (4 tests): unknown kind rejected, unsupported
  version rejected, rejected mutation does not grow history, rejected
  mutation does not invalidate redo.
- **Atomic restoration** (4 tests): valid state accepted, unknown kind
  rejected, unsupported version rejected, rejected restoration leaves
  state and history unchanged.
- **Mixed documents** (1 test): round trip through apply/undo/redo
  preserves image pixels, annotation order, geometry, and all
  user-visible properties across all seven families.
- **Default registry** (3 tests): supports every currently supported kind,
  rejects unknown kinds, rejects unknown versions.

Mutation-checked indirectly: deleting `models/document_history.py` makes
`tests/test_models/test_document_history.py` collection fail with
`ModuleNotFoundError`, which is the strongest possible red signal — every
test in that file exercises a distinct seam of the new module.

#### Verification
- `pytest tests/test_models/test_document_history.py` → 33 passed
- `pytest` → 235 passed (202 baseline + 33 new)
- `pytest -m acceptance` → 26 passed (no regressions)

#### Out of scope here (handled by Issues 02–05)
- Migrating `ui/canvas.py` to translate Qt items into records and back
  through the adapter registry.
- Removing the existing `_snapshot_state` / `_restore_state` methods and
  the `_undo_stack` / `_redo_stack` lists on `AnnotationCanvas` once all
  callers have moved through the document/history interface.
- Decoupling tool handlers and `MainWindow` from canvas internals.
- Running the frozen-build smoke gate.

### Task 17-02 — Migrate the canvas to document/history and the adapter registry ✅ (complete)

#### Decision
`ui/annotation_adapters.py` became the Qt↔record translation layer:
per-family capture/restore callables for all seven families,
`qpixmap_to_image_value` / `image_value_to_qpixmap` (stride and
device-pixel-ratio preserving), `build_canvas_registry()`, and
`capturable_types()`. `ui/canvas.py` replaced `_snapshot_state` /
`_restore_state` / `_undo_stack` / `_redo_stack` with
`_capture_document_state()` / `_restore_document_state()` over a
`DocumentHistory`, exposed via the `history` property; the background
`ImageValue` is cached on `QPixmap.cacheKey()`. All existing workflows
(draw, move, resize, crop, effects, delete, duplicate, reset, undo/redo)
route through the document/history interface.

#### Bugs found and fixed during migration
- **Child-item guard destroyed scene items** — `item.parentItem()` inside
  `_capture_annotations` flipped Shiboken ownership to Python, deleting the
  C++ object when the loop variable went out of scope. Removed.
- **Step-marker children aborted every history push** —
  `StepMarkerGraphicsItem` is a `QGraphicsItemGroup`, so its children appear
  in `scene().items()` and `capture_annotation` raised `LookupError` on them.
  `_capture_annotations` now filters on `capturable_types()`.
- **Stacking-order reversal** (post-review) — `_restore_document_state`
  iterates `reversed(state.annotations)` so annotations restore bottom-first,
  matching original scene order. Mutation-checked: forward iteration fails
  exactly `test_undo_redo_preserves_mixed_annotations_pixel_perfect`.
- Post-review hardening: temp-list restore (scene mutated only after all
  restores succeed), null/0×0 pixmap guard in `load_image`, property-timer
  stop parity in `load_image` / `reset_to_original`, rejected-apply no longer
  clears redo, `supported_versions` derived from `_RECORD_VERSION`.

#### Intentional behavior deltas (documented)
- Duplicate consecutive states no longer grow history
  (`DocumentHistory.apply` short-circuits on `new_state == current`).
- `HISTORY_CAP = 50` counts user actions; the seed state is the 51st
  `DocumentState` in the internal list.

#### Tests and verification
- New: `tests/test_ui/test_annotation_adapters.py` (15) and
  `tests/test_ui/test_mixed_annotation_roundtrip.py` (6, pixel-perfect
  rendered output across undo/redo cycles).
- `pytest` → 264 passed; `pytest -m acceptance` → 26 passed.

### Task 17-03 — Remove obsolete snapshot and duplicate history paths ✅ (complete)

#### Decision
Contraction pass after migration: deleted `_snapshot_state`,
`_restore_state`, `_undo_stack`, `_redo_stack` from the canvas (zero
production/test callers remained, verified by grep) with no compatibility
aliases. `DocumentHistory` is the single owner of current state and both
stacks. Dead `AnnotationAdapterRegistry.kinds()` deleted (zero callers).

#### Post-review fix
The 400 ms `_property_timer` could fire mid-gesture and capture an in-flight
drag preview into history (reproduced with a probe: a phantom `'rectangle'`
record). Added `_flush_pending_property_undo()`, called at every gesture
start — tool `on_press` in `mousePressEvent`, `_begin_drag_tracking()`, and
`_begin_resize_tracking()` (replacing a bare timer `stop()` that discarded a
pending property change). Regression test
`test_pending_property_undo_flushes_before_gesture`; mutation-checked (bare
`stop()` fails exactly that test).

#### Tests and verification
- `pytest` → 265 passed; `pytest -m acceptance` → 26 passed.

### Task 17-04 — Decouple tool handlers and MainWindow from canvas internals ✅ (complete)

#### Decision
`tools/handlers/context.py` defines the `HandlerContext` protocol (scene
operations, undo/history push, image_changed emission, blur/crop application,
settings getters, text-editing lifecycle). The canvas implements it as the
adapter; `build_handlers(canvas)` attaches the canvas as the context. All 8
handlers dropped every `canvas._` access. MainWindow reads status state
through new public canvas methods — `annotation_count()`, `current_zoom()`,
`has_background()` — instead of `_background_item` and scene traversal.
Dead protocol surface removed on review: `scene()`, `get_blur_settings()`,
unused imports.

#### Tests and verification
- New: `tests/test_ui/test_handler_context.py` (27) — fake-context tests
  drive every handler without canvas internals; MainWindow interface tests
  pin the three new methods; all protocol tests request `qapp` (an
  isolation run without a QApplication hard-crashes 0xC0000409 under
  Python 3.14 + PySide6 6.11).
- Mutation-checked: `annotation_count()` → `return 0` fails 5 tests;
  `has_background()` → `return False` fails exactly its one new test.
- `pytest` → 292 passed; `pytest -m acceptance` → 26 passed.

### Task 17-05 — Verify the complete refactor ✅ (complete, verified 2026-09-06)

#### Decision
Final verification ticket: audit coverage across the seams, re-run every
gate, mutation-check the key regressions, and record the delta.

#### Verification (independently re-run)
- Coverage audit passed for document/history (40 tests across immutability,
  equality, versioning, atomic restore, mutations, undo/redo, cap,
  granularity), serialization (all seven families, stride/DPR, fail-closed),
  canvas interactions (draw/move/resize/crop/effects/select/delete/
  duplicate/reset/undo/redo/text-edit protection/no-ops), and rendered-pixel
  plus scene-space assertions.
- `pytest` → **292 passed** under `QT_QPA_PLATFORM=offscreen`;
  `pytest -m acceptance` → **26 passed**.
- Mutation checks: stacking order (1 failure), `annotation_count` (5),
  `has_background` (1), property-timer flush (1) — each restored to green.
- Hidden-import test green; `dist\StepShot.exe` rebuilt 2026-09-06 from the
  committed tree; `--smoke-test` exit code 0.

#### Test delta: 202 → 292 (+90)
40 document/history (33 + 7 hardening), 15 adapter round-trip,
6 mixed-annotation pixel-perfect, 27 handler-context, 2 canvas regressions
(rejected-apply, property-flush).

#### Accepted limitations (carried)
- Crop retention remains bbox-based (Phase 14 decision).
- Blur patch is selectable but not movable/duplicable (Phase 9 decision).
- `test_mixed_annotation_roundtrip.py:76` duck-types `BlurPatchGraphicsItem`
  via `__class__.__name__` (accepted nit).
