# StepShot — Upgrade Plan v2 (Phase 18+)

Self-contained implementation guide for an AI coding agent.
Work through tasks in order — later tasks depend on earlier ones.

---

## Session Status

### Where to start next session
Phase 18 (Screenshot Inventory) complete and verified green (see `upgrade.md` for Phases 1–17 history).
Phase 19 (App Size & Startup Time Reduction) complete and verified green — see `Phase19.md`.
Next plan starts at Phase 20 (Inventory Persistence, optional post-MVP).
Last verified baseline: `pytest` = 326 passed, `pytest -m acceptance` = 30 passed.

---

## Phase 18 — Screenshot Inventory / Multi-Screenshot Management

**Priority: High — core workflow feature**

### Problem Statement
Users want to capture multiple screenshots in a session, keep them all accessible, cycle through them, and copy any one to the clipboard for pasting elsewhere. Currently each new capture replaces the previous screenshot.

### User Stories
1. As a user, I want every capture (region or full-screen) to be added to an inventory instead of replacing the current image.
2. As a user, I want to cycle through captured screenshots (Next/Previous) via toolbar buttons and keyboard shortcuts.
3. As a user, I want to see a visual indicator of which screenshot I'm viewing (e.g., "2 of 5").
4. As a user, I want to copy the current screenshot to clipboard (Ctrl+C or toolbar button) without exporting to disk.
5. As a user, I want to delete the current screenshot from the inventory.
6. As a user, I want to clear the entire inventory.
7. As a user, I want the inventory to persist for the session; closing the app discards it (no disk persistence required for MVP).

### Architecture Decisions
- **Inventory model**: Ordered list of `ScreenshotRecord` objects, each holding:
  - `QPixmap` (the captured image)
  - `ImageValue` (framework-neutral representation for undo/history)
  - `DocumentState` (annotations, step counter, history for that screenshot)
  - Metadata: capture timestamp, source type (region/full-screen)
- **Active index**: Integer pointing to current screenshot in inventory.
- **Canvas integration**: `AnnotationCanvas` operates on the *active* screenshot's `DocumentState`. Switching screenshots swaps the canvas's `_history`, `_background_item`, `_scene` annotations, and `_step_counter`.
- **Undo/redo**: Per-screenshot history stacks (each `DocumentHistory` already caps at 50). Global undo/redo only affects the active screenshot.
- **Clipboard**: `ClipboardService.copy_pixmap()` for the active screenshot's rendered output (background + annotations).
- **UI additions**:
  - Toolbar: Prev/Next buttons (icons: ← / →), counter label "N of M", Copy button, Delete button, Clear All button.
  - Shortcuts: `Ctrl+Tab` / `Ctrl+Shift+Tab` (Next/Prev), `Ctrl+C` (copy current), `Del` (delete current — already exists for annotations; add inventory-level delete via toolbar/menu).
- **Persistence**: In-memory only for MVP. No disk serialization.

### Implementation Tasks

#### 18.1 — Inventory Data Model
- Create `models/screenshot_inventory.py`:
  - `ScreenshotRecord` dataclass (frozen): `pixmap: QPixmap`, `image_value: ImageValue`, `document_state: DocumentState`, `timestamp: float`, `source: str`
  - `ScreenshotInventory` class: list of records, `current_index`, methods `add(record)`, `remove_at(index)`, `clear()`, `next()`, `prev()`, `get_current()`, `can_go_next()`, `can_go_prev()`, `__len__`
  - No PySide6 imports in model (store `QPixmap` as opaque reference; conversion helpers in canvas adapter).
- Add to `StepShot.spec` `hiddenimports`.

#### 18.2 — Canvas Adapter Integration
- `ui/canvas.py` changes:
  - Add `_inventory: ScreenshotInventory | None` and `_inventory_changed = Signal()` (emits when inventory changes or active index changes).
  - Replace `_original_pixmap`, `_history`, `_step_counter`, `_background_item` with delegation to `inventory.get_current()`.
  - New methods:
    - `set_inventory(inventory)` — initializes from inventory (first screenshot or empty).
    - `switch_to(index)` — saves current canvas state back to current record, loads new record's state into canvas (`_restore_document_state`, `_background_item`, `_step_counter`, `_history`).
    - `add_screenshot(pixmap, source)` — creates `ScreenshotRecord` with fresh `DocumentHistory` (seed = empty document with that background), appends to inventory, switches to it.
    - `remove_current()` — removes current record, switches to neighbor or shows empty state.
    - `copy_current_to_clipboard()` — renders current view, calls `ClipboardService.set_pixmap()`.
  - Update `load_image(pixmap)` → `add_screenshot(pixmap, "region")` (or "fullscreen").
  - Update `reset_to_original()` → resets *current* screenshot to its original captured pixmap (stored in `ScreenshotRecord`).
  - Property `has_screenshot` → `len(inventory) > 0`.
  - Property `inventory_count` → `len(inventory)`.
  - Property `current_index` → 1-based index for UI.

#### 18.3 — Toolbar & MainWindow UI
- `ui/toolbar.py`:
  - Add `prev_action`, `next_action`, `copy_action`, `delete_screenshot_action`, `clear_inventory_action`.
  - Add `inventory_counter` label ("1 of 3").
  - Shortcuts: `Ctrl+Tab` (next), `Ctrl+Shift+Tab` (prev), `Ctrl+C` (copy).
  - Enable/disable buttons based on `can_go_prev/next`, `has_screenshot`.
