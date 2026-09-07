# StepShot — Agent Guide

Windows desktop screenshot & annotation tool. Python + PySide6 (Qt Widgets / QGraphicsView).
Capture region or full screen → annotate (arrow, rectangle, text, highlight, blur, step number, pen, crop,
resize) → export PNG/JPG or clipboard.

## Status

**All planned phases (1–17) complete.** Last verified 2026-09-07, after the Phase 17 review-fix pass:
`pytest` = **292 passed** under `QT_QPA_PLATFORM=offscreen`; `pytest -m acceptance` = 26 passed; frozen
Windows build `dist\StepShot.exe` (248.6 MB, rebuilt 2026-09-07) passes its `--smoke-test` round-trip
with exit code 0.
See `upgrade.md` for the per-phase history and decisions. Future work should be tracked in a new plan file.

## Commands

```powershell
pip install -r requirements-test.txt            # includes requirements.txt
pytest                                          # 292 tests, ~5s — the only verification gate
pytest -m acceptance                            # 26 PRD acceptance tests
python main.py                                  # run from source
dist\StepShot.exe                               # run the frozen build
$env:QT_QPA_PLATFORM="offscreen"; dist\StepShot.exe --smoke-test   # headless smoke gate
pip install -r requirements-build.txt; python build.py            # → dist/StepShot.exe (~250 MB one-file)
```

There is **no linter, formatter, type checker, or codegen step** in this repo — no ruff/black/mypy config
exists. `pytest` is the whole verification story; do not invent a lint step or add tooling config unasked.

`build.py --no-clean` skips PyInstaller `--clean` for faster rebuilds. The windowed bootloader
(`runw.exe`) holds the host process alive; the smoke test in `main.py` uses `os._exit(0)` to release it.

## Environment gotchas

- **Local Python is 3.14; CI pins 3.13** (`.github/workflows/ci.yml`) because PySide6 has no 3.14 wheel yet.
  Don't "fix" the CI version.
- **CI runs on ubuntu-latest *and* windows-latest** with `QT_QPA_PLATFORM=offscreen`. All code and tests must
  stay headless- and Linux-import-safe even though the product is Windows-only.
- **Known flake:** running `tests/test_services/test_image_effects.py` *alone* can hard-crash
  (`0xC0000409`) under Python 3.14 + PySide6 6.11.x. Pre-existing, not a regression. Verify with the full
  suite, never that file in isolation.
- Git history starts at Phase 17: root commit `0a574a1` is the pre-refactor baseline plus Issue 01's
  module, so `git log` covers Phase 17 onward only — earlier phases were never committed.
- `keyboard` (global hotkeys) is optional: missing or failing registration degrades to toolbar-only with a
  QMessageBox, so never assume hotkeys are live.

## Architecture

Manual signal/slot wiring only — no DI, no state library.

`main.py` `StepShotApp` owns the app lifecycle and capture orchestration: hide window → `RegionSelector`
fullscreen overlay → `ScreenshotService.capture_region()` → `MainWindow.load_screenshot()`. The same
`main()` short-circuits to `_smoke_test()` when `--smoke-test` is in `sys.argv` (initializes Qt
offscreen, logs screen count, `os._exit(0)`).

`ui/canvas.py` `AnnotationCanvas(QGraphicsView)` is the hub (~1150 lines): tool mode, all property setters,
undo/redo, snapshot serialization, blur/crop application, zoom clamping, resize handle layer wiring,
in-flight gesture state. Most non-trivial changes land here.

`ui/resize_handles.py` (`ResizeHandleLayer`) is a view-overlay widget that draws 2 endpoint handles for
arrows and 4-corner + 4-edge handles for rectangle / highlight items, sized at a **constant 10 px on screen
at every supported zoom**. Hit-testing (`handle_at`) is called by the canvas; the layer is otherwise
mouse-transparent.

