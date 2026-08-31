---
triage: ready-for-agent
status: proposed
source: architecture-review-20260831-stepshot.html
---

## Problem Statement

As a StepShot maintainer, I need annotation document behavior and history behavior to have locality. Today, the Qt canvas module owns interaction state, annotation mutation, crop and effects, snapshots, restoration, undo/redo, selection, and zoom. Tool handlers and the main window reach into that implementation through private state, while snapshot and restoration logic duplicate annotation-type branching. This makes a change to one annotation type or history rule spread across unrelated code and forces tests to construct a large Qt view to verify document behavior.

## Solution

Deepen the annotation document module behind one highest seam: a document/history interface responsible for document state, annotation records, snapshot and restoration, mutation commits, and undo/redo. Keep the existing Qt canvas as the adapter that translates Qt interaction and rendering into that interface. Make annotation serialization explicit behind the document/history interface so each supported annotation type has one capture/restore implementation rather than duplicated canvas dispatch. Preserve current user-visible behavior, snapshot invariants, history cap, crop semantics, and rendering behavior.

## User Stories

1. As a StepShot maintainer, I want document state managed by a focused module, so that annotation behavior has locality.
2. As a StepShot maintainer, I want history management behind a small interface, so that undo and redo rules can change in one place.
3. As a StepShot maintainer, I want snapshot creation and restoration behind the document/history interface, so that callers do not depend on tuple layout or annotation implementation details.
4. As a StepShot maintainer, I want each supported annotation type to provide capture and restore behavior through one explicit serialization seam, so that adding an annotation does not require duplicated dispatch edits.
5. As a StepShot maintainer, I want the document/history interface to preserve the metadata and background snapshot invariants, so that step numbering, background pixels, undo, and redo remain correct.
6. As a StepShot maintainer, I want history entries to preserve annotation ordering and all supported annotation properties, so that restoration is lossless for existing behavior.
7. As a StepShot maintainer, I want mutation commits to report whether a mutation was accepted, so that invalid operations do not create history entries or emit stale image changes.
8. As a StepShot maintainer, I want undo and redo to restore document state through the same interface, so that both directions use one implementation.
9. As a StepShot maintainer, I want the existing history limit of 50 entries preserved, so that memory usage and established behavior do not change.
10. As a StepShot maintainer, I want a new action after undo to clear redo history, so that history follows the current editing branch.
11. As a StepShot maintainer, I want text-edit mode protections preserved, so that canvas undo and redo do not interfere with the text document’s own editing history.
12. As a StepShot maintainer, I want in-flight gesture cancellation preserved across undo, redo, image load, reset, delete, tool changes, and crop, so that restored state never retains stale Qt item references.
13. As a StepShot maintainer, I want crop to remain a document mutation, so that effective clamping, annotation retention, translation, blur-patch source rectangles, and reset behavior remain unchanged.
14. As a StepShot maintainer, I want invalid crop operations to remain true no-ops, so that they create no history entry and emit no image-change signal.
15. As a StepShot maintainer, I want annotation duplication, deletion, movement, resizing, and property changes to continue using the document/history interface, so that each accepted user action has the existing undo contract.
16. As a StepShot maintainer, I want the Qt canvas to remain responsible for view transforms, painting, selection, and pointer-event translation, so that the document/history module does not absorb presentation concerns.
17. As a StepShot maintainer, I want tool handlers to consume the smallest practical canvas adapter surface, so that handler behavior no longer depends on arbitrary private canvas state.
18. As a StepShot maintainer, I want MainWindow to consume derived canvas state through its existing public-facing interface, so that it does not inspect background items or traverse scene internals.
19. As a StepShot maintainer, I want document/history tests to run without constructing a QGraphicsView, so that state and history failures are fast and deterministic to diagnose.
20. As a StepShot maintainer, I want annotation serialization tests to cover every supported annotation family, so that missing capture or restore behavior fails at the explicit seam.
21. As a StepShot maintainer, I want round-trip tests for every supported annotation property, so that color, opacity, thickness, geometry, text, marker state, blur metadata, and crop-related state cannot silently disappear.
22. As a StepShot maintainer, I want tests for empty documents and background-only documents, so that history behavior is defined without annotations.
23. As a StepShot maintainer, I want tests for mixed annotation documents, so that ordering and cross-type restoration are verified together.
24. As a StepShot maintainer, I want tests for repeated undo and redo at the history cap, so that the 50-entry limit remains observable and correct.
25. As a StepShot maintainer, I want tests for rejected mutations, so that failed operations never partially alter state.
26. As a StepShot maintainer, I want real Qt interaction tests for draw, move, resize, crop, effects, select, delete, duplicate, undo, and redo, so that the canvas adapter is proven against actual user workflows.
27. As a StepShot maintainer, I want rendered-pixel assertions for visual operations, so that tests verify visible output rather than only scene item counts.
28. As a StepShot maintainer, I want coordinate assertions in scene space for moved and resized annotations, so that local geometry and item position are not confused.
29. As a StepShot maintainer, I want the existing offscreen test environment preserved, so that the full suite remains runnable on CI and headless systems.
30. As a StepShot maintainer, I want the frozen-build hidden-import contract preserved if new first-party modules are added, so that the Windows build continues to include all runtime modules.
31. As a StepShot maintainer, I want no observable behavior change from this refactor, so that users retain the current editing workflow and output.