- `ui/main_window.py`:
  - Connect toolbar signals to canvas methods.
  - Connect `canvas._inventory_changed` to update counter label and button states.
  - Update status bar to show inventory count alongside annotation count.

#### 18.4 — Capture Flow Updates
- `main.py` `StepShotApp`:
  - `start_region_capture` / `start_full_screen_capture` → on capture success, call `main_window.add_screenshot(pixmap, source)` instead of `load_screenshot`.
  - First capture creates inventory; subsequent captures append.

#### 18.5 — Clipboard Service Extension
- `services/clipboard_service.py`: add `copy_pixmap(pixmap: QPixmap) -> bool` using `QApplication.clipboard().setPixmap()`.

#### 18.6 — Tests
- `tests/test_models/test_screenshot_inventory.py`: model add/remove/next/prev/clear, index bounds, empty-state behavior.
- `tests/test_ui/test_inventory.py`: canvas switching preserves per-screenshot annotations/undo/redo; copy to clipboard; delete current; clear all; toolbar button states; shortcuts.
- `tests/test_prd_acceptance/test_acceptance_criteria.py`: extend with inventory workflow tests (capture 3, cycle, copy, delete, verify rendered output).

### Acceptance Criteria
- Capture region → added as #1. Capture full-screen → added as #2. Toolbar shows "2 of 2".
- `Ctrl+Tab` cycles to #1, `Ctrl+Shift+Tab` back to #2.
- Annotations on #1 persist when switching to #2 and back.
- Undo/redo on #1 doesn't affect #2's history.
- `Ctrl+C` copies current rendered screenshot to clipboard (verifiable by pasting into another app or reading clipboard in test).
- Delete current removes it; inventory count decrements; neighbor becomes active.
- Clear All empties inventory; canvas shows empty placeholder.
- All existing tests still pass (292 → 292+new).

### Verification
```powershell
pytest tests/test_models/test_screenshot_inventory.py
pytest tests/test_ui/test_inventory.py
pytest -m acceptance
pytest
```

---

## Phase 19 — App Size & Startup Time Reduction

**Priority: High — distribution quality**

Spec: `Phase19.md` (single source of truth). One-line summary: slim the PyInstaller spec and switch
the frozen build from one-file to `--onedir` (`dist\StepShot\`).

### Key Decisions
- **Onedir only; onefile retired**: `dist\StepShot\` is the sole distribution format — no build flag,
  no single-exe fallback. The one-file unpack-to-`%TEMP%` cold start was the core problem.
- **`opengl32sw.dll` kept**: the ~20 MB software-GL fallback stays as insurance for RDP/VM users
  without hardware acceleration.
- **UPX rejected**: it breaks Qt6 vtables/relocations and triggers antivirus false positives.
- **Sharing via manual zip**: the user zips `dist\StepShot\` by hand for colleagues; no auto-zip
  tooling.

### Verification (2026-09-10, ticket 04)

```powershell
$env:QT_QPA_PLATFORM="offscreen"; pytest
$env:QT_QPA_PLATFORM="offscreen"; pytest -m acceptance
python build.py
$env:QT_QPA_PLATFORM="offscreen"; dist\StepShot\StepShot.exe --smoke-test
```

- `pytest` → **326 passed** under `QT_QPA_PLATFORM=offscreen` (321 + 5 new spec-guard tests in
  `tests/test_build/test_spec_slimming.py`); `pytest -m acceptance` → **30 passed**.
- Full clean `python build.py` → onedir `dist\StepShot\` = **94.4 MB, 69 files**; `StepShot.exe` = 3.1 MB.
- `--smoke-test` → exit code **0**, wall time ~1.3 s (1.27 s / 1.46 s across two runs).
- Before/after: the retired one-file build was ~250 MB (248.6 MB measured) and took 46–68 s to cold-start
  (PyInstaller unpacked the bundle to `%TEMP%` on every launch); the onedir build is 94.4 MB and its
  `--smoke-test` round-trip completes in ~1.3 s — nothing is unpacked at launch.

---

## Phase 20 — Inventory Persistence (Optional, Post-MVP)

**Priority: Medium**

- Save inventory to disk on close (JSON manifest + PNG files in `%LOCALAPPDATA%\StepShot\Inventory\`).
- Load on startup.
- Add "Save Session" / "Load Session" menu items.
- Configurable max inventory size (default 50) with LRU eviction.

---

## Phase 21 — Thumbnail Strip / Visual Inventory Panel (Optional)

**Priority: Low**

- Add a collapsible side panel showing thumbnails of all screenshots.
- Click thumbnail to switch.
- Drag to reorder.
- Right-click context menu (Copy, Delete, Rename).

---

## Related Files
- `upgrade.md` — Phases 1–17 history (read-only reference).
- `AGENTS.md` — Architecture, conventions, testing notes (Status section updated for Phase 18).
- `models/document_history.py` — Per-screenshot history (already supports this model).
- `ui/canvas.py` — Primary integration point.
- `ui/toolbar.py` — New actions.
- `main.py` — Capture flow.