# 05 — Verify the complete refactor across document and canvas seams

**What to build:** A verified annotation document/history refactor whose framework-neutral state, Qt adapter, interaction workflows, rendered output, and frozen build preserve every existing contract.

**Blocked by:** 04 — Decouple tool handlers and MainWindow from canvas internals.

**Status:** ready-for-agent

- [ ] Verify document/history tests cover immutable state, image ownership, complete equality, version handling, atomic restoration, accepted/rejected mutations, undo/redo, history cap, and undo granularity.
- [ ] Verify serialization tests cover every supported annotation family, mixed ordering, geometry, user-visible properties, metadata, background state, and fail-closed capture.
- [ ] Verify canvas interaction tests cover draw, move, resize, crop, effects, select, delete, duplicate, reset, undo, redo, text-edit protection, and invalid-operation no-ops.
- [ ] Verify rendered-pixel assertions and scene-space coordinate assertions cover visual and geometry behavior.
- [ ] Run the full test suite under `QT_QPA_PLATFORM=offscreen` and the acceptance-marked suite.
- [ ] Mutation-check the key regression tests by reverting and restoring each relevant production fix.
- [ ] Run hidden-import verification and the frozen Windows smoke gate when new modules or build configuration are affected.
- [ ] Record the explicit test delta and any accepted limitations in the canonical project history.
