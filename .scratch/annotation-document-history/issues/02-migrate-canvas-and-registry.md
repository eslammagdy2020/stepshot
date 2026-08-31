# 02 — Migrate the canvas to document/history and the annotation adapter registry

**What to build:** The Qt canvas adapter translates its current background and scene annotations into framework-neutral document state and reconstructs them through a fixed annotation-adapter registry, preserving the complete editing workflow and rendered output.

**Blocked by:** 01 — Establish the framework-neutral annotation document/history module.

**Status:** ready-for-agent

- [ ] Create and restore records for every supported annotation family through the fixed registry.
- [ ] Keep annotation records self-contained, ordered, and complete for geometry and all user-visible properties.
- [ ] Keep image processing, Qt item creation, rendering, selection, view transforms, gesture state, and signal emission in the canvas adapter.
- [ ] Route draw, move, resize, crop, effects, delete, duplicate, reset, undo, and redo through the document/history interface without changing observable behavior.
- [ ] Preserve text-edit protection, property coalescing, invalid-operation no-op behavior, crop retention and translation rules, and one history entry per existing user-visible action.
- [ ] Add mixed-annotation round-trip and rendered-output integration tests through the canvas interface.
- [ ] Keep the current full and acceptance test suites green.