## Implementation Decisions

- The primary seam is one document/history interface. It covers document state, annotation records, snapshot, restore, accepted mutation commit, undo, redo, and history-cap behavior.
- The Qt canvas remains the application-facing adapter for the document/history module. It continues to own Qt scene objects, rendering, view transforms, selection, gesture lifecycle, and signal emission.
- Annotation serialization is an internal seam behind the document/history interface, not a second caller-facing seam. Annotation adapters own capture and restoration for their annotation family; the document/history module owns ordering, metadata, background state, and history transitions.
- Replace positional, canvas-owned snapshot branching with explicit versioned annotation records. The record shape must preserve the existing metadata sentinel, background pixmap state, annotation ordering, and all currently supported properties. Migration must keep existing in-memory undo/redo behavior intact; no persistent file-format migration is required unless the current implementation already persists these records.
- Preserve the current supported annotation families and their behavior: arrows, rectangles, highlights, text, pen strokes, step markers, and blur patches. Resize handles remain view-overlay state and must not enter document snapshots.
- Preserve the existing history rules: a maximum of 50 entries, redo cleared after a new accepted mutation, property changes coalesced according to the current timer behavior, and invalid mutations producing no history entry.
- Preserve text-edit mode behavior: canvas undo and redo remain inactive while a text item is being edited, allowing the text document’s own editing history to handle those keystrokes.
- Preserve gesture teardown behavior. The Qt canvas adapter must cancel in-flight resize and other gesture state before operations that detach or replace scene items.
- Preserve signal semantics. Accepted mutations and document restoration must continue to update the rendered image and status state through the existing image-change path; rejected mutations must not emit stale updates.
- Preserve crop semantics, including logical-to-physical conversion, background-bound clamping, fully outside annotation removal, partially intersecting annotation retention, effective-origin translation, blur-patch source-rectangle translation, and reset-to-original behavior.
- Reduce private canvas coupling for tool handlers where it is necessary to use the document/history seam. The adapter may retain private implementation methods internally, but handlers should depend on the smallest context needed for gesture decisions and accepted commits.
- Reduce MainWindow’s implementation coupling by exposing derived state through the canvas interface rather than reading the background item or traversing the scene for annotation counts.
- Keep the implementation compatible with the project’s existing Python, PySide6, and offscreen test conventions. New first-party modules must be included in the frozen-build hidden-import list.
- Do not introduce a general dependency-injection framework, a new state library, persistent storage, or a second parallel document model. The goal is one deep module and one Qt adapter, not a new architecture layer for its own sake.

## Testing Decisions

