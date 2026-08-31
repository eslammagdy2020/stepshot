# 04 — Decouple tool handlers and MainWindow from canvas internals

**What to build:** Tool handlers and MainWindow use focused canvas interfaces instead of reaching across arbitrary private canvas state, while the current editing workflow and status behavior remain unchanged.

**Blocked by:** 03 — Remove obsolete snapshot and duplicate history paths.

**Status:** ready-for-agent

- [ ] Give tool handlers only the context needed for gesture decisions, preview lifecycle, text editing, effects, crop, and accepted commits.
- [ ] Make the canvas the adapter from that handler context to Qt scene and document/history behavior.
- [ ] Expose image presence, zoom state, and annotation count through the canvas interface used by MainWindow.
- [ ] Remove MainWindow reads of background-item implementation details and direct scene traversal for derived status state.
- [ ] Preserve status updates, selection behavior, zoom invariants, signal behavior, and all existing tool interactions.
- [ ] Add focused handler-context and MainWindow interface tests, plus real Qt interaction coverage for representative workflows.
- [ ] Keep the current full and acceptance test suites green.
