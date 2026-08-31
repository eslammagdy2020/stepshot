# Phase 11 — Atomic text creation and editing history

> **Status: completed 2026-08-24.** The full per-phase history lives in `upgrade.md`; this file
> is the original implementation brief, kept for reference. All 16 phases of the upgrade plan
> are now done.

**Implementation brief for a coding agent.** Read this whole file before editing. Follow the
repo conventions in `AGENTS.md` (no docstrings in `ui`/`services`/`models`/`tools`,
`from __future__ import annotations` at the top of every module, type hints everywhere, manual
signal wiring, log via `main.py`'s `"stepshot"` logger — never `print()`).

Baseline before you start: `pytest` = **152 passed** under `QT_QPA_PLATFORM=offscreen`. Phases
1–10 are complete. Do not touch other phases.

---

## Goal

Make text placement + first typing **one** undoable action, and route **all** existing-text
editing (including double-click) through canvas-owned history so no edit bypasses undo. After this
phase:

- Create text → type → **one** Undo removes the item; Redo restores the completed text.
- Edit existing text → Undo restores previous content; Redo restores the edit.
- Empty new text leaves **no** annotation and **no** history entry.
- Click-away, Escape, and double-click all use the **same** finalize/history contract.
- `"Enter instruction..."` never appears after Undo unless the user typed exactly that.
- Multiline text and the 400 ms property-edit coalescing (`_schedule_property_undo`) still work.

---

## Current behavior and why it is broken

### Files involved
- `tools/handlers/text.py` — `TextHandler.on_press()` (37 lines, whole file).
- `ui/canvas.py` — `_text_item_at` (`526`), `_start_text_edit` (`532`), `_finalize_text_edit`
  (`538`), plus `keyPressEvent` (`584`) and `mousePressEvent` (`594`) which call finalize.
- `ui/graphics_items.py` — `TextGraphicsItem` (`153`), specifically `mouseDoubleClickEvent`
  (`229`), `finalize_editing` (`234`), `focusOutEvent` (`240`).
- Snapshot/restore text branch in `ui/canvas.py`: `_snapshot_state` (`~801`) and `_restore_state`
  (`~894`) — the `"text"` tuple is `("text", pos, plain_text, color, font_size, bold)`.

### Bug 1 — creation pushes two history states
`TextHandler.on_press()` (`tools/handlers/text.py:26-36`) adds a `"Enter instruction..."`
placeholder item and immediately calls `canvas._push_undo_state()`. Later,
`_finalize_text_edit()` (`ui/canvas.py:547`) pushes **again**. So creating one text annotation
appends two snapshots. Result: after typing "Hello" and clicking away, one Undo restores the
**placeholder** state ("Enter instruction..." with no user text) instead of removing the
annotation. A second Undo is required to remove it. This violates "one create = one undo".

### Bug 2 — double-click editing bypasses canvas history
`TextGraphicsItem.mouseDoubleClickEvent()` (`ui/graphics_items.py:229-232`) turns on
`TextEditorInteraction` and grabs focus **directly**, without ever registering the item through
`AnnotationCanvas._editing_text_item`. So `_finalize_text_edit()` has nothing to finalize, no
before-value is captured, and editing existing text produces **zero** history — Undo after an edit
reverts some earlier unrelated action.

### Bug 3 — focus-out finalize skips history
`TextGraphicsItem.focusOutEvent()` (`ui/graphics_items.py:240-242`) calls the item-level
`finalize_editing()` (clears interaction, blanks placeholder) but never notifies the canvas, so a
focus-out triggered by clicking a non-canvas widget (toolbar, panel) finalizes the item visually
without committing/gating history and without clearing `_editing_text_item`.

---

## Design decision (do it this way)

### 1. Placeholder is display-only, tracked by a flag — never committed as history

Do **not** push history when the placeholder is created. Add an instance flag to
`TextGraphicsItem` that marks it as a not-yet-committed new item and marks whether the placeholder
text is still untouched. The canvas decides, at finalize time, whether anything happened.

Add to `TextGraphicsItem.__init__`:
```python
self.is_placeholder = False
```
Set it `True` only for the placeholder created by `TextHandler` (the handler sets it after
construction, or pass a flag). When the user types, clear it. The simplest reliable hook: override
`keyPressEvent` on `TextGraphicsItem` to set `self.is_placeholder = False` and, on the *first*
keystroke while `is_placeholder`, clear the placeholder text so typed characters replace it:

```python
def keyPressEvent(self, event: QKeyEvent) -> None:
    if self.is_placeholder:
        self.is_placeholder = False
        self.setPlainText("")
    super().keyPressEvent(event)
```
(Import `QKeyEvent` from `PySide6.QtGui`.) This guarantees a user who types the literal string
"Enter instruction..." still keeps it — the flag is cleared on the first key, so their text is
never treated as the placeholder. `finalize_editing()` must then stop special-casing the
`"Enter instruction..."` string and rely on the flag instead (see step 4).

### 2. `_start_text_edit` captures before-edit state

Extend the canvas to remember, for the item being edited, what it looked like before. Add fields in
`AnnotationCanvas.__init__` (next to `self._editing_text_item` at `ui/canvas.py:155`):
```python
self._editing_text_before: str | None = None
self._editing_text_is_new: bool = False
```
Change `_start_text_edit(self, item, *, is_new: bool = False)`:
```python
def _start_text_edit(self, item: TextGraphicsItem, *, is_new: bool = False) -> None:
    self._editing_text_item = item
    self._editing_text_is_new = is_new
    self._editing_text_before = None if is_new else item.toPlainText()
    item.setSelected(True)
    item.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
    item.setFocus(Qt.FocusReason.MouseFocusReason)
```

### 3. `TextHandler.on_press` no longer pushes history for creation

Rewrite `tools/handlers/text.py` so the new-item branch creates the placeholder, marks it, starts
the edit as new, and does **not** push undo or emit `image_changed`:
```python
item = TextGraphicsItem(
    "Enter instruction...",
    scene_pos,
    canvas._text_color,
    canvas._text_font_size,
    canvas._text_bold,
)
item.is_placeholder = True
canvas.scene().addItem(item)
canvas._start_text_edit(item, is_new=True)
return True
```
Keep the existing "already editing → finalize, then maybe start editing the clicked item" and
"clicked an existing item → start editing it" branches, but pass `is_new=False` when starting edit
on an existing item.

### 4. `_finalize_text_edit` is the single commit point, gated on real change

Rewrite `_finalize_text_edit` (`ui/canvas.py:538-547`) to push **exactly one** state only when the
result differs from before, and to remove empty new items with no history:
```python
def _finalize_text_edit(self) -> None:
    if self._editing_text_item is None:
        return
    item = self._editing_text_item
    is_new = self._editing_text_is_new
    before = self._editing_text_before
    self._editing_text_item = None
    self._editing_text_is_new = False
    self._editing_text_before = None

    item.finalize_editing()
    self.setFocus(Qt.FocusReason.OtherFocusReason)

    text = item.toPlainText().strip()

    if not text:
        # Empty result: brand-new item is discarded silently; a cleared existing
        # item is a real change and must be committed.
        if item.scene() is not None:
            self._scene.removeItem(item)
        if is_new:
            return
        self._push_undo_state()
        self.image_changed.emit()
        return

    if is_new or text != (before or "").strip():
        self._push_undo_state()
        self.image_changed.emit()
```
`finalize_editing()` on the item must **not** blank text based on the `"Enter instruction..."`
string anymore — change it to blank only when `self.is_placeholder` is still `True`:
```python
def finalize_editing(self) -> None:
    self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
    self.clearFocus()
    if self.is_placeholder:
        self.setPlainText("")
```

### 5. Route double-click through the canvas (no item→canvas back-reference)

Do **not** give `TextGraphicsItem` a reference to the canvas. Instead intercept double-click at the
view. **Remove** `TextGraphicsItem.mouseDoubleClickEvent` entirely, and add to
`AnnotationCanvas`:
```python
def mouseDoubleClickEvent(self, event) -> None:
    if self._background_item is None or event.button() != Qt.LeftButton:
        super().mouseDoubleClickEvent(event)
        return
    scene_pos = self.mapToScene(event.position().toPoint())
    item = self._text_item_at(scene_pos)
    if item is None:
        super().mouseDoubleClickEvent(event)
        return
    if self._editing_text_item is item:
        return
    if self._editing_text_item is not None:
        self._finalize_text_edit()
    self._start_text_edit(item, is_new=False)
```
This works regardless of the active tool (double-clicking existing text should edit it even in
SELECT mode). Confirm it does not fight the Phase 10 drag-tracking in `mousePressEvent`; a
double-click is press+release+press+release, and drag tracking only commits when a position
actually changed, so a stationary double-click pushes nothing from the drag path.

### 6. Focus-out must finalize through the canvas

`focusOutEvent` on the item still fires when focus leaves via a non-canvas widget. Give the item an
optional callback the canvas installs while editing, so the item can ask the canvas to finalize
without knowing what the canvas is:

In `TextGraphicsItem.__init__`:
```python
self.on_focus_out = None
```
In `focusOutEvent`:
```python
def focusOutEvent(self, event) -> None:
    super().focusOutEvent(event)
    if self.on_focus_out is not None:
        callback, self.on_focus_out = self.on_focus_out, None
        callback()
    else:
        self.finalize_editing()
```
In `_start_text_edit`, set `item.on_focus_out = self._finalize_text_edit`. In
`_finalize_text_edit`, clear it (`item.on_focus_out = None`) before doing work to avoid re-entrancy
(the `clearFocus()` inside `finalize_editing()` can trigger another `focusOutEvent`). Guard against
re-entrancy: `_finalize_text_edit` already early-returns when `_editing_text_item is None`, and it
nulls the field first — keep that ordering.

> Re-entrancy caution: `finalize_editing()` calls `clearFocus()`, which emits `focusOutEvent`. By
> nulling `self._editing_text_item` **and** `item.on_focus_out` before calling
> `finalize_editing()`, the nested call is a no-op. Verify this by hand and with a test.

---

## Snapshot format

No change needed to the `"text"` tuple. `_restore_state` rebuilds a fresh `TextGraphicsItem` with
`NoTextInteraction`; that item has `is_placeholder = False` by default (correct — restored items are
committed) and `on_focus_out = None` (correct — not editing). Do **not** serialize `is_placeholder`
or `on_focus_out`.

Multiline: `finalize` uses `.strip()` only for the empty check and the change comparison; store and
restore the full `toPlainText()` unchanged so interior newlines survive.

---

## Existing tests to keep green (and likely adjust)

- `tests/test_ui/test_scenario2_tools.py::TestTutorialTextWorkflow::test_inline_text_placement`
  (`124-135`) — presses in TEXT mode and asserts one item with `TextEditorInteraction`. Still valid:
  placeholder is created and edit started. Keep.
- `...::test_click_away_finishes_text_without_adding_another` (`137-151`) — sets text via
  `setPlainText("Step 1: Open menu")` directly (bypasses the placeholder-clear keystroke, so
  `is_placeholder` stays `True`!). **This is a trap:** with the flag design, a direct `setPlainText`
  leaves `is_placeholder = True`, so `finalize_editing()` would blank it and the item would be
  discarded, breaking the assertion of one remaining item. **Fix the test** to clear the flag the
  way real typing would, e.g. set `texts[0].is_placeholder = False` before `setPlainText(...)`, or
  drive a real keystroke via `QTest.keyClicks`. Prefer a real keystroke so the test exercises the
  production path. Document this in the test.
- `tests/test_ui/test_canvas.py::test_text_annotation_can_be_added` (`95-104`) and the delete tests
  (`286-308`) use the `add_text_annotation` conftest helper, which adds committed text and pushes
  once. Unaffected. Keep.
- `tests/test_prd_acceptance/test_acceptance_criteria.py::TestTextTool` (`157-177`) uses
  `add_text_annotation`. Unaffected.
- `tests/test_ui/test_graphics_items.py::TestTextGraphicsItem` (`68-109`) constructs items directly.
  `is_placeholder`/`on_focus_out` default to safe values; these stay green. If you remove the
  `"Enter instruction..."` string special-case from `finalize_editing`, check no test asserts on it
  (none currently do).

If you change the `add_text_annotation` helper or `conftest`, re-run the whole suite — many files
import from `tests.conftest`.

---

## New tests to write

Create `tests/test_ui/test_text_history.py`. Drive **real** interaction, not `setPlainText` alone.
Use `QTest.keyClicks(canvas.viewport(), "Hello")` (import `from PySide6.QtTest import QTest`) after
the placement press so the placeholder-clearing keystroke path runs. Helpers `left_press` etc. are
in `tests.conftest`. A text edit is finalized by pressing elsewhere in TEXT mode, by Escape, or by
`canvas._finalize_text_edit()`.

Cover:

1. **Create + type = one undo removes it.** TEXT mode, press at P, `keyClicks("Hello")`, finalize
   (press far away). Assert one `TextGraphicsItem` with text "Hello". `canvas.undo()` → zero text
   items in the scene (in one step). `canvas.redo()` → text "Hello" back.
2. **Placeholder never surfaces after undo.** Same as (1) but after `undo()` assert no scene item's
   `toPlainText()` equals `"Enter instruction..."` and the text-item count is zero.
3. **Empty new text leaves nothing and no history.** Record `len(canvas._undo_stack)`; TEXT mode,
   press at P (placeholder created), finalize without typing. Assert zero text items and
   `len(canvas._undo_stack)` unchanged from before the press.
4. **Edit existing text: undo restores previous, redo restores edit.** Add committed text "Before"
   (via `add_text_annotation` or create+type+finalize). Double-click it
   (`canvas.mouseDoubleClickEvent` with a synthesized `QMouseEvent`, or call
   `canvas._start_text_edit(item, is_new=False)` then `keyClicks`), change to "After", finalize.
   `undo()` → text is "Before"; `redo()` → "After". Assert one text item throughout.
5. **Editing without changing text pushes no history.** Start editing committed text, finalize
   without changes. Assert `len(canvas._undo_stack)` unchanged.
6. **Double-click routes through canvas.** After committing text, synthesize a double-click over it
   and assert `canvas._editing_text_item` is that item and its interaction flag is
   `TextEditorInteraction`.
7. **Escape finalizes like click-away.** Create + type, press Escape (`QTest.keyClick(canvas,
   Qt.Key_Escape)`), assert finalized (`_editing_text_item is None`) and text retained; one undo
   removes it.
8. **Multiline survives create + undo + redo.** Type "Line1\nLine2" (use
   `QTest.keyClick(..., Qt.Key_Return)` between, or `keyClicks` won't insert newlines — send an
   explicit Return key), finalize, `undo()`, `redo()`, assert `toPlainText() == "Line1\nLine2"`.

For synthesizing a double-click event, mirror the `drag_item_on_canvas` helper added in Phase 10 in
`tests/conftest.py` (it builds `QMouseEvent`s and sends them to `canvas.viewport()`); add a small
`double_click_on_canvas(canvas, app, scene_pos)` helper there if it keeps tests clean.

---

## Acceptance criteria (from `upgrade.md` Phase 11)

- Create text, type, then Undo removes the item in one step; Redo restores the completed text.
- Edit existing text, then Undo restores the previous content and Redo restores the edit.
- Empty new text leaves no annotation and no extra undo action.
- Clicking away, pressing Escape, and double-click editing all use the same history contract.
- `"Enter instruction..."` never appears after Undo unless the user typed that exact value.
- Multiline text and property-edit coalescing behavior preserved.

---

## Verification

Run focused tests while implementing, then the full suite:
```powershell
$env:QT_QPA_PLATFORM = "offscreen"
pytest tests/test_ui/test_text_history.py tests/test_ui/test_canvas.py tests/test_ui/test_scenario2_tools.py
pytest
```
The full suite must end green. Expected count: 152 (current) minus any tests you rewrite in place,
plus the new `test_text_history.py` cases (target ≥ 8 new). Do not run
`tests/test_services/test_image_effects.py` in isolation — a known Py3.14 + PySide6 6.11 hard crash
affects single-file runs of that module only; verify via the full suite.

No new first-party source **module** is added (only a test file), so
`tests/test_build/test_spec_hiddenimports.py` needs no change. If you somehow add a module under
`ui/services/models/tools`, you must also add it to `StepShot.spec` `hiddenimports`.

---

## When done

Update `upgrade.md`:
- Move the Session Status line to "Phases 1–11 complete", set the new verified `pytest` count.
- Point "Where to start next session" at **Phase 12 — Cross-monitor and mixed-DPI region capture**.
- Add a "Done this session (Phase 11)" bullet summarizing: creation no longer double-pushes;
  double-click and focus-out routed through canvas-owned finalize; placeholder is flag-tracked;
  one-commit-on-change semantics; new `tests/test_ui/test_text_history.py`.

## Files you will touch

- `tools/handlers/text.py` — drop the create-time `_push_undo_state`/`image_changed`; mark
  placeholder; start edit as new.
- `ui/canvas.py` — `_start_text_edit(is_new=...)`, rewritten `_finalize_text_edit`, new
  `mouseDoubleClickEvent`, two new `__init__` fields, install/clear `on_focus_out`.
- `ui/graphics_items.py` — `TextGraphicsItem`: add `is_placeholder`/`on_focus_out`, `keyPressEvent`
  override, flag-based `finalize_editing`, canvas-routed `focusOutEvent`, remove
  `mouseDoubleClickEvent`.
- `tests/conftest.py` — optional `double_click_on_canvas` helper; possibly adjust the
  click-away test's setup (or do that in its own file).
- `tests/test_ui/test_scenario2_tools.py` — fix `test_click_away_finishes_text_without_adding_another`
  for the placeholder-flag path.
- `tests/test_ui/test_text_history.py` — **new** suite.
