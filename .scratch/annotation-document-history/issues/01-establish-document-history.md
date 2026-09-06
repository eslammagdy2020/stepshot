# 01 — Establish the framework-neutral annotation document/history module

**What to build:** A framework-neutral document/history module that represents the editable image and ordered annotations as immutable values, accepts or rejects document mutations, restores state atomically, and owns undo/redo history.

**Blocked by:** None — can start immediately.

**Status:** complete — committed as `0a574a1`, with follow-up hardening uncommitted

- [x] Represent the annotation document with an immutable image value and immutable annotation records, including complete observable state and record version.
- [x] Preserve pixel bytes, dimensions, color format, stride, and device-pixel-ratio metadata without depending on Qt image classes.
- [x] Provide accepted mutation results and typed restoration rejection results; rejected operations leave the current document and history unchanged.
- [x] Own the current state, undo stack, redo stack, 50-entry history cap, redo invalidation, and complete state equality in one module.
- [x] Restore valid state atomically and reject malformed, unknown, unsupported-version, or unsupported annotation records without partial state.
- [x] Add focused tests for empty and mixed documents, complete equality, history direction, history cap, rejected mutations, and atomic restoration.
- [x] Keep the existing full suite green under the offscreen Qt environment.

## Delivered

`models/document_history.py` — no PySide6 imports. `ImageValue`, `AnnotationRecord` plus one frozen
subclass per family, `DocumentState`, `AnnotationAdapter` / `AnnotationAdapterRegistry` /
`build_default_registry()`, `DocumentHistory` (list + cursor, `HISTORY_CAP = 50`), and the
`AcceptedMutation` / `RejectedMutation` union.

`tests/test_models/test_document_history.py` — **40 passed** (33 at commit time, 7 added since).
`StepShot.spec` carries `models.document_history`; `tests/test_build/test_spec_hiddenimports.py`
passes.

## Uncommitted follow-up in this module

Beyond the `0a574a1` commit, `models/document_history.py` and its tests gained:

- `ImageValue.__post_init__` — copies mutable pixel input to `bytes` and rejects negative
  dimensions/stride, stride too small for RGBA8888, pixel buffers shorter than `stride * height`, and
  non-positive device pixel ratio.
- `_validate_records` → `_validate_document`, now also checking document version, image format, and
  non-zero image dimensions, and rejecting non-`AnnotationRecord` entries.
- `DocumentHistory(..., initial_state=...)` — seeds history from a validated state, raising
  `ValueError` on an invalid seed. The canvas uses this on `load_image` / `reset_to_original`.
- `restore_snapshot` de-duplicated to delegate validation to `apply`.
- `SUPPORTED_ANNOTATION_KINDS` exported and used to build the default registry.

These are prerequisites for ticket 02 rather than gaps in 01.

## Notes

- The registry's `capture` / `restore` callables in this module are deliberate
  `NotImplementedError` stubs; the real Qt implementations land in ticket 02
  (`ui/annotation_adapters.py`).
- `models/document_history.py` has no trailing newline.
- Ticket 02's work is also present uncommitted in the same working tree, so a plain
  `git diff HEAD` mixes both tickets.
