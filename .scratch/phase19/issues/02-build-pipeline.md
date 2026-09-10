# Ticket 02 — Slim the PyInstaller spec and switch to onedir

Blocked by: 01 (read the amended spec first)
Blocks: 04

Context pointers: `Phase19.md` (amended by ticket 01), `StepShot.spec`, `build.py`, `tests/test_build/test_spec_hiddenimports.py`, `AGENTS.md` (conventions + build notes).

Environment (verified on this machine): Python 3.14.3, PyInstaller 6.20.0, PySide6 6.11.1, Pillow 12.2.0 — all installed; `python` resolves correctly.

## Phase A — slim `StepShot.spec`

- Remove `collect_all("PySide6")` and `collect_all("PIL")` and everything they injected (`pyside6_*` / `pillow_*` datas, binaries, hidden). PyInstaller's built-in hooks take over.
- **Keep the static `hiddenimports = [` literal list exactly as-is** (name, order, format): `tests/test_build/test_spec_hiddenimports.py` parses that literal block.
- Add post-Analysis filtering of `a.binaries` and `a.datas`:
  - **Keep-list (checked first, never stripped):** `platforms/qwindows.dll`, `styles/qwindowsvistastyle.dll`, the whole `imageformats` / `styles` / `platforms` plugin folders (incl. `qjpeg.dll`, `qico.dll`), `opengl32sw.dll` (explicit user decision — software GL fallback for RDP/VM), `iconengines` + `Qt6Svg.dll` (icon safety), `Qt6Core.dll`, `Qt6Gui.dll`, `Qt6Widgets.dll`, shiboken6/pyside6 runtime DLLs, python/VC runtime DLLs.
  - **Bloat patterns to strip:** `Qt6WebEngine`, `Qt6Qml`, `Qt6Quick`, `Qt63D`, `Qt6Designer`, `Qt6Multimedia`, `Qt6Network`, `Qt6Sql`, `Qt6Pdf`, `Qt6Charts`, `Qt6DataVisualization`, `Qt6Graphs`, `Qt6Bluetooth`, `Qt6Sensors`, `Qt6SerialPort`, `Qt6Positioning`, `Qt6Location`, `Qt6RemoteObjects`, `Qt6Scxml`, `Qt6StateMachine`, `Qt6WebSockets`, `Qt6Test`, `Qt6Xml`, `Qt6OpenGL`, `Qt6DBus`, `Qt6NetworkAuth`, `Qt6Nfc`, `Qt6SpatialAudio`, PySide6 `translations/` (.qm), PySide6 `typesystems`, unused PySide6 `.pyd` modules.
- Keep the existing `excludes` list as belt-and-braces.
- **UPX stays rejected:** no `upx=True` anywhere; do not introduce UPX.

## Phase B — onedir

- `EXE(..., exclude_binaries=True, ...)` + `COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=False, name="StepShot")`.
- Output becomes `dist/StepShot/StepShot.exe`. Update the spec module docstring (no longer single-file).
- `build.py`: `DIST_EXE = ROOT / "dist" / "StepShot" / "StepShot.exe"`; report the **total `dist/StepShot` folder size in MB + file count** (exe size alone is meaningless now). Keep `--no-clean`. Module docstring may be updated; **no new function/class docstrings** (repo convention).

## Tests (this ticket owns `tests/test_build/`)

New `tests/test_build/test_spec_slimming.py` (test docstrings are allowed):
- spec text contains no `collect_all`
- spec contains `COLLECT(` and `exclude_binaries=True`
- spec keep-list names `qwindows.dll`, `qwindowsvistastyle.dll`, `qjpeg.dll`, `qico.dll`, `opengl32sw.dll`
- no `upx=True` in spec
- `build.DIST_EXE` equals `<repo>/dist/StepShot/StepShot.exe` (import the `build` module)

`test_spec_hiddenimports.py` must pass unchanged.

## Verification (in your worktree, in order)

1. `$env:QT_QPA_PLATFORM="offscreen"; pytest` — full suite green (321 existing + your new tests). Never run `tests/test_services/test_image_effects.py` alone (known hard-crash flake under Python 3.14).
2. `python build.py` — full clean build (allow up to 15 min).
3. `$env:QT_QPA_PLATFORM="offscreen"; dist\StepShot\StepShot.exe --smoke-test` — exit code 0 (allow a couple of minutes; the windowed bootloader exits via `os._exit(0)`).
4. Record: `dist/StepShot` folder size (MB), file count, `StepShot.exe` size, smoke wall time.

If the smoke test fails on a missing DLL/module, that DLL belongs on the keep-list: adjust, rebuild with `python build.py --no-clean`, re-smoke. Iterate until green.

## Commit

Single commit, repo style: `Phase 19: slim PyInstaller spec and switch to onedir build`.

## Report back

Measured numbers (folder size, file count, exe size, smoke time), pytest summary line, any keep-list adjustments beyond this ticket, commit hash.