`tools/handlers/` holds per-tool mouse logic. `AnnotationCanvas` mouse events are thin dispatch into
`self._handlers[mode]`; a handler returning `True` from `on_press`/`on_release` means "committed".
`RectDragHandler` (base.py) does the shared drag/preview flow. `_commit()` now returns `bool` — `True`
means "push undo + emit image_changed", `False` means "no history" (used by `CropHandler` to skip both
when the gesture is invalid). Handlers interact with the canvas only through the `HandlerContext` protocol
(`tools.handlers.context`): the canvas implements this interface, exposing scene operations, undo/history,
settings getters, blur/crop application, and text-editing lifecycle. This decouples handler logic from
canvas internals.

`tools/*_tool.py` are thin `…ToolSettings` dataclasses with `defaults()` only. No logic lives there.

`services/` are static-method classes (`ScreenshotService`, `ExportService`, `ClipboardService`) except
`settings_service`, which is a module of `load()`/`save()` functions over QSettings (`StepShot`/`StepShot`).

## Conventions

- `from __future__ import annotations` at the top of every module; type hints everywhere.
- **One-line module docstring, and no function or class docstrings anywhere** in `main.py`/`ui`/`services`/
  `models`/`tools` (verified via AST: zero). Match this — don't add docstrings to source. Test files and
  fixtures *do* use docstrings.
- Log through `main.py`'s module `logger` (`"stepshot"`); never `print()`. `_setup_logging()` is idempotent
  and writes a rotating log to `%LOCALAPPDATA%\StepShot\StepShot\stepshot.log`, falling back to CWD.
- Hotkey callbacks from `keyboard` fire on a worker thread and must reach the GUI thread via
  `CaptureSignals` with `Qt.ConnectionType.QueuedConnection`. Never touch widgets from a hotkey callback.

## Undo / snapshots

Undo/redo is managed by `models.document_history.DocumentHistory`. `AnnotationCanvas.history` exposes the
history instance; its `undo_stack` and `redo_stack` properties return tuples of `DocumentState`. The canvas
captures state via `_capture_document_state()` (producing a `DocumentState` with `ImageValue`, annotations,
and step counter) and restores it via `_restore_document_state()`. History holds at most 50 undo entries
(51 `DocumentState`s including the current one). `load_image()` and `reset_to_original()` seed a fresh
`DocumentHistory` through `_reset_history()`, so loading a screenshot creates an initial state with no
undo entry.

`_push_undo_state()` stops `_property_timer`, captures the current document state, and applies it to
`DocumentHistory`. Property setters call `_schedule_property_undo()` instead (400 ms coalescing) so a slider
drag is one undo step. Every gesture start — tool `on_press` in `mousePressEvent`, Select-tool drag in
`_begin_drag_tracking()`, and resize-handle grabs in `_begin_resize_tracking()` — calls
`_flush_pending_property_undo()` first, so the 400 ms timer can never fire mid-gesture and capture an
in-flight drag preview or intermediate geometry into a history entry.

**Move and resize are both in undo history** since Phase 10 / Phase 13. A Select-tool move pushes one
state on `mouseReleaseEvent` if any item's `pos()` changed; a resize gesture pushes one state on
`_commit_resize_tracking` if either geometry or `pos()` changed.

**`undo()` and `redo()` short-circuit while a text item is in edit mode** (`_editing_text_item` is set).
The text doc's own Ctrl+Z / Ctrl+Y handles in-edit undo; the canvas undo resumes once
`_finalize_text_edit()` clears `_editing_text_item`. `undo()` and `redo()` also call
`_cancel_resize_tracking()` at the top so an in-flight resize gesture is dropped on any
undo / redo / load_image / reset_to_original / delete_selected / set_tool_mode / apply_crop call.

## Status-bar / zoom invariants

`image_changed` drives both `_update_annotation_count()` and `_update_zoom_indicator()` in `MainWindow`.
Any mutation of the background pixmap or the item set must emit it or the status bar goes stale.

`MIN_ZOOM`/`MAX_ZOOM` live in `ui/canvas.py`; every fit or scale path must end in `clamp_zoom()`
(`zoom_to_fit()` already does). Bypassing it with a raw `fitInView` can strand the view outside the bounds.

