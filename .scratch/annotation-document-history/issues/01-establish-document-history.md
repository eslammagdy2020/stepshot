# 01 — Establish the framework-neutral annotation document/history module

**What to build:** A framework-neutral document/history module that represents the editable image and ordered annotations as immutable values, accepts or rejects document mutations, restores state atomically, and owns undo/redo history.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] Represent the annotation document with an immutable image value and immutable annotation records, including complete observable state and record version.
- [ ] Preserve pixel bytes, dimensions, color format, stride, and device-pixel-ratio metadata without depending on Qt image classes.
- [ ] Provide accepted mutation results and typed restoration rejection results; rejected operations leave the current document and history unchanged.
- [ ] Own the current state, undo stack, redo stack, 50-entry history cap, redo invalidation, and complete state equality in one module.
- [ ] Restore valid state atomically and reject malformed, unknown, unsupported-version, or unsupported annotation records without partial state.
- [ ] Add focused tests for empty and mixed documents, complete equality, history direction, history cap, rejected mutations, and atomic restoration.
- [ ] Keep the existing full suite green under the offscreen Qt environment.
