# 03 — Remove obsolete snapshot and duplicate history paths

**What to build:** A single history owner for StepShot, with obsolete canvas snapshot methods and duplicate history paths removed after all callers have migrated.

**Blocked by:** 02 — Migrate the canvas to document/history and the annotation adapter registry.

**Status:** ready-for-agent

- [ ] Confirm zero production and test callers remain for the obsolete private snapshot and restoration paths.
- [ ] Delete obsolete snapshot methods and duplicate history state without compatibility aliases.
- [ ] Confirm the document/history module is the only owner of current state and undo/redo stacks.
- [ ] Confirm transient selection, text-editing state, previews, resize handles, and in-progress gestures remain outside document snapshots.
- [ ] Add or retain a deletion-test regression proving behavior crosses the replacement interface.
- [ ] Keep all existing document, canvas, and acceptance tests green after contraction.