- Tests must cross the highest seam available. Document/history tests exercise the document/history interface without constructing a QGraphicsView. Annotation serialization tests exercise capture/restore through the internal serialization seam and verify complete round trips.
- Tests must assert external behavior and contracts: restored state, history depth and direction, accepted/rejected mutation results, preserved ordering, emitted image-change behavior, and rendered output. Tests must not assert private helper calls or the internal class layout.
- Existing Qt interaction tests are the prior art for canvas behavior. Reuse the shared mouse and keyboard helpers in `tests/conftest.py`, drive real tool modes through synthesized events, map coordinates through the canvas, and allow the established ±1 pixel tolerance where event synthesis rounds coordinates.
- Preserve pixel-level acceptance coverage for filled rectangles, highlights, blur/pixelation, and crop dimensions. Compare rendered pixels or output dimensions rather than only annotation counts.
- Add focused document/history coverage for empty and mixed documents, metadata and background preservation, every annotation family, ordering, undo/redo round trips, redo invalidation after a new mutation, the 50-entry cap, property coalescing, text-edit mode, and rejected mutations.
- Add focused serialization coverage that fails when a supported annotation family lacks either capture or restore registration. Each family must have a round-trip test covering geometry and user-visible properties.
- Add adapter integration coverage proving that a real canvas mutation reaches the document/history interface and that restoration updates the scene and rendered output without changing current behavior.
- Add failure-path tests for every new rejection or error branch using explicit exception or result assertions appropriate to the existing project conventions. Invalid input must be verified as a true no-op, including no history change and no image-change signal.
- Run the full suite under `QT_QPA_PLATFORM=offscreen`, then run the acceptance-marked suite. If a new module is added, run the hidden-import test and the frozen-build smoke gate when build files are affected.
- Mutation-check the key regression tests by temporarily removing the production change and confirming the targeted test fails, then restoring the implementation before the final full-suite run.

## Out of Scope

- Replacing PySide6, QGraphicsView, or the current scene-based rendering model.
- Redesigning the annotation visual appearance or user interaction semantics.
- Adding new annotation types or new editing capabilities.
- Generic resizing for text, pen, blur patches, or step markers.
- Persistent document storage, project files, or compatibility migration for files not currently persisted by StepShot.
- Introducing a dependency-injection framework, state-management library, or broad rewrite of every platform adapter.
- Reworking screenshot capture, export, clipboard, or global hotkey implementations unless the document/history seam exposes a concrete regression in those modules.
- Changing the 50-entry history cap, property coalescing interval, crop retention policy, or text-edit undo semantics.
- Removing the Qt canvas adapter or moving view-only state such as resize-handle overlays into document snapshots.
- Adding a second independent implementation of document state for tests.

## Further Notes

- The architecture review identified this as the strongest candidate because it provides the most leverage and locality: history, snapshots, crop, and annotation mutation can be tested and changed behind one interface.
- The repository has no ADR directory or commit history. `CONTEXT.md` now records the resolved domain terms from this grilling session, while the spec preserves the established StepShot vocabulary and current implementation contracts.
- The current verification baseline recorded in `AGENTS.md` and `upgrade.md` is 202 full tests and 26 acceptance tests under the offscreen Qt environment. The refactor is complete only when those existing behaviors remain green, with any new tests counted explicitly.
- Tracker publication is unavailable because no issue-tracker configuration or CLI was found. The `ready-for-agent` triage label is recorded in the front matter for later import or manual publication.
- Grilling decisions: deliver the work as separately reviewable stages; use framework-neutral immutable records and image values with owned pixel bytes, stride, color-format, and device-pixel-ratio metadata; use a fixed annotation-adapter registry; reject unknown, malformed, unsupported-version, or unregistered annotation records without partial restoration or silent omission; keep one document/history owner with no duplicate canvas history; return structured internal mutation results; keep the document/history module signal-free and let the canvas adapter present errors and emit existing Qt signals.
- Grilling decisions: records are created from Qt items by the canvas adapter; document-state equality covers all observable state but excludes transient interaction state; serialization is an in-memory contract only; image processing remains canvas-owned; old private snapshot methods are deleted after caller migration with no compatibility aliases; performance optimization waits for profiling; the document interface is internal only.
- Grilling decisions: preserve one history entry per current user-visible action, initial screenshot load without an undo entry, Reset All as one undoable mutation, the current 50-entry cap, property coalescing, text-edit protection, crop policy, and all existing rendering and interaction contracts. Stage one must retain the current 202 full tests and 26 acceptance tests; completion requires focused contract coverage and mutation checks.
