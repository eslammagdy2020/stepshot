# 04 — Decouple tool handlers and MainWindow from canvas internals

**What to build:** Tool handlers and MainWindow use focused canvas interfaces instead of reaching across arbitrary private canvas state, while the current editing workflow and status behavior remain unchanged.

**Blocked by:** 03 — Remove obsolete snapshot and duplicate history paths.

**Status:** complete

- [x] Give tool handlers only the context needed for gesture decisions, preview lifecycle, text editing, effects, crop, and accepted commits.
- [x] Make the canvas the adapter from that handler context to Qt scene and document/history behavior.
- [x] Expose image presence, zoom state, and annotation count through the canvas interface used by MainWindow.
- [x] Remove MainWindow reads of background-item implementation details and direct scene traversal for derived status state.
- [x] Preserve status updates, selection behavior, zoom invariants, signal behavior, and all existing tool interactions.
- [x] Add focused handler-context and MainWindow interface tests, plus real Qt interaction coverage for representative workflows.
- [x] Keep the current full and acceptance test suites green.

**Verification:**
- Full test suite: 292 passed (was 265; +27 new tests in `tests/test_ui/test_handler_context.py`)
- Acceptance tests: 26 passed
- Smoke test: passes (rebuilt from source on 2026-09-03)
- Mutation-check new behavior tests: reverting production `AnnotationCanvas` methods `annotation_count()` → return 0, `has_background()` → return False each breaks exactly the targeted new tests (5 and 1 failures respectively). The `TestHandlerContextMutationCheck` tests in `test_handler_context.py` exercise the fake context methods; they are not production code mutations but serve as behavioral regression guards for the handler logic.

**Changes:**
- Created `tools/handlers/context.py` with `@runtime_checkable HandlerContext` protocol (zero docstrings per tools/ convention)
- Updated all 8 tool handlers to use context methods instead of canvas internals
- Added `AnnotationCanvas` adapter methods implementing `HandlerContext`
- Added MainWindow-facing methods: `annotation_count()`, `current_zoom()`, `has_background()`
- Removed dead code: unused imports, `get_blur_settings`, redundant `scene()` override
- Updated `AGENTS.md` to document the new architecture