`AnnotationCanvas` overrides `scrollContentsBy`, `scale`, and `resetTransform` to call
`self._resize_layer.resize_to_viewport(self)` so the resize handles track the selected item through every
pan / zoom path (scrollbar drag, scroll-wheel, toolbar zoom in / out / reset, fit-to-window).

## Resize behavior

Selecting exactly one resizable item in `ToolMode.SELECT` shows the handle overlay. Supported
families: **arrow endpoints** (2 handles) and **rectangle / highlight boxes** (4 corners + 4 edges).
Out of scope by Phase 13 decision: text, pen, blur patch, and step marker (`marker_size` is a property,
not geometry). Click + drag a handle to resize; release commits one undo state only if geometry
changed. Geometry is clamped to a 4-scene-unit minimum and never produces negative dimensions.
The arrow's `set_geometry` refuses updates that would collapse below 4 scene units of manhattan
length; `_project_arrow` / `_project_rect` subtract `item.pos()` so a moved item still resizes
correctly.

## Behavior worth knowing before you touch it

- **Blur is destructive-ish and asymmetric**: `_apply_blur_region()` applies a Pillow effect to a copy of the
  background region and stores a `BlurPatchGraphicsItem`. Original pixels remain in the background. The
  blur patch is **selectable but not movable** (Phase 9 decision), and `_clone_item()` has no blur
  branch, so Ctrl+D does not duplicate it. `upgrade.md` Phase 9 is the open decision record here.
- Blur and crop convert logical → physical coords via `_logical_to_physical_rect()` for hi-DPI correctness.
- `qpixmap_to_pil()` passes `image.bytesPerLine()` as the raw decoder stride and reads `constBits()`; keep
  both or padded scanlines will shear the image.
- **Crop clamps to the background bounds and removes fully-outside annotations.** A wholly invalid
  crop gesture is a no-op (no history, no `image_changed`). Partially-intersecting annotations are
  translated by the *effective clamped* origin (not the requested origin). `Reset All` restores the
  pre-crop image by design.
- **Crop retention is bbox-based.** An arrow whose `sceneBoundingRect()` (which includes
  `max(12, thickness*4)` padding) touches the crop is retained even if its line is outside the crop.
  This was a documented accepted limitation of Phase 14 — the fix would override `shape()` and
  tighten selection hit-testing app-wide, which is not worth the edge case.

## Testing notes

- `pytest.ini` sets `pythonpath = .`, `qt_api = pyside6`, `--strict-markers`, and the marker
  `acceptance`.
- `tests/__init__.py` exists so tests can do `from tests.conftest import left_press, draw_arrow_on_canvas, …`;
  the test **subdirectories deliberately have no `__init__.py`** — don't add them.
- Autouse `isolated_settings` fixture redirects `settings_service.load/save` to an in-memory dict, so no test
  touches real QSettings. Other fixtures: `qapp`, `sample_pixmap` (640×480), `mock_clipboard`, `temp_image_path`.
- UI tests drive real Qt mouse events through `qtbot` + the conftest `left_press/left_move/left_release`
  helpers and `canvas.mapFromScene(...)`. `load_image()` calls `zoom_to_fit()`, so viewport↔scene mapping is
  scaled — always map coordinates rather than hardcoding viewport pixels.
- `tests/test_build/test_spec_hiddenimports.py` fails when any first-party module under
  `ui/services/models/tools` is missing from `StepShot.spec` `hiddenimports`. **Adding a new module means
  adding it to that list.**
- **Mutation-check new behavior tests.** Reverting a production fix should make exactly the targeted
  test fail. This is the verification gate for any post-review fix pass (see `upgrade.md` post-review
  blocks for examples).

## Related files

- `upgrade.md` — phased implementation plan; **all 17 phases complete** with decisions, acceptance
  criteria, per-phase verification commands, and post-review fix passes.
- `CLAUDE.md` — pointer to this file.
- `tests/README.md` — test invocation only.
